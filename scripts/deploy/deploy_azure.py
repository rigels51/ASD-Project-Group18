#!/usr/bin/env python3
"""Reusable deployment of the integrated Group 18 application to Azure Container Apps (Release 2).

Baseline cloud profile: frontend, backend/API and database microservices only.
AI-Mode, MCP, RAG and the Multi-Agent server are NOT deployed and every backend runs with
MCP_ENABLED / RAG_ENABLED / MULTI_AGENT_ENABLED = false.

    python3 scripts/deploy/deploy_azure.py plan       # print every command, change nothing
    python3 scripts/deploy/deploy_azure.py deploy     # create/update everything, write deployment.json
    python3 scripts/deploy/deploy_azure.py status     # list the apps and their URLs
    python3 scripts/deploy/deploy_azure.py destroy --yes   # delete the whole resource group

Needs: Azure CLI (az login done, or azure/login in GitHub Actions), Docker, git.
Same script locally and in .github/workflows/cloud-deployment.yml.

How it maps the Compose application onto Container Apps
  * one Container App per Compose service, same name, one replica (SQLite lives in the container)
  * frontends + backends get public HTTPS ingress (browsers call the backends directly);
    databases get internal ingress and are called as http://<app-name> inside the environment
  * the frontends hardcode http://localhost:<port>; a build copy is rewritten to the cloud URLs
    before the images are built, so no student has to change their code
  * images are built for linux/amd64 with Docker and pushed to Azure Container Registry
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess  # noqa: S404 - runs az / docker / git with argument lists, never a shell
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORD_FILE = ROOT / "docs" / "release-2" / "cloud" / "deployment.json"

RESOURCE_GROUP = os.getenv("AZ_RESOURCE_GROUP", "asd-group18-rg")
LOCATION = os.getenv("AZ_LOCATION", "australiaeast")
ENVIRONMENT = os.getenv("AZ_CONTAINERAPP_ENV", "asd-group18-env")
AI_OFF = {"MCP_ENABLED": "false", "RAG_ENABLED": "false", "MULTI_AGENT_ENABLED": "false", "FLASK_DEBUG": "false"}

# name = Compose service name = Container App name.
# record = key used in deployment.json / the agentic-loop Cloud Deployment Review.
SERVICES = [
    {"name": "student1-database", "kind": "database", "context": "student-1/database-service", "port": 5002},
    {"name": "student2-database", "kind": "database", "context": "student-2/database-service", "port": 5002},
    {"name": "student4-database", "kind": "database", "context": "student-4/database-service", "port": 5002},
    {"name": "assessment-database-service", "kind": "database", "context": "student-5/database", "port": 5022},

    {"name": "student1-enrolment", "kind": "backend", "record": "student1-backend", "context": ".",
     "dockerfile": "student-1/enrolment-service/Dockerfile", "port": 5001,
     "env": {"DATABASE_SERVICE_URL": "db:student1-database"}},
    {"name": "student2-backend", "kind": "backend", "record": "student2-backend", "context": ".",
     "dockerfile": "student-2/backend-service/Dockerfile", "port": 5001,
     "env": {"DATABASE_SERVICE_URL": "db:student2-database"}},
    {"name": "timetable-backend", "kind": "backend", "record": "timetable-backend", "context": "student-3/backend",
     "port": 5003},
    {"name": "student4-enrolment", "kind": "backend", "record": "student4-backend", "context": ".",
     "dockerfile": "student-4/enrolment-service/Dockerfile", "port": 5001,
     "env": {"DATABASE_SERVICE_URL": "db:student4-database", "STUDENT_SERVICE_URL": "db:student1-database"}},
    {"name": "assessment-service", "kind": "backend", "record": "assessment-backend", "context": ".",
     "dockerfile": "student-5/backend/Dockerfile", "port": 5021,
     "env": {"ASSESSMENT_DATABASE_SERVICE_URL": "db:assessment-database-service",
             "STUDENT_SERVICE_URL": "db:student1-database", "COURSE_SERVICE_URL": "db:student4-database"}},

    {"name": "homepage", "kind": "frontend", "record": "homepage", "context": ".",
     "dockerfile": "shared/frontend/Dockerfile", "port": 80, "rewrite": "shared/frontend"},
    {"name": "student1-frontend", "kind": "frontend", "record": "student1-frontend",
     "context": "student-1/frontend-service", "port": 80, "rewrite": "student-1/frontend-service"},
    {"name": "student2-frontend", "kind": "frontend", "record": "student2-frontend",
     "context": "student-2/frontend-service", "port": 80, "rewrite": "student-2/frontend-service"},
    {"name": "timetable-frontend", "kind": "frontend", "record": "timetable-frontend",
     "context": "student-3/frontend", "port": 80, "rewrite": "student-3/frontend"},
    {"name": "student4-frontend", "kind": "frontend", "record": "student4-frontend",
     "context": "student-4/frontend-service", "port": 80, "rewrite": "student-4/frontend-service"},
    {"name": "assessment-frontend-service", "kind": "frontend", "record": "assessment-frontend",
     "context": "student-5/frontend", "port": 80, "rewrite": "student-5/frontend"},
]

# Host port in docker-compose.yml -> Container App that serves it in the cloud.
LOCAL_PORTS = {
    5001: "student1-enrolment", 5011: "student2-backend", 5003: "timetable-backend",
    5031: "student4-enrolment", 5021: "assessment-service",
    8090: "homepage", 8080: "student1-frontend", 8082: "student2-frontend", 8003: "timetable-frontend",
    8081: "student4-frontend", 8085: "assessment-frontend-service",
}
LOCAL_URL = re.compile(r"http://(?:localhost|127\.0\.0\.1):(\d+)")
REWRITE_SUFFIXES = {".html", ".js", ".css"}
SMOKE_PATHS = {"student1-enrolment": "/students", "student2-backend": "/staff", "timetable-backend": "/timetable",
               "student4-enrolment": "/courses", "assessment-service": "/assessments"}

DRY_RUN = False


def log(msg):
    print(f"[deploy] {msg}", flush=True)


def run(args, capture=False, check=True, secret=False):
    shown = " ".join("***" if secret and i > 0 and args[i - 1] == "--registry-password" else a
                     for i, a in enumerate(args))
    print(f"  $ {shown}", flush=True)
    if DRY_RUN:
        return ""
    result = subprocess.run(args, cwd=ROOT, text=True,  # noqa: S603 - fixed tools, argument list
                            capture_output=capture, check=False)
    if result.returncode != 0:
        if check:
            if capture:
                sys.stderr.write(result.stdout + result.stderr)
            sys.exit(f"[deploy] FAILED: {args[0]} {args[1] if len(args) > 1 else ''} (exit {result.returncode})")
        return None
    return (result.stdout or "").strip() if capture else ""


def az(*args, capture=True, check=True, secret=False):
    return run(["az", *args, "--only-show-errors"], capture=capture, check=check, secret=secret)


def git_sha():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True,  # noqa: S603, S607
                              capture_output=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def registry_name(subscription_id):
    """Globally unique, stable per subscription: asdg18 + 8 hex chars."""
    return os.getenv("AZ_ACR_NAME") or "asdg18" + hashlib.sha256(subscription_id.encode()).hexdigest()[:8]


def public_url(app, domain):
    return f"https://{app}.{domain}"


def rewrite_tree(directory, domain):
    """Replace http://localhost:<port> with the cloud URL in every frontend file. Returns (changes, unmapped)."""
    changes, unmapped = 0, set()
    for path in sorted(Path(directory).rglob("*")):
        if path.suffix not in REWRITE_SUFFIXES or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")

        def swap(match):
            nonlocal changes
            port = int(match.group(1))
            if port not in LOCAL_PORTS:
                unmapped.add(f"{path.name}:{port}")
                return match.group(0)
            changes += 1
            return public_url(LOCAL_PORTS[port], domain)

        new = LOCAL_URL.sub(swap, text)
        if new != text:
            path.write_text(new, encoding="utf-8")
    return changes, unmapped


def make_build_copy(domain):
    """Copy the tracked files to a temp dir and rewrite the frontends there (the repo is never modified)."""
    files = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True,  # noqa: S603, S607
                           check=True).stdout.decode().split("\0")
    build = Path(tempfile.mkdtemp(prefix="g18-build-"))
    for rel in filter(None, files):
        src = ROOT / rel
        if src.is_file():
            dst = build / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    for svc in SERVICES:
        if svc.get("rewrite"):
            changes, unmapped = rewrite_tree(build / svc["rewrite"], domain)
            log(f"{svc['name']}: rewrote {changes} localhost URL(s)"
                + (f"; NOT mapped (left as is): {', '.join(sorted(unmapped))}" if unmapped else ""))
    return build


def image_ref(registry, svc, tag):
    return f"{registry}.azurecr.io/{svc['name']}:{tag}"


def build_and_push(build_dir, registry, tag, only):
    for svc in SERVICES:
        if only and svc["name"] not in only:
            continue
        context = build_dir / svc["context"]
        dockerfile = build_dir / (svc.get("dockerfile") or f"{svc['context']}/Dockerfile")
        log(f"build {svc['name']}")
        run(["docker", "buildx", "build", "--platform", "linux/amd64", "--provenance=false",
             "-t", image_ref(registry, svc, tag), "-f", str(dockerfile), str(context), "--push"])


def ensure_environment():
    if DRY_RUN or not az("containerapp", "env", "show", "-g", RESOURCE_GROUP, "-n", ENVIRONMENT,
                         "--query", "name", "-o", "tsv", check=False):
        az("containerapp", "env", "create", "-g", RESOURCE_GROUP, "-n", ENVIRONMENT, "-l", LOCATION,
           "-o", "none")


def app_exists(name):
    return bool(az("containerapp", "show", "-g", RESOURCE_GROUP, "-n", name, "--query", "name", "-o", "tsv",
                   check=False))


def database_url(app, domain):
    """Address a backend uses for its database.

    Azure creates Consumption environments as "express": allowInsecure is rejected, plain
    http://<app> is redirected to https://<app>.internal.<domain>, and the environment certificate
    does not cover that internal name (hostname mismatch). The public FQDN is covered, so databases
    get external HTTPS ingress. Known limitation: database APIs are reachable from the internet
    (see scripts/deploy/README.md - restricting them is the cloud endpoint-security bonus item).
    """
    return public_url(app, domain)


def env_vars(svc, domain):
    values = {k: (database_url(v.removeprefix("db:"), domain) if v.startswith("db:") else v)
              for k, v in svc.get("env", {}).items()}
    if svc["kind"] == "backend":
        values.update(AI_OFF)
    return [f"{k}={v}" for k, v in values.items()]


def deploy_app(svc, registry, tag, acr_user, acr_password, domain):
    name, image = svc["name"], image_ref(registry, svc, tag)
    ev = env_vars(svc, domain)
    if not DRY_RUN and app_exists(name):
        log(f"update {name}")
        args = ["containerapp", "update", "-g", RESOURCE_GROUP, "-n", name, "--image", image,
                "--min-replicas", "1", "--max-replicas", "1"]
        if ev:
            args += ["--set-env-vars", *ev]
        az(*args, capture=True)
        # Ingress is not changed by "update"; set it explicitly so an app created by an earlier
        # version of this script (e.g. internal-only databases) converges to the current design.
        az("containerapp", "ingress", "enable", "-g", RESOURCE_GROUP, "-n", name, "--type", "external",
           "--target-port", str(svc["port"]), "-o", "none", capture=True)
        return
    log(f"create {name}")
    args = ["containerapp", "create", "-g", RESOURCE_GROUP, "-n", name, "--environment", ENVIRONMENT,
            "--image", image, "--target-port", str(svc["port"]),
            "--ingress", "external",
            "--min-replicas", "1", "--max-replicas", "1", "--cpu", "0.25", "--memory", "0.5Gi",
            "--registry-server", f"{registry}.azurecr.io", "--registry-username", acr_user]
    if ev:
        args += ["--env-vars", *ev]
    az(*args, "--registry-password", acr_password, capture=True, secret=True)


def smoke(url, attempts=12, delay=10):
    if DRY_RUN:
        return "dry-run"
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=15) as response:  # noqa: S310 - https URLs we just deployed
                return response.status
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                return exc.code
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(delay)
    return None


def write_record(domain, tag, ok):
    server, repo, run_id = (os.getenv(k) for k in ("GITHUB_SERVER_URL", "GITHUB_REPOSITORY", "GITHUB_RUN_ID"))
    run_url = f"{server}/{repo}/actions/runs/{run_id}" if run_id else f"manual run of scripts/deploy/deploy_azure.py on {socket.gethostname()}"
    record = {
        "platform": f"Azure Container Apps ({LOCATION})",
        "deployed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": tag,
        "workflow_run_url": run_url,
        "conclusion": "success" if ok else "failure",
        "ai_profile": "baseline",
        "ai_enabled": [],
        "resource_group": RESOURCE_GROUP,
        "environment": ENVIRONMENT,
        "frontends": {s["record"]: public_url(s["name"], domain) for s in SERVICES if s["kind"] == "frontend"},
        "backends": {s["record"]: public_url(s["name"], domain) for s in SERVICES if s["kind"] == "backend"},
    }
    if DRY_RUN:
        print(json.dumps(record, indent=2))
        return record
    RECORD_FILE.parent.mkdir(parents=True, exist_ok=True)
    RECORD_FILE.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    log(f"wrote {RECORD_FILE.relative_to(ROOT)}")
    return record


def deploy(args):
    tag = args.tag or git_sha()
    only = set(args.only or [])
    unknown = only - {s["name"] for s in SERVICES}
    if unknown:
        sys.exit(f"[deploy] unknown service(s): {', '.join(sorted(unknown))}")
    for tool in ("az", "docker", "git"):
        if not DRY_RUN and not shutil.which(tool):
            sys.exit(f"[deploy] {tool} not found on PATH")

    log("1/6 Azure subscription")
    subscription = az("account", "show", "--query", "id", "-o", "tsv") or "00000000-dry-run"
    registry = registry_name(subscription)
    # One-time per subscription. A GitHub service principal scoped to the resource group may not be
    # allowed to register providers; by then they are registered, so a refusal is only a warning.
    for provider in ("Microsoft.App", "Microsoft.OperationalInsights", "Microsoft.ContainerRegistry"):
        if az("provider", "register", "-n", provider, "--wait", capture=True, check=False) is None:
            log(f"warning: could not register {provider} (fine if it is already registered)")

    log(f"2/6 resource group {RESOURCE_GROUP}, registry {registry}, environment {ENVIRONMENT} ({LOCATION})")
    az("group", "create", "-n", RESOURCE_GROUP, "-l", LOCATION, "-o", "none")
    if DRY_RUN or not az("acr", "show", "-n", registry, "--query", "name", "-o", "tsv", check=False):
        az("acr", "create", "-g", RESOURCE_GROUP, "-n", registry, "--sku", "Basic", "--admin-enabled", "true",
           "-l", LOCATION, "-o", "none")
    ensure_environment()
    domain = az("containerapp", "env", "show", "-g", RESOURCE_GROUP, "-n", ENVIRONMENT,
                "--query", "properties.defaultDomain", "-o", "tsv") or "<env-default-domain>"
    log(f"environment domain: {domain}")

    log("3/6 build copy with cloud URLs")
    build_dir = make_build_copy(domain)
    try:
        if not args.skip_build:
            log("4/6 build + push images (linux/amd64)")
            az("acr", "login", "-n", registry, capture=True)
            build_and_push(build_dir, registry, tag, only)
        else:
            log("4/6 build skipped (--skip-build)")
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)

    log("5/6 container apps (databases first, then backends, then frontends)")
    acr_user = az("acr", "credential", "show", "-n", registry, "--query", "username", "-o", "tsv") or registry
    acr_password = az("acr", "credential", "show", "-n", registry, "--query", "passwords[0].value", "-o", "tsv") or "***"
    for svc in SERVICES:
        if not only or svc["name"] in only:
            deploy_app(svc, registry, tag, acr_user, acr_password, domain)

    log("6/6 smoke test")
    failures = []
    for svc in SERVICES:
        if svc["kind"] == "database" or (only and svc["name"] not in only):
            continue
        url = public_url(svc["name"], domain) + SMOKE_PATHS.get(svc["name"], "/")
        status = smoke(url)
        print(f"  {svc['name']:<28} {url} -> {status}", flush=True)
        if status not in (200, "dry-run"):
            failures.append(svc["name"])
    if only:
        log("partial deploy (--only): deployment.json not rewritten")
    else:
        write_record(domain, tag, ok=not failures)
    if failures:
        sys.exit(f"[deploy] smoke test failed for: {', '.join(failures)} "
                 f"(az containerapp logs show -g {RESOURCE_GROUP} -n <app> --tail 50)")
    log(f"done - homepage: {public_url('homepage', domain)}")


def status(_args):
    az("containerapp", "list", "-g", RESOURCE_GROUP, "--query",
       "[].{app:name, url:properties.configuration.ingress.fqdn, external:properties.configuration.ingress.external,"
       " state:properties.runningStatus}", "-o", "table", capture=False)


def destroy(args):
    if not args.yes:
        sys.exit("[deploy] this deletes every resource in the group; re-run with --yes")
    az("group", "delete", "-n", RESOURCE_GROUP, "--yes", "--no-wait", capture=False)
    log(f"deleting {RESOURCE_GROUP} in the background")


def main(argv=None):
    global DRY_RUN
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "deploy"):
        p = sub.add_parser(name)
        p.add_argument("--tag", help="image tag (default: current git short SHA)")
        p.add_argument("--only", nargs="+", metavar="APP", help="build/deploy only these apps")
        p.add_argument("--skip-build", action="store_true", help="reuse images already in the registry")
    sub.add_parser("status")
    d = sub.add_parser("destroy")
    d.add_argument("--yes", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "plan":
        DRY_RUN = True
        deploy(args)
    elif args.command == "deploy":
        deploy(args)
    elif args.command == "status":
        status(args)
    else:
        destroy(args)


if __name__ == "__main__":
    main()
