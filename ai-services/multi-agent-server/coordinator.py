"""Workflow Coordinator: Planner -> Worker -> Reviewer -> Human Review.

Evidence files (append-only JSON Lines, one object per line):
  workflow_history.jsonl    - full workflow records and every human decision event
  coordination_audit.jsonl  - one short line per agent handoff and per human decision
"""

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.planner_agent import plan_workflow
from agents.reviewer_agent import review_output
from agents.worker_agent import generate_output

LOG_DIR = Path(os.getenv("MULTI_AGENT_LOG_DIR", Path(__file__).resolve().parent))
HISTORY_PATH = LOG_DIR / "workflow_history.jsonl"
AUDIT_PATH = LOG_DIR / "coordination_audit.jsonl"

DECISIONS = {
    "Accept": "approved",
    "Partially Accept": "partially_approved",
    "Correct": "corrected",
    "Reject": "rejected",
}
_lock = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(path: Path, record: dict) -> None:
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _audit(workflow_id: str, event: str, **details) -> None:
    _append(AUDIT_PATH, {"timestamp": now_iso(), "workflow_id": workflow_id, "event": event, **details})


def _timed(fn, *args):
    started = time.monotonic()
    result = fn(*args)
    return result, round((time.monotonic() - started) * 1000)


def run_workflow(user_request: str, domain: str | None = None, caller: str = "terminal") -> dict[str, Any]:
    workflow_id = str(uuid.uuid4())
    started = time.monotonic()
    _audit(workflow_id, "workflow_started", caller=caller, requested_domain=domain, user_request=user_request)

    # 1. Planner
    plan, plan_ms = _timed(plan_workflow, user_request, domain)
    _audit(workflow_id, "planner_completed", status=plan["status"], domain=plan.get("domain"),
           model=plan.get("model"), duration_ms=plan_ms)

    if plan["status"] != "completed":
        record = {
            "record_type": "workflow", "workflow_id": workflow_id, "timestamp": now_iso(),
            "caller": caller, "user_request": user_request, "status": "rejected_by_planner",
            "duration_ms": round((time.monotonic() - started) * 1000),
            "participating_agents": ["planner_agent"], "planner_result": plan,
            "worker_result": None, "reviewer_result": None,
            "human_decision": {"required": False, "status": "not_applicable"},
        }
        _append(HISTORY_PATH, record)
        _audit(workflow_id, "workflow_stopped", reason=plan.get("error"))
        return record

    # 2. Worker (receives the plan: it only fetches the evidence the planner selected)
    worker, worker_ms = _timed(generate_output, user_request, plan)
    _audit(workflow_id, "worker_completed", status=worker["status"], evidence_count=worker["evidence_count"],
           grounding_issues=len(worker["grounding_issues"]), model=worker.get("model"), duration_ms=worker_ms)

    # 3. Reviewer
    reviewer, review_ms = _timed(review_output, user_request, plan, worker)
    _audit(workflow_id, "reviewer_completed", risk_level=reviewer["risk_level"],
           recommended_decision=reviewer["recommended_decision"], model=reviewer.get("model"), duration_ms=review_ms)

    # 4. Human review gate: nothing is final until a person decides
    record = {
        "record_type": "workflow",
        "workflow_id": workflow_id,
        "timestamp": now_iso(),
        "caller": caller,
        "user_request": user_request,
        "domain": plan["domain"],
        "status": "pending_human_review",
        "duration_ms": round((time.monotonic() - started) * 1000),
        "participating_agents": ["planner_agent", "worker_agent", "reviewer_agent", "human_reviewer"],
        "planner_result": plan,
        "worker_result": worker,
        "reviewer_result": reviewer,
        "human_decision": {"required": True, "status": "pending", "allowed_values": list(DECISIONS)},
    }
    _append(HISTORY_PATH, record)
    _audit(workflow_id, "awaiting_human_review", risk_level=reviewer["risk_level"])
    return record


def get_workflow(workflow_id: str) -> dict | None:
    """Latest state: the workflow record with its most recent human decision applied."""
    workflow, decision = None, None
    for rec in read_jsonl(HISTORY_PATH):
        if rec.get("workflow_id") != workflow_id:
            continue
        if rec.get("record_type") == "workflow":
            workflow = rec
        elif rec.get("record_type") == "human_decision":
            decision = rec
    if workflow and decision:
        workflow = {**workflow, "status": DECISIONS[decision["decision"]], "human_decision": decision}
    return workflow


def record_decision(workflow_id: str, decision: str, reviewer: str, comment: str = "",
                    corrected_output: str = "") -> dict[str, Any]:
    """Raises KeyError (unknown workflow) or ValueError (invalid decision)."""
    workflow = get_workflow(workflow_id)
    if workflow is None:
        raise KeyError(workflow_id)
    if workflow["status"] == "rejected_by_planner":
        raise ValueError("This workflow was stopped by the planner; there is nothing to review")
    if workflow["status"] != "pending_human_review":
        raise ValueError(f"This workflow was already decided ({workflow['status']}); run a new workflow instead")
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of: {', '.join(DECISIONS)}")
    if not reviewer.strip():
        raise ValueError("reviewer name is required")
    if decision in {"Correct", "Partially Accept", "Reject"} and not comment.strip():
        raise ValueError(f"a comment explaining the '{decision}' decision is required")
    if decision == "Correct" and not corrected_output.strip():
        raise ValueError("corrected_output is required for a 'Correct' decision")

    worker_output = (workflow.get("worker_result") or {}).get("output", "")
    final_output = {"Accept": worker_output, "Partially Accept": worker_output,
                    "Correct": corrected_output.strip(), "Reject": None}[decision]
    event = {
        "record_type": "human_decision",
        "workflow_id": workflow_id,
        "timestamp": now_iso(),
        "decision": decision,
        "status": DECISIONS[decision],
        "reviewer": reviewer.strip()[:80],
        "comment": comment.strip()[:1000],
        "agent_recommendation": workflow["reviewer_result"]["recommended_decision"],
        "agreed_with_reviewer_agent": decision == workflow["reviewer_result"]["recommended_decision"],
        "final_output": final_output,
    }
    _append(HISTORY_PATH, event)
    _audit(workflow_id, "human_decision_recorded", decision=decision, reviewer=event["reviewer"],
           agreed_with_reviewer_agent=event["agreed_with_reviewer_agent"])
    return get_workflow(workflow_id)


def list_workflows(limit: int = 20, domain: str | None = None) -> list[dict]:
    ids = []
    for rec in read_jsonl(HISTORY_PATH):
        if rec.get("record_type") == "workflow" and (domain is None or rec.get("domain") == domain):
            ids.append(rec["workflow_id"])
    summaries = []
    for wid in reversed(ids[-limit:]):
        wf = get_workflow(wid)
        summaries.append({
            "workflow_id": wid, "timestamp": wf["timestamp"], "domain": wf.get("domain"),
            "user_request": wf["user_request"], "status": wf["status"],
            "risk_level": (wf.get("reviewer_result") or {}).get("risk_level"),
            "decision": wf["human_decision"].get("decision"),
        })
    return summaries


def workflow_status() -> dict[str, Any]:
    history = read_jsonl(HISTORY_PATH)
    workflows = [r for r in history if r.get("record_type") == "workflow"]
    decisions = [r for r in history if r.get("record_type") == "human_decision"]
    by_decision: dict[str, int] = {}
    for d in decisions:
        by_decision[d["decision"]] = by_decision.get(d["decision"], 0) + 1
    decided = {d["workflow_id"] for d in decisions}
    return {
        "status": "success",
        "workflow_count": len(workflows),
        "pending_human_review": sum(1 for w in workflows
                                    if w["status"] == "pending_human_review" and w["workflow_id"] not in decided),
        "human_decisions": by_decision,
        "audit_record_count": len(read_jsonl(AUDIT_PATH)),
        "history_file": str(HISTORY_PATH),
        "audit_file": str(AUDIT_PATH),
        "latest": list_workflows(limit=5),
    }
