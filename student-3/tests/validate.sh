#!/bin/bash
# Validation matrix for Timetable & Class Scheduling microservice
# Run against the containerized service: docker compose up must be running first.

BASE="http://127.0.0.1:5003"
PASS=0
FAIL=0

check() {
    local desc="$1"
    local expected_code="$2"
    local actual_code="$3"
    if [ "$actual_code" == "$expected_code" ]; then
        echo "PASS | $desc | expected=$expected_code actual=$actual_code"
        PASS=$((PASS+1))
    else
        echo "FAIL | $desc | expected=$expected_code actual=$actual_code"
        FAIL=$((FAIL+1))
    fi
}

echo "=== Timetable & Class Scheduling — Validation Run ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# ---------- READ ----------
CODE=$(curl -s -o /tmp/r1.txt -w "%{http_code}" "$BASE/timetable")
check "GET /timetable (all sessions)" "200" "$CODE"

CODE=$(curl -s -o /tmp/r2.txt -w "%{http_code}" "$BASE/timetable/1")
check "GET /timetable/1 (valid session)" "200" "$CODE"

CODE=$(curl -s -o /tmp/r3.txt -w "%{http_code}" "$BASE/timetable/999")
check "GET /timetable/999 (not found)" "404" "$CODE"

CODE=$(curl -s -o /tmp/r4.txt -w "%{http_code}" "$BASE/timetable/by-course?course_code=ASD101")
check "GET /timetable/by-course?course_code=ASD101" "200" "$CODE"

CODE=$(curl -s -o /tmp/r5.txt -w "%{http_code}" "$BASE/timetable/by-course?course_code=ZZZ999")
check "GET /timetable/by-course?course_code=ZZZ999 (no match)" "404" "$CODE"

# ---------- CREATE ----------
CODE=$(curl -s -o /tmp/r6.txt -w "%{http_code}" -X POST "$BASE/timetable" \
    -d "course_code=TEST999&session_type=Lecture&day=Monday&start_time=09:00&end_time=11:00&room=CB01.02.15&semester=2026-S2")
check "POST /timetable (create, clashing room/time)" "201" "$CODE"
NEW_ID=$(grep -o '[0-9]\+' /tmp/r6.txt | tail -1)
echo "     Created session ID: $NEW_ID"

CODE=$(curl -s -o /tmp/r7.txt -w "%{http_code}" -X POST "$BASE/timetable" \
    -d "session_type=Lecture&day=Monday")
check "POST /timetable (missing required fields)" "400" "$CODE"

# ---------- CLASH DETECTION ----------
CODE=$(curl -s -o /tmp/r8.txt -w "%{http_code}" "$BASE/timetable/clashes")
check "GET /timetable/clashes (should detect the test clash)" "200" "$CODE"
grep -q "Clash:" /tmp/r8.txt && echo "     Clash correctly detected" || echo "     WARNING: expected a clash, none found"

# ---------- UPDATE ----------
CODE=$(curl -s -o /tmp/r9.txt -w "%{http_code}" -X PUT "$BASE/timetable/$NEW_ID" \
    -d "room=CB09.09.09")
check "PUT /timetable/$NEW_ID (update room, resolve clash)" "200" "$CODE"

CODE=$(curl -s -o /tmp/r10.txt -w "%{http_code}" "$BASE/timetable/clashes")
check "GET /timetable/clashes (should be clear after update)" "200" "$CODE"
grep -q "No clashes detected" /tmp/r10.txt && echo "     Clash correctly resolved" || echo "     WARNING: clash still present after fix"

CODE=$(curl -s -o /tmp/r11.txt -w "%{http_code}" -X PUT "$BASE/timetable/999" \
    -d "room=CB01.01.01")
check "PUT /timetable/999 (update non-existent session)" "404" "$CODE"

# ---------- DELETE ----------
CODE=$(curl -s -o /tmp/r12.txt -w "%{http_code}" -X DELETE "$BASE/timetable/$NEW_ID")
check "DELETE /timetable/$NEW_ID (cleanup test session)" "200" "$CODE"

CODE=$(curl -s -o /tmp/r13.txt -w "%{http_code}" -X DELETE "$BASE/timetable/999")
check "DELETE /timetable/999 (delete non-existent)" "404" "$CODE"

# ---------- FINAL STATE CHECK ----------
CODE=$(curl -s -o /tmp/r14.txt -w "%{http_code}" "$BASE/timetable")
check "GET /timetable (back to 10 clean records)" "200" "$CODE"
COUNT=$(grep -o "<tr>" /tmp/r14.txt | wc -l)
echo "     Session rows in final table: $((COUNT-1)) (excluding header row)"

# ---------- AI AGENT ----------
CODE=$(curl -s -o /tmp/r15.txt -w "%{http_code}" -X POST "$BASE/ask" \
    -d "question=When is my next ASD101 class?")
check "POST /ask (AI agent, valid question)" "200" "$CODE"

CODE=$(curl -s -o /tmp/r16.txt -w "%{http_code}" -X POST "$BASE/ask" -d "question=")
check "POST /ask (empty question)" "400" "$CODE"

# ---------- RELEASE 1: JSON API ----------
CODE=$(curl -s -o /tmp/r17.txt -w "%{http_code}" "$BASE/api/timetable")
check "GET /api/timetable (JSON for MCP server)" "200" "$CODE"

# ---------- RELEASE 1: MCP ----------
CODE=$(curl -s -o /tmp/r18.txt -w "%{http_code}" "$BASE/mcp/tools")
check "GET /mcp/tools (list MCP tools)" "200" "$CODE"
echo "     Tools: $(grep -o '"name": *"[a-z_]*"' /tmp/r18.txt | sed 's/.*"\([a-z_]*\)"$/\1/' | tr '\n' ' ')"

CODE=$(curl -s -o /tmp/r19.txt -w "%{http_code}" -X POST "$BASE/mcp/call" -H "Content-Type: application/json" \
    -d '{"tool":"check_room_availability","arguments":{"room":"CB01.02.15","day":"Monday","start_time":"10:00","end_time":"11:00"}}')
check "MCP check_room_availability (busy slot)" "200" "$CODE"
grep -q '"available": *false' /tmp/r19.txt && echo "     Correctly reported BOOKED (conflicts with session 1)" || echo "     WARNING: expected available=false"

CODE=$(curl -s -o /tmp/r20.txt -w "%{http_code}" -X POST "$BASE/mcp/call" -H "Content-Type: application/json" \
    -d '{"tool":"check_room_availability","arguments":{"room":"CB01.02.15","day":"Monday","start_time":"11:00","end_time":"12:00"}}')
check "MCP check_room_availability (back-to-back slot)" "200" "$CODE"
grep -q '"available": *true' /tmp/r20.txt && echo "     Correctly reported AVAILABLE" || echo "     WARNING: expected available=true"

CODE=$(curl -s -o /tmp/r21.txt -w "%{http_code}" -X POST "$BASE/mcp/call" -H "Content-Type: application/json" \
    -d '{"tool":"get_sessions_by_course","arguments":{"course_code":"ASD101"}}')
check "MCP get_sessions_by_course (ASD101)" "200" "$CODE"
grep -q '"session_count": *2' /tmp/r21.txt && echo "     2 ASD101 sessions returned" || echo "     WARNING: expected 2 sessions"

CODE=$(curl -s -o /tmp/r22.txt -w "%{http_code}" -X POST "$BASE/mcp/call" -H "Content-Type: application/json" \
    -d '{"tool":"find_timetable_clashes","arguments":{}}')
check "MCP find_timetable_clashes" "200" "$CODE"

CODE=$(curl -s -o /tmp/r23.txt -w "%{http_code}" -X POST "$BASE/mcp/call" -H "Content-Type: application/json" \
    -d '{"tool":"check_room_availability","arguments":{"room":"CB01.02.15","day":"Funday","start_time":"10:00","end_time":"11:00"}}')
check "MCP check_room_availability (invalid day rejected)" "400" "$CODE"

CODE=$(curl -s -o /tmp/r24.txt -w "%{http_code}" -X POST "$BASE/mcp/call" -H "Content-Type: application/json" \
    -d '{"tool":"drop_table","arguments":{}}')
check "MCP unknown tool rejected" "400" "$CODE"

# ---------- RELEASE 1: RAG ----------
CODE=$(curl -s -o /tmp/r25.txt -w "%{http_code}" -X POST "$BASE/rag/answer" -H "Content-Type: application/json" \
    -d '{"question":"Do two sessions clash if one ends at 11:00 and the next starts at 11:00 in the same room?"}')
check "RAG grounded answer (policy question)" "200" "$CODE"
echo "     Confidence: $(grep -o '"confidence_category": *"[a-z]*"' /tmp/r25.txt | head -1 | sed 's/.*"\([a-z]*\)"$/\1/')"
echo "     Citations:  $(grep -o '"chunk_id": *"policy-[0-9]*"' /tmp/r25.txt | sed 's/.*"\(policy-[0-9]*\)"$/\1/' | tr '\n' ' ')"

CODE=$(curl -s -o /tmp/r26.txt -w "%{http_code}" -X POST "$BASE/rag/answer" -H "Content-Type: application/json" \
    -d '{"question":"Who won the 2022 football World Cup?"}')
check "RAG off-topic question (should abstain)" "200" "$CODE"
grep -q '"confidence_category": *"low"' /tmp/r26.txt && echo "     Correctly abstained (low confidence, no citations)" || echo "     WARNING: expected abstention — check RAG_MIN_SIMILARITY"

CODE=$(curl -s -o /tmp/r27.txt -w "%{http_code}" -X POST "$BASE/rag/answer" -H "Content-Type: application/json" \
    -d '{"question":""}')
check "RAG empty question" "400" "$CODE"

# ---------- NFR: response time ----------
echo ""
echo "=== NFR check: GET /timetable response time (target <= 500ms) ==="
TOTAL_OK=0
for i in $(seq 1 20); do
    TIME=$(curl -s -o /dev/null -w "%{time_total}" "$BASE/timetable")
    UNDER=$(echo "$TIME <= 0.5" | bc)
    if [ "$UNDER" == "1" ]; then
        TOTAL_OK=$((TOTAL_OK+1))
    fi
    echo "     Request $i: ${TIME}s"
done
echo "     $TOTAL_OK/20 requests under 500ms"

echo ""
echo "=== Summary: $PASS passed, $FAIL failed ==="
