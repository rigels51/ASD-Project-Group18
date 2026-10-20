"""ACT step for Testing Review mode: read pre-commit and CI evidence from the repository."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK_LINE = re.compile(r"^(?P<name>.+?)\.{3,}(?P<status>Passed|Failed|Skipped|\(no files to check\)Skipped)\s*$")
RUFF_FINDING = re.compile(r"^\s*(?:\S+:\d+:\d+: )?(S\d{3})\b", re.MULTILINE)


def precommit_setup(required_hooks):
    """Static check of the shared pre-commit configuration."""
    config = ROOT / ".pre-commit-config.yaml"
    text = config.read_text(encoding="utf-8") if config.exists() else ""
    return {
        "config_exists": config.exists(),
        "missing_hooks": [h for h in required_hooks if f"id: {h}" not in text],
        "secrets_baseline": (ROOT / ".secrets.baseline").exists(),
        "ruff_config": (ROOT / "ruff.toml").exists() or (ROOT / "pyproject.toml").exists(),
    }


def precommit_evidence(evidence_dir, student):
    path = ROOT / evidence_dir / f"student-{student}-precommit.txt"
    if not path.exists():
        return {"present": False, "path": str(path.relative_to(ROOT))}
    text = path.read_text(encoding="utf-8")
    hooks = {}
    for line in text.splitlines():
        match = HOOK_LINE.match(line.strip())
        if match:
            hooks[match.group("name").strip()] = "Skipped" if "Skipped" in match.group("status") else match.group("status")
    exit_code = re.search(r"# exit_code: (\d+)", text)
    date = re.search(r"# date: (\S+)", text)
    vulns = re.search(r"Found (\d+) known vulnerabilit", text)
    return {
        "present": True,
        "path": str(path.relative_to(ROOT)),
        "date": date.group(1) if date else None,
        "exit_code": int(exit_code.group(1)) if exit_code else None,
        "hooks": hooks,
        "ruff_findings": sorted(set(RUFF_FINDING.findall(text))),
        "ruff_finding_count": len(RUFF_FINDING.findall(text)),
        "secrets_found": text.count("Secret Type:"),
        "vulnerabilities": int(vulns.group(1)) if vulns else 0,
    }


def ci_evidence(evidence_dir, student):
    path = ROOT / evidence_dir / f"student-{student}-ci.md"
    if not path.exists():
        return {"present": False, "path": str(path.relative_to(ROOT))}
    fields = dict(re.findall(r"^- (\w+): (.*)$", path.read_text(encoding="utf-8"), re.MULTILINE))

    def as_int(key):
        try:
            return int(fields.get(key, ""))
        except ValueError:
            return None

    endpoints = [e.strip() for e in fields.get("endpoints", "").split(";")
                 if e.strip() and not e.startswith("NOT RECORDED")]
    return {
        "present": True,
        "path": str(path.relative_to(ROOT)),
        "workflow": fields.get("workflow"),
        "run_url": fields.get("run_url"),
        "conclusion": fields.get("conclusion"),
        "date": fields.get("date"),
        "endpoints": endpoints,
        "tests_passed": as_int("tests_passed"),
        "tests_failed": as_int("tests_failed"),
    }


def workflow_file(workflow):
    path = ROOT / ".github" / "workflows" / workflow
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return {
        "exists": path.exists(),
        "runs_tests": bool(re.search(r"pytest|unittest", text)),
        "ai_flags_off": "MULTI_AGENT_ENABLED" in text,
    }
