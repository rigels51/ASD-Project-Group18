import os
import sqlite3

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "staff.db")

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(
    DATABASE_NAME
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS staff (
    staff_id INTEGER PRIMARY KEY,
    given_name TEXT NOT NULL,
    family_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    department TEXT NOT NULL,
    employment_type TEXT NOT NULL,
)
""")

cursor.execute(
    "DELETE FROM staff"
)

staff = [
    (1, "John", "Smith", "john.smith@example.com", "ASD", "Full-time"),
    (2, "Sarah", "Jones", "sarah.jones@example.com", "ASD", "Full-time"),
    (3, "Michael", "Lee", "michael.lee@example.com", "WEB201", "Part-time"),
    (4, "Emma", "Brown", "emma.brown@example.com", "WEB201", "Part-time"),
    (5, "James", "Wilson", "james.wilson@example.com", "DBS101", "Full-time"),
    (6, "Olivia", "White", "olivia.white@example.com", "DBS101", "Full-time"),
    (7, "Daniel", "Green", "daniel.green@example.com", "NET201", "Part-time"),
    (8, "Sophia", "Hall", "sophia.hall@example.com", "NET201", "Part-time"),
    (9, "Liam", "King", "liam.king@example.com", "SEC301", "Full-time"),
    (10, "Chloe", "Young", "chloe.young@example.com", "SEC301", "Full-time"),
]

cursor.executemany(
    """
    INSERT INTO staff (
        staff_id,
        given_name,
        family_name,
        email,
        department,
        employment_type
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """,
    staff
)

conn.commit()
conn.close()

print(
    "Database initialized with 10 staff members."
)