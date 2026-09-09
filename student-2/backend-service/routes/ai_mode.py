import json

from flask import Blueprint, request

from services.llm_client import OLLAMA_MODEL, call_architecture_agent, create_chat_completion
from services.database_api import get_staff
from services.prompt_loader import load_prompt


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