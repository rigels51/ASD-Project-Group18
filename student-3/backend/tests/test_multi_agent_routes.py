"""Release 2: Timetable backend -> shared Multi-Agent server routes (server mocked, no Ollama).

Run from student-3/backend:
    python -m pytest tests/test_multi_agent_routes.py -v
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app as timetable_app  # noqa: E402
import multi_agent_mode  # noqa: E402


def fake_response(payload, status=200):
    response = mock.Mock()
    response.json.return_value = payload
    response.status_code = status
    return response


class MultiAgentRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = timetable_app.app.test_client()

    def test_run_sends_timetable_domain_to_shared_server(self):
        with mock.patch.object(multi_agent_mode.requests, "request",
                               return_value=fake_response({"workflow_id": "wf-1",
                                                           "status": "pending_human_review"})) as req:
            response = self.client.post("/multi-agent/run", json={"question": "Summarise ASD101 sessions"})

        self.assertEqual(response.status_code, 200)
        method, url = req.call_args.args
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/workflow"))
        body = req.call_args.kwargs["json"]
        self.assertEqual(body["domain"], "timetable")
        self.assertEqual(body["caller"], "timetable-backend")

    def test_empty_question_is_rejected_before_calling_server(self):
        with mock.patch.object(multi_agent_mode.requests, "request") as req:
            response = self.client.post("/multi-agent/run", json={"question": "  "})
        self.assertEqual(response.status_code, 400)
        req.assert_not_called()

    def test_decision_is_forwarded_for_the_workflow(self):
        with mock.patch.object(multi_agent_mode.requests, "request",
                               return_value=fake_response({"workflow_id": "wf-1", "status": "rejected"})) as req:
            response = self.client.post("/multi-agent/decision", json={
                "workflow_id": "wf-1", "decision": "Reject", "reviewer": "Laz", "comment": "Wrong room"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(req.call_args.args[1].endswith("/workflow/wf-1/decision"))
        self.assertEqual(req.call_args.kwargs["json"]["decision"], "Reject")

    def test_history_is_limited_to_timetable_domain(self):
        with mock.patch.object(multi_agent_mode.requests, "request",
                               return_value=fake_response({"workflows": []})) as req:
            self.client.get("/multi-agent/history")
        self.assertEqual(req.call_args.kwargs["params"]["domain"], "timetable")

    def test_disabled_flag_returns_503(self):
        with mock.patch.object(multi_agent_mode, "MULTI_AGENT_ENABLED", False):
            response = self.client.post("/multi-agent/run", json={"question": "x"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["status"], "disabled")

    def test_unreachable_server_returns_503(self):
        with mock.patch.object(multi_agent_mode.requests, "request",
                               side_effect=multi_agent_mode.requests.ConnectionError()):
            response = self.client.get("/multi-agent/health")
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
