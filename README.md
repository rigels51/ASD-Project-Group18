# ASD Project Group 18

University Management System — ASD 2026 Group Project

## Team Members

| No. | Student Name | Student ID | UTS Email |
| --- | --- | --- | --- |
| 1 | Rigel Rivamonte | 25876487 | rigel.rivamonte@student.uts.edu.au |
| 2 | Jeriko Arceo | 24806008 | Jeriko.R.Arceo@student.uts.edu.au |
| 3 | Lazizbek Ismoilov | 14567426 | Lazizbek.Ismoilov@student.uts.edu.au |
| 4 | Yi Zhang | 25402140 | Yi.Zhang-41@student.uts.edu.au |
| 5 | Vu Tien Thanh Nguyen | 14673154 | Vu.T.Nguyen-5@student.uts.edu.au |

## Project Structure

```text
ASD-Project-Group18/
├── .github/
│   └── workflows/
├── shared/
├── student-1/
├── student-2/
├── student-3/
├── student-4/
├── student-5/
├── agentic_loop/
├── docker-compose.yml
└── README.md
```

## How to Run the Project

Make sure Docker Desktop and Ollama are running.

From the project root folder, run:

`docker compose up --build -d`

Check that the containers are running:

`docker ps`

Open the shared homepage:

`http://localhost:8090`

To stop the project:

`docker compose down`

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
