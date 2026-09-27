"""GET /entry-exit/kpis and /entry-exit/peak-hours with a date range.

Runs against the database in .env. Inserts a few parking sessions in January
2031 with marker plates, pins the facility clock to that week, and deletes the
sessions afterwards.

    pytest tests/test_entry_exit_range.py -v -p no:cacheprovider
"""
import os
import sys
from datetime import datetime

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, scalar  # noqa: E402

PLATE = "ZZER"          # marker prefix; no real plate starts with it
D = "2031-01-15"
D1 = "2031-01-16"
NOW = datetime(2031, 1, 20, 10, 0)

CASES = [
    # suffix, entry_time, exit_time, duration_seconds
    ("A", f"{D} 08:00:00", f"{D} 10:00:00", 7200),          # same-day visit
    ("B", f"{D} 20:00:00", f"{D1} 09:00:00", 46800),        # overnight, leaves D+1
    ("C", f"{D} 23:00:00", None, None),                     # overnight, never left
    ("D", "2031-01-14 22:00:00", f"{D} 01:00:00", 10800),   # overnight into D
    ("E", f"{D1} 07:00:00", f"{D1} 08:00:00", 3600),        # same-day visit on D+1
]


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def prefix():
    from app.routers.entry_exit import prefix
    return prefix


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    from app.routers import entry_exit
    monkeypatch.setattr(entry_exit, "facility_now_naive", lambda: NOW)


@pytest.fixture(scope="module", autouse=True)
def sessions():
    db = SessionLocal()
    if scalar(db, "SELECT COUNT(*) FROM parking_sessions WHERE entry_time >= '2031-01-01'"):
        pytest.skip("parking_sessions already has rows in 2031")
    for suffix, entry, exit_, dur in CASES:
        db.execute(text("""
            INSERT INTO parking_sessions (plate_number, is_employee, entry_time, exit_time,
                                          duration_seconds, entry_camera_id, status,
                                          created_at, updated_at)
            VALUES (:p, 0, :entry, :exit, :dur, 'pytest', :st, :entry, :entry)
        """), {"p": PLATE + suffix, "entry": entry, "exit": exit_, "dur": dur,
               "st": "closed" if exit_ else "open"})
    db.commit()
    yield
    db.execute(text("DELETE FROM parking_sessions WHERE plate_number LIKE :p"), {"p": PLATE + "%"})
    db.commit()
    db.close()


@pytest.fixture(scope="module")
def stale():
    """Real sessions still open from before 2031: inside at every 2031
    midnight, so they add to every overstay count below."""
    db = SessionLocal()
    n = scalar(db, """
        SELECT COUNT(DISTINCT plate_number) FROM parking_sessions
        WHERE exit_time IS NULL AND plate_number IS NOT NULL AND entry_time < '2031-01-01'
    """)
    db.close()
    return n or 0


def _kpis(client, prefix, **params):
    r = client.get(prefix + "/kpis", params=params)
    assert r.status_code == 200, r.text
    return r.json()


class TestKpis:
    def test_one_day(self, client, prefix, stale):
        k = _kpis(client, prefix, date_from=D, date_to=D)
        assert (k["total_enter"], k["total_exit"], k["overstays"]) == (3, 2, 1 + stale)
        # A 7200 + B 46800 + C live (D 23:00 -> NOW = 385200) over 3 cars
        assert k["avg_stay_minutes"] == 2440.0

    def test_exits_are_on_the_exit_day(self, client, prefix):
        k = _kpis(client, prefix, date_from=D1, date_to=D1)
        assert (k["total_enter"], k["total_exit"]) == (1, 2)   # E in; B and E out

    def test_overstays_inside_at_midnight(self, client, prefix, stale):
        assert _kpis(client, prefix, date_from=D1, date_to=D1)["overstays"] == 2 + stale   # B, C
        assert _kpis(client, prefix, date_from=D, date_to=D1)["overstays"] == 3 + stale    # B, C, D

    def test_no_overstays_in_a_future_range(self, client, prefix, monkeypatch):
        from app.routers import entry_exit
        monkeypatch.setattr(entry_exit, "facility_now_naive", lambda: datetime(2031, 1, 16, 12, 0))
        k = _kpis(client, prefix, date_from="2031-01-18", date_to="2031-01-19")
        assert k["overstays"] == 0          # no midnight of the range has come yet

    def test_previous_period_same_length(self, client, prefix):
        k = _kpis(client, prefix, date_from=D1, date_to=D1)
        assert (k["previous_from"], k["previous_to"]) == (D, D)
        assert k["previous"]["total_enter"] == 3
        k = _kpis(client, prefix, date_from=D, date_to=D1)
        assert (k["previous_from"], k["previous_to"]) == ("2031-01-13", "2031-01-14")
        assert k["previous"]["total_enter"] == 1     # D entered on the 14th

    def test_default_is_today(self, client, prefix, monkeypatch, stale):
        from app.routers import entry_exit
        monkeypatch.setattr(entry_exit, "facility_now_naive", lambda: datetime(2031, 1, 16, 12, 0))
        k = _kpis(client, prefix)
        assert (k["date_from"], k["date_to"]) == (D1, D1)
        assert (k["total_enter"], k["overstays"]) == (1, 2 + stale)

    def test_target_date_still_works(self, client, prefix):
        k = _kpis(client, prefix, target_date=D)
        assert (k["date_from"], k["total_enter"]) == (D, 3)

    def test_only_date_from_runs_to_today(self, client, prefix):
        k = _kpis(client, prefix, date_from=D)
        assert k["date_to"] == "2031-01-20"
        assert k["total_enter"] == 4

    def test_reversed_range_is_400(self, client, prefix):
        assert client.get(prefix + "/kpis", params={"date_from": D1, "date_to": D}).status_code == 400


class TestPeakHours:
    def test_24_buckets_summed_over_the_range(self, client, prefix):
        r = client.get(prefix + "/peak-hours", params={"date_from": D, "date_to": D})
        assert r.status_code == 200
        items = r.json()["items"]
        assert [i["hour"] for i in items] == list(range(24))
        entries = {i["hour"]: i["entries"] for i in items if i["entries"]}
        exits = {i["hour"]: i["exits"] for i in items if i["exits"]}
        assert entries == {8: 1, 20: 1, 23: 1}
        assert exits == {1: 1, 10: 1}

    def test_bars_add_up_to_the_kpis(self, client, prefix):
        items = client.get(prefix + "/peak-hours", params={"date_from": D, "date_to": D1}).json()["items"]
        k = _kpis(client, prefix, date_from=D, date_to=D1)
        assert sum(i["entries"] for i in items) == k["total_enter"]
        assert sum(i["exits"] for i in items) == k["total_exit"]

    def test_reversed_range_is_400(self, client, prefix):
        assert client.get(prefix + "/peak-hours", params={"date_from": D1, "date_to": D}).status_code == 400
