"""Active-violation columns on the slot endpoints (/occupancy/slots,
/slots/by-floor, /slots/{id}, /export).

Runs against the database in .env. Inserts a handful of alerts tagged with a
marker description and deletes them afterwards.

    pytest tests/test_slot_violations.py -v -p no:cacheprovider
"""
import os
import sys
import time

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, rows  # noqa: E402

TAG = "pytest-slot-violations"

CASES = [
    # slot, type, severity, resolved, test, triggered_at
    ("B5", "vehicle_violation", "warning", 0, 0, "2026-09-20T10:00:00"),
    ("B5", "special_needs_violation", "critical", 0, 0, "2026-09-20T11:00:00"),  # newest on B5
    ("G1", "vehicle_intrusion", "high", 0, 0, "2026-09-21T09:00:00"),
    ("B14", "vehicle_violation", "critical", 1, 0, "2026-09-21T09:00:00"),        # resolved
    ("B15", "vehicle_violation", "critical", 0, 1, "2026-09-21T09:00:00"),        # test alert
    ("B16", "unknown_vehicle", "critical", 0, 0, "2026-09-21T09:00:00"),          # not a violation type
]


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def alerts():
    db = SessionLocal()
    slots = {r["slot_id"] for r in rows(db, "SELECT slot_id FROM parking_slots")}
    if not {c[0] for c in CASES} <= slots:
        pytest.skip("needs slots B5, B14, B15, B16 and G1")
    cam = rows(db, "SELECT TOP 1 camera_id FROM cameras")[0]["camera_id"]
    for slot, typ, sev, res, tst, at in CASES:
        db.execute(text("""
            INSERT INTO alerts (alert_type, camera_id, slot_id, severity, is_resolved,
                                is_test, triggered_at, description)
            VALUES (:t, :c, :s, :sev, :r, :x, :at, :d)
        """), {"t": typ, "c": cam, "s": slot, "sev": sev, "r": res, "x": tst, "at": at, "d": TAG})
    db.commit()
    yield
    db.execute(text("DELETE FROM alerts WHERE description = :d"), {"d": TAG})
    db.commit()
    db.close()


def _violation(item):
    return (item["active_violation_type"], item["active_violation_severity"],
            item["has_active_violation"])


@pytest.mark.parametrize("slot,expected", [
    ("B5", ("special_needs_violation", "critical", True)),   # the newest of two
    ("G1", ("vehicle_intrusion", "high", True)),
    ("B14", (None, None, False)),                             # resolved
    ("B15", (None, None, False)),                             # test
    ("B16", (None, None, False)),                             # not a violation type
])
def test_slot_detail(client, slot, expected):
    assert _violation(client.get(f"/occupancy/slots/{slot}").json()) == expected


def test_list_and_grid_agree_with_detail(client):
    listed = {i["slot_id"]: _violation(i)
              for i in client.get("/occupancy/slots?page=1&page_size=100").json()["items"]}
    grid = {s["slot_id"]: _violation(s)
            for f in client.get("/occupancy/slots/by-floor").json() for s in f["slots"]}
    for slot in ("B5", "G1", "B14", "B15", "B16"):
        detail = _violation(client.get(f"/occupancy/slots/{slot}").json())
        assert listed[slot] == grid[slot] == detail, slot


def test_every_slot_listed_once(client):
    """The join must not duplicate a slot that has several active alerts."""
    items = client.get("/occupancy/slots?page=1&page_size=100").json()["items"]
    ids = [i["slot_id"] for i in items]
    assert len(ids) == len(set(ids))
    assert ids.count("B5") == 1


def test_live_grid_is_fast(client):
    client.get("/occupancy/slots/by-floor")
    t = time.time()
    for _ in range(3):
        client.get("/occupancy/slots/by-floor")
    assert (time.time() - t) / 3 < 0.3   # was ~0.85 s before the join rewrite
