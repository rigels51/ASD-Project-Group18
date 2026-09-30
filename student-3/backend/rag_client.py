"""Client for the shared RAG server, using the timetable knowledge domain."""

import os

import requests


RAG_SERVER_URL = os.getenv("RAG_SERVER_URL", "http://localhost:5050").rstrip("/")
RAG_DOMAIN = "timetable"
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def ask_rag(question: str, k: int = 3) -> tuple[dict, int]:
    """Return the RAG server's JSON body and HTTP status (errors are passed through)."""
    response = requests.post(
        f"{RAG_SERVER_URL}/answer",
        json={"query": question, "k": k, "domain": RAG_DOMAIN, "caller": "timetable-backend"},
        timeout=150,
    )
    try:
        result = response.json()
    except ValueError:
        response.raise_for_status()
        raise
    if not isinstance(result, dict):
        raise ValueError("RAG server returned an invalid response")
    return result, response.status_code
