import unittest

from timetable_tools import room_availability, sessions_by_course, timetable_clashes


SESSIONS = [
    {"session_id": 1, "course_code": "ASD101", "session_type": "Lecture", "day": "Monday",
     "start_time": "09:00", "end_time": "11:00", "room": "CB01.02.15", "semester": "2026-S2", "staff_id": None},
    {"session_id": 2, "course_code": "ASD101", "session_type": "Tutorial", "day": "Monday",
     "start_time": "11:00", "end_time": "12:00", "room": "CB01.02.16", "semester": "2026-S2", "staff_id": None},
    {"session_id": 3, "course_code": "WEB201", "session_type": "Lecture", "day": "Monday",
     "start_time": "10:00", "end_time": "12:00", "room": "CB01.02.15", "semester": "2026-S2", "staff_id": None},
]


class TimetableToolTests(unittest.TestCase):
    def test_sessions_by_course_is_case_insensitive(self):
        result = sessions_by_course("asd101", SESSIONS)
        self.assertEqual(result["session_count"], 2)
        self.assertNotIn("staff_id", result["sessions"][0])

    def test_sessions_by_course_requires_code(self):
        with self.assertRaises(ValueError):
            sessions_by_course("  ", SESSIONS)

    def test_room_busy_returns_conflict(self):
        result = room_availability("CB01.02.15", "monday", "10:30", "11:30", SESSIONS)
        self.assertFalse(result["available"])
        self.assertEqual({c["session_id"] for c in result["conflicts"]}, {1, 3})

    def test_back_to_back_slot_is_free(self):
        result = room_availability("CB01.02.16", "Monday", "12:00", "13:00", SESSIONS)
        self.assertTrue(result["available"])
        self.assertEqual(result["conflicts"], [])

    def test_room_availability_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            room_availability("CB01.02.15", "Funday", "09:00", "10:00", SESSIONS)
        with self.assertRaises(ValueError):
            room_availability("CB01.02.15", "Monday", "11:00", "09:00", SESSIONS)
        with self.assertRaises(ValueError):
            room_availability("CB01.02.15", "Monday", "9am", "10:00", SESSIONS)

    def test_clashes_detects_overlap_in_same_room(self):
        result = timetable_clashes(SESSIONS)
        self.assertEqual(result["clash_count"], 1)
        clash = result["clashes"][0]
        self.assertEqual({clash["session_a"]["session_id"], clash["session_b"]["session_id"]}, {1, 3})


if __name__ == "__main__":
    unittest.main()
