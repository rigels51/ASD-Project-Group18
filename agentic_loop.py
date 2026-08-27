import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI


# =========================================================
# ENVIRONMENT
# =========================================================

ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

PROMPT_DIR = Path(__file__).with_name("prompts")

DATABASE_SERVICE_URL = os.getenv(
    "DATABASE_SERVICE_URL",
    "http://127.0.0.1:5002"
)

ENROLMENT_SERVICE_URL = os.getenv(
    "ENROLMENT_SERVICE_URL",
    "http://127.0.0.1:5001"
)

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434/v1"
)

IMPLEMENTATION_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:0.5b"
)

REVIEW_MODEL = os.getenv(
    "OLLAMA_REVIEW_MODEL",
    "llama3.1:8b"
)


# =========================================================
# PLAN
# =========================================================

PLAN = {
    "goal": (
        "Validate Course and Enrollment Management "
        "using a local Agentic AI workflow"
    ),

    "database_plan": [
        "Check that at least 10 course records exist",
        "Check that at least 10 enrolment records exist",
        "Validate required course fields",
        "Validate required enrolment fields",
    ],

    "endpoint_plan": [
        "GET /courses",
        "GET /enrolments",
        "POST /ask",
        "POST /ask-with-context",
    ],
}


# =========================================================
# OBSERVE - DATABASE DATA
# =========================================================

def get_courses():
    response = requests.get(
        f"{DATABASE_SERVICE_URL}/courses",
        timeout=5
    )

    response.raise_for_status()

    return response.json()


def get_enrolments():
    response = requests.get(
        f"{DATABASE_SERVICE_URL}/enrolments",
        timeout=5
    )

    response.raise_for_status()

    return response.json()


def validate_course(course):
    required_fields = [
        "course_id",
        "course_code",
        "course_name",
        "credits",
        "capacity",
    ]

    for field in required_fields:
        if field not in course:
            return False, f"Missing field: {field}"

    if not course["course_code"]:
        return False, "course_code is required"

    if not course["course_name"]:
        return False, "course_name is required"

    if course["credits"] <= 0:
        return False, "credits must be greater than 0"

    if course["capacity"] <= 0:
        return False, "capacity must be greater than 0"

    return True, "ok"


def validate_enrolment(enrolment):
    required_fields = [
        "enrolment_id",
        "student_id",
        "course_id",
        "status",
    ]

    for field in required_fields:
        if field not in enrolment:
            return False, f"Missing field: {field}"

    if not enrolment["student_id"]:
        return False, "student_id is required"

    if not enrolment["course_id"]:
        return False, "course_id is required"

    if not enrolment["status"]:
        return False, "status is required"

    return True, "ok"


def observe_data_quality():
    try:
        courses = get_courses()
        enrolments = get_enrolments()

    except requests.RequestException as exc:
        return False, (
            f"Database-service unavailable: {exc}"
        )

    all_ok = True

    print(f"  Courses found: {len(courses)}")

    if len(courses) < 10:
        print("  FAIL: fewer than 10 courses")
        all_ok = False

    for course in courses:
        ok, msg = validate_course(course)

        status = "OK" if ok else f"FAIL: {msg}"

        print(
            f"  Course {course.get('course_code')} -> {status}"
        )

        if not ok:
            all_ok = False


    print(f"  Enrolments found: {len(enrolments)}")

    if len(enrolments) < 10:
        print("  FAIL: fewer than 10 enrolments")
        all_ok = False

    for enrolment in enrolments:
        ok, msg = validate_enrolment(enrolment)

        status = "OK" if ok else f"FAIL: {msg}"

        print(
            f"  Enrolment "
            f"{enrolment.get('enrolment_id')} -> {status}"
        )

        if not ok:
            all_ok = False


    if all_ok:
        return True, (
            "Course and enrolment data validation passed"
        )

    return False, (
        "One or more database validation checks failed"
    )


# =========================================================
# OBSERVE - COURSE AVAILABILITY
# =========================================================

def observe_course_availability():
    try:
        courses = get_courses()
        enrolments = get_enrolments()

    except requests.RequestException as exc:
        return False, (
            f"Unable to check course availability: {exc}"
        )

    results = []

    for course in courses:

        active_enrolments = sum(
            1
            for enrolment in enrolments
            if enrolment["course_id"] == course["course_id"]
            and enrolment["status"].lower() == "active"
        )

        available_seats = (
            course["capacity"] - active_enrolments
        )

        line = (
            f"{course['course_code']}: "
            f"capacity={course['capacity']}, "
            f"active={active_enrolments}, "
            f"available={available_seats}"
        )

        print(f"  {line}")

        results.append(line)

    return True, "; ".join(results)


# =========================================================
# OBSERVE - LIVE ENDPOINTS
# =========================================================

def observe_live_endpoints():
    results = []

    def check(label, method, url, **kwargs):

        try:
            response = requests.request(
                method,
                url,
                timeout=30,
                **kwargs
            )

            content_ok = bool(
                response.text
                and response.text.strip()
            )

            line = (
                f"{label} -> "
                f"HTTP {response.status_code}, "
                f"content_ok={content_ok}"
            )

        except Exception as exc:
            line = f"{label} -> error: {exc}"

        print(f"  Checked {line}")

        results.append(line)


    # Database APIs
    check(
        "/courses",
        "GET",
        f"{DATABASE_SERVICE_URL}/courses"
    )

    check(
        "/enrolments",
        "GET",
        f"{DATABASE_SERVICE_URL}/enrolments"
    )


    # Basic AI Mode
    check(
        "/ask",
        "POST",
        f"{ENROLMENT_SERVICE_URL}/ask",
        data={
            "question":
                "What does the Course and Enrollment "
                "Management system do?"
        }
    )


    # AI with database context
    check(
        "/ask-with-context",
        "POST",
        f"{ENROLMENT_SERVICE_URL}/ask-with-context",
        data={
            "question":
                "What courses have available seats?"
        }
    )

    return results


# =========================================================
# MODEL CALL
# =========================================================

def call_model(
    model_name,
    system_prompt,
    user_prompt,
    max_tokens=120
):

    try:
        client = OpenAI(
            base_url=OLLAMA_BASE_URL,
            api_key="ollama",
            timeout=180.0
        )

        response = client.chat.completions.create(
            model=model_name,

            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],

            max_tokens=max_tokens,
            temperature=0.1
        )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if content and content.strip():
            return content.strip(), None

        return "No response generated.", None

    except Exception as exc:

        return None, (
            f"{model_name} unavailable or "
            f"timed out ({exc})"
        )


# =========================================================
# PROMPTS
# =========================================================

def load_prompt(filename):

    prompt_path = PROMPT_DIR / filename

    return prompt_path.read_text(
        encoding="utf-8"
    ).strip()


# =========================================================
# IMPLEMENTATION AGENT
# =========================================================

def get_implementation_agent_advice(
    observe_message
):

    implementation_task_prompt = (
        load_prompt(
            "implementation_task_prompt.txt"
        )
        .replace(
            "{{VALIDATION_EVIDENCE}}",
            observe_message
        )
    )

    return call_model(
        IMPLEMENTATION_MODEL,

        load_prompt(
            "implementation_system_prompt.txt"
        ),

        implementation_task_prompt,

        max_tokens=120
    )


# =========================================================
# REVIEW AGENT
# =========================================================

def get_review_agent_advice(
    implementation_message,
    observe_message
):

    review_task_prompt = (
        load_prompt(
            "review_task_prompt.txt"
        )

        .replace(
            "{{IMPLEMENTATION_RECOMMENDATION}}",
            implementation_message
        )

        .replace(
            "{{VALIDATION_EVIDENCE}}",
            observe_message
        )
    )

    return call_model(
        REVIEW_MODEL,

        load_prompt(
            "review_system_prompt.txt"
        ),

        review_task_prompt,

        max_tokens=150
    )


# =========================================================
# HUMAN REVIEW
# =========================================================

def human_review():

    print()

    print("HUMAN REVIEW")

    print("1 - Accept")
    print("2 - Partially Accept")
    print("3 - Reject")

    decision = input(
        "Decision: "
    ).strip()

    if decision == "1":
        return "Accept"

    if decision == "2":
        return "Partially Accept"

    return "Reject"


# =========================================================
# ADAPT
# =========================================================

def adapt(decision):

    print()

    if decision == "Accept":

        print(
            "ADAPT: Apply recommendation "
            "and rerun validation."
        )

    elif decision == "Partially Accept":

        print(
            "ADAPT: Apply selected recommendations "
            "and rerun validation."
        )

    else:

        print(
            "ADAPT: Keep current implementation "
            "and document rationale."
        )


# =========================================================
# MAIN LOOP
# =========================================================

def main():

    print("=" * 65)

    print(
        "COURSE & ENROLLMENT MANAGEMENT "
        "AGENTIC AI LOOP"
    )

    print("=" * 65)


    # ---------------- PLAN ----------------

    print()
    print("PLAN")

    print(
        "Validate Course and Enrollment "
        "Management microservices."
    )

    print(PLAN)


    # ---------------- ACT ----------------

    print()
    print("ACT")

    print(
        "Run database, API, availability "
        "and AI validation checks."
    )


    # ---------------- OBSERVE: DATA ----------------

    print()
    print("OBSERVE: Database Check")

    ok_data, msg_data = (
        observe_data_quality()
    )

    print(msg_data)


    # ---------------- OBSERVE: AVAILABILITY ----------------

    print()
    print("OBSERVE: Course Availability")

    ok_availability, msg_availability = (
        observe_course_availability()
    )


    # ---------------- OBSERVE: ENDPOINTS ----------------

    print()
    print("OBSERVE: Live Endpoint Check")

    live_results = (
        observe_live_endpoints()
    )


    # Combine evidence
    observe_message = (
        f"Database validation: {msg_data}. "
        f"Course availability: "
        f"{msg_availability}. "
        f"Live endpoint checks: "
        + "; ".join(live_results)
    )


    # ---------------- IMPLEMENTATION AGENT ----------------

    print()
    print("IMPLEMENTATION AGENT")

    print(
        f"Model: {IMPLEMENTATION_MODEL}"
    )

    (
        implementation_advice,
        implementation_error
    ) = get_implementation_agent_advice(
        observe_message
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


    # ---------------- REVIEW AGENT ----------------

    print()
    print("REVIEW AGENT")

    print(
        f"Model: {REVIEW_MODEL}"
    )

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


    # ---------------- HUMAN DECISION ----------------

    print()
    print("HUMAN DECISION")

    decision = human_review()

    print()
    print(
        f"Decision: {decision}"
    )


    # ---------------- ADAPT ----------------

    adapt(decision)


    print()
    print("LOOP COMPLETE")


if __name__ == "__main__":
    main()