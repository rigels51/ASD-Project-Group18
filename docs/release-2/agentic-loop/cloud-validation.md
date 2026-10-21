# Shared Agentic Loop — CLOUD validation mode

Run: 2026-10-22T01:38:40+11:00

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

22 pass, 0 warn, 0 missing, 0 fail. Backend read latency: max 1741 ms, avg 1175 ms. Recommended release decision: Release.

| Owner | Check | Result | Detail |
|---|---|---|---|
| group | workflow cloud-deployment.yml | PASS | platform=Azure, gated on CI=True, AI flags off=3/3, credentials from secrets=True |
| group | deploy scripts | PASS | README.md, __init__.py, deploy_azure.py, test_deploy_azure.py |
| group | deployment record | PASS | Azure Container Apps (australiaeast), commit 54130c0, 2026-10-21T14:23:52+00:00, run manual run of scripts/deploy/deploy_azure.py on Lazizbeks-MacBook-Air.local |
| homepage | frontend loads | PASS | https://homepage.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 609 ms |
| student1-frontend | frontend loads | PASS | https://student1-frontend.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 611 ms |
| student2-frontend | frontend loads | PASS | https://student2-frontend.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 696 ms |
| timetable-frontend | frontend loads | PASS | https://timetable-frontend.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 607 ms |
| student4-frontend | frontend loads | PASS | https://student4-frontend.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 599 ms |
| assessment-frontend | frontend loads | PASS | https://assessment-frontend-service.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 612 ms |
| S1 Rigel - Student Records | GET /students | PASS | HTTP 200 in 1096 ms |
| S1 Rigel - Student Records | POST /rag/answer disabled | PASS | HTTP 503 in 737 ms, response says disabled |
| S2 Jeriko - Staff Management | GET /staff | PASS | HTTP 200 in 1230 ms |
| S2 Jeriko - Staff Management | POST /rag/answer disabled | PASS | HTTP 403 in 607 ms, response says disabled |
| S3 Lazizbek - Timetable | GET /timetable | PASS | HTTP 200 in 687 ms |
| S3 Lazizbek - Timetable | POST /rag/answer disabled | PASS | HTTP 503 in 637 ms, response says disabled |
| S3 Lazizbek - Timetable | POST /mcp/call disabled | PASS | HTTP 503 in 611 ms, response says disabled |
| S3 Lazizbek - Timetable | POST /multi-agent/run disabled | PASS | HTTP 503 in 611 ms, response says disabled |
| S4 Yi - Course & Enrollment | GET /courses | PASS | HTTP 200 in 1122 ms |
| S4 Yi - Course & Enrollment | POST /rag/answer disabled | PASS | HTTP 503 in 712 ms, response says disabled |
| S5 Vu - Assessment & Grades | GET /assessments | PASS | HTTP 200 in 1741 ms |
| S5 Vu - Assessment & Grades | POST /rag/ask disabled | PASS | HTTP 503 in 555 ms, response says disabled |
| S5 Vu - Assessment & Grades | POST /multi-agent/run disabled | PASS | HTTP 503 in 560 ms, response says disabled |

## ADAPT

- Every cloud check passed; no rule-based adaptation needed.
- Implementation agent (qwen2.5:0.5b):
```
- The application is usable.
- AI routes (RAG, MCP, Multi-Agent) are disabled.
- Rule-based release recommendation: Release.
```

- Review agent (llama3.1:8b):
```
Risk: low - All checks have passed and the application is usable with AI routes disabled.

Correction: None

Retest: Not required as all checks have passed.

Recommendation: Release - The evidence supports a successful deployment to Azure.
```

## HUMAN RELEASE DECISION

Loop recommendation: Release.

- Release by Lazizbek at 2026-10-21T14:39:04+00:00 (agrees with the loop recommendation).
- Reason: All 22 checks pass: 6 frontends load, 5 backends serve CRUD data, every AI route reports disabled as the baseline requires. Review agent's 'Do not release' misreads disabled-by-default as a fault, so overridden. Supersedes the 14:37 entry, whose reason text was entered in error.
- Logged to docs/release-2/agentic-loop/cloud-release-decisions.jsonl
