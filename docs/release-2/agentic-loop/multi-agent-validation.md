# Shared Agentic Loop — MULTI-AGENT validation mode

Run: 2026-10-21T00:33:15+11:00

## PLAN

Review the shared Multi-Agent server at http://localhost:5004.

- 1. Static check: required agent/coordinator files exist and the coordinator calls every agent and the human-review step.
- 2. Health check: server running, three agents + human reviewer registered.
- 3. Run 6 live Planner -> Worker -> Reviewer workflows (one per feature domain + one no-evidence case).
- 4. Inspect workflow_history.jsonl / coordination_audit.jsonl: handoffs logged, human decisions recorded.
## ACT

Collecting implementation, live-run and audit evidence.

## OBSERVE

10 passed, 0 failed.

| Area | Check | Result | Detail |
|---|---|---|---|
| implementation | files + coordinator wiring | PASS | complete |
| server | health + agents | PASS | agents=['planner_agent', 'worker_agent', 'reviewer_agent', 'human_reviewer'], models={'planner': 'qwen2.5:0.5b', 'reviewer': 'llama3.1:8b', 'worker': 'qwen2.5:0.5b'} |
| students | Summarise the students who are currently On Leave. | PASS | evidence=12, risk=low, recommends Partially Accept, worker=qwen2.5:0.5b (11259 ms) |
| staff | Summarise the staff in the Arts department. | PASS | evidence=10, risk=low, recommends Partially Accept, worker=qwen2.5:0.5b (11011 ms) |
| timetable | Summarise the timetable sessions for ASD101. | PASS | evidence=2, risk=low, recommends Partially Accept, worker=qwen2.5:0.5b (14346 ms) |
| course | Summarise course ASD101 and its enrolments. | PASS | evidence=3, risk=low, recommends Accept, worker=qwen2.5:0.5b (8558 ms) |
| assessment | Summarise the assessments and weights for ASD101. | PASS | evidence=8, risk=low, recommends Accept, worker=qwen2.5:0.5b (13995 ms) |
| assessment | List the assessments for XYZ999. | PASS | no evidence and reviewer correctly flagged high risk (9149 ms) |
| evidence | coordination audit log | PASS | 153 audit lines for 28 workflows |
| evidence | human decisions recorded | PASS | {'Accept': 2, 'Correct': 1, 'Partially Accept': 2, 'Reject': 8}; pending=15 |

- [students] Summarise the students who are currently On Leave. (workflow b2caeee8-3dfc-408d-a437-8e5a9fabe607)
```
PLANNER:
Objective: To summarize the students who are currently on leave.
Steps: [{'step': 'Filter by course codes', 'value': 'student_ids'}, {'step': 'Filter by student IDs', 'value': 'course_codes'}]
Evidence Required: None
Human Approval: No evidence required for this task.

WORKER:
To summarize the students who are currently on leave, we need to filter out those with a status of "On Leave". The student IDs that meet this criterion are listed in the first record: STU-1004 and STU-1001.

REVIEWER:
Risk: Low - The worker's output is generally accurate, but it only lists two student IDs that meet the criterion of being on leave.

Correction: None

Retest: Retest with a larger sample size to ensure all students on leave are identified.

Recommendation: Partially Accept - The worker correctly identified some students who are on leave, but more evidence and filtering is needed to accurately summarize all students in this status.
```

- [staff] Summarise the staff in the Arts department. (workflow 056599cd-f52f-454f-a75f-ed661faa3e9b)
```
PLANNER:
Objective: Summarize the staff in the Arts department.
Steps: Filter by course codes and student IDs.
Evidence Required: None required for this task.
Human Approval: No human approval is needed as the system already has access to the necessary data sources.

WORKER:
The staff in the Arts department includes Jet Smith, Nero Garcia, Denver Mesa, Leona Pilapil, Jerome Wilson, Angelina Kim, Joey Wu, Tiffany Day, Jane Remover, and Dave Banks.

REVIEWER:
Risk: Low - The worker's output is mostly accurate, but it includes some staff members not in the Arts department.

Correction: Remove Jerome Wilson, Angelina Kim, Joey Wu, and Dave Banks from the list as they are not part of the Arts department.

Retest: Retest with updated filtering to ensure only Arts department staff are included.

Recommendation: Partially Accept - The worker's output is mostly correct but requires some corrections to meet the task requirements.
```

## ADAPT

- All checks passed; no rule-based adaptation needed.
- Implementation agent (qwen2.5:0.5b):
```
The shared multi-agent orchestration layer is validated with clear responsibilities and evidence-based outcomes.
```

- Review agent (llama3.1:8b):
```
Here is the review of the multi-agent run using only the supplied handoff evidence:

**Strengths:**

* Clear responsibilities and outcomes for each agent
* Handoffs are logged and traceable through the coordination audit log
* Human decisions are recorded, including Accept, Partially Accept, Correct, and Reject

**Risks:**

* High risk flagged in assessment | List the assessments for XYZ999 due to lack of evidence
* Potential for errors or inaccuracies in worker output, as seen in students | Summarize the students who are currently On Leave (risk=low)

**Recommendations:**

* Review and refine agent models to improve accuracy and reduce risk
* Implement additional checks or filters to ensure accurate results in high-risk tasks
```

