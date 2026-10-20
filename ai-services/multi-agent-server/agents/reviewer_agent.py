"""Reviewer Agent: checks the Worker output against the plan and evidence."""

import json
import re
from pathlib import Path
from typing import Any

import llm

PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "reviewer_prompt.txt").read_text(encoding="utf-8").strip()
RISK_LEVELS = ("low", "medium", "high")


def automatic_checks(plan: dict, worker: dict) -> list[dict]:
    return [
        {"check": "plan_completed", "passed": plan.get("status") == "completed"},
        {"check": "worker_completed", "passed": worker.get("status") == "completed"},
        {"check": "evidence_retrieved", "passed": worker.get("evidence_count", 0) > 0},
        {"check": "all_sources_reachable", "passed": not worker.get("source_errors")},
        {"check": "output_grounded", "passed": not worker.get("grounding_issues")},
        {"check": "worker_used_model", "passed": "fallback" not in str(worker.get("model"))},
    ]


def rule_risk(checks: list[dict]) -> str:
    failed = {c["check"] for c in checks if not c["passed"]}
    if failed & {"plan_completed", "worker_completed", "evidence_retrieved"}:
        return "high"
    if failed:
        return "medium"
    return "low"


def review_output(user_request: str, plan: dict[str, Any], worker: dict[str, Any]) -> dict[str, Any]:
    checks = automatic_checks(plan, worker)
    risk = rule_risk(checks)
    context = (
        f"User request: {user_request}\n\nPlan:\n{plan.get('plan')}\n\n"
        f"Worker output:\n{worker.get('output')}\n\n"
        f"Evidence count: {worker.get('evidence_count')}\n"
        f"Evidence sample: {json.dumps(worker.get('evidence', [])[:8])}\n\n"
        f"Automatic checks: {json.dumps(checks)}\nRule-based risk: {risk}"
    )
    text, error = llm.chat(llm.OLLAMA_REVIEW_MODEL, PROMPT, context, max_tokens=180)

    # The model may raise the risk level but never lower it below the rule-based level.
    model_risk = None
    if text:
        match = re.search(r"Risk:\s*(low|medium|high)", text, re.IGNORECASE)
        model_risk = match.group(1).lower() if match else None
    final_risk = max(risk, model_risk or risk, key=RISK_LEVELS.index)

    recommendation = {"low": "Accept", "medium": "Partially Accept", "high": "Reject"}[final_risk]
    review = text or (
        f"Risk: {final_risk} - automatic checks failed: "
        + (", ".join(c["check"] for c in checks if not c["passed"]) or "none") + "\n"
        "Correction: Fix the failed checks before relying on the output.\n"
        "Retest: Re-run the workflow after the fix.\n"
        f"Recommendation: {recommendation} - based on automatic checks (review model unavailable)."
    )
    return {
        "status": "completed",
        "agent": "reviewer_agent",
        "model": llm.OLLAMA_REVIEW_MODEL if text else "fallback (rule-based)",
        "risk_level": final_risk,
        "recommended_decision": recommendation,
        "automatic_checks": checks,
        "review": review,
        "model_error": error,
    }
