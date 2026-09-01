from flask import Blueprint, make_response, request
import requests

from services.database_api import (
    create_staff_response,
    delete_staff_response,
    get_staff,
    get_staff_by_department_response,
    get_staff_by_id_response,
    update_staff_response,
)
from views.html_formatters import (
    format_empty_row_html,
    format_form_message_html,
    format_staff_detail_html,
    format_staff_edit_row_html,
    format_staff_html,
    format_staff_row_html,
    format_staffs_html,
)


normal_ui_bp = Blueprint("normal_ui", __name__)

STAFF_FORM_FIELDS = ("given_name", "family_name", "email", "department", "employment_type")


def _read_staff_form():
    return {field: request.form.get(field, "").strip() for field in STAFF_FORM_FIELDS}


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


@normal_ui_bp.get("/staff/by-department")
def get_staff_by_department():
    department_id = request.args.get("department_id", "").strip()

    if not department_id:
        return "<p>Department ID is required.</p>", 400

    try:
        response = get_staff_by_department_response(department_id)

        if response.status_code == 404:
            return format_empty_row_html("No staff found in this department."), 200

        response.raise_for_status()
        return format_staffs_html(response.json()), 200
    except requests.RequestException as exc:
        return (
            "<p>Failed to retrieve department results from database-service.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@normal_ui_bp.get("/staff/<int:staff_id>/edit")
def edit_staff_row(staff_id):
    try:
        response = get_staff_by_id_response(staff_id)
        if response.status_code == 404:
            return format_empty_row_html("Staff member not found."), 404

        response.raise_for_status()
        return format_staff_edit_row_html(response.json()), 200
    except requests.RequestException as exc:
        return format_empty_row_html(f"Failed to load staff member: {exc}"), 503


@normal_ui_bp.get("/staff/<int:staff_id>/view")
def view_staff_row(staff_id):
    try:
        response = get_staff_by_id_response(staff_id)
        if response.status_code == 404:
            return "", 404

        response.raise_for_status()
        return format_staff_row_html(response.json()), 200
    except requests.RequestException as exc:
        return format_empty_row_html(f"Failed to load staff member: {exc}"), 503


@normal_ui_bp.post("/staff")
def add_staff():
    payload = _read_staff_form()

    if not all(payload.values()):
        return format_form_message_html("All fields are required.", is_error=True), 200

    try:
        response = create_staff_response(payload)

        if response.status_code == 409:
            return (
                format_form_message_html(
                    "A staff member with that email already exists.", is_error=True
                ),
                200,
            )

        response.raise_for_status()
        new_staff = response.json()

        message = format_form_message_html(
            f"Added {new_staff['given_name']} {new_staff['family_name']} to {new_staff['department']}."
        )
        resp = make_response(message, 200)
        resp.headers["HX-Trigger"] = "staff-changed"
        return resp
    except requests.RequestException as exc:
        return (
            format_form_message_html(f"Failed to save staff member: {exc}", is_error=True),
            200,
        )


@normal_ui_bp.put("/staff/<int:staff_id>")
def update_staff_route(staff_id):
    payload = _read_staff_form()

    try:
        response = update_staff_response(staff_id, payload)

        if response.status_code == 404:
            return format_empty_row_html("Staff member not found."), 404

        if response.status_code == 409:
            existing = get_staff_by_id_response(staff_id)
            existing.raise_for_status()
            return format_staff_edit_row_html(existing.json()), 200

        response.raise_for_status()
        return format_staff_row_html(response.json()), 200
    except requests.RequestException as exc:
        return format_empty_row_html(f"Failed to update staff member: {exc}"), 503


@normal_ui_bp.delete("/staff/<int:staff_id>")
def delete_staff_route(staff_id):
    try:
        response = delete_staff_response(staff_id)

        if response.status_code == 404:
            return "", 404

        response.raise_for_status()
        return "", 200
    except requests.RequestException as exc:
        return format_empty_row_html(f"Failed to remove staff member: {exc}"), 503