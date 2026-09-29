"""GET /alerts/reports/overstay-violations — Total Violations = overstays + alerts.

Runs against the database in .env. Inserts marker rows on empty PAST days
(March 2025 — an overstay only counts up to today's midnight, so future days
never would) and deletes them afterwards.

    pytest tests/test_alert_report_summary.py -v -p no:cacheprovider
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
    # alert_type, triggered_at, is_resolved
    ("unknown_vehicle", f"{DAY} 09:00:00", 0),
    ("unknown_vehicle", f"{DAY} 10:00:00", 1),       # resolved still counts
    ("vehicle_intrusion", f"{DAY} 11:00:00", 1),
    ("overstay", f"{DAY} 12:00:00", 0),              # a stray row must not double the slice
    ("unknown_vehicle", "2025-03-12 09:00:00", 0),   # outside the range
]
SESSIONS = [
    # plate, entry, exit — inside at 00:00 on DAY = overstay for DAY
    ("TSTR-001", "2025-03-10 20:00:00", f"{DAY} 08:00:00"),   # overstay
    ("TSTR-002", "2025-03-10 21:00:00", f"{DAY} 07:00:00"),   # overstay
    ("TSTR-002", "2025-03-09 21:00:00", "2025-03-10 07:00:00"),  # same car, other day
    ("TSTR-003", f"{DAY} 08:00:00", f"{DAY} 17:00:00"),       # same-day visit, no overstay
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
                                    resolved_at, severity, is_test)
                OUTPUT INSERTED.id
                VALUES (:a, 'CAM-TEST', :p, :t, :r, CASE WHEN :r = 1 THEN :t END, 'high', 0)
            """), {"a": atype, "p": f"TSTR-A{i}", "t": at, "r": res}).scalar())
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


def _slices(body):
    return {i["alert_type"]: i for i in body["by_type"]}


def test_counts_resolved_alerts_and_overstays(client, url):
    r = client.get(url, params=RANGE)
    assert r.status_code == 200, r.text
    body = r.json()
    s = _slices(body)
    assert s["unknown_vehicle"]["count"] == 2           # open + resolved
    assert s["vehicle_intrusion"]["count"] == 1
    assert body["alerts_total"] == 3                    # stray "overstay" alert excluded
    assert body["overstays"] == 2                       # distinct cars, not visits
    assert body["total_violations"] == 5


def test_overstay_is_not_an_alert_slice(client, url):
    body = client.get(url, params=RANGE).json()
    assert "overstay" not in _slices(body)
    assert sum(i["count"] for i in body["by_type"]) == body["alerts_total"]


def test_matches_entry_exit_overstays_card(client, url):
    from app.routers.entry_exit import prefix as ee
    report = client.get(url, params=RANGE).json()
    kpis = client.get(ee + "/kpis", params=RANGE).json()
    assert report["overstays"] == kpis["overstays"]


def test_summary_endpoint_unchanged(client):
    from app.routers.alerts import prefix
    body = client.get(prefix + "/summary", params=RANGE).json()
    s = {i["alert_type"]: i["count"] for i in body["by_type"]}
    assert s.get("unknown_vehicle") == 1                # /summary still defaults to open only
    assert client.get(prefix + "/report-summary").status_code in (404, 422)   # removed


def test_severity_filters_alerts_only(client, url):
    low = client.get(url, params={**RANGE, "severity": "low"}).json()
    assert low["alerts_total"] == 0
    assert low["overstays"] == 2                        # overstay has no severity
    high = client.get(url, params={**RANGE, "severity": "high"}).json()
    assert high["alerts_total"] == 3


def test_search_by_plate(client, url):
    body = client.get(url, params={**RANGE, "search": "TSTR-001"}).json()
    assert body["overstays"] == 1


def test_reversed_range_is_400(client, url):
    assert client.get(url, params={"date_from": "2025-03-12", "date_to": DAY}).status_code == 400
