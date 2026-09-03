import importlib.util
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "database_service_app",
    Path(__file__).resolve().parents[1] / "database-service" / "app.py",
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class StudentRecordsApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "students.db")
        module.DATABASE_NAME = self.db_path
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                course TEXT NOT NULL,
                year_level TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                gpa REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Enrolled'
            )
            """
        )
        conn.execute(
            "INSERT INTO students (student_id, name, course, year_level, email, phone, gpa, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("STU-1001", "Rigel Rivamonte", "BS Computer Science", "3rd Year", "rigel.rivamonte@uni.edu", "0917 200 1145", 3.72, "Enrolled"),
        )
        conn.commit()
        conn.close()

        self.client = module.app.test_client()

    def tearDown(self):
        try:
            self.client.application.config["DATABASE_NAME"] = None
        except Exception:
            pass
        self.temp_dir.cleanup()

    def test_get_students_returns_student_rows(self):
        response = self.client.get("/students")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["student_id"], "STU-1001")

    def test_create_and_search_student(self):
        response = self.client.post(
            "/students",
            json={
                "student_id": "STU-1002",
                "name": "Marisol Tan",
                "course": "BS Information Technology",
                "year_level": "2nd Year",
                "email": "marisol.tan@uni.edu",
                "phone": "0918 442 0093",
                "gpa": 3.15,
            },
        )
        self.assertEqual(response.status_code, 201)

        search_response = self.client.get("/students/search", query_string={"query": "Marisol"})
        self.assertEqual(search_response.status_code, 200)
        self.assertEqual(search_response.get_json()[0]["name"], "Marisol Tan")


if __name__ == "__main__":
    unittest.main()
