"""Worker Agent: retrieves the evidence the plan asked for and generates the output."""

import json
import re
from pathlib import Path
from typing import Any

import evidence
import llm

PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "worker_prompt.txt").read_text(encoding="utf-8").strip()
IDENTIFIER = re.compile(r"\b(?:STU-\d{3,4}|[A-Z]{2,4}\d{3})\b")


def grounding_issues(output: str, records: list[dict]) -> list[str]:
    """Identifiers the model mentioned that do not appear in any evidence record."""
    evidence_text = json.dumps(records).upper()
    unknown = sorted({ident for ident in IDENTIFIER.findall(output.upper()) if ident not in evidence_text})
    return [f"identifier not in evidence: {ident}" for ident in unknown]


def _fallback_output(domain: str, records: list[dict]) -> str:
    if not records:
        return f"Output: No {domain} records matched the request.\nEvidence Used: none\nLimitations: No evidence."
    lines = "\n".join("- " + ", ".join(f"{k}={v}" for k, v in r.items() if k != "source") for r in records[:10])
    more = f"\n(+{len(records) - 10} more records)" if len(records) > 10 else ""
    return f"Output: {len(records)} matching {domain} record(s):\n{lines}{more}\nEvidence Used: {domain} service\nLimitations: Extractive answer (model unavailable)."


def generate_output(user_request: str, plan: dict[str, Any]) -> dict[str, Any]:
    domain = plan["domain"]
    retrieved = evidence.fetch_evidence(domain, plan.get("filters") or {})
    records = retrieved["records"]

    if not records:
        reason = "; ".join(retrieved["errors"]) or "no records matched the request filters"
        return {
            "status": "no_evidence",
            "agent": "worker_agent",
            "model": "none",
            "domain": domain,
            "evidence_count": 0,
            "evidence": [],
            "sources": retrieved["sources"],
            "source_errors": retrieved["errors"],
            "output": f"Output: Not answered.\nEvidence Used: none\nLimitations: {reason}.",
            "grounding_issues": [],
        }

    context = (
        f"Plan:\n{plan['plan']}\n\nUser request: {user_request}\n\n"
        f"Evidence records ({len(records)}):\n{json.dumps(records, indent=1)}"
    )
    text, error = llm.chat(llm.OLLAMA_MODEL, PROMPT, context, max_tokens=260)
    output = text or _fallback_output(domain, records)
    issues = grounding_issues(output, records)
    if issues:  # never pass an ungrounded answer on as if it were clean
        output = _fallback_output(domain, records) + "\n(Model answer replaced: " + "; ".join(issues) + ")"

    return {
        "status": "completed",
        "agent": "worker_agent",
        "model": llm.OLLAMA_MODEL if text and not issues else "fallback (extractive)",
        "domain": domain,
        "evidence_count": len(records),
        "evidence": records,
        "sources": retrieved["sources"],
        "source_errors": retrieved["errors"],
        "output": output,
        "grounding_issues": issues,
        "model_error": error,
    }
