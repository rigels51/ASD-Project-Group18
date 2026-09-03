from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)

DATABASE_NAME = "/app/data/assessment_grades.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def health():
    return jsonify({"service": "assessment-grades-database-service", "status": "running"})


# ---------------------------------------------------------------------------
# Assessments
# ---------------------------------------------------------------------------

@app.get("/assessments")
def get_assessments():
    course_id = request.args.get("course_id", "").strip().upper()
    assessment_type = request.args.get("assessment_type", "").strip()
    name_query = request.args.get("q", "").strip()

    query = "SELECT * FROM assessments WHERE 1=1"
    params = []

    if course_id:
        query += " AND UPPER(course_id) = ?"
        params.append(course_id)
    if assessment_type:
        query += " AND assessment_type = ?"
        params.append(assessment_type)
    if name_query:
        query += " AND assessment_name LIKE ?"
        params.append(f"%{name_query}%")

    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.get("/assessments/<int:assessment_id>")
def get_assessment(assessment_id):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM assessments WHERE assessment_id = ?", (assessment_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "Assessment not found"}), 404
    return jsonify(dict(row))


@app.post("/assessments")
def create_assessment():
    data = request.get_json(silent=True) or {}
    required = ["course_id", "assessment_name", "assessment_type", "due_date", "max_mark", "weight"]
    missing = [field for field in required if field not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO assessments (course_id, assessment_name, assessment_type, description, due_date, max_mark, weight)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["course_id"].upper(),
            data["assessment_name"],
            data["assessment_type"],
            data.get("description", ""),
            data["due_date"],
            data["max_mark"],
            data["weight"],
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM assessments WHERE assessment_id = ?", (new_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.put("/assessments/<int:assessment_id>")
def update_assessment(assessment_id):
    data = request.get_json(silent=True) or {}

    conn = get_db_connection()
    existing = conn.execute(
        "SELECT * FROM assessments WHERE assessment_id = ?", (assessment_id,)
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "Assessment not found"}), 404

    merged = dict(existing)
    merged.update(data)

    conn.execute(
        """
        UPDATE assessments
        SET course_id = ?, assessment_name = ?, assessment_type = ?,
            description = ?, due_date = ?, max_mark = ?, weight = ?
        WHERE assessment_id = ?
        """,
        (
            str(merged["course_id"]).upper(),
            merged["assessment_name"],
            merged["assessment_type"],
            merged.get("description", ""),
            merged["due_date"],
            merged["max_mark"],
            merged["weight"],
            assessment_id,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM assessments WHERE assessment_id = ?", (assessment_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))


@app.delete("/assessments/<int:assessment_id>")
def delete_assessment(assessment_id):
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT * FROM assessments WHERE assessment_id = ?", (assessment_id,)
    ).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "Assessment not found"}), 404

    conn.execute("DELETE FROM grades WHERE assessment_id = ?", (assessment_id,))
    conn.execute("DELETE FROM assessments WHERE assessment_id = ?", (assessment_id,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": assessment_id})


# ---------------------------------------------------------------------------
# Grades
# ---------------------------------------------------------------------------

@app.get("/grades")
def get_grades():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT grades.*, assessments.assessment_name, assessments.course_id, assessments.max_mark
        FROM grades
        JOIN assessments ON grades.assessment_id = assessments.assessment_id
        """
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.get("/grades/<int:grade_id>")
def get_grade(grade_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM grades WHERE grade_id = ?", (grade_id,)).fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "Grade not found"}), 404
    return jsonify(dict(row))


@app.post("/grades")
def create_grade():
    data = request.get_json(silent=True) or {}
    required = ["assessment_id", "student_id", "date_recorded"]
    missing = [field for field in required if field not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    conn = get_db_connection()
    assessment = conn.execute(
        "SELECT assessment_id FROM assessments WHERE assessment_id = ?", (data["assessment_id"],)
    ).fetchone()
    if assessment is None:
        conn.close()
        return jsonify({"error": "assessment_id does not exist"}), 400

    cursor = conn.execute(
        """
        INSERT INTO grades (assessment_id, student_id, mark, grade, feedback, date_recorded)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data["assessment_id"],
            data["student_id"],
            data.get("mark"),
            data.get("grade"),
            data.get("feedback", ""),
            data["date_recorded"],
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM grades WHERE grade_id = ?", (new_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.put("/grades/<int:grade_id>")
def update_grade(grade_id):
    data = request.get_json(silent=True) or {}

    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM grades WHERE grade_id = ?", (grade_id,)).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "Grade not found"}), 404

    merged = dict(existing)
    merged.update(data)

    conn.execute(
        """
        UPDATE grades
        SET assessment_id = ?, student_id = ?, mark = ?, grade = ?, feedback = ?, date_recorded = ?
        WHERE grade_id = ?
        """,
        (
            merged["assessment_id"],
            merged["student_id"],
            merged.get("mark"),
            merged.get("grade"),
            merged.get("feedback", ""),
            merged["date_recorded"],
            grade_id,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM grades WHERE grade_id = ?", (grade_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))


@app.delete("/grades/<int:grade_id>")
def delete_grade(grade_id):
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM grades WHERE grade_id = ?", (grade_id,)).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "Grade not found"}), 404

    conn.execute("DELETE FROM grades WHERE grade_id = ?", (grade_id,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": grade_id})


@app.get("/grades/student/<int:student_id>")
def get_grades_by_student(student_id):
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT grades.*, assessments.assessment_name, assessments.course_id, assessments.max_mark
        FROM grades
        JOIN assessments ON grades.assessment_id = assessments.assessment_id
        WHERE grades.student_id = ?
        """,
        (student_id,),
    ).fetchall()
    conn.close()

    if not rows:
        return jsonify({"error": "No grades found for this student"}), 404
    return jsonify([dict(row) for row in rows])


@app.get("/grades/course/<course_id>")
def get_grades_by_course(course_id):
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT grades.*, assessments.assessment_name, assessments.course_id, assessments.max_mark
        FROM grades
        JOIN assessments ON grades.assessment_id = assessments.assessment_id
        WHERE UPPER(assessments.course_id) = ?
        """,
        (course_id.upper(),),
    ).fetchall()
    conn.close()

    if not rows:
        return jsonify({"error": "No grades found for this course"}), 404
    return jsonify([dict(row) for row in rows])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5022, debug=True)