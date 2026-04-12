import asyncio
import json
from datetime import date
from functools import lru_cache
from typing import Optional
 
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
 
from app.database import get_db, rows, scalar
from app.services.upstream import iter_system1_alert_events, iter_system2_alert_events
from app.services.bus import alerts_bus
from app.shared import build_paged, stream_csv
 
router = APIRouter(prefix="/alerts", tags=["Alerts"])
 
 
@lru_cache(maxsize=None)
def _alerts_extra_cols() -> dict:
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
            "severity":         exists("severity"),
            "location_display": exists("location_display"),
            "slot_id":          exists("slot_id"),
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
 
 
def _where(search, severity, alert_type, resolved, date_from, date_to, cols):
    bits = _alert_query_bits(cols)
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
 
    return " AND ".join(clauses), params
 
 
def _normalize_stream_event(source_system: str, payload: dict) -> dict:
    slot_name = payload.get("slot_name")
    if not slot_name and payload.get("slot_number"):
        slot_name = str(payload["slot_number"])
 
    return {
        "source_system": source_system,
        "alert_type":    payload.get("alert_type"),
        "severity":      payload.get("severity", "info"),
        "slot_id":       payload.get("slot_id"),
        "slot_name":     slot_name,
        "zone_id":       payload.get("zone_id"),
        "zone_name":     payload.get("zone_name"),
        "plate_number":  payload.get("plate_number"),
        "camera_id":     payload.get("camera_id"),
        "floor":         payload.get("floor"),
        "snapshot_url":  payload.get("snapshot_url") or payload.get("snapshot_path"),
        "timestamp":     payload.get("timestamp") or payload.get("triggered_at"),
        "is_alert":      payload.get("is_alert", True),
    }
 
 
async def _pump(source_system: str, iterator, queue: asyncio.Queue):
    async for event in iterator:
        await queue.put((source_system, event))
    await queue.put((source_system, None))
 
 
@router.get("/stats")
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
 
    return {
        "active_alerts":    scalar(db, "SELECT COUNT(*) FROM alerts WHERE is_resolved=0 AND is_test=0"),
        "critical_violations": scalar(db, critical_sql),
        "resolved_today":   scalar(db, """
            SELECT COUNT(*) FROM alerts
            WHERE is_resolved=1 AND is_test=0
              AND CAST(resolved_at AS DATE) = CAST(GETDATE() AS DATE)
        """),
    }
 
 
@router.get("/")
async def get_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
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
    params["offset"]    = (page - 1) * page_size
    params["page_size"] = page_size
 
    total = scalar(db, f"SELECT COUNT(*) FROM alerts a WHERE {where}", params)
    items = rows(db, f"""
        SELECT
            a.id,
            a.alert_type,
            a.event_type,
            {bits["severity_expr"]} AS severity,
            a.plate_number,
            a.camera_id,
            {bits["slot_id_expr"]}   AS slot_id,
            {bits["slot_name_expr"]} AS slot_name,
            {bits["zone_id_expr"]}   AS zone_id,
            {bits["zone_name_expr"]} AS zone_name,
            a.region_id,
            a.slot_number,
            {bits["location_expr"]}  AS location_display,
            a.description,
            a.snapshot_path,
            a.is_resolved,
            a.resolved_at,
            a.triggered_at,
            v.owner_name,
            v.vehicle_type
        FROM alerts a
        {bits["slot_join"]}
        LEFT JOIN vehicles v ON v.plate_number = a.plate_number
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
async def stream_alerts():
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
        finished = 0
 
        try:
            yield "data: " + json.dumps({
                "source_system": "gateway",
                "alert_type":    "connection_established",
                "severity":      "info",
                "slot_id":       None,
                "slot_name":     None,
                "zone_id":       None,
                "zone_name":     None,
                "plate_number":  None,
                "camera_id":     None,
                "floor":         None,
                "snapshot_url":  None,
                "timestamp":     None,
                "is_alert":      False,
            }) + "\n\n"
 
            while True:
                source_system, payload = await client_queue.get()
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
 
 
@router.post("/test")
async def trigger_test_alert(payload: Optional[dict] = None):
    """
    Broadcasts one or more fake alerts to all active /alerts/stream subscribers.
    If no payload is sent, it cycles through all known alert types once.
    """
    if payload:
        await alerts_bus.broadcast(payload)
        return {"status": "broadcasted_custom", "payload": payload}
    else:
        # Broadcast all types once
        for t in ALERT_TEMPLATES:
            item = t.copy()
            item["triggered_at"] = str(date.today())
            await alerts_bus.broadcast(item)
            await asyncio.sleep(0.1)
        return {"status": "broadcasted_all", "count": len(ALERT_TEMPLATES)}


@router.get("/test/start")
async def start_continuous_test(interval: float = Query(1.0, ge=0.5, le=60.0)):
    """Starts an infinite loop of random test alerts every {interval} seconds."""
    alerts_bus.start_test_stream(ALERT_TEMPLATES, interval=interval)
    return {"status": "continuous_stream_started", "interval": interval}


@router.get("/test/stop")
async def stop_continuous_test():
    """Stops the infinite loop of random test alerts."""
    alerts_bus.stop_test_stream()
    return {"status": "continuous_stream_stopped"}


@router.patch("/{alert_id}/resolve")
async def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    result = db.execute(
        text("UPDATE alerts SET is_resolved=1, resolved_at=GETDATE() WHERE id=:id AND is_resolved=0"),
        {"id": alert_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Alert not found or already resolved")
    return {"success": True, "alert_id": alert_id}
 
 
@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    result = db.execute(text("DELETE FROM alerts WHERE id=:id"), {"id": alert_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Alert not found")
    return {"success": True, "alert_id": alert_id}
 
 
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
            a.event_type             AS [Event Type],
            {bits["severity_expr"]}  AS [Severity],
            {bits["slot_id_expr"]}   AS [Slot ID],
            {bits["slot_name_expr"]} AS [Slot Name],
            {bits["zone_id_expr"]}   AS [Zone ID],
            {bits["zone_name_expr"]} AS [Zone Name],
            {bits["location_expr"]}  AS [Location],
            a.description            AS [Description],
            a.snapshot_path          AS [Snapshot],
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
        "ID", "Plate Number", "Owner", "Type", "Event Type", "Severity",
        "Slot ID", "Slot Name", "Zone ID", "Zone Name", "Location",
        "Description", "Snapshot", "Triggered At", "Resolved", "Resolved At",
    ]
    return stream_csv(data, headers, filename="alerts.csv")