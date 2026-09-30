"""Shared agentic loop.

Modes:
    release0  (default) run the Release 0 loop (Student 4's agentic_loop.py), unchanged
    mcp       validate the shared MCP server  (Plan -> Act -> Observe -> Adapt)
    rag       validate the shared RAG server  (Plan -> Act -> Observe -> Adapt)
    all       release0, then mcp, then rag

Run from the repository root, on the host (not in Docker):
    python -m agentic_loop.main --mode mcp
    python -m agentic_loop.main --mode rag
Add --no-ai to skip the local Ollama suggestion in the ADAPT step.
Each Release 1 mode saves its output to docs/release-1/agentic-loop/<mode>-validation.md.
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_student4_loop():
    student4_loop = PROJECT_ROOT / "student-4" / "agentic_loop.py"

    print("=" * 65)
    print("SHARED AGENTIC LOOP")
    print("=" * 65)

    print("\nRunning Student 4 - Course and Enrollment Management")

    result = subprocess.run(
        [sys.executable, str(student4_loop)],
        cwd=PROJECT_ROOT
    )

    if result.returncode == 0:
        print("\nStudent 4 Agentic Loop completed successfully.")
    else:
        print("\nStudent 4 Agentic Loop failed.")
    return result.returncode == 0


def run_mode(title, pipeline, use_ai):
    print("=" * 65)
    print(f"SHARED AGENTIC LOOP - {title} VALIDATION MODE")
    print("=" * 65)
    return pipeline.run(use_ai=use_ai)


def main():
    parser = argparse.ArgumentParser(description="Shared agentic loop (Release 0 + Release 1 validation modes)")
    parser.add_argument("--mode", choices=["release0", "mcp", "rag", "all"], default="release0")
    parser.add_argument("--no-ai", action="store_true", help="skip the local Ollama suggestion in ADAPT")
    args = parser.parse_args()
    use_ai = not args.no_ai

    ok = True
    if args.mode in ("release0", "all"):
        ok = run_student4_loop() and ok
    if args.mode in ("mcp", "all"):
        from agentic_loop.pipelines import mcp_pipeline
        ok = run_mode("MCP", mcp_pipeline, use_ai) and ok
    if args.mode in ("rag", "all"):
        from agentic_loop.pipelines import rag_pipeline
        ok = run_mode("RAG", rag_pipeline, use_ai) and ok

    print("\n" + "=" * 65)
    print("SHARED AGENTIC LOOP COMPLETE" + ("" if ok else " - WITH FAILURES"))
    print("=" * 65)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
