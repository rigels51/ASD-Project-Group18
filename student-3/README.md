# Student 3 — Timetable & Class Scheduling Microservice

Owner: Lazizbek Ismoilov
Port: 5003

## Structure
- `frontend/` — HTMX pages for this feature only (calls this service's own backend)
- `backend/` — Flask REST API + AI-mode agent (owns the timetable data)
- `database/` — SQLite schema + seed script (only backend/ reads/writes this)
- `tests/` — endpoint validation scripts
- `docker-compose.yml` — standalone compose file to run and test this service in isolation

## Boundary rule
This service never imports another student's code or opens another student's
database file directly. Cross-feature data (e.g. course_code from Course
Catalogue, staff_id from Staff Management) is only ever fetched via that
service's own REST API, once integration begins.

## Status
- [x] Step 1: Folder structure
- [x] Step 2: Database layer
- [x] Step 3: Backend/API service
- [x] Step 4: Frontend microservice
- [x] Step 5: Standalone containerisation
- [x] Step 6: Isolated validation
- [ ] Step 7: Integration into shared repo