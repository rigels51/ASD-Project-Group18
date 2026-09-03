import os

import requests


DATABASE_SERVICE_URL = os.getenv(
    "ASSESSMENT_DATABASE_SERVICE_URL", "http://assessment-database-service:5022"
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