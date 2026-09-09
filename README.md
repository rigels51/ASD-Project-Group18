# ASD Project Group 18

University Management System — ASD 2026 Group Project

## Project Overview

This project is a University Management System developed using a microservice architecture.

The system includes five main features:

- Student Records Management
- Staff Management
- Timetable & Class Scheduling
- Course & Enrollment Management
- Assessment & Grades

Each feature is developed as an independent microservice with its own frontend, backend/API, and database components where required.

The project also uses Docker, Docker Compose, Ollama AI, GitHub Actions, REST APIs, and Agentic AI workflows.

## Team Members

| No. | Student Name | Student ID | UTS Email |
| --- | --- | --- | --- |
| 1 | Rigel Rivamonte | 25876487 | rigel.rivamonte@student.uts.edu.au |
| 2 | Jeriko Arceo | 24806008 | Jeriko.R.Arceo@student.uts.edu.au |
| 3 | Lazizbek Ismoilov | 14567426 | Lazizbek.Ismoilov@student.uts.edu.au |
| 4 | Yi Zhang | 25402140 | Yi.Zhang-41@student.uts.edu.au |
| 5 | Vu Tien Thanh Nguyen | 14673154 | Vu.T.Nguyen-5@student.uts.edu.au |
## Services

### Student 3 — Timetable & Class Scheduling
Owner: Lazizbek Ismoilov

Manages class session scheduling: when and where each course runs, with automatic clash detection and a local AI agent for natural-language scheduling queries.

**Stack:** Flask, SQLite, Docker, Ollama (qwen2.5:0.5b)
**Ports:** backend `5003`, frontend `8003`

**Run standalone:**
```bash
cd student-3
docker compose up --build
```
Then open http://127.0.0.1:8003

**Run as part of the shared app:**
```bash
docker compose up --build timetable-backend timetable-frontend
```
(from the repo root, alongside the other services)

**Endpoints:**
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

**Validation:** `student-3/tests/validate.sh` — 16/16 checks passing, see `student-3/tests/evidence_log.md` for the full run.

**CI/CD:** `.github/workflows/student-3.yml` — runs automatically on push/PR to `student-3/**`, validates endpoints and builds both Docker images.
