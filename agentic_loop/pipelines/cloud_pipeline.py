"""Cloud Deployment Review mode: Plan -> Act -> Observe -> Adapt -> Human release decision.

Reviews the Release 2 cloud deployment of the integrated application:
  - cloud-deployment.yml runs after CI, targets Azure/AWS, and keeps AI-Mode, MCP, RAG and
    Multi-Agent disabled by default (baseline profile)
  - reusable deploy scripts exist
  - the deployment record (docs/release-2/cloud/deployment.json) shows a successful run
  - live, read-only probes: every frontend loads, every backend serves its data, every AI route is disabled
The rule-based result gives a recommended release decision; a person then records the final
decision, which is appended to the release-decision log.

Output:
  docs/release-2/agentic-loop/cloud-validation.md          (review / validation log)
  docs/release-2/agentic-loop/cloud-release-decisions.jsonl (one line per human release decision)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from agentic_loop.collectors import cloud_collector as collector
from agentic_loop.config.review_config import (
    CLOUD_AI_FLAGS,
    CLOUD_DECISIONS_LOG,
    CLOUD_DEPLOY_SCRIPTS_DIR,
    CLOUD_EVIDENCE_FILE,
    CLOUD_FRONTENDS,
    CLOUD_RELEASE_DECISIONS,
    CLOUD_SERVICES,
    CLOUD_TIMEOUT_SECONDS,
    CLOUD_WORKFLOW,
    OLLAMA_MODEL,
    OLLAMA_REVIEW_MODEL,
)
from agentic_loop.core.ai_runner import ask_model
from agentic_loop.core.reporter import Reporter

ROOT = Path(__file__).resolve().parents[2]
PROMPT_DIR = ROOT / "prompts" / "cloud"
BLOCKING = ("FAIL", "MISSING")


def _workflow_row(wf):
    if not wf["exists"]:
        return ("FAIL", f"{wf['path']} not found")
    problems = []
    if not wf["platforms"]:
        problems.append("no Azure or AWS deploy step found")
    if not wf["gated_on_ci"]:
        problems.append("not gated on CI (no workflow_run trigger or needs:)")
    flags_on = [f for f, off in wf["ai_flags_off"].items() if not off]
    if flags_on:
        problems.append(f"not set to false: {', '.join(flags_on)}")
    detail = (f"platform={'/'.join(wf['platforms']) or '-'}, gated on CI={wf['gated_on_ci']}, "
              f"AI flags off={sum(wf['ai_flags_off'].values())}/{len(wf['ai_flags_off'])}, "
              f"credentials from secrets={wf['uses_secrets']}")
    return ("FAIL", "; ".join(problems) + " - " + detail) if problems else ("PASS", detail)


def _record_row(record):
    if not record["present"]:
        return ("MISSING", f"no deployment record - after deploying, copy "
                           f"docs/release-2/cloud/deployment.example.json to {record['path']} and fill it in")
    if not record.get("valid"):
        return ("FAIL", record.get("error") or f"missing fields: {', '.join(record['missing_fields'])}")
    detail = (f"{record['platform']}, commit {record['commit']}, {record['deployed_at']}, "
              f"run {record['workflow_run_url']}")
    if record["conclusion"] != "success":
        return ("FAIL", f"workflow conclusion '{record['conclusion']}' - " + detail)
    return ("PASS", detail)


def _probe_detail(result):
    if not result["reachable"]:
        return f"unreachable ({result['text']})"
    return f"HTTP {result['status']} in {result['ms']} ms"


def recommend(rows):
    results = {r[2] for r in rows}
    if results & set(BLOCKING):
        return "Do not release"
    if "WARN" in results:
        return "Release with conditions"
    return "Release"


def _ask_decision(recommended):
    print(f"\nHUMAN RELEASE DECISION (agentic loop recommends: {recommended})")
    for i, name in enumerate(CLOUD_RELEASE_DECISIONS, 1):
        print(f"  {i} - {name}")
    choice = input("Decision (1-3, Enter to leave pending): ").strip()
    if not choice:
        return None, None, None
    try:
        decision = CLOUD_RELEASE_DECISIONS[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice - decision left pending.")
        return None, None, None
    return decision, input("Your name: ").strip(), input("Reason: ").strip()


def record_decision(decision, reviewer, comment, recommended, rows, record):
    """Validate and append one human release decision. Raises ValueError on invalid input."""
    if decision not in CLOUD_RELEASE_DECISIONS:
        raise ValueError(f"decision must be one of: {', '.join(CLOUD_RELEASE_DECISIONS)}")
    if not (reviewer or "").strip():
        raise ValueError("reviewer name is required")
    if decision != recommended and not (comment or "").strip():
        raise ValueError(f"a reason is required when the decision differs from the recommendation ({recommended})")
    if decision == "Release" and recommended == "Do not release" and not (comment or "").strip():
        raise ValueError("a reason is required to release against a 'Do not release' recommendation")
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "decision": decision,
        "reviewer": reviewer.strip()[:80],
        "comment": (comment or "").strip()[:1000],
        "recommended": recommended,
        "agreed_with_loop": decision == recommended,
        "deployment_commit": record.get("commit"),
        "platform": record.get("platform"),
        "results": {k: sum(1 for r in rows if r[2] == k) for k in ("PASS", "WARN", "MISSING", "FAIL")},
        "blocking": [f"{r[0]} / {r[1]}: {r[2]}" for r in rows if r[2] in BLOCKING],
    }
    path = ROOT / CLOUD_DECISIONS_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def run(use_ai=True, decision=None, reviewer=None, comment=None, interactive=True):
    report = Reporter("cloud", release="release-2")

    # ---------- PLAN ----------
    report.stage("PLAN", "Decide whether the Release 2 cloud deployment can be released.")
    report.line(f"1. Workflow: {CLOUD_WORKFLOW} runs after CI, deploys to Azure or AWS, sets "
                f"{', '.join(CLOUD_AI_FLAGS)} to false (baseline profile).")
    report.line(f"2. Scripts: reusable deploy scripts in {CLOUD_DEPLOY_SCRIPTS_DIR}/.")
    report.line(f"3. Record: {CLOUD_EVIDENCE_FILE} shows a successful deployment (platform, commit, run URL, endpoints).")
    report.line("4. Live: every frontend loads, every backend read route returns 200, every AI route reports disabled.")
    report.line("5. Human: a person records the final release decision.")

    # ---------- ACT ----------
    report.stage("ACT", "Reading the workflow, scripts and deployment record; probing the deployed endpoints (read-only).")
    wf = collector.workflow(CLOUD_WORKFLOW, CLOUD_AI_FLAGS)
    scripts = collector.deploy_scripts(CLOUD_DEPLOY_SCRIPTS_DIR)
    record = collector.deployment_record(CLOUD_EVIDENCE_FILE)
    rows = [("group", f"workflow {CLOUD_WORKFLOW}", *_workflow_row(wf)),
            ("group", "deploy scripts",
             *(("PASS", ", ".join(scripts["files"])) if scripts["files"]
               else ("MISSING", f"no scripts in {scripts['path']}/"))),
            ("group", "deployment record", *_record_row(record))]

    frontends = record.get("frontends") or {}
    backends = record.get("backends") or {}
    ai_enabled = set(record.get("ai_enabled") or [])
    latencies = []
    if record.get("valid"):
        for name in CLOUD_FRONTENDS:
            if name not in frontends:
                rows.append((name, "frontend loads", "MISSING", "no URL in deployment record"))
                continue
            result = collector.probe_page(frontends[name], CLOUD_TIMEOUT_SECONDS)
            rows.append((name, "frontend loads", "PASS" if result["ok"] else "FAIL",
                         f"{frontends[name]} - {_probe_detail(result)}"))
        for name, svc in CLOUD_SERVICES.items():
            base = backends.get(name)
            if not base:
                rows.append((svc["owner"], f"{name} read", "MISSING", "no URL in deployment record"))
                continue
            read = collector.probe_read(base, svc["read"], CLOUD_TIMEOUT_SECONDS)
            if read["ms"] is not None:
                latencies.append(read["ms"])
            rows.append((svc["owner"], f"GET {svc['read']}", "PASS" if read["ok"] else "FAIL", _probe_detail(read)))
            for method, path, encoding, body in svc["ai"]:
                ai = collector.probe_ai(base, method, path, encoding, body, CLOUD_TIMEOUT_SECONDS)
                if not ai["reachable"]:
                    rows.append((svc["owner"], f"{method} {path} disabled", "FAIL", _probe_detail(ai)))
                elif name in ai_enabled:
                    rows.append((svc["owner"], f"{method} {path} (bonus: enabled)",
                                 "PASS" if ai["answered"] else "WARN",
                                 f"{_probe_detail(ai)} - declared enabled; "
                                 + ("answered" if ai["answered"] else "did not answer")))
                elif ai["disabled"]:
                    rows.append((svc["owner"], f"{method} {path} disabled", "PASS",
                                 f"{_probe_detail(ai)}, response says disabled"))
                elif ai["answered"]:
                    rows.append((svc["owner"], f"{method} {path} disabled", "FAIL",
                                 f"{_probe_detail(ai)} - AI route answered, but the baseline cloud profile requires it disabled"))
                else:
                    rows.append((svc["owner"], f"{method} {path} disabled", "WARN",
                                 f"{_probe_detail(ai)} - unavailable but not reporting 'disabled': "
                                 "set its *_ENABLED flag to false in the cloud deployment"))

    # ---------- OBSERVE ----------
    counts = {k: sum(1 for r in rows if r[2] == k) for k in ("PASS", "WARN", "MISSING", "FAIL")}
    recommended = recommend(rows)
    latency = f" Backend read latency: max {max(latencies)} ms, avg {round(sum(latencies) / len(latencies))} ms." if latencies else ""
    report.stage("OBSERVE", f"{counts['PASS']} pass, {counts['WARN']} warn, {counts['MISSING']} missing, "
                            f"{counts['FAIL']} fail.{latency} Recommended release decision: {recommended}.")
    report.table(["Owner", "Check", "Result", "Detail"], rows)

    # ---------- ADAPT ----------
    report.stage("ADAPT")
    actions = [r for r in rows if r[2] != "PASS"]
    for owner, check, result, detail in actions:
        report.line(f"{owner} / {check}: {result} -> {detail}")
    if not actions:
        report.line("Every cloud check passed; no rule-based adaptation needed.")

    if use_ai:
        evidence = "\n".join(f"{r[0]} | {r[1]} -> {r[2]}: {r[3]}" for r in rows)
        evidence += f"\nRule-based recommendation: {recommended}"
        impl, err = ask_model(OLLAMA_MODEL, (PROMPT_DIR / "implementation" / "cloud_review_prompt.txt")
                              .read_text(encoding="utf-8"), f"Evidence:\n{evidence}", max_tokens=160)
        report.line(f"Implementation agent ({OLLAMA_MODEL if impl else 'unavailable'}):")
        report.block(impl or err)
        review, err = ask_model(OLLAMA_REVIEW_MODEL, (PROMPT_DIR / "review" / "cloud_review_prompt.txt")
                                .read_text(encoding="utf-8"),
                                f"Implementation assessment:\n{impl or 'n/a'}\n\nEvidence:\n{evidence}", max_tokens=160)
        report.line(f"Review agent ({OLLAMA_REVIEW_MODEL if review else 'unavailable'}):")
        report.block(review or err)

    # ---------- HUMAN RELEASE DECISION ----------
    report.stage("HUMAN RELEASE DECISION", f"Loop recommendation: {recommended}.")
    if decision is None and interactive and sys.stdin.isatty():
        decision, reviewer, comment = _ask_decision(recommended)
    if decision is None:
        report.line("PENDING - record it with: python -m agentic_loop.main --mode cloud "
                    "--decision \"<Release | Release with conditions | Do not release>\" --reviewer <name> --comment \"<reason>\"")
    else:
        try:
            entry = record_decision(decision, reviewer, comment, recommended, rows, record)
        except ValueError as exc:
            report.line(f"Decision NOT recorded: {exc}")
        else:
            report.line(f"{entry['decision']} by {entry['reviewer']} at {entry['timestamp']} "
                        f"({'agrees with' if entry['agreed_with_loop'] else 'overrides'} the loop recommendation).")
            report.line(f"Reason: {entry['comment'] or '-'}")
            report.line(f"Logged to {CLOUD_DECISIONS_LOG}")

    report.save()
    return recommended != "Do not release"
