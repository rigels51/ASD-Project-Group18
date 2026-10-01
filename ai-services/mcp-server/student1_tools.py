"""Student 1 Student Records tools for the shared MCP server."""

import os
from typing import Any

import requests
from mcp.server.mcpserver.exceptions import ToolError


STUDENT1_DATABASE_URL = os.getenv(
    "STUDENT1_DATABASE_URL",
    "http://localhost:5002"
).rstrip("/")


def _get_students() -> list[dict[str, Any]]:
    response = requests.get(f"{STUDENT1_DATABASE_URL}/students", timeout=10)
    response.raise_for_status()
    records = response.json()
    if not isinstance(records, list):
        raise ValueError("Student 1 database returned an invalid student list")
    return records


def student_count() -> dict[str, int]:
    """Return the total number of Student 1 student records."""
    return {"student_count": len(_get_students())}


def student_list(course: str = "") -> list[dict[str, Any]]:
    """Return Student 1 students, optionally filtered by course."""
    records = _get_students()
    if course.strip():
        course_key = course.strip().casefold()
        records = [record for record in records if str(record.get("course", "")).casefold() == course_key]
    return records


def student_by_id(student_id: str) -> dict[str, Any]:
    """Return one Student 1 student record by student ID."""
    student_id = (student_id or "").strip().upper()
    if not student_id:
        raise ValueError("student_id is required")
    for record in _get_students():
        if str(record.get("student_id", "")).upper() == student_id:
            return record
    return {"error": "Student not found", "student_id": student_id}


def students_by_status(status: str = "") -> list[dict[str, Any]]:
    """Return Student 1 students, optionally filtered by enrolment status."""
    records = _get_students()
    if status.strip():
        status_key = status.strip().casefold()
        records = [record for record in records if str(record.get("status", "")).casefold() == status_key]
    return records


def _run(function, *args):
    try:
        return function(*args)
    except requests.RequestException as exc:
        raise ToolError("Student 1 database service is unavailable") from exc
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def register_student1_tools(mcp) -> None:
    """Register Student 1 read-only MCP tools."""

    @mcp.tool()
    def get_student_count() -> dict:
        """[Student 1] Count all students in the Student Records system."""
        return _run(student_count)

    @mcp.tool()
    def list_students(course: str = "") -> list[dict]:
        """[Student 1] List students, optionally filtered by course."""
        return _run(student_list, course)

    @mcp.tool()
    def get_student(student_id: str) -> dict:
        """[Student 1] Retrieve one student by student ID (e.g. STU-1001)."""
        return _run(student_by_id, student_id)

    @mcp.tool()
    def list_students_by_status(status: str = "") -> list[dict]:
        """[Student 1] List students filtered by status (Enrolled, On Leave, Graduated)."""
        return _run(students_by_status, status)
