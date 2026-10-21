"""Student 4 release-2 endpoint and frontend integration tests.

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


class FeatureStatusEndpointTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def test_mcp_status_reports_enabled_without_contacting_mcp_server(self):
        with (
            patch("services.mcp_api.MCP_ENABLED", True),
            patch("routes.mcp_mode.list_course_tools") as mock_tools,
        ):
            response = self.client.get("/mcp/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "enabled")
        self.assertTrue(response.get_json()["enabled"])
        mock_tools.assert_not_called()

    def test_mcp_status_and_tool_result_report_disabled(self):
        with (
            patch("services.mcp_api.MCP_ENABLED", False),
            patch("services.mcp_api._call_tool_async") as mock_tool,
        ):
            status = self.client.get("/mcp/status")
            result = self.client.post("/mcp/run", data={"tool": "list_courses"})

        self.assertEqual(status.status_code, 503)
        self.assertEqual(status.get_json()["status"], "disabled")
        self.assertFalse(status.get_json()["enabled"])
        self.assertIn(b"MCP Mode is disabled", result.data)
        self.assertEqual(result.status_code, 503)
        mock_tool.assert_not_called()

    def test_rag_status_reports_enabled_without_contacting_rag_server(self):
        with (
            patch("services.rag_api.RAG_ENABLED", True),
            patch("routes.rag_mode.refresh_course_rag") as mock_refresh,
        ):
            response = self.client.get("/rag/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "enabled")
        self.assertTrue(response.get_json()["enabled"])
        mock_refresh.assert_not_called()

    def test_rag_status_and_query_result_report_disabled(self):
        with (
            patch("services.rag_api.RAG_ENABLED", False),
            patch("services.rag_api.requests.post") as mock_answer,
        ):
            status = self.client.get("/rag/status")
            result = self.client.post("/rag/answer", data={"query": "What is ASD101?"})

        self.assertEqual(status.status_code, 503)
        self.assertEqual(status.get_json()["status"], "disabled")
        self.assertFalse(status.get_json()["enabled"])
        self.assertIn(b"RAG Mode is disabled", result.data)
        self.assertEqual(result.status_code, 503)
        mock_answer.assert_not_called()


class FeatureStatusFrontendTests(unittest.TestCase):
    FRONTEND = Path(__file__).resolve().parents[1] / "frontend-service" / "templates" / "tabs"

    def assert_dynamic_status_ui(self, filename, mode):
        text = (self.FRONTEND / filename).read_text(encoding="utf-8")
        result_id = f"{mode}-result"
        setter = f"set{mode.title()}Status"

        self.assertIn(f'id="{mode}-status"', text)
        self.assertIn('data-state="checking"', text)
        self.assertIn(f'"http://localhost:5031/{mode}/status"', text)
        self.assertIn('enabled: "Enabled"', text)
        self.assertIn('disabled: "Disabled"', text)
        self.assertIn('unavailable: "Unavailable"', text)
        self.assertRegex(
            text,
            r'response\.status === 503\s*&&\s*payload\.status === "disabled"',
        )
        self.assertRegex(
            text,
            r'response\.ok\s*&&\s*payload\.status === "enabled"',
        )
        self.assertRegex(
            text,
            rf'(?s)catch \(error\).*?{setter}\("unavailable"\)',
        )
        self.assertIn('"htmx:beforeSwap"', text)
        self.assertIn(f'detail.target?.id === "{result_id}"', text)
        self.assertIn("detail.shouldSwap = true", text)
        self.assertIn("detail.isError = false", text)
        self.assertIn('"htmx:sendError"', text)
        self.assertNotRegex(text, r'<span class="status-dot"></span>\s*Enabled')

    def test_mcp_frontend_handles_all_feature_states_and_http_errors(self):
        self.assert_dynamic_status_ui("mcp.html", "mcp")

    def test_rag_frontend_handles_all_feature_states_and_http_errors(self):
        self.assert_dynamic_status_ui("rag.html", "rag")


if __name__ == "__main__":
    unittest.main()
