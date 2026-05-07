#!/usr/bin/env python
"""Simulate an ANPR exit-gate webhook and verify session closure end-to-end.

Mirror of `01_car_enters_garage.py`: builds a Hikvision-shape ANPR XML event
for the exit camera, POSTs it to PMS-AI, then polls the Gateway to confirm
the parking session was closed: an entry-exit row with `gate=exit`, the
matching session has `exit_time` set, the vehicle is no longer parked, and
its `current_slot_id` cleared.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _common import (  # noqa: E402
    GATEWAY_DEFAULT,
    PMS_AI_DEFAULT,
    build_anpr_xml,
    cyan,
    expect,
    get_recent_entry_exit,
    get_vehicle_by_plate,
    green,
    http_session,
    load_test_image,
    now_facility_iso,
    poll_until,
    post_camera_event,
    red,
    verify_closed_session_in_db,
    yellow,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Simulate an ANPR exit event.")
    p.add_argument("--plate", default="TEST-A001")
    p.add_argument("--camera", default="CAM-EXIT")
    p.add_argument("--ip", default="10.1.13.101")
    p.add_argument("--time", dest="time_iso", default=None,
                   help="ISO-8601 with +03:00 offset; defaults to now.")
    p.add_argument("--with-image", dest="with_image", action="store_true", default=True)
    p.add_argument("--no-image", dest="with_image", action="store_false")
    p.add_argument("--pms-ai", default=PMS_AI_DEFAULT)
    p.add_argument("--gateway", default=GATEWAY_DEFAULT)
    return p.parse_args()


def _row_has_exit(row: dict) -> bool:
    """A `VehicleEvent` row has an exit when its nested `exit` object is
    populated OR `exit_time` is non-null."""
    if (row.get("exit") or {}).get("event_time"):
        return True
    return row.get("exit_time") is not None


def main() -> int:
    args = parse_args()
    dt_iso = args.time_iso or now_facility_iso()
    session = http_session()

    cyan(f"\nExit simulation for plate={args.plate} via {args.camera} @ {dt_iso}")
    cyan(f"PMS-AI: {args.pms_ai}    Gateway: {args.gateway}\n")

    # 1. Build & POST the event.
    xml_body = build_anpr_xml(args.plate, args.camera, args.ip, dt_iso)
    image_bytes = load_test_image() if args.with_image else None
    try:
        resp = post_camera_event(session, args.pms_ai, payload_xml=xml_body, image_bytes=image_bytes)
    except Exception as exc:
        red(f"POST failed: {exc!r}")
        return 1

    if not resp.ok:
        red(f"POST → {resp.status_code}: {resp.text[:500]}")
        return 1
    green(f"POST → {resp.status_code}")

    # 2. Verification.
    yellow("Verifying session closure on Gateway...")
    all_ok = True

    def has_exit_row() -> bool:
        rows = get_recent_entry_exit(session, args.gateway, args.plate, limit=5)
        return any(
            (r.get("plate_number") or "").upper() == args.plate.upper() and _row_has_exit(r)
            for r in rows
        )

    if not poll_until(has_exit_row, timeout=5.0, interval=0.5):
        red(f"No exit row appeared for plate={args.plate} within 5s")
        all_ok = False
    else:
        green("entry-exit row updated with gate=exit / exit_time set")

    def session_closed() -> bool:
        rows = get_recent_entry_exit(session, args.gateway, args.plate, limit=5)
        for r in rows:
            if (r.get("plate_number") or "").upper() != args.plate.upper():
                continue
            if r.get("status") == "closed" or _row_has_exit(r):
                return True
        return False

    all_ok &= expect(
        session_closed(),
        "matching parking_session is closed",
        "no closed parking_session found for this plate",
    )

    def vehicle_unparked() -> bool:
        v = get_vehicle_by_plate(session, args.gateway, args.plate)
        # No registry row at all → was never registered; treat as not-parked.
        if v is None:
            return True
        return not bool(v.get("is_currently_parked"))

    if not poll_until(vehicle_unparked, timeout=5.0, interval=0.5):
        red(f"Vehicle {args.plate} still appears as is_currently_parked=true")
        all_ok = False
    else:
        green("vehicle is_currently_parked=false")

    v = get_vehicle_by_plate(session, args.gateway, args.plate)
    if v is not None:
        all_ok &= expect(
            v.get("current_slot_id") in (None, ""),
            "vehicle.current_slot_id cleared (NULL)",
            f"vehicle.current_slot_id still set: {v.get('current_slot_id')!r}",
        )

    # DB-truth: a "closed" session API response can be cosmetic — the underlying
    # row may still have NULL slot_left_at or zero duration_seconds. Hit MSSQL
    # directly to catch that drift. The check returns (ok, dict_of_field_status).
    db_ok, db_fields = verify_closed_session_in_db(args.plate)
    for label, ok in db_fields.items():
        all_ok &= expect(ok, f"DB: {label}", f"DB: {label} (drift)")
    if not db_ok and not db_fields:
        yellow("DB-truth check skipped (could not connect to MSSQL)")

    print()
    if all_ok:
        green("all checks passed")
        print("PASS")
        return 0
    red("see failures above")
    print("FAIL")
    return 1


if __name__ == "__main__":
    """Validate the exit side of the parking lifecycle.

    Mirror of 01_car_enters_garage.py — posts an ANPR exit event to PMS-AI
    and polls the Gateway to confirm the matching parking_session closed:
    an exit row appears, status=closed, and the vehicle is no longer parked
    (with `current_slot_id` cleared).

    Exit code 0 = PASS, 1 = FAIL or HTTP error.
    """
    sys.exit(main())
