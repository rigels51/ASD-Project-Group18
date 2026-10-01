import os
import re
from datetime import date
from typing import Any

import requests
from mcp.server.mcpserver.exceptions import ToolError


ASSESSMENT_DATABASE_URL = os.getenv(
    "ASSESSMENT_DATABASE_URL", "http://localhost:5022"
).rstrip("/")

COURSE_CODE_PATTERN = re.compile(r"^[A-Z]{2,4}\d{3}$")
STUDENT_ID_PATTERN = re.compile(r"^STU-\d{4}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_LIMIT = 20

ASSESSMENT_FIELDS = (
    "assessment_id", "course_id", "assessment_name", "assessment_type",
    "description", "due_date", "max_mark", "weight",
)
GRADE_FIELDS = (
    "grade_id", "assessment_id", "assessment_name", "course_id",
    "mark", "max_mark", "grade", "feedback", "date_recorded",
)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _course_code(course_id: str) -> str:
    code = (course_id or "").strip().upper()
    if not COURSE_CODE_PATTERN.match(code):
        raise ValueError("course_id must be a course code like ASD101")
    return code


def _student_id(student_id: str) -> str:
    value = (student_id or "").strip().upper()
    if re.fullmatch(r"STU\d{4}", value):  # accept STU1001 as STU-1001
        value = f"STU-{value[3:]}"
    if not STUDENT_ID_PATTERN.match(value):
        raise ValueError("student_id must look like STU-1001")
    return value


def _from_date(from_date: str) -> str:
    value = (from_date or "").strip()
    if not value:
        return date.today().isoformat()
    if not DATE_PATTERN.match(value):
        raise ValueError("from_date must use YYYY-MM-DD format")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("from_date is not a real calendar date") from exc
    return value


def _limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be an integer from 1 to {MAX_LIMIT}")
    return limit


# ---------------------------------------------------------------------------
# Database-service access (read-only GETs)
# ---------------------------------------------------------------------------

def _get(path: str, params: dict | None = None) -> requests.Response:
    return requests.get(f"{ASSESSMENT_DATABASE_URL}{path}", params=params, timeout=10)


def _get_list(path: str, params: dict | None = None) -> list[dict[str, Any]]:
    response = _get(path, params)
    response.raise_for_status()
    records = response.json()
    if not isinstance(records, list):
        raise ValueError("Assessment database service returned an invalid list")
    return records


def _pick(record: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: record.get(field) for field in fields if field in record}


def _percent(mark, max_mark) -> float | None:
    try:
        if mark is None or not max_mark:
            return None
        return round(float(mark) / float(max_mark) * 100, 1)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Tool logic (plain functions, unit-tested in test_student5_tools.py)
# ---------------------------------------------------------------------------

def course_assessments(course_id: str) -> dict[str, Any]:
    """Assessments for one course with total weighting."""
    code = _course_code(course_id)
    records = _get_list("/assessments", {"course_id": code})
    assessments = sorted(
        (_pick(r, ASSESSMENT_FIELDS) for r in records),
        key=lambda a: (str(a.get("due_date") or ""), a.get("assessment_id") or 0),
    )
    total_weight = round(sum(float(a.get("weight") or 0) for a in assessments), 1)
    return {
        "course_id": code,
        "assessment_count": len(assessments),
        "total_weight": total_weight,
        "assessments": assessments,
    }


def student_grade_summary(student_id: str) -> dict[str, Any]:
    """Grades for one student, with graded/pending counts and average percentage."""
    sid = _student_id(student_id)
    response = _get(f"/grades/student/{sid}")
    if response.status_code == 404:
        return {
            "student_id": sid,
            "found": False,
            "graded_count": 0,
            "pending_count": 0,
            "average_percent": None,
            "grades": [],
        }
    response.raise_for_status()
    records = response.json()
    if not isinstance(records, list):
        raise ValueError("Assessment database service returned an invalid list")

    grades = []
    for record in records:
        row = _pick(record, GRADE_FIELDS)
        row["percent"] = _percent(record.get("mark"), record.get("max_mark"))
        grades.append(row)

    percents = [g["percent"] for g in grades if g["percent"] is not None]
    return {
        "student_id": sid,
        "found": True,
        "graded_count": len(percents),
        "pending_count": len(grades) - len(percents),
        "average_percent": round(sum(percents) / len(percents), 1) if percents else None,
        "grades": grades,
    }


def upcoming_assessments(from_date: str = "", limit: int = 5) -> dict[str, Any]:
    """Assessments due on or after from_date, soonest first."""
    start = _from_date(from_date)
    count = _limit(limit)
    records = _get_list("/assessments")
    due = sorted(
        (_pick(r, ASSESSMENT_FIELDS) for r in records if str(r.get("due_date") or "") >= start),
        key=lambda a: (str(a.get("due_date")), a.get("assessment_id") or 0),
    )
    return {
        "from_date": start,
        "limit": count,
        "total_upcoming": len(due),
        "assessments": due[:count],
    }


def _run(function, *args):
    try:
        return function(*args)
    except requests.RequestException as exc:
        raise ToolError("Assessment & Grades database service is unavailable") from exc
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def register_student5_tools(mcp) -> None:
    """Register Student 5 read-only MCP tools on the shared server."""

    @mcp.tool()
    def list_course_assessments(course_id: str) -> dict:
        """[Student 5] List the assessments for one course code (e.g. ASD101) with due dates, weights and the course's total weighting. Read-only."""
        return _run(course_assessments, course_id)

    @mcp.tool()
    def get_student_grade_summary(student_id: str) -> dict:
        """[Student 5] Summarise one student's grades (student_id like STU-1001): marks, percentages, graded vs pending, average. Read-only."""
        return _run(student_grade_summary, student_id)

    @mcp.tool()
    def get_upcoming_assessments(from_date: str = "", limit: int = 5) -> dict:
        """[Student 5] List assessments due on or after from_date (YYYY-MM-DD, default today), soonest first, up to limit (1-20). Read-only."""
        return _run(upcoming_assessments, from_date, limit)
