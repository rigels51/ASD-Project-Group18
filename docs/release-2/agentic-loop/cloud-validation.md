# Shared Agentic Loop — CLOUD validation mode

Run: 2026-10-28T02:11:51+11:00

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

25 pass, 0 warn, 0 missing, 0 fail. Backend read latency: max 1835 ms, avg 1225 ms. Recommended release decision: Release.

| Owner | Check | Result | Detail |
|---|---|---|---|
| group | workflow cloud-deployment.yml | PASS | platform=Azure, gated on CI=True, AI flags off=3/3, credentials from secrets=True |
| group | deploy scripts | PASS | README.md, __init__.py, deploy_azure.py, test_deploy_azure.py |
| group | deployment record | PASS | Azure Container Apps (australiaeast), commit d3c048b, 2026-10-21T15:09:45+00:00, run https://github.com/rigels51/ASD-Project-Group18/actions/runs/39620962050 |
| homepage | frontend loads | PASS | https://homepage.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 653 ms |
| student1-frontend | frontend loads | PASS | https://student1-frontend.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 610 ms |
| student2-frontend | frontend loads | PASS | https://student2-frontend.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 701 ms |
| timetable-frontend | frontend loads | PASS | https://timetable-frontend.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 607 ms |
| student4-frontend | frontend loads | PASS | https://student4-frontend.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 603 ms |
| assessment-frontend | frontend loads | PASS | https://assessment-frontend-service.victoriouswater-56424206.australiaeast.azurecontainerapps.io - HTTP 200 in 612 ms |
| S1 Rigel - Student Records | GET /students | PASS | HTTP 200 in 1223 ms |
| S1 Rigel - Student Records | POST /rag/answer disabled | PASS | HTTP 503 in 610 ms, response says disabled |
| S2 Jeriko - Staff Management | GET /staff | PASS | HTTP 200 in 1229 ms |
| S2 Jeriko - Staff Management | POST /rag/answer disabled | PASS | HTTP 403 in 608 ms, response says disabled |
| S3 Lazizbek - Timetable | GET /timetable | PASS | HTTP 200 in 611 ms |
| S3 Lazizbek - Timetable | POST /rag/answer disabled | PASS | HTTP 503 in 611 ms, response says disabled |
| S3 Lazizbek - Timetable | POST /mcp/call disabled | PASS | HTTP 503 in 609 ms, response says disabled |
| S3 Lazizbek - Timetable | POST /multi-agent/run disabled | PASS | HTTP 503 in 611 ms, response says disabled |
| S4 Yi - Course & Enrollment | GET /courses | PASS | HTTP 200 in 1225 ms |
| S4 Yi - Course & Enrollment | POST /ask disabled | PASS | HTTP 503 in 610 ms, response says disabled |
| S4 Yi - Course & Enrollment | POST /mcp/run disabled | PASS | HTTP 503 in 610 ms, response says disabled |
| S4 Yi - Course & Enrollment | POST /rag/answer disabled | PASS | HTTP 503 in 609 ms, response says disabled |
| S4 Yi - Course & Enrollment | POST /multi-agent/run disabled | PASS | HTTP 503 in 611 ms, response says disabled |
| S5 Vu - Assessment & Grades | GET /assessments | PASS | HTTP 200 in 1835 ms |
| S5 Vu - Assessment & Grades | POST /rag/ask disabled | PASS | HTTP 503 in 564 ms, response says disabled |
| S5 Vu - Assessment & Grades | POST /multi-agent/run disabled | PASS | HTTP 503 in 661 ms, response says disabled |

## ADAPT

- Every cloud check passed; no rule-based adaptation needed.
- Implementation agent (qwen2.5:0.5b):
```
The deployed application is usable. The AI routes (RAG, MCP, Multi-Agent) are disabled, and the rule-based release recommendation aligns with the baseline cloud profile.
```

- Review agent (llama3.1:8b):
```
Risk: low - The deployment meets all requirements and has been thoroughly tested.

Correction: None

Retest: Not required as all checks have passed.

Recommendation: Release - All tests have passed, including frontend loads and API calls, with AI routes disabled as per the baseline cloud profile.
```

## HUMAN RELEASE DECISION

Loop recommendation: Release.

- Release by Lazizbek at 2026-10-27T15:15:48+00:00 (agrees with the loop recommendation).
- Reason: Release. All checks pass. The agent flagged the disabled MCP, RAG and Multi-Agent routes, but disabled is the required cloud configuration.
- Logged to docs/release-2/agentic-loop/cloud-release-decisions.jsonl
