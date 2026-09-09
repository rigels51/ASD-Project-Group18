import subprocess
import sys
from pathlib import Path


def run_student4_loop():
    project_root = Path(__file__).resolve().parent.parent
    student4_loop = project_root / "student-4" / "agentic_loop.py"

    print("=" * 65)
    print("SHARED AGENTIC LOOP")
    print("=" * 65)

    print("\nRunning Student 4 - Course and Enrollment Management")

    result = subprocess.run(
        [sys.executable, str(student4_loop)],
        cwd=project_root
    )

    if result.returncode == 0:
        print("\nStudent 4 Agentic Loop completed successfully.")
    else:
        print("\nStudent 4 Agentic Loop failed.")


def main():
    run_student4_loop()

    print("\n" + "=" * 65)
    print("SHARED AGENTIC LOOP COMPLETE")
    print("=" * 65)


if __name__ == "__main__":
    main()