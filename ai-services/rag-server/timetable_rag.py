"""Student 3 timetable domain for the shared RAG server.

Knowledge source: corpus/timetable_policy.md (Room Booking & Scheduling Policy).
Selected by POST /answer with {"domain": "timetable"}.

PLAN    — decide which policy sections are needed for the question
ACT     — embed the question with Ollama and rank policy chunks by cosine similarity
OBSERVE — keep only chunks above the similarity threshold and grade confidence
ADAPT   — answer with citations when evidence is strong enough, otherwise abstain
"""

import json
import math
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


BASE_DIR = Path(__file__).resolve().parent
CORPUS_PATH = BASE_DIR / "corpus" / "timetable_policy.md"
AUDIT_PATH = BASE_DIR / "chroma" / "timetable-audit.jsonl"
SOURCE_ID = "ai-services/rag-server/corpus/timetable_policy.md"
DOMAIN = "timetable"

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
MIN_SIMILARITY = float(os.getenv("RAG_MIN_SIMILARITY", "0.55"))
HIGH_SIMILARITY = float(os.getenv("RAG_HIGH_SIMILARITY", "0.70"))
MAX_RESULTS = 5
INSUFFICIENT = "Insufficient evidence in the scheduling policy to answer this question."

_INDEX: dict[str, list] = {"chunks": [], "vectors": []}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(tool: str, tool_input: dict, outcome: str, started: float, details: dict | None = None) -> None:
    try:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_PATH.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps({
                "request_id": str(uuid.uuid4()),
                "tool_name": tool,
                "tool_input": tool_input,
                "timestamp": _now(),
                "duration_ms": round((time.monotonic() - started) * 1000),
                "outcome": outcome,
                "details": details or {},
            }) + "\n")
    except OSError:
        pass


def load_chunks(path: Path = CORPUS_PATH) -> list[dict[str, Any]]:
    """Split the policy document into one chunk per '## N. Title' section."""
    text = path.read_text(encoding="utf-8")
    chunks = []
    for match in re.finditer(r"^## (\d+)\. (.+?)\n(.*?)(?=^## |\Z)", text, re.M | re.S):
        number, title, body = match.group(1), match.group(2).strip(), match.group(3).strip()
        chunks.append({
            "chunk_id": f"policy-{number}",
            "section": f"Section {number}: {title}",
            "source_id": f"{SOURCE_ID}#section-{number}",
            "text": f"{title}. {body}",
        })
    return chunks


def _embed(texts: list[str], kind: str) -> list[list[float]]:
    if not texts:
        return []
    if "nomic" in OLLAMA_EMBED_MODEL:
        prefix = "search_query: " if kind == "query" else "search_document: "
        texts = [prefix + t for t in texts]
    response = requests.post(
        f"{OLLAMA_HOST}/api/embed",
        json={"model": OLLAMA_EMBED_MODEL, "input": texts},
        timeout=120,
    )
    response.raise_for_status()
    embeddings = response.json().get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) != len(texts):
        raise ValueError("Ollama returned an invalid embedding response")
    return embeddings


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def refresh_corpus(caller: str = "student") -> dict[str, Any]:
    """Re-read the policy document and rebuild the in-memory vector index."""
    started = time.monotonic()
    try:
        chunks = load_chunks()
        vectors = _embed([c["text"] for c in chunks], kind="document")
        _INDEX["chunks"], _INDEX["vectors"] = chunks, vectors
        _audit("refresh_corpus", {"caller": caller}, "success", started, {"chunk_count": len(chunks)})
        return {"status": "success", "domain": DOMAIN, "caller": caller, "chunk_count": len(chunks), "source_id": SOURCE_ID}
    except Exception as exc:
        _audit("refresh_corpus", {"caller": caller}, "error", started)
        return {"status": "error", "error": str(exc)}


def retrieve_context(query: str, k: int = 3, caller: str = "student") -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}
    started = time.monotonic()
    try:
        if not _INDEX["chunks"]:
            refreshed = refresh_corpus(caller="auto_refresh")
            if refreshed.get("status") != "success":
                raise RuntimeError(refreshed.get("error", "corpus refresh failed"))
        query_vector = _embed([query], kind="query")[0]
        scored = sorted(
            (
                {**chunk, "similarity": round(_cosine(query_vector, vector), 4)}
                for chunk, vector in zip(_INDEX["chunks"], _INDEX["vectors"])
            ),
            key=lambda row: row["similarity"],
            reverse=True,
        )[: min(k, MAX_RESULTS)]
        results = [{"rank": i + 1, **row} for i, row in enumerate(scored)]
        _audit("retrieve_context", {"query": query, "k": k, "caller": caller}, "success", started,
               {"chunk_ids": [r["chunk_id"] for r in results]})
        return {"status": "success", "domain": DOMAIN, "query": query, "caller": caller, "results": results}
    except Exception as exc:
        _audit("retrieve_context", {"query": query, "caller": caller}, "error", started)
        return {"status": "error", "query": query, "error": str(exc)}


def confidence_category(results: list[dict[str, Any]]) -> str:
    top = max((r["similarity"] for r in results), default=0.0)
    if top >= HIGH_SIMILARITY:
        return "high"
    if top >= MIN_SIMILARITY:
        return "medium"
    return "low"


def _generate(query: str, evidence: list[dict[str, Any]]) -> str:
    context = "\n\n".join(f"[{row['chunk_id']}] {row['text']}" for row in evidence)
    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": (
                "You answer questions about a university timetable policy.\n"
                "Rules:\n"
                "- Use ONLY the policy evidence below.\n"
                "- Cite every claim with its exact label, for example [policy-4].\n"
                "- Answer in at most three sentences.\n"
                f"- If the evidence does not answer the question, reply exactly: {INSUFFICIENT}\n\n"
                f"Question: {query}\n\nPolicy evidence:\n{context}"
            ),
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 220},
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("response", "").strip() or INSUFFICIENT


def answer_question(query: str, k: int = 3, caller: str = "student") -> dict[str, Any]:
    started = time.monotonic()
    retrieval = retrieve_context(query, k, caller)
    if retrieval.get("status") != "success":
        _audit("answer_question", {"query": query, "caller": caller}, "error", started)
        return retrieval

    evidence = [r for r in retrieval["results"] if r["similarity"] >= MIN_SIMILARITY]
    confidence = confidence_category(retrieval["results"])

    if confidence == "low":
        answer, citations = INSUFFICIENT, []
        adapt = "Abstained: no policy section passed the similarity threshold."
    else:
        try:
            answer = _generate(query, evidence)
        except requests.RequestException as exc:
            _audit("answer_question", {"query": query, "caller": caller}, "error", started)
            return {"status": "error", "query": query, "error": f"Ollama request failed: {exc}"}
        citations = [
            {"chunk_id": r["chunk_id"], "section": r["section"], "source_id": r["source_id"],
             "similarity": r["similarity"]}
            for r in evidence
        ]
        adapt = "Answered from retrieved policy sections with citations."

    top = retrieval["results"][0] if retrieval["results"] else None
    result = {
        "status": "success",
        "domain": DOMAIN,
        "query": query,
        "answer": answer,
        "citations": citations,
        "confidence_category": confidence,
        "retrieval_summary": {
            "retrieved_count": len(retrieval["results"]),
            "evidence_count": len(evidence),
            "top_chunk": top["chunk_id"] if top else None,
            "top_similarity": top["similarity"] if top else None,
            "min_similarity": MIN_SIMILARITY,
        },
        "agentic_workflow": {
            "plan": "Find the scheduling policy sections relevant to the question.",
            "act": f"Embedded the question with {OLLAMA_EMBED_MODEL} and ranked {len(_INDEX['chunks'])} policy sections by cosine similarity.",
            "observe": {
                "evidence_count": len(evidence),
                "confidence_category": confidence,
                "citation_chunk_ids": [c["chunk_id"] for c in citations],
            },
            "adapt": adapt,
        },
    }
    _audit("answer_question", {"query": query, "k": k, "caller": caller}, "success", started,
           {"confidence_category": confidence, "citation_chunk_ids": [c["chunk_id"] for c in citations]})
    return result
