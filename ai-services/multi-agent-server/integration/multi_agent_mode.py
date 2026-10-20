import os

import requests
from flask import Blueprint, jsonify, request

DOMAIN = "CHANGE_ME"          # <-- students | staff | timetable | course | assessment
CALLER = f"{DOMAIN}-backend"

MULTI_AGENT_SERVICE_URL = os.getenv("MULTI_AGENT_SERVICE_URL", "http://localhost:5004").rstrip("/")
MULTI_AGENT_ENABLED = os.getenv("MULTI_AGENT_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
TIMEOUT = float(os.getenv("MULTI_AGENT_TIMEOUT_SECONDS", "240"))  # three local model calls in sequence

multi_agent_bp = Blueprint("multi_agent_mode", __name__)


def _data() -> dict:
    data = request.get_json(silent=True) if request.is_json else request.form
    return {k: str(v).strip() for k, v in (data or {}).items()}


def _proxy(method: str, path: str, **kwargs):
    if not MULTI_AGENT_ENABLED:
        return jsonify({"status": "disabled", "error": "Multi-Agent is disabled (MULTI_AGENT_ENABLED=false)"}), 503
    try:
        response = requests.request(method, f"{MULTI_AGENT_SERVICE_URL}{path}", **kwargs)
        return jsonify(response.json()), response.status_code
    except requests.RequestException:
        return jsonify({"status": "error",
                        "error": f"Shared Multi-Agent server unavailable at {MULTI_AGENT_SERVICE_URL}"}), 503
    except ValueError:
        return jsonify({"status": "error", "error": "Multi-Agent server returned an invalid response"}), 502


@multi_agent_bp.get("/multi-agent/health")
def ma_health():
    return _proxy("GET", "/health", timeout=5)


@multi_agent_bp.post("/multi-agent/run")
def ma_run():
    question = _data().get("question", "")
    if not question or len(question) > 500:
        return jsonify({"status": "error", "error": "question must contain 1 to 500 characters"}), 400
    return _proxy("POST", "/workflow", timeout=TIMEOUT,
                  json={"user_request": question, "domain": DOMAIN, "caller": CALLER})


@multi_agent_bp.post("/multi-agent/decision")
def ma_decision():
    data = _data()
    workflow_id = data.get("workflow_id", "")
    if not workflow_id:
        return jsonify({"status": "error", "error": "workflow_id is required"}), 400
    payload = {k: data.get(k, "") for k in ("decision", "reviewer", "comment", "corrected_output")}
    return _proxy("POST", f"/workflow/{workflow_id}/decision", json=payload, timeout=15)


@multi_agent_bp.get("/multi-agent/workflow/<workflow_id>")
def ma_get(workflow_id):
    return _proxy("GET", f"/workflow/{workflow_id}", timeout=10)


@multi_agent_bp.get("/multi-agent/history")
def ma_history():
    return _proxy("GET", "/workflows", params={"domain": DOMAIN, "limit": 10}, timeout=10)
