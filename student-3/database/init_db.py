import sqlite3
from pathlib import Path

DATABASE_NAME = Path(__file__).with_name("timetable.db")

sessions = [
    (1, "ASD101", None, "Lecture",  "Monday",    "09:00", "11:00", "CB01.02.15", "2026-S2"),
    (2, "ASD101", None, "Tutorial", "Monday",    "11:00", "12:00", "CB01.02.16", "2026-S2"),
    (3, "WEB201", None, "Lecture",  "Tuesday",   "09:00", "11:00", "CB01.03.01", "2026-S2"),
    (4, "WEB201", None, "Lab",      "Tuesday",   "13:00", "15:00", "CB01.03.02", "2026-S2"),
    (5, "DBS101", None, "Lecture",  "Wednesday", "10:00", "12:00", "CB02.01.10", "2026-S2"),
    (6, "DBS101", None, "Tutorial", "Wednesday", "13:00", "14:00", "CB02.01.11", "2026-S2"),
    (7, "NET201", None, "Lecture",  "Thursday",  "09:00", "11:00", "CB02.02.05", "2026-S2"),
    (8, "NET201", None, "Lab",      "Thursday",  "14:00", "16:00", "CB02.02.06", "2026-S2"),
    (9, "SEC301", None, "Lecture",  "Friday",    "09:00", "11:00", "CB03.01.01", "2026-S2"),
    (10, "SEC301", None, "Tutorial", "Friday",   "11:00", "12:00", "CB03.01.02", "2026-S2"),
]


def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS timetable (
        session_id INTEGER PRIMARY KEY,
        course_code TEXT NOT NULL,
        staff_id TEXT,
        session_type TEXT NOT NULL,
        day TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        room TEXT NOT NULL,
        semester TEXT NOT NULL
    )
    """)

    cursor.execute("DELETE FROM timetable")

    cursor.executemany(
        """
        INSERT INTO timetable
        (session_id, course_code, staff_id, session_type, day, start_time, end_time, room, semester)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        sessions
    )

    conn.commit()
    conn.close()

    print(f"Database initialized with {len(sessions)} timetable sessions.")


if __name__ == "__main__":
    init_db()
