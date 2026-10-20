"""Release 2 post-commit CI/CD tests: two Timetable endpoint functions.

  1. create_session  -> POST /timetable
  2. get_clashes     -> GET  /timetable/clashes

Each test runs against its own fresh copy of the seeded database (10 sessions),
so results never depend on what earlier tests or a local run left behind.

Run from student-3/backend:
    python -m pytest tests/test_endpoints.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app as timetable_app  # noqa: E402
import init_db  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "timetable.db"
    monkeypatch.setattr(init_db, "DATABASE_NAME", db_path)
    init_db.init_db()
    monkeypatch.setattr(timetable_app, "DATABASE_NAME", str(db_path))
    timetable_app.app.config["TESTING"] = True
    return timetable_app.app.test_client()


def new_session(**overrides):
    form = {
        "course_code": "ASD101",
        "session_type": "Lab",
        "day": "Monday",
        "start_time": "13:00",
        "end_time": "15:00",
        "room": "CB01.02.20",
        "semester": "2026-S2",
    }
    form.update(overrides)
    return form


def session_count(client):
    return len(client.get("/api/timetable").get_json())


# ---------- Endpoint 1: POST /timetable (create_session) ----------

class TestCreateSession:
    def test_valid_session_is_created_and_persisted(self, client):
        response = client.post("/timetable", data=new_session())

        assert response.status_code == 201
        assert b"Session created with ID 11" in response.data
        sessions = client.get("/api/timetable").get_json()
        assert len(sessions) == 11
        created = sessions[-1]
        assert created["course_code"] == "ASD101"
        assert created["room"] == "CB01.02.20"
        assert created["staff_id"] is None  # optional field left blank is stored as NULL

    def test_missing_required_fields_are_rejected(self, client):
        response = client.post("/timetable", data=new_session(room="", start_time=""))

        assert response.status_code == 400
        assert b"start_time" in response.data and b"room" in response.data
        assert session_count(client) == 10  # nothing was written

    def test_whitespace_only_field_counts_as_missing(self, client):
        response = client.post("/timetable", data=new_session(course_code="   "))

        assert response.status_code == 400
        assert session_count(client) == 10


# ---------- Endpoint 2: GET /timetable/clashes (get_clashes) ----------

class TestClashDetection:
    def test_seed_timetable_has_no_clashes(self, client):
        response = client.get("/timetable/clashes")

        assert response.status_code == 200
        assert b"No clashes detected." in response.data

    def test_overlapping_session_in_same_room_is_reported(self, client):
        # Seed session 1: ASD101 Lecture, Monday 09:00-11:00 in CB01.02.15
        client.post("/timetable", data=new_session(course_code="WEB201", room="CB01.02.15",
                                                   start_time="10:00", end_time="12:00"))

        response = client.get("/timetable/clashes")

        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert body.count("<li>Clash:") == 1
        assert "session 1 (ASD101) and session 11 (WEB201)" in body
        assert "CB01.02.15 on Monday" in body

    def test_back_to_back_sessions_do_not_clash(self, client):
        # Starts exactly when seed session 1 ends (11:00): the policy says this is not a clash.
        client.post("/timetable", data=new_session(room="CB01.02.15", start_time="11:00", end_time="12:00"))

        assert b"No clashes detected." in client.get("/timetable/clashes").data

    def test_same_time_different_room_does_not_clash(self, client):
        client.post("/timetable", data=new_session(room="CB09.09.09", start_time="09:00", end_time="11:00"))

        assert b"No clashes detected." in client.get("/timetable/clashes").data
