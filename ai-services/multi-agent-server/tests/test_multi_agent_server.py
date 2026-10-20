"""Offline tests for the shared Multi-Agent Server (no Ollama, no feature services).

    cd ai-services/multi-agent-server && python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_DIR))
_tmp = tempfile.mkdtemp()
os.environ["MULTI_AGENT_LOG_DIR"] = _tmp

import coordinator  # noqa: E402
import evidence  # noqa: E402
import llm  # noqa: E402
from agents import worker_agent  # noqa: E402
from app import app  # noqa: E402

ASSESSMENTS = [
    {"assessment_id": 1, "course_id": "ASD101", "assessment_name": "Design Doc", "assessment_type": "Assignment",
     "due_date": "2026-09-05", "max_mark": 100, "weight": 20},
    {"assessment_id": 7, "course_id": "DBS101", "assessment_name": "Final Exam", "assessment_type": "Exam",
     "due_date": "2026-11-05", "max_mark": 100, "weight": 45},
]


def fake_get(url, timeout):
    response = mock.MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = ASSESSMENTS if url.endswith("/assessments") else []
    return response


def fake_chat(model, system, user, max_tokens=220):
    if "Planner" in system:
        return "Objective: x\nSteps: 1 2 3\nEvidence Required: assessments\nHuman Approval: Required.", None
    if "Worker" in system:
        return "Output: ASD101 has Design Doc due 2026-09-05.\nEvidence Used: assessments\nLimitations: None", None
    return "Risk: low - grounded\nCorrection: None\nRetest: rerun\nRecommendation: Accept - fine", None


class BaseCase(unittest.TestCase):
    def setUp(self):
        for path in (coordinator.HISTORY_PATH, coordinator.AUDIT_PATH):
            path.unlink(missing_ok=True)
        mock.patch.object(evidence.requests, "get", side_effect=fake_get).start()
        self.chat = mock.patch.object(llm, "chat", side_effect=fake_chat).start()
        self.client = app.test_client()

    def tearDown(self):
        mock.patch.stopall()


class WorkflowTests(BaseCase):
    def test_agents_run_in_order_and_worker_uses_filtered_evidence(self):
        wf = coordinator.run_workflow("Summarise assessments for ASD101", "assessment")
        self.assertEqual(wf["status"], "pending_human_review")
        self.assertEqual(wf["worker_result"]["evidence_count"], 1)          # DBS101 filtered out
        self.assertEqual(wf["reviewer_result"]["risk_level"], "low")
        events = [r["event"] for r in coordinator.read_jsonl(coordinator.AUDIT_PATH)]
        self.assertEqual(events, ["workflow_started", "planner_completed", "worker_completed",
                                  "reviewer_completed", "awaiting_human_review"])

    def test_keyword_routing_and_out_of_scope_rejection(self):
        self.assertEqual(coordinator.run_workflow("List upcoming exam weights")["domain"], "assessment")
        self.assertEqual(coordinator.run_workflow("What is the weather?")["status"], "rejected_by_planner")

    def test_hallucinated_identifier_is_replaced_and_raises_risk(self):
        self.chat.side_effect = lambda m, s, u, max_tokens=0: (
            ("Output: MAT999 is due.", None) if "Worker" in s else fake_chat(m, s, u))
        wf = coordinator.run_workflow("Assessments for ASD101", "assessment")
        self.assertIn("identifier not in evidence: MAT999", wf["worker_result"]["grounding_issues"])
        self.assertNotIn("MAT999 is due", wf["worker_result"]["output"].split("(Model answer")[0])
        self.assertEqual(wf["reviewer_result"]["risk_level"], "medium")   # model said low; rules win

    def test_models_down_still_completes_with_fallbacks(self):
        self.chat.side_effect = lambda *a, **k: (None, "down")
        wf = coordinator.run_workflow("Assessments for ASD101", "assessment")
        self.assertEqual(wf["status"], "pending_human_review")
        self.assertIn("fallback", wf["worker_result"]["model"])

    def test_no_evidence_is_high_risk(self):
        wf = coordinator.run_workflow("Assessments for XYZ999", "assessment")
        self.assertEqual(wf["worker_result"]["evidence_count"], 0)
        self.assertEqual(wf["reviewer_result"]["risk_level"], "high")
        self.assertEqual(wf["reviewer_result"]["recommended_decision"], "Reject")


class HumanDecisionTests(BaseCase):
    def test_correct_decision_records_corrected_output_and_audit(self):
        wf = coordinator.run_workflow("Assessments for ASD101", "assessment")
        done = coordinator.record_decision(wf["workflow_id"], "Correct", "Vu", "wrong date", "Due 2026-09-06")
        self.assertEqual(done["status"], "corrected")
        self.assertEqual(done["human_decision"]["final_output"], "Due 2026-09-06")
        self.assertEqual(coordinator.read_jsonl(coordinator.AUDIT_PATH)[-1]["event"], "human_decision_recorded")
        self.assertEqual(coordinator.workflow_status()["human_decisions"], {"Correct": 1})
        with self.assertRaises(ValueError):  # a decided workflow cannot be silently re-decided
            coordinator.record_decision(wf["workflow_id"], "Accept", "Someone else")

    def test_decision_validation(self):
        wf = coordinator.run_workflow("Assessments for ASD101", "assessment")
        with self.assertRaises(ValueError):
            coordinator.record_decision(wf["workflow_id"], "Maybe", "Vu")
        with self.assertRaises(ValueError):
            coordinator.record_decision(wf["workflow_id"], "Reject", "Vu", comment="")
        with self.assertRaises(KeyError):
            coordinator.record_decision("nope", "Accept", "Vu")


class ApiTests(BaseCase):
    def test_full_round_trip_over_http(self):
        started = self.client.post("/workflow", json={"user_request": "Assessments for ASD101",
                                                      "domain": "assessment", "caller": "student5"})
        self.assertEqual(started.status_code, 200)
        wid = started.get_json()["workflow_id"]
        decided = self.client.post(f"/workflow/{wid}/decision", json={"decision": "Accept", "reviewer": "Vu"})
        self.assertEqual(decided.get_json()["status"], "approved")
        self.assertEqual(self.client.get(f"/workflow/{wid}").get_json()["human_decision"]["decision"], "Accept")
        self.assertEqual(self.client.get("/workflow/status").get_json()["workflow_count"], 1)

    def test_bad_requests(self):
        self.assertEqual(self.client.post("/workflow", json={}).status_code, 400)
        self.assertEqual(self.client.post("/workflow", json={"user_request": "x", "domain": "weather"}).status_code, 400)
        self.assertEqual(self.client.post("/workflow/none/decision", json={"decision": "Accept",
                                                                            "reviewer": "a"}).status_code, 404)

    def test_grounding_helper(self):
        self.assertEqual(worker_agent.grounding_issues("ASD101 and STU-1001", [{"c": "ASD101", "s": "STU-1001"}]), [])


if __name__ == "__main__":
    unittest.main()
