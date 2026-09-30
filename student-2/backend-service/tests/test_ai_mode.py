import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app


class AiModeRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_mcp_call_rejects_unknown_tool(self):
        response = self.client.post("/mcp/call", json={"tool": "read_arbitrary_file"})
        self.assertEqual(response.status_code, 400)

    def test_mcp_call_validates_staff_id(self):
        response = self.client.post(
            "/mcp/call",
            json={"tool": "get_staff_member", "arguments": {"staff_id": -1}},
        )
        self.assertEqual(response.status_code, 400)

    @patch("routes.ai_mode.call_staff_tool", return_value={"staff_count": 10})
    def test_mcp_call_uses_protocol_client(self, call_staff_tool):
        response = self.client.post("/mcp/call", json={"tool": "get_staff_count"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["result"], {"staff_count": 10})
        call_staff_tool.assert_called_once_with("get_staff_count", {})

    @patch("routes.ai_mode.call_rag_service", return_value={"status": "success", "answer": "Grounded"})
    def test_rag_answer_forwards_question(self, call_rag_service):
        response = self.client.post("/rag/answer", json={"question": "Who works in Arts?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["answer"], "Grounded")
        call_rag_service.assert_called_once_with(
            "/answer",
            {"query": "Who works in Arts?", "k": 5, "caller": "student-2"},
        )

    @patch("routes.ai_mode.call_rag_service", return_value={"status": "success", "results": []})
    def test_rag_retrieval_forwards_bounded_query(self, call_rag_service):
        response = self.client.post(
            "/rag/retrieve",
            json={"query": "Arts department", "k": 3},
        )
        self.assertEqual(response.status_code, 200)
        call_rag_service.assert_called_once_with(
            "/retrieve",
            {"query": "Arts department", "k": 3, "caller": "student-2"},
        )


if __name__ == "__main__":
    unittest.main()