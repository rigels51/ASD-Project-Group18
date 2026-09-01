from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)

DATABASE_NAME = "/app/data/staff.db"

STAFF_COLUMNS = "staff_id, given_name, family_name, email, department, employment_type"
REQUIRED_FIELDS = ("given_name", "family_name", "email", "department", "employment_type")


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def get_request_data():
    """Accepts either JSON body or form-encoded data."""
    data = request.get_json(silent=True)
    if data is None:
        data = request.form
    return data


@app.get("/")
def health():
    return jsonify({"service": "database-service", "status": "running"})


@app.get("/staff")
def get_staff():
    conn = get_db_connection()
    staff = conn.execute(f"SELECT {STAFF_COLUMNS} FROM staff").fetchall()
    conn.close()
    return jsonify([dict(row) for row in staff])


@app.get("/staff/<int:staff_id>")
def get_staff_member(staff_id):
    conn = get_db_connection()
    staff_member = conn.execute(
        f"SELECT {STAFF_COLUMNS} FROM staff WHERE staff_id = ?",
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
        f"SELECT {STAFF_COLUMNS} FROM staff WHERE department = ?",
        (department,),
    ).fetchall()
    conn.close()

    if not staff:
        return jsonify({"error": "No staff found"}), 404

    return jsonify([dict(row) for row in staff])


@app.post("/staff")
def create_staff():
    data = get_request_data()

    values = {field: (data.get(field) or "").strip() for field in REQUIRED_FIELDS}
    missing = [field for field, value in values.items() if not value]
    if missing:
        return jsonify({"error": f"Missing required field(s): {', '.join(missing)}"}), 400

    values["department"] = values["department"].upper()

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO staff (given_name, family_name, email, department, employment_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                values["given_name"],
                values["family_name"],
                values["email"],
                values["department"],
                values["employment_type"],
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "A staff member with that email already exists"}), 409

    staff_member = conn.execute(
        f"SELECT {STAFF_COLUMNS} FROM staff WHERE staff_id = ?",
        (new_id,),
    ).fetchone()
    conn.close()

    return jsonify(dict(staff_member)), 201


@app.put("/staff/<int:staff_id>")
def update_staff(staff_id):
    data = get_request_data()

    fields = {}
    for field in REQUIRED_FIELDS:
        value = (data.get(field) or "").strip()
        if value:
            fields[field] = value.upper() if field == "department" else value

    if not fields:
        return jsonify({"error": "No fields provided to update"}), 400

    conn = get_db_connection()
    existing = conn.execute(
        "SELECT staff_id FROM staff WHERE staff_id = ?", (staff_id,)
    ).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Staff member not found"}), 404

    set_clause = ", ".join(f"{field} = ?" for field in fields)
    try:
        conn.execute(
            f"UPDATE staff SET {set_clause} WHERE staff_id = ?",
            (*fields.values(), staff_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "A staff member with that email already exists"}), 409

    staff_member = conn.execute(
        f"SELECT {STAFF_COLUMNS} FROM staff WHERE staff_id = ?",
        (staff_id,),
    ).fetchone()
    conn.close()

    return jsonify(dict(staff_member))


@app.delete("/staff/<int:staff_id>")
def delete_staff(staff_id):
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT staff_id FROM staff WHERE staff_id = ?", (staff_id,)
    ).fetchone()
    if existing is None:
        conn.close()
        return jsonify({"error": "Staff member not found"}), 404

    conn.execute("DELETE FROM staff WHERE staff_id = ?", (staff_id,))
    conn.commit()
    conn.close()

    return jsonify({"deleted": staff_id})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)