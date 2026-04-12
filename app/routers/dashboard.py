from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
 
from app.database import get_db, scalar, rows
from app.services.upstream import get_system1_health, get_system2_health, get_live_vehicles
 
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
 
VEHICLE_JOIN = """
    LEFT JOIN vehicles v_id ON v_id.id = ps.vehicle_id
    LEFT JOIN vehicles v_plate ON ps.vehicle_id IS NULL AND v_plate.plate_number = ps.plate_number
"""
 
 
@router.get("/ai-status")
async def ai_status():
    s1, s2 = await get_system1_health(), await get_system2_health()
 
    issues = []
    if s1.get("status") not in ("ok", "healthy"):
        issues.append({"system": "PMS-AI", "reason": s1.get("error") or s1.get("status")})
    for failure in s1.get("failures", []):
        issues.append({"system": "PMS-AI", "reason": failure})
    if s2.get("status") not in ("ok", "healthy"):
        issues.append({"system": "VideoAnalytics", "reason": s2.get("error") or s2.get("status")})
 
    return {
        "online":  len(issues) == 0,
        "issues":  issues,
        "system1": {"status": s1.get("status"), "timestamp": s1.get("timestamp")},
        "system2": {"status": s2.get("status"), "timestamp": s2.get("timestamp")},
    }
 
 
@router.get("/kpis")
async def dashboard_kpis(db: Session = Depends(get_db)):
    unique_plates = scalar(db,
        "SELECT COUNT(DISTINCT plate_number) FROM vehicles")
 
    # parking_sessions.status = 'open' means still inside
    active_now = scalar(db,
        "SELECT COUNT(*) FROM parking_sessions WHERE status = 'open'")
 
    open_alerts = scalar(db,
        "SELECT COUNT(*) FROM alerts WHERE is_resolved = 0")
 
    return {
        "total_unique_plates": unique_plates or 0,
        "active_now":          active_now    or 0,
        "open_alerts":         open_alerts   or 0,
    }
 
 
@router.get("/active-vehicles")
async def active_vehicles(db: Session = Depends(get_db)):
    """
    Open parking sessions merged with live System 2 slot data.
    Joins parking_slots to get the real slot_name for display.
    """
    sql_rows = rows(db, """
        SELECT
            ps.plate_number,
            ps.entry_time,
            ps.floor,
            ps.zone_id as slot_id,
            COALESCE(pk.slot_name, ps.slot_number, ps.zone_id) AS slot_name,
            ps.zone_id,
            ps.zone_name,
            ps.slot_number,
            ps.is_employee,
            ps.entry_snapshot_path,
            COALESCE(v_id.owner_name, v_plate.owner_name) AS owner_name,
            COALESCE(v_id.vehicle_type, v_plate.vehicle_type, ps.vehicle_type) AS vehicle_type
        FROM parking_sessions ps
    """ + VEHICLE_JOIN + """
        LEFT JOIN parking_slots pk ON pk.slot_id = ps.zone_id
        WHERE ps.status = 'open'
        ORDER BY ps.entry_time DESC
    """)
 
    sql_map = {r["plate_number"]: r for r in sql_rows}
 
    # Merge with System 2 live data (may have fresher slot/floor info)
    live = await get_live_vehicles()
    live_map = {v.get("plate_number") or v.get("plate"): v for v in live}
 
    result = []
    for plate, meta in sql_map.items():
        live_data = live_map.get(plate, {})
        result.append({
            "plate_number":    plate,
            "entry_time":      meta["entry_time"],
            "owner_name":      meta["owner_name"],
            "vehicle_type":    meta["vehicle_type"],
            "is_employee":     meta["is_employee"],
            # prefer live data for placement, fall back to session slot_name
            "slot":            live_data.get("slot_id") or meta["slot_name"] or live_data.get("slot"),
            "floor":           live_data.get("floor")   or meta["floor"],
            "zone":            live_data.get("zone_name") or live_data.get("zone") or meta["zone_name"],
            "thumbnail_url":   live_data.get("thumbnail_url") or meta["entry_snapshot_path"],
        })
 
    return result