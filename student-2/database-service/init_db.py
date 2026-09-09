import os
import sqlite3

DATA_DIR = "/app/data"
DATABASE_NAME = os.path.join(DATA_DIR, "staff.db")

os.makedirs(DATA_DIR, exist_ok=True)



conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

cursor.execute("""IF EXISTS staff DROP TABLE staff""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS staff (
    staff_id INTEGER PRIMARY KEY,
    given_name TEXT NOT NULL,
    family_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    department TEXT NOT NULL,
    employment_type TEXT NOT NULL
)
""")

conn.commit()

# Only seed if the table is empty, so re-running this on every container
# start doesn't wipe out staff added later through the app.
existing_count = cursor.execute("SELECT COUNT(*) FROM staff").fetchone()[0]

if existing_count == 0:
    staff = [
        (1, "Jet", "Smith", "jet.smith@example.com", "Computer Science", "Full-time"),
        (2, "Nero", "Garcia", "nero.garcia@example.com", "Arts", "Full-time"),
        (3, "Denver", "Mesa", "denver.mesa@example.com", "Engineering", "Part-time"),
        (4, "Leona", "Pilapil", "leona.pilapil@example.com", "Nursing", "Part-time"),
        (5, "Jerome", "Wilson", "jerome.wilson@example.com", "Marketing", "Full-time"),
        (6, "Angelina", "Kim", "angelina.kim@example.com", "Psychology", "Full-time"),
        (7, "Joey", "Wu", "joey.wu@example.com", "Psychology", "Part-time"),
        (8, "Tiffany", "Day", "tiffany.day@example.com", "Arts", "Part-time"),
        (9, "Jane", "Remover", "jane.remover@example.com", "Arts", "Full-time"),
        (10, "Dave", "Banks", "dave.banks@example.com", "Finance", "Full-time"),
    ]

    cursor.executemany(
        """
        INSERT INTO staff (
            staff_id, given_name, family_name, email, department, employment_type
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        staff,
    )
    conn.commit()
    print("Database initialized with 10 staff members.")
else:
    print(f"Database already has {existing_count} staff member(s); skipping seed.")

conn.close()