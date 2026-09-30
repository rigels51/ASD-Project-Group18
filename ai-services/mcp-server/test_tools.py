import unittest
from unittest.mock import patch

import tools


STAFF = [
    {
        "staff_id": 4,
        "given_name": "Ari",
        "family_name": "Chen",
        "email": "ari@example.com",
        "department": "Arts",
        "employment_type": "Part-time",
    },
    {
        "staff_id": 5,
        "given_name": "Rae",
        "family_name": "Diaz",
        "email": "rae@example.com",
        "department": "Arts",
        "employment_type": "Full-time",
    },
]


class StaffToolsTests(unittest.TestCase):
    @patch("tools._get_staff_records", return_value=STAFF)
    def test_count_uses_live_staff_records(self, get_records):
        self.assertEqual(tools.staff_count(), {"staff_count": 2})
        get_records.assert_called_once_with()

    @patch("tools._get_staff_records", return_value=STAFF)
    def test_directory_filters_and_omits_email(self, _get_records):
        result = tools.staff_directory("arts")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["given_name"], "Ari")
        self.assertNotIn("email", result[0])

    @patch("tools._get_staff_records", return_value=STAFF)
    def test_member_lookup_rejects_invalid_id(self, _get_records):
        with self.assertRaises(ValueError):
            tools.staff_member(0)

    @patch("tools._get_staff_records", return_value=STAFF)
    def test_summary_groups_by_department_and_employment(self, _get_records):
        self.assertEqual(
            tools.employment_summary(),
            {
                "by_department": {"Arts": 2},
                "by_employment_type": {"Part-time": 1, "Full-time": 1},
            },
        )


if __name__ == "__main__":
    unittest.main()