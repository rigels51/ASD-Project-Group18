from flask import Blueprint, jsonify, request

from services.multi_agent_api import (
    decide_student_workflow,
    get_student_workflow,
    get_workflow_status,
    list_student_workflows,
    run_student_workflow,
)


multi_agent_bp = Blueprint("multi_agent_mode", __name__)


@multi_agent_bp.post("/multi-agent/run")
def multi_agent_run():
    question = request.form.get("question", "").strip()
    if not question:
        return jsonify({"status": "error", "error": "question is required"}), 400
    if len(question) > 500:
        return jsonify({"status": "error", "error": "question must be 500 characters or fewer"}), 400

    try:
        result, status_code = run_student_workflow(question)
        return jsonify(result), status_code
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503


@multi_agent_bp.post("/multi-agent/decision")
def multi_agent_decision():
    workflow_id = request.form.get("workflow_id", "").strip()
    decision = request.form.get("decision", "").strip()
    reviewer = request.form.get("reviewer", "").strip() or "student1-chat"
    comment = request.form.get("comment", "").strip()
    corrected_output = request.form.get("corrected_output", "").strip()

    if not workflow_id:
        return jsonify({"status": "error", "error": "workflow_id is required"}), 400
    if not decision:
        return jsonify({"status": "error", "error": "decision is required"}), 400

    try:
        result, status_code = decide_student_workflow(workflow_id, decision, reviewer, comment, corrected_output)
        return jsonify(result), status_code
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503


@multi_agent_bp.get("/multi-agent/workflow/<workflow_id>")
def multi_agent_workflow(workflow_id):
    try:
        result, status_code = get_student_workflow(workflow_id)
        return jsonify(result), status_code
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503


@multi_agent_bp.get("/multi-agent/history")
def multi_agent_history():
    try:
        result, status_code = list_student_workflows()
        return jsonify(result), status_code
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503


@multi_agent_bp.get("/multi-agent/status")
def multi_agent_status():
    try:
        result, status_code = get_workflow_status()
        return jsonify(result), status_code
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503
