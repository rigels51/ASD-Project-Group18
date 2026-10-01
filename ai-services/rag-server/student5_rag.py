import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


DOMAIN = "assessment"

BASE_DIR = Path(__file__).resolve().parent
POLICY_PATH = BASE_DIR / "corpus" / "assessment_policy.md"
POLICY_SOURCE_ID = "ai-services/rag-server/corpus/assessment_policy.md"
AUDIT_PATH = BASE_DIR / "chroma" / "assessment-audit.jsonl"

ASSESSMENT_DATABASE_URL = os.getenv("ASSESSMENT_DATABASE_URL", "http://localhost:5022").rstrip("/")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

MIN_SIMILARITY = float(os.getenv("ASSESSMENT_RAG_MIN_SIMILARITY", "0.34"))
HIGH_SIMILARITY = float(os.getenv("ASSESSMENT_RAG_HIGH_SIMILARITY", "0.70"))
MAX_RESULTS = 8
INDEX_TTL_SECONDS = 60  # re-read live data at most once a minute

INSUFFICIENT = "Insufficient evidence in the Assessment & Grades data to answer this question."

COURSE_CODE = re.compile(r"\b[A-Za-z]{2,4}\d{3}\b")
STOPWORDS = {
    "a", "about", "after", "all", "am", "an", "and", "any", "are", "as", "at", "be", "been", "before",
    "being", "by", "can", "could", "did", "do", "does", "for", "from", "get", "give", "got", "had", "has",
    "have", "how", "i", "if", "in", "into", "is", "it", "its", "me", "much", "my", "need", "of", "on",
    "or", "our", "please", "should", "show", "so", "tell", "than", "that", "the", "their", "them", "then",
    "there", "these", "they", "this", "those", "to", "up", "us", "was", "we", "were", "what", "when",
    "where", "which", "who", "why", "will", "with", "would", "you", "your", "many", "list", "any",
}

_INDEX: dict[str, Any] = {"chunks": [], "loaded_at": 0.0, "warnings": []}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(tool: str, tool_input: dict, outcome: str, started: float, details: dict | None = None) -> None:
    try:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_PATH.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps({
                "request_id": str(uuid.uuid4()),
                "domain": DOMAIN,
                "tool_name": tool,
                "tool_input": tool_input,
                "timestamp": _now(),
                "duration_ms": round((time.monotonic() - started) * 1000),
                "outcome": outcome,
                "details": details or {},
            }) + "\n")
    except OSError:
        pass


def _stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _tokens(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in STOPWORDS}


def _fmt_number(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(number)) if number.is_integer() else f"{number:g}"


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------

def load_policy_chunks(path: Path = POLICY_PATH) -> list[dict[str, Any]]:
    """Split the policy document into one chunk per '## N. Title' section."""
    text = path.read_text(encoding="utf-8")
    chunks = []
    for match in re.finditer(r"^## (\d+)\. (.+?)\n(.*?)(?=^## |\Z)", text, re.M | re.S):
        number, title, body = match.group(1), match.group(2).strip(), match.group(3).strip()
        chunks.append({
            "chunk_id": f"policy-{number}",
            "source_id": f"{POLICY_SOURCE_ID}#section-{number}",
            "section": f"Policy section {number}: {title}",
            "course_id": None,
            "text": f"{title}. {body}",
        })
    return chunks


def _get_list(path: str) -> list[dict[str, Any]]:
    response = requests.get(f"{ASSESSMENT_DATABASE_URL}{path}", timeout=10)
    response.raise_for_status()
    records = response.json()
    if not isinstance(records, list):
        raise ValueError(f"assessment database returned an invalid list for {path}")
    return records


def build_data_chunks(assessments: list[dict], grades: list[dict]) -> list[dict[str, Any]]:
    """Turn assessment records + anonymised grade statistics into retrievable chunks."""
    chunks: list[dict[str, Any]] = []
    by_course: dict[str, list[dict]] = {}

    for a in sorted(assessments, key=lambda r: (str(r.get("course_id")), str(r.get("due_date")))):
        code = str(a.get("course_id") or "").upper()
        by_course.setdefault(code, []).append(a)
        description = (a.get("description") or "").strip().rstrip(".")
        chunks.append({
            "chunk_id": f"assessment-{a.get('assessment_id')}",
            "source_id": f"assessment-database-service:/assessments/{a.get('assessment_id')}",
            "section": f"{code} assessment: {a.get('assessment_name')}",
            "course_id": code,
            "text": (
                f"Assessment '{a.get('assessment_name')}' for course {code}. "
                f"Type: {a.get('assessment_type')}. "
                + (f"Description: {description}. " if description else "")
                + f"Due date {a.get('due_date')}. "
                f"Weight {_fmt_number(a.get('weight'))} percent of the course. "
                f"Marked out of {_fmt_number(a.get('max_mark'))}."
            ),
        })

    for code, items in sorted(by_course.items()):
        total = sum(float(i.get("weight") or 0) for i in items)
        listing = "; ".join(
            f"{i.get('assessment_name')} ({i.get('assessment_type')}, due {i.get('due_date')}, "
            f"weight {_fmt_number(i.get('weight'))}%)"
            for i in items
        )
        chunks.append({
            "chunk_id": f"course-{code}",
            "source_id": f"assessment-database-service:/assessments?course_id={code}",
            "section": f"{code} assessment summary",
            "course_id": code,
            "text": (
                f"Course {code} has {len(items)} assessments: {listing}. "
                f"Total weight of the course assessments is {_fmt_number(round(total, 1))} percent."
            ),
        })

    grades_by_course: dict[str, list[dict]] = {}
    for g in grades:
        grades_by_course.setdefault(str(g.get("course_id") or "").upper(), []).append(g)
    for code, rows in sorted(grades_by_course.items()):
        percents = []
        bands: dict[str, int] = {}
        for row in rows:
            if row.get("mark") is None or not row.get("max_mark"):
                continue
            percents.append(float(row["mark"]) / float(row["max_mark"]) * 100)
            if row.get("grade"):
                bands[row["grade"]] = bands.get(row["grade"], 0) + 1
        pending = len(rows) - len(percents)
        average = f"{sum(percents) / len(percents):.1f} percent" if percents else "not available yet"
        band_text = ", ".join(f"{band} {count}" for band, count in sorted(bands.items())) or "none"
        chunks.append({
            "chunk_id": f"grades-{code}",
            "source_id": f"assessment-database-service:/grades/course/{code}",
            "section": f"{code} grade statistics (anonymised)",
            "course_id": code,
            "text": (
                f"Grade statistics for course {code}: {len(percents)} marks recorded, "
                f"{pending} pending or ungraded. Average result {average}. "
                f"Grade band counts: {band_text}."
            ),
        })
    return chunks


def refresh_corpus(caller: str = "student") -> dict[str, Any]:
    """Rebuild the in-memory index from the policy file and the live database."""
    started = time.monotonic()
    try:
        chunks = load_policy_chunks()
    except OSError as exc:
        _audit("refresh_corpus", {"caller": caller}, "error", started)
        return {"status": "error", "error": f"policy corpus unreadable: {exc}"}

    warnings = []
    try:
        chunks += build_data_chunks(_get_list("/assessments"), _get_list("/grades"))
    except (requests.RequestException, ValueError) as exc:
        warnings.append(f"assessment database unavailable, indexed policy only: {type(exc).__name__}")

    _INDEX.update(chunks=chunks, loaded_at=time.monotonic(), warnings=warnings)
    for chunk in chunks:
        chunk["_tokens"] = _tokens(chunk["text"] + " " + chunk["section"])

    details = {"chunk_count": len(chunks), "warnings": warnings}
    _audit("refresh_corpus", {"caller": caller}, "success", started, details)
    return {
        "status": "success",
        "domain": DOMAIN,
        "caller": caller,
        "chunk_count": len(chunks),
        "data_chunk_count": sum(1 for c in chunks if not c["chunk_id"].startswith("policy-")),
        "policy_chunk_count": sum(1 for c in chunks if c["chunk_id"].startswith("policy-")),
        "warnings": warnings,
    }


def _ensure_index() -> dict[str, Any] | None:
    stale = time.monotonic() - _INDEX["loaded_at"] > INDEX_TTL_SECONDS
    if not _INDEX["chunks"] or stale:
        result = refresh_corpus(caller="auto_refresh")
        if result.get("status") != "success":
            return result
    return None


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

STUDENT_ID = re.compile(r"\bSTU-?\s?\d{3,4}\b", re.IGNORECASE)
# Tie-break order when scores are equal: course summary first, then single records, then policy.
CHUNK_PRIORITY = {"course": 3, "assessment": 2, "grades": 1, "policy": 0}


def _plan(query: str) -> dict[str, Any]:
    codes = sorted({c.upper() for c in COURSE_CODE.findall(query)})
    keywords = _tokens(STUDENT_ID.sub(" ", query))
    return {
        "course_codes": codes,
        "mentions_student_id": bool(STUDENT_ID.search(query)),
        "keywords": sorted(keywords),
    }


def _score(plan: dict[str, Any], chunk: dict[str, Any]) -> float:
    keywords = set(plan["keywords"])
    if not keywords:
        return 0.0
    coverage = len(keywords & chunk["_tokens"]) / len(keywords)
    # Small boost when the keywords name the section itself (e.g. "grade bands" -> policy-5).
    coverage += 0.2 * len(keywords & _tokens(chunk["section"])) / len(keywords)
    if plan["course_codes"] and chunk.get("course_id"):
        if chunk["course_id"] in plan["course_codes"]:
            coverage += 0.3
        else:
            coverage *= 0.3  # another course's data is unlikely to be the answer
    return round(min(coverage, 1.0), 4)


def _priority(chunk_id: str) -> int:
    return CHUNK_PRIORITY.get(chunk_id.split("-", 1)[0], 0)


def retrieve_context(query: str, k: int = 5, caller: str = "student") -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}
    started = time.monotonic()

    failed = _ensure_index()
    if failed:
        _audit("retrieve_context", {"query": query, "caller": caller}, "error", started)
        return failed

    plan = _plan(query)
    scored = sorted(
        (
            {key: value for key, value in chunk.items() if key != "_tokens"}
            | {"similarity": _score(plan, chunk)}
            for chunk in _INDEX["chunks"]
        ),
        key=lambda row: (row["similarity"], _priority(row["chunk_id"])),
        reverse=True,
    )[: min(max(k, 1), MAX_RESULTS)]
    results = [{"rank": i + 1, **row} for i, row in enumerate(scored)]

    _audit("retrieve_context", {"query": query, "k": k, "caller": caller}, "success", started,
           {"chunk_ids": [r["chunk_id"] for r in results]})
    return {
        "status": "success",
        "domain": DOMAIN,
        "query": query,
        "caller": caller,
        "plan": plan,
        "results": results,
        "warnings": _INDEX["warnings"],
    }


def confidence_category(results: list[dict[str, Any]]) -> str:
    top = max((r["similarity"] for r in results), default=0.0)
    if top >= HIGH_SIMILARITY:
        return "high"
    if top >= MIN_SIMILARITY:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def _generate(query: str, evidence: list[dict[str, Any]]) -> str:
    context = "\n".join(f"[{row['chunk_id']}] {row['text']}" for row in evidence)
    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": (
                "You answer questions about university assessments and grades.\n"
                "Rules:\n"
                "- Use ONLY the evidence below. Do not use outside knowledge or guess.\n"
                "- Mention assessment names, due dates and weights exactly as written.\n"
                "- Cite the evidence label for each fact, for example [course-ASD101].\n"
                "- Answer in at most four sentences.\n"
                f"- If the evidence does not answer the question, reply exactly: {INSUFFICIENT}\n\n"
                f"Question: {query}\n\nEvidence:\n{context}"
            ),
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 220},
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


def _extractive_answer(evidence: list[dict[str, Any]]) -> str:
    """Grounded fallback: quote the strongest evidence verbatim with its labels."""
    summary = next((row for row in evidence if row["chunk_id"].startswith("course-")), None)
    picked = [summary] if summary else evidence[:2]
    return " ".join(f"{row['text']} [{row['chunk_id']}]" for row in picked)


def _grounding_problem(answer: str, evidence: list[dict[str, Any]]) -> str | None:
    """Return why a model answer is not grounded, or None if it passes."""
    if not answer:
        return "empty model output"
    evidence_text = " ".join(row["text"] for row in evidence).upper()
    unknown_codes = {c.upper() for c in COURSE_CODE.findall(answer)} - set(COURSE_CODE.findall(evidence_text))
    if unknown_codes:
        return f"model mentioned course codes not in evidence: {', '.join(sorted(unknown_codes))}"
    unknown_dates = set(re.findall(r"\d{4}-\d{2}-\d{2}", answer)) - set(re.findall(r"\d{4}-\d{2}-\d{2}", evidence_text))
    if unknown_dates:
        return f"model mentioned dates not in evidence: {', '.join(sorted(unknown_dates))}"
    return None


def _abstain(query: str, reason: str, retrieval: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "domain": DOMAIN,
        "query": query,
        "answer": INSUFFICIENT,
        "citations": [],
        "confidence_category": "low",
        "insufficient_evidence": True,
        "generator": "none (abstained)",
        "retrieval_summary": {
            "retrieved_count": len(retrieval.get("results", [])),
            "evidence_count": 0,
            "top_chunk": None,
            "min_similarity": MIN_SIMILARITY,
        },
        "agentic_workflow": {
            "plan": retrieval.get("plan"),
            "act": "Ranked assessment records and policy sections by keyword coverage.",
            "observe": {"evidence_count": 0, "confidence_category": "low"},
            "adapt": reason,
        },
    }


def answer_question(query: str, k: int = 5, caller: str = "student") -> dict[str, Any]:
    started = time.monotonic()
    retrieval = retrieve_context(query, k, caller)
    if retrieval.get("status") != "success":
        _audit("answer_question", {"query": query, "caller": caller}, "error", started)
        return retrieval

    plan = retrieval["plan"]
    results = retrieval["results"]

    # A course code the system has no record of can never be answered: abstain, don't guess.
    known_codes = {c["course_id"] for c in _INDEX["chunks"] if c.get("course_id")}
    unknown = [code for code in plan["course_codes"] if code not in known_codes]
    if unknown:
        result = _abstain(query, f"Abstained: no assessment records exist for {', '.join(unknown)}.", retrieval)
        _audit("answer_question", {"query": query, "caller": caller}, "abstained", started, {"unknown": unknown})
        return result

    evidence = [r for r in results if r["similarity"] >= MIN_SIMILARITY]
    confidence = confidence_category(results)
    if confidence == "low" or not evidence:
        reason = "Abstained: no record or policy section passed the similarity threshold."
        if plan["mentions_student_id"]:
            reason += (" Individual student results are not indexed (privacy boundary); "
                       "use the MCP tool get_student_grade_summary for one student's grades.")
        result = _abstain(query, reason, retrieval)
        _audit("answer_question", {"query": query, "caller": caller}, "abstained", started)
        return result

    generator = f"ollama:{OLLAMA_MODEL}"
    try:
        answer = _generate(query, evidence)
        problem = _grounding_problem(answer, evidence)
        if problem:
            answer, generator = _extractive_answer(evidence), f"extractive fallback ({problem})"
        elif answer.strip() == INSUFFICIENT:
            if confidence == "high":
                answer, generator = _extractive_answer(evidence), "extractive fallback (model abstained on strong evidence)"
            else:
                result = _abstain(query, "Abstained: the model judged the evidence insufficient.", retrieval)
                _audit("answer_question", {"query": query, "caller": caller}, "abstained", started)
                return result
        elif "[" not in answer:
            answer += " Sources: " + ", ".join(f"[{row['chunk_id']}]" for row in evidence[:3])
    except (requests.RequestException, ValueError) as exc:
        answer, generator = _extractive_answer(evidence), f"extractive fallback (Ollama unavailable: {type(exc).__name__})"

    citations = [
        {"chunk_id": r["chunk_id"], "section": r["section"], "source_id": r["source_id"],
         "similarity": r["similarity"], "text": r["text"]}
        for r in evidence
    ]
    top = results[0] if results else None
    result = {
        "status": "success",
        "domain": DOMAIN,
        "query": query,
        "answer": answer,
        "citations": citations,
        "confidence_category": confidence,
        "insufficient_evidence": False,
        "generator": generator,
        "retrieval_summary": {
            "retrieved_count": len(results),
            "evidence_count": len(evidence),
            "top_chunk": top["chunk_id"] if top else None,
            "top_similarity": top["similarity"] if top else None,
            "min_similarity": MIN_SIMILARITY,
        },
        "agentic_workflow": {
            "plan": plan,
            "act": f"Ranked {len(_INDEX['chunks'])} assessment records and policy sections by keyword coverage.",
            "observe": {
                "evidence_count": len(evidence),
                "confidence_category": confidence,
                "citation_chunk_ids": [c["chunk_id"] for c in citations],
            },
            "adapt": f"Answered from retrieved evidence with citations ({generator}).",
        },
    }
    _audit("answer_question", {"query": query, "k": k, "caller": caller}, "success", started,
           {"confidence_category": confidence, "citation_chunk_ids": [c["chunk_id"] for c in citations],
            "generator": generator})
    return result
