
"""Multi-Agent integration for Student 4 - Course & Enrolment Management.

Connects the Student 4 backend to the shared Multi-Agent server.

Routes:
    GET  /multi-agent/health
    POST /multi-agent/run
    POST /multi-agent/decision
    GET  /multi-agent/workflow/<workflow_id>
    GET  /multi-agent/history

Environment:
    MULTI_AGENT_SERVICE_URL (default: http://localhost:5004)
    MULTI_AGENT_ENABLED (default: true)
"""

import os

import requests
from flask import Blueprint, jsonify, request


# Student 4: Course & Enrolment Management
DOMAIN = "course"
CALLER = f"{DOMAIN}-backend"


# Shared Multi-Agent server configuration
MULTI_AGENT_SERVICE_URL = os.getenv(
    "MULTI_AGENT_SERVICE_URL",
    "http://localhost:5004"
).rstrip("/")

MULTI_AGENT_ENABLED = os.getenv(
    "MULTI_AGENT_ENABLED",
    "true"
).strip().lower() in {"1", "true", "yes", "on"}

TIMEOUT = float(
    os.getenv("MULTI_AGENT_TIMEOUT_SECONDS", "240")
)


# Flask Blueprint
multi_agent_bp = Blueprint("multi_agent_mode", __name__)


def _data() -> dict:
    """Read JSON or form data from incoming requests."""
    data = request.get_json(silent=True) if request.is_json else request.form
    return {k: str(v).strip() for k, v in (data or {}).items()}


def _proxy(method: str, path: str, timeout: float, **kwargs):
    """Forward requests to the shared Multi-Agent server."""

    if not MULTI_AGENT_ENABLED:
        return jsonify({
            "status": "disabled",
            "error": "Multi-Agent is disabled (MULTI_AGENT_ENABLED=false)"
        }), 503

    try:
        response = requests.request(
            method,
            f"{MULTI_AGENT_SERVICE_URL}{path}",
            timeout=timeout,
            **kwargs
        )

        return jsonify(response.json()), response.status_code

    except requests.RequestException:
        return jsonify({
            "status": "error",
            "error": (
                "Shared Multi-Agent server unavailable at "
                f"{MULTI_AGENT_SERVICE_URL}"
            )
        }), 503

    except ValueError:
        return jsonify({
            "status": "error",
            "error": "Multi-Agent server returned an invalid response"
        }), 502


# 1. Multi-Agent Health Check
@multi_agent_bp.get("/multi-agent/health")
def ma_health():
    return _proxy(
        "GET",
        "/health",
        timeout=5
    )


# 2. Run Multi-Agent Workflow
@multi_agent_bp.post("/multi-agent/run")
def ma_run():

    question = _data().get("question", "")

    if not question or len(question) > 500:
        return jsonify({
            "status": "error",
            "error": "question must contain 1 to 500 characters"
        }), 400

    return _proxy(
        "POST",
        "/workflow",
        timeout=TIMEOUT,
        json={
            "user_request": question,
            "domain": DOMAIN,
            "caller": CALLER
        }
    )


# 3. Human Review Decision
@multi_agent_bp.post("/multi-agent/decision")
def ma_decision():

    data = _data()
    workflow_id = data.get("workflow_id", "")

    if not workflow_id:
        return jsonify({
            "status": "error",
            "error": "workflow_id is required"
        }), 400

    payload = {
        k: data.get(k, "")
        for k in (
            "decision",
            "reviewer",
            "comment",
            "corrected_output"
        )
    }

    return _proxy(
        "POST",
        f"/workflow/{workflow_id}/decision",
        json=payload,
        timeout=15
    )


# 4. Get Workflow Details
@multi_agent_bp.get("/multi-agent/workflow/<workflow_id>")
def ma_get(workflow_id):

    return _proxy(
        "GET",
        f"/workflow/{workflow_id}",
        timeout=10
    )


# 5. Get Workflow History
@multi_agent_bp.get("/multi-agent/history")
def ma_history():

    return _proxy(
        "GET",
        "/workflows",
        params={
            "domain": DOMAIN,
            "limit": 10
        },
        timeout=10
    )
