"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ENTRY TEST — Damanat PMS                                          ║
║                                                                              ║
║  Simulates a car entering the facility and parking in a slot.               ║
║  Writes to DB (as VideoAnalytics would) then verifies via API Gateway.      ║
║                                                                              ║
║  slot_name / floor / floor_id are resolved automatically from parking_slots.║
║  Run BEFORE test_exit.py.                                                   ║
║                                                                              ║
║  How to run:                                                                 ║
║    python tests/test_entry.py                                                ║
║    pytest tests/test_entry.py -v                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys, os
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# ─── CONFIG — only change values here ─────────────────────────────────────────
CONFIG = {
    # Vehicle
    "plate_number":    "abc-8976",      # plate to simulate
    "vehicle_type":    "sedan",           # car | SUV | truck | motorcycle | van
    "is_employee":     True,

    # Slot — just the slot_id. slot_name, floor, floor_id are looked up from DB.
    #   To find valid slot_ids:  SELECT TOP 20 slot_id, slot_name, floor FROM parking_slots
    "slot_id":         "B9",

    # Cameras  →  SELECT camera_id, role FROM cameras
    "entry_camera_id": "ENTRY-GATE",

    # Optional snapshot path (leave empty if none)
    "entry_snapshot":  "",
}
# ──────────────────────────────────────────────────────────────────────────────


# ─── Colour helpers ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"; RED   = "\033[91m"; YELLOW = "\033[93m"
CYAN   = "\033[96m"; BOLD  = "\033[1m";  RESET  = "\033[0m"

def ok(msg):    print(f"  {GREEN}✓{RESET} {msg}")
def fail(msg):  print(f"  {RED}✗{RESET} {msg}"); raise AssertionError(msg)
def info(msg):  print(f"  {CYAN}→{RESET} {msg}")
def warn(msg):  print(f"  {YELLOW}⚠{RESET} {msg}")
def header(msg):
    print(f"\n{BOLD}{CYAN}{'─'*70}{RESET}")
    print(f"{BOLD}{CYAN}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*70}{RESET}")


from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.main import app
from app.database import SessionLocal, scalar

client = TestClient(app, raise_server_exceptions=True)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]


# ═══════════════════════════════════════════════════════════════════════════════
#  SLOT RESOLVER — reads slot details directly from parking_slots
# ═══════════════════════════════════════════════════════════════════════════════

def resolve_slot(db: Session, slot_id: str) -> dict:
    """
    Look up slot_name, floor, floor_id from parking_slots for a given slot_id.
    Fails fast with a clear message if the slot doesn't exist.
    """
    row = db.execute(text("""
        SELECT slot_id, slot_name, floor, floor_id, is_available, is_violation_zone
        FROM parking_slots
        WHERE slot_id = :s
    """), {"s": slot_id}).fetchone()

    if not row:
        fail(
            f"Slot '{slot_id}' not found in parking_slots.\n"
            f"    Run this to see valid slot IDs:\n"
            f"    SELECT TOP 20 slot_id, slot_name, floor FROM parking_slots"
        )

    return {
        "slot_id":           row[0],
        "slot_name":         row[1],
        "floor":             row[2],
        "floor_id":          row[3],   # may be None on pre-migration DBs
        "is_available":      bool(row[4]),
        "is_violation_zone": bool(row[5]),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  DB WRITES
# ═══════════════════════════════════════════════════════════════════════════════

def db_insert_entry_log(db: Session, plate: str, cfg: dict) -> int:
    row = db.execute(text("""
        INSERT INTO entry_exit_log
            (plate_number, gate, camera_id, event_time, snapshot_path, is_test)
        OUTPUT INSERTED.id
        VALUES (:plate, 'entry', :cam, :ts, :snap, 1)
    """), {
        "plate": plate,
        "cam":   cfg["entry_camera_id"],
        "ts":    _now(),
        "snap":  cfg["entry_snapshot"],
    }).fetchone()
    db.commit()
    info(f"entry_exit_log INSERT  → id={row[0]}  gate=entry")
    return row[0]


def db_open_session(db: Session, plate: str, cfg: dict, slot: dict) -> int:
    """
    Open a parking_sessions row.
    floor / floor_id come from the resolved slot — not from CONFIG.
    """
    now_ts = _now()
    row = db.execute(text("""
        INSERT INTO parking_sessions
            (plate_number, vehicle_type, is_employee,
             entry_time, entry_camera_id, entry_snapshot_path,
             floor, floor_id, status, created_at, updated_at)
        OUTPUT INSERTED.id
        VALUES
            (:plate, :vtype, :emp,
             :ts, :cam, :snap,
             :floor, :floor_id, 'open', :ts, :ts)
    """), {
        "plate":     plate,
        "vtype":     cfg["vehicle_type"],
        "emp":       1 if cfg["is_employee"] else 0,
        "ts":        now_ts,
        "cam":       cfg["entry_camera_id"],
        "snap":      cfg["entry_snapshot"],
        "floor":     slot["floor"],        # ← from DB
        "floor_id":  slot["floor_id"],     # ← from DB
    }).fetchone()
    db.commit()
    info(f"parking_sessions INSERT → id={row[0]}  status=open  floor={slot['floor']}")
    return row[0]


def db_slot_occupied(db: Session, plate: str, slot: dict):
    db.execute(text("""
        INSERT INTO slot_status (slot_id, plate_number, status, time)
        VALUES (:slot, :plate, 'occupied', :ts)
    """), {"slot": slot["slot_id"], "plate": plate, "ts": _now()})
    db.execute(text("""
        UPDATE parking_slots SET is_available = 0 WHERE slot_id = :slot
    """), {"slot": slot["slot_id"]})
    db.commit()
    info(f"slot_status INSERT      → slot={slot['slot_id']}  status=occupied")
    info(f"parking_slots UPDATE    → slot={slot['slot_id']}  is_available=0")


def db_update_zone_occupancy(db: Session, floor: str, delta: int):
    """
    Increment/decrement current_count in zone_occupancy for the floor zone
    and the GARAGE-TOTAL row.
    """
    # 1. Update the specific floor zone (e.g. 'B1-PARKING')
    db.execute(text("""
        UPDATE zone_occupancy
        SET current_count = CASE 
            WHEN current_count + :d < 0 THEN 0 
            ELSE current_count + :d 
        END,
        last_updated = :ts
        WHERE floor = :f AND zone_id != 'GARAGE-TOTAL'
    """), {"d": delta, "f": floor, "ts": _now()})

    # 2. Update the global rollup
    db.execute(text("""
        UPDATE zone_occupancy
        SET current_count = CASE 
            WHEN current_count + :d < 0 THEN 0 
            ELSE current_count + :d 
        END,
        last_updated = :ts
        WHERE zone_id = 'GARAGE-TOTAL'
    """), {"d": delta, "ts": _now()})
    
    db.commit()
    action = "Incremented" if delta > 0 else "Decremented"
    info(f"zone_occupancy {action} → floor={floor} and GARAGE-TOTAL (delta={delta})")


def db_link_session_to_slot(db: Session, session_id: int, slot: dict):
    """
    Link the parking session to the slot.
    slot_number = slot_name from parking_slots (the human-readable label).
    floor / floor_id come from the slot row — never from CONFIG.
    """
    db.execute(text("""
        UPDATE parking_sessions
        SET slot_id     = :slot_id,
            slot_number = :slot_number,
            floor       = :floor,
            floor_id    = :floor_id,
            parked_at   = :ts
        WHERE id = :id
    """), {
        "slot_id":     slot["slot_id"],
        "slot_number": slot["slot_name"],  # ← slot_name from parking_slots
        "floor":       slot["floor"],      # ← from DB
        "floor_id":    slot["floor_id"],   # ← from DB
        "ts":          _now(),
        "id":          session_id,
    })
    db.commit()
    info(
        f"parking_sessions UPDATE → id={session_id}  "
        f"slot_id={slot['slot_id']}  slot_name={slot['slot_name']}  "
        f"floor={slot['floor']}  parked_at=NOW"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  API CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

def api_find_open_session(plate: str) -> dict | None:
    r = client.get("/entry-exit/", params={"search": plate, "page_size": 5})
    assert r.status_code == 200, f"GET /entry-exit/ → {r.status_code}: {r.text}"
    for item in r.json().get("items", []):
        if item.get("status") == "open":
            return item
    return None


def api_get_slot(slot_id: str) -> dict | None:
    r = client.get(f"/occupancy/slots/{slot_id}")
    if r.status_code == 404:
        return None
    assert r.status_code == 200, f"GET /occupancy/slots/{slot_id} → {r.status_code}: {r.text}"
    return r.json()


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def run_entry_test():
    cfg   = CONFIG
    plate = cfg["plate_number"]

    print(f"\n{BOLD}{'═'*70}")
    print(f"  ENTRY TEST  |  Plate: {plate}  |  Slot: {cfg['slot_id']}")
    print(f"{'═'*70}{RESET}\n")

    db: Session = SessionLocal()
    try:

        # ── Pre-flight ────────────────────────────────────────────────────────
        header("Pre-flight checks")

        # Resolve all slot details from DB — single source of truth
        slot = resolve_slot(db, cfg["slot_id"])
        ok(
            f"Slot resolved from DB:\n"
            f"      slot_id   = {slot['slot_id']}\n"
            f"      slot_name = {slot['slot_name']}\n"
            f"      floor     = {slot['floor']}\n"
            f"      floor_id  = {slot['floor_id']}\n"
            f"      available = {slot['is_available']}"
        )

        open_count = scalar(db,
            "SELECT COUNT(*) FROM parking_sessions "
            "WHERE plate_number = :p AND status = 'open'", {"p": plate})
        if open_count:
            warn(f"{open_count} open session(s) already exist for plate '{plate}'. "
                 "They won't break this test but may cause confusion.")

        # ── Phase 1: Gate entry ───────────────────────────────────────────────
        header("Phase 1 — Car arrives at entry gate")

        log_id     = db_insert_entry_log(db, plate, cfg)
        session_id = db_open_session(db, plate, cfg, slot)
        
        # Update occupancy (Video Analytics line-crossing simulation)
        db_update_zone_occupancy(db, slot["floor"], 1)
        info("Calling GET /entry-exit/?search=<plate> …")
        s = api_find_open_session(plate)
        if not s:
            fail(f"Open session for '{plate}' not visible via API after gate entry INSERT.")

        assert s["status"] == "open", \
            f"Expected status='open', got '{s['status']}'"
        ok(f"Session visible  id={s['id']}  status=open ✓")

        assert not s.get("slot_id"), \
            f"Expected no slot assigned yet, got slot_id='{s.get('slot_id')}'"
        ok("No slot assigned yet (vehicle is at gate) ✓")

        # ── Phase 2: Vehicle parks in slot ────────────────────────────────────
        header(f"Phase 2 — Car parks in slot {slot['slot_id']} ({slot['slot_name']})")

        db_slot_occupied(db, plate, slot)
        db_link_session_to_slot(db, session_id, slot)

        info(f"Calling GET /occupancy/slots/{slot['slot_id']} …")
        slot_api = api_get_slot(slot["slot_id"])
        if not slot_api:
            fail(f"Slot '{slot['slot_id']}' not found via API.")

        is_avail   = slot_api.get("is_available")
        cur_status = (slot_api.get("current_status") or "").upper()
        ok(
            f"Slot API response:\n"
            f"      is_available   = {is_avail}\n"
            f"      current_status = {cur_status or '(none)'}\n"
            f"      current_plate  = {slot_api.get('current_plate')}"
        )

        occupied = (not is_avail) or (
            cur_status not in ("", "VACANT", "AVAILABLE", "EMPTY", "FREE")
        )
        assert occupied, \
            f"Slot should appear occupied, but is_available={is_avail} status='{cur_status}'"
        ok("Slot shows as occupied ✓")

        info("Calling GET /entry-exit/?search=<plate> …")
        s = api_find_open_session(plate)
        if s:
            assert s.get("slot_id") == slot["slot_id"], \
                f"Expected slot_id='{slot['slot_id']}', got '{s.get('slot_id')}'"
            ok(f"Session linked to slot_id='{slot['slot_id']}' ✓")
            assert s.get("parked_at"), "parked_at should be set"
            ok("parked_at is set ✓")

        # ── Done ──────────────────────────────────────────────────────────────
        header("✅  Entry test PASSED")
        print(f"""
  {GREEN}{BOLD}Summary:{RESET}
    Plate              : {plate}
    Slot               : {slot['slot_id']}  ({slot['slot_name']})
    Floor              : {slot['floor']}  (floor_id={slot['floor_id']})
    entry_exit_log id  : {log_id}
    parking_session id : {session_id}   ← use in test_exit.py if auto-lookup fails

  {YELLOW}Run test_exit.py next to complete the journey.{RESET}
""")

    except AssertionError as e:
        print(f"\n  {RED}{BOLD}ENTRY TEST FAILED:{RESET} {e}\n")
        raise
    finally:
        db.close()


def test_entry():
    """pytest wrapper"""
    run_entry_test()


if __name__ == "__main__":
    run_entry_test()