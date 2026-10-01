from flask import Blueprint, jsonify, request

from services.rag_api import (
    answer_student_question,
    refresh_student_rag,
    retrieve_student_context,
)


rag_bp = Blueprint("rag_mode", __name__)


@rag_bp.post("/rag/refresh")
def rag_refresh():
    try:
        result = refresh_student_rag()
        return jsonify(result), 200 if result.get("status") == "success" else 503
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503


@rag_bp.post("/rag/retrieve")
def rag_retrieve():
    query = request.form.get("query", "").strip()
    if not query:
        return jsonify({"status": "error", "error": "query is required"}), 400

    k = int(request.form.get("k", 5))

    try:
        result = retrieve_student_context(query, k)
        return jsonify(result), 200 if result.get("status") == "success" else 503
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503


@rag_bp.post("/rag/answer")
def rag_answer():
    query = request.form.get("query", "").strip()
    if not query:
        return jsonify({"status": "error", "error": "query is required"}), 400

    k = int(request.form.get("k", 5))

    try:
        result = answer_student_question(query, k)
        return jsonify(result), 200 if result.get("status") == "success" else 503
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503
