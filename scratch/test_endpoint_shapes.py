"""Endpoint shape tests — exercise every modified/new endpoint via FastAPI's
TestClient with a SQL-pattern-driven mock session. Confirms:
  - routes are registered
  - response_model accepts the data we produce
  - new fields (parked_vehicles, is_monitored, monitored_capacity, etc.)
    appear in responses
  - enum query params return 422 on bad input
  - VehicleCreate format validators reject malformed payloads

Run from project root:
    PYTHONPATH=. .venv/bin/python scratch/test_endpoint_shapes.py
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any


# ---------------------------------------------------------------------------
# Mock session — answers db.execute() by regex-matching the SQL.
# ---------------------------------------------------------------------------
class MockResult:
    def __init__(self, data: Any):
        self._data = data

    def scalar(self):
        d = self._data
        if d is None:
            return None
        if isinstance(d, list):
            if not d:
                return None
            first = d[0]
            return list(first.values())[0] if isinstance(first, dict) else first
        return d

    def keys(self):
        d = self._data
        if isinstance(d, list) and d and isinstance(d[0], dict):
            return list(d[0].keys())
        return []

    def fetchall(self):
        d = self._data
        if isinstance(d, list):
            return [tuple(r.values()) if isinstance(r, dict) else r for r in d]
        return []

    # Some SQLAlchemy 2.0 paths call .rowcount on DML; harmless default.
    rowcount = 0


class MockSession:
    """Routes db.execute() to whichever pattern's response matches the SQL.
    Patterns are tried in order; first match wins. Append a catch-all at the
    end of each test's pattern list.
    """
    def __init__(self, patterns: list[tuple[str, Any]] | None = None):
        self.patterns = []
        # Default: INFORMATION_SCHEMA probes always return 1 (= exists).
        self.set_patterns(patterns or [])

    def set_patterns(self, patterns: list[tuple[str, Any]]):
        base = [
            # Defaults applied before caller-supplied patterns.
            (r"INFORMATION_SCHEMA\.TABLES",  1),
            (r"INFORMATION_SCHEMA\.COLUMNS", 1),
        ]
        self.patterns = [(re.compile(p, re.DOTALL | re.IGNORECASE), r) for p, r in (patterns + base)]

    def execute(self, sql_obj, params=None):
        sql = str(sql_obj)
        for rx, response in self.patterns:
            if rx.search(sql):
                return MockResult(response)
        return MockResult([])

    def commit(self): pass
    def rollback(self): pass
    def close(self): pass


# ---------------------------------------------------------------------------
# Patch SessionLocal in the two modules that open their own sessions
# (`_helpers._floor_schema` and `alerts._alerts_extra_cols`), then pre-warm
# their lru_caches. After this, no further direct DB connections happen.
# ---------------------------------------------------------------------------
import app.database as db_module
import app.routers._helpers as helpers_mod

_probe_session = MockSession([])  # only the INFORMATION_SCHEMA defaults
helpers_mod.SessionLocal = lambda: _probe_session
db_module.SessionLocal = lambda: _probe_session

helpers_mod._floor_schema.cache_clear()
helpers_mod._floor_schema()  # populate cache

# alerts also caches its own probe — clear + pre-warm.
from app.routers.alerts import _alerts_extra_cols
_alerts_extra_cols.cache_clear()
_alerts_extra_cols()

# Now safe to import the app — every subsequent request will hit our override.
from fastapi.testclient import TestClient
from app.database import get_db
from app.main import app


# ---------------------------------------------------------------------------
# DI wiring
# ---------------------------------------------------------------------------
def use_db(patterns: list[tuple[str, Any]]) -> MockSession:
    sess = MockSession(patterns)
    def _get_db():
        try:
            yield sess
        finally:
            pass
    app.dependency_overrides[get_db] = _get_db
    return sess


def clear_db():
    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Pretty-printing
# ---------------------------------------------------------------------------
PASS, FAIL, INFO = "\033[32mPASS\033[0m", "\033[31mFAIL\033[0m", "\033[36mINFO\033[0m"
passes, fails = 0, 0


def check(name: str, ok: bool, detail: str = ""):
    global passes, fails
    tag = PASS if ok else FAIL
    if ok:
        passes += 1
    else:
        fails += 1
    print(f"  {tag}  {name}" + (f"  — {detail}" if detail else ""))


def show(name: str, response):
    print(f"\n[{name}] HTTP {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False)[:1500])
    except Exception:
        print(response.text[:500])


client = TestClient(app)


# ===========================================================================
# Test 1 — GET /dashboard/kpis
# parked_vehicles = open_sessions(7) + ground_occupied(2) = 9
# ===========================================================================
print("=" * 72)
print("Test 1 — GET /dashboard/kpis (new parked_vehicles field)")
print("=" * 72)
use_db([
    # Order: specific → general. First match wins.
    (r"FROM parking_sessions WHERE status = 'open'",          7),    # open sessions
    (r"UPPER\(ss\.status\) NOT IN",                           5),    # dashboard occupied (slot_status)
    (r"severity='critical'",                                  3),    # critical alerts
    # Catch-all for the total_slots COUNT
    (r"COUNT\(\*\) FROM parking_slots\s+WHERE is_violation_zone = 0", 30),
])
r = client.get("/dashboard/kpis")
show("/dashboard/kpis", r)
check("status 200", r.status_code == 200)
if r.status_code == 200:
    body = r.json()
    check("has total_slots (G1)", "total_slots" in body)
    check("total_slots == 30", body.get("total_slots") == 30,
          f"got {body.get('total_slots')}")
    check("has parked_vehicles", "parked_vehicles" in body)
    check("parked_vehicles == 7 (open sessions only)", body.get("parked_vehicles") == 7,
          f"got {body.get('parked_vehicles')}")
    check("has occupied_slots", "occupied_slots" in body)
    check("has critical_alerts", "critical_alerts" in body)
    check("critical_alerts == 3", body.get("critical_alerts") == 3)
clear_db()


# ===========================================================================
# Test 2 — GET /occupancy/kpis (monitored_slots / unmonitored_slots)
# ===========================================================================
print()
print("=" * 72)
print("Test 2 — GET /occupancy/kpis")
print("=" * 72)
use_db([
    # Order: slot_status (occupied query) BEFORE is_monitored — the occupied
    # query also contains `is_monitored = 1`, so it has to be matched on a
    # more specific marker first.
    (r"FROM parking_sessions WHERE status = 'open'",                  7),    # open sessions
    (r"slot_status",                                                  5),    # occupied (slot_status join)
    (r"is_monitored = 1",                                             28),   # monitored count
    (r"COUNT\(\*\) FROM parking_slots\s+WHERE is_violation_zone = 0", 30),   # total (catch-all)
])
r = client.get("/occupancy/kpis")
show("/occupancy/kpis", r)
check("status 200", r.status_code == 200)
if r.status_code == 200:
    body = r.json()
    check("has monitored_slots", "monitored_slots" in body)
    check("has unmonitored_slots", "unmonitored_slots" in body)
    check("total_slots == 30", body.get("total_slots") == 30)
    check("available_slots == monitored - occupied (28 - 5 = 23)",
          body.get("available_slots") == 23,
          f"got {body.get('available_slots')}")
    check("coverage_note is present", isinstance(body.get("coverage_note"), str)
          and len(body["coverage_note"]) > 0)
    check("slot_occupied_spots dropped", "slot_occupied_spots" not in body)
    check("monitored_slots == 28", body.get("monitored_slots") == 28)
    check("unmonitored_slots == 2", body.get("unmonitored_slots") == 2)
    check("total_vehicles == 7 (open sessions only)", body.get("total_vehicles") == 7)
clear_db()


# ===========================================================================
# Test 3 — GET /occupancy/totals (uses same helper)
# ===========================================================================
print()
print("=" * 72)
print("Test 3 — GET /occupancy/totals (total_vehicles uses helper)")
print("=" * 72)
use_db([
    (r"FROM parking_sessions WHERE status = 'open'",                  7),
    (r"slot_status",                                                  5),    # occupied
    (r"is_monitored = 1",                                             28),   # monitored_total
    (r"COUNT\(\*\) FROM parking_slots\s+WHERE is_violation_zone = 0", 30),
])
r = client.get("/occupancy/totals")
show("/occupancy/totals", r)
check("status 200", r.status_code == 200)
if r.status_code == 200:
    body = r.json()
    check("total_vehicles == 7 (open sessions only)", body.get("total_vehicles") == 7,
          f"got {body.get('total_vehicles')}")
    check("total_slots == 30", body.get("total_slots") == 30)
    check("available_slots == monitored - occupied (28 - 5 = 23)",
          body.get("available_slots") == 23,
          f"got {body.get('available_slots')}")


clear_db()


# ===========================================================================
# Test 3b — GET /occupancy/floors — FloorOccupancy.monitored_capacity / unmonitored_count
# ===========================================================================
print()
print("=" * 72)
print("Test 3b — GET /occupancy/floors (monitored_capacity per floor)")
print("=" * 72)
# Per-floor slot-status rows for slot_occupancy_count
slot_rows_floor = [
    {"slot_id": "B1_001", "status": "OCCUPIED"},
    {"slot_id": "B1_002", "status": "OCCUPIED"},
    {"slot_id": "B1_003", "status": "VACANT"},
]
use_db([
    # Order: slot_rows query has `is_monitored = 1` too (in the WHERE), so its
    # SELECT-shape pattern must come BEFORE the is_monitored count regex.
    (r"SELECT DISTINCT.*FROM dbo\.floors|SELECT.*name.*FROM dbo\.floors|FROM floors", [{"name": "B1", "id": 2}]),
    (r"SELECT pk\.slot_id, ss\.status",                                                  slot_rows_floor),
    (r"is_monitored = 1",                                                                14),  # monitored_capacity
    (r"COUNT\(\*\) FROM parking_slots WHERE floor_id = :fid AND is_violation_zone = 0", 15),  # max_capacity (catch-all)
    (r"zone_occupancy",                                                                  []),
])
r = client.get("/occupancy/floors?page=1&page_size=10")
check("status 200", r.status_code == 200)
if r.status_code == 200:
    items = r.json()["items"]
    check("returned at least 1 floor", len(items) >= 1)
    if items:
        first = items[0]
        check("has monitored_capacity", "monitored_capacity" in first)
        check("has unmonitored_count", "unmonitored_count" in first)
        check("monitored_capacity == 14", first.get("monitored_capacity") == 14)
        check("unmonitored_count == 1 (15 - 14)", first.get("unmonitored_count") == 1)
        # G2: per-floor available is now monitored_capacity − current_count.
        # slot_rows_floor has 2 OCCUPIED + 1 VACANT, so current_count = 2.
        # available = 14 − 2 = 12 (previously would have been 15 − 2 = 13).
        check("available == monitored - current (14 - 2 = 12)",
              first.get("available") == 12,
              f"got {first.get('available')}")
        check("has coverage_note", isinstance(first.get("coverage_note"), str)
              and len(first["coverage_note"]) > 0)
        print(f"  {INFO}  floor sample: floor={first.get('floor')!r}, "
              f"max={first.get('max_capacity')}, mon={first.get('monitored_capacity')}, "
              f"unmon={first.get('unmonitored_count')}, "
              f"available={first.get('available')}, "
              f"slots_occupied={first.get('slots_occupied')}")
clear_db()


# ===========================================================================
# Test 3c — GET /occupancy/floors/{floor} — single FloorOccupancy
# ===========================================================================
print()
print("=" * 72)
print("Test 3c — GET /occupancy/floors/{floor}")
print("=" * 72)
use_db([
    (r"SELECT id FROM floors WHERE name = :n",       2),
    (r"SELECT name FROM floors WHERE id = :i",       "B1"),
    (r"SELECT pk\.slot_id, ss\.status",              slot_rows_floor),  # slot rows
    (r"is_monitored = 1",                            14),                # monitored_capacity
    (r"COUNT\(\*\) FROM parking_slots WHERE floor_id = :fid AND is_violation_zone = 0", 15),
    (r"zone_occupancy",                              []),
])
r = client.get("/occupancy/floors/B1")
check("status 200", r.status_code == 200, f"body: {r.text[:200]}")
if r.status_code == 200:
    body = r.json()
    check("FloorOccupancy.floor == 'B1'", body.get("floor") == "B1")
    check("monitored_capacity in response", "monitored_capacity" in body)
    check("unmonitored_count in response", "unmonitored_count" in body)
clear_db()


# ===========================================================================
# Test 4 — GET /occupancy/slots — is_monitored on rows
# ===========================================================================
print()
print("=" * 72)
print("Test 4 — GET /occupancy/slots — is_monitored present on rows")
print("=" * 72)
slot_row = {
    "id": 1, "slot_id": "B1_001", "slot_name": "B1 Slot 1",
    "floor": "B1", "floor_id": 2, "is_available": 1, "is_violation_zone": 0,
    "is_monitored": 1, "has_active_violation": 0,
    "active_violation_type": None, "active_violation_severity": None,
    "reservation_type": "GENERAL", "reserved_for": None,
    "current_plate": None, "current_status": "VACANT", "status_updated_at": None,
}
blind_row = {**slot_row, "id": 2, "slot_id": "B1_BLIND",
             "slot_name": "Operator-entered blind row", "is_monitored": 0}
violated_row = {**slot_row, "id": 3, "slot_id": "B1_VIO",
                "slot_name": "Reserved slot under violation",
                "has_active_violation": 1,
                "active_violation_type": "named_slot_violation",
                "active_violation_severity": "critical"}

use_db([
    (r"COUNT\(\*\) FROM parking_slots ps",   3),
    (r"FROM parking_slots ps",               [slot_row, blind_row, violated_row]),
])
r = client.get("/occupancy/slots?page=1&page_size=10")
check("status 200", r.status_code == 200)
if r.status_code == 200:
    items = r.json()["items"]
    show("/occupancy/slots[0]", type("R", (), {"status_code": 200, "json": lambda self=None: items[0], "text": json.dumps(items[0])})())
    check("returns 3 items", len(items) == 3)
    if items:
        first = items[0]
        check("has is_monitored", "is_monitored" in first)
        check("is_monitored is bool", isinstance(first.get("is_monitored"), bool))
        check("monitored item == True", first.get("is_monitored") is True)
        check("has has_active_violation field", "has_active_violation" in first)
        check("has active_violation_type field", "active_violation_type" in first)
        check("monitored slot has_active_violation == False",
              first.get("has_active_violation") is False)
        check("monitored slot active_violation_type is null",
              first.get("active_violation_type") is None)
        if len(items) > 1:
            check("blind item is_monitored == False", items[1].get("is_monitored") is False)
            check("blind item active_violation_type is null",
                  items[1].get("active_violation_type") is None)
        check("has active_violation_severity field",
              "active_violation_severity" in first)
        check("monitored slot active_violation_severity is null",
              first.get("active_violation_severity") is None)
        if len(items) > 2:
            v = items[2]
            check("violated item has_active_violation == True",
                  v.get("has_active_violation") is True)
            check("violated item active_violation_type == 'named_slot_violation'",
                  v.get("active_violation_type") == "named_slot_violation")
            check("violated item active_violation_severity == 'critical'",
                  v.get("active_violation_severity") == "critical")
            # Contract: bool true iff type non-null, severity non-null iff bool true.
            check("violated row contract holds (bool ↔ type)",
                  v.get("has_active_violation") is (v.get("active_violation_type") is not None))
clear_db()


# ===========================================================================
# Test 5 — GET /occupancy/slots/{id} — SlotDetail returns is_monitored
# ===========================================================================
print()
print("=" * 72)
print("Test 5 — GET /occupancy/slots/{id} — SlotDetail.is_monitored")
print("=" * 72)
detail_row = {**slot_row, "is_violation_slot": 0, "polygon": '[[0,0],[1,0],[1,1],[0,1]]'}
use_db([
    (r"FROM parking_slots pk\s+LEFT JOIN slot_status",   [detail_row]),
    (r"FROM parking_sessions ps\s+WHERE",                []),
])
r = client.get("/occupancy/slots/B1_001")
check("status 200", r.status_code == 200,
      f"body: {r.text[:300]}" if r.status_code != 200 else "")
if r.status_code == 200:
    body = r.json()
    check("has is_monitored", "is_monitored" in body)
    check("is_monitored == True", body.get("is_monitored") is True)
    check("has has_active_violation", "has_active_violation" in body)
    check("has active_violation_type", "active_violation_type" in body)
    check("has_active_violation == False (mock)",
          body.get("has_active_violation") is False)
    check("active_violation_type is null (mock)",
          body.get("active_violation_type") is None)
    # Contract holds on detail too.
    check("detail contract: bool == (type is not None)",
          body.get("has_active_violation") is (body.get("active_violation_type") is not None))
    print(f"  {INFO}  slot detail keys: {sorted(body.keys())}")
clear_db()

# Detail for the violated slot — flag true + named type
use_db([
    (r"FROM parking_slots pk\s+LEFT JOIN slot_status", [{**violated_row, "is_violation_slot": 0, "polygon": None}]),
    (r"FROM parking_sessions ps\s+WHERE",              []),
])
r = client.get("/occupancy/slots/B1_VIO")
check("violated detail → 200", r.status_code == 200,
      f"body: {r.text[:200]}" if r.status_code != 200 else "")
if r.status_code == 200:
    body = r.json()
    check("violated detail has_active_violation == True",
          body.get("has_active_violation") is True)
    check("violated detail active_violation_type == 'named_slot_violation'",
          body.get("active_violation_type") == "named_slot_violation")
    check("violated detail active_violation_severity == 'critical'",
          body.get("active_violation_severity") == "critical")
clear_db()

# Contract enforcement: even if a mock supplies an inconsistent triple (bool
# True, type None, severity set), the model_validator must clamp both the
# bool to False AND the severity to null.
print()
print("Test 5e — model contract enforces bool ↔ type ↔ severity sync")
print("=" * 72)
inconsistent_row = {**slot_row,
                    "has_active_violation": 1,
                    "active_violation_type": None,
                    "active_violation_severity": "critical"}  # straggling severity
use_db([
    (r"COUNT\(\*\) FROM parking_slots ps", 1),
    (r"FROM parking_slots ps",             [inconsistent_row]),
])
r = client.get("/occupancy/slots?page=1&page_size=10")
check("status 200", r.status_code == 200)
if r.status_code == 200:
    item = r.json()["items"][0]
    check("validator clamps bool to False when type is null",
          item.get("has_active_violation") is False,
          f"got {item.get('has_active_violation')}")
    check("validator clears severity when type is null",
          item.get("active_violation_severity") is None,
          f"got {item.get('active_violation_severity')!r}")
clear_db()


# ===========================================================================
# Test 5b — GET /occupancy/slots/by-floor — is_monitored per row, grouped
# ===========================================================================
print()
print("=" * 72)
print("Test 5b — GET /occupancy/slots/by-floor")
print("=" * 72)
use_db([
    (r"FROM parking_slots pk\s+LEFT JOIN slot_status", [slot_row, blind_row]),
])
r = client.get("/occupancy/slots/by-floor")
check("status 200", r.status_code == 200, f"body: {r.text[:200]}")
if r.status_code == 200:
    groups = r.json()
    check("returns a list", isinstance(groups, list))
    if groups and groups[0].get("slots"):
        first_slot = groups[0]["slots"][0]
        check("group.slots[0] has is_monitored", "is_monitored" in first_slot)
        print(f"  {INFO}  groups: {[(g['floor'], len(g['slots'])) for g in groups]}")
clear_db()


# ===========================================================================
# Test 5c — GET /occupancy/slots?is_monitored=false — filter applied
# ===========================================================================
print()
print("=" * 72)
print("Test 5c — GET /occupancy/slots?is_monitored=false")
print("=" * 72)
use_db([
    (r"COUNT\(\*\) FROM parking_slots ps",   1),
    (r"FROM parking_slots ps",               [blind_row]),
])
r = client.get("/occupancy/slots?is_monitored=false")
check("status 200", r.status_code == 200)
if r.status_code == 200:
    items = r.json()["items"]
    check("returned 1 item", len(items) == 1)
    if items:
        check("filtered item is blind", items[0].get("is_monitored") is False)
clear_db()


# ===========================================================================
# Test 6 — Enum query-param validation
# ===========================================================================
print()
print("=" * 72)
print("Test 6 — Enum query-param validation (typos → 422)")
print("=" * 72)
use_db([(r".*", 0)])

cases = [
    ("/alerts/?severity=lol",                        "severity"),
    ("/alerts/?alert_type=nope",                     "alert_type"),
    ("/cameras/?role=ghost",                         "role"),
    ("/entry-exit/?status=imaginary",                "status"),
    ("/entry-exit/by-vehicle/1?direction=sideways",  "direction"),
    ("/occupancy/slots?reservation_type=BOGUS",      "reservation_type"),
]
for url, field in cases:
    r = client.get(url)
    ok = r.status_code == 422
    check(f"{url} → 422", ok, f"got {r.status_code}")
    if ok:
        msg = json.dumps(r.json(), ensure_ascii=False)
        check(f"  error names '{field}'", field in msg)

# Happy enum value
r = client.get("/alerts/?severity=critical&page=1&page_size=5")
check("/alerts/?severity=critical → not 422", r.status_code != 422,
      f"got {r.status_code}")
clear_db()


# ===========================================================================
# Test 6b — Enum happy paths (valid values → not 422)
# ===========================================================================
print()
print("=" * 72)
print("Test 6b — Enum happy paths (every accepted value)")
print("=" * 72)
use_db([(r".*", 0)])

happy = [
    ("/alerts/?severity=critical",         "AlertSeverity.critical"),
    ("/alerts/?severity=warning",          "AlertSeverity.warning"),
    ("/alerts/?severity=info",             "AlertSeverity.info"),
    ("/alerts/?alert_type=intrusion",      "AlertType.intrusion"),
    ("/alerts/?alert_type=overstay",       "AlertType.overstay"),
    ("/cameras/?role=entry",               "CameraRole.entry"),
    ("/cameras/?role=floor_counting",      "CameraRole.floor_counting"),
    ("/entry-exit/?status=open",           "ParkingSessionStatus.open"),
    ("/entry-exit/?status=closed",         "ParkingSessionStatus.closed"),
    ("/entry-exit/?status=overstay",       "ParkingSessionStatus.overstay"),
    ("/entry-exit/by-vehicle/1?direction=entry", "EntryExitDirection.entry"),
    ("/entry-exit/by-vehicle/1?direction=exit",  "EntryExitDirection.exit"),
    ("/occupancy/slots?reservation_type=GENERAL",  "ReservationType.GENERAL"),
    ("/occupancy/slots?reservation_type=SPECIAL",  "ReservationType.SPECIAL"),
    ("/occupancy/slots?reservation_type=EMPLOYEE", "ReservationType.EMPLOYEE"),
]
for url, label in happy:
    r = client.get(url)
    check(f"{label} → not 422", r.status_code != 422, f"got {r.status_code}")
clear_db()


# ===========================================================================
# Test 7 — VehicleCreate validators (422 + plate strip)
# ===========================================================================
print()
print("=" * 72)
print("Test 7 — POST /vehicles/ format validators")
print("=" * 72)
use_db([(r".*", 0)])

invalid = [
    ("plate too short",       {"plate_number": "A"}),
    ("plate too long",        {"plate_number": "X" * 25}),
    ("plate empty",           {"plate_number": ""}),
    ("bad email",             {"plate_number": "ABC 123", "email": "not-an-email"}),
    ("bad phone (letters)",   {"plate_number": "ABC 123", "phone": "abc"}),
    ("bad phone (too short)", {"plate_number": "ABC 123", "phone": "12"}),
]
for name, payload in invalid:
    r = client.post("/vehicles/", json=payload)
    check(f"{name} → 422", r.status_code == 422, f"got {r.status_code}")

# G4: is_employee=true without employee_id is now allowed (cross-validator dropped).
# Mock the DB path that POST /vehicles takes for a new-plate insert.
use_db([
    (r"SELECT TOP 1 id, notes\s+FROM vehicles\s+WHERE plate_number = :plate", []),  # no existing
    (r"INSERT INTO vehicles",                                                  1),
    (r"SELECT id FROM vehicles WHERE plate_number = :p",                       42),
    # _fetch_vehicle_list_item (post-insert read-back)
    (r"FROM vehicles v",  [{
        "id": 42, "plate_number": "ABC 123", "owner_name": None, "vehicle_type": None,
        "employee_id": None, "title": None, "is_registered": 1, "registered_at": None,
        "notes": None, "is_employee": 1, "phone": None, "email": None,
        "current_slot_id": None, "current_slot_name": None,
        "parked_at": None, "parking_status": None, "floor": None, "floor_id": None,
    }]),
])
r = client.post("/vehicles/", json={"plate_number": "ABC 123", "is_employee": True})
check("employee without id → not 422 (validator dropped)",
      r.status_code != 422, f"got {r.status_code}")
clear_db()
use_db([(r".*", 0)])

# Show one error body for clarity
r = client.post("/vehicles/", json={"plate_number": "ABC 123", "email": "bad"})
if r.status_code == 422:
    err = r.json()["detail"][0]
    print(f"  {INFO}  sample error: {json.dumps(err, ensure_ascii=False)[:200]}")

clear_db()


# ===========================================================================
# Test 5d — is_monitored is strict boolean (rejects "1"/"0"/"yes")
# ===========================================================================
print()
print("=" * 72)
print("Test 5d — ?is_monitored= strict (only 'true'/'false')")
print("=" * 72)
use_db([
    (r"COUNT\(\*\) FROM parking_slots ps",   1),
    (r"FROM parking_slots ps",               [slot_row]),
])
# Happy paths
for v in ("true", "false", "True", "False", "TRUE", "FALSE"):
    r = client.get(f"/occupancy/slots?is_monitored={v}")
    check(f"?is_monitored={v} → not 422", r.status_code != 422,
          f"got {r.status_code}")
# Rejected
for v in ("1", "0", "yes", "no", "on", "off", "y", "n"):
    r = client.get(f"/occupancy/slots?is_monitored={v}")
    check(f"?is_monitored={v} → 422", r.status_code == 422,
          f"got {r.status_code}")
clear_db()


# ===========================================================================
# Test 8 — GET /vehicles/by-plate/{plate_number}
# ===========================================================================
print()
print("=" * 72)
print("Test 8 — GET /vehicles/by-plate/{plate_number}")
print("=" * 72)
vehicle_row = {
    "id": 42,
    "plate_number": "ABC 123",
    "owner_name": "Ali",
    "vehicle_type": "Sedan",
    "employee_id": "E001",
    "title": "Mr.",
    "is_registered": 1,
    "registered_at": None,
    "notes": None,
    "is_employee": 1,
    "phone": "+966501234567",
    "email": "ali@example.com",
    "current_slot_id": "B1_001",
    "current_slot_name": "B1 Slot 1",
}

use_db([
    (r"v\.plate_number = :plate",                            [vehicle_row]),
    (r"COUNT\(\*\) FROM parking_sessions ps WHERE ps\.plate_number = :plate",  3),
    (r"FROM parking_sessions ps\s+LEFT JOIN parking_slots", []),
])
r = client.get("/vehicles/by-plate/ABC%20123")
show("/vehicles/by-plate/ABC 123", r)
check("status 200", r.status_code == 200)
if r.status_code == 200:
    body = r.json()
    check("plate_number echoes input", body.get("plate_number") == "ABC 123")
    check("owner_name == 'Ali'", body.get("owner_name") == "Ali")
    check("is_employee is bool", isinstance(body.get("is_employee"), bool))
    check("is_currently_parked == False (no open session)", body.get("is_currently_parked") is False)
    check("events_total == 3", body.get("events_total") == 3)
clear_db()

# Unregistered row in vehicles (is_registered=false but has an id) — should
# still return 200 with the row's id intact, so PUT/DELETE remain usable.
print()
print("Test 8 (cont.) — unregistered row (is_registered=false) returns id")
unreg_row = {**vehicle_row, "id": 99, "plate_number": "B 555", "is_registered": 0}
use_db([
    (r"v\.plate_number = :plate",                                              [unreg_row]),
    (r"COUNT\(\*\) FROM parking_sessions ps WHERE ps\.plate_number = :plate",  1),
    (r"FROM parking_sessions ps\s+LEFT JOIN parking_slots",                    []),
])
r = client.get("/vehicles/by-plate/B%20555")
check("unregistered row → 200", r.status_code == 200,
      f"got {r.status_code}: {r.text[:200]}")
if r.status_code == 200:
    body = r.json()
    check("id is present (not null)", body.get("id") == 99)
    check("is_registered == False", body.get("is_registered") is False)
clear_db()


# 404 path: no row in vehicles at all (parking_sessions presence is irrelevant)
print()
print("Test 8 (cont.) — 404 when no row in vehicles table")
use_db([
    (r"v\.plate_number = :plate", []),  # not in vehicles
])
r = client.get("/vehicles/by-plate/GHOST")
check("no vehicles row → 404", r.status_code == 404,
      f"got {r.status_code}: {r.text[:120]}")
clear_db()

# Path validators (min/max length)
r = client.get("/vehicles/by-plate/A")
check("plate too short → 422", r.status_code == 422)

r = client.get(f"/vehicles/by-plate/{'X' * 25}")
check("plate too long → 422", r.status_code == 422)


# ===========================================================================
# Test 7b — PUT /vehicles/{id} — same validators apply
# ===========================================================================
print()
print("=" * 72)
print("Test 7b — PUT /vehicles/{id} validators")
print("=" * 72)
use_db([
    # Make the "lookup existing vehicle" path return SOMETHING reasonable
    # for the few requests that get past validation, but we mostly want 422s.
    (r".*", 0),
])

put_invalid = [
    ("bad plate",   {"plate_number": "A"}),
    ("bad email",   {"email": "not-an-email"}),
    ("bad phone",   {"phone": "abc"}),
]
for name, payload in put_invalid:
    r = client.put("/vehicles/1", json=payload)
    check(f"PUT {name} → 422", r.status_code == 422, f"got {r.status_code}")
clear_db()


# ===========================================================================
# Summary
# ===========================================================================
print()
print("=" * 72)
print(f"SUMMARY: {passes} passed, {fails} failed")
print("=" * 72)
sys.exit(0 if fails == 0 else 1)
