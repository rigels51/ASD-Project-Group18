import os

import requests


RAG_SERVER_URL = os.getenv(
    "RAG_SERVER_URL",
    "http://localhost:5050"
).rstrip("/")

RAG_ENABLED = os.getenv(
    "RAG_ENABLED",
    "true"
).strip().lower() in {"1", "true", "yes", "on"}


def _post(path: str, payload: dict):
    if not RAG_ENABLED:
        raise RuntimeError("RAG Mode is disabled")

    response = requests.post(
        f"{RAG_SERVER_URL}{path}",
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    return response.json()


def refresh_student_rag():
    return _post("/refresh", {"domain": "students", "caller": "student1"})


def retrieve_student_context(query: str, k: int = 5):
    return _post("/retrieve", {"domain": "students", "query": query, "k": k, "caller": "student1"})


def answer_student_question(query: str, k: int = 5):
    return _post("/answer", {"domain": "students", "query": query, "k": k, "caller": "student1"})
