"""Shared agentic loop.

Modes:
    release0  (default) run the Release 0 loop (Student 4's agentic_loop.py), unchanged
    mcp       validate the shared MCP server  (Plan -> Act -> Observe -> Adapt)
    rag       validate the shared RAG server  (Plan -> Act -> Observe -> Adapt)
    multi-agent  Release 2 Multi-Agent Workflow Review (Planner -> Worker -> Reviewer -> Human)
    testing      Release 2 Testing Review (pre-commit security scans + CI endpoint tests, all students)
    cloud        Release 2 Cloud Deployment Review (workflow, scripts, live probes) + human release decision
    all       release0, then mcp, then rag, then multi-agent

Run from the repository root, on the host (not in Docker):
    python -m agentic_loop.main --mode mcp
    python -m agentic_loop.main --mode rag
    python -m agentic_loop.main --mode multi-agent
    python -m agentic_loop.main --mode testing
    python -m agentic_loop.main --mode cloud      # asks for the release decision when run in a terminal
    python -m agentic_loop.main --mode cloud --decision "Release" --reviewer Laz --comment "..."
Add --no-ai to skip the local Ollama suggestion in the ADAPT step.
Release 1 modes save to docs/release-1/agentic-loop/<mode>-validation.md;
Release 2 modes save to docs/release-2/agentic-loop/<mode>-validation.md.
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

    result = subprocess.run(  # noqa: S603 - fixed args: this interpreter + a repo script, no user input
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
    parser.add_argument("--mode", choices=["release0", "mcp", "rag", "multi-agent", "testing", "cloud", "all"], default="release0")
    parser.add_argument("--no-ai", action="store_true", help="skip the local Ollama suggestion in ADAPT")
    parser.add_argument("--decision", choices=["Release", "Release with conditions", "Do not release"],
                        help="cloud mode: record the human release decision without the interactive prompt")
    parser.add_argument("--reviewer", help="cloud mode: name of the person making the release decision")
    parser.add_argument("--comment", default="", help="cloud mode: reason for the release decision")
    parser.add_argument("--no-review", action="store_true", help="cloud mode: skip the interactive decision prompt")
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
    if args.mode in ("multi-agent", "all"):
        from agentic_loop.pipelines import multi_agent_pipeline
        ok = run_mode("MULTI-AGENT", multi_agent_pipeline, use_ai) and ok
    if args.mode in ("testing", "all"):
        from agentic_loop.pipelines import testing_pipeline
        ok = run_mode("TESTING", testing_pipeline, use_ai) and ok
    if args.mode in ("cloud", "all"):
        from agentic_loop.pipelines import cloud_pipeline
        print("=" * 65)
        print("SHARED AGENTIC LOOP - CLOUD DEPLOYMENT REVIEW MODE")
        print("=" * 65)
        ok = cloud_pipeline.run(use_ai=use_ai, decision=args.decision, reviewer=args.reviewer,
                                comment=args.comment,
                                interactive=not args.no_review and args.mode == "cloud") and ok

    print("\n" + "=" * 65)
    print("SHARED AGENTIC LOOP COMPLETE" + ("" if ok else " - WITH FAILURES"))
    print("=" * 65)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
