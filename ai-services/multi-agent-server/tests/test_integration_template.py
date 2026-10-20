"""The drop-in blueprint students copy must work against the real server API."""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

from flask import Flask

SERVER_DIR = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ma_template", SERVER_DIR / "integration" / "multi_agent_mode.py")
template = importlib.util.module_from_spec(spec)
spec.loader.exec_module(template)
template.DOMAIN = "students"


class TemplateTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.register_blueprint(template.multi_agent_bp)
        self.client = app.test_client()

    def test_run_forwards_domain(self):
        with mock.patch.object(template.requests, "request") as req:
            req.return_value.json.return_value = {"workflow_id": "w"}
            req.return_value.status_code = 200
            r = self.client.post("/multi-agent/run", json={"question": "Who is on leave?"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(req.call_args.kwargs["json"]["domain"], "students")

    def test_disabled_flag(self):
        with mock.patch.object(template, "MULTI_AGENT_ENABLED", False):
            self.assertEqual(self.client.post("/multi-agent/run", json={"question": "x"}).status_code, 503)

    def test_unreachable_server(self):
        with mock.patch.object(template.requests, "request", side_effect=template.requests.ConnectionError()):
            self.assertEqual(self.client.get("/multi-agent/health").status_code, 503)


if __name__ == "__main__":
    unittest.main()
