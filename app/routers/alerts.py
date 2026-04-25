import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional
 
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
 
from app.config import facility_today_utc
from app.database import get_db, rows, scalar
from app.routers._helpers import _floor_schema, resolve_floor_id
from app.schemas import (
    AlertDetail,
    AlertItem,
    AlertStats,
    CameraRef,
    EntityActionResponse,
    PagedResponse,
    SlotRef,
    SuccessResponse,
    VehicleRef,
)
from app.services.auth import require_internal_token
from app.services.upstream import iter_system1_alert_events, iter_system2_alert_events
from app.services.bus import alerts_bus
from app.shared import build_paged, stream_csv
 
router = APIRouter(prefix="/alerts", tags=["Alerts"])
 
 
@lru_cache(maxsize=None)
def _alerts_extra_cols() -> dict:
    """Cached probe of which optional columns exist on dbo.alerts. Drives
    the conditional SELECT bits below — missing columns become `NULL AS col`
    so the response shape stays stable.

    The audit columns (vehicle_id, vehicle_event_id, triggering_camera_event_id,
    resolved_by, resolution_notes) only appear after the Phase 4A migration
    has run; the original columns (severity, location_display, slot_id) come
    from the older fix_system1_schema.sql."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        def exists(col: str) -> bool:
            n = db.execute(text("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'alerts' AND COLUMN_NAME = :c
            """), {"c": col}).scalar()
            return (n or 0) > 0

        return {
            # Phase 1 columns
            "severity":         exists("severity"),
            "location_display": exists("location_display"),
            "slot_id":          exists("slot_id"),
            # Phase 4A audit columns
            "vehicle_id":                  exists("vehicle_id"),
            "vehicle_event_id":            exists("vehicle_event_id"),
            "triggering_camera_event_id":  exists("triggering_camera_event_id"),
            "resolved_by":                 exists("resolved_by"),
            "resolution_notes":            exists("resolution_notes"),
            # Always present in current schema but probed for completeness
            "event_type":                  exists("event_type"),
        }
    finally:
        db.close()
 

def _alert_query_bits(cols: dict) -> dict[str, str]:
    """
    Build SQL expression fragments based on which columns exist in the alerts table.
    parking_slots is always joined to get the real human-readable slot_name.
    """
    if cols["slot_id"]:
        # alerts has its own slot_id foreign key → join parking_slots directly
        slot_join = """
            LEFT JOIN parking_slots pk ON pk.slot_id = a.slot_id
        """
        slot_id_expr   = "a.slot_id"
        slot_name_expr = "COALESCE(pk.slot_name, a.slot_number, a.slot_id)"
        zone_id_expr   = "a.zone_id"
        zone_name_expr = "a.zone_name"
    else:
        # pre-migration: zone_id on alerts is the closest thing to a slot reference
        slot_join = """
            LEFT JOIN parking_slots pk ON pk.slot_id = a.zone_id
        """
        slot_id_expr   = "a.zone_id"
        slot_name_expr = "COALESCE(pk.slot_name, a.slot_number, a.zone_id)"
        zone_id_expr   = "a.zone_id"
        zone_name_expr = "a.zone_name"
 
    severity_expr = (
        "a.severity"
        if cols["severity"]
        else (
            "CASE "
            "WHEN a.alert_type IN ('violence','intrusion','vehicle_intrusion','vehicle_violation') THEN 'critical' "
            "WHEN a.alert_type IN ('unknown_vehicle','named_slot_violation','overstay','capacity_exceeded') THEN 'warning' "
            "ELSE 'info' END"
        )
    )
 
    location_expr = (
        "a.location_display"
        if cols["location_display"]
        else (
            f"CASE "
            f"WHEN {slot_name_expr} IS NOT NULL THEN {slot_name_expr} "
            f"WHEN {zone_name_expr} IS NOT NULL THEN {zone_name_expr} "
            f"ELSE a.camera_id END"
        )
    )
 
    return {
        "slot_join":       slot_join,
        "slot_id_expr":    slot_id_expr,
        "slot_name_expr":  slot_name_expr,
        "zone_id_expr":    zone_id_expr,
        "zone_name_expr":  zone_name_expr,
        "severity_expr":   severity_expr,
        "location_expr":   location_expr,
    }
 
 
def _where(search, severity, alert_type, resolved, date_from, date_to, cols, floor_id=None, floor=None):
    bits = _alert_query_bits(cols)
    schema = _floor_schema()
    clauses = ["a.is_test = 0"]
    params: dict = {}

    if search:
        clauses.append(
            "("
            "a.plate_number LIKE :search OR "
            f"{bits['slot_id_expr']} LIKE :search OR "
            f"{bits['slot_name_expr']} LIKE :search OR "
            f"{bits['zone_name_expr']} LIKE :search OR "
            "a.description LIKE :search"
            ")"
        )
        params["search"] = f"%{search}%"

    if severity:
        if cols["severity"]:
            clauses.append("a.severity = :severity")
            params["severity"] = severity
        else:
            if severity == "critical":
                clauses.append("a.alert_type IN ('violence','intrusion','vehicle_intrusion','vehicle_violation')")
            elif severity == "warning":
                clauses.append("a.alert_type IN ('unknown_vehicle','named_slot_violation','overstay','capacity_exceeded')")
            else:
                clauses.append("a.alert_type NOT IN ('violence','intrusion','vehicle_intrusion','vehicle_violation','unknown_vehicle','named_slot_violation','overstay','capacity_exceeded')")

    if alert_type:
        clauses.append("a.alert_type = :alert_type")
        params["alert_type"] = alert_type

    if resolved is not None:
        clauses.append("a.is_resolved = :resolved")
        params["resolved"] = 1 if resolved else 0

    if date_from:
        clauses.append("CAST(a.triggered_at AS DATE) >= :date_from")
        params["date_from"] = str(date_from)

    if date_to:
        clauses.append("CAST(a.triggered_at AS DATE) <= :date_to")
        params["date_to"] = str(date_to)

    # WS-8: build IN-list from columns that actually exist in this DB.
    # Older deployments don't have `cameras.watches_floor`.
    floor_targets = ["pk.floor"]
    if schema["cameras_watches_floor"]:
        floor_targets.append("c.watches_floor")
    floor_in_list = ", ".join(floor_targets)

    if floor_id is not None and schema["floors_table"]:
        # WS-8: filter by floor name resolved from id; matches the COALESCE on floor used in SELECT.
        clauses.append(
            "(SELECT name FROM floors WHERE id = :floor_id) "
            f"IN ({floor_in_list})"
        )
        params["floor_id"] = floor_id
    elif floor:
        # Pre-migration fallback (or legacy callers): match the legacy string `floor`
        # against the available floor columns.
        clauses.append(f":floor IN ({floor_in_list})")
        params["floor"] = floor

    return " AND ".join(clauses), params
 
 
def _normalize_stream_event(source_system: str, payload: dict) -> dict:
    """Translate an upstream SSE payload (PMS-AI, VideoAnalytics, or
    in-process test bus) into the canonical `AlertStreamEventLite` shape.

    Field renames applied:
      - upstream `alert_id` → wire `id`
      - upstream `snapshot_path` → wire `snapshot_url`
      - upstream `timestamp` → wire `triggered_at`  (G-2 fix; keeps SSE
        events using the same field vocabulary as the REST list/detail views)
    """
    slot_name = payload.get("slot_name")
    if not slot_name and payload.get("slot_number"):
        slot_name = str(payload["slot_number"])

    return {
        "id":            payload.get("id") or payload.get("alert_id"),
        "source_system": source_system,
        "alert_type":    payload.get("alert_type"),
        "severity":      payload.get("severity", "info"),
        "slot_id":       payload.get("slot_id"),
        "slot_name":     slot_name,
        "plate_number":  payload.get("plate_number"),
        "camera_id":     payload.get("camera_id"),
        "floor":         payload.get("floor"),
        # WS-8: floor_id on the SSE wire — populated when upstream supplies it; None otherwise.
        "floor_id":      payload.get("floor_id"),
        "snapshot_url":  payload.get("snapshot_url") or payload.get("snapshot_path"),
        # G-2: canonical name on the wire is `triggered_at` (matches AlertItem).
        # Accept legacy `timestamp` from upstream while we wait for upstream
        # services to align.
        "triggered_at":  payload.get("triggered_at") or payload.get("timestamp"),
        "is_alert":      payload.get("is_alert", True),
    }
 
 
async def _pump(source_system: str, iterator, queue: asyncio.Queue):
    try:
        async for event in iterator:
            await queue.put((source_system, event))
        await queue.put((source_system, None))
    except asyncio.CancelledError:
        raise
    finally:
        aclose = getattr(iterator, "aclose", None)
        if aclose:
            await aclose()
 
 
@router.get("/stats", response_model=AlertStats)
async def alert_stats(db: Session = Depends(get_db)):
    cols = _alerts_extra_cols()
    if cols["severity"]:
        critical_sql = "SELECT COUNT(*) FROM alerts WHERE is_resolved=0 AND is_test=0 AND severity='critical'"
    else:
        critical_sql = """
            SELECT COUNT(*) FROM alerts
            WHERE is_resolved=0 AND is_test=0
              AND alert_type IN ('violence','intrusion','vehicle_intrusion','vehicle_violation')
        """

    # facility_today_utc() returns the UTC instant of facility-local midnight today.
    start_of_day_utc = facility_today_utc()

    return AlertStats(
        active_alerts=scalar(db, "SELECT COUNT(*) FROM alerts WHERE is_resolved=0 AND is_test=0") or 0,
        critical_violations=scalar(db, critical_sql) or 0,
        resolved_today=scalar(db, """
            SELECT COUNT(*) FROM alerts
            WHERE is_resolved=1 AND is_test=0
              AND resolved_at >= :start_of_day
        """, {"start_of_day": start_of_day_utc}) or 0,
    )
 
 
@router.get("/", response_model=PagedResponse[AlertItem])
async def get_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    floor: Optional[str] = Query(None),
    floor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    cols = _alerts_extra_cols()
    bits = _alert_query_bits(cols)
    # WS-8 schema-compat shim — branch on each probe so SQL is tolerant of pre-migration DB.
    schema = _floor_schema()
    # WS-8: resolve either floor_id or floor name once; pass the integer to the WHERE builder.
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=floor)
    where, params = _where(
        search, severity, alert_type, resolved, date_from, date_to, cols,
        floor_id=resolved_floor_id, floor=floor,
    )
    params["offset"]    = (page - 1) * page_size
    params["page_size"] = page_size
 
    # Audit columns are conditional on the Phase 4A migration. Emit NULL
    # placeholders when missing so the response shape stays stable for the
    # frontend regardless of DB version (G-6 fix). vehicle_id falls back to
    # v.id (joined from vehicles) when alerts.vehicle_id is null/missing.
    vehicle_id_col = (
        "COALESCE(a.vehicle_id, v.id) AS vehicle_id"
        if cols["vehicle_id"]
        else "v.id AS vehicle_id"
    )
    audit_cols = (
        (", a.vehicle_event_id"           if cols["vehicle_event_id"]           else ", NULL AS vehicle_event_id") +
        (", a.triggering_camera_event_id" if cols["triggering_camera_event_id"] else ", NULL AS triggering_camera_event_id") +
        (", a.resolved_by"                if cols["resolved_by"]                else ", NULL AS resolved_by") +
        (", a.resolution_notes"           if cols["resolution_notes"]           else ", NULL AS resolution_notes")
    )
    event_type_col = "a.event_type" if cols["event_type"] else "NULL AS event_type"

    # WS-8 schema-compat: build the floor expression from the columns that
    # actually exist. Older DBs predate `cameras.watches_floor`, so skip it
    # rather than 500 on `Invalid column name 'watches_floor'`.
    floor_parts = ["pk.floor"]
    if schema["cameras_watches_floor"]:
        floor_parts.append("c.watches_floor")
    floor_expr = (
        f"COALESCE({', '.join(floor_parts)})"
        if len(floor_parts) > 1
        else floor_parts[0]
    )

    # WS-8: floors LEFT JOIN is conditional on the floors table existing (Pattern B).
    if schema["floors_table"]:
        floors_join = f"LEFT JOIN floors f ON f.name = {floor_expr}"
        floor_id_select = "f.id                                AS floor_id"
    else:
        floors_join = ""
        floor_id_select = "NULL                                AS floor_id"

    # WS-8: total query needs the JOINs that the WHERE may reference (cameras/parking_slots).
    total = scalar(db, f"""
        SELECT COUNT(*) FROM alerts a
        {bits["slot_join"]}
        LEFT JOIN cameras c ON c.camera_id = a.camera_id
        {floors_join}
        WHERE {where}
    """, params)
    # WS-8: LEFT JOIN floors on the resolved name so f.id surfaces as floor_id.
    items = rows(db, f"""
        SELECT
            a.id,
            a.alert_type,
            {bits["severity_expr"]}  AS severity,
            {event_type_col},
            a.camera_id,
            a.plate_number,
            {vehicle_id_col},
            {bits["slot_id_expr"]}   AS slot_id,
            {bits["slot_name_expr"]} AS slot_name,
            {floor_expr}             AS floor,
            {floor_id_select},
            {bits["location_expr"]}  AS location,
            a.description,
            a.snapshot_path          AS snapshot_url,
            a.is_resolved,
            a.resolved_at,
            a.triggered_at,
            v.owner_name,
            v.vehicle_type
            {audit_cols}
        FROM alerts a
        {bits["slot_join"]}
        -- G-6: populate vehicle_id / owner_name / vehicle_type
        LEFT JOIN vehicles v ON v.plate_number = a.plate_number
        -- G-6: fall through to camera's watched-floor when alerts/parking_slots have no floor
        LEFT JOIN cameras c ON c.camera_id = a.camera_id
        -- WS-8: integer floor_id alongside the legacy `floor` name string.
        {floors_join}
        WHERE {where}
        ORDER BY a.triggered_at DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)
    return build_paged(items, total or 0, page, page_size)
 
 
ALERT_TEMPLATES = [
    {"alert_type": "violence", "severity": "critical", "description": "Suspicious activity detected in Zone A"},
    {"alert_type": "intrusion", "severity": "critical", "description": "Unauthorized person in restricted area"},
    {"alert_type": "vehicle_intrusion", "severity": "critical", "description": "Unknown vehicle entered restricted zone"},
    {"alert_type": "vehicle_violation", "severity": "critical", "description": "Illegal parking maneuver detected"},
    {"alert_type": "unknown_vehicle", "severity": "warning", "description": "Unregistered plate detected: ABC-123", "plate_number": "ABC-123"},
    {"alert_type": "named_slot_violation", "severity": "warning", "description": "Visitor parked in CEO slot", "slot_id": "CEO-01", "slot_name": "CEO Reserved"},
    {"alert_type": "overstay", "severity": "warning", "description": "Vehicle exceeded 24h limit", "plate_number": "XYZ-999"},
    {"alert_type": "capacity_exceeded", "severity": "info", "description": "Floor 1 is at 95% capacity", "floor": "1"},
]


@router.get("/stream")
async def stream_alerts(request: Request):
    async def event_stream():
        client_queue: asyncio.Queue = asyncio.Queue()
        bus_queue = alerts_bus.subscribe()
        
        async def _bus_pump():
            try:
                while True:
                    event = await bus_queue.get()
                    await client_queue.put(("test_system", event))
            except asyncio.CancelledError:
                pass
            finally:
                alerts_bus.unsubscribe(bus_queue)

        async def _heartbeat():
            try:
                while True:
                    await asyncio.sleep(15)
                    await client_queue.put(("gateway", "heartbeat"))
            except asyncio.CancelledError:
                pass

        tasks = [
            asyncio.create_task(_pump("pms_ai", iter_system1_alert_events(), client_queue)),
            asyncio.create_task(_pump("video_analytics", iter_system2_alert_events(), client_queue)),
            asyncio.create_task(_bus_pump()),
            asyncio.create_task(_heartbeat()),
        ]

        try:
            # connection_established frame — same shape as AlertStreamEventLite.
            yield "data: " + json.dumps({
                "id":            None,
                "source_system": "gateway",
                "alert_type":    "connection_established",
                "severity":      "info",
                "slot_id":       None,
                "slot_name":     None,
                "plate_number":  None,
                "camera_id":     None,
                "floor":         None,
                # WS-8: floor_id mirrors `floor: None` on the keep-alive frame.
                "floor_id":      None,
                "snapshot_url":  None,
                "triggered_at":  None,
                "is_alert":      False,
            }) + "\n\n"
 
            while True:
                if await request.is_disconnected():
                    break

                try:
                    source_system, payload = await asyncio.wait_for(client_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                if payload is None:
                    continue
                
                if payload == "heartbeat":
                    yield ": keep-alive\n\n"
                    continue

                normalized = _normalize_stream_event(source_system, payload)
                yield "data: " + json.dumps(normalized, default=str) + "\n\n"
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
 
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )

@router.get("/test/start", dependencies=[Depends(require_internal_token)])
async def start_continuous_test(interval: float = Query(1.0, ge=0.5, le=60.0)):
    """Start an infinite loop of random test alerts every {interval} seconds.
    Gated behind `X-Internal-Token` so anyone who finds /docs in production
    can't flood the dashboard."""
    alerts_bus.start_test_stream(ALERT_TEMPLATES, interval=interval)
    return {"status": "continuous_stream_started", "interval": interval}


@router.get("/test/stop", dependencies=[Depends(require_internal_token)])
async def stop_continuous_test():
    """Stop the infinite loop of random test alerts.
    Gated behind `X-Internal-Token` (see /test/start)."""
    alerts_bus.stop_test_stream()
    return {"status": "continuous_stream_stopped"}


@router.get("/{alert_id}", response_model=AlertDetail)
async def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """Single-alert detail view — AlertItem + fully-joined vehicle/slot/camera refs
    and related alerts (same plate or slot, within the last 7 days)."""
    cols = _alerts_extra_cols()
    bits = _alert_query_bits(cols)
    # WS-8 schema-compat shim — branch on each probe.
    schema = _floor_schema()

    # G-6: same join shape as the list query so vehicle/floor/camera fields populate.
    vehicle_event_id_col = (
        "a.vehicle_event_id" if cols["vehicle_event_id"] else "NULL AS vehicle_event_id"
    )
    triggering_camera_event_id_col = (
        "a.triggering_camera_event_id"
        if cols["triggering_camera_event_id"]
        else "NULL AS triggering_camera_event_id"
    )
    resolved_by_col = (
        "a.resolved_by" if cols["resolved_by"] else "NULL AS resolved_by"
    )
    resolution_notes_col = (
        "a.resolution_notes" if cols["resolution_notes"] else "NULL AS resolution_notes"
    )
    event_type_col = "a.event_type" if cols["event_type"] else "NULL AS event_type"
    vehicle_id_col = (
        "COALESCE(a.vehicle_id, v.id) AS vehicle_id"
        if cols["vehicle_id"]
        else "v.id AS vehicle_id"
    )

    # WS-8: build floor expression + floors join from columns that exist.
    # Older DBs predate `cameras.watches_floor`, so build the COALESCE
    # dynamically to avoid `Invalid column name`.
    floor_parts = ["pk.floor"]
    if schema["cameras_watches_floor"]:
        floor_parts.append("c.watches_floor")
    floor_expr = (
        f"COALESCE({', '.join(floor_parts)})"
        if len(floor_parts) > 1
        else floor_parts[0]
    )
    if schema["floors_table"]:
        floors_join = f"LEFT JOIN floors f ON f.name = {floor_expr}"
        floor_id_select = "f.id                                AS floor_id"
    else:
        floors_join = ""
        floor_id_select = "NULL                                AS floor_id"

    # WS-8: every `c.<col>` referenced from cameras is conditional on the
    # column actually existing. Older deployments are missing role,
    # watches_floor, watches_slots_json (Phase 4A additions).
    cam_floor_col       = "c.floor"              if schema["cameras_floor"]              else "NULL"
    cam_role_col        = "c.role"               if schema["cameras_role"]               else "NULL"
    cam_watches_floor_col = "c.watches_floor"    if schema["cameras_watches_floor"]      else "NULL"
    cam_watches_slots_col = "c.watches_slots_json" if schema["cameras_watches_slots_json"] else "NULL"
    alert_rows = rows(db, f"""
        SELECT
            a.id,
            a.alert_type,
            {bits["severity_expr"]}  AS severity,
            {event_type_col},
            a.plate_number,
            {bits["slot_id_expr"]}   AS slot_id,
            {bits["slot_name_expr"]} AS slot_name,
            {floor_expr}             AS floor,
            {floor_id_select},
            {bits["location_expr"]}  AS location,
            a.camera_id,
            a.description,
            a.snapshot_path          AS snapshot_url,
            a.is_resolved,
            a.resolved_at,
            a.triggered_at,
            {vehicle_id_col},
            {vehicle_event_id_col},
            {triggering_camera_event_id_col},
            {resolved_by_col},
            {resolution_notes_col},
            v.owner_name,
            v.vehicle_type,
            v.employee_id,
            v.title,
            v.phone,
            v.email,
            v.is_employee,
            v.is_registered,
            v.registered_at,
            v.notes,
            c.id                     AS camera_pk,
            c.name                   AS camera_name,
            {cam_floor_col}          AS camera_floor,
            {cam_role_col}           AS camera_role,
            {cam_watches_floor_col}  AS camera_watches_floor,
            {cam_watches_slots_col}  AS camera_watches_slots_json
        FROM alerts a
        {bits["slot_join"]}
        -- G-6: join vehicles + cameras for vehicle/floor/camera fall-through
        LEFT JOIN vehicles v ON v.plate_number = a.plate_number
        LEFT JOIN cameras c ON c.camera_id = a.camera_id
        -- WS-8: integer floor_id alongside the COALESCE'd floor name.
        {floors_join}
        WHERE a.id = :id AND a.is_test = 0
    """, {"id": alert_id})

    if not alert_rows:
        raise HTTPException(404, "Alert not found")

    a = alert_rows[0]

    vehicle = None
    if a.get("vehicle_id"):
        vehicle = VehicleRef(
            id=a["vehicle_id"],
            plate_number=a["plate_number"],
            owner_name=a.get("owner_name"),
            vehicle_type=a.get("vehicle_type"),
            is_employee=a.get("is_employee"),
            employee_id=a.get("employee_id"),
            title=a.get("title"),
            phone=a.get("phone"),
            email=a.get("email"),
            is_registered=bool(a.get("is_registered")) if a.get("is_registered") is not None else False,
            registered_at=a.get("registered_at"),
            notes=a.get("notes"),
        )

    slot = None
    if a.get("slot_id"):
        # WS-8: surface integer id + floor_id from parking_slots so SlotRef carries them
        # (NULL fallback when columns missing — Pattern A).
        ps_id_col = "id" if schema["parking_slots_id"] else "NULL AS id"
        ps_floor_id_col = "floor_id" if schema["parking_slots_floor_id"] else "NULL AS floor_id"
        slot_rows = rows(db, f"""
            SELECT {ps_id_col}, slot_id, slot_name, floor, {ps_floor_id_col}, is_available, is_violation_zone, polygon
            FROM parking_slots WHERE slot_id = :sid
        """, {"sid": a["slot_id"]})
        if slot_rows:
            s = slot_rows[0]
            slot = SlotRef(
                id=s.get("id"),
                slot_id=s["slot_id"],
                slot_name=s.get("slot_name"),
                floor=s.get("floor"),
                floor_id=s.get("floor_id"),
                is_available=bool(s.get("is_available")) if s.get("is_available") is not None else True,
                is_violation_slot=bool(s.get("is_violation_zone")) if s.get("is_violation_zone") is not None else False,
                polygon=s.get("polygon"),
            )

    camera = None
    if a.get("camera_pk") and a.get("camera_id"):
        watches_slots = None
        raw_slots = a.get("camera_watches_slots_json")
        if raw_slots:
            try:
                parsed = json.loads(raw_slots)
                if isinstance(parsed, list):
                    watches_slots = [str(x) for x in parsed]
            except (TypeError, ValueError):
                watches_slots = None
        camera = CameraRef(
            id=a["camera_pk"],
            camera_id=a["camera_id"],
            name=a.get("camera_name"),
            floor=a.get("camera_floor"),
            role=a.get("camera_role") or "other",
            watches_floor=a.get("camera_watches_floor"),
            watches_slots=watches_slots,
        )

    # vehicle_event: only populated when alerts row carries a session FK
    vehicle_event = None
    ve_id = a.get("vehicle_event_id")
    if ve_id:
        from app.routers.entry_exit import _event_from_row
        ve_rows = rows(db, """
            SELECT TOP 1
                ps.id, ps.vehicle_id, ps.plate_number,
                ps.is_employee, ps.entry_time, ps.exit_time,
                ps.duration_seconds, ps.entry_camera_id, ps.exit_camera_id,
                ps.entry_snapshot_path, ps.exit_snapshot_path,
                ps.floor, ps.slot_id, ps.slot_number, ps.parked_at, ps.slot_left_at,
                ps.slot_camera_id, ps.slot_snapshot_path, ps.status,
                pk.slot_name AS slot_name,
                v.owner_name, v.vehicle_type
            FROM parking_sessions ps
            LEFT JOIN parking_slots pk ON pk.slot_id = ps.slot_id
            LEFT JOIN vehicles v ON v.plate_number = ps.plate_number
            WHERE ps.id = :ve_id
        """, {"ve_id": ve_id})
        if ve_rows:
            vehicle_event = _event_from_row(ve_rows[0], ve_rows[0].get("plate_number"))

    # Related alerts — same plate OR same slot, last 7 days, excluding this alert
    related = rows(db, f"""
        SELECT TOP 10
            a.id,
            a.alert_type,
            {bits["severity_expr"]} AS severity,
            a.plate_number,
            {bits["slot_id_expr"]}   AS slot_id,
            {bits["slot_name_expr"]} AS slot_name,
            a.description,
            a.triggered_at,
            a.is_resolved,
            a.resolved_at
        FROM alerts a
        {bits["slot_join"]}
        WHERE a.id != :id
          AND a.is_test = 0
          AND a.triggered_at >= DATEADD(DAY, -7, :triggered_at)
          AND (
              (a.plate_number IS NOT NULL AND a.plate_number = :plate)
              OR ({bits["slot_id_expr"]} IS NOT NULL AND {bits["slot_id_expr"]} = :slot)
          )
        ORDER BY a.triggered_at DESC
    """, {"id": alert_id, "plate": a.get("plate_number"), "slot": a.get("slot_id"),
          "triggered_at": a["triggered_at"]})

    # Floor preference: explicit slot.floor → camera.watches_floor (G-6 fall-through)
    floor_value = (slot.floor if slot else None) or a.get("floor")

    return AlertDetail(
        id=a["id"],
        alert_type=a.get("alert_type"),
        severity=a.get("severity"),
        event_type=a.get("event_type"),
        camera_id=a.get("camera_id"),
        plate_number=a.get("plate_number"),
        vehicle_id=a.get("vehicle_id"),
        owner_name=a.get("owner_name"),
        vehicle_type=a.get("vehicle_type"),
        slot_id=a.get("slot_id"),
        slot_name=a.get("slot_name"),
        floor=floor_value,
        # WS-8: integer floor_id from the floors LEFT JOIN, alongside the legacy `floor` name.
        floor_id=a.get("floor_id"),
        vehicle_event_id=a.get("vehicle_event_id"),
        triggering_camera_event_id=a.get("triggering_camera_event_id"),
        description=a.get("description"),
        location=a.get("location"),
        snapshot_url=a.get("snapshot_url"),
        triggered_at=a.get("triggered_at"),
        resolved_at=a.get("resolved_at"),
        is_resolved=a.get("is_resolved"),
        resolved_by=a.get("resolved_by"),
        resolution_notes=a.get("resolution_notes"),
        vehicle=vehicle,
        slot=slot,
        camera=camera,
        vehicle_event=vehicle_event,
        related_alerts=[AlertItem(**r) for r in related],
    )


@router.patch("/{alert_id}/resolve", response_model=EntityActionResponse)
async def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    result = db.execute(
        text("UPDATE alerts SET is_resolved=1, resolved_at=GETDATE() WHERE id=:id AND is_resolved=0"),
        {"id": alert_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Alert not found or already resolved")
    return EntityActionResponse(id=alert_id)


@router.delete("/{alert_id}", response_model=EntityActionResponse)
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    result = db.execute(text("DELETE FROM alerts WHERE id=:id"), {"id": alert_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Alert not found")
    return EntityActionResponse(id=alert_id)
 
 
@router.get("/export/csv")
async def export_alerts_csv(
    search: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    cols = _alerts_extra_cols()
    bits = _alert_query_bits(cols)
    where, params = _where(search, severity, alert_type, resolved, date_from, date_to, cols)
 
    data = rows(db, f"""
        SELECT
            a.id                     AS [ID],
            a.plate_number           AS [Plate Number],
            v.owner_name             AS [Owner],
            a.alert_type             AS [Type],
            {bits["severity_expr"]}  AS [Severity],
            {bits["slot_id_expr"]}   AS [Slot ID],
            {bits["slot_name_expr"]} AS [Slot Name],
            {bits["location_expr"]}  AS [Location],
            a.camera_id              AS [Camera],
            a.description            AS [Description],
            a.snapshot_path          AS [Snapshot URL],
            a.triggered_at           AS [Triggered At],
            a.is_resolved            AS [Resolved],
            a.resolved_at            AS [Resolved At]
        FROM alerts a
        {bits["slot_join"]}
        LEFT JOIN vehicles v ON v.plate_number = a.plate_number
        WHERE {where}
        ORDER BY a.triggered_at DESC
    """, params)

    headers = [
        "ID", "Plate Number", "Owner", "Type", "Severity",
        "Slot ID", "Slot Name", "Location", "Camera",
        "Description", "Snapshot URL", "Triggered At", "Resolved", "Resolved At",
    ]
    return stream_csv(data, headers, filename="alerts.csv")
