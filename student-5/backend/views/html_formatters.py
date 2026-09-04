def _slug(value):
    return (value or "").strip().lower().replace(" ", "-")


def format_assessments_html(assessments):
    if not assessments:
        return (
            "<div class='empty-state'>"
            "<h3>No assessments found</h3>"
            "<p>Try a different course code, type, or clear your filters.</p>"
            "</div>"
        )

    rows = []
    for a in assessments:
        type_slug = _slug(a["assessment_type"])
        rows.append(
            "<tr>"
            f"<td class='mono'>{a['assessment_id']}</td>"
            f"<td>{a['course_id']}</td>"
            f"<td><strong>{a['assessment_name']}</strong></td>"
            f"<td><span class='pill type-{type_slug}'>{a['assessment_type']}</span></td>"
            f"<td class='mono'>{a['due_date']}</td>"
            f"<td class='mark-cell'>{a['max_mark']}</td>"
            f"<td><span class='weight-tag'>{a['weight']}%</span></td>"
            "<td><div class='row-actions'>"
            f"<button class='icon-btn' data-action='view' data-id='{a['assessment_id']}'>View</button>"
            f"<button class='icon-btn' data-action='edit-assessment' data-id='{a['assessment_id']}'>Edit</button>"
            f"<button class='icon-btn' data-action='delete-assessment' data-id='{a['assessment_id']}'>Delete</button>"
            "</div></td>"
            "</tr>"
        )

    return (
        "<table>"
        "<thead><tr>"
        "<th>ID</th><th>Course</th><th>Name</th><th>Type</th>"
        "<th>Due date</th><th>Max mark</th><th>Weight</th><th></th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def format_assessment_detail_html(a):
    type_slug = _slug(a["assessment_type"])
    return (
        "<div class='field'>"
        f"<div class='stat-row'><span class='l'>Course</span><span class='n mono' style='font-size:15px'>{a['course_id']}</span></div>"
        f"<div class='stat-row'><span class='l'>Name</span><span>{a['assessment_name']}</span></div>"
        f"<div class='stat-row'><span class='l'>Type</span><span class='pill type-{type_slug}'>{a['assessment_type']}</span></div>"
        f"<div class='stat-row'><span class='l'>Description</span><span>{a.get('description') or '—'}</span></div>"
        f"<div class='stat-row'><span class='l'>Due date</span><span class='mono'>{a['due_date']}</span></div>"
        f"<div class='stat-row'><span class='l'>Max mark</span><span class='mono'>{a['max_mark']}</span></div>"
        f"<div class='stat-row'><span class='l'>Weight</span><span class='mono'>{a['weight']}%</span></div>"
        "</div>"
    )


def _grade_pill(grade):
    if not grade:
        return "<span class='pill grade-ungraded'>Ungraded</span>"
    slug = _slug(grade)
    return f"<span class='pill grade-{slug}'>{grade}</span>"


def format_grades_html(grades):
    if not grades:
        return (
            "<div class='empty-state'>"
            "<h3>No grades found</h3>"
            "<p>Record a mark using the form below, or adjust your search.</p>"
            "</div>"
        )

    rows = []
    for g in grades:
        assessment_name = g.get("assessment_name") or f"Assessment {g['assessment_id']}"
        course_id = g.get("course_id", "—")
        mark = g["mark"] if g.get("mark") is not None else "—"
        feedback = g.get("feedback") or "—"

        rows.append(
            "<tr>"
            f"<td class='mono'>{g['grade_id']}</td>"
            f"<td><strong>{assessment_name}</strong></td>"
            f"<td>{course_id}</td>"
            f"<td class='mono'>{g['student_id']}</td>"
            f"<td class='mark-cell'>{mark}</td>"
            f"<td>{_grade_pill(g.get('grade'))}</td>"
            f"<td>{feedback}</td>"
            "<td><div class='row-actions'>"
            f"<button class='icon-btn' data-action='edit-grade' data-id='{g['grade_id']}'>Edit</button>"
            f"<button class='icon-btn' data-action='delete-grade' data-id='{g['grade_id']}'>Delete</button>"
            "</div></td>"
            "</tr>"
        )

    return (
        "<table>"
        "<thead><tr>"
        "<th>ID</th><th>Assessment</th><th>Course</th><th>Student</th>"
        "<th>Mark</th><th>Grade</th><th>Feedback</th><th></th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def format_grade_html(g):
    mark = g["mark"] if g.get("mark") is not None else "—"
    return (
        "<div class='field'>"
        f"<div class='stat-row'><span class='l'>Grade ID</span><span class='n mono' style='font-size:15px'>{g['grade_id']}</span></div>"
        f"<div class='stat-row'><span class='l'>Assessment ID</span><span class='mono'>{g['assessment_id']}</span></div>"
        f"<div class='stat-row'><span class='l'>Student ID</span><span class='mono'>{g['student_id']}</span></div>"
        f"<div class='stat-row'><span class='l'>Mark</span><span class='mono'>{mark}</span></div>"
        f"<div class='stat-row'><span class='l'>Grade</span>{_grade_pill(g.get('grade'))}</div>"
        f"<div class='stat-row'><span class='l'>Feedback</span><span>{g.get('feedback') or '—'}</span></div>"
        f"<div class='stat-row'><span class='l'>Date recorded</span><span class='mono'>{g['date_recorded']}</span></div>"
        "</div>"
    )
