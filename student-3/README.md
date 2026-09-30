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
- `backend/` — Flask REST API + AI-mode agent (owns the timetable data); `mcp_client.py` / `rag_client.py` call the shared Release 1 AI services
- Timetable's parts of the shared AI services (outside this folder): `ai-services/mcp-server/timetable_tools.py`, `ai-services/rag-server/timetable_rag.py`, `ai-services/rag-server/corpus/timetable_policy.md`
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
# terminal 1: shared MCP server      cd ai-services/mcp-server && python server.py
# terminal 2: shared RAG server      cd ai-services/rag-server && python rag_http_server.py
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
| GET | `/api/timetable` | All sessions as JSON (read by the MCP server) |
| GET | `/mcp/tools` | List the Timetable MCP tools |
| POST | `/mcp/call` | Call an MCP tool: `{"tool": "...", "arguments": {...}}` |
| POST | `/rag/answer` | Grounded policy answer: `{"question": "..."}` |

## Release 1 — shared MCP & RAG (local only, not containerised)

```
frontend :8003 → backend :5003 (Docker) ─┬→ shared MCP server  localhost:8000/mcp → backend /api/timetable
                                         └→ shared RAG server  localhost:5050  (domain "timetable")
                                              → Ollama (nomic-embed-text + qwen2.5:0.5b)
```

The MCP and RAG servers run on the host with `python`, like Ollama, and are not
Docker Compose services. The backend container reaches them through
`host.docker.internal`, configured in `docker-compose.yml`.

**Timetable MCP tools** (`ai-services/mcp-server/timetable_tools.py`, registered on the shared server):

| Tool | Arguments | Returns |
|---|---|---|
| `check_room_availability` | `room, day, start_time, end_time` (HH:MM) | `available` + conflicting sessions |
| `get_sessions_by_course` | `course_code` | sessions for that course |
| `find_timetable_clashes` | — | every same-room overlapping pair |

Tool boundary: all three are read-only, validate their inputs, and read data only through the
backend API. The backend only allows these three tool names (`ALLOWED_TOOLS`), so the
Timetable UI cannot call another feature's tools.

**Timetable RAG domain** (`ai-services/rag-server/timetable_rag.py`): the Room Booking & Scheduling Policy is split into 12 sections, embedded with `nomic-embed-text`, and ranked by cosine similarity. Sections scoring at least `RAG_MIN_SIMILARITY` (default 0.55) are passed to `qwen2.5:0.5b` as the only evidence. Confidence is `high` (top ≥ `RAG_HIGH_SIMILARITY`, default 0.70), `medium`, or `low`; on `low` the server abstains and returns no citations. Every response includes its Plan → Act → Observe → Adapt trace.

**Prerequisite:** `ollama pull nomic-embed-text` (plus `qwen2.5:0.5b` from Release 0).

**Feature flags:** `MCP_ENABLED` / `RAG_ENABLED` (default `true`). CI sets both to `false`; the routes then return `503 {"status": "disabled"}`.

## Validation
Run `bash tests/validate.sh` against the running backend (containerised or
local). Release 0 run: 16/16 checks passed, NFR met (~2.7ms avg response time
against a 500ms target). Release 1 adds 11 MCP/RAG checks. Full results in `tests/evidence_log.md`.

Offline unit tests (no Ollama or servers needed):
```bash
(cd backend && python init_db.py && python -m unittest discover -s tests -v)
(cd ../ai-services/mcp-server && python -m unittest test_timetable_tools -v)
(cd ../ai-services/rag-server && python -m unittest test_timetable_rag -v)
```

## CI/CD
`.github/workflows/student-3.yml` (repo root) runs automatically on push/PR to
`student-3/**`: installs dependencies, seeds and verifies the database, starts
the app, validates core endpoints, and builds both Docker images. Release 1
adds the backend and Timetable MCP/RAG unit tests and checks that MCP and RAG
report disabled when flagged off.

## Status
- [x] Step 1: Folder structure
- [x] Step 2: Database layer
- [x] Step 3: Backend/API service
- [x] Step 4: Frontend microservice
- [x] Step 5: Standalone containerisation
- [x] Step 6: Isolated validation
- [x] Step 7: Integration into shared repo + CI/CD
- [x] Release 1: 3 Timetable tools on the shared MCP server, wired frontend → backend → MCP
- [x] Release 1: Timetable domain on the shared RAG server (policy corpus, citations, confidence, abstention)
- [x] Release 1: Shared agentic loop MCP and RAG validation modes (`agentic_loop/`)
- [x] Release 1: CI updated with MCP/RAG flagged off