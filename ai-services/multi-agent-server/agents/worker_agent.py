"""Worker Agent: retrieves the evidence the plan asked for and generates the output."""

import json
import re
from pathlib import Path
from typing import Any

import evidence
import llm

PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "worker_prompt.txt").read_text(encoding="utf-8").strip()
IDENTIFIER = re.compile(r"\b(?:STU-\d{3,4}|[A-Z]{2,4}\d{3})\b")


def _staff_filter_records(
    user_request: str, records: list[dict]
) -> tuple[list[dict], list[str]]:
    """Apply department and employment-type filters named in the request."""
    departments = {
        str(record["department"])
        for record in records
        if record.get("department")
    }
    employment_types = {
        str(record["employment_type"])
        for record in records
        if record.get("employment_type")
    }
    normalized_request = re.sub(r"[-_]+", " ", user_request.lower())

    def find_values(values: set[str]) -> list[str]:
        return sorted(
            (
                value
                for value in values
                if re.search(
                    rf"(?<!\w){re.escape(re.sub(r'[-_]+', ' ', value.lower()))}(?!\w)",
                    normalized_request,
                )
            ),
            key=str.lower,
        )

    selected_departments = find_values(departments)
    selected_employment_types = find_values(employment_types)
    if not selected_departments and not selected_employment_types:
        return records, []

    filtered = records
    if selected_departments:
        filtered = [
            record for record in filtered
            if record.get("department") in selected_departments
        ]
    if selected_employment_types:
        filtered = [
            record for record in filtered
            if record.get("employment_type") in selected_employment_types
        ]

    labels = [f"{value} department" for value in selected_departments]
    labels.extend(f"{value} employment" for value in selected_employment_types)
    return filtered, labels


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
    staff_filters = []
    if domain == "staff":
        records, staff_filters = _staff_filter_records(user_request, records)

    if not records:
        reason = "; ".join(retrieved["errors"]) or "no records matched the request filters"
        if staff_filters:
            reason = f"no staff records matched the requested {' and '.join(staff_filters)}"
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

    if staff_filters:
        names = [
            f"{record.get('given_name', '')} {record.get('family_name', '')}".strip()
            for record in records
        ]
        lines = "\n".join(f"- {name}" for name in names)
        output = (
            f"Output: {len(records)} staff member(s) matching "
            f"{' and '.join(staff_filters)}:\n"
            f"{lines}\n"
            "Evidence Used: staff service\n"
            "Limitations: Exact match against retrieved staff records."
        )
        return {
            "status": "completed",
            "agent": "worker_agent",
            "model": "deterministic (evidence-filtered)",
            "domain": domain,
            "evidence_count": len(records),
            "evidence": records,
            "sources": retrieved["sources"],
            "source_errors": retrieved["errors"],
            "output": output,
            "grounding_issues": [],
            "model_error": None,
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
