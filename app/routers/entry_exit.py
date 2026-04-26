import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import facility_today_utc, facility_tz
from app.database import get_db, scalar, rows
from app.routers._helpers import _floor_schema, resolve_floor_id
from app.services.snapshots import resolve_snapshot_url
from app.schemas import (
    AlertItem,
    CameraRef,
    EntryExitEvent,
    EntryExitKPIs,
    PagedResponse,
    TrafficBucket,
    VehicleEvent,
    VehicleEventDetail,
    VehicleRef,
)
from app.shared import build_paged, stream_csv

router = APIRouter(prefix="/entry-exit", tags=["Entry/Exit"])


def _live_duration_seconds(
    entry_time, exit_time, parked_at, stored_duration: Optional[int]
) -> Optional[int]:
    """Return the session's elapsed seconds, computed live when the session
    is still open.

    Rules:
      - If the session is closed (exit_time set), trust the stored value when
        present, otherwise compute (exit_time - start) ourselves.
      - If still open, count from whichever start signal fired first:
          * `entry_time` (line-crossing at B1 entry, or ANPR at the gate),
          * else `parked_at` (slot occupation on the Ground Floor / direct
            slot detection without a prior entry event).
      - Returns None when neither start signal has fired yet.

    All timestamps are UTC; we normalise tz-naive values to UTC so the
    arithmetic doesn't blow up on DBs that strip tzinfo.
    """
    def _as_utc(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    entry_utc = _as_utc(entry_time)
    exit_utc = _as_utc(exit_time)
    parked_utc = _as_utc(parked_at)
    start = entry_utc or parked_utc
    if start is None:
        return None
    end = exit_utc or datetime.now(timezone.utc)
    if exit_utc is not None and stored_duration is not None:
        # Trust the writer's stored value once a session is closed — it's
        # what reports/CSVs have been pinned to historically.
        return int(stored_duration)
    return max(int((end - start).total_seconds()), 0)


def _event_from_row(r: dict, plate_number: str) -> VehicleEvent:
    """Build a VehicleEvent with nested entry + optional exit from a parking_sessions row.
    The row should include the joined `owner_name`, `vehicle_type`, `is_employee`
    columns (queries below alias them under those names)."""
    vehicle_id = r.get("vehicle_id")
    entry = EntryExitEvent(
        plate_number=plate_number,
        vehicle_id=vehicle_id,
        direction="entry",
        camera_id=r.get("entry_camera_id"),
        event_time=r.get("entry_time"),
        snapshot_url=resolve_snapshot_url(r.get("entry_snapshot_path")),
        vehicle_event_id=r["id"],
    )
    exit_event: Optional[EntryExitEvent] = None
    if r.get("exit_time") is not None:
        exit_event = EntryExitEvent(
            plate_number=plate_number,
            vehicle_id=vehicle_id,
            direction="exit",
            camera_id=r.get("exit_camera_id"),
            event_time=r.get("exit_time"),
            snapshot_url=resolve_snapshot_url(r.get("exit_snapshot_path")),
            vehicle_event_id=r["id"],
        )
    is_employee_raw = r.get("is_employee")
    return VehicleEvent(
        id=r["id"],
        vehicle_id=vehicle_id,
        plate_number=plate_number,
        owner_name=r.get("owner_name"),
        vehicle_type=r.get("vehicle_type"),
        is_employee=bool(is_employee_raw) if is_employee_raw is not None else None,
        status=r.get("status"),
        entry=entry,
        exit=exit_event,
        duration_seconds=_live_duration_seconds(
            entry_time=r.get("entry_time"),
            exit_time=r.get("exit_time"),
            parked_at=r.get("parked_at"),
            stored_duration=r.get("duration_seconds"),
        ),
        slot_id=r.get("slot_id"),
        slot_name=r.get("slot_name"),
        slot_number=r.get("slot_number"),
        floor=r.get("floor"),
        # WS-8.E: integer-id sibling field; None on legacy rows where backfill hasn't run.
        floor_id=r.get("floor_id"),
        parked_at=r.get("parked_at"),
        slot_left_at=r.get("slot_left_at"),
        slot_camera_id=r.get("slot_camera_id"),
        slot_snapshot_url=resolve_snapshot_url(r.get("slot_snapshot_path")),
    )
 
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
 
 
@router.get("/kpis", response_model=EntryExitKPIs)
async def entry_exit_kpis(
    target_date: Optional[date] = Query(None, description="ISO date e.g. 2024-06-01"),
    db: Session = Depends(get_db),
):
    if target_date:
        # Specific date provided: filter for that 24h window in local time
        local_tz = facility_tz()
        dt_local = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=local_tz)
        start_utc = dt_local.astimezone(timezone.utc)
        end_utc   = (dt_local + timedelta(days=1)).astimezone(timezone.utc)
        date_filter = "AND entry_time >= :start AND entry_time < :end"
        params = {"start": start_utc, "end": end_utc}
    else:
        # facility_today_utc() returns the UTC instant of facility-local midnight today.
        start_utc = facility_today_utc()
        date_filter = "AND entry_time >= :start"
        params = {"start": start_utc}

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

    # overstay = status column set by entry_exit_service or open > 24h
    # Removed date_filter to show all current overstays regardless of entry day
    # Option B: Overstays = unique vehicles that entered before today's local midnight
    overstays = scalar(db, """
        SELECT COUNT(DISTINCT plate_number)
        FROM parking_sessions
        WHERE plate_number IS NOT NULL
          AND (status = 'open' OR status = 'overstay')
          AND entry_time < :start_of_today
    """, {"start_of_today": start_utc})

    return EntryExitKPIs(
        total_vehicles_today=total or 0,
        currently_parked=currently_parked or 0,
        avg_stay_minutes=avg_stay_minutes,
        overstays=overstays or 0,
    )
 
 
@router.get("/traffic", response_model=list[TrafficBucket])
async def traffic_chart(
    period: str = Query("daily", description="daily | weekly | monthly"),
    db: Session = Depends(get_db),
):
    """Rolling-window traffic counts from `entry_exit_log`, zero-filled.

    Window semantics:
      - **daily**   → last 24 hours from now (24 hourly buckets,
                     anchored on the current hour boundary).
      - **weekly**  → last 7 days starting today  (today + 6 prior, daily buckets).
      - **monthly** → last 30 days starting today (today + 29 prior, daily buckets).

    Buckets and labels live in facility-local time
    (`FACILITY_TIMEZONE_OFFSET_HOURS`, default UTC+2). Events stored in UTC
    are shifted into facility-local before being grouped, so the daily
    buckets line up with the operator's wall clock. Labels are ISO strings
    (`YYYY-MM-DDTHH:00` for daily, `YYYY-MM-DD` for weekly/monthly) so the
    chart can render them unambiguously regardless of locale.
    """
    from app.config import settings  # local import to avoid a circular at module load
    offset_minutes = int(settings.facility_timezone_offset_hours * 60)
    local_tz = facility_tz()

    if period == "daily":
        # 24 hourly buckets, anchored on the current local hour. The window
        # ends at `current_hour + 1h` (exclusive) and starts 24h earlier.
        now_local = datetime.now(local_tz)
        current_hour_local = now_local.replace(minute=0, second=0, microsecond=0)
        window_start_local = current_hour_local - timedelta(hours=23)
        window_end_local   = current_hour_local + timedelta(hours=1)
        window_start_utc = window_start_local.astimezone(timezone.utc)
        window_end_utc   = window_end_local.astimezone(timezone.utc)

        # Each hour-of-day appears exactly once in a rolling 24-hour window,
        # so the bare "HH:00" label is unambiguous.
        full_labels: list[dict] = [
            {
                "label": (window_start_local + timedelta(hours=i)).strftime("%H:00"),
                "entries": 0,
                "exits": 0,
            }
            for i in range(24)
        ]
        # DATEDIFF(HOUR, start_utc, event_time) gives 0-23. event_time is UTC,
        # start_utc is UTC — no offset shift needed inside DATEDIFF.
        sql = """
            SELECT
                DATEDIFF(HOUR, :start_utc, event_time)                  AS bucket_idx,
                SUM(CASE WHEN gate LIKE '%entry%' OR gate LIKE '%in%' THEN 1 ELSE 0 END) AS entries,
                SUM(CASE WHEN gate LIKE '%exit%'  OR gate LIKE '%out%' THEN 1 ELSE 0 END) AS exits
            FROM entry_exit_log
            WHERE event_time >= :start_utc
              AND event_time <  :end_utc
              AND is_test = 0
            GROUP BY DATEDIFF(HOUR, :start_utc, event_time)
        """
        params = {"start_utc": window_start_utc, "end_utc": window_end_utc}

    elif period == "weekly":
        # 7 daily buckets in facility-local time: today-6, …, today.
        # Each day-of-week appears at most once in a 7-day window, so the
        # weekday name is an unambiguous label.
        now_local = datetime.now(local_tz)
        today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        window_start_local = today_local - timedelta(days=6)
        window_end_local   = today_local + timedelta(days=1)
        window_start_utc = window_start_local.astimezone(timezone.utc)
        window_end_utc   = window_end_local.astimezone(timezone.utc)

        full_labels = [
            {
                "label": (window_start_local + timedelta(days=i)).strftime("%A"),  # "Monday"
                "entries": 0,
                "exits": 0,
            }
            for i in range(7)
        ]
        # Shift events into facility-local before bucketing by day.
        sql = """
            SELECT
                DATEDIFF(DAY, :start_local_date, DATEADD(MINUTE, :offset_min, event_time)) AS bucket_idx,
                SUM(CASE WHEN gate LIKE '%entry%' OR gate LIKE '%in%' THEN 1 ELSE 0 END) AS entries,
                SUM(CASE WHEN gate LIKE '%exit%'  OR gate LIKE '%out%' THEN 1 ELSE 0 END) AS exits
            FROM entry_exit_log
            WHERE event_time >= :start_utc
              AND event_time <  :end_utc
              AND is_test = 0
            GROUP BY DATEDIFF(DAY, :start_local_date, DATEADD(MINUTE, :offset_min, event_time))
        """
        params = {
            "start_local_date": window_start_local.date(),
            "offset_min": offset_minutes,
            "start_utc": window_start_utc,
            "end_utc": window_end_utc,
        }

    else:  # monthly — 30 daily buckets
        now_local = datetime.now(local_tz)
        today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        window_start_local = today_local - timedelta(days=29)
        window_end_local   = today_local + timedelta(days=1)
        window_start_utc = window_start_local.astimezone(timezone.utc)
        window_end_utc   = window_end_local.astimezone(timezone.utc)

        # Format: "Apr 25" when the 30-day window stays within one year;
        # "Apr 25, 2026" when the window crosses a year boundary.
        crosses_year = window_start_local.year != today_local.year
        date_fmt = "%b %d, %Y" if crosses_year else "%b %d"
        full_labels = [
            {
                "label": (window_start_local + timedelta(days=i)).strftime(date_fmt),
                "entries": 0,
                "exits": 0,
            }
            for i in range(30)
        ]
        sql = """
            SELECT
                DATEDIFF(DAY, :start_local_date, DATEADD(MINUTE, :offset_min, event_time)) AS bucket_idx,
                SUM(CASE WHEN gate LIKE '%entry%' OR gate LIKE '%in%' THEN 1 ELSE 0 END) AS entries,
                SUM(CASE WHEN gate LIKE '%exit%'  OR gate LIKE '%out%' THEN 1 ELSE 0 END) AS exits
            FROM entry_exit_log
            WHERE event_time >= :start_utc
              AND event_time <  :end_utc
              AND is_test = 0
            GROUP BY DATEDIFF(DAY, :start_local_date, DATEADD(MINUTE, :offset_min, event_time))
        """
        params = {
            "start_local_date": window_start_local.date(),
            "offset_min": offset_minutes,
            "start_utc": window_start_utc,
            "end_utc": window_end_utc,
        }

    db_results = rows(db, sql, params)
    for row in db_results:
        idx = row["bucket_idx"]
        if idx is not None and 0 <= idx < len(full_labels):
            full_labels[idx]["entries"] = row["entries"]
            full_labels[idx]["exits"] = row["exits"]
    return full_labels
 
 
@router.get("/", response_model=PagedResponse[VehicleEvent])
async def get_entry_exit(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="plate number or owner name"),
    floor: Optional[str] = Query(None),
    # WS-8.E: integer-id sibling filter; wins over `?floor=` when both are sent.
    floor_id: Optional[int] = Query(None),
    is_employee: Optional[bool] = Query(None),
    status: Optional[str] = Query(None, description="open | closed | overstay | unknown_exit"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    min_duration_seconds: Optional[int] = Query(None, ge=0),
    max_duration_seconds: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    """Flat list of every parking event (one row per entry, expanded with its
    paired exit when present). Replaces the old grouped-by-plate shape — each
    row stands alone with full vehicle / slot / camera context."""
    # WS-8 schema-compat: cache the probe so SELECT and WHERE branch in lockstep.
    schema = _floor_schema()
    ps_floor_id = "ps.floor_id" if schema["parking_sessions_floor_id"] else "NULL"
    clauses = ["1=1"]
    params: dict = {}

    if search:
        clauses.append(f"(ps.plate_number LIKE :search OR {OWNER_NAME_EXPR} LIKE :search)")
        params["search"] = f"%{search}%"
    # WS-8.E: integer-id filter wins; fall back to legacy string filter for back-compat.
    # Schema-compat: when the floor_id column doesn't exist yet, fall through to the string filter.
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=None)
    if resolved_floor_id is not None and schema["parking_sessions_floor_id"]:
        clauses.append("ps.floor_id = :floor_id")
        params["floor_id"] = resolved_floor_id
    elif floor:
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
    if min_duration_seconds is not None:
        clauses.append("ps.duration_seconds >= :min_dur")
        params["min_dur"] = min_duration_seconds
    if max_duration_seconds is not None:
        clauses.append("ps.duration_seconds <= :max_dur")
        params["max_dur"] = max_duration_seconds

    where = " AND ".join(clauses)
    total = scalar(db, f"""
        SELECT COUNT(*)
        FROM parking_sessions ps
        {VEHICLE_JOIN}
        WHERE {where}
    """, params)

    params["offset"] = (page - 1) * page_size
    params["page_size"] = page_size

    event_rows = rows(db, f"""
        SELECT
            ps.id,
            ps.vehicle_id,
            ps.plate_number,
            ps.status,
            ps.entry_time,
            ps.exit_time,
            ps.duration_seconds,
            ps.floor,
            {ps_floor_id} AS floor_id,
            ps.slot_id,
            COALESCE(pk.slot_name, ps.slot_number) AS slot_name,
            ps.slot_number,
            ps.parked_at,
            ps.slot_left_at,
            ps.entry_camera_id,
            ps.exit_camera_id,
            ps.slot_camera_id,
            ps.entry_snapshot_path,
            ps.exit_snapshot_path,
            ps.slot_snapshot_path,
            {OWNER_NAME_EXPR}   AS owner_name,
            {VEHICLE_TYPE_EXPR} AS vehicle_type,
            ps.is_employee
        FROM parking_sessions ps
        {VEHICLE_JOIN}
        LEFT JOIN parking_slots pk ON pk.slot_id = ps.slot_id
        WHERE {where}
        ORDER BY ps.entry_time DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)

    items = [_event_from_row(r, r["plate_number"]) for r in event_rows]
    return build_paged(items, total or 0, page, page_size)


@router.get("/export/csv")
async def export_entry_exit_csv(
    search: Optional[str] = Query(None),
    floor: Optional[str] = Query(None),
    # WS-8.E: integer-id sibling filter; wins over `?floor=` when both are sent.
    floor_id: Optional[int] = Query(None),
    is_employee: Optional[bool] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    min_duration_seconds: Optional[int] = Query(None, ge=0),
    max_duration_seconds: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    schema = _floor_schema()
    ps_floor_id = "ps.floor_id" if schema["parking_sessions_floor_id"] else "NULL"
    clauses = ["1=1"]
    params: dict = {}
    if search:
        clauses.append(f"(ps.plate_number LIKE :search OR {OWNER_NAME_EXPR} LIKE :search)")
        params["search"] = f"%{search}%"
    # WS-8.E: same dual-key floor filter pattern as the list endpoint.
    # Schema-compat: when ps.floor_id column missing, fall through to legacy string filter.
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=None)
    if resolved_floor_id is not None and schema["parking_sessions_floor_id"]:
        clauses.append("ps.floor_id = :floor_id")
        params["floor_id"] = resolved_floor_id
    elif floor:
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
    if min_duration_seconds is not None:
        clauses.append("ps.duration_seconds >= :min_dur")
        params["min_dur"] = min_duration_seconds
    if max_duration_seconds is not None:
        clauses.append("ps.duration_seconds <= :max_dur")
        params["max_dur"] = max_duration_seconds

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
            {ps_floor_id}                                    AS [Floor ID],
            ps.slot_id                                       AS [Slot ID],
            COALESCE(pk.slot_name, ps.slot_number)           AS [Slot Name],
            ps.parked_at                                     AS [Parked At],
            ps.slot_left_at                                  AS [Slot Left At],
            ps.entry_camera_id                               AS [Entry Camera],
            ps.exit_camera_id                                AS [Exit Camera]
        FROM parking_sessions ps
    """ + VEHICLE_JOIN + f"""
        LEFT JOIN parking_slots pk ON pk.slot_id = ps.slot_id
        WHERE {" AND ".join(clauses)}
        ORDER BY ps.entry_time DESC
    """, params)

    # WS-8.E: Floor ID column added next to Floor.
    headers = ["Plate Number", "Owner", "Vehicle Type", "Employee", "Status",
               "Entry Time", "Exit Time", "Duration (min)", "Floor", "Floor ID",
               "Slot ID", "Slot Name",
               "Parked At", "Slot Left At", "Entry Camera", "Exit Camera"]
    return stream_csv(data, headers, filename="entry_exit.csv")


# ── GET /entry-exit/by-vehicle/{vehicle_id} ──────────────────────────────────
@router.get("/by-vehicle/{vehicle_id}", response_model=PagedResponse[VehicleEvent])
async def get_events_by_vehicle(
    vehicle_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="open | closed | overstay | unknown_exit"),
    direction: Optional[str] = Query(
        None,
        description="entry → only events with an entry; exit → only events with an exit recorded; null → both",
    ),
    floor: Optional[str] = Query(None),
    # WS-8.E: integer-id sibling filter; wins over `?floor=` when both are sent.
    floor_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    min_duration_seconds: Optional[int] = Query(None, ge=0),
    max_duration_seconds: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    """All parking events for a single vehicle, with the same filter set as
    the main list. Falls back to plate-based matching for legacy session
    rows whose vehicle_id was never populated."""
    schema = _floor_schema()
    ps_floor_id = "ps.floor_id" if schema["parking_sessions_floor_id"] else "NULL"
    # Look up the plate so we can match legacy sessions (vehicle_id = NULL).
    vehicle_rows = rows(
        db,
        "SELECT plate_number FROM vehicles WHERE id = :id",
        {"id": vehicle_id},
    )
    if not vehicle_rows:
        from fastapi import HTTPException
        raise HTTPException(404, "Vehicle not found")
    plate = vehicle_rows[0]["plate_number"]

    clauses = ["(ps.vehicle_id = :vid OR ps.plate_number = :plate)"]
    params: dict = {"vid": vehicle_id, "plate": plate}

    if status:
        clauses.append("ps.status = :status")
        params["status"] = status
    if direction == "entry":
        clauses.append("ps.entry_time IS NOT NULL")
    elif direction == "exit":
        clauses.append("ps.exit_time IS NOT NULL")
    # WS-8.E: integer-id wins; legacy string filter remains for back-compat.
    # Schema-compat: when ps.floor_id column missing, fall through to legacy filter.
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=None)
    if resolved_floor_id is not None and schema["parking_sessions_floor_id"]:
        clauses.append("ps.floor_id = :floor_id")
        params["floor_id"] = resolved_floor_id
    elif floor:
        clauses.append("ps.floor = :floor")
        params["floor"] = floor
    if date_from:
        clauses.append("CAST(ps.entry_time AS DATE) >= :date_from")
        params["date_from"] = str(date_from)
    if date_to:
        clauses.append("CAST(ps.entry_time AS DATE) <= :date_to")
        params["date_to"] = str(date_to)
    if min_duration_seconds is not None:
        clauses.append("ps.duration_seconds >= :min_dur")
        params["min_dur"] = min_duration_seconds
    if max_duration_seconds is not None:
        clauses.append("ps.duration_seconds <= :max_dur")
        params["max_dur"] = max_duration_seconds

    where = " AND ".join(clauses)
    total = scalar(
        db,
        f"SELECT COUNT(*) FROM parking_sessions ps WHERE {where}",
        params,
    )

    params["offset"] = (page - 1) * page_size
    params["page_size"] = page_size

    event_rows = rows(db, f"""
        SELECT
            ps.id,
            ps.vehicle_id,
            ps.plate_number,
            ps.status,
            ps.entry_time,
            ps.exit_time,
            ps.duration_seconds,
            ps.floor,
            {ps_floor_id} AS floor_id,
            ps.slot_id,
            COALESCE(pk.slot_name, ps.slot_number) AS slot_name,
            ps.slot_number,
            ps.parked_at,
            ps.slot_left_at,
            ps.entry_camera_id,
            ps.exit_camera_id,
            ps.slot_camera_id,
            ps.entry_snapshot_path,
            ps.exit_snapshot_path,
            ps.slot_snapshot_path,
            {OWNER_NAME_EXPR}   AS owner_name,
            {VEHICLE_TYPE_EXPR} AS vehicle_type,
            ps.is_employee
        FROM parking_sessions ps
        {VEHICLE_JOIN}
        LEFT JOIN parking_slots pk ON pk.slot_id = ps.slot_id
        WHERE {where}
        ORDER BY ps.entry_time DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)

    items = [_event_from_row(r, r["plate_number"]) for r in event_rows]
    return build_paged(items, total or 0, page, page_size)


# Declared LAST so FastAPI matches specific routes (/kpis, /traffic, /, /export/csv) first.
@router.get("/{event_id}", response_model=VehicleEventDetail)
async def get_entry_exit_detail(event_id: int, db: Session = Depends(get_db)):
    """Detail view for a single parking event. One fetch — includes vehicle,
    slot, entry/exit cameras, and any alerts that fired during this event."""
    schema = _floor_schema()
    ps_floor_id = "ps.floor_id" if schema["parking_sessions_floor_id"] else "NULL"
    event_rows = rows(db, f"""
        SELECT
            ps.id,
            ps.vehicle_id,
            ps.plate_number,
            ps.status,
            ps.entry_time,
            ps.exit_time,
            ps.duration_seconds,
            ps.floor,
            {ps_floor_id} AS floor_id,
            ps.slot_id,
            COALESCE(pk.slot_name, ps.slot_number) AS slot_name,
            ps.slot_number,
            ps.parked_at,
            ps.slot_left_at,
            ps.entry_camera_id,
            ps.exit_camera_id,
            ps.slot_camera_id,
            ps.entry_snapshot_path,
            ps.exit_snapshot_path,
            ps.slot_snapshot_path,
            {OWNER_NAME_EXPR}   AS owner_name,
            {VEHICLE_TYPE_EXPR} AS vehicle_type,
            v_id.id             AS vehicle_pk,
            v_id.employee_id    AS emp_id_id,
            v_id.title          AS emp_title,
            v_id.phone,
            v_id.email,
            v_id.is_employee,
            v_id.is_registered,
            v_id.registered_at,
            v_id.notes,
            pk.floor            AS slot_floor,
            pk.is_available     AS slot_is_available,
            pk.is_violation_zone AS slot_is_violation,
            pk.polygon          AS slot_polygon
        FROM parking_sessions ps
        {VEHICLE_JOIN}
        LEFT JOIN parking_slots pk ON pk.slot_id = ps.slot_id
        WHERE ps.id = :id
    """, {"id": event_id})

    if not event_rows:
        raise HTTPException(404, "Parking event not found")

    r = event_rows[0]
    plate = r["plate_number"]
    base_event = _event_from_row(r, plate)

    vehicle = None
    if r.get("vehicle_pk"):
        vehicle = VehicleRef(
            id=r["vehicle_pk"],
            plate_number=plate,
            owner_name=r.get("owner_name"),
            vehicle_type=r.get("vehicle_type"),
            is_employee=r.get("is_employee"),
            employee_id=r.get("emp_id_id"),
            title=r.get("emp_title"),
            phone=r.get("phone"),
            email=r.get("email"),
            is_registered=bool(r.get("is_registered")) if r.get("is_registered") is not None else False,
            registered_at=r.get("registered_at"),
            notes=r.get("notes"),
        )

    slot = None
    if r.get("slot_id"):
        slot = {
            "slot_id": r["slot_id"],
            "slot_name": r.get("slot_name"),
            "floor": r.get("slot_floor") or r.get("floor"),
            # WS-8.E: integer-id sibling field on the slot dict.
            "floor_id": r.get("floor_id"),
            "is_available": bool(r.get("slot_is_available")) if r.get("slot_is_available") is not None else True,
            "is_violation_slot": bool(r.get("slot_is_violation")) if r.get("slot_is_violation") is not None else False,
            "polygon": r.get("slot_polygon"),
        }

    # WS-8 schema-compat: same NULL-fallback pattern for cameras integer cols.
    cam_floor_id = "floor_id" if schema["cameras_floor_id"] else "NULL AS floor_id"
    cam_watches_floor_id = (
        "watches_floor_id" if schema["cameras_watches_floor_id"]
        else "NULL AS watches_floor_id"
    )

    def _camera_ref(camera_id: Optional[str]) -> Optional[CameraRef]:
        if not camera_id:
            return None
        # WS-8.E: pull floor_id / watches_floor[_id] so CameraRef populates the new fields.
        cam = rows(
            db,
            f"SELECT id, camera_id, name, floor, {cam_floor_id}, watches_floor, "
            f"{cam_watches_floor_id} "
            "FROM cameras WHERE camera_id = :cid",
            {"cid": camera_id},
        )
        if not cam:
            return None
        c = cam[0]
        return CameraRef(
            id=c["id"],
            camera_id=c["camera_id"],
            name=c.get("name"),
            floor=c.get("floor"),
            floor_id=c.get("floor_id"),
            watches_floor=c.get("watches_floor"),
            watches_floor_id=c.get("watches_floor_id"),
        )

    entry_camera = _camera_ref(r.get("entry_camera_id"))
    exit_camera = _camera_ref(r.get("exit_camera_id"))

    # Alerts that fired between entry and exit (or after entry if still open)
    alert_where = ["a.is_test = 0", "a.plate_number = :plate", "a.triggered_at >= :entry_time"]
    alert_params: dict = {"plate": plate, "entry_time": r["entry_time"]}
    if r.get("exit_time"):
        alert_where.append("a.triggered_at <= :exit_time")
        alert_params["exit_time"] = r["exit_time"]
    alert_rows = rows(db, f"""
        SELECT TOP 50
            a.id, a.alert_type, a.plate_number, a.camera_id,
            a.description, a.snapshot_path AS snapshot_url,
            a.triggered_at, a.resolved_at, a.is_resolved
        FROM alerts a
        WHERE {" AND ".join(alert_where)}
        ORDER BY a.triggered_at DESC
    """, alert_params)

    return VehicleEventDetail(
        **base_event.model_dump(),
        vehicle=vehicle,
        slot=slot,
        entry_camera=entry_camera,
        exit_camera=exit_camera,
        alerts=[AlertItem(**{**a, "snapshot_url": resolve_snapshot_url(a.get("snapshot_url"))}) for a in alert_rows],
    )