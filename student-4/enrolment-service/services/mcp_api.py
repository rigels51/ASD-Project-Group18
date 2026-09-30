import json
import os


MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "http://localhost:8000/mcp"
)

MCP_ENABLED = os.getenv(
    "MCP_ENABLED",
    "true"
).strip().lower() in {"1", "true", "yes", "on"}


# Student 4 can only call its own Course & Enrollment tools.
ALLOWED_TOOLS = {
    "get_course_count",
    "list_courses",
    "get_course",
    "list_enrolments",
}


async def _list_tools_async():
    from mcp import Client

    async with Client(MCP_SERVER_URL) as client:
        result = await client.list_tools()

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in result.tools
            if tool.name in ALLOWED_TOOLS
        ]


async def _call_tool_async(name: str, arguments: dict):
    from mcp import Client
    from mcp.types import TextContent

    async with Client(MCP_SERVER_URL) as client:
        result = await client.call_tool(name, arguments)

    if result.is_error:
        messages = [
            block.text
            for block in result.content
            if isinstance(block, TextContent)
        ]

        raise RuntimeError(
            "; ".join(messages) or "MCP tool call failed"
        )

    if result.structured_content is not None:
        return result.structured_content

    text = "\n".join(
        block.text
        for block in result.content
        if isinstance(block, TextContent)
    )

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"result": text}


def list_course_tools():
    import anyio

    if not MCP_ENABLED:
        raise RuntimeError("MCP Mode is disabled")

    return anyio.run(_list_tools_async)


def call_course_tool(name: str, arguments: dict | None = None):
    import anyio

    if not MCP_ENABLED:
        raise RuntimeError("MCP Mode is disabled")

    if name not in ALLOWED_TOOLS:
        raise ValueError(
            f"Unknown Student 4 MCP tool: {name}"
        )

    return anyio.run(
        _call_tool_async,
        name,
        arguments or {}
    )