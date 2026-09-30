# Shared Agentic Loop — MCP validation mode

Run: 2026-10-01T00:03:24+10:00

## PLAN

Validate the shared MCP server at http://localhost:8000/mcp.

- 1. List registered tools (tool discovery).
- 2. Call every tool that has validation cases; check it returns a structured result.
- 3. Send invalid inputs and expect rejection (input validation).
- 4. Call an unregistered tool ('drop_all_tables') and expect rejection (tool boundary).
## ACT

Discovering tools and executing validation cases.

- 10 tools registered (listed in 512 ms): get_sessions_by_course, check_room_availability, find_timetable_clashes, get_staff_count, list_staff, get_staff_member, get_employment_summary, refresh_corpus, retrieve_context, answer_question
## OBSERVE

11 passed, 0 failed, 0 tools not exercised.

| Tool | Arguments | Result | Detail |
|---|---|---|---|
| get_sessions_by_course | {"course_code": "ASD101"} | PASS | structured result {"course_code": "ASD101", "session_count": 2, "sessions": [{"session_id": 1, "course_code"… (17 ms) |
| check_room_availability | {"room": "CB01.02.15", "day": "Monday", "start_time": "10:00", "end_time": "11:00"} | PASS | structured result {"room": "CB01.02.15", "day": "Monday", "start_time": "10:00", "end_time": "11:00", "avail… (15 ms) |
| check_room_availability | {"room": "CB01.02.15", "day": "Funday", "start_time": "10:00", "end_time": "11:00"} | PASS | rejected as expected: Error executing tool check_room_availability: day must be one of: Monday, Tuesday, Wednesd (10 ms) |
| check_room_availability | {"room": "CB01.02.15", "day": "Monday", "start_time": "11:00", "end_time": "09:00"} | PASS | rejected as expected: Error executing tool check_room_availability: start_time must be earlier than end_time (9 ms) |
| find_timetable_clashes | {} | PASS | structured result {"clash_count": 0, "clashes": []} (15 ms) |
| get_staff_count | {} | PASS | structured result {"staff_count": 10} (86 ms) |
| list_staff | {} | PASS | structured result {"result": [{"staff_id": 1, "given_name": "Jet", "family_name": "Smith", "department": "Co… (19 ms) |
| get_staff_member | {"staff_id": 1} | PASS | structured result {"staff_id": 1, "given_name": "Jet", "family_name": "Smith", "department": "Computer Scien… (18 ms) |
| get_staff_member | {"staff_id": 0} | PASS | rejected as expected: Error executing tool get_staff_member: staff_id must be a positive integer (8 ms) |
| get_employment_summary | {} | PASS | structured result {"by_department": {"Computer Science": 1, "Arts": 3, "Engineering": 1, "Nursing": 1, "Mark… (15 ms) |
| refresh_corpus | — | SKIP | validated through RAG mode |
| retrieve_context | — | SKIP | validated through RAG mode |
| answer_question | — | SKIP | validated through RAG mode |
| drop_all_tables | {} | PASS | unregistered tool rejected (boundary enforced) |

## ADAPT

- All registered tools validated; no rule-based adaptation needed.
- Local AI suggestion (qwen2.5:0.5b):
```
| Check | Result |
| --- | --- |
| get_sessions_by_course | PASS: structured result {"course_code": "ASD101", "session_count": 2, "sessions": [{"session_id": 1, "course_code": "ASD101"}, {"session_id": 2, "course_code": "ASD101"}]}. |
| check_room_availability | PASS: structured result {"room": "CB01.02.15", "day": "Monday", "start_time": "10:00", "end_time": "11:00", "availability": "available"}. |
| check_room_availability | PASS: rejected as expected: Error executing tool check_room_availability: day must be one of: Monday, Tuesday, Wednesd. (9 ms) |
| check_room_availability | PASS: rejected as expected: Error executing tool check_room_availability: start_time must be earlier than end_time (9 ms). |

Additional Validation Case:
- **get_staff
```

