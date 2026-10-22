import os

import requests


MULTI_AGENT_SERVICE_URL = os.getenv(
    "MULTI_AGENT_SERVICE_URL",
    "http://localhost:5004"
).rstrip("/")

MULTI_AGENT_ENABLED = os.getenv(
    "MULTI_AGENT_ENABLED",
    "true"
).strip().lower() in {"1", "true", "yes", "on"}

# Planner -> Worker -> Reviewer run as three sequential model calls.
MULTI_AGENT_TIMEOUT = float(os.getenv("MULTI_AGENT_TIMEOUT_SECONDS", "240"))

DOMAIN = "students"
CALLER = "student1"


def _check_enabled():
    if not MULTI_AGENT_ENABLED:
        raise RuntimeError("Multi-Agent Mode is disabled")


def run_student_workflow(question: str):
    """Start a Planner -> Worker -> Reviewer workflow for the student records domain."""
    _check_enabled()

    response = requests.post(
        f"{MULTI_AGENT_SERVICE_URL}/workflow",
        json={"user_request": question, "domain": DOMAIN, "caller": CALLER},
        timeout=MULTI_AGENT_TIMEOUT
    )

    return response.json(), response.status_code


def decide_student_workflow(workflow_id: str, decision: str, reviewer: str, comment: str = "", corrected_output: str = ""):
    """Record the human decision (Accept / Partially Accept / Correct / Reject) for a workflow."""
    _check_enabled()

    response = requests.post(
        f"{MULTI_AGENT_SERVICE_URL}/workflow/{workflow_id}/decision",
        json={
            "decision": decision,
            "reviewer": reviewer,
            "comment": comment,
            "corrected_output": corrected_output,
        },
        timeout=15
    )

    return response.json(), response.status_code


def get_student_workflow(workflow_id: str):
    _check_enabled()

    response = requests.get(
        f"{MULTI_AGENT_SERVICE_URL}/workflow/{workflow_id}",
        timeout=10
    )

    return response.json(), response.status_code


def list_student_workflows(limit: int = 10):
    _check_enabled()

    response = requests.get(
        f"{MULTI_AGENT_SERVICE_URL}/workflows",
        params={"domain": DOMAIN, "limit": limit},
        timeout=10
    )

    return response.json(), response.status_code


def get_workflow_status():
    """Server-wide counts: how many workflows ran, how many are pending human review, etc."""
    _check_enabled()

    response = requests.get(
        f"{MULTI_AGENT_SERVICE_URL}/workflow/status",
        timeout=10
    )

    return response.json(), response.status_code
