# Student 5 — Assessment & Grades Management

Owner: **Vu Tien Thanh Nguyen**

Self-contained microservice set for the Assessment & Grades feature: create,
search, edit, and delete assessments and grades, plus an AI agent that
answers natural-language questions using the **Plan → Act → Observe → Adapt**
workflow.

## Folder structure

```
student-5/
├── frontend/                        # standalone frontend microservice
│   ├── Dockerfile
│   ├── templates/
│   │   ├── index.html               # Standalone home page (same content as the tab)
│   │   └── tabs/
│   │       ├── normal.html
│   │       ├── ai-mode.html
│   │       ├── mcp.html                 # Release 1 - MCP Tools tab
│   │       └── rag.html                 # Release 1 - RAG Answers tab
│   └── css/
│       ├── styles.css
│       └── features/
│           ├── assessment-grades.css
│           └── mcp-rag.css              # Release 1 tab styles
├── backend/                         # Flask API — CRUD + AI agent
│   ├── app.py
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── routes/            (assessments.py, grades.py, ai_mode.py, mcp_mode.py, rag_mode.py)
│   ├── services/          (database_api.py, llm_client.py, prompt_loader.py, mcp_api.py, rag_api.py)
│   └── views/             (html_formatters.py, mcp_rag_formatters.py)
├── database/                        # Flask REST API over SQLite
│   ├── app.py
│   ├── Dockerfile
│   ├── init_db.py                   # Seeds 10 assessments + 12 grades
│   └── requirements.txt
├── prompts/assessment-grades/       # AI system + task prompts
├── tests/
│   ├── test_assessment_grades_service.py
│   └── test_mcp_rag_routes.py       # Release 1 - offline MCP/RAG route tests
├── ci-workflow/                     # copy into .github/workflows/
│   └── VuTienThanhNguyen.yml
└── docker-compose.snippet.yml

```

## Ports

| Service | Port |
|---|---|
| `assessment-database-service` | 5022 |
| `assessment-service` (backend/API) | 5021 |
| `assessment-frontend-service` (standalone UI) | 8085 → 80 |

## Relationships with other students' microservices

- **Student 1 → Student 5 (`student_id`)**: grades store the exact
  `STU-XXXX` id format Student 1's database-service issues. When a grade is
  created or updated, the backend calls
  `GET {STUDENT_SERVICE_URL}/students/{student_id}` on Student 1's
  database-service to confirm the student exists before saving, and grade
  listings are enriched with the student's real name (fetched from
  `GET {STUDENT_SERVICE_URL}/students`).
- **Student 4 → Student 5 (`course_id`)**: assessments store the same course
  code Student 4 uses (`course_code`, e.g. `ASD101`). Assessment listings are
  enriched with the course's real name by fetching
  `GET {COURSE_SERVICE_URL}/courses` from Student 4's database-service and
  matching on `course_code`.
- Both lookups fail *gracefully* for reads (the id/code is shown on its own if
  the other service is unreachable) but POST/PUT `/grades` returns `503` if
  Student 1's service can't be reached, since that check can't be skipped
  silently.
- `STUDENT_SERVICE_URL` (default `http://student1-database:5002`) and
  `COURSE_SERVICE_URL` (default `http://student4-database:5002`) are the env
  vars controlling this — set by the team's root `docker-compose.yml`.

## Running standalone

```bash
docker compose -f student-5/docker-compose.snippet.yml up -d --build
```
(or merge the snippet into the team's root `docker-compose.yml` as described
in the comments at the top of that file, then run the whole stack from there)

Open **http://localhost:8085** to see the Assessment & Grades UI running on
its own. Note: standalone, the Student 1 / Student 4 lookups above can't
resolve (those services aren't part of the standalone file), so names/course
names won't show and grade creation will return 503 — that's expected, not a
bug; run the full team stack to see the relationships resolve.

## Integrating into the team's unified home page

Already done: `frontend/templates/index.html` and the two tab pages link back
to the shared home page at `http://localhost:8090`, and
`shared/frontend/homepage.html` links out to
`http://localhost:8085` for the "Assessments & grades" card.

## CI

`.github/workflows/student-5.yml` (repo root) builds the database, backend/API
and frontend images, runs them together, smoke-tests every page and endpoint,
runs the Release 0 pytest suite plus the offline MCP/RAG unit tests, and checks
that the MCP and RAG routes answer **503 "disabled"**. MCP and RAG are switched
off in CI with `MCP_ENABLED=false` / `RAG_ENABLED=false` — the integration code
stays in the app. (`ci-workflow/VuTienThanhNguyen.yml` is the old Release 0 copy.)

## Release 1 — MCP and RAG

The feature calls the team's **shared, local (non-Docker)** MCP and RAG servers
through its own backend — the frontend never talks to them directly:

```
MCP:  UI tab "MCP Tools"   -> assessment-service :5021 /mcp/call -> MCP server :8000/mcp (host)
                              -> Student 5 tool -> assessment-database-service :5022
RAG:  UI tab "RAG Answers" -> assessment-service :5021 /rag/ask  -> RAG server :5050 (host), domain "assessment"
                              -> retrieve context -> Ollama grounded answer -> answer + sources + confidence
```

**MCP tools** (`ai-services/mcp-server/student5_tools.py`, all read-only, inputs validated):

| Tool | Input | Structured result |
|---|---|---|
| `list_course_assessments` | `course_id` like `ASD101` | `course_id, assessment_count, total_weight, assessments[]` |
| `get_student_grade_summary` | `student_id` like `STU-1001` | `student_id, found, graded_count, pending_count, average_percent, grades[]` |
| `get_upcoming_assessments` | `from_date` YYYY-MM-DD, `limit` 1-20 | `from_date, limit, total_upcoming, assessments[]` |

The backend only allows these three tools (`services/mcp_api.py` → `ALLOWED_TOOLS`).

**RAG domain `assessment`** (`ai-services/rag-server/student5_rag.py`) indexes live
assessment records, per-course summaries, anonymised per-course grade statistics,
and `corpus/assessment_policy.md`. Individual student marks are *not* indexed
(use the MCP tool for those). Answers carry citations and a `confidence_category`
(high/medium/low). With no relevant context — an off-topic question, an unknown
course code, or a single student's marks — it returns *"Insufficient evidence…"*
with no citations instead of guessing. If Ollama is down or its output names a
course/date not in the evidence, an extractive answer built from the cited
evidence is returned instead (the `generator` field says which).

**Backend routes** (HTML for the UI; add `?format=json` for JSON):

| Method | Path | Notes |
|---|---|---|
| GET | `/mcp/tools` | Student 5 tools listed by the shared server |
| POST | `/mcp/call` | `tool` + its arguments (form or JSON `{"tool","arguments"}`) |
| GET | `/rag/health` | shared RAG server reachable + `assessment` domain hosted |
| POST | `/rag/refresh` | rebuild the `assessment` index |
| POST | `/rag/ask` | `question`, optional `course_id` (used for "this course") |

Status codes: `200` ok, `400` input rejected / tool outside boundary, `503` disabled or server unreachable.

### Run it locally

```bash
# 1. Ollama on the host
ollama pull qwen2.5:0.5b

# 2. Containers (frontend/backend/db) from the repo root
docker compose up --build -d

# 3. Shared servers on the host (two terminals, repo root)
pip install -r ai-services/mcp-server/requirements.txt
cd ai-services/mcp-server && python server.py          # http://localhost:8000/mcp
cd ai-services/rag-server && python rag_http_server.py  # http://localhost:5050
```

Open http://localhost:8085 → **MCP Tools** (e.g. *Course assessments → ASD101*) and
**RAG Answers** (e.g. *"What assessments do I have for this course?"* with ASD101).

### Tests and agentic-loop evidence

```bash
python -m pytest student-5/tests/test_mcp_rag_routes.py -v
cd ai-services/mcp-server && python -m unittest test_student5_tools -v
cd ai-services/rag-server && python -m unittest test_student5_rag -v
python -m agentic_loop.main --mode mcp   # -> docs/release-1/agentic-loop/mcp-validation.md
python -m agentic_loop.main --mode rag   # -> docs/release-1/agentic-loop/rag-validation.md
```

## API reference

**Assessments**
| Method | Path | Notes |
|---|---|---|
| GET | `/assessments` | optional `course_id`, `assessment_type`, `q` query params |
| GET | `/assessments/<id>` | |
| POST | `/assessments` | |
| PUT | `/assessments/<id>` | |
| DELETE | `/assessments/<id>` | |

**Grades**
| Method | Path | Notes |
|---|---|---|
| GET | `/grades` | |
| GET | `/grades/<id>` | |
| POST | `/grades` | validates `student_id` against Student 1 |
| PUT | `/grades/<id>` | validates `student_id` against Student 1 if provided |
| DELETE | `/grades/<id>` | |
| GET | `/grades/student/<student_id>` | e.g. `/grades/student/STU-1001` |
| GET | `/grades/course/<course_id>` | |

**AI agent**
| Method | Path | Notes |
|---|---|---|
| POST | `/ask` | form field `question`; Plan → Act → Observe → Adapt |

## Database schema

**assessments** — `assessment_id` (PK), `course_id`, `assessment_name`,
`assessment_type`, `description`, `due_date`, `max_mark`, `weight`

**grades** — `grade_id` (PK), `assessment_id` (FK), `student_id` (TEXT,
matches Student 1's `STU-XXXX` format), `mark`, `grade`, `feedback`,
`date_recorded`
