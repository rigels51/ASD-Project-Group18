import os
import requests


RAG_SERVER_URL = os.getenv(
    "RAG_SERVER_URL",
    "http://localhost:5050"
).rstrip("/")

RAG_ENABLED = os.getenv(
    "RAG_ENABLED",
    "true"
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on"
}


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


def refresh_course_rag():
    return _post(
        "/refresh",
        {
            "domain": "course",
            "caller": "student4"
        }
    )


def retrieve_course_context(
    query: str,
    k: int = 5
):
    return _post(
        "/retrieve",
        {
            "domain": "course",
            "query": query,
            "k": k,
            "caller": "student4"
        }
    )


def answer_course_question(
    query: str,
    k: int = 5
):
    return _post(
        "/answer",
        {
            "domain": "course",
            "query": query,
            "k": k,
            "caller": "student4"
        }
    )