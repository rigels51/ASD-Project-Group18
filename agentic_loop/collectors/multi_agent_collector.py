import time
from pathlib import Path

import requests

SERVER_DIR = Path(__file__).resolve().parents[2] / "ai-services" / "multi-agent-server"
REQUIRED_FILES = [
    "app.py", "coordinator.py", "evidence.py", "llm.py", "workflow_runner.py", "requirements.txt",
    "agents/planner_agent.py", "agents/worker_agent.py", "agents/reviewer_agent.py",
    "prompts/planner_prompt.txt", "prompts/worker_prompt.txt", "prompts/reviewer_prompt.txt",
]
REQUIRED_CALLS = ["plan_workflow", "generate_output", "review_output", "record_decision"]


def structure():
    """Static check: required files exist and the coordinator wires every agent + human step."""
    missing = [f for f in REQUIRED_FILES if not (SERVER_DIR / f).exists()]
    coordinator = SERVER_DIR / "coordinator.py"
    text = coordinator.read_text(encoding="utf-8") if coordinator.exists() else ""
    return {"missing_files": missing, "missing_calls": [c for c in REQUIRED_CALLS if c not in text]}


def health(url):
    try:
        response = requests.get(f"{url}/health", timeout=5)
        response.raise_for_status()
        return {"ok": True, **response.json()}
    except (requests.RequestException, ValueError) as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def run_workflow(url, domain, user_request):
    started = time.monotonic()
    try:
        response = requests.post(f"{url}/workflow", json={"user_request": user_request, "domain": domain,
                                                          "caller": "agentic-loop"}, timeout=300)
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        body = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    body["latency_ms"] = round((time.monotonic() - started) * 1000)
    return body


def status(url):
    try:
        response = requests.get(f"{url}/workflow/status", timeout=10)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
