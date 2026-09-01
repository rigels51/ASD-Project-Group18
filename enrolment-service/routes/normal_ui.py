from flask import Blueprint, request
import requests

from services.database_api import get_staff, get_staff_by_id_response, get_staff_by_department_response, get_staff_by_subject_response
from views.html_formatters import format_staff_detail_html, format_staff_html, format_staffs_html


normal_ui_bp = Blueprint("normal_ui", __name__)


@normal_ui_bp.get("/")
def health():
    return "<p>enrolment-service running</p>", 200


@normal_ui_bp.get("/staff")
def get_staff_route():
    try:
        return format_staff_html(get_staff()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve staff from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.get("/staff/by-id")
def get_staff_by_id():
    staff_id = request.args.get("staff_id", "").strip()

    if not staff_id:
        return "<p>Staff ID is required.</p>", 400

    try:
        response = get_staff_by_id_response(staff_id)

        if response.status_code == 404:
            return "<p>Staff member not found.</p>", 404
        if response.status_code == 400:
            return "<p>Staff ID must be valid.</p>", 400

        response.raise_for_status()
        return format_staff_detail_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve staff member from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.get("/staff/by-subject")
def get_staff_by_subject():
    subject_code = request.args.get("subject_code", "").strip().upper()

    if not subject_code:
        return "<p>Subject code is required.</p>", 400

    try:
        response = get_staff_by_subject_response(subject_code)

        if response.status_code == 404:
            return f"<p>No staff members found for {subject_code}.</p>", 404

        response.raise_for_status()
        return format_staffs_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve subject results from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )