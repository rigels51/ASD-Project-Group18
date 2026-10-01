import unittest
from unittest.mock import MagicMock, patch

import requests

import student5_tools
from student5_tools import course_assessments, student_grade_summary, upcoming_assessments


ASSESSMENTS = [
    {"assessment_id": 3, "course_id": "ASD101", "assessment_name": "Final Project", "assessment_type": "Project",
     "description": "Team microservices project", "due_date": "2026-10-24", "max_mark": 100, "weight": 40},
    {"assessment_id": 1, "course_id": "ASD101", "assessment_name": "Assignment 1 - Design Doc",
     "assessment_type": "Assignment", "description": "Software design document", "due_date": "2026-09-05",
     "max_mark": 100, "weight": 20},
    {"assessment_id": 7, "course_id": "DBS101", "assessment_name": "Final Exam", "assessment_type": "Exam",
     "description": "Closed book, 2 hours", "due_date": "2026-11-05", "max_mark": 100, "weight": 45},
]

STUDENT_GRADES = [
    {"grade_id": 1, "assessment_id": 1, "student_id": "STU-1001", "mark": 88, "grade": "HD",
     "feedback": "Excellent design coverage.", "date_recorded": "2026-09-10",
     "assessment_name": "Assignment 1 - Design Doc", "course_id": "ASD101", "max_mark": 100},
    {"grade_id": 3, "assessment_id": 2, "student_id": "STU-1001", "mark": 42, "grade": "D",
     "feedback": "Strong understanding.", "date_recorded": "2026-09-20",
     "assessment_name": "Mid-Semester Test", "course_id": "ASD101", "max_mark": 50},
    {"grade_id": 12, "assessment_id": 3, "student_id": "STU-1001", "mark": None, "grade": None,
     "feedback": None, "date_recorded": "2026-10-24",
     "assessment_name": "Final Project", "course_id": "ASD101", "max_mark": 100},
]


def _response(payload, status=200):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"{status}")
    return response


class CourseAssessmentsTests(unittest.TestCase):
    @patch("student5_tools.requests.get")
    def test_returns_sorted_assessments_and_total_weight(self, mock_get):
        mock_get.return_value = _response([a for a in ASSESSMENTS if a["course_id"] == "ASD101"])
        result = course_assessments("asd101")
        self.assertEqual(result["course_id"], "ASD101")
        self.assertEqual(result["assessment_count"], 2)
        self.assertEqual(result["total_weight"], 60.0)
        self.assertEqual([a["assessment_id"] for a in result["assessments"]], [1, 3])
        self.assertEqual(mock_get.call_args.kwargs["params"], {"course_id": "ASD101"})

    @patch("student5_tools.requests.get")
    def test_rejects_invalid_course_code_without_calling_database(self, mock_get):
        for bad in ("", "ASD", "DROP TABLE", "ASD1011"):
            with self.assertRaises(ValueError):
                course_assessments(bad)
        mock_get.assert_not_called()


class StudentGradeSummaryTests(unittest.TestCase):
    @patch("student5_tools.requests.get")
    def test_summarises_graded_and_pending(self, mock_get):
        mock_get.return_value = _response(STUDENT_GRADES)
        result = student_grade_summary("stu-1001")
        self.assertTrue(result["found"])
        self.assertEqual(result["graded_count"], 2)
        self.assertEqual(result["pending_count"], 1)
        self.assertEqual(result["average_percent"], 86.0)  # (88% + 84%) / 2
        self.assertNotIn("student_id", result["grades"][0])

    @patch("student5_tools.requests.get")
    def test_unknown_student_is_not_an_error(self, mock_get):
        mock_get.return_value = _response({"error": "No grades found"}, status=404)
        result = student_grade_summary("STU-9999")
        self.assertFalse(result["found"])
        self.assertEqual(result["grades"], [])

    def test_accepts_id_without_dash(self):
        with patch("student5_tools.requests.get", return_value=_response(STUDENT_GRADES)):
            self.assertEqual(student_grade_summary("STU1001")["student_id"], "STU-1001")

    def test_rejects_invalid_student_id(self):
        for bad in ("1001", "STU-1", "student 1001", ""):
            with self.assertRaises(ValueError):
                student_grade_summary(bad)


class UpcomingAssessmentsTests(unittest.TestCase):
    @patch("student5_tools.requests.get")
    def test_filters_and_limits_by_due_date(self, mock_get):
        mock_get.return_value = _response(ASSESSMENTS)
        result = upcoming_assessments("2026-10-01", 1)
        self.assertEqual(result["total_upcoming"], 2)
        self.assertEqual(len(result["assessments"]), 1)
        self.assertEqual(result["assessments"][0]["assessment_name"], "Final Project")

    def test_rejects_bad_date_and_limit(self):
        with self.assertRaises(ValueError):
            upcoming_assessments("01/10/2026", 5)
        with self.assertRaises(ValueError):
            upcoming_assessments("2026-02-30", 5)
        with self.assertRaises(ValueError):
            upcoming_assessments("2026-10-01", 0)
        with self.assertRaises(ValueError):
            upcoming_assessments("2026-10-01", 21)


class ToolErrorMappingTests(unittest.TestCase):
    def test_database_outage_becomes_tool_error(self):
        from mcp.server.mcpserver.exceptions import ToolError

        with patch("student5_tools.requests.get", side_effect=requests.ConnectionError("down")):
            with self.assertRaises(ToolError):
                student5_tools._run(course_assessments, "ASD101")

    def test_validation_error_becomes_tool_error(self):
        from mcp.server.mcpserver.exceptions import ToolError

        with self.assertRaises(ToolError):
            student5_tools._run(course_assessments, "nope")


if __name__ == "__main__":
    unittest.main()
