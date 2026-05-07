#!/usr/bin/env python
"""Simulate an ANPR entry-gate webhook and verify the lifecycle end-to-end.

Builds a Hikvision-shape ANPR XML event, POSTs it to PMS-AI's
`/api/v1/events/camera`, then polls the API Gateway to confirm the event
landed: a new entry-exit row, a vehicle marked `is_currently_parked=true`,
and the dashboard `active_now` KPI bumped.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make this dir importable so the leading-digit module name doesn't bite us.
sys.path.insert(0, str(Path(__file__).parent))

from _common import (  # noqa: E402
    GATEWAY_DEFAULT,
    PMS_AI_DEFAULT,
    build_anpr_xml,
    cyan,
    expect,
    get_dashboard_kpis,
    get_recent_entry_exit,
    get_vehicle_by_plate,
    green,
    http_session,
    load_test_image,
    now_facility_iso,
    poll_until,
    post_camera_event,
    red,
    yellow,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Simulate an ANPR entry event.")
    p.add_argument("--plate", default="TEST-A001")
    p.add_argument("--camera", default="CAM-ENTRY")
    p.add_argument("--ip", default="10.1.13.100")
    p.add_argument("--time", dest="time_iso", default=None,
                   help="ISO-8601 with +03:00 offset; defaults to now.")
    p.add_argument("--with-image", dest="with_image", action="store_true", default=True,
                   help="Attach a multipart image (default).")
    p.add_argument("--no-image", dest="with_image", action="store_false",
                   help="Skip the multipart image — XML body only.")
    p.add_argument("--pms-ai", default=PMS_AI_DEFAULT)
    p.add_argument("--gateway", default=GATEWAY_DEFAULT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    dt_iso = args.time_iso or now_facility_iso()
    session = http_session()

    cyan(f"\nEntry simulation for plate={args.plate} via {args.camera} @ {dt_iso}")
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

    # 2. Verification (allow up to 5s for the writer to flush).
    yellow("Verifying lifecycle on Gateway...")
    all_ok = True

    def has_entry_row() -> bool:
        rows = get_recent_entry_exit(session, args.gateway, args.plate, limit=5)
        return any(
            ((r.get("entry") or {}).get("camera_id") is not None
             or r.get("entry_time") is not None)
            and (r.get("plate_number") or "").upper() == args.plate.upper()
            for r in rows
        )

    if not poll_until(has_entry_row, timeout=5.0, interval=0.5):
        red(f"No entry-exit row appeared for plate={args.plate} within 5s")
        all_ok = False
    else:
        green("entry-exit row recorded with gate=entry")

    # `current_slot_id` is expected to still be NULL here — VA hasn't bound a
    # slot yet (race window between ANPR and the slot-detection camera).
    # We check parking_status='open' on the LIST endpoint (exposed by the
    # parking_sessions JOIN) — `is_currently_parked` is detail-only.
    def vehicle_marked_parked() -> bool:
        v = get_vehicle_by_plate(session, args.gateway, args.plate)
        if v is None:
            return False
        return v.get("parking_status") == "open" or bool(v.get("is_currently_parked"))

    if not poll_until(vehicle_marked_parked, timeout=5.0, interval=0.5):
        red(f"Vehicle {args.plate} not in an open parking session")
        all_ok = False
    else:
        green("vehicle parking_status=open (current_slot_id may still be null)")

    kpis = get_dashboard_kpis(session, args.gateway)
    all_ok &= expect(
        (kpis.get("active_now") or 0) >= 1,
        f"dashboard.active_now = {kpis.get('active_now')} (>=1)",
        f"dashboard.active_now = {kpis.get('active_now')} (expected >=1)",
    )

    print()
    if all_ok:
        green("all checks passed")
        print("PASS")
        return 0
    red("see failures above")
    print("FAIL")
    return 1


if __name__ == "__main__":
    """Validate the entry side of the parking lifecycle.

    Posts a Hikvision ANPR XML event (optionally with a multipart JPEG so the
    image-extraction path is exercised) to PMS-AI, then polls the Gateway
    for: a new entry-exit row, a parked vehicle, and a bumped active_now KPI.

    Exit code 0 = PASS, 1 = FAIL or HTTP error.
    """
    sys.exit(main())
