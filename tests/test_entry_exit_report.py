"""Custom Reports -> Entry/Exit Report:
GET /entry-exit/reports/activity/kpis (cards) and
GET /entry-exit/reports/activity (table).

Runs against the database in .env. Inserts visits on empty PAST days (April
2025) plus one visit entered a few minutes ago (the only way to get a
still-parking, not-yet-overstay row), and deletes them afterwards by id.

    pytest tests/test_entry_exit_report.py -v -p no:cacheprovider
"""
import os
import sys
from datetime import timedelta

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import facility_now_naive  # noqa: E402
from app.database import SessionLocal, scalar  # noqa: E402

DAY = "2025-04-15"
NEXT = "2025-04-16"
RANGE = {"date_from": DAY, "date_to": DAY}

VISITS = [
    # plate, entry, exit, stored duration, floor, slot_id, slot_number
    ("TSTE-001", f"{DAY} 08:00:00", f"{DAY} 10:00:00", 7200, "B1", None, "A12"),   # completed
    ("TSTE-002", f"{DAY} 20:00:00", f"{NEXT} 07:00:00", 39600, "B2", None, None),  # overstayed, then left
    ("TSTE-003", f"{DAY} 09:00:00", None, None, "B1", None, None),                 # never left: overstay
    ("TSTE-004", f"{DAY} 11:00:00", f"{DAY} 11:00:00", 0, None, "G1", None),       # zero stay; floor from slot
    ("TSTE-006", f"{DAY} 12:00:00", f"{DAY} 13:00:00", None, "B2", None, None),    # no stored duration
    ("TSTE-005", "2025-04-14 10:00:00", "2025-04-14 12:00:00", 7200, "B1", None, None),  # outside the range
]
PARKING_PLATE = "TSTE-007"   # entered minutes ago, still inside


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def base():
    from app.routers.entry_exit_report import prefix
    return prefix + "/activity"


_inserted: list[int] = []


def _insert(db, plate, entry, exit_, duration, floor, slot_id, slot_number):
    _inserted.append(db.execute(text("""
        INSERT INTO parking_sessions (plate_number, is_employee, entry_time, exit_time,
            duration_seconds, entry_camera_id, exit_camera_id, status, floor, slot_id,
            slot_number, created_at, updated_at)
        OUTPUT INSERTED.id
        VALUES (:p, 0, :e, :x, :d, 'CAM-ENTRY', CASE WHEN :x IS NULL THEN NULL ELSE 'CAM-EXIT' END,
                CASE WHEN :x IS NULL THEN 'open' ELSE 'closed' END, :f, :sid, :sn, :e, :e)
    """), {"p": plate, "e": entry, "x": exit_, "d": duration, "f": floor,
           "sid": slot_id, "sn": slot_number}).scalar())


@pytest.fixture(scope="module", autouse=True)
def data():
    db = SessionLocal()
    if scalar(db, "SELECT COUNT(*) FROM parking_sessions WHERE entry_time >= '2025-04-01' AND entry_time < '2025-05-01'"):
        db.close()
        pytest.skip("parking_sessions already has rows in April 2025")
    try:
        for v in VISITS:
            _insert(db, *v)
        _insert(db, PARKING_PLATE, facility_now_naive() - timedelta(minutes=5), None, None, "B1", None, None)
        db.commit()
        yield
    finally:
        db.rollback()
        if _inserted:
            db.execute(text(f"DELETE FROM parking_sessions WHERE id IN ({', '.join(map(str, _inserted))})"))
            db.commit()
        db.close()


def _kpis(client, base, **params):
    r = client.get(base + "/kpis", params={**RANGE, **params})
    assert r.status_code == 200, r.text
    return r.json()


def _list(client, base, **params):
    r = client.get(base, params={**RANGE, "page_size": 50, **params})
    assert r.status_code == 200, r.text
    return r.json()


def _items(client, base, **params):
    return _list(client, base, **params)["items"]


def test_kpis(client, base):
    k = _kpis(client, base)
    assert k["total_entries"] == 5          # 005 entered the day before
    assert k["total_exits"] == 4            # 003 never left
    assert k["net_vehicles"] == 1
    assert k["overstays"] == 2              # 002 (left the next morning) + 003 (never left)


def test_kpis_match_the_table(client, base):
    assert _list(client, base)["total_count"] == _kpis(client, base)["total_entries"]


def test_avg_stay_whole_minutes_positive_only(client, base):
    # B2: 002 = 39600s, 006 = 3600s (exit - entry: no stored duration).
    k = _kpis(client, base, location="b2")
    assert (k["total_entries"], k["total_exits"], k["net_vehicles"]) == (2, 2, 0)
    assert k["avg_stay_minutes"] == 360
    assert isinstance(k["avg_stay_minutes"], int)


def test_rows(client, base):
    rows = {r["plate_number"]: r for r in _items(client, base)}
    assert set(rows) == {"TSTE-001", "TSTE-002", "TSTE-003", "TSTE-004", "TSTE-006"}

    r = rows["TSTE-001"]
    assert (r["type"], r["status"], r["is_overstay"]) == ("exit", "completed", False)
    assert r["location"] == "B1 - A12"
    assert r["duration_seconds"] == 7200
    assert r["entry"]["event_time"].startswith(f"{DAY}T08:00:00")
    assert r["exit"]["event_time"].startswith(f"{DAY}T10:00:00")

    r = rows["TSTE-002"]                    # Type and Status are independent
    assert (r["type"], r["status"], r["is_overstay"]) == ("exit", "overstay", True)

    r = rows["TSTE-003"]
    assert (r["type"], r["status"], r["is_overstay"]) == ("entry", "overstay", True)
    assert r["exit"] is None
    assert r["duration_seconds"] > 86400    # live, up to now

    r = rows["TSTE-004"]
    assert r["duration_seconds"] is None    # zero stay reads as no duration
    assert (r["floor"], r["location"]) == ("Ground", "Ground - G1")   # floor from the slot

    assert rows["TSTE-006"]["duration_seconds"] == 3600
    assert "gate" not in rows["TSTE-001"]


def test_parking_status(client, base):
    today = facility_now_naive().date().isoformat()
    rows = _items(client, base, date_from=today, date_to=today, search=PARKING_PLATE)
    assert [(r["type"], r["status"], r["is_overstay"]) for r in rows] == [("entry", "parking", False)]


def test_location_filter(client, base):
    assert {r["plate_number"] for r in _items(client, base, location="B1")} == {"TSTE-001", "TSTE-003"}
    assert {r["plate_number"] for r in _items(client, base, location="ground")} == {"TSTE-004"}
    assert _items(client, base, location="plaza-1") == []


def test_search_either_plate_order(client, base):
    assert [r["plate_number"] for r in _items(client, base, search="002-TSTE")] == ["TSTE-002"]
    assert _kpis(client, base, search="TSTE-002")["total_entries"] == 1


def test_sort_by_duration(client, base):
    asc = [r["plate_number"] for r in _items(client, base, sort_by="duration", sort_dir="asc")]
    desc = [r["plate_number"] for r in _items(client, base, sort_by="duration", sort_dir="desc")]
    assert asc == ["TSTE-006", "TSTE-001", "TSTE-002", "TSTE-003", "TSTE-004"]   # no duration last
    assert desc == ["TSTE-003", "TSTE-002", "TSTE-001", "TSTE-006", "TSTE-004"]


def test_sort_by_plate(client, base):
    asc = [r["plate_number"] for r in _items(client, base, sort_by="plate", sort_dir="asc")]
    assert asc == ["TSTE-001", "TSTE-002", "TSTE-003", "TSTE-004", "TSTE-006"]
    assert [r["plate_number"] for r in _items(client, base, sort_by="plate", sort_dir="desc")] == asc[::-1]


def test_sort_by_location(client, base):
    asc = [r["location"] for r in _items(client, base, sort_by="location", sort_dir="asc")]
    assert asc == sorted(asc)


def test_sort_by_time_and_default(client, base):
    asc = [r["plate_number"] for r in _items(client, base, sort_by="time", sort_dir="asc")]
    assert asc == ["TSTE-001", "TSTE-003", "TSTE-004", "TSTE-006", "TSTE-002"]
    assert [r["plate_number"] for r in _items(client, base)] == asc[::-1]   # newest entry first


def test_paging(client, base):
    page = _list(client, base, page=2, page_size=2)
    assert (page["total_count"], page["page"], len(page["items"])) == (5, 2, 2)
    past = _list(client, base, page=9, page_size=2)
    assert (past["total_count"], past["items"]) == (5, [])


@pytest.mark.parametrize("suffix", ["", "/kpis"])
def test_reversed_range_is_400(client, base, suffix):
    assert client.get(base + suffix, params={"date_from": NEXT, "date_to": DAY}).status_code == 400


def test_entry_exit_page_untouched(client):
    # The Entry/Exit page keeps its own exit-day Exits card and list shape.
    from app.routers.entry_exit import prefix as ee
    k = client.get(ee + "/kpis", params=RANGE).json()
    assert {"total_enter", "total_exit", "avg_stay_minutes", "overstays"} <= set(k)
    assert client.get(ee + "/", params=RANGE).status_code == 200
