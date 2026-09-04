# Evidence Log — Timetable & Class Scheduling Microservice

Owner: Lazizbek Ismoilov (Student 3)
Feature: Timetable & Class Scheduling
Run timestamp: 2026-09-02T15:49:24Z
Environment: Dockerised (docker compose), macOS (Apple Silicon)

## Standalone Containerisation

| Check | Result | Detail |
|---|---|---|
| Backend Dockerfile builds | PASS | `python:3.12-slim`, deps installed, `init_db.py` run at build time |
| Frontend Dockerfile builds | PASS | `nginx:alpine` serving static HTML/CSS |
| `docker compose up --build` | PASS | Both containers start clean, no crash-loop |
| Backend bound to 0.0.0.0 | PASS | Required fix — default Flask binding (127.0.0.1) is unreachable from outside the container |
| CORS enabled (flask-cors) | PASS | Required — frontend (port 8003) and backend (port 5003) are different origins |
| Ollama reachable from container | PASS | Required `host.docker.internal` + `extra_hosts: host-gateway`, since Ollama runs on the host, not in a container |

## Endpoint Validation (containerised)

| Check | Expected | Actual | Pass/Fail |
|---|---|---|---|
| GET /timetable | 200, 10 sessions | 200 | PASS |
| GET /timetable/1 | 200, session detail | 200 | PASS |
| GET /timetable/999 | 404 not found | 404 | PASS |
| GET /timetable/by-course?course_code=ASD101 | 200, matching sessions | 200 | PASS |
| GET /timetable/by-course?course_code=ZZZ999 | 404 no match | 404 | PASS |
| POST /timetable (valid, clashing) | 201 created | 201 | PASS |
| POST /timetable (missing fields) | 400 bad request | 400 | PASS |
| GET /timetable/clashes (clash present) | 200, clash listed | 200, clash detected | PASS |
| PUT /timetable/&lt;id&gt; (resolve clash) | 200 updated | 200 | PASS |
| GET /timetable/clashes (after fix) | 200, no clashes | 200, "No clashes detected." | PASS |
| PUT /timetable/999 (non-existent) | 404 not found | 404 | PASS |
| DELETE /timetable/&lt;id&gt; | 200 deleted | 200 | PASS |
| DELETE /timetable/999 (non-existent) | 404 not found | 404 | PASS |
| GET /timetable (final state) | 200, back to 10 records | 200, 10 rows | PASS |
| POST /ask (valid question) | 200, grounded answer | 200 | PASS |
| POST /ask (empty question) | 400 bad request | 400 | PASS |

**Summary: 16/16 checks passed.**

## Non-Functional Requirement Validation

**Requirement:** GET /timetable returns within 500ms.

**Test:** 20 sequential requests to the containerised backend.

**Results (seconds):** 0.004823, 0.003002, 0.002785, 0.002888, 0.002397, 0.002902, 0.002848, 0.002400, 0.002728, 0.003068, 0.002940, 0.002721, 0.002803, 0.002327, 0.002390, 0.002654, 0.002781, 0.002555, 0.002708, 0.002325

**Summary:** 20/20 requests completed in ≤ 0.500s (threshold: ≥19/20 required).

**Result: PASS**

## Bug Found & Fixed During Frontend Integration

**Issue:** "View All Sessions" and course filtering failed silently in the browser with a `htmx:invalidPath` console error, despite the backend responding correctly to direct `curl` requests.

**Root cause:** htmx 2.x enforces `selfRequestsOnly` by default, blocking AJAX calls to a different origin than the page itself. Since the frontend (port 8003) and backend (port 5003) are genuinely separate microservices — the architecture the spec requires — every `htmx.ajax()` call to the backend was silently blocked.

**Fix:** Replaced all `htmx.ajax()` calls with plain `fetch()`, matching the pattern already used successfully for Create/Update/Delete/Ask. Removed the now-unused htmx script dependency entirely.

**Evidence:** Post-fix validation run (this log) shows all read/filter/clash-check endpoints passing from both `curl` and the browser UI.

## Role-Based View Validation

| Role | Manage tab | Clashes tab | Browse tab | Ask AI tab |
|---|---|---|---|---|
| Student | Hidden | Hidden | Visible | Visible |
| Lecturer | Hidden | Hidden | Visible (+ staff lookup note) | Visible |
| Admin | Visible | Visible | Visible | Visible |

Verified manually via the role-stamp toggle in the browser; switching roles correctly shows/hides the Manage and Clashes tabs and auto-redirects away from a hidden tab if it was active.
