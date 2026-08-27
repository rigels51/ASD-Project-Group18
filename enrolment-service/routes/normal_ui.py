from flask import Blueprint, request
import requests

from services.database_api import (
    get_courses,
    get_course_response,
    create_course_response,
    update_course_response,
    delete_course_response,
    get_enrolments,
    get_enrolment_response,
    create_enrolment_response,
    update_enrolment_response,
    delete_enrolment_response,
)

from views.html_formatters import (
    format_course_html,
    format_courses_html,
    format_enrolment_html,
    format_enrolments_html,
)


normal_ui_bp = Blueprint("normal_ui", __name__)


@normal_ui_bp.get("/")
def health():
    return "<p>enrolment-service running</p>", 200


# =========================================================
# COURSE ROUTES
# =========================================================

@normal_ui_bp.get("/courses")
def get_courses_route():
    try:
        return format_courses_html(get_courses()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve courses from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.get("/courses/by-id")
def get_course_by_id():
    course_id = request.args.get("course_id", "").strip()

    if not course_id:
        return "<p>Course ID is required.</p>", 400

    try:
        response = get_course_response(course_id)

        if response.status_code == 404:
            return "<p>Course not found.</p>", 404

        response.raise_for_status()

        return format_course_html(response.json()), 200

    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve course from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.post("/courses")
def create_course():
    course_code = request.form.get("course_code", "").strip().upper()
    course_name = request.form.get("course_name", "").strip()
    credits = request.form.get("credits", "").strip()
    capacity = request.form.get("capacity", "").strip()

    if not course_code or not course_name or not credits or not capacity:
        return "<p>All course fields are required.</p>", 400

    data = {
        "course_code": course_code,
        "course_name": course_name,
        "credits": credits,
        "capacity": capacity,
    }

    try:
        response = create_course_response(data)

        if response.status_code == 409:
            return "<p>Course code already exists.</p>", 409

        if response.status_code == 400:
            return f"<p>{response.json().get('error')}</p>", 400

        response.raise_for_status()

        result = response.json()

        return (
            f"<p>Course created successfully. "
            f"Course ID: {result.get('course_id')}</p>",
            201,
        )

    except requests.RequestException as exc:
        return (
            "<p>Failed to create course.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.post("/courses/update")
def update_course():
    course_id = request.form.get("course_id", "").strip()
    course_code = request.form.get("course_code", "").strip().upper()
    course_name = request.form.get("course_name", "").strip()
    credits = request.form.get("credits", "").strip()
    capacity = request.form.get("capacity", "").strip()

    if (
        not course_id
        or not course_code
        or not course_name
        or not credits
        or not capacity
    ):
        return "<p>All course fields are required.</p>", 400

    data = {
        "course_code": course_code,
        "course_name": course_name,
        "credits": credits,
        "capacity": capacity,
    }

    try:
        response = update_course_response(course_id, data)

        if response.status_code == 404:
            return "<p>Course not found.</p>", 404

        if response.status_code == 409:
            return "<p>Course code already exists.</p>", 409

        if response.status_code == 400:
            return f"<p>{response.json().get('error')}</p>", 400

        response.raise_for_status()

        return "<p>Course updated successfully.</p>", 200

    except requests.RequestException as exc:
        return (
            "<p>Failed to update course.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.post("/courses/delete")
def delete_course():
    course_id = request.form.get("course_id", "").strip()

    if not course_id:
        return "<p>Course ID is required.</p>", 400

    try:
        response = delete_course_response(course_id)

        if response.status_code == 404:
            return "<p>Course not found.</p>", 404

        if response.status_code == 409:
            return (
                "<p>Cannot delete this course because students "
                "are enrolled in it.</p>",
                409,
            )

        response.raise_for_status()

        return "<p>Course deleted successfully.</p>", 200

    except requests.RequestException as exc:
        return (
            "<p>Failed to delete course.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


# =========================================================
# ENROLMENT ROUTES
# =========================================================

@normal_ui_bp.get("/enrolments")
def get_enrolments_route():
    try:
        return format_enrolments_html(get_enrolments()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve enrolments from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.get("/enrolments/by-id")
def get_enrolment_by_id():
    enrolment_id = request.args.get("enrolment_id", "").strip()

    if not enrolment_id:
        return "<p>Enrolment ID is required.</p>", 400

    try:
        response = get_enrolment_response(enrolment_id)

        if response.status_code == 404:
            return "<p>Enrolment not found.</p>", 404

        response.raise_for_status()

        return format_enrolment_html(response.json()), 200

    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve enrolment.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.post("/enrolments")
def create_enrolment():
    student_id = request.form.get("student_id", "").strip()
    course_id = request.form.get("course_id", "").strip()
    status = request.form.get("status", "Active").strip()

    if not student_id or not course_id:
        return "<p>Student ID and Course ID are required.</p>", 400

    data = {
        "student_id": student_id,
        "course_id": course_id,
        "status": status,
    }

    try:
        response = create_enrolment_response(data)

        if response.status_code == 404:
            return "<p>Course not found.</p>", 404

        if response.status_code == 400:
            return f"<p>{response.json().get('error')}</p>", 400

        response.raise_for_status()

        result = response.json()

        return (
            f"<p>Student enrolled successfully. "
            f"Enrolment ID: {result.get('enrolment_id')}</p>",
            201,
        )

    except requests.RequestException as exc:
        return (
            "<p>Failed to create enrolment.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.post("/enrolments/update")
def update_enrolment():
    enrolment_id = request.form.get("enrolment_id", "").strip()
    student_id = request.form.get("student_id", "").strip()
    course_id = request.form.get("course_id", "").strip()
    status = request.form.get("status", "").strip()

    if (
        not enrolment_id
        or not student_id
        or not course_id
        or not status
    ):
        return "<p>All enrolment fields are required.</p>", 400

    data = {
        "student_id": student_id,
        "course_id": course_id,
        "status": status,
    }

    try:
        response = update_enrolment_response(enrolment_id, data)

        if response.status_code == 404:
            return "<p>Enrolment or course not found.</p>", 404

        if response.status_code == 400:
            return f"<p>{response.json().get('error')}</p>", 400

        response.raise_for_status()

        return "<p>Enrolment updated successfully.</p>", 200

    except requests.RequestException as exc:
        return (
            "<p>Failed to update enrolment.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.post("/enrolments/delete")
def delete_enrolment():
    enrolment_id = request.form.get("enrolment_id", "").strip()

    if not enrolment_id:
        return "<p>Enrolment ID is required.</p>", 400

    try:
        response = delete_enrolment_response(enrolment_id)

        if response.status_code == 404:
            return "<p>Enrolment not found.</p>", 404

        response.raise_for_status()

        return "<p>Enrolment deleted successfully.</p>", 200

    except requests.RequestException as exc:
        return (
            "<p>Failed to delete enrolment.</p>"
            f"<pre>{exc}</pre>",
            503,
        )