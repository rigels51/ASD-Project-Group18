"""Shared Ollama client for the three agents.

Every call returns (text, error). Agents never raise on a model failure: they fall
back to a deterministic answer so the workflow, its audit log and the human review
step still complete when Ollama is down or slow.
"""

import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")              # planner + worker
OLLAMA_REVIEW_MODEL = os.getenv("OLLAMA_REVIEW_MODEL", "llama3.1:8b")  # reviewer
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))
LLM_ENABLED = os.getenv("MULTI_AGENT_LLM_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", timeout=OLLAMA_TIMEOUT_SECONDS)
    return _client


def chat(model: str, system: str, user: str, max_tokens: int = 220) -> tuple[str | None, str | None]:
    if not LLM_ENABLED:
        return None, "LLM disabled (MULTI_AGENT_LLM_ENABLED=false)"
    try:
        response = _get_client().chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        text = (response.choices[0].message.content or "").strip()
        return (text, None) if text else (None, "empty model output")
    except Exception as exc:  # noqa: BLE001 - any model failure becomes a fallback, never a crash
        return None, f"{model} unavailable ({type(exc).__name__}: {exc})"
