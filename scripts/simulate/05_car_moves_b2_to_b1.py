#!/usr/bin/env python
"""Simulate a vehicle moving from a B2 slot to a B1 slot inside the garage.

Mirror of 04_car_moves_b1_to_b2.py: same composite (unbind -> sleep -> bind),
optional CAM-09 (B2 exit) + CAM-03 (B1 entry) linedetection events.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from _common import (  # noqa: E402
    PMS_AI_DEFAULT,
    GATEWAY_DEFAULT,
    cyan,
    expect,
    get_vehicle_by_plate,
    green,
    http_session,
    now_facility_iso,
    poll_until,
    post_camera_event,
    red,
    yellow,
)

CAM_09_IP = "10.1.13.68"  # B2 exit boundary line camera
CAM_03_IP = "10.1.13.62"  # B1 entry boundary line camera


def build_line_event_xml(camera_id: str, ip: str, dt_iso: str) -> str:
    """Minimal Hikvision linedetection XML payload."""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<EventNotificationAlert version="2.0" '
        'xmlns="http://www.isapi.org/ver20/XMLSchema">\n'
        f"<ipAddress>{ip}</ipAddress>\n"
        f"<dateTime>{dt_iso}</dateTime>\n"
        "<eventType>linedetection</eventType>\n"
        "<eventState>active</eventState>\n"
        f"<channelName>{camera_id}</channelName>\n"
        "</EventNotificationAlert>\n"
    )


def run_subscript(name: str, args: list[str]) -> tuple[bool, str]:
    """Run a sibling simulate script via subprocess. Return (ok, stdout)."""
    cmd = [sys.executable, str(HERE / name), *args]
    cyan(f"  -> {name} {' '.join(args)}")
    proc = subprocess.run(
        cmd,
        cwd=str(HERE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    sys.stdout.write(proc.stdout or "")
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    ok = proc.returncode == 0 and (proc.stdout or "").strip().splitlines()[-1:] == ["PASS"]
    return ok, proc.stdout or ""


def main() -> int:
    p = argparse.ArgumentParser(description="Simulate a B2 -> B1 in-garage slot change.")
    p.add_argument("--plate", default="TEST-A001")
    p.add_argument("--from-slot", default="B16",
                   help="Source slot on floor B2 (default: B16). "
                        "Per seed.sql, B2 floor slots include: "
                        "B14, B15, B16, B17, B18, B19, B20, B21, B22, B23, B24, B25, B27.")
    p.add_argument("--from-camera", default="CAM-09")
    p.add_argument("--to-slot", default="B11_CFO",
                   help="Destination slot on floor B1 (default: B11_CFO)")
    p.add_argument("--to-camera", default="CAM-03")
    p.add_argument("--with-line-events", action="store_true")
    p.add_argument("--delay", type=float, default=1.0)
    p.add_argument("--pms-ai", default=PMS_AI_DEFAULT)
    p.add_argument("--gateway", default=GATEWAY_DEFAULT)
    args = p.parse_args()

    cyan(f"=== B2 -> B1 move: plate={args.plate} "
               f"{args.from_slot} -> {args.to_slot} ===")

    session = http_session()

    # 1. Pre-check: vehicle must already be parked in --from-slot.
    cyan("[1/6] Pre-check: vehicle is in expected start slot...")
    veh = get_vehicle_by_plate(session, args.gateway, args.plate)
    if not veh:
        red(f"FAIL: vehicle {args.plate} not found in gateway")
        print("FAIL")
        return 1
    current_slot = veh.get("current_slot_id") or veh.get("current_event", {}).get("slot_id")
    if current_slot != args.from_slot:
        red(f"FAIL: vehicle not in expected start slot "
                  f"(have={current_slot!r}, want={args.from_slot!r})")
        print("FAIL")
        return 1
    green(f"  vehicle currently in {current_slot}")

    # 2. Unbind from old slot via 03_car_leaves_slot.py.
    cyan(f"[2/6] Unbind from old slot {args.from_slot} (camera {args.from_camera})...")
    ok, _ = run_subscript(
        "03_car_leaves_slot.py",
        [
            "--plate", args.plate,
            "--slot-id", args.from_slot,
            "--camera", args.from_camera,
            "--pms-ai", args.pms_ai,
            "--gateway", args.gateway,
        ],
    )
    if not ok:
        red("FAIL: unbind step (03) did not return PASS")
        print("FAIL")
        return 1

    # 3. Sleep so PMS-AI flushes the unbind transaction.
    cyan(f"[3/6] Sleeping {args.delay}s for PMS-AI flush...")
    time.sleep(args.delay)

    # 4. Optional: fire Hikvision linedetection events.
    if args.with_line_events:
        cyan("[4/6] Posting linedetection events: CAM-09 (B2 exit) + CAM-03 (B1 entry)...")
        for cam_id, cam_ip in (("CAM-09", CAM_09_IP), ("CAM-03", CAM_03_IP)):
            xml = build_line_event_xml(cam_id, cam_ip, now_facility_iso())
            resp = post_camera_event(session, args.pms_ai, payload_xml=xml)
            ok = 200 <= resp.status_code < 300
            expect(ok, f"linedetection {cam_id} accepted ({resp.status_code})",
                   f"linedetection {cam_id} rejected ({resp.status_code})")
            if not ok:
                red("FAIL: linedetection event was rejected")
                print("FAIL")
                return 1
    else:
        cyan("[4/6] Skipping linedetection events (--with-line-events not set).")

    # 5. Bind to new slot via 02_car_parks_in_slot.py.
    cyan(f"[5/6] Bind to new slot {args.to_slot} (camera {args.to_camera})...")
    ok, _ = run_subscript(
        "02_car_parks_in_slot.py",
        [
            "--plate", args.plate,
            "--slot-id", args.to_slot,
            "--camera", args.to_camera,
            "--zone-id", "B1-PARKING",
            "--zone-name", "B1 Parking",
            "--floor", "B1",
            "--pms-ai", args.pms_ai,
            "--gateway", args.gateway,
        ],
    )
    if not ok:
        red("FAIL: bind step (02) did not return PASS")
        print("FAIL")
        return 1

    # 6. Verify end-state via gateway, polling for eventual consistency.
    cyan("[6/6] Verifying end-state via gateway...")

    def _check() -> bool:
        v = get_vehicle_by_plate(session, args.gateway, args.plate)
        if not v:
            return False
        ce = v.get("current_event") or {}
        return (
            v.get("current_slot_id") == args.to_slot
            and v.get("floor") == "B1"
            and ce.get("slot_id") == args.to_slot
            and ce.get("floor") == "B1"
        )

    consistent = poll_until(_check, timeout=5.0, interval=0.5)
    if not consistent:
        v = get_vehicle_by_plate(session, args.gateway, args.plate) or {}
        red(f"FAIL: end-state not as expected — vehicle={v}")
        print("FAIL")
        return 1

    green(f"  vehicle now in {args.to_slot} on floor B1")
    green("=== B2 -> B1 move PASS ===")
    print("PASS")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        yellow("\nInterrupted.")
        print("FAIL")
        sys.exit(130)
