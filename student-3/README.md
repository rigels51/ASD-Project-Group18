# Student 3 — Timetable & Class Scheduling Microservice

Owner: Lazizbek Ismoilov
Feature: Timetable & Class Scheduling
Ports: backend `5003`, frontend `8003`

## What this does
Manages when and where each course/subject session runs. Students and lecturers
can browse and filter the timetable; admins can create, update, and delete
sessions; the system automatically detects room/time clashes; and a local AI
agent answers natural-language scheduling questions grounded in the real
timetable data.

## Structure
- `frontend/` — HTML/CSS/JS UI with role-based views (Student/Lecturer/Admin) and tab navigation (calls this service's own backend only)
- `backend/` — Flask REST API + AI-mode agent (owns the timetable data)
- `database/` — SQLite schema + seed script (source of truth; backend copies it in at build time)
- `tests/` — `validate.sh` (endpoint validation matrix) + `evidence_log.md` (test run results)
- `docker-compose.yml` — standalone compose file to run and test this service in isolation, independent of the rest of the team repo

## Boundary rule
This service never imports another student's code or opens another student's
database file directly. Cross-feature data (e.g. course_code from Course
Catalogue, staff_id from Staff Management) is only ever fetched via that
service's own REST API, once integration begins.

## Run it

**Standalone (isolated from the rest of the team's app):**
```bash
docker compose up --build
```
Open http://127.0.0.1:8003

**As part of the shared team app** (from the repo root):
```bash
docker compose up --build timetable-backend timetable-frontend
```

## Roles
| Role | Can do |
|---|---|
| Student | Browse/filter the timetable, ask the AI agent |
| Lecturer | Same as Student, plus a "my sessions" lookup (pending Staff Management integration) |
| Admin | Full CRUD, clash detection |

## Endpoints
| Method | Path | Description |
|---|---|---|
| GET | `/timetable` | List all sessions |
| GET | `/timetable/<id>` | Get one session |
| GET | `/timetable/by-course?course_code=` | Filter by course |
| POST | `/timetable` | Create a session |
| PUT | `/timetable/<id>` | Update a session |
| DELETE | `/timetable/<id>` | Delete a session |
| GET | `/timetable/clashes` | Detect scheduling clashes |
| POST | `/ask` | AI agent (natural-language scheduling questions) |

## Validation
Run `bash tests/validate.sh` against the running backend (containerised or
local). Latest run: 16/16 checks passed, NFR met (~2.7ms avg response time
against a 500ms target). Full results in `tests/evidence_log.md`.

## CI/CD
`.github/workflows/student-3.yml` (repo root) runs automatically on push/PR to
`student-3/**`: installs dependencies, seeds and verifies the database, starts
the app, validates core endpoints, and builds both Docker images.

## Status
- [x] Step 1: Folder structure
- [x] Step 2: Database layer
- [x] Step 3: Backend/API service
- [x] Step 4: Frontend microservice
- [x] Step 5: Standalone containerisation
- [x] Step 6: Isolated validation
- [x] Step 7: Integration into shared repo + CI/CD