# Student 5 — Assessment & Grades Management

Owner: **Vu Tien Thanh Nguyen**

Self-contained microservice set for the Assessment & Grades feature: create,
search, edit, and delete assessments and grades, plus an AI agent that
answers natural-language questions using the **Plan → Act → Observe → Adapt**
workflow.

## Folder structure

```
student-5/
├── frontend/                        # 🆕 NEW — standalone frontend microservice
│   ├── Dockerfile
│   ├── templates/
│   │   ├── index.html               # Standalone home page (same content as the tab)
│   │   └── tabs/
│   │       └── assessment-grades.html   # Same file, for embedding as a tab
│   └── css/
│       ├── styles.css               # Shared design system (tab shell, pills, drawer, etc.)
│       └── features/
│           └── assessment-grades.css    # Feature-only additions, scoped under .ag-app
├── backend/                         # Flask API — CRUD + AI agent
│   ├── app.py
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── routes/            (assessments.py, grades.py, ai_mode.py)
│   ├── services/          (database_api.py, llm_client.py, prompt_loader.py)
│   └── views/              html_formatters.py
├── database/                        # Flask REST API over SQLite
│   ├── app.py
│   ├── Dockerfile
│   ├── init_db.py                   # Seeds 10 assessments + 12 grades
│   └── requirements.txt
├── prompts/assessment-grades/       # AI system + task prompts
│   ├── system_prompt.txt
│   └── task_prompt.txt
├── tests/
│   └── test_assessment_grades_service.py   # 9 pytest smoke tests
├── ci-workflow/                     # 🆕 NEW — copy into .github/workflows/
│   └── VuTienThanhNguyen.yml
└── docker-compose.snippet.yml       # 🆕 UPDATED — now includes the frontend service
```

**What's new in this pass:** the `frontend/` folder (previously my UI only existed
as a file dropped into the team's shared `frontend-service/`, with no
self-contained container of my own) and `ci-workflow/` (no CI workflow existed
for this feature at all). `docker-compose.snippet.yml` is updated to add the
new frontend container alongside the two that were already there.

## Ports

| Service | Port |
|---|---|
| `assessment-database-service` | 5022 |
| `assessment-service` (backend/API) | 5021 |
| `assessment-frontend-service` (standalone UI) | 8085 → 80 |

These don't collide with any other student's services (student1: 5001/5002,
Student2: 5011/5012, Student4: 5031/5032).

## Running standalone

```bash
docker compose -f student-5/docker-compose.snippet.yml up -d --build
```
(or merge the snippet into the team's root `docker-compose.yml` as described
in the comments at the top of that file, then run the whole stack from there)

Open **http://localhost:8085** to see the Assessment & Grades UI running on
its own, independent of the rest of the team's app.

## Integrating into the team's unified home page

The exact same file, `frontend/templates/tabs/assessment-grades.html`, also
works as an iframe tab inside the team's shared `frontend-service`. To wire
it in:
1. Copy `frontend/templates/tabs/assessment-grades.html` → team's
   `frontend-service/templates/tabs/assessment-grades.html`
2. Copy `frontend/css/features/assessment-grades.css` → team's
   `frontend-service/css/features/assessment-grades.css`
3. Add a tab button + iframe entry in the team's `frontend-service/templates/index.html`
   pointing at `tabs/assessment-grades.html`
4. Make sure the team's shared `frontend-service/css/styles.css` includes the
   same `.tab-shell` / `.pill` / `.drawer` / etc. rules as
   `frontend/css/styles.css` here — copy it over if unsure, since it's a
   superset that's safe to use as the whole app's shared stylesheet.

## CI

`ci-workflow/VuTienThanhNguyen.yml` builds both Docker images, runs them
together on a Docker network, smoke-tests the endpoints, then runs the full
pytest suite. GitHub Actions only picks up workflows from `.github/workflows/`
at the repo root, so copy this file there (it can't run from inside
`student-5/`).

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
| POST | `/grades` | |
| PUT | `/grades/<id>` | |
| DELETE | `/grades/<id>` | |
| GET | `/grades/student/<student_id>` | |
| GET | `/grades/course/<course_id>` | |

**AI agent**
| Method | Path | Notes |
|---|---|---|
| POST | `/ask` | form field `question`; Plan → Act → Observe → Adapt |

## Database schema

**assessments** — `assessment_id` (PK), `course_id`, `assessment_name`,
`assessment_type`, `description`, `due_date`, `max_mark`, `weight`

**grades** — `grade_id` (PK), `assessment_id` (FK), `student_id`, `mark`,
`grade`, `feedback`, `date_recorded`
