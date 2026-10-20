"""Configuration for the shared agentic loop's Release 1 validation modes.

Each student adds their own MCP tool cases and RAG domain cases here.
A tool the MCP server lists but that has no case below is reported as
"listed, not exercised" so gaps are visible in the loop output.
"""

import os


MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
RAG_SERVER_URL = os.getenv("RAG_SERVER_URL", "http://localhost:5050").rstrip("/")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
OLLAMA_REVIEW_MODEL = os.getenv("OLLAMA_REVIEW_MODEL", "llama3.1:8b")

# ---- Release 2: shared Multi-Agent server ----
MULTI_AGENT_SERVER_URL = os.getenv("MULTI_AGENT_SERVER_URL", "http://localhost:5004").rstrip("/")

# A tool name no feature registers: calling it must be rejected (tool boundary).
UNREGISTERED_TOOL = "drop_all_tables"

# expect: "success" -> tool returns a structured result containing every key in expect_keys
#         "error"   -> tool rejects the request (input validation / boundary)
MCP_TOOL_CASES = {
    # ---- Student 2: Staff Management ----
    "get_staff_count": [
        {"arguments": {}, "expect": "success", "expect_keys": ["staff_count"]},
    ],
    "list_staff": [
        {"arguments": {}, "expect": "success", "expect_keys": []},
    ],
    "get_staff_member": [
        {"arguments": {"staff_id": 1}, "expect": "success", "expect_keys": []},
        {"arguments": {"staff_id": 0}, "expect": "error"},
    ],
    "get_employment_summary": [
        {"arguments": {}, "expect": "success", "expect_keys": ["by_department", "by_employment_type"]},
    ],

    # ---- Student 3: Timetable & Class Scheduling ----
    "check_room_availability": [
        {"arguments": {"room": "CB01.02.15", "day": "Monday", "start_time": "10:00", "end_time": "11:00"},
         "expect": "success", "expect_keys": ["available", "conflicts"]},
        {"arguments": {"room": "CB01.02.15", "day": "Funday", "start_time": "10:00", "end_time": "11:00"},
         "expect": "error"},
        {"arguments": {"room": "CB01.02.15", "day": "Monday", "start_time": "11:00", "end_time": "09:00"},
         "expect": "error"},
    ],
    "get_sessions_by_course": [
        {"arguments": {"course_code": "ASD101"}, "expect": "success", "expect_keys": ["session_count", "sessions"]},
    ],
    "find_timetable_clashes": [
        {"arguments": {}, "expect": "success", "expect_keys": ["clash_count", "clashes"]},
    ],
    # ---- Student 5: Assessment & Grades Management ----
    "list_course_assessments": [
        {"arguments": {"course_id": "ASD101"}, "expect": "success",
         "expect_keys": ["course_id", "assessment_count", "total_weight", "assessments"]},
        {"arguments": {"course_id": "DROP TABLE"}, "expect": "error"},
    ],
    "get_student_grade_summary": [
        {"arguments": {"student_id": "STU-1001"}, "expect": "success",
         "expect_keys": ["student_id", "found", "graded_count", "pending_count", "average_percent", "grades"]},
        {"arguments": {"student_id": "12345"}, "expect": "error"},
    ],
    "get_upcoming_assessments": [
        {"arguments": {"from_date": "2026-09-01", "limit": 3}, "expect": "success",
         "expect_keys": ["from_date", "total_upcoming", "assessments"]},
        {"arguments": {"from_date": "2026-09-01", "limit": 99}, "expect": "error"},
        {"arguments": {"from_date": "01/09/2026", "limit": 3}, "expect": "error"},
    ],
}

# Tools that call Ollama or rebuild indexes are listed but not exercised by the loop
# (they are validated through RAG mode instead).
MCP_SKIP_TOOLS = {"refresh_corpus", "retrieve_context", "answer_question"}

# expect: "grounded" -> success, >=1 citation, confidence high/medium
#         "abstain"  -> success, no citations, confidence low
RAG_CASES = [
    # ---- Student 2: Staff Management ----
    {"domain": "staff", "question": "Which staff members work in the Arts department?", "expect": "grounded"},
    {"domain": "staff", "question": "What is the boiling point of water on Mars?", "expect": "abstain"},

    # ---- Student 3: Timetable & Class Scheduling ----
    {"domain": "timetable",
     "question": "Do two sessions clash if one ends at 11:00 and the next starts at 11:00 in the same room?",
     "expect": "grounded"},
    {"domain": "timetable", "question": "Who won the 2022 football World Cup?", "expect": "abstain"},
    # ---- Student 5: Assessment & Grades Management ----
    {"domain": "assessment", "question": "What assessments do I have for ASD101?", "expect": "grounded"},
    {"domain": "assessment", "question": "What is the penalty for late submission?", "expect": "grounded"},
    {"domain": "assessment", "question": "What is the boiling point of water on Mars?", "expect": "abstain"},
    {"domain": "assessment", "question": "What assessments are in XYZ999?", "expect": "abstain"},
]


# Release 2 - one Planner -> Worker -> Reviewer case per feature domain.
# expect: "evidence" -> worker must retrieve >= 1 record and reviewer risk must not be "high"
#         "no_evidence" -> worker retrieves nothing and reviewer must flag risk "high"
MULTI_AGENT_CASES = [
    {"domain": "students", "request": "Summarise the students who are currently On Leave.", "expect": "evidence"},
    {"domain": "staff", "request": "Summarise the staff in the Arts department.", "expect": "evidence"},
    {"domain": "timetable", "request": "Summarise the timetable sessions for ASD101.", "expect": "evidence"},
    {"domain": "course", "request": "Summarise course ASD101 and its enrolments.", "expect": "evidence"},
    {"domain": "assessment", "request": "Summarise the assessments and weights for ASD101.", "expect": "evidence"},
    {"domain": "assessment", "request": "List the assessments for XYZ999.", "expect": "no_evidence"},
]


# Release 2 - Testing Review: where each student's evidence lives and which workflow is theirs.
# Evidence is written by: python3 scripts/capture_test_evidence.py precommit|ci --student <n>
TESTING_EVIDENCE_DIR = "docs/release-2/testing"
TESTING_STUDENTS = {
    1: {"name": "Rigel Rivamonte", "workflow": "RigelRivamonte.yml"},
    2: {"name": "Jeriko Arceo", "workflow": "JerikoArceo.yml"},
    3: {"name": "Lazizbek Ismoilov", "workflow": "student-3.yml"},
    4: {"name": "Yi Zhang", "workflow": "YiZhang.yml"},
    5: {"name": "Vu Tien Thanh Nguyen", "workflow": "student-5.yml"},
}
REQUIRED_PRECOMMIT_HOOKS = ("ruff-security", "detect-secrets", "pip-audit")
MIN_ENDPOINTS_PER_STUDENT = 2
