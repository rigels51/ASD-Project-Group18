import time

from flask import Blueprint, jsonify, request

from services import mcp_api
from views.mcp_rag_formatters import (
    format_mcp_result_html,
    format_mcp_tools_html,
    format_message_html,
)


mcp_mode_bp = Blueprint("assessment_mcp_mode", __name__)


def _wants_json() -> bool:
    return request.args.get("format") == "json" or request.is_json


def _respond(status: int, payload: dict, html: str):
    if _wants_json():
        return jsonify(payload), status
    return html, status


def _input() -> dict:
    if request.is_json:
        data = request.get_json(silent=True) or {}
        args = data.get("arguments") if isinstance(data.get("arguments"), dict) else data
        return {"tool": str(data.get("tool", "")).strip(), **{k: v for k, v in args.items() if k != "tool"}}
    return {key: value.strip() for key, value in request.form.items()}


def _arguments(tool: str, data: dict) -> dict:
    """Build tool arguments from the request; the MCP server does the real validation."""
    if tool == "list_course_assessments":
        return {"course_id": str(data.get("course_id", ""))}
    if tool == "get_student_grade_summary":
        return {"student_id": str(data.get("student_id", ""))}
    if tool == "get_upcoming_assessments":
        arguments = {"from_date": str(data.get("from_date", ""))}
        limit = data.get("limit", 5)
        try:
            arguments["limit"] = int(limit) if str(limit).strip() else 5
        except (TypeError, ValueError):
            raise ValueError("limit must be a whole number")
        return arguments
    return {}


@mcp_mode_bp.get("/mcp/tools")
def mcp_tools():
    if not mcp_api.MCP_ENABLED:
        message = "MCP is disabled (MCP_ENABLED=false)"
        return _respond(503, {"status": "disabled", "error": message},
                        format_message_html("disabled", "MCP disabled", message))
    try:
        tools = mcp_api.list_assessment_tools()
    except Exception:  # noqa: BLE001 - any connection failure means the server is unreachable
        message = f"Shared MCP server unavailable at {mcp_api.MCP_SERVER_URL}"
        return _respond(503, {"status": "error", "error": message},
                        format_message_html("error", "MCP server unreachable", message))
    return _respond(200, {"status": "success", "server": mcp_api.MCP_SERVER_URL, "tools": tools},
                    format_mcp_tools_html(tools, mcp_api.MCP_SERVER_URL))


@mcp_mode_bp.post("/mcp/call")
def mcp_call():
    data = _input()
    tool = data.get("tool", "")

    if not mcp_api.MCP_ENABLED:
        message = "MCP is disabled (MCP_ENABLED=false)"
        return _respond(503, {"status": "disabled", "tool": tool, "error": message},
                        format_message_html("disabled", "MCP disabled", message))

    if tool not in mcp_api.ALLOWED_TOOLS:
        message = f"'{tool}' is not an Assessment & Grades tool. Allowed: {', '.join(sorted(mcp_api.ALLOWED_TOOLS))}"
        return _respond(400, {"status": "rejected", "tool": tool, "error": message},
                        format_message_html("rejected", "Tool outside feature boundary", message))

    try:
        arguments = _arguments(tool, data)
        started = time.monotonic()
        result = mcp_api.call_assessment_tool(tool, arguments)
        elapsed_ms = round((time.monotonic() - started) * 1000)
    except ValueError as exc:  # the tool rejected the input (validation / boundary)
        return _respond(400, {"status": "rejected", "tool": tool, "error": str(exc)},
                        format_message_html("rejected", "Request rejected by the MCP tool", str(exc)))
    except Exception:  # noqa: BLE001
        message = f"Shared MCP server unavailable at {mcp_api.MCP_SERVER_URL}"
        return _respond(503, {"status": "error", "tool": tool, "error": message},
                        format_message_html("error", "MCP server unreachable", message))

    return _respond(
        200,
        {"status": "success", "tool": tool, "arguments": arguments, "elapsed_ms": elapsed_ms, "result": result},
        format_mcp_result_html(tool, arguments, result, elapsed_ms),
    )
