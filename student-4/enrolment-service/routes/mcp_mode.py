import json

from flask import Blueprint, request

from services.mcp_api import (
    list_course_tools,
    call_course_tool,
)


mcp_bp = Blueprint("mcp_mode", __name__)


def render_json(title: str, payload):
    return f"""
    <h3>{title}</h3>
    <pre>{json.dumps(payload, indent=2)}</pre>
    """


@mcp_bp.get("/mcp/tools")
def mcp_tools():
    try:
        tools = list_course_tools()
        return render_json(
            "Student 4 MCP Tools",
            tools
        ), 200

    except Exception as exc:
        return render_json(
            "MCP Error",
            {"error": str(exc)}
        ), 503


@mcp_bp.post("/mcp/course-count")
def mcp_course_count():
    try:
        result = call_course_tool(
            "get_course_count"
        )

        return render_json(
            "MCP Tool: get_course_count",
            result
        ), 200

    except Exception as exc:
        return render_json(
            "MCP Error",
            {"error": str(exc)}
        ), 503


@mcp_bp.post("/mcp/courses")
def mcp_courses():
    try:
        result = call_course_tool(
            "list_courses"
        )

        return render_json(
            "MCP Tool: list_courses",
            result
        ), 200

    except Exception as exc:
        return render_json(
            "MCP Error",
            {"error": str(exc)}
        ), 503


@mcp_bp.post("/mcp/course")
def mcp_course():
    course_id = request.form.get(
        "course_id",
        ""
    ).strip()

    if not course_id:
        return render_json(
            "MCP Error",
            {"error": "course_id is required"}
        ), 400

    try:
        course_id_int = int(course_id)

    except ValueError:
        return render_json(
            "MCP Error",
            {"error": "course_id must be an integer"}
        ), 400

    try:
        result = call_course_tool(
            "get_course",
            {
                "course_id": course_id_int
            }
        )

        return render_json(
            "MCP Tool: get_course",
            result
        ), 200

    except Exception as exc:
        return render_json(
            "MCP Error",
            {"error": str(exc)}
        ), 503


@mcp_bp.post("/mcp/enrolments")
def mcp_enrolments():
    try:
        result = call_course_tool(
            "list_enrolments"
        )

        return render_json(
            "MCP Tool: list_enrolments",
            result
        ), 200

    except Exception as exc:
        return render_json(
            "MCP Error",
            {"error": str(exc)}
        ), 503