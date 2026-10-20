import os

import requests

MULTI_AGENT_SERVICE_URL = os.getenv("MULTI_AGENT_SERVICE_URL", "http://localhost:5004").rstrip("/")
MULTI_AGENT_ENABLED = os.getenv("MULTI_AGENT_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
MULTI_AGENT_TIMEOUT = float(os.getenv("MULTI_AGENT_TIMEOUT_SECONDS", "240"))  # three model calls in sequence
DOMAIN = "assessment"
CALLER = "student5-assessment-service"


class MultiAgentDisabledError(RuntimeError):
    """Raised when MULTI_AGENT_ENABLED is false (CI and the baseline cloud deployment)."""


def _check():
    if not MULTI_AGENT_ENABLED:
        raise MultiAgentDisabledError("Multi-Agent is disabled (MULTI_AGENT_ENABLED=false)")


def _json(response):
    try:
        return response.json(), response.status_code
    except ValueError:
        response.raise_for_status()
        raise


def health():
    _check()
    return _json(requests.get(f"{MULTI_AGENT_SERVICE_URL}/health", timeout=5))


def run_workflow(user_request: str):
    _check()
    return _json(requests.post(
        f"{MULTI_AGENT_SERVICE_URL}/workflow",
        json={"user_request": user_request, "domain": DOMAIN, "caller": CALLER},
        timeout=MULTI_AGENT_TIMEOUT,
    ))


def decide(workflow_id: str, payload: dict):
    _check()
    return _json(requests.post(f"{MULTI_AGENT_SERVICE_URL}/workflow/{workflow_id}/decision", json=payload, timeout=15))


def history(limit: int = 10):
    _check()
    return _json(requests.get(f"{MULTI_AGENT_SERVICE_URL}/workflows",
                              params={"domain": DOMAIN, "limit": limit}, timeout=10))
