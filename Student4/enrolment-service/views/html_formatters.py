def format_courses_html(courses):
    if not courses:
        return "<p>No courses found.</p>"

    html = """
    <table border="1" cellpadding="6" cellspacing="0">
        <tr>
            <th>ID</th>
            <th>Course Code</th>
            <th>Course Name</th>
            <th>Credits</th>
            <th>Capacity</th>
        </tr>
    """

    for course in courses:
        html += f"""
        <tr>
            <td>{course['course_id']}</td>
            <td>{course['course_code']}</td>
            <td>{course['course_name']}</td>
            <td>{course['credits']}</td>
            <td>{course['capacity']}</td>
        </tr>
        """

    html += "</table>"
    return html


def format_course_html(course):
    return f"""
    <p>
        <strong>Course ID:</strong> {course['course_id']}<br>
        <strong>Course Code:</strong> {course['course_code']}<br>
        <strong>Course Name:</strong> {course['course_name']}<br>
        <strong>Credits:</strong> {course['credits']}<br>
        <strong>Capacity:</strong> {course['capacity']}
    </p>
    """


def format_enrolments_html(enrolments):
    if not enrolments:
        return "<p>No enrolments found.</p>"

    html = """
    <table border="1" cellpadding="6" cellspacing="0">
        <tr>
            <th>Enrolment ID</th>
            <th>Student ID</th>
            <th>Course ID</th>
            <th>Course Code</th>
            <th>Course Name</th>
            <th>Status</th>
        </tr>
    """

    for enrolment in enrolments:
        html += f"""
        <tr>
            <td>{enrolment['enrolment_id']}</td>
            <td>{enrolment['student_id']}</td>
            <td>{enrolment['course_id']}</td>
            <td>{enrolment['course_code']}</td>
            <td>{enrolment['course_name']}</td>
            <td>{enrolment['status']}</td>
        </tr>
        """

    html += "</table>"
    return html


def format_enrolment_html(enrolment):
    return f"""
    <p>
        <strong>Enrolment ID:</strong> {enrolment['enrolment_id']}<br>
        <strong>Student ID:</strong> {enrolment['student_id']}<br>
        <strong>Course ID:</strong> {enrolment['course_id']}<br>
        <strong>Course Code:</strong> {enrolment['course_code']}<br>
        <strong>Course Name:</strong> {enrolment['course_name']}<br>
        <strong>Status:</strong> {enrolment['status']}
    </p>
    """