"""pre-commit hook: run pip-audit on the requirements files being committed.

pre-commit passes the staged requirements*.txt paths; pip-audit needs each one as `-r <file>`.
Exit code is pip-audit's: non-zero (commit blocked) if any dependency has a known vulnerability.
"""

import subprocess  # noqa: S404 - runs the pip-audit CLI with fixed arguments
import sys


def main() -> int:
    files = [f for f in sys.argv[1:] if f.endswith(".txt")]
    if not files:
        return 0
    args = [sys.executable, "-m", "pip_audit", "--progress-spinner", "off", "--desc", "off"]
    for f in files:
        args += ["-r", f]
    print("pip-audit:", " ".join(files))
    return subprocess.call(args)  # noqa: S603 - fixed program, file paths come from git


if __name__ == "__main__":
    sys.exit(main())
