from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db, scalar, rows
from app.services.upstream import get_live_slots
from app.shared import build_paged

router = APIRouter(prefix="/occupancy", tags=["Occupancy"])

# zone_occupancy real columns:
#   id, zone_id, camera_id, current_count, max_capacity,
#   last_updated, zone_name, floor
#
# parking_slots real columns:
#   slot_id, slot_name, floor, polygon, is_available, is_violation_zone
#
# slot_status real columns:
#   id, slot_id, plate_number, status, time


@router.get("/kpis")
async def occupancy_kpis(db: Session = Depends(get_db)):
    total_spots = scalar(db, "SELECT COUNT(*) FROM parking_slots")

    # occupied = slots where latest slot_status is not 'empty'/'available'
    occupied_sql = scalar(db, """
        SELECT COUNT(DISTINCT ss.slot_id)
        FROM slot_status ss
        INNER JOIN (
            SELECT slot_id, MAX(time) AS latest
            FROM slot_status
            GROUP BY slot_id
        ) latest_ss ON latest_ss.slot_id = ss.slot_id AND latest_ss.latest = ss.time
        WHERE ss.status NOT IN ('empty', 'available', 'free')
    """)

    # fallback: sum current_count from zone_occupancy
    occupied_zone = scalar(db, "SELECT SUM(current_count) FROM zone_occupancy")

    occupied    = occupied_sql or occupied_zone or 0
    available   = max((total_spots or 0) - occupied, 0)
    utilization = round(occupied / total_spots * 100, 1) if total_spots else 0.0

    active_vehicles = scalar(db,
        "SELECT COUNT(*) FROM parking_sessions WHERE status = 'open'")

    return {
        "total_spots":         total_spots     or 0,
        "available_spots":     available,
        "occupied_spots":      occupied,
        "overall_utilization": utilization,
        "total_vehicles":      active_vehicles or 0,
    }


@router.get("/zones")
async def get_zones(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="zone name or floor"),
    floor: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    clauses = ["1=1"]
    params: dict = {}

    if search:
        clauses.append("(zo.zone_name LIKE :search OR CAST(zo.floor AS NVARCHAR) LIKE :search OR zo.zone_id LIKE :search)")
        params["search"] = f"%{search}%"
    if floor:
        clauses.append("zo.floor = :floor")
        params["floor"] = floor

    where = " AND ".join(clauses)
    total = scalar(db, f"SELECT COUNT(*) FROM zone_occupancy zo WHERE {where}", params)

    params["offset"]    = (page - 1) * page_size
    params["page_size"] = page_size

    zone_rows = rows(db, f"""
        SELECT
            zo.id,
            zo.zone_id,
            zo.zone_name,
            zo.floor,
            zo.camera_id,
            zo.max_capacity,
            zo.current_count,
            zo.last_updated
        FROM zone_occupancy zo
        WHERE {where}
        ORDER BY zo.floor, zo.zone_name
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)

    # overlay live slot counts from System 2 per zone
    live_slots = await get_live_slots()
    live_by_zone: dict[str, int] = {}
    for slot in live_slots:
        zid = str(slot.get("zone_id") or slot.get("zone") or "")
        if zid:
            live_by_zone[zid] = live_by_zone.get(zid, 0) + (
                1 if slot.get("status") not in ("empty", "available", "free") else 0
            )

    items = []
    for z in zone_rows:
        zid      = str(z["zone_id"])
        # prefer live count → fall back to zone_occupancy.current_count
        occupied = live_by_zone.get(zid, z["current_count"] or 0)
        capacity = z["max_capacity"] or 1
        items.append({
            **z,
            "occupied":    occupied,
            "available":   max(capacity - occupied, 0),
            "utilization": round(occupied / capacity * 100, 1),
        })

    return build_paged(items, total or 0, page, page_size)


@router.get("/slots")
async def get_slots(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    floor: Optional[str] = Query(None),
    is_available: Optional[bool] = Query(None),
    is_violation_zone: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """Individual slot grid — joins parking_slots with latest slot_status."""
    clauses = ["1=1"]
    params: dict = {}

    if floor:
        clauses.append("ps.floor = :floor")
        params["floor"] = floor
    if is_available is not None:
        clauses.append("ps.is_available = :is_available")
        params["is_available"] = 1 if is_available else 0
    if is_violation_zone is not None:
        clauses.append("ps.is_violation_zone = :is_vz")
        params["is_vz"] = 1 if is_violation_zone else 0

    where = " AND ".join(clauses)
    total = scalar(db, f"SELECT COUNT(*) FROM parking_slots ps WHERE {where}", params)

    params["offset"]    = (page - 1) * page_size
    params["page_size"] = page_size

    items = rows(db, f"""
        SELECT
            ps.slot_id,
            ps.slot_name,
            ps.floor,
            ps.is_available,
            ps.is_violation_zone,
            ss.plate_number     AS current_plate,
            ss.status           AS current_status,
            ss.time             AS status_updated_at
        FROM parking_slots ps
        LEFT JOIN slot_status ss ON ss.slot_id = ps.slot_id
            AND ss.time = (
                SELECT MAX(time) FROM slot_status WHERE slot_id = ps.slot_id
            )
        WHERE {where}
        ORDER BY ps.floor, ps.slot_name
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)

    return build_paged(items, total or 0, page, page_size)
