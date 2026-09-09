import os

import requests


DATABASE_SERVICE_URL = os.getenv(
    "ASSESSMENT_DATABASE_SERVICE_URL", "http://assessment-database-service:5022"
)

# ---------------------------------------------------------------------------
# Relationship fix: Student 1 -> Student 5 (student_id) and
# Student 4 -> Student 5 (course_id). Same pattern Student 4 already uses
# to reach Student 1's database-service (see
# student-4/enrolment-service/services/database_api.py).
# ---------------------------------------------------------------------------
STUDENT_SERVICE_URL = os.getenv(
    "STUDENT_SERVICE_URL", "http://student1-database:5002"
)
COURSE_SERVICE_URL = os.getenv(
    "COURSE_SERVICE_URL", "http://student4-database:5002"
)


# ---------------------------------------------------------------------------
# Assessments
# ---------------------------------------------------------------------------

def get_assessments(course_id=None, assessment_type=None, q=None):
    params = {}
    if course_id:
        params["course_id"] = course_id
    if assessment_type:
        params["assessment_type"] = assessment_type
    if q:
        params["q"] = q

    response = requests.get(f"{DATABASE_SERVICE_URL}/assessments", params=params, timeout=5)
    response.raise_for_status()
    return response.json()


def get_assessment_response(assessment_id):
    return requests.get(f"{DATABASE_SERVICE_URL}/assessments/{assessment_id}", timeout=5)


def create_assessment_response(payload):
    return requests.post(f"{DATABASE_SERVICE_URL}/assessments", json=payload, timeout=5)


def update_assessment_response(assessment_id, payload):
    return requests.put(f"{DATABASE_SERVICE_URL}/assessments/{assessment_id}", json=payload, timeout=5)


def delete_assessment_response(assessment_id):
    return requests.delete(f"{DATABASE_SERVICE_URL}/assessments/{assessment_id}", timeout=5)


# ---------------------------------------------------------------------------
# Grades
# ---------------------------------------------------------------------------

def get_grades():
    response = requests.get(f"{DATABASE_SERVICE_URL}/grades", timeout=5)
    response.raise_for_status()
    return response.json()


def get_grade_response(grade_id):
    return requests.get(f"{DATABASE_SERVICE_URL}/grades/{grade_id}", timeout=5)


def create_grade_response(payload):
    return requests.post(f"{DATABASE_SERVICE_URL}/grades", json=payload, timeout=5)


def update_grade_response(grade_id, payload):
    return requests.put(f"{DATABASE_SERVICE_URL}/grades/{grade_id}", json=payload, timeout=5)


def delete_grade_response(grade_id):
    return requests.delete(f"{DATABASE_SERVICE_URL}/grades/{grade_id}", timeout=5)


def get_grades_by_student_response(student_id):
    return requests.get(f"{DATABASE_SERVICE_URL}/grades/student/{student_id}", timeout=5)


def get_grades_by_course_response(course_id):
    return requests.get(f"{DATABASE_SERVICE_URL}/grades/course/{course_id}", timeout=5)


# ---------------------------------------------------------------------------
# Student 1 API (relationship: Student 1 -> Student 5 via student_id)
# ---------------------------------------------------------------------------

def get_student_response(student_id):
    """Look up a single student by id on Student 1's database-service."""
    return requests.get(f"{STUDENT_SERVICE_URL}/students/{student_id}", timeout=5)


def get_all_students():
    """Fetch every student from Student 1's database-service.

    Used to enrich grade rows with a name instead of a bare student_id.
    Returns {} (not raises) if Student 1's service is unreachable, so a
    grades list can still render without names rather than failing outright.
    """
    try:
        response = requests.get(f"{STUDENT_SERVICE_URL}/students", timeout=5)
        response.raise_for_status()
        return {s["student_id"].upper(): s for s in response.json()}
    except requests.RequestException:
        return {}


# ---------------------------------------------------------------------------
# Student 4 API (relationship: Student 4 -> Student 5 via course_id)
# ---------------------------------------------------------------------------

def get_all_courses():
    """Fetch every course from Student 4's database-service, keyed by
    course_code (e.g. "ASD101"), which is what Student 5's assessments
    store in their course_id field. Returns {} if unreachable.
    """
    try:
        response = requests.get(f"{COURSE_SERVICE_URL}/courses", timeout=5)
        response.raise_for_status()
        return {c["course_code"].upper(): c for c in response.json()}
    except requests.RequestException:
        return {}
