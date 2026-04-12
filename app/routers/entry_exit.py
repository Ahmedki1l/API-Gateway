from datetime import date
from typing import Optional
 
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
 
from app.database import get_db, scalar, rows
from app.shared import build_paged, stream_csv
 
router = APIRouter(prefix="/entry-exit", tags=["Entry/Exit"])
 
VEHICLE_JOIN = """
    LEFT JOIN vehicles v_id ON v_id.id = ps.vehicle_id
    LEFT JOIN vehicles v_plate ON ps.vehicle_id IS NULL AND v_plate.plate_number = ps.plate_number
"""
OWNER_NAME_EXPR = "COALESCE(v_id.owner_name, v_plate.owner_name)"
VEHICLE_TYPE_EXPR = "COALESCE(v_id.vehicle_type, v_plate.vehicle_type, ps.vehicle_type)"
 
# entry_exit_log real columns:
#   id, plate_number, vehicle_id, vehicle_type, gate, camera_id,
#   event_time, parking_duration, snapshot_path, matched_entry_id, is_test, created_at
#
# parking_sessions real columns:
#   id, plate_number, vehicle_id, vehicle_type, is_employee, entry_time, exit_time,
#   duration_seconds, entry_camera_id, exit_camera_id, entry_snapshot_path,
#   exit_snapshot_path, floor, zone_id, zone_name, slot_number, parked_at,
#   slot_left_at, slot_camera_id, slot_snapshot_path, slot_id, status, created_at, updated_at
#
# parking_slots real columns:
#   slot_id, slot_name, floor, polygon, is_available, is_violation_zone
 
 
@router.get("/kpis")
async def entry_exit_kpis(
    target_date: Optional[date] = Query(None, description="ISO date e.g. 2024-06-01"),
    db: Session = Depends(get_db),
):
    date_filter = "AND CAST(entry_time AS DATE) = :d" if target_date else ""
    params      = {"d": str(target_date)} if target_date else {}
 
    total = scalar(db, f"""
        SELECT COUNT(DISTINCT plate_number)
        FROM parking_sessions
        WHERE 1=1 {date_filter}
    """, params)
 
    currently_parked = scalar(db,
        "SELECT COUNT(*) FROM parking_sessions WHERE status = 'open'")
 
    # duration_seconds → minutes average (exclude still-open sessions)
    avg_stay_sec = scalar(db, f"""
        SELECT AVG(CAST(duration_seconds AS FLOAT))
        FROM parking_sessions
        WHERE status != 'open'
          AND duration_seconds IS NOT NULL
          {date_filter}
    """, params)
    avg_stay_minutes = round((avg_stay_sec or 0) / 60, 1)
 
    # overstay = status column set by entry_exit_service
    overstays = scalar(db, f"""
        SELECT COUNT(*) FROM parking_sessions
        WHERE status = 'overstay' {date_filter}
    """, params)
 
    return {
        "total_vehicles":    total            or 0,
        "currently_parked":  currently_parked or 0,
        "avg_stay_minutes":  avg_stay_minutes,
        "overstays":         overstays        or 0,
    }
 
 
@router.get("/traffic")
async def traffic_chart(
    period: str = Query("daily", description="daily | weekly | monthly"),
    db: Session = Depends(get_db),
):
    """
    Uses entry_exit_log for raw event counts.
    event_time column + gate column (entry/exit direction).
    System 1 stores entry and exit as separate rows; gate indicates direction.
    """
    if period == "daily":
        sql = """
            SELECT
                DATEPART(HOUR, event_time)                              AS label,
                SUM(CASE WHEN gate LIKE '%entry%' OR gate LIKE '%in%' THEN 1 ELSE 0 END) AS entries,
                SUM(CASE WHEN gate LIKE '%exit%'  OR gate LIKE '%out%' THEN 1 ELSE 0 END) AS exits
            FROM entry_exit_log
            WHERE CAST(event_time AS DATE) = CAST(GETDATE() AS DATE)
              AND is_test = 0
            GROUP BY DATEPART(HOUR, event_time)
            ORDER BY label
        """
    elif period == "weekly":
        sql = """
            SELECT
                DATENAME(WEEKDAY, event_time)                           AS label,
                SUM(CASE WHEN gate LIKE '%entry%' OR gate LIKE '%in%' THEN 1 ELSE 0 END) AS entries,
                SUM(CASE WHEN gate LIKE '%exit%'  OR gate LIKE '%out%' THEN 1 ELSE 0 END) AS exits
            FROM entry_exit_log
            WHERE event_time >= DATEADD(DAY, 2 - DATEPART(WEEKDAY, GETDATE()), CAST(GETDATE() AS DATE))
              AND is_test = 0
            GROUP BY DATENAME(WEEKDAY, event_time), DATEPART(WEEKDAY, event_time)
            ORDER BY MIN(DATEPART(WEEKDAY, event_time))
        """
    else:  # monthly
        sql = """
            SELECT
                DAY(event_time)                                         AS label,
                SUM(CASE WHEN gate LIKE '%entry%' OR gate LIKE '%in%' THEN 1 ELSE 0 END) AS entries,
                SUM(CASE WHEN gate LIKE '%exit%'  OR gate LIKE '%out%' THEN 1 ELSE 0 END) AS exits
            FROM entry_exit_log
            WHERE YEAR(event_time)  = YEAR(GETDATE())
              AND MONTH(event_time) = MONTH(GETDATE())
              AND is_test = 0
            GROUP BY DAY(event_time)
            ORDER BY label
        """
    return rows(db, sql)
 
 
@router.get("/")
async def get_entry_exit(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="plate number or owner name"),
    floor: Optional[str] = Query(None),
    is_employee: Optional[bool] = Query(None),
    status: Optional[str] = Query(None, description="open | closed | overstay | unknown_exit"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    clauses = ["1=1"]
    params: dict = {}
 
    if search:
        clauses.append(f"(ps.plate_number LIKE :search OR {OWNER_NAME_EXPR} LIKE :search)")
        params["search"] = f"%{search}%"
    if floor:
        clauses.append("ps.floor = :floor")
        params["floor"] = floor
    if is_employee is not None:
        clauses.append("ps.is_employee = :is_employee")
        params["is_employee"] = 1 if is_employee else 0
    if status:
        clauses.append("ps.status = :status")
        params["status"] = status
    if date_from:
        clauses.append("CAST(ps.entry_time AS DATE) >= :date_from")
        params["date_from"] = str(date_from)
    if date_to:
        clauses.append("CAST(ps.entry_time AS DATE) <= :date_to")
        params["date_to"] = str(date_to)
 
    where  = " AND ".join(clauses)
    total  = scalar(db, f"""
        SELECT COUNT(DISTINCT ps.plate_number)
        FROM parking_sessions ps
    """ + VEHICLE_JOIN + f"""
        WHERE {where}
    """, params)
 
    params["offset"]    = (page - 1) * page_size
    params["page_size"] = page_size
 
    plate_rows = rows(db, f"""
        SELECT DISTINCT
            ps.plate_number,
            {OWNER_NAME_EXPR} AS owner_name,
            {VEHICLE_TYPE_EXPR} AS vehicle_type,
            ps.is_employee
        FROM parking_sessions ps
    """ + VEHICLE_JOIN + f"""
        WHERE {where}
        ORDER BY ps.plate_number
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)
 
    items = []
    for pr in plate_rows:
        plate  = pr["plate_number"]
        events = rows(db, """
            SELECT
                ps.id,
                ps.status,
                ps.entry_time,
                ps.exit_time,
                ps.duration_seconds,
                ps.floor,
                ps.zone_id as slot_id,
                COALESCE(pk.slot_name, ps.slot_number, ps.zone_id) AS slot_name,
                ps.zone_id,
                ps.zone_name,
                ps.slot_number,
                ps.parked_at,
                ps.slot_left_at,
                ps.entry_camera_id,
                ps.exit_camera_id,
                ps.entry_snapshot_path,
                ps.exit_snapshot_path,
                ps.slot_snapshot_path
            FROM parking_sessions ps
            LEFT JOIN parking_slots pk ON pk.slot_id = ps.zone_id
            WHERE ps.plate_number = :plate
            ORDER BY ps.entry_time DESC
        """, {"plate": plate})
 
        items.append({
            "plate_number": plate,
            "owner_name":   pr["owner_name"],
            "vehicle_type": pr["vehicle_type"],
            "is_employee":  bool(pr["is_employee"]) if pr["is_employee"] is not None else False,
            "events":       events,
        })
 
    return build_paged(items, total or 0, page, page_size)
 
 
@router.get("/export/csv")
async def export_entry_exit_csv(
    search: Optional[str] = Query(None),
    floor: Optional[str] = Query(None),
    is_employee: Optional[bool] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    clauses = ["1=1"]
    params: dict = {}
    if search:
        clauses.append(f"(ps.plate_number LIKE :search OR {OWNER_NAME_EXPR} LIKE :search)")
        params["search"] = f"%{search}%"
    if floor:
        clauses.append("ps.floor = :floor")
        params["floor"] = floor
    if is_employee is not None:
        clauses.append("ps.is_employee = :is_employee")
        params["is_employee"] = 1 if is_employee else 0
    if status:
        clauses.append("ps.status = :status")
        params["status"] = status
    if date_from:
        clauses.append("CAST(ps.entry_time AS DATE) >= :date_from")
        params["date_from"] = str(date_from)
    if date_to:
        clauses.append("CAST(ps.entry_time AS DATE) <= :date_to")
        params["date_to"] = str(date_to)
 
    data = rows(db, f"""
        SELECT
            ps.plate_number                                  AS [Plate Number],
            {OWNER_NAME_EXPR}                                AS [Owner],
            {VEHICLE_TYPE_EXPR}                              AS [Vehicle Type],
            ps.is_employee                                   AS [Employee],
            ps.status                                        AS [Status],
            ps.entry_time                                    AS [Entry Time],
            ps.exit_time                                     AS [Exit Time],
            ps.duration_seconds / 60                         AS [Duration (min)],
            ps.floor                                         AS [Floor],
            ps.zone_id                                       AS [Slot ID],
            COALESCE(pk.slot_name, ps.slot_number, ps.zone_id) AS [Slot Name],
            ps.zone_name                                     AS [Zone],
            ps.parked_at                                     AS [Parked At],
            ps.slot_left_at                                  AS [Slot Left At],
            ps.entry_camera_id                               AS [Entry Camera],
            ps.exit_camera_id                                AS [Exit Camera]
        FROM parking_sessions ps
    """ + VEHICLE_JOIN + f"""
        LEFT JOIN parking_slots pk ON pk.slot_id = ps.zone_id
        WHERE {" AND ".join(clauses)}
        ORDER BY ps.entry_time DESC
    """, params)
 
    headers = ["Plate Number", "Owner", "Vehicle Type", "Employee", "Status",
               "Entry Time", "Exit Time", "Duration (min)", "Floor", "Slot ID", "Slot Name", "Zone",
               "Parked At", "Slot Left At", "Entry Camera", "Exit Camera"]
    return stream_csv(data, headers, filename="entry_exit.csv")