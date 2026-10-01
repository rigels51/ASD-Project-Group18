import re
import time

from flask import Blueprint, jsonify, request

from services import rag_api
from views.mcp_rag_formatters import (
    format_message_html,
    format_rag_answer_html,
    format_rag_refresh_html,
)


rag_mode_bp = Blueprint("assessment_rag_mode", __name__)

COURSE_CODE = re.compile(r"^[A-Za-z]{2,4}\d{3}$")


def _wants_json() -> bool:
    return request.args.get("format") == "json" or request.is_json


def _respond(status: int, payload: dict, html: str):
    if _wants_json():
        return jsonify(payload), status
    return html, status


def _disabled():
    message = "RAG is disabled (RAG_ENABLED=false)"
    return _respond(503, {"status": "disabled", "error": message},
                    format_message_html("disabled", "RAG disabled", message))


def _unreachable():
    message = f"Shared RAG server unavailable at {rag_api.RAG_SERVER_URL}"
    return _respond(503, {"status": "error", "error": message},
                    format_message_html("error", "RAG server unreachable", message))


def build_question(question: str, course_id: str) -> str:
    """Attach the course picked in the UI so "this course" can be resolved by retrieval."""
    course_id = course_id.strip().upper()
    if course_id and COURSE_CODE.match(course_id) and course_id not in question.upper():
        return f"{question} (course {course_id})"
    return question


@rag_mode_bp.get("/rag/health")
def rag_health():
    if not rag_api.RAG_ENABLED:
        return _disabled()
    try:
        health = rag_api.rag_health()
    except Exception:  # noqa: BLE001
        return _unreachable()
    hosted = rag_api.RAG_DOMAIN in (health.get("domains") or [])
    payload = {"status": "success", "server": rag_api.RAG_SERVER_URL, "domain": rag_api.RAG_DOMAIN,
               "domain_hosted": hosted, "server_health": health}
    html = format_message_html(
        "ok" if hosted else "error",
        "RAG server reachable" if hosted else "Domain not registered",
        f"{rag_api.RAG_SERVER_URL} hosts domains: {', '.join(health.get('domains') or [])}",
    )
    return _respond(200 if hosted else 503, payload, html)


@rag_mode_bp.post("/rag/refresh")
def rag_refresh():
    if not rag_api.RAG_ENABLED:
        return _disabled()
    try:
        result = rag_api.refresh_assessment_rag()
    except Exception:  # noqa: BLE001
        return _unreachable()
    status = 200 if result.get("status") == "success" else 503
    return _respond(status, result, format_rag_refresh_html(result) if status == 200 else
                    format_message_html("error", "Refresh failed", str(result.get("error", ""))))


@rag_mode_bp.post("/rag/ask")
def rag_ask():
    data = request.get_json(silent=True) if request.is_json else request.form
    data = data or {}
    question = str(data.get("question", "")).strip()
    course_id = str(data.get("course_id", "")).strip()

    if not question:
        return _respond(400, {"status": "error", "error": "question is required"},
                        format_message_html("rejected", "Question required", "Type a question first."))
    if len(question) > 500:
        return _respond(400, {"status": "error", "error": "question must be 500 characters or fewer"},
                        format_message_html("rejected", "Question too long", "Keep it under 500 characters."))
    if not rag_api.RAG_ENABLED:
        return _disabled()

    query = build_question(question, course_id)
    try:
        started = time.monotonic()
        result = rag_api.ask_assessment_rag(query)
        elapsed_ms = round((time.monotonic() - started) * 1000)
    except Exception:  # noqa: BLE001
        return _unreachable()

    if result.get("status") != "success":
        message = str(result.get("error") or "RAG request failed")
        return _respond(503, {"status": "error", "error": message},
                        format_message_html("error", "RAG request failed", message))

    return _respond(200, {**result, "sent_query": query, "elapsed_ms": elapsed_ms},
                    format_rag_answer_html(question, result, elapsed_ms))
