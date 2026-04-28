"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           EXIT TEST — Damanat PMS                                           ║
║                                                                              ║
║  Simulates a car leaving its slot and exiting the facility.                 ║
║  Finds the open session for the plate automatically (created by             ║
║  test_entry.py), then writes exit events and verifies via API Gateway.      ║
║                                                                              ║
║  slot_name / floor / floor_id are resolved automatically from parking_slots.║
║  Run AFTER test_entry.py.                                                   ║
║                                                                              ║
║  How to run:                                                                 ║
║    python tests/test_exit.py                                                 ║
║    pytest tests/test_exit.py -v                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys, os
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# ─── CONFIG — only change values here ─────────────────────────────────────────
CONFIG = {
    "plate_number":   "abc-8976",
    "exit_camera_id": "EXIT-GATE",
    "exit_snapshot":  "",
    "session_id_override": None,
    "cleanup_after": True,
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
from app.database import SessionLocal

client = TestClient(app, raise_server_exceptions=True)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]


# ═══════════════════════════════════════════════════════════════════════════════
#  SLOT RESOLVER — reads slot details directly from parking_slots
# ═══════════════════════════════════════════════════════════════════════════════

def resolve_slot(db: Session, slot_id: str) -> dict:
    """
    Look up slot_name, floor, floor_id from parking_slots.
    slot_id is taken from the open parking_session — not from CONFIG.
    """
    row = db.execute(text("""
        SELECT slot_id, slot_name, floor, floor_id, is_available
        FROM parking_slots
        WHERE slot_id = :s
    """), {"s": slot_id}).fetchone()

    if not row:
        fail(
            f"Slot '{slot_id}' not found in parking_slots.\n"
            f"    This slot_id came from the open parking_session — "
            f"check whether it was written correctly by test_entry.py."
        )

    return {
        "slot_id":      row[0],
        "slot_name":    row[1],
        "floor":        row[2],
        "floor_id":     row[3],
        "is_available": bool(row[4]),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  DB WRITES
# ═══════════════════════════════════════════════════════════════════════════════

def db_find_open_session(db: Session, plate: str) -> dict | None:
    """Return the most recent open parking session for this plate."""
    row = db.execute(text("""
        SELECT TOP 1 id, entry_time, slot_id
        FROM parking_sessions
        WHERE plate_number = :p AND status = 'open'
        ORDER BY entry_time DESC
    """), {"p": plate}).fetchone()
    if not row:
        return None
    return {"id": row[0], "entry_time": row[1], "slot_id": row[2]}


def db_slot_available(db: Session, slot: dict):
    """Phase 3 — car drives out of the slot."""
    db.execute(text("""
        INSERT INTO slot_status (slot_id, plate_number, status, time)
        VALUES (:slot, NULL, 'available', :ts)
    """), {"slot": slot["slot_id"], "ts": _now()})
    db.execute(text("""
        UPDATE parking_slots SET is_available = 1 WHERE slot_id = :slot
    """), {"slot": slot["slot_id"]})
    db.commit()
    info(f"slot_status INSERT   → slot={slot['slot_id']}  status=available")
    info(f"parking_slots UPDATE → slot={slot['slot_id']}  is_available=1")


def db_record_slot_left(db: Session, session_id: int):
    db.execute(text("""
        UPDATE parking_sessions SET slot_left_at = :ts WHERE id = :id
    """), {"ts": _now(), "id": session_id})
    db.commit()
    info(f"parking_sessions UPDATE → id={session_id}  slot_left_at=NOW")


def db_insert_exit_log(db: Session, plate: str, cfg: dict) -> int:
    row = db.execute(text("""
        INSERT INTO entry_exit_log
            (plate_number, gate, camera_id, event_time, snapshot_path, is_test)
        OUTPUT INSERTED.id
        VALUES (:plate, 'exit', :cam, :ts, :snap, 1)
    """), {
        "plate": plate,
        "cam":   cfg["exit_camera_id"],
        "ts":    _now(),
        "snap":  cfg["exit_snapshot"],
    }).fetchone()
    db.commit()
    info(f"entry_exit_log INSERT  → id={row[0]}  gate=exit")
    return row[0]


def db_update_zone_occupancy(db: Session, floor: str, delta: int):
    """
    Increment/decrement current_count in zone_occupancy for the floor zone
    and the GARAGE-TOTAL row.
    """
    db.execute(text("""
        UPDATE zone_occupancy
        SET current_count = CASE 
            WHEN current_count + :d < 0 THEN 0 
            ELSE current_count + :d 
        END,
        last_updated = :ts
        WHERE floor = :f AND zone_id != 'GARAGE-TOTAL'
    """), {"d": delta, "f": floor, "ts": _now()})

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


def db_close_session(db: Session, session_id: int, cfg: dict, entry_time) -> int:
    now = datetime.now(timezone.utc)
    if entry_time:
        if entry_time.tzinfo is None:
            entry_time = entry_time.replace(tzinfo=timezone.utc)
        duration = max(int((now - entry_time).total_seconds()), 1)
    else:
        duration = 0

    db.execute(text("""
        UPDATE parking_sessions
        SET exit_time          = :exit_time,
            exit_camera_id     = :cam,
            exit_snapshot_path = :snap,
            duration_seconds   = :dur,
            status             = 'closed'
        WHERE id = :id
    """), {
        "exit_time": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
        "cam":       cfg["exit_camera_id"],
        "snap":      cfg["exit_snapshot"],
        "dur":       duration,
        "id":        session_id,
    })
    db.commit()
    info(f"parking_sessions UPDATE → id={session_id}  status=closed  duration={duration}s")
    return duration


# ═══════════════════════════════════════════════════════════════════════════════
#  API CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

def api_find_session(plate: str) -> dict | None:
    r = client.get("/entry-exit/", params={"search": plate, "page_size": 5})
    assert r.status_code == 200, f"GET /entry-exit/ → {r.status_code}: {r.text}"
    items = r.json().get("items", [])
    return items[0] if items else None


def api_get_slot(slot_id: str) -> dict | None:
    r = client.get(f"/occupancy/slots/{slot_id}")
    if r.status_code == 404:
        return None
    assert r.status_code == 200, f"GET /occupancy/slots/{slot_id} → {r.status_code}: {r.text}"
    return r.json()


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def run_exit_test():
    cfg   = CONFIG
    plate = cfg["plate_number"]

    print(f"\n{BOLD}{'═'*70}")
    print(f"  EXIT TEST  |  Plate: {plate}")
    print(f"{'═'*70}{RESET}\n")

    db: Session = SessionLocal()
    created_log_id = None
    session_id     = None
    slot           = None

    try:

        # ── Pre-flight ────────────────────────────────────────────────────────
        header("Pre-flight checks")

        # Find the open session
        if cfg["session_id_override"]:
            row = db.execute(text(
                "SELECT id, entry_time, slot_id FROM parking_sessions WHERE id = :id"
            ), {"id": cfg["session_id_override"]}).fetchone()
            if not row:
                fail(f"session_id_override={cfg['session_id_override']} not found.")
            session = {"id": row[0], "entry_time": row[1], "slot_id": row[2]}
            info(f"Using session_id_override = {session['id']}")
        else:
            session = db_find_open_session(db, plate)
            if not session:
                fail(
                    f"No open parking session found for plate '{plate}'.\n"
                    f"    Run test_entry.py first, or set CONFIG['session_id_override']."
                )

        session_id = session["id"]
        entry_time = session["entry_time"]
        ok(f"Found open session  id={session_id}  entry_time={entry_time}")

        # Resolve slot details from DB using the slot_id stored on the session
        session_slot_id = session.get("slot_id")
        if session_slot_id:
            slot = resolve_slot(db, session_slot_id)
            ok(
                f"Slot resolved from DB:\n"
                f"      slot_id   = {slot['slot_id']}\n"
                f"      slot_name = {slot['slot_name']}\n"
                f"      floor     = {slot['floor']}\n"
                f"      floor_id  = {slot['floor_id']}\n"
                f"      available = {slot['is_available']}"
            )
        else:
            warn("Session has no slot_id — slot was never assigned. "
                 "Slot-leave steps will be skipped.")

        # ── Phase 3: Car leaves the slot ──────────────────────────────────────
        if slot:
            header(f"Phase 3 — Car leaves slot {slot['slot_id']} ({slot['slot_name']})")

            db_slot_available(db, slot)
            db_record_slot_left(db, session_id)

            info(f"Calling GET /occupancy/slots/{slot['slot_id']} …")
            slot_api = api_get_slot(slot["slot_id"])
            if slot_api:
                is_avail   = slot_api.get("is_available")
                cur_status = (slot_api.get("current_status") or "").upper()
                ok(
                    f"Slot API response:\n"
                    f"      is_available   = {is_avail}\n"
                    f"      current_status = {cur_status or '(none)'}"
                )
                freed = is_avail is True or cur_status in (
                    "VACANT", "AVAILABLE", "EMPTY", "FREE", ""
                )
                assert freed, \
                    f"Slot should be free now, got is_available={is_avail} status='{cur_status}'"
                ok("Slot is free again ✓")

            info("Calling GET /entry-exit/?search=<plate> …")
            s = api_find_session(plate)
            if s:
                assert s.get("slot_left_at"), "slot_left_at should be set on the session"
                ok("slot_left_at is set ✓")
        else:
            header("Phase 3 — Skipped (no slot was assigned to this session)")

        # ── Phase 4: Car exits the gate ───────────────────────────────────────
        header("Phase 4 — Car exits the facility gate")

        created_log_id = db_insert_exit_log(db, plate, cfg)
        duration       = db_close_session(db, session_id, cfg, entry_time)
        
        # Update occupancy (Video Analytics line-crossing simulation)
        if slot:
            db_update_zone_occupancy(db, slot["floor"], -1)
        
        info("Calling GET /entry-exit/?search=<plate> …")
        s = api_find_session(plate)
        if not s:
            fail(f"Session for '{plate}' not visible via API after exit.")

        assert s["status"] == "closed", \
            f"Expected status='closed', got '{s['status']}'"
        ok("Session status = 'closed' ✓")

        assert s.get("exit") is not None, "exit event should be present on the session"
        ok("exit event is present ✓")

        api_dur = s.get("duration_seconds")
        assert api_dur and api_dur > 0, \
            f"Expected duration_seconds > 0, got {api_dur}"
        ok(f"duration_seconds = {api_dur}s  ({api_dur // 60}m {api_dur % 60}s) ✓")

        exit_evt = s.get("exit") or {}
        assert exit_evt.get("event_time"), "exit.event_time should be set"
        ok(f"exit.event_time = {exit_evt.get('event_time')} ✓")

        # ── Done ──────────────────────────────────────────────────────────────
        header("✅  Exit test PASSED")
        slot_label = f"{slot['slot_id']} ({slot['slot_name']})" if slot else "N/A"
        print(f"""
  {GREEN}{BOLD}Summary:{RESET}
    Plate                : {plate}
    Slot                 : {slot_label}
    Floor                : {slot['floor'] if slot else 'N/A'}
    parking_session id   : {session_id}  → status=closed
    exit entry_exit_log  : {created_log_id}
    Duration             : {duration}s  ({duration // 60}m {duration % 60}s)
""")

    except AssertionError as e:
        print(f"\n  {RED}{BOLD}EXIT TEST FAILED:{RESET} {e}\n")
        raise

    finally:
        if cfg["cleanup_after"] and session_id:
            header("Cleanup — removing all test data")
            try:
                db.execute(text(
                    "DELETE FROM parking_sessions WHERE id = :id"
                ), {"id": session_id})
                info(f"Deleted parking_sessions id={session_id}")

                # Remove all is_test entry_exit_log rows for this plate
                db.execute(text("""
                    DELETE FROM entry_exit_log
                    WHERE plate_number = :p AND is_test = 1
                """), {"p": plate})
                info(f"Deleted entry_exit_log rows (is_test=1) for plate={plate}")

                # Remove slot_status rows written during the test
                if slot:
                    db.execute(text("""
                        DELETE FROM slot_status
                        WHERE slot_id = :slot
                          AND (plate_number = :p OR plate_number IS NULL)
                    """), {"slot": slot["slot_id"], "p": plate})
                    info(f"Deleted slot_status rows for slot={slot['slot_id']}")

                    # Restore slot availability
                    db.execute(text(
                        "UPDATE parking_slots SET is_available = 1 WHERE slot_id = :s"
                    ), {"s": slot["slot_id"]})
                    info(f"Restored parking_slots.is_available=1 for slot={slot['slot_id']}")

                db.commit()
                ok("All test data cleaned up ✓")
            except Exception as ex:
                warn(f"Cleanup error: {ex} — you may need to clean up manually.")
        elif not cfg["cleanup_after"]:
            warn(
                f"Cleanup skipped (cleanup_after=False).\n"
                f"    Manually delete:\n"
                f"      DELETE FROM parking_sessions WHERE id = {session_id};\n"
                f"      DELETE FROM entry_exit_log WHERE plate_number = '{plate}' AND is_test = 1;\n"
                + (f"      DELETE FROM slot_status WHERE slot_id = '{slot['slot_id']}';\n"
                   f"      UPDATE parking_slots SET is_available = 1 WHERE slot_id = '{slot['slot_id']}';"
                   if slot else "")
            )

        db.close()


def test_exit():
    """pytest wrapper"""
    run_exit_test()


if __name__ == "__main__":
    run_exit_test()