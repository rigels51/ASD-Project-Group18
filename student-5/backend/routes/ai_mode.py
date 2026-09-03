import re

from flask import Blueprint, request
import requests

from services.database_api import (
    get_assessments,
    get_grades,
    get_grades_by_student_response,
    get_grades_by_course_response,
)
from services.llm_client import create_chat_completion, OLLAMA_MODEL
from services.prompt_loader import load_prompt


ai_mode_bp = Blueprint("assessment_ai_mode", __name__)

COURSE_CODE_PATTERN = re.compile(r"\b[A-Z]{2,4}\d{3}\b")
STUDENT_ID_PATTERN = re.compile(r"student\s*(?:id\s*)?#?\s*(\d+)", re.IGNORECASE)


def _plan(question):
    """PLAN: work out which evidence the question needs."""
    course_match = COURSE_CODE_PATTERN.search(question.upper())
    student_match = STUDENT_ID_PATTERN.search(question)

    return {
        "course_id": course_match.group(0) if course_match else None,
        "student_id": int(student_match.group(1)) if student_match else None,
    }


def _act_and_observe(plan):
    """ACT: call the real backend/database functions. OBSERVE: collect what came back."""
    evidence_parts = []

    if plan["student_id"]:
        response = get_grades_by_student_response(plan["student_id"])
        if response.status_code == 200:
            evidence_parts.append(f"Grades for student {plan['student_id']}: {response.json()}")
        else:
            evidence_parts.append(f"No grade records found for student {plan['student_id']}.")

    if plan["course_id"]:
        response = get_grades_by_course_response(plan["course_id"])
        if response.status_code == 200:
            evidence_parts.append(f"Grades for course {plan['course_id']}: {response.json()}")
        else:
            evidence_parts.append(f"No grade records found for course {plan['course_id']}.")

        assessments = get_assessments(course_id=plan["course_id"])
        evidence_parts.append(f"Assessments for course {plan['course_id']}: {assessments}")

    if not plan["student_id"] and not plan["course_id"]:
        # Fall back to a general snapshot so the model still has grounded context.
        evidence_parts.append(f"All assessments: {get_assessments()}")
        evidence_parts.append(f"All grades: {get_grades()}")

    return "\n".join(evidence_parts)


@ai_mode_bp.post("/ask")
def ask_assessment_agent():
    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400

    try:
        # PLAN
        plan = _plan(question)

        # ACT + OBSERVE
        evidence = _act_and_observe(plan)

        # ADAPT: generate a grounded answer using the evidence gathered above.
        system_prompt = load_prompt("system_prompt.txt")
        task_prompt = load_prompt("task_prompt.txt")

        final_prompt = f"""{task_prompt}

Retrieved Evidence:
{evidence}

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
    except requests.RequestException as exc:
        return (
            "<p>Could not reach the assessment/grades data services.</p>"
            f"<pre>{exc}</pre>",
            503,
        )
    except Exception as exc:
        return (
            "<p>Assessment & Grades AI agent request failed. "
            "Check that Ollama is running and that the configured model is installed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )
