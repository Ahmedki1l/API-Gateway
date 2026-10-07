"""GET /alerts/reports/overstay-violations/kpis (cards) and
GET /alerts/reports/overstay-violations (Violation Details table).

A violation is a violation-type alert (vehicle_violation = No-Parking;
special_needs_violation / vehicle_intrusion / named_slot_violation = Other)
or one overnight stay from parking_sessions.

Runs against the database in .env. Inserts marker rows on empty PAST days
(March 2025 — an overstay only counts up to today's midnight, so future days
never would) and deletes them afterwards.

    pytest tests/test_overstay_violations_report.py -v -p no:cacheprovider
"""
import os
import sys

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, scalar  # noqa: E402

DAY = "2025-03-11"
RANGE = {"date_from": DAY, "date_to": DAY}

ALERTS = [
    # alert_type, triggered_at, resolved_at
    ("vehicle_violation", f"{DAY} 09:00:00", f"{DAY} 09:30:00"),        # 1800s, in zone Violation-B1
    ("vehicle_violation", f"{DAY} 10:00:00", None),                     # unresolved: no duration
    ("special_needs_violation", f"{DAY} 11:00:00", f"{DAY} 11:05:00"),  # 300s
    ("vehicle_intrusion", f"{DAY} 12:00:00", f"{DAY} 13:00:00"),        # 3600s
    ("unknown_vehicle", f"{DAY} 13:00:00", None),                       # not a violation
    ("capacity_exceeded", f"{DAY} 14:00:00", None),                     # not a violation
    ("overstay", f"{DAY} 15:00:00", None),                              # stray row, never counted
    ("vehicle_violation", "2025-03-12 09:00:00", None),                 # outside the range
]
SESSIONS = [
    # plate, entry, exit — inside at 00:00 on DAY = overstay for DAY
    ("TSTR-001", "2025-03-10 20:00:00", f"{DAY} 08:00:00"),      # overstay, 8h past midnight
    ("TSTR-002", "2025-03-10 21:00:00", f"{DAY} 07:00:00"),      # overstay, 7h past midnight
    ("TSTR-002", "2025-03-09 21:00:00", "2025-03-10 07:00:00"),  # same car, the night before
    ("TSTR-003", f"{DAY} 08:00:00", f"{DAY} 17:00:00"),          # same-day visit, no overstay
]


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def url():
    from app.routers.reports import prefix
    return prefix + "/overstay-violations"


# Row ids this module inserted. Cleanup deletes exactly these, never by
# plate pattern: a real car once matched the old `LIKE 'ZZR%'` cleanup.
_inserted: dict[str, list[int]] = {"alerts": [], "parking_sessions": []}


def _cleanup(db):
    db.rollback()
    for table, ids in _inserted.items():
        if ids:
            db.execute(text(f"DELETE FROM {table} WHERE id IN ({', '.join(map(str, ids))})"))
        ids.clear()
    db.commit()


@pytest.fixture(scope="module", autouse=True)
def data():
    db = SessionLocal()
    busy = scalar(db, "SELECT COUNT(*) FROM alerts WHERE triggered_at >= '2025-03-01' AND triggered_at < '2025-04-01'")
    busy = busy or scalar(db, "SELECT COUNT(*) FROM parking_sessions WHERE entry_time >= '2025-03-01' AND entry_time < '2025-04-01'")
    if busy:
        db.close()
        pytest.skip("alerts / parking_sessions already have rows in March 2025")
    try:
        for i, (atype, at, res) in enumerate(ALERTS):
            _inserted["alerts"].append(db.execute(text("""
                INSERT INTO alerts (alert_type, camera_id, plate_number, triggered_at, is_resolved,
                                    resolved_at, severity, is_test, slot_id)
                OUTPUT INSERTED.id
                VALUES (:a, 'CAM-TEST', :p, :t, :r, :res, 'critical', 0, :slot)
            """), {"a": atype, "p": f"TSTR-A{i}", "t": at, "r": 1 if res else 0, "res": res,
                   "slot": "Violation-B1" if i == 0 else None}).scalar())
        for plate, entry, exit_ in SESSIONS:
            _inserted["parking_sessions"].append(db.execute(text("""
                INSERT INTO parking_sessions (plate_number, is_employee, entry_time, exit_time,
                    duration_seconds, entry_camera_id, status, floor, created_at, updated_at)
                OUTPUT INSERTED.id
                VALUES (:p, 0, :e, :x, DATEDIFF(SECOND, :e, :x), 'CAM-ENTRY', 'closed', 'B1', :e, :e)
            """), {"p": plate, "e": entry, "x": exit_}).scalar())
        db.commit()
        yield
    finally:
        _cleanup(db)
        db.close()


def _kpis(client, url, **params):
    r = client.get(url + "/kpis", params={**RANGE, **params})
    assert r.status_code == 200, r.text
    return r.json()


def _list(client, url, **params):
    r = client.get(url, params={**RANGE, "page_size": 100, **params})
    assert r.status_code == 200, r.text
    return r.json()


def _items(client, url, **params):
    return _list(client, url, **params)["items"]


def test_cards_count_violations_only(client, url):
    body = _kpis(client, url)
    assert body["no_parking"] == 2          # open + resolved vehicle_violation
    assert body["other"] == 2               # special_needs_violation + vehicle_intrusion
    assert body["overstays"] == 2
    assert body["total_violations"] == 6    # unknown_vehicle / capacity / stray overstay left out
    assert "items" not in body


def test_list_total_matches_kpis(client, url):
    page = _list(client, url)
    assert page["total_count"] == _kpis(client, url)["total_violations"] == 6
    assert len(page["items"]) == 6


def test_by_type_is_violation_types_only(client, url):
    from app.routers.reports import VIOLATION_TYPES
    body = _kpis(client, url)
    types = {t["alert_type"] for t in body["by_type"]}
    assert types <= set(VIOLATION_TYPES)
    assert sum(t["count"] for t in body["by_type"]) == body["no_parking"] + body["other"]


def test_row_fields(client, url):
    items = _items(client, url)
    by_plate = {i["plate_number"]: i for i in items}
    assert by_plate["TSTR-A0"]["duration_seconds"] == 1800      # resolved_at - triggered_at
    assert by_plate["TSTR-A1"]["duration_seconds"] is None      # unresolved
    assert by_plate["TSTR-A0"]["category"] == "no_parking"
    assert by_plate["TSTR-A0"]["location"] == "Violation-B1"     # the zone, not just its floor
    assert by_plate["TSTR-A1"]["location"] == "CAM-TEST"         # no zone or floor: the camera
    assert by_plate["TSTR-A2"]["category"] == "other"
    assert by_plate["TSTR-A3"]["category"] == "other"
    ov = by_plate["TSTR-001"]
    assert (ov["source"], ov["violation_type"], ov["category"], ov["display_name"]) == \
        ("overstay", "overstay", "overstay", "Overstay")
    assert ov["duration_seconds"] == 8 * 3600                   # midnight -> 08:00 exit
    assert ov["location"] == "B1"
    assert "fine_amount" not in ov and "status" not in ov


def test_sort_by_duration(client, url):
    asc = [i["duration_seconds"] for i in _items(client, url, sort_by="duration", sort_dir="asc")]
    desc = [i["duration_seconds"] for i in _items(client, url, sort_by="duration", sort_dir="desc")]
    assert asc == [300, 1800, 3600, 25200, 28800, None]         # empty last either way
    assert desc == [28800, 25200, 3600, 1800, 300, None]


def test_sort_by_plate_as_displayed(client, url):
    # Displayed digits first: "001-TSTR" sorts before "A0-TSTR".
    asc = [i["plate_number"] for i in _items(client, url, sort_by="plate", sort_dir="asc")]
    assert asc[:2] == ["TSTR-001", "TSTR-002"]
    desc = [i["plate_number"] for i in _items(client, url, sort_by="plate", sort_dir="desc")]
    assert desc == asc[::-1]


def test_sort_by_location(client, url):
    # Overstays sit on floor B1; the test alerts have no floor or slot, so show the camera.
    asc = [i["location"] for i in _items(client, url, sort_by="location", sort_dir="asc")]
    assert asc == sorted(asc)
    assert asc[:2] == ["B1", "B1"]


def test_default_order_newest_first(client, url):
    items = _items(client, url)
    stamps = [i["occurred_at"] for i in items]
    assert stamps == sorted(stamps, reverse=True)


def test_paging(client, url):
    body = _list(client, url, page=2, page_size=4)
    assert body["total_count"] == 6
    assert body["page"] == 2
    assert len(body["items"]) == 2


def test_overstay_counts_stays_not_cars(client, url):
    from app.routers.entry_exit import prefix as ee
    span = {"date_from": "2025-03-10", "date_to": DAY}
    kpis = _kpis(client, url, **span)
    ee_kpis = client.get(ee + "/kpis", params=span).json()
    assert kpis["overstays"] == 3           # TSTR-002 overstayed two separate nights
    assert ee_kpis["overstays"] == 2        # the Entry/Exit card still counts cars
    assert sum(i["source"] == "overstay" for i in _items(client, url, **span)) == 3


def test_search_by_plate(client, url):
    kpis = _kpis(client, url, search="TSTR-001")
    assert kpis["overstays"] == 1
    assert kpis["total_violations"] == 1
    assert [i["plate_number"] for i in _items(client, url, search="TSTR-001")] == ["TSTR-001"]


@pytest.mark.parametrize("plate", ["TSTR-002", "002-TSTR", "TSTR 002"])
def test_plate_number_filter_any_order(client, url, plate):
    kpis = _kpis(client, url, plate_number=plate)
    assert (kpis["overstays"], kpis["no_parking"], kpis["other"]) == (1, 0, 0)
    assert [i["plate_number"] for i in _items(client, url, plate_number=plate)] == ["TSTR-002"]


def test_plate_number_filter_hits_alerts(client, url):
    kpis = _kpis(client, url, plate_number="TSTR-A2")
    assert (kpis["overstays"], kpis["no_parking"], kpis["other"]) == (0, 0, 1)
    assert _list(client, url, plate_number="TSTR-A2")["total_count"] == 1


def test_plate_number_combines_with_search(client, url):
    # search matches only TSTR-001's row; plate_number only TSTR-002's: nothing.
    assert _kpis(client, url, search="TSTR-001", plate_number="TSTR-002")["total_violations"] == 0


@pytest.mark.parametrize("types, expected", [
    (["overstay"], (2, 0, 0)),
    (["vehicle_violation"], (0, 2, 0)),
    (["vehicle_intrusion"], (0, 0, 1)),
    (["special_needs_violation", "overstay"], (2, 0, 1)),
])
def test_alert_type_filter(client, url, types, expected):
    kpis = _kpis(client, url, alert_type=types)
    assert (kpis["overstays"], kpis["no_parking"], kpis["other"]) == expected
    page = _list(client, url, alert_type=types)
    assert page["total_count"] == kpis["total_violations"] == sum(expected)
    assert {i["violation_type"] for i in page["items"]} == set(types)


def test_alert_type_and_plate_together(client, url):
    assert _list(client, url, alert_type="overstay", plate_number="TSTR-A0")["total_count"] == 0
    assert _list(client, url, alert_type="vehicle_violation", plate_number="TSTR-A0")["total_count"] == 1


@pytest.mark.parametrize("bad", ["unknown_vehicle", "capacity_exceeded", "nope"])
def test_alert_type_rejects_non_violations(client, url, bad):
    assert client.get(url, params={**RANGE, "alert_type": bad}).status_code == 422


@pytest.mark.parametrize("suffix", ["", "/kpis"])
def test_reversed_range_is_400(client, url, suffix):
    assert client.get(url + suffix, params={"date_from": "2025-03-12", "date_to": DAY}).status_code == 400
