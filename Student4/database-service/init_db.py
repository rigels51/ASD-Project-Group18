import os
import sqlite3

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "enrolment.db")

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

# Enable foreign key support
cursor.execute("PRAGMA foreign_keys = ON")

# -------------------------
# Create courses table
# -------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS courses (
    course_id INTEGER PRIMARY KEY,
    course_code TEXT NOT NULL UNIQUE,
    course_name TEXT NOT NULL,
    credits INTEGER NOT NULL,
    capacity INTEGER NOT NULL
)
""")

# -------------------------
# Create enrolments table
# -------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS enrolments (
    enrolment_id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
)
""")

# Clear old data
cursor.execute("DELETE FROM enrolments")
cursor.execute("DELETE FROM courses")

# -------------------------
# Course sample data
# -------------------------
courses = [
    (1, "ASD101", "Advanced Software Development", 6, 30),
    (2, "DBS101", "Database Systems", 6, 25),
    (3, "WEB201", "Web Development", 6, 40),
    (4, "NET201", "Computer Networks", 6, 30),
    (5, "SEC301", "Cyber Security", 6, 25),
    (6, "DAT201", "Data Analytics", 6, 35),
    (7, "AIT101", "Artificial Intelligence", 6, 30),
    (8, "CLD201", "Cloud Computing", 6, 25),
    (9, "SWE301", "Software Engineering", 6, 40),
    (10, "PMT101", "Project Management", 6, 30),
]

cursor.executemany("""
INSERT INTO courses (
    course_id,
    course_code,
    course_name,
    credits,
    capacity
)
VALUES (?, ?, ?, ?, ?)
""", courses)

# -------------------------
# Enrolment sample data
# -------------------------
enrolments = [
    (1, 1001, 1, "Active"),
    (2, 1002, 1, "Active"),
    (3, 1003, 2, "Active"),
    (4, 1004, 2, "Completed"),
    (5, 1005, 3, "Active"),
    (6, 1006, 4, "Active"),
    (7, 1007, 5, "Withdrawn"),
    (8, 1008, 6, "Active"),
    (9, 1009, 7, "Active"),
    (10, 1010, 8, "Completed"),
]

cursor.executemany("""
INSERT INTO enrolments (
    enrolment_id,
    student_id,
    course_id,
    status
)
VALUES (?, ?, ?, ?)
""", enrolments)

conn.commit()
conn.close()

print("Database initialized with 10 courses and 10 enrolments.")