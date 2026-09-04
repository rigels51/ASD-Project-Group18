from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)

DATABASE_NAME = "/app/data/enrolment.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@app.get("/")
def health():
    return jsonify({
        "service": "database-service",
        "status": "running"
    })



#  Get all courses
@app.get("/courses")
def get_courses():
    conn = get_db_connection()

    courses = conn.execute("""
        SELECT course_id, course_code, course_name, credits, capacity
        FROM courses
        ORDER BY course_id
    """).fetchall()

    conn.close()

    return jsonify([dict(row) for row in courses])


#Get one course
@app.get("/courses/<int:course_id>")
def get_course(course_id):
    conn = get_db_connection()

    course = conn.execute("""
        SELECT course_id, course_code, course_name, credits, capacity
        FROM courses
        WHERE course_id = ?
    """, (course_id,)).fetchone()

    conn.close()

    if course is None:
        return jsonify({"error": "Course not found"}), 404

    return jsonify(dict(course))


#Add course
@app.post("/courses")
def create_course():
    data = request.get_json(silent=True) or {}

    course_code = str(data.get("course_code", "")).strip().upper()
    course_name = str(data.get("course_name", "")).strip()
    credits = data.get("credits")
    capacity = data.get("capacity")

    if not course_code or not course_name:
        return jsonify({
            "error": "course_code and course_name are required"
        }), 400

    try:
        credits = int(credits)
        capacity = int(capacity)
    except (TypeError, ValueError):
        return jsonify({
            "error": "credits and capacity must be integers"
        }), 400

    if credits <= 0 or capacity <= 0:
        return jsonify({
            "error": "credits and capacity must be greater than 0"
        }), 400

    conn = get_db_connection()

    try:
        cursor = conn.execute("""
            INSERT INTO courses (
                course_code,
                course_name,
                credits,
                capacity
            )
            VALUES (?, ?, ?, ?)
        """, (
            course_code,
            course_name,
            credits,
            capacity
        ))

        conn.commit()

        course_id = cursor.lastrowid

    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({
            "error": "Course code already exists"
        }), 409

    conn.close()

    return jsonify({
        "message": "Course created successfully",
        "course_id": course_id
    }), 201


# Update course
@app.put("/courses/<int:course_id>")
def update_course(course_id):
    data = request.get_json(silent=True) or {}

    course_code = str(data.get("course_code", "")).strip().upper()
    course_name = str(data.get("course_name", "")).strip()
    credits = data.get("credits")
    capacity = data.get("capacity")

    if not course_code or not course_name:
        return jsonify({
            "error": "course_code and course_name are required"
        }), 400

    try:
        credits = int(credits)
        capacity = int(capacity)
    except (TypeError, ValueError):
        return jsonify({
            "error": "credits and capacity must be integers"
        }), 400

    conn = get_db_connection()

    existing = conn.execute("""
        SELECT course_id
        FROM courses
        WHERE course_id = ?
    """, (course_id,)).fetchone()

    if existing is None:
        conn.close()
        return jsonify({"error": "Course not found"}), 404

    try:
        conn.execute("""
            UPDATE courses
            SET course_code = ?,
                course_name = ?,
                credits = ?,
                capacity = ?
            WHERE course_id = ?
        """, (
            course_code,
            course_name,
            credits,
            capacity,
            course_id
        ))

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({
            "error": "Course code already exists"
        }), 409

    conn.close()

    return jsonify({
        "message": "Course updated successfully"
    })


#Delete course
@app.delete("/courses/<int:course_id>")
def delete_course(course_id):
    conn = get_db_connection()

    course = conn.execute("""
        SELECT course_id
        FROM courses
        WHERE course_id = ?
    """, (course_id,)).fetchone()

    if course is None:
        conn.close()
        return jsonify({"error": "Course not found"}), 404

    enrolment = conn.execute("""
        SELECT enrolment_id
        FROM enrolments
        WHERE course_id = ?
        LIMIT 1
    """, (course_id,)).fetchone()

    if enrolment is not None:
        conn.close()
        return jsonify({
            "error": "Cannot delete course because students are enrolled in it"
        }), 409

    conn.execute("""
        DELETE FROM courses
        WHERE course_id = ?
    """, (course_id,))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Course deleted successfully"
    })


# =========================================================
# ENROLMENT CRUD
# =========================================================

# READ - Get all enrolments
@app.get("/enrolments")
def get_enrolments():
    conn = get_db_connection()

    enrolments = conn.execute("""
        SELECT
            e.enrolment_id,
            e.student_id,
            e.course_id,
            c.course_code,
            c.course_name,
            e.status
        FROM enrolments e
        JOIN courses c
            ON e.course_id = c.course_id
        ORDER BY e.enrolment_id
    """).fetchall()

    conn.close()

    return jsonify([dict(row) for row in enrolments])


# READ - Get one enrolment
@app.get("/enrolments/<int:enrolment_id>")
def get_enrolment(enrolment_id):
    conn = get_db_connection()

    enrolment = conn.execute("""
        SELECT
            e.enrolment_id,
            e.student_id,
            e.course_id,
            c.course_code,
            c.course_name,
            e.status
        FROM enrolments e
        JOIN courses c
            ON e.course_id = c.course_id
        WHERE e.enrolment_id = ?
    """, (enrolment_id,)).fetchone()

    conn.close()

    if enrolment is None:
        return jsonify({"error": "Enrolment not found"}), 404

    return jsonify(dict(enrolment))


# CREATE - Add enrolment
@app.post("/enrolments")
def create_enrolment():
    data = request.get_json(silent=True) or {}

    student_id = data.get("student_id")
    course_id = data.get("course_id")
    status = str(data.get("status", "Active")).strip()

    try:
        student_id = int(student_id)
        course_id = int(course_id)
    except (TypeError, ValueError):
        return jsonify({
            "error": "student_id and course_id must be integers"
        }), 400

    if not status:
        status = "Active"

    conn = get_db_connection()

    course = conn.execute("""
        SELECT course_id
        FROM courses
        WHERE course_id = ?
    """, (course_id,)).fetchone()

    if course is None:
        conn.close()
        return jsonify({
            "error": "Course not found"
        }), 404

    cursor = conn.execute("""
        INSERT INTO enrolments (
            student_id,
            course_id,
            status
        )
        VALUES (?, ?, ?)
    """, (
        student_id,
        course_id,
        status
    ))

    conn.commit()

    enrolment_id = cursor.lastrowid

    conn.close()

    return jsonify({
        "message": "Student enrolled successfully",
        "enrolment_id": enrolment_id
    }), 201


# UPDATE - Update enrolment
@app.put("/enrolments/<int:enrolment_id>")
def update_enrolment(enrolment_id):
    data = request.get_json(silent=True) or {}

    student_id = data.get("student_id")
    course_id = data.get("course_id")
    status = str(data.get("status", "")).strip()

    try:
        student_id = int(student_id)
        course_id = int(course_id)
    except (TypeError, ValueError):
        return jsonify({
            "error": "student_id and course_id must be integers"
        }), 400

    if not status:
        return jsonify({
            "error": "status is required"
        }), 400

    conn = get_db_connection()

    enrolment = conn.execute("""
        SELECT enrolment_id
        FROM enrolments
        WHERE enrolment_id = ?
    """, (enrolment_id,)).fetchone()

    if enrolment is None:
        conn.close()
        return jsonify({
            "error": "Enrolment not found"
        }), 404

    course = conn.execute("""
        SELECT course_id
        FROM courses
        WHERE course_id = ?
    """, (course_id,)).fetchone()

    if course is None:
        conn.close()
        return jsonify({
            "error": "Course not found"
        }), 404

    conn.execute("""
        UPDATE enrolments
        SET student_id = ?,
            course_id = ?,
            status = ?
        WHERE enrolment_id = ?
    """, (
        student_id,
        course_id,
        status,
        enrolment_id
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Enrolment updated successfully"
    })


# DELETE - Delete enrolment
@app.delete("/enrolments/<int:enrolment_id>")
def delete_enrolment(enrolment_id):
    conn = get_db_connection()

    enrolment = conn.execute("""
        SELECT enrolment_id
        FROM enrolments
        WHERE enrolment_id = ?
    """, (enrolment_id,)).fetchone()

    if enrolment is None:
        conn.close()
        return jsonify({
            "error": "Enrolment not found"
        }), 404

    conn.execute("""
        DELETE FROM enrolments
        WHERE enrolment_id = ?
    """, (enrolment_id,))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Enrolment deleted successfully"
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5002,
        debug=True
    )