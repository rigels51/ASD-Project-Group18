import json
import os


MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
MCP_ENABLED = os.getenv("MCP_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}

# Tool boundary: this feature may only call its own tools on the shared server.
ALLOWED_TOOLS = {
    "list_course_assessments",
    "get_student_grade_summary",
    "get_upcoming_assessments",
}


class McpDisabledError(RuntimeError):
    """Raised when MCP_ENABLED is false (e.g. in CI/CD)."""


async def _list_tools_async():
    from mcp import Client

    async with Client(MCP_SERVER_URL) as client:
        result = await client.list_tools()
    return [
        {"name": tool.name, "description": tool.description, "input_schema": tool.input_schema}
        for tool in result.tools
        if tool.name in ALLOWED_TOOLS
    ]


async def _call_tool_async(name: str, arguments: dict):
    from mcp import Client
    from mcp.types import TextContent

    async with Client(MCP_SERVER_URL) as client:
        result = await client.call_tool(name, arguments)

    # Raise only after the client session has closed; raising inside it wraps
    # the error in an ExceptionGroup and hides the tool's validation message.
    if result.is_error:
        messages = [block.text for block in result.content if isinstance(block, TextContent)]
        raise ValueError("; ".join(messages) or "MCP tool call failed")
    if result.structured_content is not None:
        return result.structured_content
    text = "\n".join(block.text for block in result.content if isinstance(block, TextContent))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"result": text}


def list_assessment_tools():
    import anyio

    if not MCP_ENABLED:
        raise McpDisabledError("MCP is disabled (MCP_ENABLED=false)")
    return anyio.run(_list_tools_async)


def call_assessment_tool(name: str, arguments: dict | None = None):
    """Call one Student 5 tool. ValueError = rejected input; other errors = server unreachable."""
    import anyio

    if not MCP_ENABLED:
        raise McpDisabledError("MCP is disabled (MCP_ENABLED=false)")
    if name not in ALLOWED_TOOLS:
        raise PermissionError(f"Tool '{name}' is outside the Assessment & Grades boundary")
    return anyio.run(_call_tool_async, name, arguments or {})
