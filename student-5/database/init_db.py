import os
import sqlite3

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "assessment_grades.db")

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS assessments (
    assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    assessment_name TEXT NOT NULL,
    assessment_type TEXT NOT NULL,
    description TEXT,
    due_date TEXT NOT NULL,
    max_mark REAL NOT NULL,
    weight REAL NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS grades (
    grade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    mark REAL,
    grade TEXT,
    feedback TEXT,
    date_recorded TEXT NOT NULL,
    FOREIGN KEY (assessment_id) REFERENCES assessments (assessment_id)
)
""")

cursor.execute("DELETE FROM assessments")
cursor.execute("DELETE FROM grades")

assessments = [
    (1, "ASD101", "Assignment 1 - Design Doc",   "Assignment", "Software design document",         "2026-09-05", 100, 20),
    (2, "ASD101", "Mid-Semester Test",           "Test",       "Closed book, 1 hour",               "2026-09-19", 50,  15),
    (3, "ASD101", "Final Project",               "Project",    "Team microservices project",        "2026-10-24", 100, 40),
    (4, "WEB201", "Assignment 1 - Frontend",      "Assignment", "HTMX front-end build",              "2026-09-08", 100, 25),
    (5, "WEB201", "Practical Exam",               "Exam",       "In-lab practical assessment",       "2026-10-10", 100, 35),
    (6, "DBS101", "Database Design Report",       "Assignment", "ER diagram and normalisation",      "2026-09-12", 100, 20),
    (7, "DBS101", "Final Exam",                   "Exam",       "Closed book, 2 hours",              "2026-11-05", 100, 45),
    (8, "NET201", "Networking Lab Journal",       "Assignment", "Weekly lab write-ups",              "2026-09-15", 60,  15),
    (9, "SEC301", "Security Audit Report",        "Assignment", "Vulnerability assessment report",   "2026-09-22", 100, 30),
    (10, "SEC301", "Capstone Presentation",       "Presentation", "10 minute team presentation",     "2026-10-30", 50,  20),
]

cursor.executemany(
    """
    INSERT INTO assessments (
        assessment_id, course_id, assessment_name, assessment_type,
        description, due_date, max_mark, weight
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    assessments,
)

grades = [
    (1, 1, 1, 88, "HD", "Excellent design coverage.",        "2026-09-10"),
    (2, 1, 2, 74, "D",  "Good structure, minor gaps.",       "2026-09-10"),
    (3, 2, 1, 42, "D",  "Strong understanding of concepts.", "2026-09-20"),
    (4, 2, 2, 35, "C",  "Solid but rushed in places.",       "2026-09-20"),
    (5, 4, 3, 91, "HD", "Polished, responsive UI.",           "2026-09-11"),
    (6, 4, 4, 68, "C",  "Functional but limited styling.",   "2026-09-11"),
    (7, 6, 5, 80, "D",  "Well-normalised schema.",            "2026-09-14"),
    (8, 6, 6, 55, "P",  "Meets minimum requirements.",        "2026-09-14"),
    (9, 8, 7, 48, "D",  "Consistent weekly submissions.",     "2026-09-18"),
    (10, 9, 9, 92, "HD", "Thorough audit methodology.",       "2026-09-25"),
    (11, 9, 10, 77, "D", "Good coverage, missing one CVE.",   "2026-09-25"),
    (12, 3, 1, None, None, None,                              "2026-10-24"),
]

cursor.executemany(
    """
    INSERT INTO grades (
        grade_id, assessment_id, student_id, mark, grade, feedback, date_recorded
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    grades,
)

conn.commit()
conn.close()

print("Database initialized with assessments and grades records.")
