import json
import re

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


def find_student_by_id(question, students):
    match = re.search(r"\bSTU-\d+\b", question, re.IGNORECASE)
    if not match:
        return None

    student_id = match.group(0).upper()
    return next(
        (student for student in students if student["student_id"].upper() == student_id),
        None,
    )


def is_valid_question(question):
    words = re.findall(r"[a-z0-9]+", question.casefold())
    if len(words) < 3:
        return False
    if len(set(words)) == 1:
        return False
    if len(set(words)) / len(words) < 0.5:
        return False
    return any(
        term in words
        for term in (
            "student",
            "students",
            "name",
            "course",
            "gpa",
            "grade",
            "status",
            "enrolled",
            "leave",
            "graduated",
            "record",
            "records",
            "who",
            "what",
            "which",
            "how",
            "list",
        )
    ) or bool(re.search(r"\bstu-\d+\b", question, re.IGNORECASE))


def deterministic_answer(question, students):
    student = find_student_by_id(question, students)
    if student:
        return f"{student['name']} ({student['student_id']})"

    normalized_question = question.casefold()
    gpa_match = re.search(
        r"(?:gpa|grade point average)\s*(?:above|over|greater than|more than|higher than|>)\s*(\d+(?:\.\d+)?)",
        normalized_question,
    )
    if gpa_match and re.search(r"who|which|list|student", normalized_question):
        threshold = float(gpa_match.group(1))
        matching_students = [
            student for student in students if float(student["gpa"]) > threshold
        ]
        if not matching_students:
            return f"No students have a GPA above {threshold:g}."
        return ", ".join(
            f"{student['name']} ({float(student['gpa']):.2f})"
            for student in matching_students
        ) + "."

    status = next(
        (
            value
            for value, phrase in (
                ("On Leave", "on leave"),
                ("Enrolled", "enrolled"),
                ("Graduated", "graduated"),
            )
            if phrase in normalized_question
        ),
        None,
    )
    course = next(
        (
            value
            for value in (
                "BS Computer Science",
                "BS Information Technology",
                "BS Cybersecurity",
                "BS Psychology",
                "BS Civil Engineering",
            )
            if value.removeprefix("BS ").casefold() in normalized_question
        ),
        None,
    )
    if status and re.search(r"who|which|list|student", normalized_question):
        matching_students = [
            student
            for student in students
            if student["status"].casefold() == status.casefold()
            and (course is None or student["course"].casefold() == course.casefold())
        ]
        scope = f" {course.removeprefix('BS ')} students" if course else " students"
        if not matching_students:
            return f"No{scope} are {status.casefold()}."
        names = ", ".join(student["name"] for student in matching_students)
        return f"{names} ({status})."

    if re.search(r"\b(how many|count|number of)\b.*\bstudents?\b", question, re.IGNORECASE):
        return f"There are {len(students)} students in the records."

    return None


@ai_mode_bp.post("/ask")
def ask_local_agent():
    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400
    if not is_valid_question(question):
        return "<p>Please enter a complete question about the student records.</p>", 400

    try:
        context = build_student_records_context()
        student_data = context["students"]
        exact_answer = deterministic_answer(question, student_data)
        if exact_answer:
            return f"<p>{exact_answer}</p>", 200

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
    if not is_valid_question(question):
        return "<p>Please enter a complete question about the student records.</p>", 400

    try:
        student_data = get_students()
        exact_answer = deterministic_answer(question, student_data)
        if exact_answer:
            return f"<p>{exact_answer}</p>", 200

        records_text = json.dumps(student_data, ensure_ascii=False, indent=2)

        final_prompt = f"""
Answer the user's question using only the student records below.
The records are the source of truth. Copy student names exactly as written.
Never invent, alter, or substitute a student's name, ID, course, status, or other value.
If the requested information cannot be determined from the records, say that it is unavailable.
Answer briefly and directly. Do not describe your reasoning or create/update/delete records.

Student records (JSON):
{records_text}

User Question:

{question}
"""

        answer = create_chat_completion(
            [
                {
                    "role": "system",
                    "content": "You are a precise student records assistant. Never guess or fabricate data.",
                },
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