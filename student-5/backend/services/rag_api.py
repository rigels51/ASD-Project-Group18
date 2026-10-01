import os

import requests


RAG_SERVER_URL = os.getenv("RAG_SERVER_URL", "http://localhost:5050").rstrip("/")
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
RAG_DOMAIN = "assessment"
RAG_CALLER = "student5-assessment-service"


class RagDisabledError(RuntimeError):
    """Raised when RAG_ENABLED is false (e.g. in CI/CD)."""


def _post(path: str, payload: dict, timeout: int = 150) -> dict:
    if not RAG_ENABLED:
        raise RagDisabledError("RAG is disabled (RAG_ENABLED=false)")
    response = requests.post(
        f"{RAG_SERVER_URL}{path}",
        json={"domain": RAG_DOMAIN, "caller": RAG_CALLER, **payload},
        timeout=timeout,
    )
    try:
        result = response.json()
    except ValueError:
        response.raise_for_status()
        raise
    if not isinstance(result, dict):
        raise ValueError("RAG server returned an invalid response")
    return result


def refresh_assessment_rag() -> dict:
    return _post("/refresh", {}, timeout=60)


def rag_health() -> dict:
    if not RAG_ENABLED:
        raise RagDisabledError("RAG is disabled (RAG_ENABLED=false)")
    response = requests.get(f"{RAG_SERVER_URL}/health", timeout=5)
    response.raise_for_status()
    return response.json()


def ask_assessment_rag(question: str, k: int = 6) -> dict:
    return _post("/answer", {"query": question, "k": k})
