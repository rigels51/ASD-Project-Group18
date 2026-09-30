import json
import os

from flask import Blueprint, request
import requests

from services.llm_client import OLLAMA_MODEL, call_architecture_agent, create_chat_completion
from services.database_api import get_staff
from services.mcp_client import ALLOWED_TOOLS, call_staff_tool
from services.prompt_loader import load_prompt
from services.rag_api import call_rag_service, rag_mode_is_enabled


ai_mode_bp = Blueprint("ai_mode", __name__)


def _staff_context():
    staff = get_staff()
    department_counts = {}
    employment_counts = {}
    for member in staff:
        department = member["department"]
        employment_type = member["employment_type"]
        department_counts[department] = department_counts.get(department, 0) + 1
        employment_counts[employment_type] = employment_counts.get(employment_type, 0) + 1

    return (
        "Staff data retrieved from the database service. Use only this data for "
        "staff-related answers; if the answer is not present, say so.\n"
        f"Exact total staff: {len(staff)}\n"
        f"Exact staff count by department: {json.dumps(department_counts)}\n"
        f"Exact staff count by employment type: {json.dumps(employment_counts)}\n"
        f"{json.dumps(staff, indent=2)}"
    )


@ai_mode_bp.get("/mcp/tools")
def list_mcp_tools():
    if not _mcp_is_enabled():
        return {"error": "MCP mode is disabled."}, 503
    return {"tools": sorted(ALLOWED_TOOLS)}, 200


@ai_mode_bp.post("/mcp/call")
def call_mcp_tool():
    if not _mcp_is_enabled():
        return {"error": "MCP mode is disabled."}, 503
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"error": "A JSON request body is required."}, 400

    tool_name = payload.get("tool")
    arguments = payload.get("arguments", {})
    if tool_name not in ALLOWED_TOOLS:
        return {"error": "Unknown staff MCP tool."}, 400
    if not isinstance(arguments, dict):
        return {"error": "Tool arguments must be a JSON object."}, 400

    if tool_name == "get_staff_member":
        staff_id = arguments.get("staff_id")
        if not isinstance(staff_id, int) or isinstance(staff_id, bool) or staff_id < 1:
            return {"error": "staff_id must be a positive integer."}, 400
        arguments = {"staff_id": staff_id}
    elif tool_name == "list_staff":
        department = arguments.get("department", "")
        if not isinstance(department, str) or len(department) > 100:
            return {"error": "department must be a string of at most 100 characters."}, 400
        arguments = {"department": department}
    elif tool_name in {"retrieve_context", "answer_question"}:
        query = arguments.get("query")
        k = arguments.get("k", 5)
        if not isinstance(query, str) or not query.strip() or len(query) > 1000:
            return {"error": "query must contain 1 to 1000 characters."}, 400
        if not isinstance(k, int) or isinstance(k, bool) or not 1 <= k <= 10:
            return {"error": "k must be an integer between 1 and 10."}, 400
        arguments = {"query": query.strip(), "k": k}
    elif arguments:
        return {"error": "This tool does not accept arguments."}, 400

    try:
        return {"tool": tool_name, "result": call_staff_tool(tool_name, arguments)}, 200
    except Exception as exc:
        return {"error": f"MCP tool call failed: {exc}"}, 503


def _mcp_is_enabled() -> bool:
    return os.getenv("MCP_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


@ai_mode_bp.post("/rag/refresh")
def refresh_rag_corpus():
    if not rag_mode_is_enabled(request):
        return {"status": "error", "error": "RAG mode is disabled."}, 403
    try:
        return call_rag_service("/refresh", {"caller": "student-2"}), 200
    except (requests.RequestException, ValueError) as exc:
        return {"status": "error", "error": f"RAG service request failed: {exc}"}, 503


@ai_mode_bp.post("/rag/answer")
def answer_with_rag():
    if not rag_mode_is_enabled(request):
        return {"status": "error", "error": "RAG mode is disabled."}, 403
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = request.form
    question = payload.get("question", payload.get("query", ""))
    if not isinstance(question, str) or not question.strip() or len(question) > 1000:
        return {"status": "error", "error": "Question must contain 1 to 1000 characters."}, 400
    try:
        result = call_rag_service(
            "/answer",
            {"query": question.strip(), "k": 5, "caller": "student-2"},
        )
        return result, 200
    except (requests.RequestException, ValueError) as exc:
        return {"status": "error", "error": f"RAG service request failed: {exc}"}, 503


@ai_mode_bp.post("/rag/retrieve")
def retrieve_rag_context():
    if not rag_mode_is_enabled(request):
        return {"status": "error", "error": "RAG mode is disabled."}, 403
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = request.form
    query = payload.get("query", payload.get("question", ""))
    k = payload.get("k", 5)
    if not isinstance(query, str) or not query.strip() or len(query) > 1000:
        return {"status": "error", "error": "Query must contain 1 to 1000 characters."}, 400
    if isinstance(k, str) and k.isdigit():
        k = int(k)
    if not isinstance(k, int) or isinstance(k, bool) or not 1 <= k <= 10:
        return {"status": "error", "error": "k must be an integer between 1 and 10."}, 400
    try:
        result = call_rag_service(
            "/retrieve",
            {"query": query.strip(), "k": k, "caller": "student-2"},
        )
        return result, 200
    except (requests.RequestException, ValueError) as exc:
        return {"status": "error", "error": f"RAG service request failed: {exc}"}, 503


@ai_mode_bp.post("/ask")
def ask_local_agent():
    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400

    try:
        staff_context = _staff_context()
        answer = create_chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a concise staff registry assistant. Answer in one "
                        "short paragraph unless asked otherwise. Use only the supplied "
                        "staff data for staff-related questions. Do not invent records."
                    ),
                },
                {
                    "role": "user",
                    "content": f"{staff_context}\n\nUser question:\n{question}",
                },
            ],
            max_tokens=200,
            temperature=0.2,
            model=OLLAMA_MODEL,
        )
        return f"<p>{answer}</p>", 200
    except Exception as exc:
        return (
            "<p>Local AI agent request failed. "
            "Check that Ollama is running and that qwen2.5:0.5b is installed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@ai_mode_bp.post("/ask-with-context")
def ask_with_context():
    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400

    try:
        system_prompt = load_prompt("service/implementation/system_prompt.txt")
        task_prompt = load_prompt("service/implementation/task_prompt.txt")
        context_prompt = load_prompt("service/implementation/context_prompt.txt")
        staff_context = _staff_context()

        final_prompt = f"""
{task_prompt}

{context_prompt}

    {staff_context}

User Question:

{question}
"""

        answer = create_chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_prompt},
            ],
            max_tokens=300,
            temperature=0.2,
            model=OLLAMA_MODEL,
        )
        return f"<p>{answer}</p>", 200
    except Exception as exc:
        return (
            "<p>Context-aware request failed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@ai_mode_bp.post("/pattern-selection")
def pattern_selection():
    architecture_request = request.form.get("architecture_request", "").strip()

    if not architecture_request:
        return "<p>Architecture request is required.</p>", 400

    try:
        answer = call_architecture_agent(
            "architecture_system_prompt.txt",
            "pattern_selection_prompt.txt",
            architecture_request,
        )
        return f"<pre>{answer}</pre>", 200
    except Exception as exc:
        return (
            "<p>Pattern selection request failed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@ai_mode_bp.post("/architecture-review")
def architecture_review():
    architecture_request = request.form.get("architecture_request", "").strip()

    if not architecture_request:
        return "<p>Architecture request is required.</p>", 400

    try:
        answer = call_architecture_agent(
            "architecture_system_prompt.txt",
            "architecture_task_prompt.txt",
            architecture_request,
        )
        return f"<pre>{answer}</pre>", 200
    except Exception as exc:
        return (
            "<p>Architecture review request failed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@ai_mode_bp.post("/adr-review")
def adr_review():
    architecture_request = request.form.get("architecture_request", "").strip()

    if not architecture_request:
        return "<p>ADR text is required.</p>", 400

    try:
        answer = call_architecture_agent(
            "architecture_system_prompt.txt",
            "adr_review_prompt.txt",
            architecture_request,
        )
        return f"<pre>{answer}</pre>", 200
    except Exception as exc:
        return (
            "<p>ADR review request failed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )