from flask import Blueprint, jsonify, request
import requests

from services.database_api import (
    create_student,
    delete_student,
    get_student_by_id_response,
    get_students,
    get_students_by_subject_response,
    search_students,
    update_student,
)
from views.html_formatters import format_student_html, format_students_html


normal_ui_bp = Blueprint("normal_ui", __name__)


@normal_ui_bp.get("/")
def health():
    return "<p>enrolment-service running</p>", 200


@normal_ui_bp.get("/students")
def get_students_route():
    try:
        return jsonify(get_students()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve students from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.get("/students/search")
def search_students_route():
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify([])
    try:
        return jsonify(search_students(query)), 200
    except requests.RequestException as exc:
        return (f"<pre>{exc}</pre>", 503)


@normal_ui_bp.get("/students/by-id")
def get_student_by_id():
    student_id = request.args.get("student_id", "").strip()

    if not student_id:
        return "<p>Student ID is required.</p>", 400

    try:
        response = get_student_by_id_response(student_id)

        if response.status_code == 404:
            return "<p>Student not found.</p>", 404
        if response.status_code == 400:
            return "<p>Student ID must be valid.</p>", 400

        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve student from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.get("/students/by-subject")
def get_students_by_subject():
    subject_code = request.args.get("subject_code", "").strip()

    if not subject_code:
        return "<p>Subject code is required.</p>", 400

    try:
        response = get_students_by_subject_response(subject_code)

        if response.status_code == 404:
            return f"<p>No students found for {subject_code}.</p>", 404

        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve subject results from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.post("/students")
def create_student_route():
    payload = request.get_json(silent=True) or {}
    try:
        student = create_student(payload)
        return jsonify(student), 201
    except requests.RequestException as exc:
        return jsonify({"error": str(exc)}), 503


@normal_ui_bp.put("/students/<student_id>")
def update_student_route(student_id):
    payload = request.get_json(silent=True) or {}
    try:
        student = update_student(student_id, payload)
        return jsonify(student), 200
    except requests.RequestException as exc:
        return jsonify({"error": str(exc)}), 503


@normal_ui_bp.delete("/students/<student_id>")
def delete_student_route(student_id):
    try:
        result = delete_student(student_id)
        return jsonify(result), 200
    except requests.RequestException as exc:
        return jsonify({"error": str(exc)}), 503