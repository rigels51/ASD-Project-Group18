"""ACT step for RAG mode: talk to the shared RAG server and record raw observations."""

import time

import requests


def health(url):
    try:
        response = requests.get(f"{url}/health", timeout=5)
        response.raise_for_status()
        return {"ok": True, **response.json()}
    except (requests.RequestException, ValueError) as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def ask(url, domain, question):
    started = time.monotonic()
    try:
        response = requests.post(
            f"{url}/answer",
            json={"query": question, "domain": domain, "caller": "agentic-loop"},
            timeout=180,
        )
        body = response.json()
        status_code = response.status_code
    except (requests.RequestException, ValueError) as exc:
        body, status_code = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}, None
    return {
        "status_code": status_code,
        "body": body if isinstance(body, dict) else {"status": "error", "error": "non-object response"},
        "latency_ms": round((time.monotonic() - started) * 1000),
    }
