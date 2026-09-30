# Room Booking & Scheduling Policy — Timetable & Class Scheduling

This is the knowledge source the Timetable RAG server retrieves from. Each `##` section is indexed as one chunk and cited by its section number (for example `policy-4`).

## 1. Purpose and scope
This policy sets the rules the Timetable & Class Scheduling service follows when sessions are created, changed, or deleted. It applies to every lecture, tutorial, and lab in the University Management System timetable. The timetable service is the single owner of session data; other features read it only through the timetable API.

## 2. Teaching days and hours
Sessions may be scheduled Monday to Friday between 08:00 and 21:00. Saturday and Sunday sessions are not permitted unless the Head of School approves them in writing, and they must be recorded with a note to the timetable administrator. No session may start before 08:00 or finish after 21:00.

## 3. Session types and standard durations
The timetable recognises three session types. A Lecture runs for 1 to 3 hours. A Tutorial runs for exactly 1 hour. A Lab runs for 2 hours. Any other duration must be approved by the course coordinator before the session is created.

## 4. Room clash rule
Two sessions clash when they are booked in the same room, on the same day, at overlapping times. Sessions that are back-to-back do not clash: a session ending at 11:00 and another starting at 11:00 in the same room is allowed. The clash check compares every pair of sessions and reports each clash with both session IDs, the room, the day, and both time ranges.

## 5. Clash resolution priority
When a clash is detected, the Lecture keeps the room and the Tutorial or Lab is moved. If both sessions are the same type, the session created most recently is moved. The timetable administrator must re-run the clash check after every change until no clashes are reported.

## 6. Time format
All times use 24-hour HH:MM format, for example 09:00 or 14:30. The start time must be earlier than the end time. Times such as 9am or 2:30pm are rejected by the service.

## 7. Room codes
Room codes follow the pattern building.level.room, for example CB01.02.15 means building CB01, level 02, room 15. A session must name exactly one room. Lab sessions must be booked in rooms designated as computer labs, and the room capacity must be at least the expected enrolment for the session.

## 8. Semester codes
Every session belongs to one semester, written as year followed by S1 or S2, for example 2026-S1 or 2026-S2. Semester 2026-S2 teaching runs for 12 weeks. Sessions are not copied automatically between semesters; each semester's timetable is created separately.

## 9. Who can change the timetable
Students and lecturers can view and filter the timetable. Only users in the Admin role can create, update, or delete sessions. Lecturers who need a change must submit the request to a timetable administrator.

## 10. Notice period for changes and cancellations
Changes to the day, time, or room of an existing session require at least 5 business days' notice to enrolled students, except for emergencies such as room unavailability. A cancelled session is deleted from the timetable and students are notified through the course announcement channel.

## 11. Staff assignment
Each session may record the staff ID of the teaching staff member. The staff ID is optional when a session is first created and is filled in once the Staff Management feature confirms the assignment. A staff member must not be assigned to two sessions at overlapping times.

## 12. Accessibility requests
Students with an approved accessibility plan may request that a session be moved to an accessible room. Accessibility requests take priority over the standard clash resolution order in section 5, and the administrator must confirm the new room is free using the room availability check before moving the session.
