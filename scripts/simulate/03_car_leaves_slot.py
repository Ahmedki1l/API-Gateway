#!/usr/bin/env python
"""Simulate VideoAnalytics unbinding a slot when a car drives off (PMS-AI internal call).

VA's `slot_status_service.py` posts to PMS-AI's
`/api/v1/internal/parking-sessions/unbind-slot` once its CV pipeline sees the
previously-occupied slot is empty. PMS-AI's `parking_session_service.py:178-179`
then clears `parking_sessions.slot_id` (via slot_left_at) AND
`vehicles.current_slot_id` -- but only if the open session's slot_id matches
the unbind slot. The parking session itself stays open (status='open');
exit-from-garage is handled later by `06_car_exits_garage.py`.
"""

from __future__ import annotations

import argparse
import re
import sys

from _common import (
    PMS_AI_DEFAULT, GATEWAY_DEFAULT,
    now_facility_iso, http_session, post_internal,
    get_vehicle_by_plate, get_occupancy_slot,
    green, red, yellow, cyan,
    expect, poll_until, va_write_slot_status,
)


def derive_slot_number(slot_id: str) -> str:
    m = re.match(r"^[Bb](\d+)", slot_id or "")
    return m.group(1) if m else "1"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--plate", default="TEST-A001")
    p.add_argument("--slot-id", default="B11_CFO")
    p.add_argument("--slot-number", default=None)
    p.add_argument("--camera", default="CAM-03")
    p.add_argument("--left-at", default=None)
    p.add_argument("--snapshot", default="")
    p.add_argument("--pms-ai", default=PMS_AI_DEFAULT)
    p.add_argument("--gateway", default=GATEWAY_DEFAULT)
    args = p.parse_args()
    args.slot_number = args.slot_number or derive_slot_number(args.slot_id)
    args.left_at     = args.left_at     or now_facility_iso()
    return args


def main() -> int:
    args = parse_args()
    session = http_session()
    cyan("── 03 car leaves slot ──────────────────────────────")
    print(f"plate={args.plate}  slot={args.slot_id}  camera={args.camera}")

    pre = get_vehicle_by_plate(session, args.gateway, args.plate)
    if pre is None:
        red(f"vehicle not found - run 01/02 first (plate={args.plate})")
        print("FAIL"); return 1

    pre_slot = pre.get("current_slot_id")
    print(f"  pre-state: current_slot_id={pre_slot}")
    if pre_slot is None:
        yellow("  vehicle has no current_slot_id - did 02_car_parks_in_slot.py run?")
    elif pre_slot != args.slot_id:
        yellow(
            f"  current_slot_id ({pre_slot}) != --slot-id ({args.slot_id}); "
            "PMS-AI will refuse to clear vehicles.current_slot_id"
        )

    # In production VA writes slot_status BEFORE calling PMS-AI unbind-slot
    # (see slot_status_service.log_vehicle_event). Mirror that here so
    # /occupancy/slots/{id} reflects the unbind too.
    yellow(f"VA-side: writing slot_status row + freeing parking_slots.is_available for {args.slot_id}")
    if not va_write_slot_status(args.slot_id, args.plate, is_parked=False, camera_id=args.camera):
        red("VA slot_status write failed - aborting (occupancy will not be consistent)")
        print("FAIL"); return 1
    green("VA slot_status row inserted (status=available); any open intrusion alert on this slot resolved")

    payload = {
        "plate_number": args.plate,
        "slot_id":      args.slot_id,
        "slot_number":  args.slot_number,
        "camera_id":    args.camera,
        "left_at":      args.left_at,
        "snapshot_path": args.snapshot,
    }

    yellow(f"POST {args.pms_ai}/api/v1/internal/parking-sessions/unbind-slot")
    resp = post_internal(session, args.pms_ai, "parking-sessions/unbind-slot", payload)
    print(f"  status: {resp.status_code}")
    try:
        body = resp.json()
    except ValueError:
        body = resp.text
    print(f"  body  : {body}")
    if resp.status_code >= 400:
        red("unbind-slot HTTP error - aborting verification")
        print("FAIL"); return 1

    results = []
    matched_slot = (pre_slot == args.slot_id)

    if matched_slot:
        # PMS-AI :178-179 cleared vehicles.current_slot_id because slot matched.
        cyan("verifying slot was released (slot_id matched pre-state)...")
        cleared = poll_until(
            lambda: (get_vehicle_by_plate(session, args.gateway, args.plate) or {}).get("current_slot_id") is None,
            timeout=5.0, interval=0.5,
        )
        results.append(expect(cleared,
                              "vehicle.current_slot_id is now NULL",
                              "vehicle.current_slot_id never cleared within 5s"))
        v = get_vehicle_by_plate(session, args.gateway, args.plate) or {}
        results.append(expect(v.get("current_slot_name") is None,
                              "vehicle.current_slot_name is now NULL",
                              f"vehicle.current_slot_name still set: {v.get('current_slot_name')}"))
        # Session should still be open -- unbind releases the slot, not the garage.
        cur = v.get("current_event")
        session_open = (cur is not None) or bool(v.get("is_currently_parked"))
        results.append(expect(session_open,
                              "parking session still open (vehicle still in garage)",
                              "parking session unexpectedly closed - unbind should not exit the vehicle"))
        if cur is not None:
            results.append(expect(cur.get("slot_id") is None,
                                  "current_event.slot_id is now NULL",
                                  f"current_event.slot_id still set: {cur.get('slot_id')}"))
        # Occupancy must reflect the unbind as well — slot back to available.
        cyan("verifying /occupancy/slots/{slot_id} reflects the unbind...")
        try:
            slot_view = get_occupancy_slot(session, args.gateway, args.slot_id)
        except Exception as e:
            red(f"could not fetch /occupancy/slots/{args.slot_id}: {e}")
            results.append(False)
        else:
            cur_view = (slot_view or {}).get("current") or {}
            results.append(expect(
                slot_view.get("is_available") is True,
                "occupancy.is_available == true",
                f"occupancy.is_available = {slot_view.get('is_available')!r} (expected true)",
            ))
            results.append(expect(
                cur_view.get("plate_number") in (None, ""),
                "occupancy.current.plate_number cleared",
                f"occupancy.current.plate_number still set: {cur_view.get('plate_number')!r}",
            ))
    else:
        # Wrong-slot guard: PMS-AI :178-179 refuses to clear current_slot_id when
        # the requested slot doesn't match the open session's slot. Verify state
        # did NOT change -- this is the *correct* behaviour, not a bug.
        cyan("verifying wrong-slot guard (PMS-AI should NOT clear current_slot_id)...")
        post = get_vehicle_by_plate(session, args.gateway, args.plate) or {}
        results.append(expect(post.get("current_slot_id") == pre_slot,
                              f"current_slot_id unchanged ({pre_slot}) - PMS-AI correctly ignored wrong slot",
                              f"current_slot_id changed unexpectedly: {pre_slot} -> {post.get('current_slot_id')}"))
        cyan(
            "  note: this is the expected behaviour when --slot-id doesn't match "
            "the session's bound slot. parking_session_service.py:178-179 only "
            "clears current_slot_id when the slots match."
        )

    passed = sum(1 for r in results if r)
    failed = len(results) - passed
    cyan(f"── result: {passed} passed, {failed} failed ──")
    print("PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
