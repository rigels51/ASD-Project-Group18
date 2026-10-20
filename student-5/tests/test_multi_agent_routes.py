"""Release 2 - offline tests for the Assessment & Grades Multi-Agent proxy routes.

The shared Multi-Agent server is mocked, so these run in CI with no Ollama:
    python -m pytest student-5/tests/test_multi_agent_routes.py -v
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

import requests

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402
from services import multi_agent_api  # noqa: E402

CHECKS = [{"check": "evidence_retrieved", "passed": True}]
PENDING = {
    "workflow_id": "wf-1", "status": "pending_human_review", "domain": "assessment",
    "timestamp": "2026-10-20T10:00:00+00:00", "user_request": "Summarise ASD101",
    "planner_result": {"status": "completed", "model": "qwen2.5:0.5b", "plan": "Objective: summarise <ASD101>"},
    "worker_result": {"status": "completed", "model": "qwen2.5:0.5b", "evidence_count": 3,
                      "sources": [{"label": "assessments", "matched": 3, "total": 10}],
                      "output": "Output: ASD101 has 3 assessments."},
    "reviewer_result": {"status": "completed", "risk_level": "low", "recommended_decision": "Accept",
                        "review": "Risk: low", "automatic_checks": CHECKS},
    "human_decision": {"required": True, "status": "pending"},
}
DECIDED = {**PENDING, "status": "corrected",
           "human_decision": {"decision": "Correct", "reviewer": "Vu", "comment": "fix",
                              "final_output": "Corrected text"}}


class FlagOffTests(unittest.TestCase):
    def test_routes_report_disabled_when_flag_off(self):
        client = create_app().test_client()
        with mock.patch.object(multi_agent_api, "MULTI_AGENT_ENABLED", False):
            r = client.post("/multi-agent/run?format=json", data={"question": "Summarise ASD101"})
            self.assertEqual(r.status_code, 503)
            self.assertEqual(r.get_json()["status"], "disabled")
            self.assertEqual(client.get("/multi-agent/health").status_code, 503)


class RunRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        mock.patch.object(multi_agent_api, "MULTI_AGENT_ENABLED", True).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_run_sends_assessment_domain_and_renders_all_four_steps(self):
        with mock.patch.object(multi_agent_api, "run_workflow", return_value=(PENDING, 200)) as run:
            r = self.client.post("/multi-agent/run", data={"question": "Summarise ASD101"})
        run.assert_called_once_with("Summarise ASD101")
        body = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        for text in ("Planner", "Worker", "Reviewer", "Human review", "Risk: low", "data-decision-form"):
            self.assertIn(text, body)
        self.assertIn("&lt;ASD101&gt;", body)  # model text is escaped

    def test_run_requires_question(self):
        self.assertEqual(self.client.post("/multi-agent/run", data={"question": " "}).status_code, 400)

    def test_server_down_returns_503(self):
        with mock.patch.object(multi_agent_api, "run_workflow", side_effect=requests.ConnectionError("x")):
            self.assertEqual(self.client.post("/multi-agent/run", data={"question": "q"}).status_code, 503)

    def test_api_client_sends_domain_and_caller(self):
        with mock.patch.object(multi_agent_api.requests, "post") as post:
            post.return_value.json.return_value = PENDING
            post.return_value.status_code = 200
            multi_agent_api.run_workflow("Summarise ASD101")
        self.assertEqual(post.call_args.kwargs["json"]["domain"], "assessment")


class DecisionRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        mock.patch.object(multi_agent_api, "MULTI_AGENT_ENABLED", True).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_decision_is_forwarded_and_result_rendered(self):
        with mock.patch.object(multi_agent_api, "decide", return_value=(DECIDED, 200)) as decide:
            r = self.client.post("/multi-agent/decision", data={
                "workflow_id": "wf-1", "decision": "Correct", "reviewer": "Vu",
                "comment": "fix", "corrected_output": "Corrected text"})
        decide.assert_called_once_with("wf-1", {"decision": "Correct", "reviewer": "Vu", "comment": "fix",
                                                "corrected_output": "Corrected text"})
        body = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("Corrected", body)
        self.assertNotIn("data-decision-form", body)  # no second decision on a decided workflow

    def test_server_validation_error_is_shown(self):
        with mock.patch.object(multi_agent_api, "decide",
                               return_value=({"status": "error", "error": "a comment is required"}, 400)):
            r = self.client.post("/multi-agent/decision", data={"workflow_id": "wf-1", "decision": "Reject"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("a comment is required", r.get_data(as_text=True))

    def test_decision_requires_workflow_id(self):
        self.assertEqual(self.client.post("/multi-agent/decision", data={"decision": "Accept"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
