

import sys
import unittest
from pathlib import Path
from unittest import mock

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402
from routes.rag_mode import build_question  # noqa: E402
from services import mcp_api, rag_api  # noqa: E402


COURSE_RESULT = {
    "course_id": "ASD101",
    "assessment_count": 1,
    "total_weight": 20.0,
    "assessments": [{"assessment_id": 1, "course_id": "ASD101", "assessment_name": "Design <Doc>",
                     "assessment_type": "Assignment", "due_date": "2026-09-05", "max_mark": 100, "weight": 20}],
}

RAG_GROUNDED = {
    "status": "success", "domain": "assessment", "query": "q",
    "answer": "ASD101 has 3 assessments [course-ASD101].",
    "citations": [{"chunk_id": "course-ASD101", "section": "ASD101 assessment summary",
                   "source_id": "assessment-database-service:/assessments?course_id=ASD101",
                   "similarity": 1.0, "text": "Course ASD101 has 3 assessments"}],
    "confidence_category": "high", "insufficient_evidence": False, "generator": "ollama:qwen2.5:0.5b",
}

RAG_ABSTAIN = {
    "status": "success", "domain": "assessment", "query": "q",
    "answer": "Insufficient evidence in the Assessment & Grades data to answer this question.",
    "citations": [], "confidence_category": "low", "insufficient_evidence": True,
}


class FlagsOffTests(unittest.TestCase):
    """What CI checks: integration code is present but switched off."""

    def setUp(self):
        self.client = create_app().test_client()
        mock.patch.object(mcp_api, "MCP_ENABLED", False).start()
        mock.patch.object(rag_api, "RAG_ENABLED", False).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_mcp_routes_report_disabled(self):
        self.assertEqual(self.client.get("/mcp/tools").status_code, 503)
        response = self.client.post("/mcp/call?format=json", json={"tool": "list_course_assessments",
                                                                   "arguments": {"course_id": "ASD101"}})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["status"], "disabled")

    def test_rag_routes_report_disabled(self):
        response = self.client.post("/rag/ask?format=json", data={"question": "What assessments are in ASD101?"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["status"], "disabled")
        self.assertEqual(self.client.post("/rag/refresh").status_code, 503)
        self.assertEqual(self.client.get("/rag/health").status_code, 503)


class McpRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        mock.patch.object(mcp_api, "MCP_ENABLED", True).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_call_renders_structured_result_and_escapes_html(self):
        with mock.patch.object(mcp_api, "call_assessment_tool", return_value=COURSE_RESULT) as call:
            response = self.client.post("/mcp/call", data={"tool": "list_course_assessments", "course_id": "asd101"})
        self.assertEqual(response.status_code, 200)
        call.assert_called_once_with("list_course_assessments", {"course_id": "asd101"})
        body = response.get_data(as_text=True)
        self.assertIn("Total weight", body)
        self.assertIn("Design &lt;Doc&gt;", body)
        self.assertIn("Structured result (JSON)", body)

    def test_json_format_returns_structured_payload(self):
        with mock.patch.object(mcp_api, "call_assessment_tool", return_value=COURSE_RESULT):
            response = self.client.post("/mcp/call?format=json",
                                        json={"tool": "list_course_assessments", "arguments": {"course_id": "ASD101"}})
        self.assertEqual(response.get_json()["result"]["total_weight"], 20.0)

    def test_tool_outside_boundary_is_rejected_without_calling_server(self):
        with mock.patch.object(mcp_api, "call_assessment_tool") as call:
            response = self.client.post("/mcp/call", data={"tool": "list_staff"})
        self.assertEqual(response.status_code, 400)
        call.assert_not_called()

    def test_invalid_input_rejected_by_tool_returns_400(self):
        with mock.patch.object(mcp_api, "call_assessment_tool",
                               side_effect=ValueError("student_id must look like STU-1001")):
            response = self.client.post("/mcp/call", data={"tool": "get_student_grade_summary", "student_id": "12"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("STU-1001", response.get_data(as_text=True))

    def test_server_down_returns_503(self):
        with mock.patch.object(mcp_api, "call_assessment_tool", side_effect=ConnectionError("refused")):
            response = self.client.post("/mcp/call", data={"tool": "get_upcoming_assessments"})
        self.assertEqual(response.status_code, 503)


class RagRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        mock.patch.object(rag_api, "RAG_ENABLED", True).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_grounded_answer_shows_sources_and_confidence(self):
        with mock.patch.object(rag_api, "ask_assessment_rag", return_value=RAG_GROUNDED) as ask:
            response = self.client.post("/rag/ask", data={"question": "What assessments do I have for this course?",
                                                          "course_id": "ASD101"})
        self.assertEqual(response.status_code, 200)
        ask.assert_called_once_with("What assessments do I have for this course? (course ASD101)")
        body = response.get_data(as_text=True)
        self.assertIn("Confidence: high", body)
        self.assertIn("course-ASD101", body)
        self.assertIn("Sources (1)", body)

    def test_insufficient_evidence_is_displayed(self):
        with mock.patch.object(rag_api, "ask_assessment_rag", return_value=RAG_ABSTAIN):
            response = self.client.post("/rag/ask", data={"question": "Who won the World Cup?"})
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Insufficient evidence", body)
        self.assertIn("Confidence: low", body)

    def test_question_required(self):
        self.assertEqual(self.client.post("/rag/ask", data={"question": " "}).status_code, 400)

    def test_server_down_returns_503(self):
        with mock.patch.object(rag_api, "ask_assessment_rag", side_effect=ConnectionError("refused")):
            response = self.client.post("/rag/ask", data={"question": "Exams?"})
        self.assertEqual(response.status_code, 503)

    def test_build_question_adds_course_once(self):
        self.assertEqual(build_question("Due dates?", "sec301"), "Due dates? (course SEC301)")
        self.assertEqual(build_question("Due dates in SEC301?", "SEC301"), "Due dates in SEC301?")
        self.assertEqual(build_question("Due dates?", "bad input"), "Due dates?")


if __name__ == "__main__":
    unittest.main()
