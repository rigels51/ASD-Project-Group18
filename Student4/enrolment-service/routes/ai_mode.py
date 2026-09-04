from flask import Blueprint, request

from services.llm_client import (
    OLLAMA_MODEL,
    call_architecture_agent,
    create_chat_completion,
)

from services.database_api import (
    get_courses,
    get_enrolments,
)

from services.prompt_loader import load_prompt


ai_mode_bp = Blueprint("ai_mode", __name__)



@ai_mode_bp.post("/ask")
def ask_local_agent():
    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400

    try:
        answer = create_chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a university Course and Enrollment "
                        "Management assistant. "
                        "Answer clearly and briefly."
                    ),
                },
                {
                    "role": "user",
                    "content": question,
                },
            ],
            max_tokens=200,
            temperature=0.2,
            model=OLLAMA_MODEL,
        )

        return f"<p>{answer}</p>", 200

    except Exception as exc:
        return (
            "<p>Local AI agent request failed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )




@ai_mode_bp.post("/ask-with-context")
def ask_with_context():
    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400

    try:
        # database-service
        courses = get_courses()
        enrolments = get_enrolments()

        # Create course information
        course_context = []

        for course in courses:
            course_id = course["course_id"]

            active_count = sum(
                1
                for enrolment in enrolments
                if enrolment["course_id"] == course_id
                and enrolment["status"].lower() == "active"
            )

            available_seats = course["capacity"] - active_count

            course_context.append(
                {
                    "course_id": course["course_id"],
                    "course_code": course["course_code"],
                    "course_name": course["course_name"],
                    "credits": course["credits"],
                    "capacity": course["capacity"],
                    "active_enrolments": active_count,
                    "available_seats": available_seats,
                }
            )

        system_prompt = (
            "You are a university Course and Enrollment Management assistant. "
            "Answer the user's question using only the supplied database data. "
            "Do not invent courses, students, enrolments, or numbers. "
            "If the requested information is not in the data, say that it "
            "is not available. Keep the answer short and clear."
        )

        final_prompt = f"""
COURSE DATA:
{course_context}

ENROLMENT DATA:
{enrolments}

USER QUESTION:
{question}
"""

        answer = create_chat_completion(
            [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": final_prompt,
                },
            ],
            max_tokens=300,
            temperature=0.1,
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
    architecture_request = request.form.get(
        "architecture_request",
        "",
    ).strip()

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
    architecture_request = request.form.get(
        "architecture_request",
        "",
    ).strip()

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
    architecture_request = request.form.get(
        "architecture_request",
        "",
    ).strip()

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