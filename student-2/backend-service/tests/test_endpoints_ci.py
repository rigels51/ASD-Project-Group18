import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app


class StaffEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    @patch("routes.normal_ui.get_staff")
    def test_get_staff_route_returns_registry_rows(self, get_staff):
        get_staff.return_value = [
            {
                "staff_id": 12,
                "given_name": "Taylor",
                "family_name": "Example",
                "email": "taylor@example.test",
                "department": "Arts",
                "employment_type": "Full-time",
            }
        ]

        response = self.client.get("/staff")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Taylor Example", response.data)
        self.assertIn(b"Arts", response.data)
        get_staff.assert_called_once_with()

    @patch("routes.normal_ui.create_staff_response")
    def test_add_staff_route_creates_registry_entry(self, create_staff_response):
        database_response = Mock()
        database_response.status_code = 201
        database_response.json.return_value = {
            "staff_id": 13,
            "given_name": "Jordan",
            "family_name": "Example",
            "department": "Science",
            "employment_type": "Part-time",
        }
        create_staff_response.return_value = database_response
        payload = {
            "given_name": "Jordan",
            "family_name": "Example",
            "email": "jordan@example.test",
            "department": "Science",
            "employment_type": "Part-time",
        }

        response = self.client.post("/staff", data=payload)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Added Jordan Example to Science", response.data)
        self.assertEqual(response.headers["HX-Trigger"], "staff-changed")
        create_staff_response.assert_called_once_with(payload)


if __name__ == "__main__":
    unittest.main()
