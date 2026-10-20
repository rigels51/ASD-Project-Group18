"""Terminal interface: run Planner -> Worker -> Reviewer, then make the human decision here.

    python workflow_runner.py --domain assessment "What assessments are due in ASD101?"
    python workflow_runner.py --status
    python workflow_runner.py --decide <workflow_id>          # decide on a workflow started from the UI
"""

import argparse
import sys

import coordinator
import evidence

LINE = "=" * 70


def show(wf: dict) -> None:
    print(LINE)
    print(f"WORKFLOW {wf['workflow_id']}  [{wf['status']}]  domain={wf.get('domain')}")
    print(f"Request: {wf['user_request']}")
    plan, worker, review = wf.get("planner_result"), wf.get("worker_result"), wf.get("reviewer_result")
    if plan:
        print(f"\n[1] PLANNER ({plan.get('model')}) - {plan['status']}\n{plan.get('plan') or plan.get('error')}")
    if worker:
        print(f"\n[2] WORKER ({worker.get('model')}) - {worker['status']}, evidence={worker['evidence_count']}")
        print(worker["output"])
        for err in worker.get("source_errors") or []:
            print(f"   ! source error: {err}")
    if review:
        print(f"\n[3] REVIEWER ({review.get('model')}) - risk={review['risk_level']}, "
              f"recommends {review['recommended_decision']}")
        print(review["review"])
        print("   checks: " + ", ".join(f"{c['check']}={'PASS' if c['passed'] else 'FAIL'}"
                                     for c in review["automatic_checks"]))
    hd = wf.get("human_decision") or {}
    if hd.get("decision"):
        print(f"\n[4] HUMAN REVIEW - {hd['decision']} by {hd['reviewer']}: {hd.get('comment') or '-'}")
    print(LINE)


def ask_decision(wf: dict) -> None:
    print("\n[4] HUMAN REVIEW")
    options = list(coordinator.DECISIONS)
    for i, name in enumerate(options, 1):
        print(f"  {i} - {name}")
    choice = input("Decision (1-4, Enter to leave pending): ").strip()
    if not choice:
        print("Left pending - decide later from the UI or with --decide.")
        return
    try:
        decision = options[int(choice) - 1]
    except (ValueError, IndexError):
        sys.exit("Invalid choice.")
    reviewer = input("Your name: ").strip()
    comment = input("Comment / reason: ").strip()
    corrected = input("Corrected output: ").strip() if decision == "Correct" else ""
    try:
        show(coordinator.record_decision(wf["workflow_id"], decision, reviewer, comment, corrected))
    except ValueError as exc:
        sys.exit(f"Decision not recorded: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Shared Multi-Agent workflow (terminal)")
    parser.add_argument("request", nargs="?", help="what you want the agents to do")
    parser.add_argument("--domain", choices=sorted(evidence.DOMAINS), help="feature domain (default: auto)")
    parser.add_argument("--status", action="store_true", help="show workflow history summary")
    parser.add_argument("--decide", metavar="WORKFLOW_ID", help="record a decision for an existing workflow")
    parser.add_argument("--no-review", action="store_true", help="skip the interactive decision prompt")
    args = parser.parse_args()

    if args.status:
        st = coordinator.workflow_status()
        print(f"workflows={st['workflow_count']} pending={st['pending_human_review']} "
              f"decisions={st['human_decisions']} audit_lines={st['audit_record_count']}")
        for w in st["latest"]:
            print(f"  {w['timestamp'][:19]} {w['workflow_id'][:8]} {w['domain'] or '-':<10} "
                  f"{w['status']:<20} risk={w['risk_level']} decision={w['decision']}")
        return
    if args.decide:
        wf = coordinator.get_workflow(args.decide)
        if wf is None:
            sys.exit("Workflow not found.")
        show(wf)
        ask_decision(wf)
        return
    if not args.request:
        parser.error("give a request, or use --status / --decide")

    wf = coordinator.run_workflow(args.request, args.domain, caller="terminal")
    show(wf)
    if wf["status"] == "pending_human_review" and not args.no_review:
        ask_decision(wf)


if __name__ == "__main__":
    main()
