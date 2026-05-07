#!/usr/bin/env python
"""Simulate VideoAnalytics binding a slot for a parked car (PMS-AI internal call).

VA's `slot_status_service.py:85` posts to PMS-AI's
`/api/v1/internal/parking-sessions/bind-slot` once its CV pipeline detects a
vehicle has settled in a slot. PMS-AI's `parking_session_service.py:141` then
writes both `parking_sessions.slot_id` AND `vehicles.current_slot_id` in the
same transaction. This script replays that call and verifies the Gateway sees
the resulting state via `GET /vehicles/?search=<plate>` (which JOINs to
`parking_slots` for `current_slot_name`).

Pre-condition: `01_car_enters_garage.py` must have created the open
parking_sessions row for `--plate`.
"""

from __future__ import annotations

import argparse
import re
import sys

from _common import (
    PMS_AI_DEFAULT, GATEWAY_DEFAULT,
    now_facility_iso, http_session, post_internal,
    get_vehicle_by_plate, get_occupancy_slot, get_alerts_for_slot,
    green, red, yellow, cyan,
    expect, poll_until, slot_is_violation_zone, va_write_slot_status,
)


def derive_slot_number(slot_id: str) -> str:
    m = re.match(r"^[Bb](\d+)", slot_id or "")
    return m.group(1) if m else "1"


def derive_floor(zone_id: str) -> str:
    m = re.match(r"^([Bb]\d+)", zone_id or "")
    return m.group(1).upper() if m else "B1"


def derive_zone_name(zone_id: str) -> str:
    parts = (zone_id or "").split("-", 1)
    return f"{parts[0].upper()} {parts[1].title()}" if len(parts) == 2 else (zone_id or "")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--plate", default="TEST-A001")
    p.add_argument("--slot-id", default="B11_CFO")
    p.add_argument("--slot-number", default=None)
    p.add_argument("--zone-id", default="B1-PARKING")
    p.add_argument("--zone-name", default=None)
    p.add_argument("--floor", default=None)
    p.add_argument("--camera", default="CAM-03")
    p.add_argument("--parked-at", default=None)
    p.add_argument("--snapshot", default="")
    p.add_argument("--pms-ai", default=PMS_AI_DEFAULT)
    p.add_argument("--gateway", default=GATEWAY_DEFAULT)
    args = p.parse_args()
    args.slot_number = args.slot_number or derive_slot_number(args.slot_id)
    args.zone_name   = args.zone_name   or derive_zone_name(args.zone_id)
    args.floor       = args.floor       or derive_floor(args.zone_id)
    args.parked_at   = args.parked_at   or now_facility_iso()
    return args


def main() -> int:
    args = parse_args()
    session = http_session()
    cyan("── 02 car parks in slot ────────────────────────────")
    print(f"plate={args.plate}  slot={args.slot_id}  floor={args.floor}  camera={args.camera}")

    pre = get_vehicle_by_plate(session, args.gateway, args.plate)
    if pre is None:
        red(f"vehicle not found - run 01_car_enters_garage.py first (plate={args.plate})")
        print("FAIL"); return 1
    if not pre.get("current_event"):
        red(f"no open parking session for {args.plate} - run 01 first")
        print("FAIL"); return 1
    green(f"pre-check ok: vehicle exists, open session id={pre['current_event'].get('id')}")

    # In production VA writes slot_status BEFORE calling PMS-AI bind-slot
    # (see slot_status_service.log_vehicle_event order). Mirror that here so
    # /occupancy/slots/{id} reflects the bind too — without this the slot
    # stays 'available' even though the parking_session is bound. When the
    # slot is a violation zone, va_write_slot_status also fires the
    # vehicle_intrusion alert with a snapshot path (mirrors VA's report_alert).
    yellow(f"VA-side: writing slot_status row + toggling parking_slots.is_available for {args.slot_id}")
    if not va_write_slot_status(args.slot_id, args.plate, is_parked=True, camera_id=args.camera):
        red("VA slot_status write failed - aborting (occupancy will not be consistent)")
        print("FAIL"); return 1
    green("VA slot_status row inserted (status=occupied)")

    payload = {
        "plate_number": args.plate,
        "slot_id":      args.slot_id,
        "slot_number":  args.slot_number,
        "zone_id":      args.zone_id,
        "zone_name":    args.zone_name,
        "floor":        args.floor,
        "camera_id":    args.camera,
        "parked_at":    args.parked_at,
        "snapshot_path": args.snapshot,
    }

    yellow(f"POST {args.pms_ai}/api/v1/internal/parking-sessions/bind-slot")
    resp = post_internal(session, args.pms_ai, "parking-sessions/bind-slot", payload)
    print(f"  status: {resp.status_code}")
    try:
        body = resp.json()
    except ValueError:
        body = resp.text
    print(f"  body  : {body}")
    if resp.status_code >= 400:
        red("bind-slot HTTP error - aborting verification")
        print("FAIL"); return 1

    cyan("verifying via Gateway /vehicles/?search=...")
    bound = poll_until(
        lambda: bool((get_vehicle_by_plate(session, args.gateway, args.plate) or {}).get("current_slot_id") == args.slot_id),
        timeout=5.0, interval=0.5,
    )
    results = [expect(bound, f"vehicle.current_slot_id == {args.slot_id}",
                              "vehicle.current_slot_id never bound within 5s")]

    v = get_vehicle_by_plate(session, args.gateway, args.plate) or {}
    results += [
        expect(bool(v.get("current_slot_name")),
               f"vehicle.current_slot_name populated ({v.get('current_slot_name')})",
               "vehicle.current_slot_name is null - parking_slots JOIN issue"),
        expect(v.get("parked_at") is not None,
               f"vehicle.parked_at populated ({v.get('parked_at')})",
               "vehicle.parked_at is null"),
        expect(v.get("floor") == args.floor,
               f"vehicle.floor == {args.floor}",
               f"vehicle.floor = {v.get('floor')} (expected {args.floor})"),
    ]

    cur = v.get("current_event")
    results.append(expect(cur is not None,
                          "vehicle.current_event is non-null",
                          "vehicle.current_event is null - session not visible"))
    if cur:
        results.append(expect(cur.get("slot_id") == args.slot_id,
                              f"current_event.slot_id == {args.slot_id}",
                              f"current_event.slot_id = {cur.get('slot_id')} (expected {args.slot_id})"))
        # Three-way invariant (acceptance #3): vehicle.current_slot_id ==
        # current_event.slot_id. The DB-side leg can't be checked from the
        # Gateway, but if these two agree the PMS-AI transaction succeeded.
        results.append(expect(v.get("current_slot_id") == cur.get("slot_id"),
                              "three-way invariant: vehicle.current_slot_id == current_event.slot_id",
                              f"INVARIANT BROKEN: vehicle.current_slot_id={v.get('current_slot_id')} "
                              f"vs current_event.slot_id={cur.get('slot_id')}"))

    # If we just parked into a violation zone, the simulator should have
    # also written a vehicle_intrusion alert with a snapshot path. Verify
    # via the Gateway that an open intrusion alert exists on the slot AND
    # carries a snapshot_url. We don't insist the alert's plate matches
    # this run's plate: VA's dedup (alert_service.report_alert) returns
    # the existing active row instead of creating a new one when the slot
    # already has an open alert — exact production behaviour.
    is_violation = slot_is_violation_zone(args.slot_id)
    if is_violation is True:
        cyan("verifying intrusion alert visible on Gateway (slot is_violation_zone=true)...")
        alerts = get_alerts_for_slot(
            session, args.gateway, args.slot_id,
            alert_type="vehicle_intrusion", only_open=True,
        )
        results.append(expect(
            len(alerts) >= 1,
            f"open vehicle_intrusion alert exists on {args.slot_id} (count={len(alerts)})",
            f"no open vehicle_intrusion alert on violation-zone slot {args.slot_id}",
        ))
        if alerts:
            a = alerts[0]
            results.append(expect(
                bool(a.get("snapshot_url")),
                f"alert.snapshot_url populated ({a.get('snapshot_url')})",
                "alert.snapshot_url is empty - intrusion has no evidence image",
            ))
            # Severity isn't asserted: pre-existing alerts may have been
            # created with different severity (e.g. 'info' for the rolling
            # latest-snapshot path) and dedup keeps the original row.
            mine = [x for x in alerts if (x.get("plate_number") or "").upper() == args.plate.upper()]
            if mine:
                green(f"  alert plate matches this run ({args.plate}) — fresh alert (no pre-existing dedup)")
            else:
                yellow(
                    f"  alert plate is {a.get('plate_number')!r}, not {args.plate} — "
                    "deduped against a pre-existing open alert (production-correct)"
                )
    elif is_violation is False:
        cyan(f"slot {args.slot_id} is not a violation zone — no intrusion alert expected")
    else:
        yellow(f"could not read is_violation_zone for {args.slot_id} — skipping intrusion-alert assertion")

    # Now that the simulator writes slot_status itself (mimicking VA), the
    # gateway's /occupancy/slots/{id} should report the slot as occupied
    # by *this* plate. Promoted from informational to a real assertion.
    cyan("verifying /occupancy/slots/{slot_id} reflects the bind...")
    try:
        slot_view = get_occupancy_slot(session, args.gateway, args.slot_id)
    except Exception as e:
        red(f"could not fetch /occupancy/slots/{args.slot_id}: {e}")
        results.append(False)
    else:
        cur_view = (slot_view or {}).get("current") or {}
        results.append(expect(
            (cur_view.get("plate_number") or "").upper() == args.plate.upper(),
            f"occupancy.current.plate_number == {args.plate} "
            f"(state={cur_view.get('state')})",
            f"occupancy.current.plate_number = {cur_view.get('plate_number')!r} "
            f"(expected {args.plate})",
        ))
        results.append(expect(
            slot_view.get("is_available") is False,
            "occupancy.is_available == false",
            f"occupancy.is_available = {slot_view.get('is_available')!r} (expected false)",
        ))

    passed = sum(1 for r in results if r)
    failed = len(results) - passed
    cyan(f"── result: {passed} passed, {failed} failed ──")
    print("PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
