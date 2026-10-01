import json
from html import escape


def _e(value) -> str:
    return escape("—" if value is None or value == "" else str(value))


def _num(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _e(value)
    return str(int(number)) if number.is_integer() else f"{number:g}"


def _raw_json(payload) -> str:
    return (
        "<details class='raw-json'><summary>Structured result (JSON)</summary>"
        f"<pre>{escape(json.dumps(payload, indent=2))}</pre></details>"
    )


def _meta(parts) -> str:
    return "<p class='result-meta mono'>" + " · ".join(escape(p) for p in parts if p) + "</p>"


def format_message_html(kind: str, title: str, message: str) -> str:
    """kind: 'disabled' | 'error' | 'rejected'"""
    return (
        f"<div class='notice notice-{escape(kind)}'>"
        f"<strong>{escape(title)}</strong><p>{escape(message)}</p></div>"
    )


# ---------------------------------------------------------------------------
# MCP
# ---------------------------------------------------------------------------

def format_mcp_tools_html(tools, server_url: str) -> str:
    if not tools:
        return format_message_html("error", "No Assessment & Grades tools found",
                                   f"The MCP server at {server_url} did not list any Student 5 tools.")
    items = "".join(
        f"<li><code>{escape(t['name'])}</code><span>{escape(t.get('description') or '')}</span></li>"
        for t in tools
    )
    return (
        f"<ul class='tool-list'>{items}</ul>"
        + _meta([f"{len(tools)} tools available", f"shared MCP server {server_url}"])
    )


def _assessment_table(assessments) -> str:
    if not assessments:
        return "<div class='empty-state'><h3>No assessments</h3><p>Nothing matched this request.</p></div>"
    rows = "".join(
        "<tr>"
        f"<td class='mono'>{_e(a.get('course_id'))}</td>"
        f"<td><strong>{_e(a.get('assessment_name'))}</strong></td>"
        f"<td><span class='pill type-{escape(str(a.get('assessment_type') or '').lower())}'>"
        f"{_e(a.get('assessment_type'))}</span></td>"
        f"<td class='mono'>{_e(a.get('due_date'))}</td>"
        f"<td class='mark-cell'>{_num(a.get('max_mark'))}</td>"
        f"<td><span class='weight-tag'>{_num(a.get('weight'))}%</span></td>"
        "</tr>"
        for a in assessments
    )
    return (
        "<div class='table-wrap'><table><thead><tr>"
        "<th>Course</th><th>Assessment</th><th>Type</th><th>Due</th><th>Max</th><th>Weight</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )


def _grade_table(grades) -> str:
    rows = "".join(
        "<tr>"
        f"<td class='mono'>{_e(g.get('course_id'))}</td>"
        f"<td><strong>{_e(g.get('assessment_name'))}</strong></td>"
        f"<td class='mark-cell'>{_num(g.get('mark')) if g.get('mark') is not None else '—'} / {_num(g.get('max_mark'))}</td>"
        f"<td class='mark-cell'>{(_num(g.get('percent')) + '%') if g.get('percent') is not None else '—'}</td>"
        f"<td><span class='pill grade-{escape(str(g.get('grade') or 'ungraded').lower())}'>"
        f"{_e(g.get('grade') or 'Pending')}</span></td>"
        "</tr>"
        for g in grades
    )
    return (
        "<div class='table-wrap'><table><thead><tr>"
        "<th>Course</th><th>Assessment</th><th>Mark</th><th>Percent</th><th>Grade</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )


def format_mcp_result_html(tool: str, arguments: dict, result: dict, elapsed_ms: int) -> str:
    if tool == "list_course_assessments":
        headline = (
            f"<div class='stat-strip'>"
            f"<div><span class='n'>{_e(result.get('course_id'))}</span><span class='l'>Course</span></div>"
            f"<div><span class='n'>{_e(result.get('assessment_count'))}</span><span class='l'>Assessments</span></div>"
            f"<div><span class='n'>{_num(result.get('total_weight'))}%</span><span class='l'>Total weight</span></div>"
            "</div>"
        )
        body = _assessment_table(result.get("assessments") or [])
    elif tool == "get_student_grade_summary":
        if not result.get("found"):
            headline = ""
            body = format_message_html("rejected", "No grades recorded",
                                       f"There are no grade records for {result.get('student_id')}.")
        else:
            average = result.get("average_percent")
            headline = (
                f"<div class='stat-strip'>"
                f"<div><span class='n'>{_e(result.get('student_id'))}</span><span class='l'>Student</span></div>"
                f"<div><span class='n'>{_e(result.get('graded_count'))}</span><span class='l'>Graded</span></div>"
                f"<div><span class='n'>{_e(result.get('pending_count'))}</span><span class='l'>Pending</span></div>"
                f"<div><span class='n'>{(_num(average) + '%') if average is not None else '—'}</span>"
                f"<span class='l'>Average</span></div>"
                "</div>"
            )
            body = _grade_table(result.get("grades") or [])
    elif tool == "get_upcoming_assessments":
        headline = (
            f"<div class='stat-strip'>"
            f"<div><span class='n'>{_e(result.get('from_date'))}</span><span class='l'>Due on/after</span></div>"
            f"<div><span class='n'>{_e(result.get('total_upcoming'))}</span><span class='l'>Upcoming</span></div>"
            f"<div><span class='n'>{_e(len(result.get('assessments') or []))}</span><span class='l'>Shown</span></div>"
            "</div>"
        )
        body = _assessment_table(result.get("assessments") or [])
    else:
        headline, body = "", ""

    return (
        headline + body
        + _meta([f"tool {tool}", f"arguments {json.dumps(arguments)}", f"{elapsed_ms} ms", "via shared MCP server"])
        + _raw_json(result)
    )


# ---------------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------------

def format_rag_answer_html(question: str, result: dict, elapsed_ms: int) -> str:
    confidence = str(result.get("confidence_category") or "low").lower()
    insufficient = bool(result.get("insufficient_evidence")) or not result.get("citations")

    sources = "".join(
        "<li class='source'>"
        f"<div class='source-head'><code>{_e(c.get('chunk_id'))}</code>"
        f"<span class='mono'>similarity {_e(c.get('similarity'))}</span></div>"
        f"<div class='source-section'>{_e(c.get('section'))}</div>"
        f"<div class='source-id mono'>{_e(c.get('source_id'))}</div>"
        + (f"<blockquote>{_e(c.get('text'))}</blockquote>" if c.get("text") else "")
        + "</li>"
        for c in result.get("citations") or []
    )
    sources_html = (
        f"<h4>Sources ({len(result.get('citations') or [])})</h4><ol class='source-list'>{sources}</ol>"
        if sources else
        "<h4>Sources</h4><p class='helper-text'>No sources — the server found no relevant context, "
        "so it returned an insufficient-evidence response instead of guessing.</p>"
    )

    workflow = result.get("agentic_workflow") or {}
    adapt = workflow.get("adapt")

    return (
        f"<div class='rag-answer {'is-insufficient' if insufficient else ''}'>"
        "<div class='rag-answer-head'>"
        f"<span class='eyebrow'>{'No answer — not enough evidence' if insufficient else 'Grounded answer'}</span>"
        f"<span class='pill confidence-{escape(confidence)}'>Confidence: {escape(confidence)}</span>"
        + ("<span class='pill insufficient-pill'>Insufficient evidence</span>" if insufficient else "")
        + "</div>"
        f"<p class='rag-question'>Q: {_e(question)}</p>"
        f"<p class='rag-answer-text'>{_e(result.get('answer'))}</p>"
        "</div>"
        + sources_html
        + (f"<p class='helper-text'>{_e(adapt)}</p>" if adapt else "")
        + _meta([f"domain {result.get('domain', 'assessment')}", f"generator {result.get('generator', '—')}",
                 f"{elapsed_ms} ms", "via shared RAG server"])
        + _raw_json(result)
    )


def format_rag_refresh_html(result: dict) -> str:
    warnings = result.get("warnings") or []
    return (
        "<div class='stat-strip'>"
        f"<div><span class='n'>{_e(result.get('chunk_count'))}</span><span class='l'>Chunks indexed</span></div>"
        f"<div><span class='n'>{_e(result.get('data_chunk_count'))}</span><span class='l'>From database</span></div>"
        f"<div><span class='n'>{_e(result.get('policy_chunk_count'))}</span><span class='l'>Policy sections</span></div>"
        "</div>"
        + "".join(format_message_html("rejected", "Warning", w) for w in warnings)
        + _raw_json(result)
    )
