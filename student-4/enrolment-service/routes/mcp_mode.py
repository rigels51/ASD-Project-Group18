import html
import json

from flask import Blueprint, request

from services.mcp_api import (
    list_course_tools,
    call_course_tool,
)


mcp_bp = Blueprint(
    "mcp_mode",
    __name__
)


# =========================================================
# Helpers
# =========================================================

def escape(value):
    return html.escape(
        str(value)
    )


def raw_json(payload):
    return f"""
    <details class="raw-result">
        <summary>
            Raw MCP tool result (JSON)
        </summary>

        <pre>{escape(json.dumps(payload, indent=2))}</pre>
    </details>
    """


def error_result(message):
    payload = {
        "status": "error",
        "error": str(message),
    }

    return f"""
    <div class="error-box">
        <strong>MCP Error</strong>
        <p>{escape(message)}</p>
    </div>

    {raw_json(payload)}
    """


def normalise_list(payload, key):
    """
    Supports both:
        [...]
    and:
        {"courses": [...]}
    """

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):

        value = payload.get(key)

        if isinstance(value, list):
            return value

        result = payload.get("result")

        if isinstance(result, list):
            return result

        if isinstance(result, dict):

            nested = result.get(key)

            if isinstance(nested, list):
                return nested

    return []


# =========================================================
# Render Course Count
# =========================================================

def render_course_count(result):

    count = 0

    if isinstance(result, dict):

        count = result.get(
            "course_count",
            result.get("count", 0)
        )

        nested = result.get("result")

        if isinstance(nested, dict):

            count = nested.get(
                "course_count",
                nested.get("count", count)
            )

    return f"""
    <div class="result-summary">

        <span class="result-badge">
            COURSE COUNT
        </span>

        <span class="result-count">
            {escape(count)} Course(s)
        </span>

    </div>

    {raw_json(result)}
    """


# =========================================================
# Render Courses
# =========================================================

def render_courses(result):

    courses = normalise_list(
        result,
        "courses"
    )

    rows = []

    for course in courses:

        if not isinstance(course, dict):
            continue

        course_id = course.get(
            "course_id",
            course.get("id", "")
        )

        code = course.get(
            "course_code",
            course.get("code", "")
        )

        name = course.get(
            "course_name",
            course.get(
                "name",
                course.get("title", "")
            )
        )

        credits = course.get(
            "credits",
            ""
        )

        capacity = course.get(
            "capacity",
            ""
        )

        rows.append(
            f"""
            <tr>
                <td>{escape(course_id)}</td>
                <td><strong>{escape(code)}</strong></td>
                <td>{escape(name)}</td>
                <td>{escape(credits)}</td>
                <td>{escape(capacity)}</td>
            </tr>
            """
        )


    if rows:

        table = f"""
        <div class="result-table-wrap">

            <table>

                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Code</th>
                        <th>Course Name</th>
                        <th>Credits</th>
                        <th>Capacity</th>
                    </tr>
                </thead>

                <tbody>
                    {''.join(rows)}
                </tbody>

            </table>

        </div>
        """

    else:

        table = """
        <p class="muted">
            No courses were returned.
        </p>
        """


    return f"""
    <div class="result-summary">

        <span class="result-badge">
            COURSES
        </span>

        <span class="result-count">
            {len(courses)} Course(s)
        </span>

    </div>

    {table}

    {raw_json(result)}
    """


# =========================================================
# Render One Course
# =========================================================

def render_course(result):

    course = result

    if isinstance(result, dict):

        nested = result.get("result")

        if isinstance(nested, dict):
            course = nested

        nested_course = result.get("course")

        if isinstance(nested_course, dict):
            course = nested_course


    if not isinstance(course, dict):

        return f"""
        <p class="muted">
            Course data could not be displayed.
        </p>

        {raw_json(result)}
        """


    if course.get("error"):

        return f"""
        <div class="error-box">
            <strong>Course not found</strong>
            <p>{escape(course.get("error"))}</p>
        </div>

        {raw_json(result)}
        """


    course_id = course.get(
        "course_id",
        course.get("id", "")
    )

    code = course.get(
        "course_code",
        course.get("code", "")
    )

    name = course.get(
        "course_name",
        course.get(
            "name",
            course.get("title", "")
        )
    )

    credits = course.get(
        "credits",
        ""
    )

    capacity = course.get(
        "capacity",
        ""
    )


    return f"""
    <div class="result-summary">

        <span class="result-badge">
            {escape(code or "COURSE")}
        </span>

        <span class="result-count">
            {escape(name)}
        </span>

    </div>


    <div class="result-table-wrap">

        <table>

            <thead>
                <tr>
                    <th>ID</th>
                    <th>Code</th>
                    <th>Course Name</th>
                    <th>Credits</th>
                    <th>Capacity</th>
                </tr>
            </thead>

            <tbody>
                <tr>
                    <td>{escape(course_id)}</td>
                    <td><strong>{escape(code)}</strong></td>
                    <td>{escape(name)}</td>
                    <td>{escape(credits)}</td>
                    <td>{escape(capacity)}</td>
                </tr>
            </tbody>

        </table>

    </div>


    {raw_json(result)}
    """


# =========================================================
# Render Enrolments
# =========================================================

def render_enrolments(result):

    enrolments = normalise_list(
        result,
        "enrolments"
    )

    rows = []


    for enrolment in enrolments:

        if not isinstance(enrolment, dict):
            continue


        enrolment_id = enrolment.get(
            "enrolment_id",
            enrolment.get("id", "")
        )

        student_id = enrolment.get(
            "student_id",
            ""
        )

        course_id = enrolment.get(
            "course_id",
            ""
        )

        course_code = enrolment.get(
            "course_code",
            ""
        )

        status = enrolment.get(
            "status",
            enrolment.get(
                "enrolment_status",
                ""
            )
        )


        rows.append(
            f"""
            <tr>
                <td>{escape(enrolment_id)}</td>
                <td>{escape(student_id)}</td>
                <td>{escape(course_id)}</td>
                <td>{escape(course_code)}</td>
                <td>{escape(status)}</td>
            </tr>
            """
        )


    if rows:

        table = f"""
        <div class="result-table-wrap">

            <table>

                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Student ID</th>
                        <th>Course ID</th>
                        <th>Course</th>
                        <th>Status</th>
                    </tr>
                </thead>

                <tbody>
                    {''.join(rows)}
                </tbody>

            </table>

        </div>
        """

    else:

        table = """
        <p class="muted">
            No enrolments were returned.
        </p>
        """


    return f"""
    <div class="result-summary">

        <span class="result-badge">
            ENROLMENTS
        </span>

        <span class="result-count">
            {len(enrolments)} Enrolment(s)
        </span>

    </div>

    {table}

    {raw_json(result)}
    """


# =========================================================
# New unified MCP endpoint
# =========================================================

@mcp_bp.post("/mcp/run")
def mcp_run():

    tool = request.form.get(
        "tool",
        ""
    ).strip()


    try:

        if tool == "get_course_count":

            result = call_course_tool(
                "get_course_count"
            )

            return render_course_count(
                result
            ), 200


        if tool == "list_courses":

            result = call_course_tool(
                "list_courses"
            )

            return render_courses(
                result
            ), 200


        if tool == "get_course":

            course_id = request.form.get(
                "course_id",
                ""
            ).strip()


            if not course_id:

                return error_result(
                    "course_id is required"
                ), 400


            try:

                course_id_int = int(
                    course_id
                )

            except ValueError:

                return error_result(
                    "course_id must be an integer"
                ), 400


            result = call_course_tool(
                "get_course",
                {
                    "course_id":
                        course_id_int
                }
            )

            return render_course(
                result
            ), 200


        if tool == "list_enrolments":

            result = call_course_tool(
                "list_enrolments"
            )

            return render_enrolments(
                result
            ), 200


        return error_result(
            "Unknown MCP tool"
        ), 400


    except Exception as exc:

        return error_result(
            str(exc)
        ), 503


# =========================================================
# Existing endpoints
# Keep these so old code / tests still work.
# =========================================================

@mcp_bp.get("/mcp/tools")
def mcp_tools():

    try:

        tools = list_course_tools()

        return raw_json(
            tools
        ), 200

    except Exception as exc:

        return error_result(
            str(exc)
        ), 503


@mcp_bp.post("/mcp/course-count")
def mcp_course_count():

    try:

        result = call_course_tool(
            "get_course_count"
        )

        return render_course_count(
            result
        ), 200

    except Exception as exc:

        return error_result(
            str(exc)
        ), 503


@mcp_bp.post("/mcp/courses")
def mcp_courses():

    try:

        result = call_course_tool(
            "list_courses"
        )

        return render_courses(
            result
        ), 200

    except Exception as exc:

        return error_result(
            str(exc)
        ), 503


@mcp_bp.post("/mcp/course")
def mcp_course():

    course_id = request.form.get(
        "course_id",
        ""
    ).strip()


    if not course_id:

        return error_result(
            "course_id is required"
        ), 400


    try:

        course_id_int = int(
            course_id
        )

    except ValueError:

        return error_result(
            "course_id must be an integer"
        ), 400


    try:

        result = call_course_tool(
            "get_course",
            {
                "course_id":
                    course_id_int
            }
        )

        return render_course(
            result
        ), 200

    except Exception as exc:

        return error_result(
            str(exc)
        ), 503


@mcp_bp.post("/mcp/enrolments")
def mcp_enrolments():

    try:

        result = call_course_tool(
            "list_enrolments"
        )

        return render_enrolments(
            result
        ), 200

    except Exception as exc:

        return error_result(
            str(exc)
        ), 503