from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI
import sqlite3
import os

load_dotenv()

import mcp_client
import rag_client

DATABASE_NAME = "timetable.db"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

app = Flask(__name__)
CORS(app)

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama"
)


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    return {key: row[key] for key in row.keys()}


def sessions_to_html(sessions):
    html = (
        "<table>"
        "<thead><tr>"
        "<th>ID</th><th>Course</th><th>Type</th><th>Day</th>"
        "<th>Start</th><th>End</th><th>Room</th><th>Semester</th>"
        "</tr></thead><tbody>"
    )
    for s in sessions:
        html += (
            f"<tr>"
            f"<td>{s['session_id']}</td>"
            f"<td>{s['course_code']}</td>"
            f"<td>{s['session_type']}</td>"
            f"<td>{s['day']}</td>"
            f"<td>{s['start_time']}</td>"
            f"<td>{s['end_time']}</td>"
            f"<td>{s['room']}</td>"
            f"<td>{s['semester']}</td>"
            f"</tr>"
        )
    html += "</tbody></table>"
    return html


# ---------- READ ----------

@app.route("/timetable")
def get_timetable():
    conn = get_db_connection()
    sessions = conn.execute("SELECT * FROM timetable").fetchall()
    conn.close()
    return sessions_to_html(sessions)


@app.route("/timetable/<int:session_id>")
def get_session(session_id):
    conn = get_db_connection()
    session = conn.execute(
        "SELECT * FROM timetable WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()

    if session is None:
        return "<p>Session not found.</p>", 404

    return sessions_to_html([session])


@app.route("/timetable/by-course")
def get_sessions_by_course():
    course_code = request.args.get("course_code", "").strip()

    if not course_code:
        return "<p>course_code is required.</p>", 400

    conn = get_db_connection()
    sessions = conn.execute(
        "SELECT * FROM timetable WHERE course_code = ?", (course_code,)
    ).fetchall()
    conn.close()

    if not sessions:
        return "<p>No sessions found for this course.</p>", 404

    return sessions_to_html(sessions)


# ---------- CREATE ----------

@app.route("/timetable", methods=["POST"])
def create_session():
    data = request.form

    required = ["course_code", "session_type", "day", "start_time", "end_time", "room", "semester"]
    missing = [f for f in required if not data.get(f, "").strip()]
    if missing:
        return f"<p>Missing required field(s): {', '.join(missing)}</p>", 400

    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO timetable
        (course_code, staff_id, session_type, day, start_time, end_time, room, semester)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["course_code"],
            data.get("staff_id") or None,
            data["session_type"],
            data["day"],
            data["start_time"],
            data["end_time"],
            data["room"],
            data["semester"],
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return f"<p>Session created with ID {new_id}.</p>", 201


# ---------- UPDATE ----------

@app.route("/timetable/<int:session_id>", methods=["PUT"])
def update_session(session_id):
    data = request.form

    conn = get_db_connection()
    existing = conn.execute(
        "SELECT * FROM timetable WHERE session_id = ?", (session_id,)
    ).fetchone()

    if existing is None:
        conn.close()
        return "<p>Session not found.</p>", 404

    updated = {
        "course_code": data.get("course_code", existing["course_code"]),
        "staff_id": data.get("staff_id", existing["staff_id"]),
        "session_type": data.get("session_type", existing["session_type"]),
        "day": data.get("day", existing["day"]),
        "start_time": data.get("start_time", existing["start_time"]),
        "end_time": data.get("end_time", existing["end_time"]),
        "room": data.get("room", existing["room"]),
        "semester": data.get("semester", existing["semester"]),
    }

    conn.execute(
        """
        UPDATE timetable
        SET course_code = ?, staff_id = ?, session_type = ?, day = ?,
            start_time = ?, end_time = ?, room = ?, semester = ?
        WHERE session_id = ?
        """,
        (*updated.values(), session_id),
    )
    conn.commit()
    conn.close()

    return f"<p>Session {session_id} updated.</p>"


# ---------- DELETE ----------

@app.route("/timetable/<int:session_id>", methods=["DELETE"])
def delete_session(session_id):
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT * FROM timetable WHERE session_id = ?", (session_id,)
    ).fetchone()

    if existing is None:
        conn.close()
        return "<p>Session not found.</p>", 404

    conn.execute("DELETE FROM timetable WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

    return f"<p>Session {session_id} deleted.</p>"


# ---------- CLASH DETECTION ----------

@app.route("/timetable/clashes")
def get_clashes():
    conn = get_db_connection()
    sessions = conn.execute("SELECT * FROM timetable").fetchall()
    conn.close()

    sessions = [row_to_dict(s) for s in sessions]
    clashes = []

    for i in range(len(sessions)):
        for j in range(i + 1, len(sessions)):
            a, b = sessions[i], sessions[j]
            if a["day"] != b["day"] or a["room"] != b["room"]:
                continue
            if a["start_time"] < b["end_time"] and b["start_time"] < a["end_time"]:
                clashes.append((a, b))

    if not clashes:
        return "<p>No clashes detected.</p>"

    html = "<ul>"
    for a, b in clashes:
        html += (
            f"<li>Clash: session {a['session_id']} ({a['course_code']}) "
            f"and session {b['session_id']} ({b['course_code']}) "
            f"both in {a['room']} on {a['day']} "
            f"({a['start_time']}-{a['end_time']} overlaps "
            f"{b['start_time']}-{b['end_time']})</li>"
        )
    html += "</ul>"

    return html


# ---------- JSON API (read by the Timetable MCP server) ----------

@app.route("/api/timetable")
def get_timetable_json():
    conn = get_db_connection()
    sessions = conn.execute("SELECT * FROM timetable ORDER BY session_id").fetchall()
    conn.close()
    return jsonify([row_to_dict(s) for s in sessions])


# ---------- RELEASE 1: MCP TOOLS ----------

@app.route("/mcp/tools")
def mcp_list_tools():
    if not mcp_client.MCP_ENABLED:
        return jsonify({"status": "disabled", "error": "MCP is disabled (MCP_ENABLED=false)"}), 503
    try:
        return jsonify({"status": "success", "tools": mcp_client.list_timetable_tools()})
    except Exception:
        return jsonify({"status": "error", "error": f"MCP server unavailable at {mcp_client.MCP_SERVER_URL}"}), 503


@app.route("/mcp/call", methods=["POST"])
def mcp_call_tool():
    if not mcp_client.MCP_ENABLED:
        return jsonify({"status": "disabled", "error": "MCP is disabled (MCP_ENABLED=false)"}), 503

    payload = request.get_json(silent=True) or {}
    tool = payload.get("tool", "")
    arguments = payload.get("arguments") or {}

    if tool not in mcp_client.ALLOWED_TOOLS:
        return jsonify({"status": "error", "error": f"Unknown tool '{tool}'"}), 400
    if not isinstance(arguments, dict):
        return jsonify({"status": "error", "error": "arguments must be a JSON object"}), 400

    try:
        result = mcp_client.call_timetable_tool(tool, arguments)
        return jsonify({"status": "success", "tool": tool, "arguments": arguments, "result": result})
    except RuntimeError as exc:
        return jsonify({"status": "error", "tool": tool, "error": str(exc)}), 400
    except Exception:
        return jsonify({"status": "error", "tool": tool, "error": f"MCP server unavailable at {mcp_client.MCP_SERVER_URL}"}), 503


# ---------- RELEASE 1: RAG GROUNDED ANSWERS ----------

@app.route("/rag/answer", methods=["POST"])
def rag_answer():
    if not rag_client.RAG_ENABLED:
        return jsonify({"status": "disabled", "error": "RAG is disabled (RAG_ENABLED=false)"}), 503

    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()

    if not question:
        return jsonify({"status": "error", "error": "question is required"}), 400

    try:
        result, status_code = rag_client.ask_rag(question)
        return jsonify(result), status_code
    except Exception:
        return jsonify({"status": "error", "error": f"RAG server unavailable at {rag_client.RAG_SERVER_URL}"}), 503


# ---------- AI AGENT ----------

@app.route("/ask", methods=["POST"])
def ask_local_agent():
    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400

    conn = get_db_connection()
    sessions = conn.execute("SELECT * FROM timetable").fetchall()
    conn.close()

    context_lines = [
        f"{s['course_code']} {s['session_type']} - {s['day']} "
        f"{s['start_time']}-{s['end_time']} in {s['room']} ({s['semester']})"
        for s in sessions
    ]
    context = "\n".join(context_lines)

    try:
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a concise university timetable assistant. "
                        "Only use the session data provided below to answer. "
                        "If the answer isn't in the data, say so.\n\n"
                        f"Timetable data:\n{context}"
                    )
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            max_tokens=200,
            temperature=0.2,
        )

        answer = response.choices[0].message.content
        return f"<p>{answer}</p>"

    except Exception as exc:
        return (
            "<p>Local AI agent request failed. "
            "Check that Ollama is running and the model is installed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5003)
