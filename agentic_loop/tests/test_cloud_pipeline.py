"""Cloud Deployment Review mode - offline tests (no cloud, no Ollama).

Each test builds a throwaway repository layout (workflow, scripts, deployment.json) and fakes the
deployed services. Disabled responses mirror each backend's real code:
S1/S4 503 "RAG Mode is disabled", S2 403 "RAG mode is disabled.", S3/S5 503 {"status": "disabled"}.

    python -m unittest agentic_loop.tests.test_cloud_pipeline -v      # from the repository root
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentic_loop.collectors import cloud_collector
from agentic_loop.config import review_config as cfg
from agentic_loop.core import reporter
from agentic_loop.pipelines import cloud_pipeline

GOOD_WORKFLOW = """name: Cloud deployment
on:
  workflow_run:
    workflows: ["Student 3 - Timetable & Class Scheduling CI"]
    types: [completed]
jobs:
  deploy:
    runs-on: ubuntu-latest
    env:
      MCP_ENABLED: "false"
      RAG_ENABLED: "false"
      MULTI_AGENT_ENABLED: "false"
    steps:
      - uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - run: bash scripts/deploy/deploy_azure.sh
"""

DISABLED = {
    "/rag/answer": {
        "student1-backend": (503, '{"status": "error", "error": "RAG Mode is disabled"}'),
        "student2-backend": (403, '{"status": "error", "error": "RAG mode is disabled."}'),
        "timetable-backend": (503, '{"status": "disabled", "error": "RAG is disabled (RAG_ENABLED=false)"}'),
        "student4-backend": (503, '{"status": "error", "error": "RAG Mode is disabled"}'),
    },
    "/rag/ask": {"assessment-backend": (503, '{"status": "disabled", "error": "RAG is disabled"}')},
    "/mcp/call": {"timetable-backend": (503, '{"status": "disabled", "error": "MCP is disabled"}')},
    "/multi-agent/run": {
        "timetable-backend": (503, '{"status": "disabled", "error": "Multi-Agent is disabled"}'),
        "assessment-backend": (503, '{"status": "disabled", "error": "Multi-Agent is disabled"}'),
    },
}


def record(**overrides):
    data = json.loads((Path(cfg.__file__).resolve().parents[2] / "docs" / "release-2" / "cloud"
                       / "deployment.example.json").read_text(encoding="utf-8"))
    data.update(overrides)
    return data


class FakeCloud:
    """Answers requests.request(...) like the deployed application would."""

    def __init__(self, record_data, overrides=None):
        self.hosts = {**{u: n for n, u in record_data["frontends"].items()},
                      **{u: n for n, u in record_data["backends"].items()}}
        self.overrides = overrides or {}  # (service, path) -> (status, body)
        self.calls = []

    def __call__(self, method, url, timeout=None, json=None, data=None):  # noqa: A002 - mirrors requests
        self.calls.append({"method": method, "url": url, "json": json, "data": data})
        base, path = next((b, url[len(b):]) for b in sorted(self.hosts, key=len, reverse=True) if url.startswith(b))
        service = self.hosts[base]
        status, body = self.overrides.get((service, path)) or DISABLED.get(path, {}).get(service) or (200, "<table></table>")
        response = mock.Mock(status_code=status, text=body)
        response.elapsed.total_seconds.return_value = 0.042
        return response


class CloudPipelineTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        for target in (cloud_collector, cloud_pipeline):
            patcher = mock.patch.object(target, "ROOT", self.root)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch.object(reporter, "DOCS_DIR", self.root / "docs")
        patcher.start()
        self.addCleanup(patcher.stop)

    # ---- helpers ----
    def write_repo(self, workflow=GOOD_WORKFLOW, scripts=("deploy_azure.sh",), record_data=None):
        if workflow is not None:
            (self.root / ".github" / "workflows").mkdir(parents=True)
            (self.root / ".github" / "workflows" / cfg.CLOUD_WORKFLOW).write_text(workflow)
        (self.root / cfg.CLOUD_DEPLOY_SCRIPTS_DIR).mkdir(parents=True)
        for name in scripts:
            (self.root / cfg.CLOUD_DEPLOY_SCRIPTS_DIR / name).write_text("#!/bin/bash\n")
        if record_data is not None:
            path = self.root / cfg.CLOUD_EVIDENCE_FILE
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record_data))

    def run_review(self, fake=None, **kwargs):
        with mock.patch.object(cloud_collector.requests, "request", side_effect=fake or FakeCloud(record())):
            ok = cloud_pipeline.run(use_ai=False, interactive=False, **kwargs)
        report = (self.root / "docs" / "release-2" / "agentic-loop" / "cloud-validation.md").read_text()
        return ok, report

    def decisions(self):
        path = self.root / cfg.CLOUD_DECISIONS_LOG
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    # ---- tests ----
    def test_nothing_deployed_yet_recommends_do_not_release(self):
        self.write_repo(workflow=None, scripts=())
        ok, report = self.run_review()
        self.assertFalse(ok)
        self.assertIn("Recommended release decision: Do not release", report)
        self.assertIn("cloud-deployment.yml not found", report)
        self.assertIn("no deployment record", report)
        self.assertIn("PENDING", report)

    def test_healthy_baseline_deployment_recommends_release_and_logs_decision(self):
        self.write_repo(record_data=record())
        ok, report = self.run_review(decision="Release", reviewer="Laz")
        self.assertTrue(ok)
        self.assertIn("Recommended release decision: Release.", report)
        self.assertNotIn("| FAIL |", report)
        self.assertNotIn("| WARN |", report)
        self.assertIn("GET /timetable | PASS", report)
        self.assertIn("POST /rag/answer disabled | PASS", report)  # includes S2's 403 answer
        [entry] = self.decisions()
        self.assertEqual(entry["decision"], "Release")
        self.assertTrue(entry["agreed_with_loop"])
        self.assertEqual(entry["results"]["FAIL"], 0)

    def test_form_backends_are_probed_with_form_fields(self):
        self.write_repo(record_data=record())
        fake = FakeCloud(record())
        self.run_review(fake=fake)
        s1 = [c for c in fake.calls if "student1-backend" in c["url"] and c["url"].endswith("/rag/answer")][0]
        self.assertEqual(s1["data"], {"query": "Who is on leave?"})
        self.assertIsNone(s1["json"])

    def test_ai_route_answering_in_baseline_profile_fails(self):
        self.write_repo(record_data=record())
        fake = FakeCloud(record(), {("timetable-backend", "/rag/answer"): (200, '{"status": "success"}')})
        ok, report = self.run_review(fake=fake)
        self.assertFalse(ok)
        self.assertIn("AI route answered, but the baseline cloud profile requires it disabled", report)

    def test_flag_left_on_with_server_unreachable_is_a_warning(self):
        self.write_repo(record_data=record())
        fake = FakeCloud(record(), {("student4-backend", "/rag/answer"):
                                    (503, '{"status": "error", "error": "Connection refused"}')})
        ok, report = self.run_review(fake=fake)
        self.assertTrue(ok)
        self.assertIn("Recommended release decision: Release with conditions", report)
        self.assertIn("set its *_ENABLED flag to false", report)

    def test_bonus_profile_counts_enabled_ai_as_pass(self):
        data = record(ai_profile="bonus", ai_enabled=["timetable-backend"])
        self.write_repo(record_data=data)
        fake = FakeCloud(data, {("timetable-backend", p): (200, '{"status": "success"}')
                                for p in ("/rag/answer", "/mcp/call", "/multi-agent/run")})
        ok, report = self.run_review(fake=fake)
        self.assertTrue(ok)
        self.assertIn("POST /rag/answer (bonus: enabled) | PASS", report)

    def test_backend_down_fails(self):
        self.write_repo(record_data=record())
        fake = FakeCloud(record(), {("assessment-backend", "/assessments"): (502, "Bad Gateway")})
        ok, report = self.run_review(fake=fake)
        self.assertFalse(ok)
        self.assertIn("GET /assessments | FAIL | HTTP 502", report)

    def test_workflow_not_gated_and_ai_flag_on_fails(self):
        workflow = GOOD_WORKFLOW.replace("workflow_run:", "push:").replace('RAG_ENABLED: "false"', 'RAG_ENABLED: "true"')
        self.write_repo(workflow=workflow, record_data=record())
        _ok, report = self.run_review()
        self.assertIn("not gated on CI", report)
        self.assertIn("not set to false: RAG_ENABLED", report)

    def test_failed_deployment_run_fails_record(self):
        self.write_repo(record_data=record(conclusion="failure"))
        ok, report = self.run_review()
        self.assertFalse(ok)
        self.assertIn("workflow conclusion 'failure'", report)

    def test_overriding_recommendation_needs_a_reason(self):
        self.write_repo(workflow=None, record_data=record())
        _ok, report = self.run_review(decision="Release", reviewer="Laz", comment="")
        self.assertIn("Decision NOT recorded", report)
        self.assertEqual(self.decisions(), [])
        _ok, report = self.run_review(decision="Release", reviewer="Laz", comment="Workflow added in the next PR")
        self.assertEqual(self.decisions()[0]["agreed_with_loop"], False)

    def test_reviewer_name_is_required(self):
        self.write_repo(record_data=record())
        _ok, report = self.run_review(decision="Release", reviewer=" ")
        self.assertIn("reviewer name is required", report)


if __name__ == "__main__":
    unittest.main()
