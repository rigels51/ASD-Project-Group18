import os

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
import requests

from tools import employment_summary, staff_count, staff_directory, staff_member


mcp = MCPServer(
	"Student 2 Staff Registry",
	instructions=(
		"Use these read-only tools for staff registry facts. Tool results exclude "
		"email addresses; do not infer missing staff information."
	),
)
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://student2-rag:5003").rstrip("/")


def _run_tool(function, *args):
	try:
		return function(*args)
	except requests.RequestException as exc:
		raise ToolError("Staff database service is unavailable") from exc
	except ValueError as exc:
		raise ToolError(str(exc)) from exc


def _call_rag_service(path: str, payload: dict):
	try:
		response = requests.post(f"{RAG_SERVICE_URL}{path}", json=payload, timeout=150)
		response.raise_for_status()
		result = response.json()
	except requests.RequestException as exc:
		raise ToolError("RAG service is unavailable") from exc
	if not isinstance(result, dict) or result.get("status") == "error":
		raise ToolError("RAG operation failed")
	return result


@mcp.tool()
def get_staff_count() -> dict[str, int]:
	"""Count all staff records in the registry."""
	return _run_tool(staff_count)


@mcp.tool()
def list_staff(department: str = "") -> list[dict]:
	"""List staff names and work classifications, optionally by department."""
	return _run_tool(staff_directory, department)


@mcp.tool()
def get_staff_member(staff_id: int) -> dict:
	"""Retrieve one staff member by ID without exposing their email address."""
	return _run_tool(staff_member, staff_id)


@mcp.tool()
def get_employment_summary() -> dict[str, dict[str, int]]:
	"""Summarize staff counts by department and employment type."""
	return _run_tool(employment_summary)


@mcp.tool()
def refresh_corpus() -> dict:
	"""Refresh the local RAG corpus from the current staff registry."""
	return _call_rag_service("/refresh", {"caller": "mcp"})


@mcp.tool()
def retrieve_context(query: str, k: int = 5) -> dict:
	"""Retrieve staff registry evidence relevant to a query."""
	return _call_rag_service("/retrieve", {"query": query, "k": k, "caller": "mcp"})


@mcp.tool()
def answer_question(query: str, k: int = 5) -> dict:
	"""Answer a staff question from retrieved evidence with citations."""
	return _call_rag_service("/answer", {"query": query, "k": k, "caller": "mcp"})


if __name__ == "__main__":
	mcp.run(
		transport="streamable-http",
		host="0.0.0.0",
		port=int(os.getenv("PORT", "8000")),
		stateless_http=True,
		json_response=True,
	)
