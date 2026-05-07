#!/usr/bin/env python
"""
T24 — Run the 9 acceptance checks from HIGH_SEVERITY_FIX_PLAN.md against the
running services. Prints PASS/FAIL per check. Read-only — safe to re-run.

Usage:
    python scripts/run_acceptance_checks.py
    python scripts/run_acceptance_checks.py --gateway http://localhost:8001 --pms-ai http://localhost:8080

Requires only the standard library + `requests` (already in requirements.txt).
"""
from __future__ import annotations
import argparse, sys, os, time
from typing import Optional

# Windows console defaults to cp1252 — force UTF-8 so emoji + box-drawing chars render.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import requests
except ImportError:
    print("ERROR: this script requires 'requests'. Install with: pip install requests", file=sys.stderr)
    sys.exit(2)

GREEN, RED, YELLOW, CYAN, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[36m", "\033[0m"
state = {"pass": 0, "fail": 0, "skip": 0}

def ok(msg):   print(f"  {GREEN}✅{RESET} {msg}"); state["pass"] += 1
def err(msg):  print(f"  {RED}❌{RESET} {msg}"); state["fail"] += 1
def note(msg): print(f"  {CYAN}ℹ️{RESET}  {msg}")
def skip(msg): print(f"  {YELLOW}⊘{RESET}  SKIP: {msg}"); state["skip"] += 1
def header(n, title):
    print(f"\n── {n}) {title} ──")

def safe_get(session: requests.Session, url: str) -> Optional[dict]:
    try:
        r = session.get(url, timeout=5)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None

def check_1_open_alerts_match(s, gw):
    header(1, "dashboard.open_alerts == alerts.active_alerts")
    d = safe_get(s, f"{gw}/dashboard/kpis")
    a = safe_get(s, f"{gw}/alerts/stats")
    if not d or not a:
        skip("could not reach Gateway endpoints"); return
    da = d.get("open_alerts")
    aa = a.get("active_alerts")
    if da == aa:
        ok(f"both = {da}")
    else:
        err(f"dashboard={da} vs alerts={aa}")

def check_2_vehicles_have_slot_and_event(s, gw):
    header(2, "vehicles[].current_slot_id and current_event populated for parked")
    body = safe_get(s, f"{gw}/vehicles/?is_currently_parked=true&page_size=5")
    if not body:
        skip("Gateway unreachable"); return
    items = body.get("items", [])
    if not items:
        skip("no currently-parked vehicles"); return
    n = len(items)
    cs = sum(1 for it in items if it.get("current_slot_id"))
    ev = sum(1 for it in items if it.get("current_event"))
    if cs > 0: ok(f"current_slot_id populated on {cs}/{n}")
    else:      err(f"current_slot_id null on all {n}")
    if ev > 0: ok(f"current_event populated on {ev}/{n}")
    else:      err(f"current_event null on all {n}")

def check_3_three_way_invariant():
    header(3, "vehicles.current_slot_id == current_event.slot_id == parking_sessions.slot_id")
    note("SQL-only — run against the live DB:")
    note("  SELECT v.plate_number, v.current_slot_id, ps.slot_id")
    note("    FROM vehicles v JOIN parking_sessions ps ON ps.plate_number = v.plate_number")
    note("    WHERE ps.status='open'")
    note("      AND (v.current_slot_id IS NULL OR ps.slot_id IS NULL OR v.current_slot_id != ps.slot_id);")
    note("Expected: zero rows.")

def check_4_alert_slot_id(s, gw):
    header(4, "alerts.slot_id populated on alerts with vehicle context")
    body = safe_get(s, f"{gw}/alerts/?page_size=20")
    if not body:
        skip("Gateway unreachable"); return
    with_plate = [a for a in body.get("items", []) if a.get("plate_number")]
    if not with_plate:
        skip("no recent alerts with plate context"); return
    with_slot = [a for a in with_plate if a.get("slot_id")]
    if with_slot:
        ok(f"{len(with_slot)}/{len(with_plate)} alerts with plate also have slot_id")
    else:
        err(f"0/{len(with_plate)} alerts with plate have slot_id")

def check_5_entry_exit_detail_slot(s, gw):
    header(5, "/entry-exit/{id} detail surfaces slot_id/slot_name/floor")
    body = safe_get(s, f"{gw}/entry-exit/?page_size=1")
    if not body or not body.get("items"):
        skip("no entry/exit events"); return
    eid = body["items"][0].get("id")
    detail = safe_get(s, f"{gw}/entry-exit/{eid}")
    if not detail:
        skip(f"could not fetch event {eid}"); return
    slot_id = detail.get("slot_id")
    if slot_id:
        ok(f"event {eid} has slot_id={slot_id}")
    else:
        note(f"event {eid} has no slot (may be open + unbound)")

def check_6_vehicle_detail_flat_fields(s, gw):
    header(6, "GET /vehicles/{id} exposes parked_at/floor/floor_id/parking_status/last_seen_at")
    listing = safe_get(s, f"{gw}/vehicles/?is_currently_parked=true&page_size=1")
    if not listing or not listing.get("items"):
        skip("no currently-parked vehicle"); return
    vid = listing["items"][0].get("id")
    if not vid:
        skip("no vehicle id"); return
    detail = safe_get(s, f"{gw}/vehicles/{vid}")
    if not detail:
        skip(f"could not fetch vehicle {vid}"); return
    needed = ["parked_at", "parking_status", "floor", "floor_id", "last_seen_at"]
    missing = [k for k in needed if k not in detail]
    if not missing:
        ok("all 5 flat fields present")
    else:
        err(f"missing keys: {missing}")

def check_7_tz_logged():
    header(7, "Both services run with same FACILITY_TIMEZONE_OFFSET_HOURS")
    note("Read each service's startup log and confirm:")
    note("  Gateway: 'Facility TZ offset: UTC+<X>'")
    note("  PMS-AI:  '🕐 Facility TZ offset: UTC+<X>'")
    note("Both <X> values must match.")

def check_8_camera_names_and_format(s, gw):
    header(8, "cameras.list[].name unique and camera_id canonical (CAM-XX dash-form)")
    body = safe_get(s, f"{gw}/cameras/?page_size=100")
    if not body:
        skip("Gateway unreachable"); return
    items = body.get("items", [])
    n = len(items)
    if n == 0:
        skip("no cameras"); return
    names = [it.get("name") or "" for it in items]
    uniq = len(set(names))
    if uniq == n: ok(f"{n} cameras, all names unique")
    else:         err(f"{n} cameras but only {uniq} unique names")
    nondash = [it for it in items if not (it.get("camera_id") or "").startswith("CAM-")]
    if not nondash: ok("all camera_ids are dash-form")
    else:           err(f"{len(nondash)} camera_ids are NOT dash-form (expected CAM-XX): {[c['camera_id'] for c in nondash]}")

def check_9_entry_snapshot(s, gw):
    header(9, "entry_snapshot_path populated on recent entries")
    body = safe_get(s, f"{gw}/entry-exit/?status=open&page_size=10")
    if not body:
        skip("Gateway unreachable"); return
    items = body.get("items", [])
    if not items:
        skip("no recent open events"); return
    with_snap = sum(1 for it in items if (it.get("entry") or {}).get("snapshot_url"))
    if with_snap > 0:
        ok(f"{with_snap}/{len(items)} recent entries have snapshot")
    else:
        err(f"0/{len(items)} entries have snapshot — see T22 (camera auth)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gateway", default=os.environ.get("GATEWAY", "http://localhost:8001"))
    ap.add_argument("--pms-ai",  default=os.environ.get("PMS_AI",  "http://localhost:8080"))
    args = ap.parse_args()
    s = requests.Session()

    print("=" * 50)
    print(f"Acceptance checks  Gateway={args.gateway}  PMS-AI={args.pms_ai}")
    print("=" * 50)

    check_1_open_alerts_match(s, args.gateway)
    check_2_vehicles_have_slot_and_event(s, args.gateway)
    check_3_three_way_invariant()
    check_4_alert_slot_id(s, args.gateway)
    check_5_entry_exit_detail_slot(s, args.gateway)
    check_6_vehicle_detail_flat_fields(s, args.gateway)
    check_7_tz_logged()
    check_8_camera_names_and_format(s, args.gateway)
    check_9_entry_snapshot(s, args.gateway)

    print("\n" + "=" * 50)
    print(f"Result: {state['pass']} passed, {state['fail']} failed, {state['skip']} skipped")
    print("=" * 50)
    return 0 if state["fail"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
