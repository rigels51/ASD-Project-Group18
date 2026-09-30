"""Student 3 (Timetable & Class Scheduling) tools for the shared MCP server.

Every tool is read-only and reads the live timetable through the timetable
backend's JSON API (GET /api/timetable). The shared MCP server runs on the
host, so the default URL is the backend's published host port. The server
never opens timetable.db directly (service boundary rule).

Registered on the shared server by register_timetable_tools(mcp) in server.py.
"""

import os
import re
from typing import Any

import requests
from mcp.server.mcpserver.exceptions import ToolError


TIMETABLE_API_URL = os.getenv(
    "TIMETABLE_API_URL", "http://localhost:5003/api/timetable"
).rstrip("/")

VALID_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
PUBLIC_FIELDS = (
    "session_id", "course_code", "session_type", "day",
    "start_time", "end_time", "room", "semester",
)


def _get_sessions() -> list[dict[str, Any]]:
    response = requests.get(TIMETABLE_API_URL, timeout=10)
    response.raise_for_status()
    records = response.json()
    if not isinstance(records, list):
        raise ValueError("Timetable service returned an invalid session list")
    return records


def _public(record: dict[str, Any]) -> dict[str, Any]:
    return {field: record[field] for field in PUBLIC_FIELDS if field in record}


def _normalise_day(day: str) -> str:
    for valid in VALID_DAYS:
        if valid.casefold() == (day or "").strip().casefold():
            return valid
    raise ValueError(f"day must be one of: {', '.join(VALID_DAYS)}")


def _validate_times(start_time: str, end_time: str) -> tuple[str, str]:
    start_time, end_time = (start_time or "").strip(), (end_time or "").strip()
    if not TIME_PATTERN.match(start_time) or not TIME_PATTERN.match(end_time):
        raise ValueError("start_time and end_time must use 24-hour HH:MM format")
    if start_time >= end_time:
        raise ValueError("start_time must be earlier than end_time")
    return start_time, end_time


def _overlaps(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    return a_start < b_end and b_start < a_end


def sessions_by_course(course_code: str, sessions: list[dict] | None = None) -> dict[str, Any]:
    """Return every scheduled session for one course code."""
    code = (course_code or "").strip().upper()
    if not code:
        raise ValueError("course_code is required")
    sessions = _get_sessions() if sessions is None else sessions
    matches = [_public(s) for s in sessions if str(s.get("course_code", "")).upper() == code]
    return {"course_code": code, "session_count": len(matches), "sessions": matches}


def room_availability(
    room: str, day: str, start_time: str, end_time: str, sessions: list[dict] | None = None
) -> dict[str, Any]:
    """Check whether a room is free for a time slot, listing any conflicting sessions."""
    room = (room or "").strip()
    if not room:
        raise ValueError("room is required")
    day = _normalise_day(day)
    start_time, end_time = _validate_times(start_time, end_time)
    sessions = _get_sessions() if sessions is None else sessions
    conflicts = [
        _public(s)
        for s in sessions
        if str(s.get("room", "")).casefold() == room.casefold()
        and s.get("day") == day
        and _overlaps(start_time, end_time, s["start_time"], s["end_time"])
    ]
    return {
        "room": room,
        "day": day,
        "start_time": start_time,
        "end_time": end_time,
        "available": not conflicts,
        "conflicts": conflicts,
    }


def timetable_clashes(sessions: list[dict] | None = None) -> dict[str, Any]:
    """Find every pair of sessions booked in the same room at overlapping times."""
    sessions = _get_sessions() if sessions is None else sessions
    clashes = []
    for i in range(len(sessions)):
        for j in range(i + 1, len(sessions)):
            a, b = sessions[i], sessions[j]
            if a.get("day") != b.get("day") or a.get("room") != b.get("room"):
                continue
            if _overlaps(a["start_time"], a["end_time"], b["start_time"], b["end_time"]):
                clashes.append({
                    "room": a["room"],
                    "day": a["day"],
                    "session_a": _public(a),
                    "session_b": _public(b),
                })
    return {"clash_count": len(clashes), "clashes": clashes}


def _run(function, *args):
    try:
        return function(*args)
    except requests.RequestException as exc:
        raise ToolError("Timetable service is unavailable") from exc
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def register_timetable_tools(mcp) -> None:
    """Register the three read-only Timetable tools on the shared MCP server."""

    @mcp.tool()
    def get_sessions_by_course(course_code: str) -> dict:
        """[Timetable] List every scheduled session (day, time, room, type) for a course code such as ASD101."""
        return _run(sessions_by_course, course_code)

    @mcp.tool()
    def check_room_availability(room: str, day: str, start_time: str, end_time: str) -> dict:
        """[Timetable] Check if a room is free on a day between start_time and end_time (HH:MM); returns any conflicting sessions."""
        return _run(room_availability, room, day, start_time, end_time)

    @mcp.tool()
    def find_timetable_clashes() -> dict:
        """[Timetable] Find all pairs of sessions booked in the same room at overlapping times."""
        return _run(timetable_clashes)
