import os

import requests


DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://127.0.0.1:5002")


def get_students():
    response = requests.get(f"{DATABASE_SERVICE_URL}/students", timeout=5)
    response.raise_for_status()
    return response.json()


def get_student_by_id_response(student_id):
    return requests.get(f"{DATABASE_SERVICE_URL}/students/{student_id}", timeout=5)


def get_students_by_subject_response(subject_code):
    return requests.get(
        f"{DATABASE_SERVICE_URL}/students/by-subject",
        params={"subject_code": subject_code},
        timeout=5,
    )


def search_students(query):
    response = requests.get(
        f"{DATABASE_SERVICE_URL}/students/search",
        params={"query": query},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def create_student(payload):
    response = requests.post(
        f"{DATABASE_SERVICE_URL}/students",
        json=payload,
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def update_student(student_id, payload):
    response = requests.put(
        f"{DATABASE_SERVICE_URL}/students/{student_id}",
        json=payload,
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def delete_student(student_id):
    response = requests.delete(f"{DATABASE_SERVICE_URL}/students/{student_id}", timeout=5)
    response.raise_for_status()
    return response.json()