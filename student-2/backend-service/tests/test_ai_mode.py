import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


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


class MultiAgentRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    @patch("routes.multi_agent_mode.requests.request")
    def test_run_forwards_staff_domain_and_question(self, request):
        response_from_server = Mock()
        response_from_server.json.return_value = {
            "workflow_id": "workflow-123",
            "status": "pending_human_review",
        }
        response_from_server.status_code = 200
        request.return_value = response_from_server

        response = self.client.post(
            "/multi-agent/run",
            json={"question": "Summarise staff in Arts"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["workflow_id"], "workflow-123")
        request.assert_called_once_with(
            "POST",
            "http://localhost:5004/workflow",
            timeout=240,
            json={
                "user_request": "Summarise staff in Arts",
                "domain": "staff",
                "caller": "staff-backend",
            },
        )

    def test_run_rejects_empty_or_oversized_question(self):
        empty = self.client.post("/multi-agent/run", json={"question": " "})
        oversized = self.client.post(
            "/multi-agent/run",
            json={"question": "x" * 501},
        )

        self.assertEqual(empty.status_code, 400)
        self.assertEqual(oversized.status_code, 400)

    @patch("routes.multi_agent_mode.MULTI_AGENT_ENABLED", False)
    @patch("routes.multi_agent_mode.requests.request")
    def test_all_routes_report_disabled(self, request):
        responses = (
            self.client.get("/multi-agent/health"),
            self.client.post("/multi-agent/run", json={"question": "staff"}),
            self.client.post(
                "/multi-agent/decision",
                json={"workflow_id": "workflow-123", "decision": "Accept"},
            ),
            self.client.get("/multi-agent/workflow/workflow-123"),
            self.client.get("/multi-agent/history"),
        )

        for response in responses:
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json["status"], "disabled")
            self.assertIn("disabled", response.json["error"])
        request.assert_not_called()

    @patch("routes.multi_agent_mode.requests.request")
    def test_decision_is_forwarded_to_shared_server(self, request):
        response_from_server = Mock()
        response_from_server.json.return_value = {"status": "approved"}
        response_from_server.status_code = 200
        request.return_value = response_from_server

        response = self.client.post(
            "/multi-agent/decision",
            json={
                "workflow_id": "workflow-123",
                "decision": "Accept",
                "reviewer": "Jeriko",
                "comment": "",
                "corrected_output": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        request.assert_called_once_with(
            "POST",
            "http://localhost:5004/workflow/workflow-123/decision",
            timeout=15,
            json={
                "decision": "Accept",
                "reviewer": "Jeriko",
                "comment": "",
                "corrected_output": "",
            },
        )

    @patch("routes.multi_agent_mode.requests.request")
    def test_non_json_server_response_is_reported(self, request):
        response_from_server = Mock()
        response_from_server.json.side_effect = ValueError("invalid JSON")
        request.return_value = response_from_server

        response = self.client.get("/multi-agent/health")

        self.assertEqual(response.status_code, 502)
        self.assertIn("invalid response", response.json["error"])


if __name__ == "__main__":
    unittest.main()