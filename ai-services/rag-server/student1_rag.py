"""Student 1 Student Records RAG"""

import os
import re
from typing import Any

import requests


DOMAIN = "students"

STUDENT1_DATABASE_URL = os.getenv(
    "STUDENT1_DATABASE_URL",
    "http://localhost:5002"
).rstrip("/")

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://localhost:11434"
).rstrip("/")

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:0.5b"
)

MAX_RESULTS = 5
MIN_SIMILARITY = 0.18
HIGH_SIMILARITY = 0.35

INSUFFICIENT = (
    "Insufficient context in the Student Records "
    "data to answer this question."
)

_INDEX: dict[str, Any] = {"chunks": []}


def _get_json(path: str):
    response = requests.get(
        f"{STUDENT1_DATABASE_URL}{path}",
        timeout=15
    )

    response.raise_for_status()

    return response.json()


def load_chunks() -> list[dict[str, Any]]:
    students = _get_json("/students")

    chunks = []

    chunks.append({
        "chunk_id": "student-summary",
        "source_id": "student1-database:/students",
        "section": "Student Summary",
        "text": f"There are {len(students)} students on record."
    })

    for student in students:
        chunks.append({
            "chunk_id": f"student-{student.get('student_id')}",
            "source_id": (
                "student1-database:/students/"
                f"{student.get('student_id')}"
            ),
            "section": f"Student {student.get('student_id')}",
            "text": (
                f"Student ID {student.get('student_id')}. "
                f"Name {student.get('name')}. "
                f"Course {student.get('course')}. "
                f"Year level {student.get('year_level')}. "
                f"GPA {student.get('gpa')}. "
                f"Status {student.get('status')}."
            )
        })

    return chunks


def _text_score(query: str, text: str) -> float:
    query_tokens = re.findall(r"[a-z0-9]+", query.lower())
    text_lower = text.lower()

    if not query_tokens:
        return 0.0

    matches = sum(1 for token in query_tokens if token in text_lower)
    score = (matches / len(query_tokens)) * 0.6

    # Strong bonus for exact student IDs, e.g. STU-1001
    for token in query_tokens:
        if re.fullmatch(r"stu\d+", token) and token in text_lower.replace("-", ""):
            score += 0.8

    return min(score, 1.0)


def refresh_corpus(caller: str = "student") -> dict[str, Any]:
    try:
        chunks = load_chunks()
        _INDEX["chunks"] = chunks

        return {
            "status": "success",
            "domain": DOMAIN,
            "caller": caller,
            "chunk_count": len(chunks)
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def retrieve_context(
    query: str,
    k: int = 5,
    caller: str = "student"
) -> dict[str, Any]:
    query = (query or "").strip()

    if not query:
        return {"status": "error", "error": "query is required"}

    if not _INDEX["chunks"]:
        result = refresh_corpus(caller="auto_refresh")
        if result.get("status") != "success":
            return result

    results = []

    for chunk in _INDEX["chunks"]:
        similarity = _text_score(query, chunk["text"])
        results.append({**chunk, "similarity": round(similarity, 4)})

    results.sort(key=lambda row: row["similarity"], reverse=True)

    top_results = results[:min(k, MAX_RESULTS)]

    for index, row in enumerate(top_results, start=1):
        row["rank"] = index

    return {
        "status": "success",
        "domain": DOMAIN,
        "query": query,
        "caller": caller,
        "results": top_results
    }


def _confidence(results: list[dict[str, Any]]) -> str:
    if not results:
        return "low"

    top_similarity = results[0].get("similarity", 0)

    if top_similarity >= HIGH_SIMILARITY:
        return "high"

    if top_similarity >= MIN_SIMILARITY:
        return "medium"

    return "low"


def _generate_answer(query: str, evidence: list[dict[str, Any]]) -> str:
    # Exact student-ID question, e.g. "Who is STU-1001?"
    student_match = re.search(r"\bstu-?\s*\d+\b", query, re.IGNORECASE)

    if student_match:
        student_id = "STU-" + re.sub(r"\D", "", student_match.group())

        for row in evidence:
            if row.get("chunk_id") == f"student-{student_id}":
                return f"{row['text']} [{row['chunk_id']}]"

    # Other questions use Ollama, but only with retrieved evidence.
    context = "\n".join(f"[{row['chunk_id']}] {row['text']}" for row in evidence)

    prompt = f"""
Answer the question using ONLY the evidence below.

Strict rules:
- Do not use outside knowledge.
- Do not guess.
- Do not invent any information.
- Every factual statement must come from the evidence.
- Cite the relevant chunk ID.
- Keep the answer short.
- If the evidence is insufficient, answer exactly:
{INSUFFICIENT}

Question:
{query}

Evidence:
{context}
"""

    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 120}
        },
        timeout=120
    )

    response.raise_for_status()

    return response.json().get("response", "").strip() or INSUFFICIENT


def answer_question(
    query: str,
    k: int = 5,
    caller: str = "student"
) -> dict[str, Any]:
    retrieval = retrieve_context(query=query, k=k, caller=caller)

    if retrieval.get("status") != "success":
        return retrieval

    results = retrieval.get("results", [])
    confidence = _confidence(results)

    evidence = [row for row in results if row.get("similarity", 0) >= MIN_SIMILARITY]

    if confidence == "low" or not evidence:
        return {
            "status": "success",
            "domain": DOMAIN,
            "query": query,
            "answer": INSUFFICIENT,
            "citations": [],
            "confidence_category": "low"
        }

    try:
        answer = _generate_answer(query, evidence)
    except requests.RequestException as exc:
        return {"status": "error", "error": f"Ollama request failed: {exc}"}

    citations = [
        {
            "chunk_id": row["chunk_id"],
            "source_id": row["source_id"],
            "section": row["section"],
            "similarity": row["similarity"]
        }
        for row in evidence
    ]

    return {
        "status": "success",
        "domain": DOMAIN,
        "query": query,
        "answer": answer,
        "citations": citations,
        "confidence_category": confidence,
        "retrieval_summary": {
            "retrieved_count": len(results),
            "evidence_count": len(evidence),
            "top_chunk": results[0]["chunk_id"] if results else None
        }
    }
