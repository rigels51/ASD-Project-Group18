"""
Pre/post-testing evidence for the Assessment & Grades Management microservices
(Student 5 — Vu Tien Thanh Nguyen).

Run against a live stack, e.g.:
    docker compose up -d
    pytest student-5/tests/test_assessment_grades_service.py -v

These tests hit the backend/API service (default: http://localhost:5021), which in
turn proxies to the database service, so a pass demonstrates the whole chain works:
frontend-facing API -> backend -> database.

NOTE: POST /grades now validates student_id against Student 1's database-service
(relationship: Student 1 -> Student 5 via student_id). When run standalone (e.g. in
CI, without student1-database on the network) that call fails and the route returns
503 rather than 201/400 — this suite does not exercise grade creation for that
reason, so it stays green in both standalone and full-stack runs.
"""

import os
import requests

BACKEND_URL = os.getenv("ASSESSMENT_BACKEND_URL", "http://localhost:5021")


def test_get_all_assessments_returns_html():
    response = requests.get(f"{BACKEND_URL}/assessments")
    assert response.status_code == 200
    assert "<table" in response.text or "No assessments found" in response.text


def test_get_single_assessment():
    response = requests.get(f"{BACKEND_URL}/assessments/1")
    assert response.status_code == 200
    assert "ASD101" in response.text or "assessment" in response.text.lower()


def test_get_assessment_not_found():
    response = requests.get(f"{BACKEND_URL}/assessments/99999")
    assert response.status_code == 404


def test_create_update_delete_assessment_roundtrip():
    create = requests.post(
        f"{BACKEND_URL}/assessments",
        data={
            "course_id": "TST999",
            "assessment_name": "Automated Test Assessment",
            "assessment_type": "Quiz",
            "due_date": "2026-12-01",
            "max_mark": "20",
            "weight": "5",
        },
    )
    assert create.status_code == 201

    # Find the new assessment id by filtering on course code.
    search = requests.get(f"{BACKEND_URL}/assessments", params={"course_id": "TST999"})
    assert search.status_code == 200

    # Clean-up is done through the database service directly since the HTML
    # response does not expose the new id in a machine-readable way here.
    db_url = os.getenv("ASSESSMENT_DATABASE_URL", "http://localhost:5022")
    raw = requests.get(f"{db_url}/assessments", params={"course_id": "TST999"}).json()
    assert len(raw) >= 1
    new_id = raw[-1]["assessment_id"]

    update = requests.put(f"{BACKEND_URL}/assessments/{new_id}", data={"weight": "10"})
    assert update.status_code == 200

    delete = requests.delete(f"{BACKEND_URL}/assessments/{new_id}")
    assert delete.status_code == 200


def test_get_all_grades():
    response = requests.get(f"{BACKEND_URL}/grades")
    assert response.status_code == 200


def test_get_grades_by_student():
    # STU-1001 matches the seeded Student 1 id format (see student-5/database/init_db.py).
    response = requests.get(f"{BACKEND_URL}/grades/student/STU-1001")
    assert response.status_code in (200, 404)


def test_get_grades_by_course():
    response = requests.get(f"{BACKEND_URL}/grades/course/ASD101")
    assert response.status_code in (200, 404)


def test_ask_ai_agent_requires_question():
    response = requests.post(f"{BACKEND_URL}/ask", data={"question": ""})
    assert response.status_code == 400


def test_ask_ai_agent_returns_answer_or_service_unavailable():
    response = requests.post(
        f"{BACKEND_URL}/ask",
        data={"question": "What did student STU-1009 score in SEC301?"},
    )
    # 200 when Ollama is reachable, 503 with a clear error message otherwise.
    assert response.status_code in (200, 503)
