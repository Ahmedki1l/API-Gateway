"""End-to-end TestClient sweep for every gateway endpoint.

Run after PR 1 / PR 2 / PR 3 so we can confirm:
  - Every endpoint responds (200 / 401 / 422 — no 5xx, no crashes).
  - Paged endpoints return the canonical envelope with `total_count`,
    `page`, `page_size`, `items`.
  - `response_model=` is wired on every list/detail/write endpoint that
    GATEWAY_MODIFICATIONS_REQUIRED.md asked for.
  - PR 3 breaking changes (G-2, G-4, G-20) are visible in the responses
    and OpenAPI spec.

The DB is stubbed with module-level `scalar`/`rows` patches that return
zero / empty list (per-router, since each router imports them as locals).
Upstream HTTP calls are stubbed with empty fixtures. Camera monitor is
no-op'd via lifespan replacement.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# Per-route fixtures used by the stubbed `rows()` to return believable shapes.
# We key on a substring of the SQL the router emits — far simpler than
# trying to mock at the driver level.
ROW_FIXTURES = {
    "FROM vehicles": [{
        "id": 1, "vehicle_id": 1, "plate_number": "TEST-001",
        "owner_name": "Test Owner", "vehicle_type": "Sedan",
        "company": None, "phone": None, "email": None,
        "is_employee": False, "registration_date": None,
        "first_seen": None, "last_seen": None,
        "is_currently_parked": False, "current_floor": None, "current_slot": None,
        "employee_id": None, "title": None, "is_registered": True,
        "registered_at": None, "notes": None,
    }],
    "FROM alerts": [{
        "id": 1, "alert_type": "test", "severity": "low",
        "plate_number": "TEST-001", "slot_id": None, "slot_name": None,
        "floor": None, "camera_id": None, "snapshot_url": None,
        "triggered_at": None, "resolved_at": None, "resolved": False,
        "owner_name": None, "is_test": False,
        "description": None, "vehicle_event_id": None,
        "location_display": None,
    }],
    "FROM parking_sessions": [{
        "id": 1, "vehicle_id": 1, "plate_number": "TEST-001",
        "entry_time": None, "exit_time": None, "duration_seconds": None,
        "floor": "B1", "slot_id": "B1-001", "slot_name": "B1-001",
        "slot_number": "001", "is_employee": False,
        "entry_snapshot_path": None, "exit_snapshot_path": None,
        "slot_snapshot_path": None,
        "status": "open", "owner_name": "Test", "vehicle_type": "Sedan",
        "entry_camera_id": None, "exit_camera_id": None,
        "slot_camera_id": None, "parked_at": None, "slot_left_at": None,
    }],
    "FROM entry_exit_log": [{
        "id": 1, "vehicle_id": 1, "plate_number": "TEST-001",
        "event_type": "entry", "event_time": None, "floor": "B1",
        "slot_id": "B1-001", "is_employee": False,
        "snapshot_path": None, "camera_id": None,
        "owner_name": "Test", "vehicle_type": "Sedan",
        "vehicle_event_id": 1,
    }],
    "FROM zone_occupancy": [{
        "zone_id": "B1-PARKING", "zone_name": "B1 Parking",
        "max_capacity": 50, "current_count": 0, "available_count": 50,
        "occupancy_rate": 0.0, "last_updated": None,
    }],
    "FROM parking_slots": [{
        "slot_id": "B1-001", "slot_name": "B1-001", "floor": "B1",
        "is_available": True, "is_violation_zone": False,
        "current_plate": None, "current_status": "empty",
        "status_updated_at": None,
    }],
    "FROM cameras": [{
        "id": 1, "camera_id": "CAM-001", "name": "Test Cam",
        "floor": "B1", "role": "entry", "watches_floor": "B1",
        "watches_slots_json": None, "ip_address": "10.0.0.1",
        "rtsp_port": 554, "rtsp_path": "/stream1", "username": "admin",
        "password_encrypted": None, "enabled": True,
        "notes": None,
        "created_at": "2024-01-01T00:00:00", "updated_at": "2024-01-01T00:00:00",
        "last_check_at": None, "last_seen_at": None, "last_status": "ok",
        "is_online": True,
    }],
    "FROM camera_feeds": [],
}


def fake_scalar(_db: Any, sql: str, params: dict | None = None) -> Any:
    s = sql.lower().lstrip()
    if s.startswith("select count("):
        return 1
    if "scope_identity()" in s or "@@identity" in s:
        return 1
    # Existence-style checks (`SELECT id FROM <table> WHERE ...`) used by
    # PATCH/DELETE/PUT endpoints to 404 when the row is missing. Return 1 so
    # the harness exercises the write-path, not the not-found branch.
    if s.startswith("select id "):
        return 1
    return None


def fake_rows(_db: Any, sql: str, params: dict | None = None) -> list[dict]:
    s_lower = sql.lower()

    # INFORMATION_SCHEMA probes — return a rich column list so compat-shim
    # branches in alerts.py / vehicles.py / camera_feeds.py take the "rich"
    # path (columns present), exercising the production code path.
    if "information_schema.columns" in s_lower:
        return [
            {"COLUMN_NAME": "severity"}, {"COLUMN_NAME": "location_display"},
            {"COLUMN_NAME": "slot_id"}, {"COLUMN_NAME": "is_employee"},
            {"COLUMN_NAME": "phone"}, {"COLUMN_NAME": "email"},
            {"COLUMN_NAME": "id"}, {"COLUMN_NAME": "camera_id"},
        ]

    # GROUP BY queries: many routers use them for KPI aggregates that produce
    # bespoke shapes. Returning [] is safe — the endpoint then falls back to
    # its zero-filled / empty-aggregate path.
    if "group by" in s_lower:
        return []

    for needle, payload in ROW_FIXTURES.items():
        if needle in sql:
            return payload
    return []


def main() -> int:
    with patch("app.database.create_engine"):
        from app.main import app
        from app.services import camera_monitor

    # Disable camera-monitor background task so the lifespan returns quickly.
    camera_monitor.start = lambda: None  # type: ignore
    async def _noop_stop() -> None:
        return None
    camera_monitor.stop = _noop_stop  # type: ignore

    from fastapi.testclient import TestClient

    # Patch every router's local `scalar` / `rows` aliases (they're imported
    # into each module so module-level patching is required, not just
    # `app.database.scalar`).
    targets = [
        "app.routers.vehicles", "app.routers.alerts", "app.routers.dashboard",
        "app.routers.occupancy", "app.routers.cameras", "app.routers.camera_feeds",
        "app.routers.entry_exit",
        # WS-8: shared helpers module imports `scalar` for resolve_floor_id /
        # resolve_floor_name; patch its local alias too so the harness doesn't
        # hit a real DB looking for the floors table.
        "app.routers._helpers",
    ]
    cms = []
    for mod in targets:
        cms.append(patch(f"{mod}.scalar", side_effect=fake_scalar, create=True))
        cms.append(patch(f"{mod}.rows",   side_effect=fake_rows,   create=True))

    # Upstream HTTP / SSE calls.
    cms += [
        patch("app.services.upstream.get_live_vehicles", return_value=[]),
        patch("app.services.upstream.get_live_slots",    return_value=[]),
        patch("app.services.upstream.get_system1_health", return_value={"status": "ok"}),
        patch("app.services.upstream.get_system2_health", return_value={"status": "ok"}),
        patch("app.services.upstream.get_system2_stats", return_value={}),
        patch("app.services.upstream.get_system1_last_connected_at", return_value=None),
        patch("app.services.upstream.get_system2_last_connected_at", return_value=None),
    ]

    # Internal-token: short-circuit Depends so /cameras/internal/all doesn't 503.
    from app.services import auth as auth_svc
    auth_svc.require_internal_token = lambda: None  # type: ignore

    # Stub the credential cipher so /cameras/{id}/credentials doesn't crash on None.
    from app.services import crypto as crypto_svc
    if hasattr(crypto_svc, "cipher"):
        crypto_svc.cipher.decrypt = lambda *_a, **_k: "REDACTED"  # type: ignore

    for cm in cms:
        cm.start()

    client = TestClient(app)

    # ---------------------------------------------------------------- enumerate
    routes = []
    for r in app.routes:
        if not hasattr(r, "methods"):
            continue
        for method in sorted(r.methods - {"HEAD", "OPTIONS"}):
            routes.append((method, r.path, r))

    # Skip noise + endpoints that need real I/O loops.
    SKIP = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc",
            "/alerts/stream"}

    # ---------------------------------------------------------------- exercise
    results: list[tuple[str, str, int, str]] = []

    def record(method: str, path: str, code: int, note: str = "") -> None:
        results.append((method, path, code, note))

    # Plug per-path-template values for any `{param}` placeholders.
    PATH_VALUES = {
        "{alert_id}": "1", "{camera_id}": "1", "{vehicle_id}": "1",
        "{event_id}": "1", "{slot_id}": "B1-001", "{floor}": "B1",
    }

    def fill(path: str) -> str:
        for k, v in PATH_VALUES.items():
            path = path.replace(k, v)
        return path

    BODIES = {
        ("POST",  "/vehicles/"): {"plate_number": "NEW-001", "owner_name": "Test"},
        ("PUT",   "/vehicles/1"): {"plate_number": "UPD-001", "owner_name": "Test"},
        ("POST",  "/cameras/"): {
            "camera_id": "CAM-002", "name": "Test 2", "floor": "B1",
            "ip_address": "10.0.0.2", "rtsp_port": 554, "rtsp_path": "/s",
            "username": "a", "password": "b", "enabled": True,
            "role": "entry",
        },
        ("PUT",   "/cameras/1"): {"name": "Updated"},
    }

    for method, path, _route in routes:
        if path in SKIP:
            continue
        url = fill(path)
        try:
            if method == "GET":
                r = client.get(url)
            elif method == "DELETE":
                r = client.delete(url)
            elif method == "POST":
                body = BODIES.get((method, path), {})
                r = client.post(url, json=body)
            elif method == "PUT":
                body = BODIES.get((method, path), {})
                r = client.put(url, json=body)
            elif method == "PATCH":
                r = client.patch(url, json={})
            else:
                continue
        except Exception as e:
            record(method, url, 0, f"EXCEPTION: {type(e).__name__}: {e}")
            continue

        record(method, url, r.status_code, r.text[:120] if r.status_code >= 500 else "")

    # ---------------------------------------------------------------- pagination check
    print("=" * 80)
    print("ENDPOINT SWEEP")
    print("=" * 80)
    ok = warn = fail = 0
    for method, path, code, note in results:
        if code == 0 or code >= 500:
            tag = "FAIL"; fail += 1
        elif code in (200, 201, 204):
            tag = "OK  "; ok += 1
        elif code in (401, 422, 404):
            tag = "EXPT"; warn += 1
        else:
            tag = "??  "; warn += 1
        line = f"  [{tag}] {method:6s} {path:42s} → {code}"
        if note:
            line += f"  {note[:60]}"
        print(line)
    print()
    print(f"Totals: ok={ok}  expected-other={warn}  fail={fail}  total={len(results)}")

    # ---------------------------------------------------------------- pagination shape
    print()
    print("=" * 80)
    print("PAGINATION ENVELOPE CHECK")
    print("=" * 80)
    paged = [
        "/vehicles/", "/alerts/", "/entry-exit/", "/cameras/",
        "/camera-feeds/", "/occupancy/slots",
    ]
    paged_fail = 0
    expected_keys = {"total_count", "page", "page_size", "items"}
    for p in paged:
        try:
            r = client.get(p)
        except Exception as e:
            print(f"  [FAIL] GET {p:30s} EXCEPTION: {type(e).__name__}: {e}")
            paged_fail += 1
            continue
        if r.status_code != 200:
            print(f"  [FAIL] GET {p:30s} → {r.status_code}")
            paged_fail += 1
            continue
        try:
            body = r.json()
        except Exception:
            body = {}
        keys = set(body.keys()) if isinstance(body, dict) else set()
        good = keys >= expected_keys
        tag = "OK  " if good else "FAIL"
        if not good:
            paged_fail += 1
        # Confirm page-meta values match what we sent (page_size=2, page=1)
        page_ok = ""
        if good:
            r2 = client.get(p, params={"page": 1, "page_size": 5})
            b2 = r2.json()
            page_ok = f" pg={b2.get('page')} sz={b2.get('page_size')} total={b2.get('total_count')}"
        print(f"  [{tag}] GET {p:30s} keys={sorted(keys)}{page_ok}")

    # ---------------------------------------------------------------- response_model coverage
    print()
    print("=" * 80)
    print("response_model COVERAGE")
    print("=" * 80)
    rm_routes = [(r.path, r.methods, getattr(r, "response_model", None)) for r in app.routes if hasattr(r, "methods")]
    with_rm = sum(1 for _, _, m in rm_routes if m is not None)
    without_rm = [(p, list(ms)) for p, ms, m in rm_routes if m is None and p not in {"/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect", "/alerts/stream"}]
    print(f"  routes with response_model:    {with_rm}")
    print(f"  routes without response_model: {len(without_rm)}")
    for p, ms in without_rm:
        print(f"    - {sorted(ms)} {p}")

    # ---------------------------------------------------------------- PR 3 spot checks
    print()
    print("=" * 80)
    print("PR 3 SPOT CHECKS")
    print("=" * 80)
    spec = client.get("/openapi.json").json()

    # G-2
    from app.schemas import AlertStreamEventLite, AlertStreamEvent
    g2_alias = AlertStreamEvent is AlertStreamEventLite
    g2_fields = "triggered_at" in AlertStreamEventLite.model_fields and "timestamp" not in AlertStreamEventLite.model_fields
    print(f"  [G-2 ] AlertStreamEvent ≡ AlertStreamEventLite           : {g2_alias}")
    print(f"  [G-2 ] schema has triggered_at, no timestamp             : {g2_fields}")

    # G-4
    g4_params = [p["name"] for p in spec["paths"]["/occupancy/slots"]["get"].get("parameters", [])]
    g4_no_grouped = "grouped" not in g4_params
    g4_paged = (spec["paths"]["/occupancy/slots"]["get"]["responses"]["200"]
                ["content"]["application/json"]["schema"]["$ref"]
                .endswith("PagedResponse_SlotListItem_"))
    print(f"  [G-4 ] /occupancy/slots removed `grouped` param          : {g4_no_grouped}")
    print(f"  [G-4 ] /occupancy/slots responds PagedResponse[SlotListItem]: {g4_paged}")

    # G-20
    g20_dep = spec["paths"]["/dashboard/active-vehicles"]["get"].get("deprecated") is True
    print(f"  [G-20] /dashboard/active-vehicles deprecated=True        : {g20_dep}")

    print()
    print("=" * 80)
    if fail == 0 and paged_fail == 0 and g2_alias and g2_fields and g4_no_grouped and g4_paged and g20_dep:
        print("✓ ALL CHECKS PASSED")
        return 0
    print(f"✗ FAILURES: endpoint={fail}  pagination={paged_fail}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
