from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db, scalar, rows
from app.services.upstream import get_system1_health, get_system2_health, get_live_vehicles

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


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
    Columns mapped from real schema:
      parking_sessions: plate_number, entry_time, floor, zone_id, zone_name,
                        slot_number, is_employee, entry_snapshot_path
      vehicles:         owner_name, vehicle_type
    """
    sql_rows = rows(db, """
        SELECT
            ps.plate_number,
            ps.entry_time,
            ps.floor,
            ps.zone_id,
            ps.zone_name,
            ps.slot_number,
            ps.is_employee,
            ps.entry_snapshot_path,
            v.owner_name,
            v.vehicle_type
        FROM parking_sessions ps
        LEFT JOIN vehicles v ON v.plate_number = ps.plate_number
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
            # prefer live data for placement, fall back to session snapshot
            "slot":            live_data.get("slot_id") or live_data.get("slot") or meta["slot_number"],
            "floor":           live_data.get("floor")   or meta["floor"],
            "zone":            live_data.get("zone")    or meta["zone_name"],
            "thumbnail_url":   live_data.get("thumbnail_url") or meta["entry_snapshot_path"],
        })

    return result
