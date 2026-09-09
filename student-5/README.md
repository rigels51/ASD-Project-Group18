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
│   │       └── ai-mode.html
│   └── css/
│       ├── styles.css
│       └── features/
│           └── assessment-grades.css
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
├── tests/
│   └── test_assessment_grades_service.py
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
