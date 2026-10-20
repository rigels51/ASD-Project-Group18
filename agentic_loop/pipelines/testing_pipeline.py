"""Testing Review mode: Plan -> Act -> Observe -> Adapt over the Release 2 testing evidence.

Reviews (1) the shared pre-commit security setup, (2) each student's pre-commit scan report,
(3) each student's post-commit CI endpoint-test evidence and student-x.yml workflow.
Output: docs/release-2/agentic-loop/testing-validation.md
"""

from pathlib import Path

from agentic_loop.collectors import testing_collector as collector
from agentic_loop.config.review_config import (
    MIN_ENDPOINTS_PER_STUDENT,
    OLLAMA_MODEL,
    OLLAMA_REVIEW_MODEL,
    REQUIRED_PRECOMMIT_HOOKS,
    TESTING_EVIDENCE_DIR,
    TESTING_STUDENTS,
)
from agentic_loop.core.ai_runner import ask_model
from agentic_loop.core.reporter import Reporter

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts" / "testing"


def _precommit_verdict(pc, number):
    if not pc["present"]:
        return "MISSING", f"no scan captured - run: python3 scripts/capture_test_evidence.py precommit --student {number}"
    failed = [h for h, s in pc["hooks"].items() if s == "Failed"]
    ran = [h for h, s in pc["hooks"].items() if s != "Skipped"]
    detail = (f"{len(ran)}/{len(pc['hooks'])} hooks ran; ruff {pc['ruff_finding_count']} "
              f"({', '.join(pc['ruff_findings']) or 'none'}), secrets {pc['secrets_found']}, "
              f"vulnerable deps {pc['vulnerabilities']} [{pc['date']}]")
    if len(pc["hooks"]) < len(REQUIRED_PRECOMMIT_HOOKS):
        return "FAIL", "not all required hooks in the report - " + detail
    return ("PASS", detail) if not failed else ("FINDINGS", f"failed: {', '.join(failed)}; " + detail)


def _ci_verdict(ci, wf, number):
    if not wf["exists"]:
        return "FAIL", "workflow file missing from .github/workflows/"
    if not ci["present"]:
        return "MISSING", f"no CI run captured - after a green run: python3 scripts/capture_test_evidence.py ci --student {number}"
    detail = (f"{ci['conclusion']}, {ci['tests_passed']} passed / {ci['tests_failed']} failed, "
              f"endpoints: {'; '.join(ci['endpoints']) or 'none recorded'}")
    if ci["conclusion"] != "success" or (ci["tests_failed"] or 0) > 0:
        return "FAIL", detail
    if len(ci["endpoints"]) < MIN_ENDPOINTS_PER_STUDENT:
        return "FAIL", f"fewer than {MIN_ENDPOINTS_PER_STUDENT} endpoints evidenced - " + detail
    if not ci["tests_passed"]:
        return "FAIL", "no passing tests recorded - " + detail
    return "PASS", detail


def run(use_ai=True):
    report = Reporter("testing", release="release-2")

    # ---------- PLAN ----------
    report.stage("PLAN", "Review Release 2 testing evidence for all five students.")
    report.line("1. Shared setup: .pre-commit-config.yaml defines ruff-security, detect-secrets and pip-audit.")
    report.line("2. Pre-commit: each student's scan report exists and every hook passed (findings fixed or documented).")
    report.line(f"3. CI: each student's student-x.yml exists, ran green on GitHub, and tested >= {MIN_ENDPOINTS_PER_STUDENT} endpoints.")
    report.line(f"Evidence folder: {TESTING_EVIDENCE_DIR}/")

    # ---------- ACT ----------
    report.stage("ACT", "Reading configuration, scan reports and CI run evidence.")
    setup = collector.precommit_setup(REQUIRED_PRECOMMIT_HOOKS)
    setup_ok = setup["config_exists"] and not setup["missing_hooks"] and setup["secrets_baseline"]
    rows = [("group", "pre-commit setup", "PASS" if setup_ok else "FAIL",
             f"config={setup['config_exists']}, missing hooks={setup['missing_hooks'] or 'none'}, "
             f"secrets baseline={setup['secrets_baseline']}, ruff config={setup['ruff_config']}")]
    per_student = []
    for number, info in TESTING_STUDENTS.items():
        pc = collector.precommit_evidence(TESTING_EVIDENCE_DIR, number)
        ci = collector.ci_evidence(TESTING_EVIDENCE_DIR, number)
        wf = collector.workflow_file(info["workflow"])
        pc_result, pc_detail = _precommit_verdict(pc, number)
        ci_result, ci_detail = _ci_verdict(ci, wf, number)
        label = f"S{number} {info['name']}"
        rows.append((label, "pre-commit scan", pc_result, pc_detail))
        rows.append((label, f"CI {info['workflow']}", ci_result, ci_detail
                     + ("" if wf["ai_flags_off"] or not wf["exists"] else " (warning: MULTI_AGENT_ENABLED not set in workflow)")))
        per_student.append((number, info["name"], pc_result, ci_result, ci.get("run_url")))

    # ---------- OBSERVE ----------
    counts = {k: sum(1 for r in rows if r[2] == k) for k in ("PASS", "FINDINGS", "MISSING", "FAIL")}
    complete = [f"S{n}" for n, _name, pc, ci, _url in per_student if pc == "PASS" and ci == "PASS"]
    report.stage("OBSERVE", f"{counts['PASS']} pass, {counts['FINDINGS']} with findings, "
                            f"{counts['MISSING']} missing, {counts['FAIL']} fail. "
                            f"Fully evidenced students: {', '.join(complete) or 'none yet'}.")
    report.table(["Owner", "Check", "Result", "Detail"], rows)
    report.table(["Student", "Pre-commit", "CI", "CI run"],
                 [(f"S{n} {name}", pc, ci, url or "-") for n, name, pc, ci, url in per_student])

    # ---------- ADAPT ----------
    report.stage("ADAPT")
    actions = [r for r in rows if r[2] != "PASS"]
    for owner, check, result, detail in actions:
        report.line(f"{owner} / {check}: {result} -> {detail}")
    if not actions:
        report.line("All testing evidence complete and passing; no rule-based adaptation needed.")

    if use_ai:
        evidence = "\n".join(f"{r[0]} | {r[1]} -> {r[2]}: {r[3]}" for r in rows)
        impl, err = ask_model(OLLAMA_MODEL, (PROMPT_DIR / "implementation" / "testing_review_prompt.txt")
                              .read_text(encoding="utf-8"), f"Evidence:\n{evidence}", max_tokens=160)
        report.line(f"Implementation agent ({OLLAMA_MODEL if impl else 'unavailable'}):")
        report.block(impl or err)
        review, err = ask_model(OLLAMA_REVIEW_MODEL, (PROMPT_DIR / "review" / "testing_review_prompt.txt")
                                .read_text(encoding="utf-8"),
                                f"Implementation assessment:\n{impl or 'n/a'}\n\nEvidence:\n{evidence}", max_tokens=160)
        report.line(f"Review agent ({OLLAMA_REVIEW_MODEL if review else 'unavailable'}):")
        report.block(review or err)

    report.save()
    return not actions
