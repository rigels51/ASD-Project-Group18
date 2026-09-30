"""Release 1 backend tests: MCP and RAG routes with the external servers mocked.

Run from student-3/backend after `python init_db.py`:
    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app as timetable_app  # noqa: E402
import mcp_client  # noqa: E402
import rag_client  # noqa: E402


class JsonApiTests(unittest.TestCase):
    def setUp(self):
        self.client = timetable_app.app.test_client()

    def test_api_timetable_returns_ten_json_records(self):
        response = self.client.get("/api/timetable")
        self.assertEqual(response.status_code, 200)
        records = response.get_json()
        self.assertEqual(len(records), 10)
        self.assertEqual(records[0]["course_code"], "ASD101")


class McpRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = timetable_app.app.test_client()

    def test_disabled_mcp_returns_503(self):
        with mock.patch.object(mcp_client, "MCP_ENABLED", False):
            response = self.client.post("/mcp/call", json={"tool": "find_timetable_clashes"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["status"], "disabled")

    def test_unknown_tool_is_rejected(self):
        with mock.patch.object(mcp_client, "MCP_ENABLED", True):
            response = self.client.post("/mcp/call", json={"tool": "drop_table", "arguments": {}})
        self.assertEqual(response.status_code, 400)

    def test_tool_result_is_passed_through(self):
        fake = {"room": "CB01.02.15", "available": False, "conflicts": [{"session_id": 1}]}
        with mock.patch.object(mcp_client, "MCP_ENABLED", True), \
             mock.patch.object(mcp_client, "call_timetable_tool", return_value=fake) as call:
            response = self.client.post("/mcp/call", json={
                "tool": "check_room_availability",
                "arguments": {"room": "CB01.02.15", "day": "Monday", "start_time": "10:00", "end_time": "11:00"},
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["result"], fake)
        call.assert_called_once()

    def test_tool_error_returns_400(self):
        with mock.patch.object(mcp_client, "MCP_ENABLED", True), \
             mock.patch.object(mcp_client, "call_timetable_tool", side_effect=RuntimeError("day must be one of")):
            response = self.client.post("/mcp/call", json={"tool": "check_room_availability", "arguments": {}})
        self.assertEqual(response.status_code, 400)


class RagRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = timetable_app.app.test_client()

    def test_disabled_rag_returns_503(self):
        with mock.patch.object(rag_client, "RAG_ENABLED", False):
            response = self.client.post("/rag/answer", json={"question": "When do sessions clash?"})
        self.assertEqual(response.status_code, 503)

    def test_empty_question_is_rejected(self):
        with mock.patch.object(rag_client, "RAG_ENABLED", True):
            response = self.client.post("/rag/answer", json={"question": "  "})
        self.assertEqual(response.status_code, 400)

    def test_grounded_answer_is_passed_through(self):
        fake = {"status": "success", "answer": "No clash [policy-4].", "confidence_category": "high",
                "citations": [{"chunk_id": "policy-4"}]}
        with mock.patch.object(rag_client, "RAG_ENABLED", True), \
             mock.patch.object(rag_client, "ask_rag", return_value=(fake, 200)):
            response = self.client.post("/rag/answer", json={"question": "Do back-to-back sessions clash?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["citations"][0]["chunk_id"], "policy-4")


if __name__ == "__main__":
    unittest.main()
