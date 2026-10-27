"""Offline tests for deploy_azure.py - no Azure account, no Docker daemon needed.

    python3 -m unittest scripts.deploy.test_deploy_azure -v      # from the repository root
"""

import contextlib
import io
import json
import re
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "deploy"))
sys.path.insert(0, str(ROOT))

import deploy_azure as d  # noqa: E402
from agentic_loop.config import review_config as cfg  # noqa: E402

DOMAIN = "calmsky-1234.australiaeast.azurecontainerapps.io"


def compose_services():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    return set(re.findall(r"^    ([a-z0-9-]+):\s*$", text.split("\nvolumes:")[0], re.MULTILINE))


def run_plan(*extra):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        d.main(["plan", *extra])
    d.DRY_RUN = False
    return out.getvalue()


class ServiceMapTests(unittest.TestCase):
    def test_every_compose_service_is_deployed(self):
        self.assertEqual(compose_services(), {s["name"] for s in d.SERVICES})

    def test_app_names_are_valid_container_app_names(self):
        for svc in d.SERVICES:
            self.assertRegex(svc["name"], r"^[a-z][a-z0-9-]{0,30}[a-z0-9]$", svc["name"])

    def test_dockerfiles_exist_and_ports_match_expose(self):
        for svc in d.SERVICES:
            dockerfile = ROOT / (svc.get("dockerfile") or f"{svc['context']}/Dockerfile")
            self.assertTrue(dockerfile.exists(), dockerfile)
            exposed = re.findall(r"^EXPOSE\s+(\d+)", dockerfile.read_text(encoding="utf-8"), re.MULTILINE)
            self.assertIn(str(svc["port"]), exposed, f"{svc['name']}: target port vs EXPOSE {exposed}")

    def test_backends_call_databases_over_https(self):
        names = {s["name"] for s in d.SERVICES}
        for svc in (s for s in d.SERVICES if s["kind"] == "backend"):
            env = dict(item.split("=", 1) for item in d.env_vars(svc, DOMAIN))
            for key, value in env.items():
                if not key.endswith("_URL"):
                    continue
                match = re.fullmatch(rf"https://([a-z0-9-]+)\.{re.escape(DOMAIN)}", value)
                self.assertIsNotNone(match, f"{svc['name']} {key}={value}")
                self.assertIn(match.group(1), names)
                self.assertEqual(next(s for s in d.SERVICES if s["name"] == match.group(1))["kind"], "database")

    def test_no_allow_insecure_anywhere(self):
        self.assertNotIn("--allow-insecure", run_plan())

    def test_every_backend_runs_with_ai_disabled(self):
        for svc in (s for s in d.SERVICES if s["kind"] == "backend"):
            env = dict(item.split("=", 1) for item in d.env_vars(svc, DOMAIN))
            for flag in cfg.CLOUD_AI_FLAGS:
                self.assertEqual(env[flag], "false", f"{svc['name']} {flag}")

    def test_only_student4_disables_ai_mode_in_baseline_cloud_profile(self):
        backends = {
            svc["name"]: dict(item.split("=", 1) for item in d.env_vars(svc, DOMAIN))
            for svc in d.SERVICES
            if svc["kind"] == "backend"
        }
        self.assertEqual(backends["student4-enrolment"]["AI_MODE_ENABLED"], "false")
        for name, env in backends.items():
            if name != "student4-enrolment":
                self.assertNotIn("AI_MODE_ENABLED", env, name)

    def test_student4_cloud_review_matches_deployed_disabled_features(self):
        service = cfg.CLOUD_SERVICES["student4-backend"]
        self.assertEqual(service["read"], "/courses")
        self.assertEqual(service["disabled_status"], 503)
        probes = {(method, path, encoding) for method, path, encoding, _body in service["ai"]}
        self.assertEqual(probes, {
            ("POST", "/ask", "form"),
            ("POST", "/mcp/run", "form"),
            ("POST", "/rag/answer", "form"),
            ("POST", "/multi-agent/run", "json"),
        })

        deployed = next(svc for svc in d.SERVICES if svc.get("record") == "student4-backend")
        env = dict(item.split("=", 1) for item in d.env_vars(deployed, DOMAIN))
        for flag in ("AI_MODE_ENABLED", "MCP_ENABLED", "RAG_ENABLED", "MULTI_AGENT_ENABLED"):
            self.assertEqual(env[flag], "false")

    def test_databases_use_https_ingress_not_plain_http(self):
        plan = run_plan()
        for svc in (s for s in d.SERVICES if s["kind"] == "database"):
            line = next(ln for ln in plan.splitlines() if f"containerapp create -g asd-group18-rg -n {svc['name']} " in ln)
            self.assertIn("--ingress external", line)
            self.assertNotIn("--allow-insecure", line)

    def test_record_keys_match_the_cloud_review(self):
        frontends = {s["record"] for s in d.SERVICES if s["kind"] == "frontend"}
        backends = {s["record"] for s in d.SERVICES if s["kind"] == "backend"}
        self.assertEqual(frontends, set(cfg.CLOUD_FRONTENDS))
        self.assertEqual(backends, set(cfg.CLOUD_SERVICES))

    def test_smoke_paths_are_the_cloud_review_read_routes(self):
        for svc in (s for s in d.SERVICES if s["kind"] == "backend"):
            self.assertEqual(d.SMOKE_PATHS[svc["name"]], cfg.CLOUD_SERVICES[svc["record"]]["read"])


class RewriteTests(unittest.TestCase):
    def setUp(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.build = d.make_build_copy(DOMAIN)
        self.log = out.getvalue()
        self.addCleanup(shutil.rmtree, self.build, ignore_errors=True)

    def test_no_localhost_left_and_nothing_unmapped(self):
        self.assertNotIn("NOT mapped", self.log)
        for svc in (s for s in d.SERVICES if s.get("rewrite")):
            for path in (self.build / svc["rewrite"]).rglob("*"):
                if path.suffix in d.REWRITE_SUFFIXES:
                    self.assertNotRegex(path.read_text(encoding="utf-8"), r"localhost|127\.0\.0\.1", str(path))

    def test_repository_files_are_not_modified(self):
        self.assertIn('const API_BASE = "http://127.0.0.1:5003";',
                      (ROOT / "student-3/frontend/index.html").read_text(encoding="utf-8"))

    def test_timetable_frontend_points_at_cloud_backend(self):
        html = (self.build / "student-3/frontend/index.html").read_text(encoding="utf-8")
        self.assertIn(f'const API_BASE = "https://timetable-backend.{DOMAIN}";', html)
        self.assertIn(f'href="https://homepage.{DOMAIN}"', html)

    def test_homepage_links_every_frontend(self):
        html = (self.build / "shared/frontend/homepage.html").read_text(encoding="utf-8")
        for app in ("student1-frontend", "student2-frontend", "timetable-frontend", "student4-frontend",
                    "assessment-frontend-service"):
            self.assertIn(f"https://{app}.{DOMAIN}", html)


class PlanTests(unittest.TestCase):
    def test_plan_creates_every_app_once_and_writes_a_valid_record(self):
        plan = run_plan()
        for svc in d.SERVICES:
            self.assertEqual(plan.count(f"containerapp create -g asd-group18-rg -n {svc['name']} "), 1, svc["name"])
        record = json.loads(plan[plan.index("{\n"):plan.rindex("}") + 1])
        for field in ("platform", "deployed_at", "commit", "workflow_run_url", "conclusion", "frontends", "backends"):
            self.assertTrue(record[field], field)
        self.assertEqual(record["ai_profile"], "baseline")
        self.assertEqual(record["ai_enabled"], [])

    def test_only_limits_builds_and_apps(self):
        plan = run_plan("--only", "timetable-backend", "timetable-frontend")
        self.assertEqual(plan.count("docker buildx build"), 2)
        self.assertEqual(plan.count("containerapp create"), 2)

    def test_registry_password_is_never_printed(self):
        plan = run_plan()
        for line in plan.splitlines():
            if "--registry-password" in line:
                self.assertRegex(line, r"--registry-password \*\*\*")

    def test_unknown_service_is_rejected(self):
        with self.assertRaises(SystemExit):
            run_plan("--only", "not-a-service")

    def test_destroy_needs_confirmation(self):
        with self.assertRaises(SystemExit):
            d.main(["destroy"])


if __name__ == "__main__":
    unittest.main()
