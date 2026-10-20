"""ACT step for Cloud Deployment Review mode.

Three kinds of evidence:
  1. static   - cloud-deployment.yml and the reusable deploy scripts in the repository
  2. record   - docs/release-2/cloud/deployment.json, written by whoever ran the deployment
  3. live     - read-only HTTP probes against the deployed frontends and backends
"""

import json
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_RECORD_FIELDS = ("platform", "deployed_at", "commit", "workflow_run_url", "conclusion",
                          "frontends", "backends")
PLATFORM_HINTS = {
    "Azure": ("azure/login", "az containerapp", "az webapp", "azure/container-apps-deploy-action"),
    "AWS": ("aws-actions/", "aws ecs", "amazon-ecs-deploy-task-definition"),
}


def workflow(name, ai_flags):
    """Static check of .github/workflows/<name>."""
    path = ROOT / ".github" / "workflows" / name
    if not path.exists():
        return {"exists": False, "path": str(path.relative_to(ROOT))}
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()
    platforms = [p for p, hints in PLATFORM_HINTS.items() if any(h in lowered for h in hints)]
    # Deployment must wait for CI: either triggered by other workflows completing, or a job that needs a test job.
    gated = bool(re.search(r"workflow_run\s*:", text)) or bool(re.search(r"^\s+needs\s*:", text, re.MULTILINE))
    flags_off = {flag: bool(re.search(rf"{flag}\s*[:=]\s*[\"']?false", text, re.IGNORECASE)) for flag in ai_flags}
    return {
        "exists": True,
        "path": str(path.relative_to(ROOT)),
        "platforms": platforms,
        "gated_on_ci": gated,
        "ai_flags_off": flags_off,
        "uses_secrets": "${{ secrets." in text,
    }


def deploy_scripts(directory):
    path = ROOT / directory
    files = sorted(p.name for p in path.iterdir() if p.is_file() and not p.name.startswith(".")) if path.is_dir() else []
    return {"path": directory, "files": files}


def deployment_record(evidence_file):
    path = ROOT / evidence_file
    if not path.exists():
        return {"present": False, "path": evidence_file}
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"present": True, "valid": False, "path": evidence_file, "error": f"invalid JSON: {exc}"}
    missing = [f for f in REQUIRED_RECORD_FIELDS if not record.get(f)]
    return {"present": True, "valid": not missing, "path": evidence_file, "missing_fields": missing, **record}


def _request(method, url, timeout, body=None, encoding="json"):
    try:
        if encoding == "form":
            response = requests.request(method, url, data=body, timeout=timeout)
        else:
            response = requests.request(method, url, json=body, timeout=timeout)
        return {"reachable": True, "status": response.status_code, "text": response.text[:400],
                "ms": round(response.elapsed.total_seconds() * 1000)}
    except requests.RequestException as exc:
        return {"reachable": False, "status": None, "text": f"{type(exc).__name__}", "ms": None}


def probe_page(url, timeout):
    result = _request("GET", url, timeout)
    result["ok"] = result["status"] == 200
    return result


def probe_read(base_url, path, timeout):
    result = _request("GET", base_url.rstrip("/") + path, timeout)
    result["ok"] = result["status"] == 200
    return result


def probe_ai(base_url, method, path, encoding, body, timeout):
    """Classify one AI route on a deployed backend.

    disabled - an error status (4xx/5xx) whose body says the feature is disabled
               (S2 answers 403, the others 503 - both count)
    answered - a 2xx response: the AI feature actually ran
    neither  - an error that does not mention 'disabled', e.g. flag still on but the AI server is unreachable
    """
    result = _request(method, base_url.rstrip("/") + path, timeout, body, encoding)
    status = result["status"]
    result["disabled"] = status is not None and status >= 400 and "disabled" in result["text"].lower()
    result["answered"] = status is not None and 200 <= status < 300
    return result
