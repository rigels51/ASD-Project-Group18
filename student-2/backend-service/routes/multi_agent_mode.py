import os
from urllib.parse import quote

import requests
from flask import Blueprint, jsonify, request


DOMAIN = "staff"
CALLER = "staff-backend"
MULTI_AGENT_SERVICE_URL = os.getenv(
    "MULTI_AGENT_SERVICE_URL", "http://localhost:5004"
).rstrip("/")
MULTI_AGENT_ENABLED = (
    os.getenv("MULTI_AGENT_ENABLED", "true").strip().lower()
    in {"1", "true", "yes", "on"}
)
MULTI_AGENT_TIMEOUT_SECONDS = float(
    os.getenv("MULTI_AGENT_TIMEOUT_SECONDS", "240")
)

multi_agent_bp = Blueprint("multi_agent_mode", __name__)


def _request_data() -> dict:
    data = request.get_json(silent=True) if request.is_json else request.form
    if isinstance(data, dict):
        return data
    return dict(data) if data is not None else {}


def _proxy(method: str, path: str, timeout: float, **kwargs):
    if not MULTI_AGENT_ENABLED:
        return (
            jsonify({
                "status": "disabled",
                "error": "Multi-Agent is disabled (MULTI_AGENT_ENABLED=false)",
            }),
            503,
        )

    try:
        response = requests.request(
            method,
            f"{MULTI_AGENT_SERVICE_URL}{path}",
            timeout=timeout,
            **kwargs,
        )
    except requests.RequestException:
        return (
            jsonify({
                "status": "error",
                "error": (
                    "Shared Multi-Agent server is unavailable at "
                    f"{MULTI_AGENT_SERVICE_URL}"
                ),
            }),
            503,
        )

    try:
        payload = response.json()
    except ValueError:
        return (
            jsonify({
                "status": "error",
                "error": "Multi-Agent server returned an invalid response",
            }),
            502,
        )

    if not isinstance(payload, dict):
        return (
            jsonify({
                "status": "error",
                "error": "Multi-Agent server returned an invalid response",
            }),
            502,
        )
    return jsonify(payload), response.status_code


@multi_agent_bp.get("/multi-agent/health")
def multi_agent_health():
    return _proxy("GET", "/health", timeout=5)


@multi_agent_bp.post("/multi-agent/run")
def run_multi_agent_workflow():
    question = _request_data().get("question", "")
    if not isinstance(question, str):
        return jsonify({"status": "error", "error": "question must be text"}), 400
    question = question.strip()
    if not question or len(question) > 500:
        return (
            jsonify({
                "status": "error",
                "error": "question must contain 1 to 500 characters",
            }),
            400,
        )

    return _proxy(
        "POST",
        "/workflow",
        timeout=MULTI_AGENT_TIMEOUT_SECONDS,
        json={"user_request": question, "domain": DOMAIN, "caller": CALLER},
    )


@multi_agent_bp.post("/multi-agent/decision")
def record_multi_agent_decision():
    data = _request_data()
    workflow_id = data.get("workflow_id", "")
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        return jsonify({"status": "error", "error": "workflow_id is required"}), 400

    payload = {
        key: data.get(key, "")
        for key in ("decision", "reviewer", "comment", "corrected_output")
    }
    return _proxy(
        "POST",
        f"/workflow/{quote(workflow_id.strip(), safe='')}/decision",
        timeout=15,
        json=payload,
    )


@multi_agent_bp.get("/multi-agent/workflow/<workflow_id>")
def get_multi_agent_workflow(workflow_id):
    return _proxy(
        "GET",
        f"/workflow/{quote(workflow_id, safe='')}",
        timeout=10,
    )


@multi_agent_bp.get("/multi-agent/history")
def list_multi_agent_history():
    return _proxy(
        "GET",
        "/workflows",
        timeout=10,
        params={"domain": DOMAIN, "limit": 10},
    )
