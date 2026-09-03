from flask import Blueprint, request
import requests

from services.database_api import (
    get_grades,
    get_grade_response,
    create_grade_response,
    update_grade_response,
    delete_grade_response,
    get_grades_by_student_response,
    get_grades_by_course_response,
)
from views.html_formatters import format_grades_html, format_grade_html


grades_bp = Blueprint("grades", __name__)


@grades_bp.get("/grades")
def get_grades_route():
    try:
        grades = get_grades()
        return format_grades_html(grades), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve grades from the database service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@grades_bp.get("/grades/<int:grade_id>")
def get_grade_route(grade_id):
    try:
        response = get_grade_response(grade_id)
        if response.status_code == 404:
            return "<p>Grade not found.</p>", 404
        response.raise_for_status()
        return format_grade_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve grade from the database service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@grades_bp.post("/grades")
def create_grade_route():
    form = request.form
    payload = {
        "assessment_id": form.get("assessment_id", "").strip(),
        "student_id": form.get("student_id", "").strip(),
        "mark": form.get("mark", "").strip(),
        "grade": form.get("grade", "").strip(),
        "feedback": form.get("feedback", "").strip(),
        "date_recorded": form.get("date_recorded", "").strip(),
    }

    if not payload["assessment_id"] or not payload["student_id"] or not payload["date_recorded"]:
        return "<p>Assessment ID, Student ID, and Date Recorded are required.</p>", 400

    try:
        payload["assessment_id"] = int(payload["assessment_id"])
        payload["student_id"] = int(payload["student_id"])
        payload["mark"] = float(payload["mark"]) if payload["mark"] else None
    except ValueError:
        return "<p>Assessment ID, Student ID, and Mark must be numeric.</p>", 400

    try:
        response = create_grade_response(payload)
        if response.status_code == 400:
            return f"<p>{response.json().get('error', 'Invalid request')}</p>", 400
        response.raise_for_status()
        grades = get_grades()
        return format_grades_html(grades), 201
    except requests.RequestException as exc:
        return (
            "<p>Failed to record grade.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@grades_bp.put("/grades/<int:grade_id>")
def update_grade_route(grade_id):
    form = request.form
    payload = {k: v for k, v in {
        "assessment_id": form.get("assessment_id"),
        "student_id": form.get("student_id"),
        "mark": form.get("mark"),
        "grade": form.get("grade"),
        "feedback": form.get("feedback"),
        "date_recorded": form.get("date_recorded"),
    }.items() if v not in (None, "")}

    try:
        response = update_grade_response(grade_id, payload)
        if response.status_code == 404:
            return "<p>Grade not found.</p>", 404
        response.raise_for_status()
        grades = get_grades()
        return format_grades_html(grades), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to update grade.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@grades_bp.delete("/grades/<int:grade_id>")
def delete_grade_route(grade_id):
    try:
        response = delete_grade_response(grade_id)
        if response.status_code == 404:
            return "<p>Grade not found.</p>", 404
        response.raise_for_status()
        grades = get_grades()
        return format_grades_html(grades), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to delete grade.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@grades_bp.get("/grades/student/<int:student_id>")
def get_grades_by_student_route(student_id):
    try:
        response = get_grades_by_student_response(student_id)
        if response.status_code == 404:
            return f"<p>No grades found for student {student_id}.</p>", 404
        response.raise_for_status()
        return format_grades_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve grades for student.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@grades_bp.get("/grades/course/<course_id>")
def get_grades_by_course_route(course_id):
    try:
        response = get_grades_by_course_response(course_id)
        if response.status_code == 404:
            return f"<p>No grades found for course {course_id}.</p>", 404
        response.raise_for_status()
        return format_grades_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve grades for course.</p>"
            f"<pre>{exc}</pre>",
            503,
        )
