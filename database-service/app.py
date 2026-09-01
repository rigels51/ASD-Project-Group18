from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)

DATABASE_NAME = "/app/data/staff.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def health():
    return jsonify({"service": "database-service", "status": "running"})

@app.get("/staff")
def get_staff():
    conn = get_db_connection()
    staff = conn.execute(
        "SELECT staff_id, given_name, family_name, email, department, employment_type FROM staff"
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in staff])

@app.get("/staff/<int:staff_id>")
def get_staff_member(staff_id):
    conn = get_db_connection()
    staff_member = conn.execute(
        "SELECT staff_id, given_name, family_name, email, department, employment_type FROM staff WHERE staff_id = ?",
        (staff_id,),
    ).fetchone()
    conn.close()

    if staff_member is None:
        return jsonify({"error": "Staff member not found"}), 404

    return jsonify(dict(staff_member))

@app.get("/staff/by-department")
def get_staff_by_department():
    department = request.args.get("department", "").strip().upper()

    if not department:
        return jsonify({"error": "department required"}), 400

    conn = get_db_connection()
    staff = conn.execute(
        "SELECT staff_id, given_name, family_name, email, department, employment_type FROM staff WHERE department = ?",
        (department,),
    ).fetchall()
    conn.close()

    if not staff:
        return jsonify({"error": "No staff found"}), 404

    return jsonify([dict(row) for row in staff])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)