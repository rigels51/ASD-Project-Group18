import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


DATABASE_SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATABASE_SERVICE_DIR))

import app as database_app


class StaffDatabaseApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "staff.db"
        self.database_patch = patch.object(
            database_app,
            "DATABASE_NAME",
            str(self.database_path),
        )
        self.database_patch.start()
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(
                """
                CREATE TABLE staff (
                    staff_id INTEGER PRIMARY KEY,
                    given_name TEXT NOT NULL,
                    family_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    department TEXT NOT NULL,
                    employment_type TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO staff
                    (staff_id, given_name, family_name, email, department, employment_type)
                VALUES (1, 'Taylor', 'Example', 'taylor@example.test', 'ARTS', 'Full-time')
                """
            )
            connection.commit()
        finally:
            connection.close()
        self.client = database_app.app.test_client()

    def tearDown(self):
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def test_update_staff_changes_supplied_fields_and_preserves_others(self):
        response = self.client.put(
            "/staff/1",
            json={"given_name": "Jordan", "department": "science"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["given_name"], "Jordan")
        self.assertEqual(response.json["department"], "SCIENCE")
        self.assertEqual(response.json["family_name"], "Example")
        self.assertEqual(response.json["email"], "taylor@example.test")
        self.assertEqual(response.json["employment_type"], "Full-time")

    def test_department_filter_treats_input_as_a_value(self):
        response = self.client.get(
            "/staff/by-department",
            query_string={"department": "' OR 1=1 --"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["error"], "No staff found")


if __name__ == "__main__":
    unittest.main()
