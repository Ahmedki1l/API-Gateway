"""Shared helpers for the Damanat PMS lifecycle simulation scripts.

This module is the contract between the simulator scripts (01_*..06_*) and
exposes:
  - default URLs (PMS-AI :8080, Gateway :8001) and facility timezone (+03:00)
  - timestamp helpers (now_facility_iso / now_facility_dt)
  - HTTP helpers (http_session, post_camera_event, post_internal)
  - Gateway verification GETs (vehicles, entry_exit, dashboard, occupancy, alerts)
  - Output helpers (green / red / yellow / cyan / expect)
  - poll_until() polling helper
  - Hikvision-shape payload builders (XML for ANPR, JSON for AccessControllerEvent)
  - load_test_image() — reads _fixtures/tiny.jpg

Sister scripts import these names; do NOT rename or change signatures.
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path
from typing import Callable, Optional

# Windows console defaults to cp1252 — force UTF-8 (and fall back gracefully on
# legacy Python builds where reconfigure isn't available). Without this, every
# call to red()/green()/yellow() that emits ✅/❌/🔍 raises UnicodeEncodeError
# and crashes the calling simulator. errors="replace" so a missing glyph in
# any future emoji decays to '?' instead of crashing.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ── Defaults
# PMS-AI binds to BACKEND_IP=5.5.5.2 in damanat-backend/.env but is reachable
# from this dev box at 5.5.5.1. Override either default via env vars
# (PMS_AI_URL / GATEWAY_URL) or the per-script --pms-ai / --gateway flags.
PMS_AI_DEFAULT = os.environ.get("PMS_AI_URL", "http://5.5.5.1:8080")
GATEWAY_DEFAULT = os.environ.get("GATEWAY_URL", "http://localhost:8001")
FACILITY_OFFSET_HOURS = 3
_FACILITY_TZ = dt.timezone(dt.timedelta(hours=FACILITY_OFFSET_HOURS))
_FIXTURES_DIR = Path(__file__).parent / "_fixtures"

# ── ANSI color codes (no external colorama dep)
_RESET = "\033[0m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"


# ── Timestamp helpers ─────────────────────────────────────────────────────────
def now_facility_dt() -> dt.datetime:
    """Return tz-aware `datetime` in facility offset (+03:00)."""
    return dt.datetime.now(_FACILITY_TZ)


def now_facility_iso() -> str:
    """ISO-8601 timestamp with +03:00 offset, e.g. 2026-05-04T10:00:00.123+03:00."""
    return now_facility_dt().isoformat(timespec="milliseconds")


# ── HTTP plumbing ─────────────────────────────────────────────────────────────
def http_session() -> requests.Session:
    """Long-lived `requests.Session` with sensible retries + a default timeout."""
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
    )
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.request_timeout = 10  # used by helpers below
    return s


def _timeout(session: requests.Session) -> float:
    return getattr(session, "request_timeout", 10)


def post_camera_event(
    session: requests.Session,
    pms_ai_url: str,
    payload_xml: Optional[str] = None,
    payload_json: Optional[dict] = None,
    image_bytes: Optional[bytes] = None,
) -> requests.Response:
    """POST a camera event to PMS-AI's `/api/v1/events/camera`.

    - If `image_bytes` is provided, use multipart/form-data (Hikvision style:
      one metadata part + one image/jpeg part). The metadata part is the XML
      when given, otherwise a JSON dump of `payload_json`.
    - Else `payload_xml` → application/xml.
    - Else `payload_json` → application/json.
    """
    url = pms_ai_url.rstrip("/") + "/api/v1/events/camera"
    if image_bytes is not None:
        if payload_xml is not None:
            files = {
                "EventInfo": ("event.xml", payload_xml.encode("utf-8"), "application/xml"),
                "image": ("snapshot.jpg", image_bytes, "image/jpeg"),
            }
        else:
            import json as _json
            body = _json.dumps(payload_json or {}).encode("utf-8")
            files = {
                "EventInfo": ("event.json", body, "application/json"),
                "image": ("snapshot.jpg", image_bytes, "image/jpeg"),
            }
        return session.post(url, files=files, timeout=_timeout(session))
    if payload_xml is not None:
        return session.post(
            url,
            data=payload_xml.encode("utf-8"),
            headers={"Content-Type": "application/xml"},
            timeout=_timeout(session),
        )
    if payload_json is not None:
        return session.post(url, json=payload_json, timeout=_timeout(session))
    raise ValueError("post_camera_event: pass payload_xml, payload_json, or image_bytes")


def post_internal(session: requests.Session, pms_ai_url: str, route: str, payload: dict) -> requests.Response:
    """POST to PMS-AI's `/api/v1/internal/{route}` (e.g. `parking-sessions/bind-slot`)."""
    url = pms_ai_url.rstrip("/") + "/api/v1/internal/" + route.lstrip("/")
    return session.post(url, json=payload, timeout=_timeout(session))


# ── Gateway verification GETs ─────────────────────────────────────────────────
def get_vehicle_by_plate(session: requests.Session, gateway_url: str, plate: str) -> Optional[dict]:
    """Return the first vehicles row matching plate (or None)."""
    r = session.get(
        gateway_url.rstrip("/") + "/vehicles/",
        params={"search": plate, "page_size": 5},
        timeout=_timeout(session),
    )
    r.raise_for_status()
    items = (r.json() or {}).get("items") or []
    for v in items:
        if (v.get("plate_number") or "").upper() == plate.upper():
            return v
    return items[0] if items else None


def get_entry_exit_event(session: requests.Session, gateway_url: str, event_id: int) -> dict:
    r = session.get(
        gateway_url.rstrip("/") + f"/entry-exit/{event_id}",
        timeout=_timeout(session),
    )
    r.raise_for_status()
    return r.json()


def get_recent_entry_exit(session: requests.Session, gateway_url: str, plate: str, limit: int = 5) -> list[dict]:
    r = session.get(
        gateway_url.rstrip("/") + "/entry-exit/",
        params={"search": plate, "page_size": limit},
        timeout=_timeout(session),
    )
    r.raise_for_status()
    return (r.json() or {}).get("items") or []


def get_dashboard_kpis(session: requests.Session, gateway_url: str) -> dict:
    r = session.get(gateway_url.rstrip("/") + "/dashboard/kpis", timeout=_timeout(session))
    r.raise_for_status()
    return r.json()


def get_occupancy_slot(session: requests.Session, gateway_url: str, slot_id: str) -> dict:
    r = session.get(
        gateway_url.rstrip("/") + f"/occupancy/slots/{slot_id}",
        timeout=_timeout(session),
    )
    r.raise_for_status()
    return r.json()


def get_alerts_for_plate(session: requests.Session, gateway_url: str, plate: str, limit: int = 5) -> list[dict]:
    r = session.get(
        gateway_url.rstrip("/") + "/alerts/",
        params={"search": plate, "page_size": limit},
        timeout=_timeout(session),
    )
    r.raise_for_status()
    return (r.json() or {}).get("items") or []


def get_alerts_for_slot(
    session: requests.Session,
    gateway_url: str,
    slot_id: str,
    *,
    alert_type: Optional[str] = None,
    only_open: bool = True,
    limit: int = 10,
) -> list[dict]:
    """Fetch the most recent /alerts/ rows touching this slot. Filters
    client-side because the Gateway's slot_id query param expects an exact
    match on the alert.slot_id column and the simulator wants flexibility
    (e.g. open-only filter)."""
    params: dict = {"page_size": limit}
    if alert_type:
        params["alert_type"] = alert_type
    r = session.get(
        gateway_url.rstrip("/") + "/alerts/",
        params=params,
        timeout=_timeout(session),
    )
    r.raise_for_status()
    items = (r.json() or {}).get("items") or []
    out = []
    for a in items:
        if (a.get("slot_id") or "") != slot_id:
            continue
        if only_open and a.get("is_resolved"):
            continue
        out.append(a)
    return out


def slot_is_violation_zone(slot_id: str) -> Optional[bool]:
    """Hit MSSQL directly to read parking_slots.is_violation_zone. Returns
    None if the connection fails or the slot isn't found — caller treats
    that as 'unknown, skip the assertion'."""
    conn = _connect_db()
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT TOP 1 is_violation_zone FROM parking_slots WHERE slot_id = ?", slot_id)
        row = cur.fetchone()
        if row is None:
            return None
        return bool(row[0])
    except Exception:  # noqa: BLE001
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ── Output helpers ────────────────────────────────────────────────────────────
def green(msg: str) -> None:
    print(f"{_GREEN}✅ {msg}{_RESET}")


def red(msg: str) -> None:
    print(f"{_RED}❌ {msg}{_RESET}")


def yellow(msg: str) -> None:
    print(f"{_YELLOW}\U0001F50D {msg}{_RESET}")


def cyan(msg: str) -> None:
    print(f"{_CYAN}{msg}{_RESET}")


def expect(cond: bool, ok_msg: str, fail_msg: str) -> bool:
    """One-line assertion: print green if `cond`, red otherwise. Returns `cond`."""
    if cond:
        green(ok_msg)
    else:
        red(fail_msg)
    return bool(cond)


# ── Polling ───────────────────────────────────────────────────────────────────
def poll_until(check: Callable[[], bool], timeout: float = 5.0, interval: float = 0.5) -> bool:
    """Re-run `check()` every `interval` seconds until it returns truthy or
    `timeout` elapses. Returns True on success, False on timeout. Exceptions
    raised by `check` are caught — they count as a failed attempt."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            if check():
                return True
        except Exception:
            pass
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval)


# ── Payload builders ──────────────────────────────────────────────────────────
def build_anpr_xml(plate: str, camera_id: str, ip: str, dt_iso: str) -> str:
    """Hikvision ISAPI ANPR EventNotificationAlert XML — exact production shape."""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<EventNotificationAlert version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">\n'
        f'<ipAddress>{ip}</ipAddress>\n'
        '<ipv6Address>::</ipv6Address>\n'
        '<protocol>HTTP</protocol>\n'
        '<macAddress>e8:a0:ed:2f:0e:46</macAddress>\n'
        '<dynChannelID>1</dynChannelID>\n'
        '<channelID>1</channelID>\n'
        f'<dateTime>{dt_iso}</dateTime>\n'
        '<activePostCount>1</activePostCount>\n'
        '<eventType>ANPR</eventType>\n'
        '<eventState>active</eventState>\n'
        '<eventDescription>ANPR</eventDescription>\n'
        f'<channelName>{camera_id}</channelName>\n'
        '<deviceID>88</deviceID>\n'
        '<ANPR>\n'
        '<country>77</country>\n'
        f'<licensePlate>{plate}</licensePlate>\n'
        '<line>1</line>\n'
        '<direction>forward</direction>\n'
        '<confidenceLevel>95</confidenceLevel>\n'
        '<plateType>private</plateType>\n'
        '<plateColor>white</plateColor>\n'
        '<vehicleType>vehicle</vehicleType>\n'
        '<detectDir>2</detectDir>\n'
        '<detectType>2</detectType>\n'
        '<barrierGateCtrlType>0</barrierGateCtrlType>\n'
        '<vehicleInfo>\n'
        '<index>112</index>\n'
        '<color>white</color>\n'
        '</vehicleInfo>\n'
        '</ANPR>\n'
        '</EventNotificationAlert>\n'
    )


def build_access_controller_event_json(plate: str, camera_id: str, dt_iso: str) -> dict:
    """Hikvision AccessControllerEvent JSON shape (used by some camera models
    instead of the XML ANPR event)."""
    return {
        "ipAddress": "0.0.0.0",
        "portNo": 80,
        "protocol": "HTTP",
        "macAddress": "e8:a0:ed:2f:0e:46",
        "channelID": 1,
        "dateTime": dt_iso,
        "activePostCount": 1,
        "eventType": "AccessControllerEvent",
        "eventState": "active",
        "eventDescription": "Access Controller Event",
        "channelName": camera_id,
        "AccessControllerEvent": {
            "deviceName": camera_id,
            "majorEventType": 5,
            "subEventType": 75,
            "cardReaderKind": 1,
            "cardReaderNo": 1,
            "name": plate,
            "cardNo": plate,
            "licensePlate": plate,
            "currentVerifyMode": "cardOrFaceOrFp",
        },
    }


def load_test_image() -> bytes:
    """Return the bytes of the bundled tiny.jpg test fixture."""
    p = _FIXTURES_DIR / "tiny.jpg"
    if not p.exists():
        red(f"Missing fixture: {p}")
        sys.exit(2)
    return p.read_bytes()


# ── DB-truth verification (read-only) ────────────────────────────────────────
def _gateway_env_path() -> Path:
    """Locate API-Gateway/.env relative to this file."""
    return Path(__file__).resolve().parents[2] / ".env"


def _load_db_dsn_from_env() -> Optional[str]:
    """Build an ODBC DSN from API-Gateway/.env. Returns None if unreadable."""
    env_file = _gateway_env_path()
    if not env_file.exists():
        return None
    cfg: dict[str, str] = {}
    for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        cfg[k.strip()] = v.strip().strip('"').strip("'")
    driver = cfg.get("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    server = cfg.get("DB_SERVER", "localhost")
    port = cfg.get("DB_PORT", "1433")
    db = cfg.get("DB_NAME", "damanat_pms")
    user = cfg.get("DB_USER", "sa")
    pwd = cfg.get("DB_PASSWORD", "")
    return (
        f"DRIVER={{{driver}}};SERVER={server},{port};DATABASE={db};"
        f"UID={user};PWD={pwd};TrustServerCertificate=yes;Encrypt=no"
    )


def _connect_db():
    """Return an open pyodbc connection or None if pyodbc/DSN unavailable."""
    try:
        import pyodbc
    except ImportError:
        return None
    dsn = _load_db_dsn_from_env()
    if not dsn:
        return None
    try:
        return pyodbc.connect(dsn, timeout=5, autocommit=False)
    except Exception as exc:  # noqa: BLE001
        red(f"DB connect failed: {exc!r}")
        return None


def va_write_slot_status(
    slot_id: str,
    plate: str,
    *,
    is_parked: bool,
    camera_id: str = "CAM-03",
    snapshot_path: Optional[str] = None,
) -> bool:
    """Mirror VideoAnalytics' slot_status_service.log_vehicle_event side
    effects (without the PMS-AI bind callback, which the simulator scripts
    fire separately): insert a new `slot_status` row with status='occupied'
    or 'available', toggle `parking_slots.is_available`, AND on a park into a
    `is_violation_zone` slot create a `vehicle_intrusion` alert with a
    snapshot path (mirrors `alert_service.report_alert`). On a leave, resolve
    any open alert on that slot.

    Returns True on a successful commit, False on any failure (caller
    decides whether to abort or treat as informational).
    """
    conn = _connect_db()
    if conn is None:
        return False
    status_value = "occupied" if is_parked else "available"
    try:
        cur = conn.cursor()
        # 1. Toggle parking_slots.is_available (VA does this first).
        cur.execute(
            "UPDATE parking_slots SET is_available = ? WHERE slot_id = ?",
            0 if is_parked else 1, slot_id,
        )
        if cur.rowcount == 0:
            red(f"va_write_slot_status: slot {slot_id!r} not in parking_slots")
            conn.rollback()
            return False
        # 2. Append a new slot_status row (VA appends, never updates).
        cur.execute(
            "INSERT INTO slot_status (slot_id, plate_number, status, time) "
            "VALUES (?, ?, ?, SYSUTCDATETIME())",
            slot_id, plate, status_value,
        )
        # 3. Read slot metadata so we can faithfully mirror alert_service.report_alert.
        cur.execute(
            "SELECT slot_name, zone_id, zone_name, is_violation_zone "
            "FROM parking_slots WHERE slot_id = ?",
            slot_id,
        )
        meta = cur.fetchone()
        if meta is not None:
            slot_name, zone_id, zone_name, is_violation = meta
            zone_name = zone_name or zone_id or slot_id
            slot_label = slot_name or slot_id
            if is_parked and bool(is_violation):
                # Dedupe: VA's report_alert returns the existing active row instead
                # of creating a duplicate when the slot already has an open alert.
                cur.execute(
                    "SELECT TOP 1 id FROM alerts "
                    "WHERE slot_id = ? AND is_resolved = 0 AND alert_type = 'vehicle_intrusion'",
                    slot_id,
                )
                if cur.fetchone() is None:
                    if snapshot_path is None:
                        ts = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                        snapshot_path = (
                            f"alerts/test_vehicle_intrusion_{slot_id}_{camera_id}_{ts}.jpg"
                        )
                    cur.execute(
                        """
                        INSERT INTO alerts
                          (alert_type, camera_id, zone_id, zone_name, slot_id, event_type,
                           slot_number, description, snapshot_path, is_resolved, triggered_at,
                           plate_number, severity)
                        VALUES
                          ('vehicle_intrusion', ?, ?, ?, ?, 'vehicle_detected',
                           ?, ?, ?, 0, SYSUTCDATETIME(),
                           ?, 'critical')
                        """,
                        camera_id, zone_id, zone_name, slot_id,
                        slot_label,
                        f"Unauthorized vehicle detected in {slot_label}",
                        snapshot_path,
                        plate,
                    )
            elif not is_parked:
                # Resolve any open alerts on this slot — mirrors alert_service.resolve_alert.
                cur.execute(
                    "UPDATE alerts SET is_resolved = 1, resolved_at = SYSUTCDATETIME() "
                    "WHERE slot_id = ? AND is_resolved = 0",
                    slot_id,
                )
        conn.commit()
        return True
    except Exception as exc:  # noqa: BLE001
        red(f"va_write_slot_status error: {exc!r}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def verify_closed_session_in_db(plate: str) -> tuple[bool, dict[str, bool]]:
    """Hit MSSQL directly and assert the most-recent parking_sessions row for
    `plate` is fully closed: status='closed', exit_time set, slot_left_at set
    (when the session ever held a slot), duration_seconds > 0, and the
    matching vehicles row has current_slot_id NULL.

    Returns (ok, {field_label: bool}). Empty dict means the connection
    failed — caller should treat as "skipped" rather than failure.
    """
    try:
        import pyodbc
    except ImportError:
        return False, {}
    dsn = _load_db_dsn_from_env()
    if not dsn:
        return False, {}
    fields: dict[str, bool] = {}
    try:
        conn = pyodbc.connect(dsn, timeout=5)
        cur = conn.cursor()
        cur.execute(
            "SELECT TOP 1 status, exit_time, slot_id, slot_left_at, duration_seconds "
            "FROM parking_sessions WHERE plate_number = ? "
            "ORDER BY id DESC",
            plate,
        )
        row = cur.fetchone()
        if row is None:
            return False, {"parking_sessions row exists": False}
        status, exit_time, slot_id, slot_left_at, duration = row
        fields["parking_sessions.status == 'closed'"] = status == "closed"
        fields["parking_sessions.exit_time IS NOT NULL"] = exit_time is not None
        fields["parking_sessions.duration_seconds > 0"] = (duration or 0) > 0
        # slot_left_at only required when the session ever had a slot bound.
        fields["parking_sessions.slot_left_at consistent with slot_id"] = (
            slot_left_at is not None if slot_id is not None else True
        )
        cur.execute(
            "SELECT TOP 1 current_slot_id FROM vehicles WHERE plate_number = ? ORDER BY id DESC",
            plate,
        )
        vrow = cur.fetchone()
        if vrow is not None:
            fields["vehicles.current_slot_id IS NULL"] = vrow[0] in (None, "")
        cur.close()
        conn.close()
    except Exception as exc:  # noqa: BLE001
        red(f"DB-truth probe error: {exc!r}")
        return False, {}
    return all(fields.values()), fields
