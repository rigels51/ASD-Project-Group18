# Shared Agentic Loop — TESTING validation mode

Run: 2026-10-20T19:40:46+11:00

## PLAN

Review Release 2 testing evidence for all five students.

- 1. Shared setup: .pre-commit-config.yaml defines ruff-security, detect-secrets and pip-audit.
- 2. Pre-commit: each student's scan report exists and every hook passed (findings fixed or documented).
- 3. CI: each student's student-x.yml exists, ran green on GitHub, and tested >= 2 endpoints.
- Evidence folder: docs/release-2/testing/
## ACT

Reading configuration, scan reports and CI run evidence.

## OBSERVE

3 pass, 0 with findings, 8 missing, 0 fail. Fully evidenced students: S5.

| Owner | Check | Result | Detail |
|---|---|---|---|
| group | pre-commit setup | PASS | config=True, missing hooks=none, secrets baseline=True, ruff config=True |
| S1 Rigel Rivamonte | pre-commit scan | MISSING | no scan captured - run: python3 scripts/capture_test_evidence.py precommit --student 1 |
| S1 Rigel Rivamonte | CI RigelRivamonte.yml | MISSING | no CI run captured - after a green run: python3 scripts/capture_test_evidence.py ci --student 1 (warning: MULTI_AGENT_ENABLED not set in workflow) |
| S2 Jeriko Arceo | pre-commit scan | MISSING | no scan captured - run: python3 scripts/capture_test_evidence.py precommit --student 2 |
| S2 Jeriko Arceo | CI JerikoArceo.yml | MISSING | no CI run captured - after a green run: python3 scripts/capture_test_evidence.py ci --student 2 (warning: MULTI_AGENT_ENABLED not set in workflow) |
| S3 Lazizbek Ismoilov | pre-commit scan | MISSING | no scan captured - run: python3 scripts/capture_test_evidence.py precommit --student 3 |
| S3 Lazizbek Ismoilov | CI student-3.yml | MISSING | no CI run captured - after a green run: python3 scripts/capture_test_evidence.py ci --student 3 (warning: MULTI_AGENT_ENABLED not set in workflow) |
| S4 Yi Zhang | pre-commit scan | MISSING | no scan captured - run: python3 scripts/capture_test_evidence.py precommit --student 4 |
| S4 Yi Zhang | CI YiZhang.yml | MISSING | no CI run captured - after a green run: python3 scripts/capture_test_evidence.py ci --student 4 (warning: MULTI_AGENT_ENABLED not set in workflow) |
| S5 Vu Tien Thanh Nguyen | pre-commit scan | PASS | 3/3 hooks ran; ruff 0 (none), secrets 0, vulnerable deps 0 [2026-10-20T07:57:08+00:00] |
| S5 Vu Tien Thanh Nguyen | CI student-5.yml | PASS | success, 7 passed / 0 failed, endpoints: GET /assessments; POST /assessments |

| Student | Pre-commit | CI | CI run |
|---|---|---|---|
| S1 Rigel Rivamonte | MISSING | MISSING | - |
| S2 Jeriko Arceo | MISSING | MISSING | - |
| S3 Lazizbek Ismoilov | MISSING | MISSING | - |
| S4 Yi Zhang | MISSING | MISSING | - |
| S5 Vu Tien Thanh Nguyen | PASS | PASS | https://github.com/rigels51/ASD-Project-Group18/actions/runs/39394583521 |

## ADAPT

- S1 Rigel Rivamonte / pre-commit scan: MISSING -> no scan captured - run: python3 scripts/capture_test_evidence.py precommit --student 1
- S1 Rigel Rivamonte / CI RigelRivamonte.yml: MISSING -> no CI run captured - after a green run: python3 scripts/capture_test_evidence.py ci --student 1 (warning: MULTI_AGENT_ENABLED not set in workflow)
- S2 Jeriko Arceo / pre-commit scan: MISSING -> no scan captured - run: python3 scripts/capture_test_evidence.py precommit --student 2
- S2 Jeriko Arceo / CI JerikoArceo.yml: MISSING -> no CI run captured - after a green run: python3 scripts/capture_test_evidence.py ci --student 2 (warning: MULTI_AGENT_ENABLED not set in workflow)
- S3 Lazizbek Ismoilov / pre-commit scan: MISSING -> no scan captured - run: python3 scripts/capture_test_evidence.py precommit --student 3
- S3 Lazizbek Ismoilov / CI student-3.yml: MISSING -> no CI run captured - after a green run: python3 scripts/capture_test_evidence.py ci --student 3 (warning: MULTI_AGENT_ENABLED not set in workflow)
- S4 Yi Zhang / pre-commit scan: MISSING -> no scan captured - run: python3 scripts/capture_test_evidence.py precommit --student 4
- S4 Yi Zhang / CI YiZhang.yml: MISSING -> no CI run captured - after a green run: python3 scripts/capture_test_evidence.py ci --student 4 (warning: MULTI_AGENT_ENABLED not set in workflow)
