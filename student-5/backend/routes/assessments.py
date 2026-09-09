from flask import Blueprint, request
import requests

from services.database_api import (
    get_assessments,
    get_assessment_response,
    create_assessment_response,
    update_assessment_response,
    delete_assessment_response,
    get_all_courses,
)
from views.html_formatters import format_assessments_html, format_assessment_detail_html


assessments_bp = Blueprint("assessments", __name__)


def _enrich_with_courses(assessments):
    """Attach a course_name to each assessment using Student 4's records
    (relationship: Student 4 -> Student 5 via course_id / course_code)."""
    courses = get_all_courses()
    for a in assessments:
        course = courses.get(str(a.get("course_id", "")).upper())
        a["course_name"] = course["course_name"] if course else None
    return assessments


@assessments_bp.get("/assessments")
def get_assessments_route():
    course_id = request.args.get("course_id", "").strip()
    assessment_type = request.args.get("assessment_type", "").strip()
    q = request.args.get("q", "").strip()

    try:
        assessments = get_assessments(course_id=course_id, assessment_type=assessment_type, q=q)
        assessments = _enrich_with_courses(assessments)
        return format_assessments_html(assessments), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve assessments from the database service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@assessments_bp.get("/assessments/<int:assessment_id>")
def get_assessment_route(assessment_id):
    try:
        response = get_assessment_response(assessment_id)
        if response.status_code == 404:
            return "<p>Assessment not found.</p>", 404
        response.raise_for_status()
        assessment = response.json()
        courses = get_all_courses()
        course = courses.get(str(assessment.get("course_id", "")).upper())
        assessment["course_name"] = course["course_name"] if course else None
        return format_assessment_detail_html(assessment), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve assessment from the database service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@assessments_bp.post("/assessments")
def create_assessment_route():
    form = request.form
    payload = {
        "course_id": form.get("course_id", "").strip(),
        "assessment_name": form.get("assessment_name", "").strip(),
        "assessment_type": form.get("assessment_type", "").strip(),
        "description": form.get("description", "").strip(),
        "due_date": form.get("due_date", "").strip(),
        "max_mark": form.get("max_mark", "").strip(),
        "weight": form.get("weight", "").strip(),
    }

    if not all([payload["course_id"], payload["assessment_name"], payload["assessment_type"],
                payload["due_date"], payload["max_mark"], payload["weight"]]):
        return "<p>All fields except description are required.</p>", 400

    try:
        payload["max_mark"] = float(payload["max_mark"])
        payload["weight"] = float(payload["weight"])
    except ValueError:
        return "<p>Max mark and weight must be numbers.</p>", 400

    try:
        response = create_assessment_response(payload)
        response.raise_for_status()
        assessments = _enrich_with_courses(get_assessments())
        return format_assessments_html(assessments), 201
    except requests.RequestException as exc:
        return (
            "<p>Failed to create assessment.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@assessments_bp.put("/assessments/<int:assessment_id>")
def update_assessment_route(assessment_id):
    form = request.form
    payload = {k: v for k, v in {
        "course_id": form.get("course_id"),
        "assessment_name": form.get("assessment_name"),
        "assessment_type": form.get("assessment_type"),
        "description": form.get("description"),
        "due_date": form.get("due_date"),
        "max_mark": form.get("max_mark"),
        "weight": form.get("weight"),
    }.items() if v not in (None, "")}

    try:
        response = update_assessment_response(assessment_id, payload)
        if response.status_code == 404:
            return "<p>Assessment not found.</p>", 404
        response.raise_for_status()
        assessments = _enrich_with_courses(get_assessments())
        return format_assessments_html(assessments), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to update assessment.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@assessments_bp.delete("/assessments/<int:assessment_id>")
def delete_assessment_route(assessment_id):
    try:
        response = delete_assessment_response(assessment_id)
        if response.status_code == 404:
            return "<p>Assessment not found.</p>", 404
        response.raise_for_status()
        assessments = _enrich_with_courses(get_assessments())
        return format_assessments_html(assessments), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to delete assessment.</p>"
            f"<pre>{exc}</pre>",
            503,
        )
