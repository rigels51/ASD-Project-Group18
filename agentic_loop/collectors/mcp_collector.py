"""ACT step for MCP mode: talk to the shared MCP server and record raw observations."""

import json
import time

import anyio


async def _list_tools(url):
    from mcp import Client

    async with Client(url) as client:
        result = await client.list_tools()
    return [{"name": tool.name, "description": tool.description or ""} for tool in result.tools]


async def _call_tool(url, name, arguments):
    from mcp import Client
    from mcp.types import TextContent

    async with Client(url) as client:
        result = await client.call_tool(name, arguments)

    text = "\n".join(block.text for block in result.content if isinstance(block, TextContent))
    payload = result.structured_content
    if payload is None and text and not result.is_error:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = {"result": text}
    return {"is_error": bool(result.is_error), "result": payload, "message": text if result.is_error else ""}


def _root_cause(exc):
    """MCP client errors arrive wrapped in ExceptionGroups; report the innermost message."""
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    return f"{type(exc).__name__}: {exc}"


def list_tools(url):
    started = time.monotonic()
    try:
        tools = anyio.run(_list_tools, url)
        return {"ok": True, "tools": tools, "latency_ms": round((time.monotonic() - started) * 1000)}
    except BaseException as exc:  # noqa: BLE001 - connection failures are observations, not crashes
        return {"ok": False, "tools": [], "error": _root_cause(exc)}


def call_tool(url, name, arguments):
    started = time.monotonic()
    try:
        observation = anyio.run(_call_tool, url, name, arguments)
    except BaseException as exc:  # noqa: BLE001
        observation = {"is_error": True, "result": None, "message": _root_cause(exc)}
    observation["latency_ms"] = round((time.monotonic() - started) * 1000)
    return observation
