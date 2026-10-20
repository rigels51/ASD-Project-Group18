"""Save one student's Release 2 testing evidence where the agentic loop Testing Review reads it.

  Pre-commit scan of your own files (run locally, from the repo root):
      python3 scripts/capture_test_evidence.py precommit --student 5

  Latest GitHub Actions run of your student-x.yml (needs the GitHub CLI `gh`, logged in):
      python3 scripts/capture_test_evidence.py ci --student 5

  ...or record a run by hand if you don't have `gh`:
      python3 scripts/capture_test_evidence.py ci --student 5 --run-url <url> --conclusion success --passed 7 --failed 0

Output: docs/release-2/testing/student-<n>-precommit.txt and student-<n>-ci.md
"""

import argparse
import json
import re
import shutil
import subprocess  # noqa: S404 - runs git / pre-commit / gh with fixed arguments
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "release-2" / "testing"

STUDENTS = {
    1: {"name": "Rigel Rivamonte", "folder": "student-1", "workflow": "RigelRivamonte.yml"},
    2: {"name": "Jeriko Arceo", "folder": "student-2", "workflow": "JerikoArceo.yml"},
    3: {"name": "Lazizbek Ismoilov", "folder": "student-3", "workflow": "student-3.yml"},
    4: {"name": "Yi Zhang", "folder": "student-4", "workflow": "YiZhang.yml"},
    5: {"name": "Vu Tien Thanh Nguyen", "folder": "student-5", "workflow": "student-5.yml"},
}


def _run(args):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True)  # noqa: S603 - fixed tools


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def precommit(student: int) -> int:
    info = STUDENTS[student]
    if not shutil.which("pre-commit"):
        sys.exit("pre-commit not installed: python3 -m pip install pre-commit && pre-commit install")
    files = _run(["git", "ls-files", info["folder"]]).stdout.split()
    if not files:
        sys.exit(f"No tracked files under {info['folder']}/")
    result = _run(["pre-commit", "run", "--color", "never", "--files", *files])
    commit = _run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    header = (
        f"# Student {student} - {info['name']} - pre-commit security scan\n"
        f"# date: {_now()}\n# commit: {commit}\n# scope: {info['folder']}/ ({len(files)} tracked files)\n"
        f"# hooks: ruff-security, detect-secrets, pip-audit (.pre-commit-config.yaml)\n"
        f"# exit_code: {result.returncode}\n\n"
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"student-{student}-precommit.txt"
    path.write_text(header + result.stdout + result.stderr, encoding="utf-8")
    print(result.stdout)
    print(f"Saved {path.relative_to(ROOT)} (exit code {result.returncode}: "
          f"{'all hooks passed' if result.returncode == 0 else 'findings - fix or document them'})")
    return 0


def _parse_counts(text: str):
    passed = failed = None
    for line in reversed(text.splitlines()):
        if " in " in line and ("passed" in line or "failed" in line):
            p = re.search(r"(\d+) passed", line)
            f = re.search(r"(\d+) failed", line)
            passed, failed = (int(p.group(1)) if p else 0), (int(f.group(1)) if f else 0)
            break
    return passed, failed


def ci(student: int, args) -> int:
    info = STUDENTS[student]
    fields = {"run_url": args.run_url, "conclusion": args.conclusion, "commit": None, "date": None,
              "tests_passed": args.passed, "tests_failed": args.failed}
    log_tail = ""
    if not args.run_url:
        if not shutil.which("gh"):
            sys.exit("GitHub CLI not found. Install it (brew install gh; gh auth login) or pass "
                     "--run-url/--conclusion/--passed/--failed by hand.")
        listing = _run(["gh", "run", "list", "--workflow", info["workflow"], "--limit", "1",
                        "--json", "databaseId,conclusion,url,headSha,createdAt"])
        runs = json.loads(listing.stdout or "[]")
        if listing.returncode != 0 or not runs:
            sys.exit(f"No runs found for {info['workflow']}: {listing.stderr.strip()}")
        run = runs[0]
        fields.update(run_url=run["url"], conclusion=run["conclusion"] or "in_progress",
                      commit=run["headSha"][:7], date=run["createdAt"])
        log = _run(["gh", "run", "view", str(run["databaseId"]), "--log"]).stdout
        test_lines = [ln.split("\t")[-1] for ln in log.splitlines()
                      if re.search(r"(PASSED|FAILED|ERROR)\s*\[|\d+ (passed|failed)", ln)]
        log_tail = "\n".join(test_lines[-40:])
        fields["tests_passed"], fields["tests_failed"] = _parse_counts(log_tail)
    fields["date"] = fields["date"] or _now()

    body = [f"# Student {student} - {info['name']} - post-commit CI evidence", "",
            f"- student: {student}",
            f"- workflow: .github/workflows/{info['workflow']}",
            f"- endpoints: {args.endpoints or 'NOT RECORDED - pass --endpoints'}"]
    body += [f"- {k}: {v if v is not None else 'unknown'}" for k, v in fields.items()]
    if log_tail:
        body += ["", "## Test output (from the GitHub Actions log)", "", "```", log_tail, "```"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"student-{student}-ci.md"
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    print("\n".join(body[:12]))
    print(f"\nSaved {path.relative_to(ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture Release 2 testing evidence for one student")
    parser.add_argument("kind", choices=["precommit", "ci"])
    parser.add_argument("--student", type=int, required=True, choices=sorted(STUDENTS))
    parser.add_argument("--endpoints", help='e.g. "GET /assessments; POST /assessments"')
    parser.add_argument("--run-url")
    parser.add_argument("--conclusion", choices=["success", "failure", "cancelled"])
    parser.add_argument("--passed", type=int)
    parser.add_argument("--failed", type=int)
    args = parser.parse_args()
    return precommit(args.student) if args.kind == "precommit" else ci(args.student, args)


if __name__ == "__main__":
    sys.exit(main())
