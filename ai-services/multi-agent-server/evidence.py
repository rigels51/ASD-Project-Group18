"""Evidence sources for the Worker agent: one domain per student feature.

The server runs on the host (not in Docker), so it reads each feature's data through
that feature's published REST API on localhost. It never opens another student's
SQLite file directly (service-boundary rule from Release 0/1).

To add or change a domain, edit DOMAINS only.
"""

import os
import re
from typing import Any

import requests

TIMEOUT = float(os.getenv("EVIDENCE_TIMEOUT_SECONDS", "8"))
MAX_RECORDS = int(os.getenv("EVIDENCE_MAX_RECORDS", "25"))

COURSE_CODE = re.compile(r"\b[A-Z]{2,4}\d{3}\b")
STUDENT_ID = re.compile(r"\bSTU-?\d{3,4}\b", re.IGNORECASE)


def _url(env: str, default: str) -> str:
    return os.getenv(env, default).rstrip("/")


# domain -> owner, description, keywords (for auto-routing), sources (label, url, fields kept)
DOMAINS: dict[str, dict[str, Any]] = {
    "students": {
        "owner": "Student 1 - Student Records",
        "keywords": ["student record", "gpa", "enrolled", "on leave", "graduated", "year level"],
        "sources": [
            ("students", lambda: f"{_url('STUDENT1_DATABASE_URL', 'http://localhost:5002')}/students",
             ("student_id", "name", "course", "year_level", "gpa", "status")),
        ],
    },
    "staff": {
        "owner": "Student 2 - Staff Registry",
        "keywords": ["staff", "employee", "department", "full-time", "part-time", "lecturer"],
        "sources": [
            # email deliberately excluded (same privacy rule as the MCP staff tools)
            ("staff", lambda: f"{_url('STAFF_DATABASE_URL', 'http://localhost:5012')}/staff",
             ("staff_id", "given_name", "family_name", "department", "employment_type")),
        ],
    },
    "timetable": {
        "owner": "Student 3 - Timetable & Class Scheduling",
        "keywords": ["timetable", "session", "room", "clash", "lecture", "tutorial", "lab", "schedule"],
        "sources": [
            ("sessions", lambda: _url("TIMETABLE_API_URL", "http://localhost:5003/api/timetable"),
             ("session_id", "course_code", "session_type", "day", "start_time", "end_time", "room", "semester")),
        ],
    },
    "course": {
        "owner": "Student 4 - Course & Enrollment",
        "keywords": ["course", "capacity", "seat", "credit", "enrolment", "enrollment"],
        "sources": [
            ("courses", lambda: f"{_url('STUDENT4_DATABASE_URL', 'http://localhost:5032')}/courses",
             ("course_id", "course_code", "course_name", "credits", "capacity")),
            ("enrolments", lambda: f"{_url('STUDENT4_DATABASE_URL', 'http://localhost:5032')}/enrolments",
             ("enrolment_id", "student_id", "course_code", "status")),
        ],
    },
    "assessment": {
        "owner": "Student 5 - Assessment & Grades",
        "keywords": ["assessment", "grade", "mark", "due", "exam", "assignment", "weight", "feedback"],
        "sources": [
            ("assessments", lambda: f"{_url('ASSESSMENT_DATABASE_URL', 'http://localhost:5022')}/assessments",
             ("assessment_id", "course_id", "assessment_name", "assessment_type", "due_date", "max_mark", "weight")),
            ("grades", lambda: f"{_url('ASSESSMENT_DATABASE_URL', 'http://localhost:5022')}/grades",
             ("grade_id", "assessment_name", "course_id", "student_id", "mark", "max_mark", "grade")),
        ],
    },
}


def detect_domain(user_request: str) -> str | None:
    text = user_request.lower()
    scores = {name: sum(1 for kw in cfg["keywords"] if kw in text) for name, cfg in DOMAINS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def extract_filters(user_request: str) -> dict[str, list[str]]:
    return {
        "course_codes": sorted({c for c in COURSE_CODE.findall(user_request.upper())}),
        "student_ids": sorted({"STU-" + re.sub(r"\D", "", s) for s in STUDENT_ID.findall(user_request)}),
    }


def _matches(record: dict, filters: dict[str, list[str]]) -> bool:
    values = " ".join(str(v) for v in record.values()).upper()
    for key in ("course_codes", "student_ids"):
        wanted = filters.get(key) or []
        if wanted and not any(w in values for w in wanted):
            return False
    return True


def fetch_evidence(domain: str, filters: dict[str, list[str]]) -> dict[str, Any]:
    """Return {"records": [...], "sources": [...], "errors": [...]} for one domain."""
    cfg = DOMAINS[domain]
    records, sources, errors = [], [], []
    for label, url_fn, fields in cfg["sources"]:
        url = url_fn()
        try:
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            rows = response.json()
            if not isinstance(rows, list):
                raise ValueError("expected a JSON list")
        except requests.ConnectionError:
            errors.append(f"{label}: service unreachable at {url}")
            continue
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{label}: {type(exc).__name__} from {url}: {str(exc)[:120]}")
            continue
        kept = [{"source": label, **{f: r.get(f) for f in fields if f in r}} for r in rows if isinstance(r, dict)]
        filtered = [r for r in kept if _matches(r, filters)]
        # If a filter removes everything, report that honestly rather than falling back to all rows.
        records.extend(filtered[:MAX_RECORDS])
        sources.append({"label": label, "url": url, "total": len(kept), "matched": len(filtered)})
    return {"records": records, "sources": sources, "errors": errors}
