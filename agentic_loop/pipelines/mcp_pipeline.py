"""MCP validation mode: Plan -> Act -> Observe -> Adapt against the shared MCP server."""

import json

from agentic_loop.collectors import mcp_collector
from agentic_loop.config.review_config import (
    MCP_SERVER_URL,
    MCP_SKIP_TOOLS,
    MCP_TOOL_CASES,
    UNREGISTERED_TOOL,
)
from agentic_loop.config.review_config import OLLAMA_MODEL
from agentic_loop.core.ai_runner import suggest_adaptation
from agentic_loop.core.reporter import Reporter


def _evaluate(case, observation):
    """Return (passed, detail) for one tool call against its expectation."""
    if case["expect"] == "error":
        if observation["is_error"]:
            return True, f"rejected as expected: {observation['message'][:90]}"
        return False, "expected the tool to reject this input, but it succeeded"

    if observation["is_error"]:
        return False, observation["message"][:120] or "tool returned an error"
    result = observation["result"]
    if not isinstance(result, (dict, list)):
        return False, "result is not structured JSON"
    missing = [key for key in case.get("expect_keys", []) if not isinstance(result, dict) or key not in result]
    if missing:
        return False, f"structured result missing keys: {', '.join(missing)}"
    preview = json.dumps(result)[:90]
    return True, f"structured result {preview}{'…' if len(json.dumps(result)) > 90 else ''}"


def run(use_ai=True):
    report = Reporter("mcp")

    # ---------- PLAN ----------
    report.stage("PLAN", f"Validate the shared MCP server at {MCP_SERVER_URL}.")
    report.line("1. List registered tools (tool discovery).")
    report.line("2. Call every tool that has validation cases; check it returns a structured result.")
    report.line("3. Send invalid inputs and expect rejection (input validation).")
    report.line(f"4. Call an unregistered tool ('{UNREGISTERED_TOOL}') and expect rejection (tool boundary).")

    # ---------- ACT ----------
    report.stage("ACT", "Discovering tools and executing validation cases.")
    listing = mcp_collector.list_tools(MCP_SERVER_URL)
    if not listing["ok"]:
        report.line(f"MCP server unreachable: {listing['error']}")
        report.stage("OBSERVE", "0 checks run — server unreachable.")
        report.stage("ADAPT", "Start the shared MCP server (cd ai-services/mcp-server && python server.py) and rerun.")
        report.save()
        return False

    tools = listing["tools"]
    report.line(f"{len(tools)} tools registered (listed in {listing['latency_ms']} ms): "
                + ", ".join(tool["name"] for tool in tools))

    rows, results = [], []
    registered = {tool["name"] for tool in tools}
    for tool in tools:
        name = tool["name"]
        cases = MCP_TOOL_CASES.get(name)
        if name in MCP_SKIP_TOOLS:
            rows.append((name, "—", "SKIP", "validated through RAG mode"))
            continue
        if not cases:
            rows.append((name, "—", "NOT EXERCISED", "no case in agentic_loop/config/review_config.py"))
            results.append(("not_exercised", name))
            continue
        for case in cases:
            observation = mcp_collector.call_tool(MCP_SERVER_URL, name, case["arguments"])
            passed, detail = _evaluate(case, observation)
            results.append(("pass" if passed else "fail", name))
            rows.append((name, json.dumps(case["arguments"]), "PASS" if passed else "FAIL",
                         f"{detail} ({observation['latency_ms']} ms)"))

    for name in sorted(set(MCP_TOOL_CASES) - registered):
        rows.append((name, "—", "MISSING", "has validation cases but is not registered on the server"))
        results.append(("fail", name))

    boundary = mcp_collector.call_tool(MCP_SERVER_URL, UNREGISTERED_TOOL, {})
    boundary_passed = boundary["is_error"]
    results.append(("pass" if boundary_passed else "fail", UNREGISTERED_TOOL))
    rows.append((UNREGISTERED_TOOL, "{}", "PASS" if boundary_passed else "FAIL",
                 "unregistered tool rejected (boundary enforced)" if boundary_passed
                 else "unregistered tool was accepted — boundary NOT enforced"))

    # ---------- OBSERVE ----------
    passed = sum(1 for status, _ in results if status == "pass")
    failed = [name for status, name in results if status == "fail"]
    unexercised = [name for status, name in results if status == "not_exercised"]
    report.stage("OBSERVE", f"{passed} passed, {len(failed)} failed, {len(unexercised)} tools not exercised.")
    report.table(["Tool", "Arguments", "Result", "Detail"], rows)

    # ---------- ADAPT ----------
    report.stage("ADAPT")
    if failed:
        report.line("Fix before submission: " + ", ".join(sorted(set(failed))))
    if unexercised:
        report.line("Add validation cases for: " + ", ".join(unexercised))
    if not failed and not unexercised:
        report.line("All registered tools validated; no rule-based adaptation needed.")
    if use_ai:
        summary = "\n".join(f"{r[0]} {r[1]} -> {r[2]}: {r[3]}" for r in rows)
        advice, error = suggest_adaptation("mcp", summary)
        report.line(f"Local AI suggestion ({OLLAMA_MODEL if advice else 'unavailable'}):")
        report.block(advice or error)

    report.save()
    return not failed
