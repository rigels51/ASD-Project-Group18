"""Multi-Agent Review mode: Plan -> Act -> Observe -> Adapt against the shared Multi-Agent server.

Reviews (1) the server implementation, (2) live Planner -> Worker -> Reviewer runs for every
feature domain, and (3) the workflow history / coordination audit evidence, including human
decisions. Output: docs/release-2/agentic-loop/multi-agent-validation.md
"""

import json
from pathlib import Path

from agentic_loop.collectors import multi_agent_collector as collector
from agentic_loop.config.review_config import (
    MULTI_AGENT_CASES,
    MULTI_AGENT_SERVER_URL,
    OLLAMA_MODEL,
    OLLAMA_REVIEW_MODEL,
)
from agentic_loop.core.ai_runner import ask_model
from agentic_loop.core.reporter import Reporter

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts" / "multi-agent"
EXPECTED_EVENTS = ["planner_completed", "worker_completed", "reviewer_completed", "awaiting_human_review"]


def _prompt(name):
    return (PROMPT_DIR / name).read_text(encoding="utf-8").strip()


def _evaluate(case, wf):
    """Return (passed, detail) for one live workflow run."""
    if wf.get("status") not in {"pending_human_review", "approved", "corrected", "partially_approved", "rejected"}:
        return False, f"workflow did not reach human review: {wf.get('status')} {wf.get('error', '')}"[:140]
    worker, review = wf["worker_result"], wf["reviewer_result"]
    agents = wf.get("participating_agents", [])
    if agents[:3] != ["planner_agent", "worker_agent", "reviewer_agent"]:
        return False, f"unexpected agent sequence {agents}"
    detail = (f"evidence={worker['evidence_count']}, risk={review['risk_level']}, "
              f"recommends {review['recommended_decision']}, worker={worker.get('model')}")
    if case["expect"] == "evidence":
        if worker["evidence_count"] == 0:
            return False, "no evidence retrieved - " + "; ".join(worker.get("source_errors") or ["filters matched nothing"])
        if review["risk_level"] == "high":
            return False, "reviewer flagged high risk - " + detail
        return True, detail
    if worker["evidence_count"] == 0 and review["risk_level"] == "high":
        return True, "no evidence and reviewer correctly flagged high risk"
    return False, "expected no evidence + high risk, got " + detail


def run(use_ai=True):
    report = Reporter("multi-agent", release="release-2")

    # ---------- PLAN ----------
    report.stage("PLAN", f"Review the shared Multi-Agent server at {MULTI_AGENT_SERVER_URL}.")
    report.line("1. Static check: required agent/coordinator files exist and the coordinator calls every agent and the human-review step.")
    report.line("2. Health check: server running, three agents + human reviewer registered.")
    report.line(f"3. Run {len(MULTI_AGENT_CASES)} live Planner -> Worker -> Reviewer workflows (one per feature domain + one no-evidence case).")
    report.line("4. Inspect workflow_history.jsonl / coordination_audit.jsonl: handoffs logged, human decisions recorded.")

    # ---------- ACT ----------
    report.stage("ACT", "Collecting implementation, live-run and audit evidence.")
    static = collector.structure()
    health = collector.health(MULTI_AGENT_SERVER_URL)
    rows, results, runs = [], [], []

    static_ok = not static["missing_files"] and not static["missing_calls"]
    results.append(static_ok)
    rows.append(("implementation", "files + coordinator wiring", "PASS" if static_ok else "FAIL",
                 "complete" if static_ok else f"missing files {static['missing_files']}, calls {static['missing_calls']}"))

    if not health["ok"]:
        report.line(f"Multi-Agent server unreachable: {health['error']}")
        report.stage("OBSERVE", "Live checks skipped - server unreachable.")
        report.table(["Area", "Check", "Result", "Detail"], rows)
        report.stage("ADAPT", "Start it: cd ai-services/multi-agent-server && python app.py, then rerun.")
        report.save()
        return False

    agents_ok = {"planner_agent", "worker_agent", "reviewer_agent", "human_reviewer"} <= set(health.get("agents", []))
    results.append(agents_ok)
    rows.append(("server", "health + agents", "PASS" if agents_ok else "FAIL",
                 f"agents={health.get('agents')}, models={health.get('models')}"))

    for case in MULTI_AGENT_CASES:
        wf = collector.run_workflow(MULTI_AGENT_SERVER_URL, case["domain"], case["request"])
        passed, detail = _evaluate(case, wf)
        results.append(passed)
        runs.append(wf)
        rows.append((case["domain"], case["request"], "PASS" if passed else "FAIL", f"{detail} ({wf['latency_ms']} ms)"))

    st = collector.status(MULTI_AGENT_SERVER_URL)
    decisions = st.get("human_decisions") or {}
    audit_ok = st.get("audit_record_count", 0) >= len(MULTI_AGENT_CASES) * len(EXPECTED_EVENTS)
    human_ok = sum(decisions.values()) > 0
    results += [audit_ok, human_ok]
    rows.append(("evidence", "coordination audit log", "PASS" if audit_ok else "FAIL",
                 f"{st.get('audit_record_count')} audit lines for {st.get('workflow_count')} workflows"))
    rows.append(("evidence", "human decisions recorded", "PASS" if human_ok else "FAIL",
                 f"{decisions or 'none yet'}; pending={st.get('pending_human_review')}"))

    # ---------- OBSERVE ----------
    passed = sum(results)
    report.stage("OBSERVE", f"{passed} passed, {len(results) - passed} failed.")
    report.table(["Area", "Check", "Result", "Detail"], rows)
    for wf in runs[:2]:
        if wf.get("worker_result"):
            report.line(f"[{wf.get('domain')}] {wf['user_request']} (workflow {wf['workflow_id']})")
            report.block(f"PLANNER:\n{wf['planner_result']['plan']}\n\nWORKER:\n{wf['worker_result']['output']}"
                         f"\n\nREVIEWER:\n{wf['reviewer_result']['review']}")

    # ---------- ADAPT ----------
    report.stage("ADAPT")
    failed = [r for r in rows if r[2] == "FAIL"]
    for area, check, _result, detail in failed:
        report.line(f"Fix: {area} / {check} -> {detail}")
    if not human_ok:
        report.line("Record at least one human decision (UI 'Human review' step or "
                    "`python workflow_runner.py --decide <id>`) and rerun.")
    if not failed:
        report.line("All checks passed; no rule-based adaptation needed.")

    if use_ai:
        evidence = "\n".join(f"{r[0]} | {r[1]} -> {r[2]}: {r[3]}" for r in rows)
        impl, err = ask_model(OLLAMA_MODEL, _prompt("implementation/multi_agent_task_prompt.txt"),
                              f"Observed evidence:\n{evidence}")
        report.line(f"Implementation agent ({OLLAMA_MODEL if impl else 'unavailable'}):")
        report.block(impl or err)
        review, err = ask_model(OLLAMA_REVIEW_MODEL, _prompt("review/multi_agent_review_prompt.txt"),
                                f"Implementation assessment:\n{impl or 'n/a'}\n\nHandoff evidence:\n{evidence}\n\n"
                                f"Sample workflow:\n{json.dumps(runs[0], default=str)[:2500] if runs else 'none'}")
        report.line(f"Review agent ({OLLAMA_REVIEW_MODEL if review else 'unavailable'}):")
        report.block(review or err)

    report.save()
    return not failed
