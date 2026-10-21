# Shared Agentic Loop — CLOUD validation mode

Run: 2026-10-22T02:31:37+11:00

## PLAN

Decide whether the Release 2 cloud deployment can be released.

- 1. Workflow: cloud-deployment.yml runs after CI, deploys to Azure or AWS, sets MCP_ENABLED, RAG_ENABLED, MULTI_AGENT_ENABLED to false (baseline profile).
- 2. Scripts: reusable deploy scripts in scripts/deploy/.
- 3. Record: docs/release-2/cloud/deployment.json shows a successful deployment (platform, commit, run URL, endpoints).
- 4. Live: every frontend loads, every backend read route returns 200, every AI route reports disabled.
- 5. Human: a person records the final release decision.
## ACT

Reading the workflow, scripts and deployment record; probing the deployed endpoints (read-only).

## OBSERVE

22 pass, 0 warn, 0 missing, 0 fail. Backend read latency: max 1741 ms, avg 1178 ms. Recommended release decision: Release.

| Owner | Check | Result | Detail |
|---|---|---|---|
| group | workflow cloud-deployment.yml | PASS | platform=Azure, gated on CI=True, AI flags off=3/3, credentials from secrets=True |
| group | deploy scripts | PASS | README.md, __init__.py, deploy_azure.py, test_deploy_azure.py |
| group | deployment record | PASS | Azure Container Apps (australiaeast), commit d3c048b, 2026-10-21T15:09:45+00:00, run https://github.com/rigels51/ASD-Project-Group18/actions/runs/39620962050 |
| homepage | frontend loads | PASS | https://homepage.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 615 ms |
| student1-frontend | frontend loads | PASS | https://student1-frontend.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 596 ms |
| student2-frontend | frontend loads | PASS | https://student2-frontend.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 607 ms |
| timetable-frontend | frontend loads | PASS | https://timetable-frontend.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 605 ms |
| student4-frontend | frontend loads | PASS | https://student4-frontend.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 602 ms |
| assessment-frontend | frontend loads | PASS | https://assessment-frontend-service.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 578 ms |
| S1 Rigel - Student Records | GET /students | PASS | HTTP 200 in 1155 ms |
| S1 Rigel - Student Records | POST /rag/answer disabled | PASS | HTTP 503 in 610 ms, response says disabled |
| S2 Jeriko - Staff Management | GET /staff | PASS | HTTP 200 in 1227 ms |
| S2 Jeriko - Staff Management | POST /rag/answer disabled | PASS | HTTP 403 in 607 ms, response says disabled |
| S3 Lazizbek - Timetable | GET /timetable | PASS | HTTP 200 in 587 ms |
| S3 Lazizbek - Timetable | POST /rag/answer disabled | PASS | HTTP 503 in 554 ms, response says disabled |
| S3 Lazizbek - Timetable | POST /mcp/call disabled | PASS | HTTP 503 in 561 ms, response says disabled |
| S3 Lazizbek - Timetable | POST /multi-agent/run disabled | PASS | HTTP 503 in 576 ms, response says disabled |
| S4 Yi - Course & Enrollment | GET /courses | PASS | HTTP 200 in 1182 ms |
| S4 Yi - Course & Enrollment | POST /rag/answer disabled | PASS | HTTP 503 in 610 ms, response says disabled |
| S5 Vu - Assessment & Grades | GET /assessments | PASS | HTTP 200 in 1741 ms |
| S5 Vu - Assessment & Grades | POST /rag/ask disabled | PASS | HTTP 503 in 606 ms, response says disabled |
| S5 Vu - Assessment & Grades | POST /multi-agent/run disabled | PASS | HTTP 503 in 613 ms, response says disabled |

## ADAPT

- Every cloud check passed; no rule-based adaptation needed.
- Implementation agent (qwen2.5:0.5b):
```
The deployed application is usable with the AI routes reporting disabled.
```

- Review agent (llama3.1:8b):
```
Risk: low - The deployment appears to be successful with all routes reporting disabled.

Correction: None

Retest: Retest the deployment with AI routes enabled to ensure functionality is as expected.

Recommendation: Do not release - While the deployment is technically successful, it's unclear how the application will function with AI routes enabled.
```

## HUMAN RELEASE DECISION

Loop recommendation: Release.

- Release by Lazizbek at 2026-10-21T15:32:07+00:00 (agrees with the loop recommendation).
- Reason: Automated deployment via cloud-deployment.yml (run 39620962050): CI gate green for all 5 student workflows, all checks pass, AI services disabled by default.
- Logged to docs/release-2/agentic-loop/cloud-release-decisions.jsonl
