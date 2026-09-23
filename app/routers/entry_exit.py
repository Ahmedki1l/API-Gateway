from datetime import date, datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import facility_now_naive, facility_today_utc, facility_tz, localize_naive
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
from app.schemas_enums import EntryExitDirection, ParkingSessionStatus
from app.shared import build_paged, plate_search_clause, stream_csv

from app.routers.prefix_injection import (get_prefix)
prefix = get_prefix() + "/entry-exit"

router = APIRouter(prefix=prefix, tags=["Entry/Exit"])


def _live_duration_seconds(
    entry_time, exit_time, parked_at, stored_duration: Optional[int]
) -> Optional[int]:
    """Return the session's elapsed seconds, computed live when the session
    is still open.

    Rules:
      - If the session is closed (exit_time set), trust the stored value when
        present, otherwise compute (exit_time - start) ourselves.
      - If still open, use the entry timestamp, falling back to slot occupation:
          * `entry_time` (line-crossing at B1 entry, or ANPR at the gate),
          * else `parked_at` (slot occupation on the Ground Floor / direct
            slot detection without a prior entry event).
      - Returns None when neither start signal has fired yet.

    Naive database timestamps are facility-local. Aware timestamps retain
    their offsets when computing elapsed time.
    """
    def _as_aware(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=facility_tz())
        return dt

    entry_utc = _as_aware(entry_time)
    exit_utc = _as_aware(exit_time)
    parked_utc = _as_aware(parked_at)
    start = entry_utc or parked_utc
    if start is None:
        return None
    end = exit_utc or _as_aware(facility_now_naive())
    if exit_utc is not None and stored_duration is not None:
        # Trust the writer's stored value once a session is closed — it's
        # what reports/CSVs have been pinned to historically.
        return int(stored_duration)
    return max(int((end - start).total_seconds()), 0)


def _duration_sql(alias: str = "ps") -> str:
    """SQL equivalent of _live_duration_seconds; aliases are internal constants."""
    prefix = f"{alias}." if alias else ""
    start = f"COALESCE({prefix}entry_time, {prefix}parked_at)"
    end = f"COALESCE({prefix}exit_time, :now_naive)"
    return f"""CASE
        WHEN {start} IS NULL THEN NULL
        WHEN {prefix}exit_time IS NOT NULL AND {prefix}duration_seconds IS NOT NULL
            THEN {prefix}duration_seconds
        WHEN {end} < {start} THEN 0
        ELSE DATEDIFF(SECOND, {start}, {end})
    END"""


def _event_from_row(r: dict, plate_number: str) -> VehicleEvent:
    """Build a VehicleEvent with nested entry + optional exit from a parking_sessions row.
    The row should include the joined `owner_name`, `vehicle_type`, `is_employee`
    columns (queries below alias them under those names)."""
    vehicle_id = r.get("vehicle_id")
    _today_naive = facility_today_utc().replace(tzinfo=None)
    entry_time_raw = r.get("entry_time")
    is_overstay = (
        r.get("status") in ("open", "overstay")
        and entry_time_raw is not None
        and entry_time_raw < _today_naive
    )
    entry = EntryExitEvent(
        plate_number=plate_number,
        vehicle_id=vehicle_id,
        direction="entry",
        camera_id=r.get("entry_camera_id"),
        event_time=localize_naive(r.get("entry_time")),
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
            event_time=localize_naive(r.get("exit_time")),
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
        is_overstay=is_overstay,
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
        parked_at=localize_naive(r.get("parked_at")),
        slot_left_at=localize_naive(r.get("slot_left_at")),
        slot_camera_id=r.get("slot_camera_id"),
        slot_snapshot_url=resolve_snapshot_url(r.get("slot_snapshot_path")),
    )
 
VEHICLE_JOIN = """
    LEFT JOIN vehicles v_id ON v_id.id = ps.vehicle_id
    LEFT JOIN vehicles v_plate ON ps.vehicle_id IS NULL AND v_plate.plate_number = ps.plate_number
"""
OWNER_NAME_EXPR = "COALESCE(v_id.owner_name, v_plate.owner_name)"
VEHICLE_TYPE_EXPR = "COALESCE(v_id.vehicle_type, v_plate.vehicle_type, ps.vehicle_type)"
# Prefer the registry's CURRENT is_employee over the parking_sessions snapshot
# (which is frozen at session creation). Keeps the list filter + list display +
# detail page consistent — fixes the bug where a vehicle showed under the
# "Employee = No" filter but its detail read "Employee = Yes".
IS_EMPLOYEE_EXPR = "COALESCE(v_id.is_employee, v_plate.is_employee, ps.is_employee)"
VEHICLE_TITLE_EXPR = "COALESCE(v_id.title, v_plate.title)"


def _entry_exit_filters(
    db: Session,
    schema: dict,
    *,
    search: Optional[str],
    floor: Optional[str],
    floor_id: Optional[int],
    is_employee: Optional[bool],
    status: Optional[ParkingSessionStatus],
    date_from: Optional[date],
    date_to: Optional[date],
    min_duration_seconds: Optional[int],
    max_duration_seconds: Optional[int],
) -> tuple[str, dict]:
    """Build the filter shared by the Entry/Exit list, count, and CSV export."""
    clauses = ["1=1"]
    params: dict = {"now_naive": facility_now_naive()}

    if search:
        plate_clause = plate_search_clause("ps.plate_number", search, params)
        clauses.append(
            f"({plate_clause} OR {OWNER_NAME_EXPR} LIKE :search "
            f"OR {VEHICLE_TITLE_EXPR} LIKE :search)"
        )
        params["search"] = f"%{search}%"
    # Schema-compat: when the floor_id column doesn't exist yet, fall through
    # to the legacy string filter.
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=None)
    if resolved_floor_id is not None and schema["parking_sessions_floor_id"]:
        clauses.append("ps.floor_id = :floor_id")
        params["floor_id"] = resolved_floor_id
    elif floor:
        clauses.append("ps.floor = :floor")
        params["floor"] = floor
    if is_employee is not None:
        # Match the vehicle's CURRENT employee status, not the frozen session snapshot.
        clauses.append(f"{IS_EMPLOYEE_EXPR} = :is_employee")
        params["is_employee"] = 1 if is_employee else 0
    if status:
        if status == "overstay":
            clauses.append("ps.status IN ('open', 'overstay')")
            clauses.append("ps.entry_time < :overstay_cutoff")
            params["overstay_cutoff"] = facility_today_utc()
        else:
            clauses.append("ps.status = :status")
            params["status"] = status
    # Completed visits are selected by departure date, including overnight stays.
    date_column = "ps.exit_time" if status == ParkingSessionStatus.closed else "ps.entry_time"
    if date_from:
        clauses.append(f"CAST({date_column} AS DATE) >= :date_from")
        params["date_from"] = str(date_from)
    if date_to:
        clauses.append(f"CAST({date_column} AS DATE) <= :date_to")
        params["date_to"] = str(date_to)
    if min_duration_seconds is not None:
        clauses.append(f"({_duration_sql()}) >= :min_dur")
        params["min_dur"] = min_duration_seconds
    if max_duration_seconds is not None:
        clauses.append(f"({_duration_sql()}) <= :max_dur")
        params["max_dur"] = max_duration_seconds
    return " AND ".join(clauses), params


def _entry_exit_order(
    sort_by: Literal["entry_time", "exit_time"],
    sort_direction: Literal["asc", "desc"],
) -> str:
    """Return the only supported, deterministic session ordering.

    A NULL timestamp always follows dated sessions. Rows with the same
    timestamp (including NULL timestamps) use ``ps.id`` in the requested
    direction, so pagination cannot shuffle them between requests.
    """
    columns = {"entry_time": "ps.entry_time", "exit_time": "ps.exit_time"}
    directions = {"asc": "ASC", "desc": "DESC"}
    column = columns[sort_by]
    direction = directions[sort_direction]
    return (
        f"CASE WHEN {column} IS NULL THEN 1 ELSE 0 END ASC, "
        f"{column} {direction}, ps.id {direction}"
    )
 
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
    scope: Literal["today", "filtered"] = Query("today"),
    search: Optional[str] = Query(None),
    floor: Optional[str] = Query(None),
    floor_id: Optional[int] = Query(None),
    is_employee: Optional[bool] = Query(None),
    status: Optional[ParkingSessionStatus] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    min_duration_seconds: Optional[int] = Query(None, ge=0),
    max_duration_seconds: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    if scope == "filtered":
        where, params = _entry_exit_filters(
            db, _floor_schema(), search=search, floor=floor, floor_id=floor_id,
            is_employee=is_employee, status=status,
            date_from=date_from or target_date, date_to=date_to or target_date,
            min_duration_seconds=min_duration_seconds,
            max_duration_seconds=max_duration_seconds,
        )
        params["start_of_today"] = facility_today_utc()
        summary = rows(db, f"""
            SELECT COUNT(*) AS total_enter,
                SUM(CASE WHEN ps.status = 'closed' THEN 1 ELSE 0 END) AS total_exit,
                AVG(CASE WHEN ps.status = 'closed'
                    THEN CAST({_duration_sql()} AS FLOAT) END) AS avg_stay_sec,
                COUNT(DISTINCT CASE WHEN ps.status IN ('open', 'overstay')
                    AND ps.entry_time < :start_of_today
                    THEN ps.plate_number END) AS overstays
            FROM parking_sessions ps
            {VEHICLE_JOIN}
            WHERE {where}
        """, params)[0]
        return EntryExitKPIs(
            total_enter=summary["total_enter"] or 0,
            total_exit=summary["total_exit"] or 0,
            avg_stay_minutes=round((summary["avg_stay_sec"] or 0) / 60, 1),
            overstays=summary["overstays"] or 0,
        )
    if target_date:
        # Specific date provided: filter for that 24h window in facility-local time.
        # NAIVE local, not UTC-aware: parking_sessions timestamps are stored
        # facility-local-naive (convention since 2026-05-07), so converting to UTC
        # here shifted the whole window 3h earlier and made a target_date KPI cover
        # 21:00 the previous evening → 21:00 that day.
        dt_local = datetime.combine(target_date, datetime.min.time())
        start_local = dt_local
        end_local   = dt_local + timedelta(days=1)
        date_filter = "AND entry_time >= :start AND entry_time < :end"
        params = {"start": start_local, "end": end_local}
    else:
        # facility_today_utc() returns naive facility-local midnight today.
        start_local = facility_today_utc()
        date_filter = "AND entry_time >= :start"
        params = {"start": start_local}

    total_enter = scalar(db, f"""
        SELECT COUNT(*)
        FROM parking_sessions
        WHERE 1=1 {date_filter}
    """, params)

    # Departures belong to their exit day, including visits entered earlier.
    # Use a half-open facility-local day for explicit dates and today's default.
    total_exit = scalar(db, """
        SELECT COUNT(*)
        FROM parking_sessions
        WHERE status = 'closed'
          AND exit_time >= :start AND exit_time < :end
    """, {"start": start_local, "end": start_local + timedelta(days=1)})

    # Completed visits only, attributed to departure day. Open visits continue
    # displaying live duration in lists/exports but do not distort completed stays.
    now_naive = facility_now_naive()
    avg_stay_sec = scalar(db, f"""
        SELECT AVG(CAST({_duration_sql('')} AS FLOAT))
        FROM parking_sessions
        WHERE status = 'closed'
          AND exit_time >= :start AND exit_time < :end
    """, {"start": start_local, "end": start_local + timedelta(days=1),
           "now_naive": now_naive})
    avg_stay_minutes = round((avg_stay_sec or 0) / 60, 1)

    # Overstays = unique vehicles that entered before today's local midnight and are still open
    overstays = scalar(db, """
        SELECT COUNT(DISTINCT plate_number)
        FROM parking_sessions
        WHERE plate_number IS NOT NULL
          AND (status = 'open' OR status = 'overstay')
          AND entry_time < :start_of_today
    """, {"start_of_today": start_local})

    return EntryExitKPIs(
        total_enter=total_enter or 0,
        total_exit=total_exit or 0,
        avg_stay_minutes=avg_stay_minutes,
        overstays=overstays or 0,
    )
 
 
@router.get("/traffic", response_model=list[TrafficBucket])
async def traffic_chart(
    period: Literal["daily", "weekly", "monthly"] = Query("daily"),
    db: Session = Depends(get_db),
):
    """Zero-filled traffic from facility-local-naive entry_exit_log timestamps.

    Daily covers the operating day (08:00–08:00 by default); before its start,
    the previous operating day is shown. Weekly/monthly retain their rolling
    7/30 calendar-day windows ending today. No timestamp-format guessing or
    historical data rewriting is performed.
    """
    from app.config import settings

    now_local = facility_now_naive()
    if period == "daily":
        window_start = now_local.replace(
            hour=settings.traffic_day_start_hour, minute=0, second=0, microsecond=0
        )
        if now_local < window_start:
            window_start -= timedelta(days=1)
        window_end = window_start + timedelta(days=1)
        count, unit, step, date_fmt = 24, "HOUR", timedelta(hours=1), "%H:00"
    else:
        count = 7 if period == "weekly" else 30
        today = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        window_start = today - timedelta(days=count - 1)
        window_end = today + timedelta(days=1)
        unit, step = "DAY", timedelta(days=1)
        date_fmt = "%A" if period == "weekly" else (
            "%b %d, %Y" if window_start.year != today.year else "%b %d"
        )

    buckets = [
        {"label": (window_start + i * step).strftime(date_fmt), "entries": 0, "exits": 0}
        for i in range(count)
    ]
    # Group by the derived column: repeating a bound DATEDIFF expression in
    # SELECT and GROUP BY produces distinct ODBC parameters and SQL Server 8120.
    # unit is selected internally above; every timestamp boundary is parameterized.
    result = rows(db, f"""
        SELECT bucket_idx,
               SUM(CASE WHEN gate LIKE '%entry%' OR gate LIKE '%in%' THEN 1 ELSE 0 END) AS entries,
               SUM(CASE WHEN gate LIKE '%exit%' OR gate LIKE '%out%' THEN 1 ELSE 0 END) AS exits
        FROM (
            SELECT DATEDIFF({unit}, :start_local, event_time) AS bucket_idx, gate
            FROM entry_exit_log
            WHERE event_time >= :start_local AND event_time < :end_local
              AND is_test = 0
        ) AS bucketed_events
        GROUP BY bucket_idx
    """, {"start_local": window_start, "end_local": window_end})
    for row in result:
        index = row["bucket_idx"]
        if index is not None and 0 <= index < count:
            buckets[index]["entries"] = row["entries"] or 0
            buckets[index]["exits"] = row["exits"] or 0
    return buckets


@router.get("/", response_model=PagedResponse[VehicleEvent])
async def get_entry_exit(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="plate number, owner name, or vehicle title"),
    floor: Optional[str] = Query(None),
    # WS-8.E: integer-id sibling filter; wins over `?floor=` when both are sent.
    floor_id: Optional[int] = Query(None),
    is_employee: Optional[bool] = Query(None),
    status: Optional[ParkingSessionStatus] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    min_duration_seconds: Optional[int] = Query(None, ge=0),
    max_duration_seconds: Optional[int] = Query(None, ge=0),
    sort_by: Literal["entry_time", "exit_time"] = Query("entry_time"),
    sort_direction: Literal["asc", "desc"] = Query("desc"),
    db: Session = Depends(get_db),
):
    """Flat list of every parking event (one row per entry, expanded with its
    paired exit when present). Replaces the old grouped-by-plate shape — each
    row stands alone with full vehicle / slot / camera context."""
    # WS-8 schema-compat: cache the probe so SELECT and WHERE branch in lockstep.
    schema = _floor_schema()
    ps_floor_id = "ps.floor_id" if schema["parking_sessions_floor_id"] else "NULL"
    where, params = _entry_exit_filters(
        db, schema, search=search, floor=floor, floor_id=floor_id,
        is_employee=is_employee, status=status, date_from=date_from,
        date_to=date_to, min_duration_seconds=min_duration_seconds,
        max_duration_seconds=max_duration_seconds,
    )
    order_by = _entry_exit_order(sort_by, sort_direction)
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
            {IS_EMPLOYEE_EXPR}  AS is_employee
        FROM parking_sessions ps
        {VEHICLE_JOIN}
        LEFT JOIN parking_slots pk ON pk.slot_id = ps.slot_id
        WHERE {where}
        ORDER BY {order_by}
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)

    items = [_event_from_row(r, r["plate_number"]) for r in event_rows]
    return build_paged(items, total or 0, page, page_size)


@router.get("/export/csv")
async def export_entry_exit_csv(
    search: Optional[str] = Query(None, description="plate number, owner name, or vehicle title"),
    floor: Optional[str] = Query(None),
    # WS-8.E: integer-id sibling filter; wins over `?floor=` when both are sent.
    floor_id: Optional[int] = Query(None),
    is_employee: Optional[bool] = Query(None),
    status: Optional[ParkingSessionStatus] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    min_duration_seconds: Optional[int] = Query(None, ge=0),
    max_duration_seconds: Optional[int] = Query(None, ge=0),
    sort_by: Literal["entry_time", "exit_time"] = Query("entry_time"),
    sort_direction: Literal["asc", "desc"] = Query("desc"),
    db: Session = Depends(get_db),
):
    schema = _floor_schema()
    ps_floor_id = "ps.floor_id" if schema["parking_sessions_floor_id"] else "NULL"
    where, params = _entry_exit_filters(
        db, schema, search=search, floor=floor, floor_id=floor_id,
        is_employee=is_employee, status=status, date_from=date_from,
        date_to=date_to, min_duration_seconds=min_duration_seconds,
        max_duration_seconds=max_duration_seconds,
    )
    order_by = _entry_exit_order(sort_by, sort_direction)

    # Closed visits use stored/final elapsed duration; open visits use the
    # same facility-local report clock as duration filters.
    data = rows(db, f"""
        SELECT
            ps.plate_number                                  AS [Plate Number],
            {OWNER_NAME_EXPR}                                AS [Owner],
            {VEHICLE_TYPE_EXPR}                              AS [Vehicle Type],
            {IS_EMPLOYEE_EXPR}                               AS [Employee],
            ps.status                                        AS [Status],
            ps.entry_time                                    AS [Entry Time],
            ps.exit_time                                     AS [Exit Time],
            ({_duration_sql()}) / 60.0                       AS [Duration (min)],
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
        WHERE {where}
        ORDER BY {order_by}
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
    status: Optional[ParkingSessionStatus] = Query(None),
    direction: Optional[EntryExitDirection] = Query(
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
    params["now_naive"] = facility_now_naive()
    if min_duration_seconds is not None:
        clauses.append(f"({_duration_sql()}) >= :min_dur")
        params["min_dur"] = min_duration_seconds
    if max_duration_seconds is not None:
        clauses.append(f"({_duration_sql()}) <= :max_dur")
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
            {IS_EMPLOYEE_EXPR}  AS is_employee
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
            {IS_EMPLOYEE_EXPR}  AS is_employee,
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
    cam_area = "area" if schema["cameras_area"] else "NULL AS area"

    def _camera_ref(camera_id: Optional[str]) -> Optional[CameraRef]:
        if not camera_id:
            return None
        # WS-8.E: pull floor_id / watches_floor[_id] so CameraRef populates the new fields.
        cam = rows(
            db,
            f"SELECT id, camera_id, name, {cam_area}, floor, {cam_floor_id}, watches_floor, "
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
            area=c.get("area"),
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
