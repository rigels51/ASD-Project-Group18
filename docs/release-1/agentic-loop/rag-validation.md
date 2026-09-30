# Shared Agentic Loop — RAG validation mode

Run: 2026-09-30T23:57:56+10:00

## PLAN

Validate the shared RAG server at http://localhost:5050.

- 1. Health check and list the knowledge domains the server hosts.
- 2. For each domain, ask an in-scope question: expect a grounded answer with citations and a high/medium confidence category.
- 3. For each domain, ask an out-of-scope question: expect an insufficient-context response (no citations, low confidence).
- Domains under test: staff, timetable
## ACT

Checking health and sending grounded / out-of-scope questions.

- Server healthy; hosted domains: staff, timetable
## OBSERVE

4 passed, 0 failed.

| Domain | Question | Expect | Result | Detail |
|---|---|---|---|---|
| staff | Which staff members work in the Arts department? | grounded | PASS | grounded answer, confidence high, cites staff-2, staff-9, staff-8 (11116 ms) |
| staff | What is the boiling point of water on Mars? | abstain | PASS | insufficient-context response returned (no citations, confidence low) (74 ms) |
| timetable | Do two sessions clash if one ends at 11:00 and the next starts at 11:00 in the same room? | grounded | PASS | grounded answer, confidence high, cites policy-4, policy-5, policy-2, policy-3, policy-10 (2964 ms) |
| timetable | Who won the 2022 football World Cup? | abstain | PASS | insufficient-context response returned (no citations, confidence low) (87 ms) |

- [staff] Q: Which staff members work in the Arts department?
```
A: [staff-2] [staff-9] [staff-8]
confidence: high | citations: staff-2 (student2-database:/staff/2), staff-9 (student2-database:/staff/9), staff-8 (student2-database:/staff/8)
```

- [staff] Q: What is the boiling point of water on Mars?
```
A: Insufficient evidence in the staff registry to answer this question.
confidence: low | citations: none
```

- [timetable] Q: Do two sessions clash if one ends at 11:00 and the next starts at 11:00 in the same room?
```
A: To answer this question about a university timetable policy, we need to consider two sessions that clash when one ends at 11:0 AM and the next starts at 11:00 AM in the same room.

[policy-4] Room clash rule states that two sessions clash if they are booked in the same room on the same day, overlapping times. Since both sessions end at 11:00 AM in the same room, they do not conflict with each other and can be scheduled together without any issues related to room clashes.

[Policy-5] Clash resolution priority ensures that when a clash is detected, the Lecture keeps the room and the Tutorial or Lab is moved. If both sessions are of the same type (Lecture), the session created most recently is moved. This rule allows for flexibility in scheduling but may not always resolve conflicts as it does not consider overlapping times.

[Policy-3] Session types and standard durations specify that a Lecture runs for 1 to 3 hours, a Tutorial runs for exactly 1 hour, and a Lab runs for 2
confidence: high | citations: policy-4 (ai-services/rag-server/corpus/timetable_policy.md#section-4), policy-5 (ai-services/rag-server/corpus/timetable_policy.md#section-5), policy-2 (ai-services/rag-server/corpus/timetable_policy.md#section-2), policy-3 (ai-services/rag-server/corpus/timetable_policy.md#section-3), policy-10 (ai-services/rag-server/corpus/timetable_policy.md#section-10)
```

- [timetable] Q: Who won the 2022 football World Cup?
```
A: Insufficient evidence in the scheduling policy to answer this question.
confidence: low | citations: none
```

## ADAPT

- All domains returned grounded answers and abstained correctly; no rule-based adaptation needed.
- Local AI suggestion (qwen2.5:0.5b):
```
| Check | Cause | Fix |
| --- | --- | --- |
| staff | Staff members working in the Arts department | Verify if the staff list includes all relevant staff members from the Arts department. |
| timetable | Two sessions clash if one ends at 11:00 and the next starts at 11:00 in the same room | Ensure that the time slots for two events are distinct to avoid conflicts. |
```

