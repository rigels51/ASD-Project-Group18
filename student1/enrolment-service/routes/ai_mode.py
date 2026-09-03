from flask import Blueprint, request

from services.database_api import get_students
from services.llm_client import OLLAMA_MODEL, call_architecture_agent, create_chat_completion
from services.prompt_loader import load_prompt


ai_mode_bp = Blueprint("ai_mode", __name__)


def build_student_records_context():
    students = get_students()
    return {
        "student_count": len(students),
        "students": students,
    }


@ai_mode_bp.post("/ask")
def ask_local_agent():
    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400

    try:
        context = build_student_records_context()
        student_data = context["students"]
        records_text = "\n".join(
            f"{student['student_id']} | {student['name']} | {student['course']} | {student['year_level']} | {student['status']} | GPA {student['gpa']} | {student['email']} | {student['phone']}"
            for student in student_data
        )
        answer = create_chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are the AI records assistant for a university student records system. "
                        "Use only the provided student data. Answer clearly and briefly in 2-5 sentences. "
                        "If the information is not present, say so plainly.\n\nSTUDENT DATA:\n"
                        + records_text
                    ),
                },
                {"role": "user", "content": question},
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
        student_data = get_students()
        records_text = "\n".join(
            f"{student['student_id']} | {student['name']} | {student['course']} | {student['year_level']} | {student['status']} | GPA {student['gpa']} | {student['email']} | {student['phone']}"
            for student in student_data
        )

        final_prompt = f"""
{task_prompt}

{context_prompt}

Current student records:
{records_text}

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