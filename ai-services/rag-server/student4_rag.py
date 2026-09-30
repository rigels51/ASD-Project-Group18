"""Student 4 Course & Enrollment RAG domain."""

import os
import re
from typing import Any

import requests


DOMAIN = "course"

STUDENT4_DATABASE_URL = os.getenv(
    "STUDENT4_DATABASE_URL",
    "http://localhost:5032"
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
    "Insufficient context in the Course & Enrollment "
    "data to answer this question."
)

_INDEX = {
    "chunks": []
}


def _get_json(path: str):
    response = requests.get(
        f"{STUDENT4_DATABASE_URL}{path}",
        timeout=15
    )

    response.raise_for_status()

    return response.json()


def load_chunks() -> list[dict[str, Any]]:
    courses = _get_json("/courses")
    enrolments = _get_json("/enrolments")

    chunks = []

    # Course summary
    chunks.append({
        "chunk_id": "course-summary",
        "source_id": "student4-database:/courses",
        "section": "Course Summary",
        "text": f"There are {len(courses)} courses."
    })

    # Individual courses
    for course in courses:
        chunks.append({
            "chunk_id": f"course-{course.get('course_id')}",
            "source_id": (
                "student4-database:/courses/"
                f"{course.get('course_id')}"
            ),
            "section": (
                f"Course {course.get('course_code')}"
            ),
            "text": (
                f"Course ID {course.get('course_id')}. "
                f"Course code {course.get('course_code')}. "
                f"Course name {course.get('course_name')}. "
                f"Credits {course.get('credits')}. "
                f"Capacity {course.get('capacity')}."
            )
        })

    # Enrolment summary
    chunks.append({
        "chunk_id": "enrolment-summary",
        "source_id": "student4-database:/enrolments",
        "section": "Enrolment Summary",
        "text": (
            f"There are {len(enrolments)} "
            "enrolment records."
        )
    })

    # Individual enrolments
    for enrolment in enrolments:
        chunks.append({
            "chunk_id": (
                "enrolment-"
                f"{enrolment.get('enrolment_id')}"
            ),
            "source_id": (
                "student4-database:/enrolments/"
                f"{enrolment.get('enrolment_id')}"
            ),
            "section": (
                "Enrolment "
                f"{enrolment.get('enrolment_id')}"
            ),
            "text": (
                f"Enrolment ID "
                f"{enrolment.get('enrolment_id')}. "
                f"Student ID "
                f"{enrolment.get('student_id')}. "
                f"Course ID "
                f"{enrolment.get('course_id')}. "
                f"Course code "
                f"{enrolment.get('course_code')}. "
                f"Course name "
                f"{enrolment.get('course_name')}. "
                f"Status "
                f"{enrolment.get('status')}."
            )
        })

    return chunks


def _text_score(
    query: str,
    text: str
) -> float:

    query_tokens = re.findall(
        r"[a-z0-9]+",
        query.lower()
    )

    text_lower = text.lower()

    if not query_tokens:
        return 0.0

    matches = sum(
        1
        for token in query_tokens
        if token in text_lower
    )

    score = (
        matches / len(query_tokens)
    ) * 0.6

    # Strong bonus for exact course codes
    # Examples: ASD101, WEB201, DBS101
    for token in query_tokens:
        if (
            re.fullmatch(
                r"[a-z]{2,}\d+",
                token
            )
            and token in text_lower
        ):
            score += 0.8

    return min(
        score,
        1.0
    )


def refresh_corpus(
    caller: str = "student"
) -> dict[str, Any]:

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
        return {
            "status": "error",
            "error": str(exc)
        }


def retrieve_context(
    query: str,
    k: int = 5,
    caller: str = "student"
) -> dict[str, Any]:

    query = (
        query or ""
    ).strip()

    if not query:
        return {
            "status": "error",
            "error": "query is required"
        }

    if not _INDEX["chunks"]:
        result = refresh_corpus(
            caller="auto_refresh"
        )

        if (
            result.get("status")
            != "success"
        ):
            return result

    results = []

    for chunk in _INDEX["chunks"]:

        similarity = _text_score(
            query,
            chunk["text"]
        )

        results.append({
            **chunk,
            "similarity": round(
                similarity,
                4
            )
        })

    results.sort(
        key=lambda row:
            row["similarity"],
        reverse=True
    )

    top_results = results[
        :min(k, MAX_RESULTS)
    ]

    for index, row in enumerate(
        top_results,
        start=1
    ):
        row["rank"] = index

    return {
        "status": "success",
        "domain": DOMAIN,
        "query": query,
        "caller": caller,
        "results": top_results
    }


def _confidence(
    results: list[dict[str, Any]]
) -> str:

    if not results:
        return "low"

    top_similarity = (
        results[0]
        .get(
            "similarity",
            0
        )
    )

    if (
        top_similarity
        >= HIGH_SIMILARITY
    ):
        return "high"

    if (
        top_similarity
        >= MIN_SIMILARITY
    ):
        return "medium"

    return "low"


def _generate_answer(
    query: str,
    evidence: list[dict[str, Any]]
) -> str:

    # -------------------------------------------------
    # Exact course-code question
    # Example:
    # What is ASD101?
    # -------------------------------------------------
    course_match = re.search(
        r"\b[A-Za-z]{2,}\d+\b",
        query
    )

    if course_match:
        course_code = (
            course_match
            .group()
            .upper()
        )

        for row in evidence:
            text = row.get(
                "text",
                ""
            )

            chunk_id = row.get(
                "chunk_id",
                ""
            )

            if (
                chunk_id.startswith("course-")
                and
                f"Course code {course_code}."
                in text
            ):
                return (
                    f"{text} "
                    f"[{chunk_id}]"
                )

    # -------------------------------------------------
    # Other questions use Ollama,
    # but only with retrieved evidence.
    # -------------------------------------------------
    context = "\n".join(
        f"[{row['chunk_id']}] {row['text']}"
        for row in evidence
    )

    prompt = f"""
Answer the question using ONLY the evidence below.

Strict rules:
- Do not use outside knowledge.
- Do not guess.
- Do not invent any information.
- Do not add a university, country, school,
  department or organisation unless it appears
  in the evidence.
- Every factual statement must come from
  the evidence.
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
            "options": {
                "temperature": 0,
                "num_predict": 120
            }
        },
        timeout=120
    )

    response.raise_for_status()

    return (
        response.json()
        .get(
            "response",
            ""
        )
        .strip()
        or INSUFFICIENT
    )


def answer_question(
    query: str,
    k: int = 5,
    caller: str = "student"
) -> dict[str, Any]:

    retrieval = retrieve_context(
        query=query,
        k=k,
        caller=caller
    )

    if (
        retrieval.get("status")
        != "success"
    ):
        return retrieval

    results = retrieval.get(
        "results",
        []
    )

    confidence = _confidence(
        results
    )

    evidence = [
        result
        for result in results
        if result.get(
            "similarity",
            0
        ) >= MIN_SIMILARITY
    ]

    if (
        confidence == "low"
        or not evidence
    ):
        return {
            "status": "success",
            "domain": DOMAIN,
            "query": query,
            "answer": INSUFFICIENT,
            "citations": [],
            "confidence_category": "low"
        }

    try:
        answer = _generate_answer(
            query,
            evidence
        )

    except requests.RequestException as exc:
        return {
            "status": "error",
            "error": (
                f"Ollama request failed: {exc}"
            )
        }

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
            "top_chunk": (
                results[0]["chunk_id"]
                if results
                else None
            )
        }
    }