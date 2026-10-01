from flask import Blueprint, jsonify, request

from services.mcp_api import call_student_tool, list_student_tools


mcp_bp = Blueprint("mcp_mode", __name__)


@mcp_bp.get("/mcp/tools")
def mcp_tools():
    try:
        return jsonify({"status": "success", "tools": list_student_tools()}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503


@mcp_bp.post("/mcp/student-count")
def mcp_student_count():
    try:
        result = call_student_tool("get_student_count")
        return jsonify({"status": "success", "result": result}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503


@mcp_bp.post("/mcp/students")
def mcp_students():
    course = request.form.get("course", "").strip()
    try:
        result = call_student_tool("list_students", {"course": course})
        return jsonify({"status": "success", "result": result}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503


@mcp_bp.post("/mcp/student")
def mcp_student():
    student_id = request.form.get("student_id", "").strip()
    if not student_id:
        return jsonify({"status": "error", "error": "student_id is required"}), 400
    try:
        result = call_student_tool("get_student", {"student_id": student_id})
        return jsonify({"status": "success", "result": result}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503


@mcp_bp.post("/mcp/students-by-status")
def mcp_students_by_status():
    status = request.form.get("status", "").strip()
    try:
        result = call_student_tool("list_students_by_status", {"status": status})
        return jsonify({"status": "success", "result": result}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 503
