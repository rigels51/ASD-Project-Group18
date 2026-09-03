import os
import sqlite3

from flask import Flask, jsonify, request

app = Flask(__name__)

DATABASE_NAME = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "enrolment.db"))


def initialize_database():
    os.makedirs(os.path.dirname(DATABASE_NAME) or ".", exist_ok=True)
    conn = sqlite3.connect(DATABASE_NAME)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            course TEXT NOT NULL,
            year_level TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            gpa REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Enrolled'
        )
        """
    )

    student_count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    if student_count == 0:
        seed_students = [
            ("STU-1001", "Rigel Rivamonte", "BS Computer Science", "3rd Year", "rigel.rivamonte@uni.edu", "0917 200 1145", 3.72, "Enrolled"),
            ("STU-1002", "Marisol Tan", "BS Information Technology", "2nd Year", "marisol.tan@uni.edu", "0918 442 0093", 3.15, "Enrolled"),
            ("STU-1003", "Andres Villamor", "BS Business Administration", "4th Year", "andres.villamor@uni.edu", "0920 553 7712", 2.98, "On Leave"),
            ("STU-1004", "Priya Nathan", "BS Psychology", "1st Year", "priya.nathan@uni.edu", "0917 664 2201", 3.44, "Enrolled"),
            ("STU-1005", "Julius Bermudez", "BS Civil Engineering", "4th Year", "julius.bermudez@uni.edu", "0919 305 8842", 3.05, "Enrolled"),
            ("STU-1006", "Keisha Alonzo", "BS Computer Science", "2nd Year", "keisha.alonzo@uni.edu", "0921 774 1129", 3.88, "Enrolled"),
            ("STU-1007", "Noel Fajardo", "BS Information Technology", "3rd Year", "noel.fajardo@uni.edu", "0917 883 4420", 2.61, "On Leave"),
            ("STU-1008", "Camille Ordoñez", "BS Psychology", "Graduate", "camille.ordonez@uni.edu", "0918 220 9931", 3.91, "Graduated"),
            ("STU-1009", "Dexter Salcedo", "BS Business Administration", "1st Year", "dexter.salcedo@uni.edu", "0920 114 5567", 3.20, "Enrolled"),
            ("STU-1010", "Faye Bautista", "BS Civil Engineering", "3rd Year", "faye.bautista@uni.edu", "0917 992 3315", 3.63, "Enrolled"),
            ("STU-1011", "Miguel Estrella", "BS Computer Science", "4th Year", "miguel.estrella@uni.edu", "0919 441 7723", 3.30, "Graduated"),
            ("STU-1012", "Anika Roque", "BS Information Technology", "1st Year", "anika.roque@uni.edu", "0918 662 0087", 2.85, "Enrolled"),
        ]
        conn.executemany(
            """
            INSERT INTO students (
                student_id, name, course, year_level, email, phone, gpa, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            seed_students,
        )

    conn.commit()
    conn.close()


initialize_database()


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def serialize_student(row):
    if row is None:
        return None
    student = dict(row)
    if "gpa" in student and student["gpa"] is not None:
        student["gpa"] = float(student["gpa"])
    return student


@app.get("/")
def health():
    return jsonify({"service": "database-service", "status": "running"})


@app.get("/students")
def get_students():
    conn = get_db_connection()
    students = conn.execute(
        "SELECT * FROM students ORDER BY name"
    ).fetchall()
    conn.close()
    return jsonify([serialize_student(row) for row in students])


@app.get("/students/search")
def search_students():
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify([])

    like_query = f"%{query}%"
    conn = get_db_connection()
    students = conn.execute(
        """
        SELECT * FROM students
        WHERE lower(name) LIKE lower(?)
           OR lower(student_id) LIKE lower(?)
           OR lower(course) LIKE lower(?)
        ORDER BY name
        """,
        (like_query, like_query, like_query),
    ).fetchall()
    conn.close()
    return jsonify([serialize_student(row) for row in students])


@app.get("/students/by-id")
def get_student_by_id():
    student_id = request.args.get("student_id", "").strip()
    if not student_id:
        return jsonify({"error": "student_id required"}), 400
    return get_student(student_id)


@app.get("/students/<student_id>")
def get_student(student_id):
    conn = get_db_connection()
    student = conn.execute(
        "SELECT * FROM students WHERE student_id = ?",
        (student_id,),
    ).fetchone()
    conn.close()

    if student is None:
        return jsonify({"error": "Student not found"}), 404

    return jsonify(serialize_student(student))


@app.get("/students/by-subject")
def get_students_by_subject():
    subject_code = request.args.get("subject_code", "").strip()
    if not subject_code:
        return jsonify({"error": "subject_code required"}), 400

    conn = get_db_connection()
    students = conn.execute(
        "SELECT * FROM students WHERE lower(course) = lower(?) ORDER BY name",
        (subject_code,),
    ).fetchall()
    conn.close()

    if not students:
        return jsonify({"error": "No students found"}), 404

    return jsonify([serialize_student(row) for row in students])


@app.post("/students")
def create_student():
    payload = request.get_json(silent=True) or {}
    required_fields = [
        "name",
        "course",
        "year_level",
        "email",
        "gpa",
    ]

    missing = [field for field in required_fields if not payload.get(field)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    student_id = payload.get("student_id") or f"STU-{len(get_students().get_json()) + 1:04d}"
    name = payload["name"].strip()
    course = payload["course"].strip()
    year_level = payload["year_level"].strip()
    email = payload["email"].strip()
    phone = (payload.get("phone") or "").strip()
    gpa = float(payload["gpa"])
    status = (payload.get("status") or "Enrolled").strip()

    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO students (student_id, name, course, year_level, email, phone, gpa, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (student_id, name, course, year_level, email, phone, gpa, status),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify({
        "student_id": student_id,
        "name": name,
        "course": course,
        "year_level": year_level,
        "email": email,
        "phone": phone,
        "gpa": gpa,
        "status": status,
    }), 201


@app.put("/students/<student_id>")
def update_student(student_id):
    payload = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({"error": "No student data provided"}), 400

    conn = get_db_connection()
    current = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    if current is None:
        conn.close()
        return jsonify({"error": "Student not found"}), 404

    updated_name = payload.get("name", current["name"]).strip()
    updated_course = payload.get("course", current["course"]).strip()
    updated_year = payload.get("year_level", current["year_level"]).strip()
    updated_email = payload.get("email", current["email"]).strip()
    updated_phone = (payload.get("phone", current["phone"]) or "").strip()
    updated_gpa = float(payload.get("gpa", current["gpa"]))
    updated_status = (payload.get("status", current["status"]) or "Enrolled").strip()

    conn.execute(
        """
        UPDATE students
        SET name = ?, course = ?, year_level = ?, email = ?, phone = ?, gpa = ?, status = ?
        WHERE student_id = ?
        """,
        (updated_name, updated_course, updated_year, updated_email, updated_phone, updated_gpa, updated_status, student_id),
    )
    conn.commit()
    conn.close()

    return jsonify({
        "student_id": student_id,
        "name": updated_name,
        "course": updated_course,
        "year_level": updated_year,
        "email": updated_email,
        "phone": updated_phone,
        "gpa": updated_gpa,
        "status": updated_status,
    })


@app.delete("/students/<student_id>")
def delete_student(student_id):
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": cursor.rowcount > 0, "student_id": student_id})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
