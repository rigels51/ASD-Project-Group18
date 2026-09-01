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