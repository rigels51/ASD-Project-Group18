"""Release 2 - post-commit CI endpoint tests for Student 5 (assessment-service backend/API).

Two endpoint functions of student-5/backend/routes/assessments.py are tested against the
REAL running containers (assessment-service :5021 -> assessment-database-service :5022):

  1. get_assessments_route     GET  /assessments
  2. create_assessment_route   POST /assessments

Run by .github/workflows/student-5.yml after every push, or locally with the stack up:
    python -m pytest student-5/tests/test_endpoints_ci.py -v
"""

import os
import uuid

import pytest
import requests

BACKEND_URL = os.getenv("ASSESSMENT_BACKEND_URL", "http://localhost:5021")
DATABASE_URL = os.getenv("ASSESSMENT_DATABASE_URL", "http://localhost:5022")
TIMEOUT = 15


def _db_assessments(**params):
    response = requests.get(f"{DATABASE_URL}/assessments", params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Endpoint 1: GET /assessments  (get_assessments_route)
# ---------------------------------------------------------------------------

class TestGetAssessments:
    def test_lists_seeded_assessments_as_html_table(self):
        response = requests.get(f"{BACKEND_URL}/assessments", timeout=TIMEOUT)
        assert response.status_code == 200
        assert "<table" in response.text
        assert response.text.count("<tr>") - 1 == len(_db_assessments())  # one row per DB record
        assert "Assignment 1 - Design Doc" in response.text

    def test_course_filter_returns_only_that_course(self):
        response = requests.get(f"{BACKEND_URL}/assessments", params={"course_id": "SEC301"}, timeout=TIMEOUT)
        assert response.status_code == 200
        assert "Security Audit Report" in response.text
        assert "Capstone Presentation" in response.text
        assert "ASD101" not in response.text

    def test_type_and_name_filters_combine(self):
        response = requests.get(f"{BACKEND_URL}/assessments",
                                params={"assessment_type": "Exam", "q": "Final"}, timeout=TIMEOUT)
        assert response.status_code == 200
        assert "Final Exam" in response.text
        assert "Practical Exam" not in response.text

    def test_no_match_shows_empty_state(self):
        response = requests.get(f"{BACKEND_URL}/assessments", params={"course_id": "ZZZ999"}, timeout=TIMEOUT)
        assert response.status_code == 200
        assert "No assessments found" in response.text


# ---------------------------------------------------------------------------
# Endpoint 2: POST /assessments  (create_assessment_route)
# ---------------------------------------------------------------------------

@pytest.fixture
def unique_name():
    name = f"CI Assessment {uuid.uuid4().hex[:8]}"
    yield name
    for row in _db_assessments(q=name):  # clean up through the backend so the DB is left as seeded
        requests.delete(f"{BACKEND_URL}/assessments/{row['assessment_id']}", timeout=TIMEOUT)


class TestCreateAssessment:
    def test_creates_assessment_and_persists_it(self, unique_name):
        response = requests.post(f"{BACKEND_URL}/assessments", data={
            "course_id": "asd101", "assessment_name": unique_name, "assessment_type": "Quiz",
            "due_date": "2026-12-01", "max_mark": "20", "weight": "5", "description": "created by CI",
        }, timeout=TIMEOUT)
        assert response.status_code == 201
        assert unique_name in response.text  # returned table includes the new row
        stored = _db_assessments(q=unique_name)
        assert len(stored) == 1
        assert stored[0]["course_id"] == "ASD101"  # course code normalised to upper case
        assert stored[0]["max_mark"] == 20 and stored[0]["weight"] == 5

    def test_missing_required_fields_rejected(self, unique_name):
        response = requests.post(f"{BACKEND_URL}/assessments",
                                 data={"course_id": "ASD101", "assessment_name": unique_name}, timeout=TIMEOUT)
        assert response.status_code == 400
        assert "required" in response.text
        assert _db_assessments(q=unique_name) == []  # nothing written

    def test_non_numeric_mark_rejected(self, unique_name):
        response = requests.post(f"{BACKEND_URL}/assessments", data={
            "course_id": "ASD101", "assessment_name": unique_name, "assessment_type": "Quiz",
            "due_date": "2026-12-01", "max_mark": "twenty", "weight": "5",
        }, timeout=TIMEOUT)
        assert response.status_code == 400
        assert "must be numbers" in response.text
        assert _db_assessments(q=unique_name) == []
