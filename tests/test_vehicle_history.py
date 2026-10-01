"""GET /vehicles/history — everything about one plate.

Runs against the database in .env. Inserts rows for a marker plate on empty
future days (2031) and deletes them afterwards.

    pytest tests/test_vehicle_history.py -v -p no:cacheprovider
"""
import os
import sys

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, scalar  # noqa: E402

PLATE = "TSTH-7741"         # stored letters-first; not a real plate format
OTHER = "TSTH-774"           # a different plate that a substring match would catch
# Temporary slot, flagged as a violation zone so no occupancy count includes it.
SLOT = "TSTH-TEST-SLOT"
SNAP = "https://snapshots.test/tsth-7741.jpg"   # absolute, so it is served unchanged

SESSIONS = [
    # plate, entry_time, exit_time, duration, status
    (PLATE, "2031-01-14 08:00:00", "2031-01-14 17:00:00", 32400, "closed"),
    (PLATE, "2031-01-15 22:00:00", "2031-01-16 07:00:00", 32400, "closed"),   # crossed midnight
    (PLATE, "2031-01-17 09:00:00", None, None, "open"),
    (OTHER, "2031-01-15 09:00:00", "2031-01-15 10:00:00", 3600, "closed"),
]
GATE_READS = [
    (PLATE, "entry", "CAM-ENTRY", "2031-01-14 08:00:00"),
    (PLATE, "exit", "CAM-EXIT", "2031-01-14 17:00:00"),
    (PLATE, "entry", "CAM-ENTRY", "2031-01-17 09:00:00"),
]
ALERTS = [
    # alert_type, triggered_at, is_resolved
    ("vehicle_intrusion", "2031-01-14 10:00:00", 1),
    ("overstay", "2031-01-16 00:30:00", 0),
]
SLOT_READINGS = [
    # plate, status, time — the first two are one sighting, the third ends it
    (PLATE, "occupied", "2031-01-14 08:10:00"),
    (PLATE, "occupied", "2031-01-14 09:00:00"),
    ("", "available", "2031-01-14 16:50:00"),
]


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def url():
    from app.routers.vehicles import prefix
    return prefix + "/history"


# Row ids this module inserted. Cleanup deletes exactly these, never by
# plate pattern: a real car once matched a `LIKE 'ZZR%'` test cleanup.
_inserted: dict[str, list[int]] = {
    "slot_status": [], "alerts": [], "entry_exit_log": [], "parking_sessions": [], "vehicles": [],
}


def _insert(db, table: str, sql: str, params: dict) -> None:
    _inserted[table].append(db.execute(text(sql), params).scalar())


def _cleanup(db, slot_created: bool):
    db.rollback()
    for table, ids in _inserted.items():      # slot_status first: it references the slot
        if ids:
            db.execute(text(f"DELETE FROM {table} WHERE id IN ({', '.join(map(str, ids))})"))
        ids.clear()
    if slot_created:
        db.execute(text("DELETE FROM parking_slots WHERE slot_id = :s"), {"s": SLOT})
    db.commit()


@pytest.fixture(scope="module", autouse=True)
def data():
    db = SessionLocal()
    taken = scalar(db, "SELECT COUNT(*) FROM parking_sessions WHERE plate_number IN (:a, :b)",
                   {"a": PLATE, "b": OTHER})
    taken = taken or scalar(db, "SELECT COUNT(*) FROM parking_slots WHERE slot_id = :s", {"s": SLOT})
    if taken:
        db.close()
        pytest.skip("marker plate or slot already exists")
    slot_created = False
    try:
        _insert(db, "vehicles", """
            INSERT INTO vehicles (plate_number, owner_name, vehicle_type, title, is_employee, is_registered)
            OUTPUT INSERTED.id
            VALUES (:p, 'History Test', 'sedan', '', 0, 1)
        """, {"p": PLATE})
        for plate, entry, exit_, dur, status in SESSIONS:
            _insert(db, "parking_sessions", """
                INSERT INTO parking_sessions (plate_number, is_employee, entry_time, exit_time,
                    duration_seconds, entry_camera_id, entry_snapshot_path, status, floor,
                    created_at, updated_at)
                OUTPUT INSERTED.id
                VALUES (:p, 0, :e, :x, :d, 'CAM-ENTRY', :snap, :s, 'B1', :e, :e)
            """, {"p": plate, "e": entry, "x": exit_, "d": dur, "s": status, "snap": SNAP})
        for plate, gate, cam, at in GATE_READS:
            _insert(db, "entry_exit_log", """
                INSERT INTO entry_exit_log (plate_number, gate, camera_id, event_time, snapshot_path, is_test)
                OUTPUT INSERTED.id
                VALUES (:p, :g, :c, :t, :snap, 0)
            """, {"p": plate, "g": gate, "c": cam, "t": at, "snap": SNAP})
        for atype, at, res in ALERTS:
            _insert(db, "alerts", """
                INSERT INTO alerts (alert_type, camera_id, plate_number, triggered_at, is_resolved,
                                    resolved_at, severity, is_test)
                OUTPUT INSERTED.id
                VALUES (:a, 'CAM-TEST', :p, :t, :r, CASE WHEN :r = 1 THEN :t END, 'high', 0)
            """, {"a": atype, "p": PLATE, "t": at, "r": res})
        db.execute(text("""
            INSERT INTO parking_slots (slot_id, slot_name, floor, is_available, is_violation_zone)
            VALUES (:s, 'History Test', 'B1', 1, 1)
        """), {"s": SLOT})
        slot_created = True
        for plate, status, at in SLOT_READINGS:
            _insert(db, "slot_status", """
                INSERT INTO slot_status (slot_id, plate_number, status, time)
                OUTPUT INSERTED.id
                VALUES (:s, :p, :st, :t)
            """, {"s": SLOT, "p": plate, "st": status, "t": at})
        db.commit()
        yield
    finally:
        _cleanup(db, slot_created)
        db.close()


RANGE = {"date_from": "2031-01-01", "date_to": "2031-01-31"}


def test_either_display_order_matches(client, url):
    for typed in ("TSTH-7741", "7741-TSTH", "7741 tsth", "tsth7741"):
        body = client.get(url, params={"plate": typed, **RANGE}).json()
        assert body["matched_plates"] == [PLATE], typed
        assert body["sessions"]["total"] == 3, typed


def test_exact_match_never_catches_another_plate(client, url):
    body = client.get(url, params={"plate": OTHER, **RANGE}).json()
    assert body["sessions"]["total"] == 1
    assert body["vehicle"] is None
    assert body["alerts"]["total"] == 0


def test_sections_and_summary(client, url):
    body = client.get(url, params={"plate": PLATE, **RANGE}).json()
    assert body["found"] is True
    assert body["vehicle"]["owner_name"] == "History Test"
    assert body["sessions"]["total"] == 3
    assert body["gate_reads"]["total"] == 3
    assert body["alerts"]["total"] == 2
    s = body["summary"]
    assert s["visits"] == 3
    # Only the visit that crossed midnight. The open one entered in 2031, after
    # today's midnight, so it hasn't been inside at a midnight yet.
    assert s["overstays"] == 1
    assert s["alerts"] == 2 and s["open_alerts"] == 1
    assert s["gate_reads"] == 3
    assert body["timeline"] is None       # only on request


def test_current_ignores_the_range(client, url):
    body = client.get(url, params={"plate": PLATE, "date_from": "2031-01-14", "date_to": "2031-01-14"}).json()
    assert body["sessions"]["total"] == 1
    cur = body["current"]
    assert cur["is_inside"] is True
    assert cur["open_sessions_count"] == 1
    assert cur["open_session"]["entry"]["event_time"].startswith("2031-01-17T09:00:00")
    assert cur["open_alerts"] == 1


def test_filters_apply_to_their_section_only(client, url):
    body = client.get(url, params={
        "plate": PLATE, **RANGE, "session_status": "closed", "resolved": "false", "gate": "exit",
    }).json()
    assert body["sessions"]["total"] == 2
    assert body["alerts"]["total"] == 1
    assert body["alerts"]["items"][0]["alert_type"] == "overstay"
    assert body["gate_reads"]["total"] == 1
    assert body["summary"]["visits"] == 3          # summary ignores filters


def test_slot_readings_merge_into_one_sighting(client, url):
    body = client.get(url, params={"plate": PLATE, **RANGE, "include": "slots"}).json()
    assert body["sessions"] is None
    sl = body["slot_history"]
    assert sl["total"] == 1
    item = sl["items"][0]
    assert item["slot_id"] == SLOT
    assert item["observations"] == 2
    assert item["seen_from"].startswith("2031-01-14T08:10:00")
    assert item["seen_until"].startswith("2031-01-14T16:50:00")
    assert item["duration_seconds"] == 8 * 3600 + 40 * 60


def test_timeline_newest_first_and_capped(client, url):
    body = client.get(url, params={"plate": PLATE, **RANGE, "include": "timeline", "limit": 4}).json()
    assert body["sessions"] is None       # timeline alone doesn't return the sections
    tl = body["timeline"]
    assert len(tl) == 4
    assert [t["at"] for t in tl] == sorted((t["at"] for t in tl), reverse=True)
    assert tl[0]["kind"] in ("entry", "gate_read") and tl[0]["at"].startswith("2031-01-17T09:00:00")


def test_timeline_carries_each_events_image(client, url):
    tl = client.get(url, params={"plate": PLATE, **RANGE, "include": "timeline", "limit": 500}).json()["timeline"]
    by_kind: dict[str, set] = {}
    for t in tl:
        by_kind.setdefault(t["kind"], set()).add(t["snapshot_url"])
    assert by_kind["entry"] == {SNAP}
    assert by_kind["gate_read"] == {SNAP}
    assert by_kind["exit"] == {None}              # the fixture stores no exit image
    assert by_kind["alert_resolved"] == {None}
    assert by_kind["slot"] == {None}


def test_limit_caps_items_not_total(client, url):
    body = client.get(url, params={"plate": PLATE, **RANGE, "limit": 1}).json()
    assert body["sessions"]["total"] == 3
    assert len(body["sessions"]["items"]) == 1
    assert body["sessions"]["items"][0]["status"] == "open"     # newest first


def test_unknown_plate_is_not_found(client, url):
    body = client.get(url, params={"plate": "TSTH-0000"}).json()
    assert body["found"] is False
    assert body["current"]["is_inside"] is False


def test_bad_requests(client, url):
    assert client.get(url, params={"plate": PLATE, "include": "nope"}).status_code == 400
    assert client.get(url, params={"plate": PLATE, "date_from": "2031-01-02",
                                   "date_to": "2031-01-01"}).status_code == 400
    assert client.get(url, params={"plate": "--"}).status_code == 400
    assert client.get(url).status_code == 422


def test_csv_is_the_full_timeline(client, url):
    r = client.get(url + "/export/csv", params={"plate": PLATE, **RANGE})
    assert r.status_code == 200
    lines = r.text.strip().splitlines()
    assert lines[0] == "Time,Event,Reference,Details,Camera,Slot,Floor,Severity"
    # 3 entries + 2 exits + 3 gate reads + 2 alerts + 1 resolution + 1 slot sighting
    assert len(lines) - 1 == 12
