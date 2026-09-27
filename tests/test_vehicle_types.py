"""GET /entry-exit/vehicle-types — the Vehicle Type Distribution donut.

Runs against the database in .env. Inserts a few parking sessions on an empty
future day with marker plates and deletes them afterwards.

    pytest tests/test_vehicle_types.py -v -p no:cacheprovider
"""
import os
import sys

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, scalar  # noqa: E402

PLATE = "ZZVT"          # marker prefix; no real plate starts with it
DAY = "2031-01-15"

CASES = [
    # plate suffix, vehicle_type, entry_time
    ("1", "Sedan", f"{DAY} 08:00:00"),
    ("2", " sedan ", f"{DAY} 09:00:00"),     # same type, different spelling
    ("3", "sedan", f"{DAY} 10:00:00"),
    ("4", "SUV", f"{DAY} 11:00:00"),
    ("5", "pickup", f"{DAY} 23:59:59"),       # last second of the day
    ("6", None, f"{DAY} 12:00:00"),           # no type -> other
    ("7", "unknown", f"{DAY} 13:00:00"),      # -> other
    ("8", "", f"{DAY} 14:00:00"),             # -> other
    ("9", "suv", "2031-01-16 00:00:00"),      # next day, outside date_to
]


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def url():
    from app.routers.entry_exit import prefix
    return prefix + "/vehicle-types"


@pytest.fixture(scope="module", autouse=True)
def sessions():
    db = SessionLocal()
    if scalar(db, "SELECT COUNT(*) FROM parking_sessions WHERE entry_time >= '2031-01-01'"):
        pytest.skip("parking_sessions already has rows in 2031")
    for suffix, vtype, at in CASES:
        db.execute(text("""
            INSERT INTO parking_sessions (plate_number, vehicle_type, is_employee, entry_time,
                                          entry_camera_id, status, created_at, updated_at)
            VALUES (:p, :t, 0, :at, 'pytest', 'open', :at, :at)
        """), {"p": PLATE + suffix, "t": vtype, "at": at})
    db.commit()
    yield
    db.execute(text("DELETE FROM parking_sessions WHERE plate_number LIKE :p"), {"p": PLATE + "%"})
    db.commit()
    db.close()


def _counts(body):
    return {i["vehicle_type"]: i["count"] for i in body["items"]}


def test_one_day(client, url):
    r = client.get(url, params={"date_from": DAY, "date_to": DAY})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 8
    assert _counts(body) == {"sedan": 3, "suv": 1, "pickup": 1, "other": 3}


def test_order_most_first_other_last(client, url):
    body = client.get(url, params={"date_from": DAY, "date_to": DAY}).json()
    assert [i["vehicle_type"] for i in body["items"]] == ["sedan", "pickup", "suv", "other"]


def test_pct(client, url):
    body = client.get(url, params={"date_from": DAY, "date_to": DAY}).json()
    pct = {i["vehicle_type"]: i["pct"] for i in body["items"]}
    assert pct == {"sedan": 37.5, "pickup": 12.5, "suv": 12.5, "other": 37.5}


def test_open_ended_range(client, url):
    body = client.get(url, params={"date_from": DAY}).json()
    assert body["total"] == 9
    assert _counts(body)["suv"] == 2


def test_empty_range_keeps_other(client, url):
    body = client.get(url, params={"date_from": "2031-02-01", "date_to": "2031-02-01"}).json()
    assert body["total"] == 0
    assert body["items"] == [{"vehicle_type": "other", "count": 0, "pct": 0.0}]


def test_reversed_range_is_400(client, url):
    r = client.get(url, params={"date_from": "2031-01-16", "date_to": DAY})
    assert r.status_code == 400


def test_all_time_adds_up(client, url):
    body = client.get(url).json()
    assert body["total"] == sum(i["count"] for i in body["items"])
    assert body["items"][-1]["vehicle_type"] == "other"
