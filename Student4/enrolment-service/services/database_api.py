import os
import requests


DATABASE_SERVICE_URL = os.getenv(
    "DATABASE_SERVICE_URL",
    "http://student4-database:5002"
)

STUDENT_SERVICE_URL = os.getenv(
    "STUDENT_SERVICE_URL",
    "http://student1-database:5002"
)


# =========================================================
# COURSE API
# =========================================================

def get_courses():
    response = requests.get(
        f"{DATABASE_SERVICE_URL}/courses",
        timeout=5
    )
    response.raise_for_status()
    return response.json()


def get_course_response(course_id):
    return requests.get(
        f"{DATABASE_SERVICE_URL}/courses/{course_id}",
        timeout=5
    )


def create_course_response(data):
    return requests.post(
        f"{DATABASE_SERVICE_URL}/courses",
        json=data,
        timeout=5
    )


def update_course_response(course_id, data):
    return requests.put(
        f"{DATABASE_SERVICE_URL}/courses/{course_id}",
        json=data,
        timeout=5
    )


def delete_course_response(course_id):
    return requests.delete(
        f"{DATABASE_SERVICE_URL}/courses/{course_id}",
        timeout=5
    )


# =========================================================
# ENROLMENT API
# =========================================================

def get_enrolments():
    response = requests.get(
        f"{DATABASE_SERVICE_URL}/enrolments",
        timeout=5
    )
    response.raise_for_status()
    return response.json()


def get_enrolment_response(enrolment_id):
    return requests.get(
        f"{DATABASE_SERVICE_URL}/enrolments/{enrolment_id}",
        timeout=5
    )


def create_enrolment_response(data):
    return requests.post(
        f"{DATABASE_SERVICE_URL}/enrolments",
        json=data,
        timeout=5
    )


def update_enrolment_response(enrolment_id, data):
    return requests.put(
        f"{DATABASE_SERVICE_URL}/enrolments/{enrolment_id}",
        json=data,
        timeout=5
    )


def delete_enrolment_response(enrolment_id):
    return requests.delete(
        f"{DATABASE_SERVICE_URL}/enrolments/{enrolment_id}",
        timeout=5
    )


# =========================================================
# STUDENT 1 API
# =========================================================

def get_student_response(student_id):
    return requests.get(
        f"{STUDENT_SERVICE_URL}/students/{student_id}",
        timeout=5
    )