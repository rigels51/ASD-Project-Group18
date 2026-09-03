import os
import sqlite3

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "enrolment.db")

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

cursor.execute(
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

cursor.execute("DELETE FROM students")

students = [
    ("STU-1001", "Rigel Rivamonte", "BS Computer Science", "3rd Year", "rigel.rivamonte@uni.edu", "0917 200 1145", 3.72, "Enrolled"),
    ("STU-1002", "Vu Tien Thanh Nguyen", "BS Information Technology", "2nd Year", "marisol.tan@uni.edu", "0918 442 0093", 3.15, "Enrolled"),
    ("STU-1003", "Andres Villamor", "BS Cybersecurity", "4th Year", "andres.villamor@uni.edu", "0920 553 7712", 2.98, "On Leave"),
    ("STU-1004", "Priya Nathan", "BS Psychology", "1st Year", "priya.nathan@uni.edu", "0917 664 2201", 3.44, "Enrolled"),
    ("STU-1005", "Julius Bermudez", "BS Civil Engineering", "4th Year", "julius.bermudez@uni.edu", "0919 305 8842", 3.05, "Enrolled"),
    ("STU-1006", "Keisha Alonzo", "BS Computer Science", "2nd Year", "keisha.alonzo@uni.edu", "0921 774 1129", 3.88, "Enrolled"),
    ("STU-1007", "Noel Fajardo", "BS Information Technology", "3rd Year", "noel.fajardo@uni.edu", "0917 883 4420", 2.61, "On Leave"),
    ("STU-1008", "Jeriko Arceo", "BS Psychology", "Graduate", "camille.ordonez@uni.edu", "0918 220 9931", 3.91, "Graduated"),
    ("STU-1009", "Lazizbek Ismoilov", "BS Cybersecurity", "1st Year", "dexter.salcedo@uni.edu", "0920 114 5567", 3.20, "Enrolled"),
    ("STU-1010", "Yi Zhang", "BS Civil Engineering", "3rd Year", "faye.bautista@uni.edu", "0917 992 3315", 3.63, "Enrolled"),
    ("STU-1011", "Miguel Estrella", "BS Computer Science", "4th Year", "miguel.estrella@uni.edu", "0919 441 7723", 3.30, "Graduated"),
    ("STU-1012", "Anika Roque", "BS Information Technology", "1st Year", "anika.roque@uni.edu", "0918 662 0087", 2.85, "Enrolled"),
]

cursor.executemany(
    """
    INSERT INTO students (
        student_id,
        name,
        course,
        year_level,
        email,
        phone,
        gpa,
        status
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    students,
)

conn.commit()
conn.close()

print("Database initialized with 12 student records.")