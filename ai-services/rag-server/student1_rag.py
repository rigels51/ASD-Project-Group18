"""Student 1 Student Records RAG"""

import os
import re
from pathlib import Path
from typing import Any

import requests


DOMAIN = "students"
BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATH = BASE_DIR / "chroma"

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

OLLAMA_EMBED_MODEL = os.getenv(
    "OLLAMA_EMBED_MODEL",
    "nomic-embed-text"
)

COLLECTION_NAME = "student1_students_context"
MAX_RESULTS = 5

# Chroma cosine distance thresholds (lower = more relevant).
MAX_EVIDENCE_DISTANCE = 0.50
HIGH_CONFIDENCE_DISTANCE = 0.30

INSUFFICIENT = (
    "Insufficient context in the Student Records "
    "data to answer this question."
)

# Used only by the lexical fallback path if ChromaDB/Ollama embeddings are unavailable.
STOPWORDS = {
    "a", "about", "after", "all", "am", "an", "and", "any", "are", "as", "at", "be", "been",
    "being", "by", "can", "could", "currently", "did", "do", "does", "for", "from", "get",
    "give", "had", "has", "have", "how", "i", "if", "in", "into", "is", "it", "its", "me",
    "much", "my", "of", "on", "or", "our", "please", "record", "show", "so", "student",
    "students", "tell", "than", "that", "the", "their", "them", "then", "there", "these",
    "they", "this", "those", "to", "up", "us", "was", "we", "were", "what", "when", "where",
    "which", "who", "why", "will", "with", "would", "you", "your",
}

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

    # tier_2: a derived/aggregate fact, not a primary database record.
    chunks.append({
        "chunk_id": "student-summary",
        "source_id": "student1-database:/students",
        "section": "Student Summary",
        "authority_tier": "tier_2",
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
            # tier_1: a primary record pulled directly from the database.
            "authority_tier": "tier_1",
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


def _embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

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


def _get_collection():
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _text_score(query: str, text: str) -> float:
    """Keyword-overlap fallback scorer, used only if ChromaDB/embeddings fail."""
    query_tokens = [
        token for token in re.findall(r"[a-z0-9]+", query.lower())
        if token not in STOPWORDS
    ]
    text_tokens = set(re.findall(r"[a-z0-9]+", text.lower()))

    if not query_tokens:
        return 0.0

    matches = sum(1 for token in query_tokens if token in text_tokens)
    score = (matches / len(query_tokens)) * 0.6

    text_lower = text.lower()
    for token in query_tokens:
        if re.fullmatch(r"stu\d+", token) and token in text_lower.replace("-", ""):
            score += 0.8

    return min(score, 1.0)


def refresh_corpus(caller: str = "student") -> dict[str, Any]:
    try:
        chunks = load_chunks()
        _INDEX["chunks"] = chunks

        vector_store_status = "ready"
        vector_store_error = None

        try:
            collection = _get_collection()
            existing = collection.get(include=[])
            existing_ids = existing.get("ids", [])
            if existing_ids:
                collection.delete(ids=existing_ids)

            if chunks:
                embeddings = _embed_texts([chunk["text"] for chunk in chunks])
                collection.add(
                    ids=[chunk["chunk_id"] for chunk in chunks],
                    documents=[chunk["text"] for chunk in chunks],
                    metadatas=[
                        {
                            "source_id": chunk["source_id"],
                            "section": chunk["section"],
                            "authority_tier": chunk["authority_tier"],
                        }
                        for chunk in chunks
                    ],
                    embeddings=embeddings,
                )
        except Exception as exc:
            vector_store_status = "degraded"
            vector_store_error = str(exc)

        output = {
            "status": "success",
            "domain": DOMAIN,
            "caller": caller,
            "chunk_count": len(chunks),
            "collection": COLLECTION_NAME,
            "vector_store_status": vector_store_status,
        }
        if vector_store_error:
            output["vector_store_error"] = vector_store_error

        return output
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _lexical_fallback_retrieve(query: str, k: int) -> list[dict[str, Any]]:
    tier_weight = {"tier_1": 2, "tier_2": 1}
    scored = []

    for chunk in _INDEX["chunks"]:
        score = _text_score(query, chunk["text"])
        scored.append({**chunk, "_score": score})

    scored.sort(
        key=lambda row: (tier_weight.get(row.get("authority_tier"), 0), row["_score"]),
        reverse=True,
    )

    top = scored[:min(k, MAX_RESULTS)]
    ranked = []
    for index, row in enumerate(top, start=1):
        ranked.append({
            "rank": index,
            "chunk_id": row["chunk_id"],
            "source_id": row["source_id"],
            "section": row["section"],
            "authority_tier": row["authority_tier"],
            # Pseudo-distance so it's comparable to vector mode (lower = better).
            "distance": round(1 - row["_score"], 4),
            "text": row["text"],
        })
    return ranked


def retrieve_context(
    query: str,
    k: int = 5,
    caller: str = "student"
) -> dict[str, Any]:
    query = (query or "").strip()

    if not query:
        return {"status": "error", "error": "query is required"}

    # Always rebuild from the live database so newly added/edited students
    # (e.g. via the Normal UI) show up immediately, without a manual refresh.
    refreshed = refresh_corpus(caller="auto_refresh")
    if refreshed.get("status") != "success":
        return refreshed

    retrieval_mode = "vector"
    ranked: list[dict[str, Any]] = []

    try:
        collection = _get_collection()
        if collection.count() == 0:
            raise RuntimeError("empty_collection")

        query_embedding = _embed_texts([query])
        results = collection.query(query_embeddings=query_embedding, n_results=min(k, MAX_RESULTS))

        ids = (results.get("ids") or [[]])[0]
        docs = (results.get("documents") or [[]])[0]
        metas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        for index, chunk_id in enumerate(ids):
            meta = metas[index] if index < len(metas) and isinstance(metas[index], dict) else {}
            ranked.append({
                "rank": index + 1,
                "chunk_id": chunk_id,
                "source_id": meta.get("source_id"),
                "section": meta.get("section"),
                "authority_tier": meta.get("authority_tier"),
                "distance": distances[index] if index < len(distances) else None,
                "text": docs[index] if index < len(docs) else "",
            })
    except Exception:
        retrieval_mode = "lexical_fallback"
        ranked = _lexical_fallback_retrieve(query, k)

    return {
        "status": "success",
        "domain": DOMAIN,
        "query": query,
        "caller": caller,
        "retrieval_mode": retrieval_mode,
        "results": ranked,
    }


def _confidence(results: list[dict[str, Any]]) -> str:
    distances = [
        row["distance"]
        for row in results
        if isinstance(row.get("distance"), (int, float))
    ]
    reliable = [distance for distance in distances if distance <= MAX_EVIDENCE_DISTANCE]

    if not reliable:
        return "low"

    if len(reliable) >= 2 and max(reliable) <= HIGH_CONFIDENCE_DISTANCE:
        return "high"

    return "medium"


def _generate_answer(query: str, evidence: list[dict[str, Any]]) -> str:
    # Exact student-ID question, e.g. "Who is STU-1001?"
    student_match = re.search(r"\bstu-?\s*\d+\b", query, re.IGNORECASE)

    if student_match:
        student_id = "STU-" + re.sub(r"\D", "", student_match.group())

        for row in evidence:
            if row.get("chunk_id") == f"student-{student_id}":
                return f"{row['text']} [{row['chunk_id']}]"

    # Multiple matching student records: list every one directly instead of
    # relying on the small LLM, which tends to under-report multi-item answers.
    student_rows = [row for row in evidence if row.get("chunk_id") != "student-summary"]
    if len(student_rows) > 1:
        lines = [f"- {row['text']} [{row['chunk_id']}]" for row in student_rows]
        return "Answer:\n" + "\n".join(lines)

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

    evidence = [
        row for row in results
        if isinstance(row.get("distance"), (int, float)) and row["distance"] <= MAX_EVIDENCE_DISTANCE
    ]

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
            "authority_tier": row.get("authority_tier"),
            "distance": row["distance"],
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

