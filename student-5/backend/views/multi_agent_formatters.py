import json
from html import escape

from views.mcp_rag_formatters import format_message_html

RISK_PILL = {"low": "confidence-high", "medium": "confidence-medium", "high": "confidence-low"}
DECISION_LABEL = {"approved": "Accepted", "partially_approved": "Partially accepted",
                  "corrected": "Corrected", "rejected": "Rejected", "pending_human_review": "Awaiting your review"}


def _e(value) -> str:
    return escape("—" if value is None or value == "" else str(value))


def _pre(text) -> str:
    return f"<pre class='agent-text'>{_e(text)}</pre>"


def _decision_form(wf: dict) -> str:
    rec = wf["reviewer_result"]["recommended_decision"]
    options = "".join(
        f"<label class='decision-option'><input type='radio' name='decision' value='{d}' {'checked' if d == rec else ''}> {d}</label>"
        for d in ("Accept", "Partially Accept", "Correct", "Reject")
    )
    return (
        "<form class='decision-form' data-decision-form>"
        f"<input type='hidden' name='workflow_id' value='{_e(wf['workflow_id'])}'>"
        f"<div class='decision-options'>{options}</div>"
        "<div class='field-row'>"
        "<div class='field'><label>Your name</label><input name='reviewer' required placeholder='e.g. Vu Nguyen'></div>"
        "<div class='field'><label>Comment / reason</label><input name='comment' placeholder='Required unless you Accept'></div>"
        "</div>"
        "<div class='field corrected-field'><label>Corrected output (for Correct)</label>"
        "<textarea name='corrected_output' rows='3'></textarea></div>"
        "<button class='btn btn-primary' type='submit'>Record decision</button>"
        "</form>"
    )


def format_workflow_html(wf: dict, elapsed_ms: int | None = None) -> str:
    if wf.get("status") == "rejected_by_planner":
        return format_message_html("rejected", "Planner stopped the workflow", wf["planner_result"].get("error", ""))

    plan, worker, review = wf["planner_result"], wf["worker_result"], wf["reviewer_result"]
    human = wf.get("human_decision") or {}
    checks = "".join(
        f"<li class='{'pass' if c['passed'] else 'fail'}'>{'✓' if c['passed'] else '✗'} {_e(c['check'])}</li>"
        for c in review["automatic_checks"]
    )
    sources = ", ".join(f"{_e(s['label'])} ({_e(s['matched'])}/{_e(s['total'])})" for s in worker.get("sources", []))

    if human.get("decision"):
        human_html = (
            f"<div class='notice notice-ok'><strong>{_e(DECISION_LABEL.get(wf['status'], wf['status']))}</strong>"
            f" by {_e(human['reviewer'])} — {_e(human.get('comment'))}"
            + (f"<pre class='agent-text'>{_e(human['final_output'])}</pre>" if human.get("final_output") and human["decision"] == "Correct" else "")
            + "</div>"
        )
    else:
        human_html = _decision_form(wf)

    meta = [f"workflow {wf['workflow_id']}", f"domain {wf.get('domain')}"]
    if elapsed_ms is not None:
        meta.append(f"{elapsed_ms} ms")
    return (
        "<ol class='agent-steps'>"
        f"<li class='agent-step'><div class='step-head'><span class='step-no'>1</span><h4>Planner</h4>"
        f"<span class='mono helper-text'>{_e(plan.get('model'))}</span></div>{_pre(plan['plan'])}</li>"
        f"<li class='agent-step'><div class='step-head'><span class='step-no'>2</span><h4>Worker</h4>"
        f"<span class='mono helper-text'>{_e(worker.get('model'))} · {_e(worker['evidence_count'])} records · {sources}</span></div>"
        f"{_pre(worker['output'])}</li>"
        f"<li class='agent-step'><div class='step-head'><span class='step-no'>3</span><h4>Reviewer</h4>"
        f"<span class='pill {RISK_PILL[review['risk_level']]}'>Risk: {_e(review['risk_level'])}</span>"
        f"<span class='helper-text'>recommends <strong>{_e(review['recommended_decision'])}</strong></span></div>"
        f"{_pre(review['review'])}<ul class='check-list'>{checks}</ul></li>"
        f"<li class='agent-step'><div class='step-head'><span class='step-no'>4</span><h4>Human review</h4></div>{human_html}</li>"
        "</ol>"
        f"<p class='result-meta mono'>{' · '.join(escape(m) for m in meta)}</p>"
        "<details class='raw-json'><summary>Workflow record (JSON)</summary>"
        f"<pre>{escape(json.dumps(wf, indent=2))}</pre></details>"
    )


def format_history_html(workflows: list[dict]) -> str:
    if not workflows:
        return "<p class='helper-text'>No Assessment & Grades workflows yet.</p>"
    rows = "".join(
        "<tr>"
        f"<td class='mono'>{_e(w['timestamp'][:16].replace('T', ' '))}</td>"
        f"<td>{_e(w['user_request'])}</td>"
        f"<td><span class='pill {RISK_PILL.get(w.get('risk_level'), '')}'>{_e(w.get('risk_level'))}</span></td>"
        f"<td>{_e(DECISION_LABEL.get(w['status'], w['status']))}</td>"
        f"<td><button class='icon-btn' type='button' data-open-workflow='{_e(w['workflow_id'])}'>Open</button></td>"
        "</tr>"
        for w in workflows
    )
    return ("<div class='table-wrap'><table><thead><tr><th>When</th><th>Request</th><th>Risk</th>"
            f"<th>Status</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>")
