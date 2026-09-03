import os
import sqlite3
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from openai import OpenAI

# ============================= Agents Env Setup =============================
ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

PROMPT_DIR = Path(__file__).with_name("prompts")
DATABASE_NAME = Path(__file__).with_name("enrolment.db")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
IMPLEMENTATION_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
REVIEW_MODEL = os.getenv("OLLAMA_REVIEW_MODEL", "llama3.1:8b")

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5001")
DATABASE_BASE_URL = os.getenv("DATABASE_BASE_URL", "http://127.0.0.1:5002")

# ==================================== Plan ====================================
PLAN = {
    "goal": "Validate the Student Records management app using a local multi-agent workflow",
    "db_plan": [
        "Check student data quality (expected student record fields and valid values)",
        "Check course and search queries return matching students",
    ],
    "endpoints_plan": [
        "GET /students - list all student records",
        "GET /students/by-id - fetch one student by ID",
        "GET /students/search - search by name or ID",
        "GET /students/by-subject - filter by course",
        "POST /ask-with-context - answer questions from the live student dataset",
    ],
}


# =============================== Model Call Helper ================================
def call_model(model_name, system_prompt, user_prompt, max_tokens=256):
    try:
        client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", timeout=180.0)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.1,
        )

        content = response.choices[0].message.content
        if content and content.strip():
            return content.strip(), None

        return "No response generated.", None
    except Exception as exc:
        return None, f"{model_name} unavailable or timed out ({exc})"


# ================================ Observe: Database ================================
def validate_student(student):
    required_fields = {
        "student_id": "string/ID",
        "name": "student name",
        "course": "course name",
        "year_level": "year level",
        "email": "email address",
        "gpa": "GPA number",
        "status": "student status",
    }

    for field, label in required_fields.items():
        if field not in student or student[field] in (None, ""):
            return False, f"{label} is required"

    if not isinstance(student["student_id"], str) or not student["student_id"].strip():
        return False, "student_id must be a non-empty string"

    if not isinstance(student["name"], str) or not student["name"].strip():
        return False, "name is required"

    if not isinstance(student["course"], str) or not student["course"].strip():
        return False, "course is required"

    if not isinstance(student["year_level"], str) or not student["year_level"].strip():
        return False, "year_level is required"

    email = str(student["email"]).strip()
    if "@" not in email or "." not in email:
        return False, "email must be valid"

    try:
        gpa = float(student["gpa"])
    except (TypeError, ValueError):
        return False, "gpa must be numeric"

    if gpa < 0 or gpa > 4:
        return False, "gpa must be between 0.00 and 4.00"

    if student["status"] not in {"Enrolled", "On Leave", "Graduated"}:
        return False, "status must be Enrolled, On Leave, or Graduated"

    return True, "ok"


def fetch_database_students():
    try:
        response = requests.get(f"{DATABASE_BASE_URL}/students", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        if DATABASE_NAME.exists():
            conn = sqlite3.connect(DATABASE_NAME)
            conn.row_factory = sqlite3.Row
            students = conn.execute("SELECT * FROM students").fetchall()
            conn.close()
            return [dict(row) for row in students]
        raise


def observe_data_quality():
    students = fetch_database_students()

    if not students:
        return False, "No student records were returned"

    if len(students) < 10:
        return False, f"Expected at least 10 students, found {len(students)}"

    all_ok = True
    for student in students:
        ok, msg = validate_student(student)
        status = "OK" if ok else f"FAIL: {msg}"
        print(f"  Checked student_id={student.get('student_id')} -> {status}")
        if not ok:
            all_ok = False

    if not all_ok:
        return False, "One or more student records failed validation"

    return True, "Data validation passed"


def observe_subject_search(course_name):
    try:
        response = requests.get(
            f"{DATABASE_BASE_URL}/students/by-subject",
            params={"subject_code": course_name},
            timeout=5,
        )
        if response.status_code == 404:
            return False, f"No students found for course {course_name}"
        response.raise_for_status()
        students = response.json()
    except requests.RequestException as exc:
        return False, f"Course search failed: {exc}"

    if not students:
        return False, f"No students found for course {course_name}"

    for student in students:
        status = "OK" if student.get("course") == course_name else f"FAIL: unexpected course {student.get('course')}"
        print(f"  Checked student_id={student.get('student_id')} -> {status}")
        if student.get("course") != course_name:
            return False, f"Unexpected course found: {student.get('course')}"

    return True, f"Course search validation passed for {course_name}"


def get_sample_student():
    students = fetch_database_students()
    if not students:
        return None
    return students[0]["student_id"], students[0]["course"]


# ============================= Observe: Live Endpoints ==============================
def observe_live_endpoints(sample_student):
    results = []
    student_id, course_name = sample_student if sample_student else (None, None)

    def check(label, method, url, expected_status=200, **kwargs):
        try:
            response = requests.request(method, url, timeout=10, **kwargs)
            content_ok = bool(response.text and response.text.strip())
            passed = response.status_code == expected_status and content_ok
            line = f"{label} -> HTTP {response.status_code}, content_ok={content_ok}, passed={passed}"
        except Exception as exc:
            passed = False
            line = f"{label} -> error: {exc}"
        print(f"  Checked {line}")
        results.append({"label": label, "status": response.status_code if 'response' in locals() else None, "passed": passed, "detail": line})
        return passed

    check("/students", "GET", f"{APP_BASE_URL}/students")

    if student_id is not None:
        check("/students/by-id", "GET", f"{APP_BASE_URL}/students/by-id?student_id={student_id}")
        check("/students/search", "GET", f"{APP_BASE_URL}/students/search?query={student_id}")
    else:
        skipped_id = "/students/<student_id> -> skipped: no sample student found"
        skipped_search = "/students/search -> skipped: no sample student found"
        print(f"  Checked {skipped_id}")
        print(f"  Checked {skipped_search}")
        results.extend([skipped_id, skipped_search])

    if course_name is not None:
        check("/students/by-subject", "GET", f"{APP_BASE_URL}/students/by-subject?subject_code={course_name}")
    else:
        skipped_subject = "/students/by-subject -> skipped: no sample student found"
        print(f"  Checked {skipped_subject}")
        results.append(skipped_subject)

    ai_ok = check(
        "/ask-with-context",
        "POST",
        f"{APP_BASE_URL}/ask-with-context",
        data={"question": "Which students are currently on leave?"},
    )

    if not ai_ok:
        print("  AI validation failed: the context-aware route did not return a usable answer.")

    return results, ai_ok


def ask_student_records_agent(question: str) -> tuple[str | None, Optional[str]]:
    """Ask the app's AI route and return a plain response plus optional error."""
    try:
        response = requests.post(
            f"{APP_BASE_URL}/ask-with-context",
            data={"question": question},
            timeout=25,
        )
        if response.ok:
            return response.text.strip(), None
        return None, f"AI route returned status {response.status_code}: {response.text[:200]}"
    except requests.RequestException as exc:
        system_prompt = (
            "You are a helpful university records assistant. Use only the current student dataset "
            "provided by the app. Give concise, factual answers and state if information is missing."
        )
        answer, error = call_model(
            IMPLEMENTATION_MODEL,
            system_prompt,
            question,
            max_tokens=180,
        )
        if error:
            return None, f"Local model fallback failed: {error}"
        return answer, None


def run_agentic_loop():
    print("=== Student Records agentic loop ===")
    print("Goal:", PLAN["goal"])

    ok, message = observe_data_quality()
    print(f"Data quality: {message}")
    if not ok:
        return {"status": "failed", "message": message}

    sample_student = get_sample_student()
    if sample_student:
        ok, message = observe_subject_search(sample_student[1])
        print(f"Course search: {message}")
        if not ok:
            return {"status": "failed", "message": message}

    results, ai_ok = observe_live_endpoints(sample_student)
    print("Endpoint checks completed.")
    if not ai_ok:
        return {
            "status": "failed",
            "message": "The context-aware AI endpoint did not return a usable answer",
            "results": results,
            "sample_student": sample_student,
        }
    return {"status": "passed", "results": results, "sample_student": sample_student}


# TASK 2: ======================== Implementation & Review Agents ===========================

def load_prompt(filename):
    prompt_path = PROMPT_DIR / filename
    return prompt_path.read_text(encoding="utf-8").strip()

# TASK 2: Implement the implementation-agent and review-agent advice
# functions. Each must load its task/system prompt files, substitute the
# evidence placeholders, and call call_model() with the correct model,
# system prompt, task prompt, and max_tokens.
def get_implementation_agent_advice(observe_message):
    # TODO: Load "implementation_task_prompt.txt" and replace the
    #       "{{VALIDATION_EVIDENCE}}" placeholder with observe_message.
    implementation_task_prompt = load_prompt("implementation_task_prompt.txt").replace("{{VALIDATION_EVIDENCE}}", observe_message)

    # TODO: Call call_model() using IMPLEMENTATION_MODEL, the loaded
    #       "implementation_system_prompt.txt", the task prompt, and
    #       max_tokens=120. Return its result.
    return call_model(IMPLEMENTATION_MODEL, load_prompt("implementation_system_prompt.txt"), implementation_task_prompt, max_tokens=120)


def get_review_agent_advice(implementation_message, observe_message):
    # TODO: Load "review_task_prompt.txt" and replace both the
    #       "{{IMPLEMENTATION_RECOMMENDATION}}" and "{{VALIDATION_EVIDENCE}}"
    #       placeholders.

    # TODO: Call call_model() using REVIEW_MODEL, the loaded
    #       "review_system_prompt.txt", the task prompt, and
    #       max_tokens=150. Return its result.
    
    review_task_prompt = load_prompt("review_task_prompt.txt").replace("{{IMPLEMENTATION_RECOMMENDATION}}", implementation_message).replace("{{VALIDATION_EVIDENCE}}", observe_message)
    return call_model(REVIEW_MODEL, load_prompt("review_system_prompt.txt"), review_task_prompt, max_tokens=150)


# =============================== Human Review & Adapt ================================
def human_review():
    print()
    print("HUMAN REVIEW")
    print("1 - Accept")
    print("2 - Partially Accept")
    print("3 - Reject")

    decision = input("Decision: ").strip()

    if decision == "1":
        return "Accept"

    if decision == "2":
        return "Partially Accept"

    return "Reject"


def adapt(decision):
    print()

    if decision == "Accept":
        print(
            "ADAPT: Apply recommendation and rerun validation."
        )

    elif decision == "Partially Accept":
        print(
            "ADAPT: Apply selected recommendations and "
            "rerun validation."
        )

    else:
        print(
            "ADAPT: Keep current implementation and "
            "document rationale."
        )


# ================================= Main / Loop Entry ================================
def main():
    print("=" * 60)
    print("ASD LAB 02 AGENTIC LOOP")
    print("=" * 60)

    print()
    print("PLAN")
    print(PLAN)

    print()
    print("ACT")
    print("Check local database records")

    print()
    print("OBSERVE: Database Check")
    ok_data, msg_data = observe_data_quality()
    print(msg_data)

    sample_student = get_sample_student()
    sample_subject_code = sample_student[1] if sample_student else None

    print()
    print("OBSERVE: Subject Search Check")
    subject_results = []
    if sample_subject_code:
        ok, msg = observe_subject_search(sample_subject_code)
        subject_results.append(msg)
    else:
        subject_results.append("Course search skipped: no sample student found")

    msg_subject = "; ".join(subject_results)    
    print(msg_subject)

    print()
    print("OBSERVE: Live Endpoint Check")
    live_results, ai_ok = observe_live_endpoints(sample_student)

    observe_message = (
        f"{msg_data}. "
        f"{msg_subject}. "
        f"Live endpoint checks: " + "; ".join(result["detail"] for result in live_results)
    )

    print()
    print("IMPLEMENTATION AGENT")
    print(f"Model: {IMPLEMENTATION_MODEL}")

    implementation_advice, implementation_error = (
        get_implementation_agent_advice(
            observe_message
        )
    )

    if implementation_advice:
        print()
        print(implementation_advice)
    else:
        print()
        print(implementation_error)
        implementation_advice = (
            "Implementation agent unavailable."
        )

    print()
    print("REVIEW AGENT")
    print(f"Model: {REVIEW_MODEL}")

    review_advice, review_error = (
        get_review_agent_advice(
            implementation_advice,
            observe_message
        )
    )

    if review_advice:
        print()
        print(review_advice)
    else:
        print()
        print(review_error)

    print()
    print("HUMAN DECISION")

    decision = human_review()

    print()
    print(f"Decision: {decision}")

    adapt(decision)

    print()
    print("LOOP COMPLETE")


if __name__ == "__main__":
    main()