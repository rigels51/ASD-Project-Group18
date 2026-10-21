"""Planner Agent: decides the domain and evidence sources, and writes the workflow plan."""

from pathlib import Path
from typing import Any

import evidence
import llm

PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "planner_prompt.txt").read_text(encoding="utf-8").strip()


def _fallback_plan(user_request: str, domain: str, sources: list[str]) -> str:
    return (
        f"Objective: {user_request}\n"
        f"Steps: 1. Retrieve {', '.join(sources)} records from the {domain} service. "
        "2. Produce an answer using only those records. 3. Review the answer for unsupported claims.\n"
        f"Evidence Required: {', '.join(sources)} ({evidence.DOMAINS[domain]['owner']}).\n"
        "Human Approval: Required before the output is used."
    )


def plan_workflow(user_request: str, domain: str | None = None) -> dict[str, Any]:
    """Return the plan. The routing decision is rule-based so it is reproducible; the
    plan text is written by the model (with a deterministic fallback)."""
    routed_by = "caller"
    if domain not in evidence.DOMAINS:
        domain, routed_by = evidence.detect_domain(user_request), "keywords"
    else:
        detected_domain = evidence.detect_domain(user_request)
        if detected_domain and detected_domain != domain:
            return {
                "status": "rejected",
                "agent": "planner_agent",
                "model": "rule-based routing",
                "domain": domain,
                "error": (
                    f"This feature handles {domain} questions; this request appears "
                    f"to be about {detected_domain}."
                ),
            }
    if domain is None:
        return {
            "status": "rejected",
            "agent": "planner_agent",
            "model": "rule-based routing",
            "error": "Request does not match any feature domain: " + ", ".join(sorted(evidence.DOMAINS)),
        }

    filters = evidence.extract_filters(user_request)
    sources = [label for label, _url, _fields in evidence.DOMAINS[domain]["sources"]]
    context = (
        f"Domain: {domain} ({evidence.DOMAINS[domain]['owner']})\n"
        f"Available evidence sources: {', '.join(sources)}\n"
        f"Filters found in request: {filters}\n\n"
        f"User request: {user_request}"
    )
    text, error = llm.chat(llm.OLLAMA_MODEL, PROMPT, context, max_tokens=160)
    return {
        "status": "completed",
        "agent": "planner_agent",
        "model": llm.OLLAMA_MODEL if text else "fallback (rule-based)",
        "domain": domain,
        "routed_by": routed_by,
        "evidence_sources": sources,
        "filters": filters,
        "plan": text or _fallback_plan(user_request, domain, sources),
        "model_error": error,
        "steps": [
            {"step": 1, "agent": "planner_agent", "action": "Create plan and select evidence"},
            {"step": 2, "agent": "worker_agent", "action": f"Retrieve {domain} evidence and generate output"},
            {"step": 3, "agent": "reviewer_agent", "action": "Assess risk, correction, retest, recommendation"},
            {"step": 4, "agent": "human_reviewer", "action": "Accept, partially accept, correct, or reject"},
        ],
    }
