"""Student 4 Course & Enrollment tools for the shared MCP server."""

import os
from typing import Any

import requests
from mcp.server.mcpserver.exceptions import ToolError


STUDENT4_DATABASE_URL = os.getenv(
    "STUDENT4_DATABASE_URL",
    "http://localhost:5032"
).rstrip("/")


def _get_json(path: str):
    response = requests.get(
        f"{STUDENT4_DATABASE_URL}{path}",
        timeout=10
    )
    response.raise_for_status()
    return response.json()


def course_count() -> dict[str, int]:
    """Return the total number of Student 4 courses."""
    courses = _get_json("/courses")

    if not isinstance(courses, list):
        raise ValueError("Student 4 database returned an invalid course list")

    return {
        "course_count": len(courses)
    }


def course_list() -> list[dict[str, Any]]:
    """Return all Student 4 courses."""
    courses = _get_json("/courses")

    if not isinstance(courses, list):
        raise ValueError("Student 4 database returned an invalid course list")

    return courses


def course_by_id(course_id: int) -> dict[str, Any]:
    """Return one course by course ID."""
    if course_id < 1:
        raise ValueError("course_id must be a positive integer")

    response = requests.get(
        f"{STUDENT4_DATABASE_URL}/courses/{course_id}",
        timeout=10
    )

    if response.status_code == 404:
        return {
            "error": "Course not found",
            "course_id": course_id
        }

    response.raise_for_status()
    return response.json()


def enrolment_list() -> list[dict[str, Any]]:
    """Return all Student 4 enrolment records."""
    enrolments = _get_json("/enrolments")

    if not isinstance(enrolments, list):
        raise ValueError("Student 4 database returned an invalid enrolment list")

    return enrolments


def _run(function, *args):
    try:
        return function(*args)

    except requests.RequestException as exc:
        raise ToolError(
            "Student 4 Course & Enrollment database service is unavailable"
        ) from exc

    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def register_student4_tools(mcp) -> None:
    """Register Student 4 read-only MCP tools."""

    @mcp.tool()
    def get_course_count() -> dict:
        """[Student 4] Count all courses in Course & Enrollment Management."""
        return _run(course_count)

    @mcp.tool()
    def list_courses() -> list[dict]:
        """[Student 4] List all available courses."""
        return _run(course_list)

    @mcp.tool()
    def get_course(course_id: int) -> dict:
        """[Student 4] Retrieve one course by course ID."""
        return _run(course_by_id, course_id)

    @mcp.tool()
    def list_enrolments() -> list[dict]:
        """[Student 4] List all Course & Enrollment enrolment records."""
        return _run(enrolment_list)