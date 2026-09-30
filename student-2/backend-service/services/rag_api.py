import os

import requests


RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://student2-rag:5003").rstrip("/")
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def rag_mode_is_enabled(req) -> bool:
    if not RAG_ENABLED:
        return False
    mode_header = req.headers.get("X-RAG-Mode", "on").strip().lower()
    return mode_header in {"1", "true", "yes", "on"}


def call_rag_service(path: str, payload: dict):
    response = requests.post(f"{RAG_SERVICE_URL}{path}", json=payload, timeout=150)
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise ValueError("RAG service returned an invalid response")
    return result