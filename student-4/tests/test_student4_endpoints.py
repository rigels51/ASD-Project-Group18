"""Student 4 release-2 tests: GET /courses and POST /courses.

Runs against Flask's test client and mocks the downstream database HTTP
service. No live Docker, Ollama, MCP, or RAG service is required.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

BACKEND = Path(__file__).resolve().parents[1] / "enrolment-service"
sys.path.insert(0, str(BACKEND))

from app import create_app  # noqa: E402


class CourseEndpointTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    @patch("routes.normal_ui.get_courses")
    def test_get_courses_returns_course_table(self, mock_get_courses):
        """GET /courses returns HTML that includes retrieved course data."""
        mock_get_courses.return_value = [
            {
                "course_id": 1,
                "course_code": "ASD101",
                "course_name": "Advanced Software Development",
                "credits": 6,
                "capacity": 30,
            }
        ]
        response = self.client.get("/courses")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ASD101", response.data)
        mock_get_courses.assert_called_once_with()

    @patch("routes.normal_ui.create_course_response")
    def test_post_courses_creates_course(self, mock_create_course):
        """POST /courses accepts form data and returns HTTP 201."""
        upstream = Mock()
        upstream.status_code = 201
        upstream.json.return_value = {"course_id": 11}
        mock_create_course.return_value = upstream

        response = self.client.post(
            "/courses",
            data={
                "course_code": "TST101",
                "course_name": "Test Course",
                "credits": "6",
                "capacity": "25",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn(b"Course created successfully", response.data)
        mock_create_course.assert_called_once_with(
            {
                "course_code": "TST101",
                "course_name": "Test Course",
                "credits": "6",
                "capacity": "25",
            }
        )


class AIModeEndpointTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def test_all_ai_routes_return_503_without_calling_dependencies_when_disabled(self):
        routes = [
            ("/ask", {"question": "Hello"}),
            ("/ask-with-context", {"question": "What is ASD101?"}),
            ("/pattern-selection", {"architecture_request": "Choose a pattern"}),
            ("/architecture-review", {"architecture_request": "Review this design"}),
            ("/adr-review", {"architecture_request": "Review this ADR"}),
        ]

        with (
            patch("routes.ai_mode.AI_MODE_ENABLED", False),
            patch("routes.ai_mode.create_chat_completion") as mock_chat,
            patch("routes.ai_mode.call_architecture_agent") as mock_architecture,
            patch("routes.ai_mode.get_courses") as mock_courses,
            patch("routes.ai_mode.get_enrolments") as mock_enrolments,
        ):
            for path, data in routes:
                with self.subTest(path=path):
                    response = self.client.post(path, data=data)
                    self.assertEqual(response.status_code, 503)
                    self.assertIn(b"AI Mode is disabled", response.data)

        mock_chat.assert_not_called()
        mock_architecture.assert_not_called()
        mock_courses.assert_not_called()
        mock_enrolments.assert_not_called()

    @patch("routes.ai_mode.create_chat_completion", return_value="AI is available")
    def test_ai_route_still_works_when_enabled(self, mock_chat):
        with patch("routes.ai_mode.AI_MODE_ENABLED", True):
            response = self.client.post("/ask", data={"question": "Hello"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"AI is available", response.data)
        mock_chat.assert_called_once()


if __name__ == "__main__":
    unittest.main()
