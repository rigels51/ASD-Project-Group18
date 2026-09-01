import os

import requests


DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://database-service:5002")


def get_staff():
    response = requests.get(f"{DATABASE_SERVICE_URL}/staff", timeout=5)
    response.raise_for_status()
    return response.json()


def get_staff_by_id_response(staff_id):
    return requests.get(f"{DATABASE_SERVICE_URL}/staff/{staff_id}", timeout=5)


def get_staff_by_department_response(department):
    return requests.get(
        f"{DATABASE_SERVICE_URL}/staff/by-department",
        params={"department": department},
        timeout=5,
    )


def create_staff_response(payload):
    return requests.post(f"{DATABASE_SERVICE_URL}/staff", data=payload, timeout=5)


def update_staff_response(staff_id, payload):
    return requests.put(f"{DATABASE_SERVICE_URL}/staff/{staff_id}", data=payload, timeout=5)


def delete_staff_response(staff_id):
    return requests.delete(f"{DATABASE_SERVICE_URL}/staff/{staff_id}", timeout=5)