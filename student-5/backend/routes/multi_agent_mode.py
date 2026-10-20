import time

import requests
from flask import Blueprint, jsonify, request

from services import multi_agent_api
from views.mcp_rag_formatters import format_message_html
from views.multi_agent_formatters import format_history_html, format_workflow_html

multi_agent_bp = Blueprint("assessment_multi_agent_mode", __name__)


def _wants_json() -> bool:
    return request.args.get("format") == "json" or request.is_json


def _respond(status: int, payload: dict, html: str):
    return (jsonify(payload), status) if _wants_json() else (html, status)


def _data() -> dict:
    data = request.get_json(silent=True) if request.is_json else request.form
    return {k: str(v).strip() for k, v in (data or {}).items()}


def _disabled():
    msg = "Multi-Agent is disabled (MULTI_AGENT_ENABLED=false)"
    return _respond(503, {"status": "disabled", "error": msg}, format_message_html("disabled", "Multi-Agent disabled", msg))


def _unreachable():
    msg = f"Shared Multi-Agent server unavailable at {multi_agent_api.MULTI_AGENT_SERVICE_URL}"
    return _respond(503, {"status": "error", "error": msg},
                    format_message_html("error", "Multi-Agent server unreachable", msg))


def _call(fn, *args):
    """Run a service call; returns (result, error_response)."""
    if not multi_agent_api.MULTI_AGENT_ENABLED:
        return None, _disabled()
    try:
        return fn(*args), None
    except requests.RequestException:
        return None, _unreachable()


@multi_agent_bp.get("/multi-agent/health")
def ma_health():
    result, err = _call(multi_agent_api.health)
    if err:
        return err
    body, status = result
    return _respond(status, body, format_message_html(
        "ok", "Multi-Agent server reachable",
        f"{multi_agent_api.MULTI_AGENT_SERVICE_URL} · agents: {', '.join(body.get('agents', []))}"))


@multi_agent_bp.post("/multi-agent/run")
def ma_run():
    question = _data().get("question", "")
    if not question:
        return _respond(400, {"status": "error", "error": "question is required"},
                        format_message_html("rejected", "Request required", "Describe the task first."))
    if len(question) > 500:
        return _respond(400, {"status": "error", "error": "question must be 500 characters or fewer"},
                        format_message_html("rejected", "Request too long", "Keep it under 500 characters."))
    started = time.monotonic()
    result, err = _call(multi_agent_api.run_workflow, question)
    if err:
        return err
    body, status = result
    if status >= 400 and body.get("status") == "error":
        return _respond(status, body, format_message_html("rejected", "Workflow not started", body.get("error", "")))
    return _respond(status, body, format_workflow_html(body, round((time.monotonic() - started) * 1000)))


@multi_agent_bp.post("/multi-agent/decision")
def ma_decision():
    data = _data()
    workflow_id = data.pop("workflow_id", "")
    if not workflow_id:
        return _respond(400, {"status": "error", "error": "workflow_id is required"},
                        format_message_html("rejected", "Missing workflow", "workflow_id is required."))
    payload = {k: data.get(k, "") for k in ("decision", "reviewer", "comment", "corrected_output")}
    result, err = _call(multi_agent_api.decide, workflow_id, payload)
    if err:
        return err
    body, status = result
    if status != 200:
        return _respond(status, body, format_message_html("rejected", "Decision not recorded", body.get("error", "")))
    return _respond(200, body, format_workflow_html(body))


@multi_agent_bp.get("/multi-agent/history")
def ma_history():
    result, err = _call(multi_agent_api.history, 10)
    if err:
        return err
    body, status = result
    return _respond(status, body, format_history_html(body.get("workflows", [])))


@multi_agent_bp.get("/multi-agent/workflow/<workflow_id>")
def ma_get(workflow_id):
    def fetch(wid):
        r = requests.get(f"{multi_agent_api.MULTI_AGENT_SERVICE_URL}/workflow/{wid}", timeout=10)
        return r.json(), r.status_code
    result, err = _call(fetch, workflow_id)
    if err:
        return err
    body, status = result
    if status != 200:
        return _respond(status, body, format_message_html("rejected", "Not found", body.get("error", "")))
    return _respond(200, body, format_workflow_html(body))
