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
]
