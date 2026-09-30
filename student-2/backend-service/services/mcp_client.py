import json
import os


MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://student2-mcp:8000/mcp")
ALLOWED_TOOLS = {
    "get_staff_count",
    "list_staff",
    "get_staff_member",
    "get_employment_summary",
    "refresh_corpus",
    "retrieve_context",
    "answer_question",
}


async def _call_tool_async(name: str, arguments: dict):
    from mcp import Client
    from mcp.types import TextContent

    async with Client(MCP_SERVER_URL) as client:
        result = await client.call_tool(name, arguments)
        if result.is_error:
            messages = [block.text for block in result.content if isinstance(block, TextContent)]
            raise RuntimeError("; ".join(messages) or "MCP tool call failed")
        if result.structured_content is not None:
            return result.structured_content
        text = "\n".join(
            block.text for block in result.content if isinstance(block, TextContent)
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"result": text}


def call_staff_tool(name: str, arguments: dict | None = None):
    import anyio

    if name not in ALLOWED_TOOLS:
        raise ValueError("Unknown staff MCP tool")
    return anyio.run(_call_tool_async, name, arguments or {})