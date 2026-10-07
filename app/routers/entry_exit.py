import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Optional

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
    EntryExitCounts,
    EntryExitKPIs,
    PagedResponse,
    PeakHourBucket,
    PeakHours,
    TrafficBucket,
    VehicleEvent,
    VehicleEventDetail,
    VehicleRef,
    VehicleTypeCount,
    VehicleTypeDistribution,
)
from app.schemas_enums import EntryExitDirection, EntryExitSort, ParkingSessionStatus, SortDir
from app.shared import (
    build_paged,
    order_by_nulls_last,
    plate_display_sort_expr,
    plate_search_clause,
    stream_csv,
)

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
      - If still open, count from whichever start signal fired first:
          * `entry_time` (line-crossing at B1 entry, or ANPR at the gate),
          * else `parked_at` (slot occupation on the Ground Floor / direct
            slot detection without a prior entry event).
      - Returns None when neither start signal has fired yet.

    All timestamps are UTC; we normalise tz-naive values to UTC so the
    arithmetic doesn't blow up on DBs that strip tzinfo.
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
    end = exit_utc or datetime.now(timezone.utc)
    if exit_utc is not None and stored_duration is not None:
        # Trust the writer's stored value once a session is closed — it's
        # what reports/CSVs have been pinned to historically.
        return int(stored_duration)
    return max(int((end - start).total_seconds()), 0)


def _duration_sql(alias: str = "ps", now_param: str = "now_naive") -> str:
    """SQL equivalent of _live_duration_seconds, so filters, sorting and the CSV
    use the stay the list displays: the stored value once closed, live elapsed
    time while open, NULL with no start signal, never negative. The caller binds
    `:<now_param>` to facility_now_naive(). Aliases are internal constants."""
    prefix = f"{alias}." if alias else ""
    start = f"COALESCE({prefix}entry_time, {prefix}parked_at)"
    end = f"COALESCE({prefix}exit_time, :{now_param})"
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
VEHICLE_TITLE_EXPR = "COALESCE(v_id.title, v_plate.title)"
VEHICLE_TYPE_EXPR = "COALESCE(v_id.vehicle_type, v_plate.vehicle_type, ps.vehicle_type)"
# Prefer the registry's CURRENT is_employee over the parking_sessions snapshot
# (which is frozen at session creation). Keeps the list filter + list display +
# detail page consistent — fixes the bug where a vehicle showed under the
# "Employee = No" filter but its detail read "Employee = Yes".
IS_EMPLOYEE_EXPR = "COALESCE(v_id.is_employee, v_plate.is_employee, ps.is_employee)"
 
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
 
 
def _page_range(date_from: Optional[date], date_to: Optional[date]) -> tuple[date, date]:
    """The Entry/Exit page's date picker: both omitted = today; only
    date_from = up to today; only date_to = that one day."""
    if date_from is None and date_to is None:
        date_from = date_to = facility_now_naive().date()
    elif date_to is None:
        date_to = max(date_from, facility_now_naive().date())
    elif date_from is None:
        date_from = date_to
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must not be after date_to")
    return date_from, date_to


def _midnight(d: date) -> datetime:
    return datetime.combine(d, datetime.min.time())


def _kpi_counts(db: Session, date_from: date, date_to: date) -> EntryExitCounts:
    """The four Entry/Exit cards for [date_from, date_to], facility-local days.
    parking_sessions stores facility-local naive timestamps (since 2026-05-07),
    so the day boundaries are plain local midnights."""
    params = {"start": _midnight(date_from), "end": _midnight(date_to + timedelta(days=1))}

    total_enter = scalar(db, """
        SELECT COUNT(*) FROM parking_sessions
        WHERE entry_time >= :start AND entry_time < :end
    """, params)

    # Every session CLOSED in the range, on the exit axis: a car that entered
    # yesterday and left today counts as one of today's exits. Same definition
    # as /dashboard/kpis.exits_today.
    #
    # Its drill-down is `?status=closed&exit_date_from=...` on the list/CSV, NOT
    # `date_from` (entry axis). The 2026-09-16 "card 13 vs list 3" drift came
    # from pairing this KPI with the entry-date filter; keep the two on the same
    # axis. `status = 'closed'` <=> `exit_time IS NOT NULL`: every writer goes
    # through `_close_session_record`, which sets both.
    total_exit = scalar(db, """
        SELECT COUNT(*) FROM parking_sessions
        WHERE status = 'closed' AND exit_time >= :start AND exit_time < :end
    """, params)

    # Cars that ENTERED in the range; an open session counts its live elapsed
    # time. facility_now_naive(), not GETUTCDATE(): the column is local.
    avg_stay_sec = scalar(db, """
        SELECT AVG(CAST(COALESCE(duration_seconds, DATEDIFF(SECOND, entry_time, :now)) AS FLOAT))
        FROM parking_sessions
        WHERE entry_time >= :start AND entry_time < :end
    """, {**params, "now": facility_now_naive()})

    return EntryExitCounts(
        total_enter=total_enter or 0,
        total_exit=total_exit or 0,
        avg_stay_minutes=round((avg_stay_sec or 0) / 60, 1),
        overstays=overstay_count(db, date_from, date_to),
    )


def overstay_sessions_sql(
    date_from: Optional[date],
    date_to: Optional[date],
    *,
    floor: Optional[str] = None,
    floor_id: Optional[int] = None,
    search: Optional[str] = None,
    plate: Optional[str] = None,
) -> tuple[str, dict]:
    """`(sql, params)`: a SELECT of every parking_sessions row that
    overstayed in [date_from, date_to] — one row per stay. A stay overstayed
    if the car was inside the garage at a local midnight that falls in the
    range (the midnights that START each day of it, up to today's). No
    date_from = since the first session; no date_to = up to today.

    `first_mn` is the first such midnight after the car entered; it
    overstayed if that midnight is still in the range and the car had not
    left by then. For "today" this is every car that was inside at 00:00,
    whether it has left since or not. `over_from` is the first midnight after
    entry, NOT clipped to the range: when the overstay began.

    Nothing writes an `overstay` alert (Damanat-DB-Migrator 0010), so this is
    the only overstay source: the Entry/Exit Overstays card (distinct cars,
    `overstay_count`) and GET /alerts/reports/overstay-violations (stays)
    both read it."""
    today = facility_now_naive().date()
    params: dict = {"last_mn": _midnight(min(date_to, today) if date_to else today)}
    next_mn = "DATEADD(DAY, 1, CAST(CAST(entry_time AS DATE) AS DATETIME2))"
    if date_from:
        params["start"] = _midnight(date_from)
        first_mn = f"CASE WHEN {next_mn} > :start THEN {next_mn} ELSE :start END"
    else:
        first_mn = next_mn

    clauses = ["plate_number IS NOT NULL", "entry_time < :last_mn"]
    schema = _floor_schema()
    if floor_id is not None and schema["parking_sessions_floor_id"]:
        clauses.append("floor_id = :floor_id")
        params["floor_id"] = floor_id
    elif floor:
        clauses.append("floor = :floor")
        params["floor"] = floor
    if search:
        clauses.append(plate_search_clause("plate_number", search, params, prefix="ovplate"))
    if plate:
        clauses.append(plate_search_clause("plate_number", plate, params, prefix="ovpn"))

    return f"""
        SELECT s.* FROM (
            SELECT id, plate_number, floor, slot_id, slot_number, exit_time,
                   slot_snapshot_path, entry_snapshot_path,
                   {next_mn} AS over_from, {first_mn} AS first_mn
            FROM parking_sessions
            WHERE {" AND ".join(clauses)}
        ) s
        WHERE s.first_mn <= :last_mn AND (s.exit_time IS NULL OR s.exit_time > s.first_mn)
    """, params


def overstay_count(
    db: Session,
    date_from: Optional[date],
    date_to: Optional[date],
    *,
    floor: Optional[str] = None,
    floor_id: Optional[int] = None,
    search: Optional[str] = None,
) -> int:
    """Distinct CARS that overstayed in [date_from, date_to] — the Entry/Exit
    Overstays card. See `overstay_sessions_sql` for the rule."""
    sql, params = overstay_sessions_sql(date_from, date_to, floor=floor, floor_id=floor_id, search=search)
    return scalar(db, f"SELECT COUNT(DISTINCT o.plate_number) FROM ({sql}) o", params) or 0


@router.get("/kpis", response_model=EntryExitKPIs)
async def entry_exit_kpis(
    date_from: Optional[date] = Query(None, description="First day (inclusive), facility-local. Omit both for today."),
    date_to: Optional[date] = Query(None, description="Last day (inclusive), facility-local."),
    target_date: Optional[date] = Query(None, description="Deprecated: one day, same as date_from=date_to=target_date."),
    db: Session = Depends(get_db),
):
    """Entry/Exit KPI cards for the date range (today when omitted).
    `previous` holds the same four numbers for the equally long period right
    before it (yesterday, for today); the frontend draws the "vs" arrows."""
    if target_date and not (date_from or date_to):
        date_from = date_to = target_date
    date_from, date_to = _page_range(date_from, date_to)
    days = (date_to - date_from).days + 1
    prev_to = date_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=days - 1)
    return EntryExitKPIs(
        **_kpi_counts(db, date_from, date_to).model_dump(),
        date_from=date_from,
        date_to=date_to,
        previous=_kpi_counts(db, prev_from, prev_to),
        previous_from=prev_from,
        previous_to=prev_to,
    )


@router.get("/peak-hours", response_model=PeakHours)
async def peak_hours(
    date_from: Optional[date] = Query(None, description="First day (inclusive), facility-local. Omit both for today."),
    date_to: Optional[date] = Query(None, description="Last day (inclusive), facility-local."),
    db: Session = Depends(get_db),
):
    """Peak Entry / Exit Hours chart: 24 bars (hour 0-23, facility-local),
    each summed over every day in the range. Same sessions as /kpis, so the
    bars add up to its total_enter / total_exit."""
    date_from, date_to = _page_range(date_from, date_to)
    params = {"start": _midnight(date_from), "end": _midnight(date_to + timedelta(days=1))}
    items = [PeakHourBucket(hour=h, entries=0, exits=0) for h in range(24)]
    for r in rows(db, """
        SELECT DATEPART(HOUR, entry_time) AS h, COUNT(*) AS n FROM parking_sessions
        WHERE entry_time >= :start AND entry_time < :end
        GROUP BY DATEPART(HOUR, entry_time)
    """, params):
        items[int(r["h"])].entries = int(r["n"])
    for r in rows(db, """
        SELECT DATEPART(HOUR, exit_time) AS h, COUNT(*) AS n FROM parking_sessions
        WHERE status = 'closed' AND exit_time >= :start AND exit_time < :end
        GROUP BY DATEPART(HOUR, exit_time)
    """, params):
        items[int(r["h"])].exits = int(r["n"])
    return PeakHours(date_from=date_from, date_to=date_to, items=items)


# Ranges up to this many days are drawn hour by hour; longer ones day by day.
_TRAFFIC_HOURLY_MAX_DAYS = 2


def _last_24_hours() -> tuple[datetime, datetime]:
    """The default chart window: the current facility-local hour and the 23
    before it, so exactly 24 hourly bars with the newest one partial."""
    start = facility_now_naive().replace(minute=0, second=0, microsecond=0) - timedelta(hours=23)
    return start, start + timedelta(hours=24)


def _ranged_traffic(db: Session, date_from: Optional[date], date_to: Optional[date]) -> list[TrafficBucket]:
    """Traffic chart for [date_from, date_to], facility-local days, zero-filled;
    no dates = the last 24 hours. Same sessions as /kpis and /peak-hours, so
    the bars of a date range add up to its total_enter / total_exit. Labels
    are `YYYY-MM-DDTHH:00` (hourly) or `YYYY-MM-DD` (daily); the frontend
    formats them."""
    if date_from is None and date_to is None:
        start, end = _last_24_hours()
        unit, step, fmt, count = "HOUR", timedelta(hours=1), "%Y-%m-%dT%H:00", 24
    else:
        date_from, date_to = _page_range(date_from, date_to)
        start, end = _midnight(date_from), _midnight(date_to + timedelta(days=1))
        days = (date_to - date_from).days + 1
        if days <= _TRAFFIC_HOURLY_MAX_DAYS:
            unit, step, fmt, count = "HOUR", timedelta(hours=1), "%Y-%m-%dT%H:00", days * 24
        else:
            unit, step, fmt, count = "DAY", timedelta(days=1), "%Y-%m-%d", days
    buckets = [
        TrafficBucket(label=(start + step * i).strftime(fmt), entries=0, exits=0)
        for i in range(count)
    ]
    params = {"start": start, "end": end}
    for r in rows(db, f"""
        SELECT idx, COUNT(*) AS n FROM (
            SELECT DATEDIFF({unit}, :start, entry_time) AS idx FROM parking_sessions
            WHERE entry_time >= :start AND entry_time < :end
        ) t GROUP BY idx
    """, params):
        buckets[int(r["idx"])].entries = int(r["n"])
    for r in rows(db, f"""
        SELECT idx, COUNT(*) AS n FROM (
            SELECT DATEDIFF({unit}, :start, exit_time) AS idx FROM parking_sessions
            WHERE status = 'closed' AND exit_time >= :start AND exit_time < :end
        ) t GROUP BY idx
    """, params):
        buckets[int(r["idx"])].exits = int(r["n"])
    return buckets


@router.get("/traffic", response_model=list[TrafficBucket])
async def traffic_chart(
    date_from: Optional[date] = Query(None, description="First day (inclusive), facility-local. Omit both for the last 24 hours."),
    date_to: Optional[date] = Query(None, description="Last day (inclusive), facility-local."),
    period: Optional[str] = Query(None, description="Deprecated: daily | weekly | monthly rolling window. Ignored when a date is given."),
    db: Session = Depends(get_db),
):
    """Entries / exits per bucket.

    Default (and with `date_from` / `date_to`, same picker semantics as
    /kpis): counts from `parking_sessions`, hourly buckets for ranges of up
    to 2 days, daily buckets beyond that. No params = the last 24 hours
    (current hour and the 23 before it), 24 hourly bars.

    Only an explicit `period` (and no date) takes the legacy path below:

    Rolling-window traffic counts from `entry_exit_log`, zero-filled.

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
    if period is None or date_from or date_to:
        return _ranged_traffic(db, date_from, date_to)

    from app.config import settings  # local import to avoid a circular at module load
    offset_minutes = int(settings.facility_timezone_offset_hours * 60)
    local_tz = facility_tz()

    if period == "daily":
        # 24 hourly buckets, anchored on the current local hour.
        now_local = datetime.now(local_tz)
        current_hour_local = now_local.replace(minute=0, second=0, microsecond=0)
        window_start_local = current_hour_local - timedelta(hours=23)
        window_end_local   = current_hour_local + timedelta(hours=1)
        
        # We query using UTC boundaries for performance, but bucket using local time
        # to ensure the labels match what the user expects.
        window_start_utc = window_start_local.astimezone(timezone.utc)
        window_end_utc   = window_end_local.astimezone(timezone.utc)

        full_labels: list[dict] = [
            {
                "label": (window_start_local + timedelta(hours=i)).strftime("%H:00"),
                "entries": 0,
                "exits": 0,
            }
            for i in range(24)
        ]
        
        # Hybrid query handles transition from Local to UTC storage
        sql = """
            SELECT
                bucket_idx,
                SUM(is_entry) AS entries,
                SUM(is_exit)  AS exits
            FROM (
                SELECT
                    DATEDIFF(HOUR, :start_local, 
                        CASE 
                            WHEN event_time >= :start_local THEN event_time 
                            ELSE DATEADD(MINUTE, :offset_min, event_time) 
                        END
                    ) AS bucket_idx,
                    CASE WHEN gate LIKE '%entry%' OR gate LIKE '%in%' THEN 1 ELSE 0 END AS is_entry,
                    CASE WHEN gate LIKE '%exit%'  OR gate LIKE '%out%' THEN 1 ELSE 0 END AS is_exit
                FROM entry_exit_log
                WHERE ((event_time >= :start_utc AND event_time < :end_utc)
                   OR (event_time >= :start_local AND event_time < :end_local))
                  AND is_test = 0
            ) AS t
            WHERE bucket_idx >= 0 AND bucket_idx < 24
            GROUP BY bucket_idx
        """
        params = {
            "start_local": window_start_local.replace(tzinfo=None),
            "end_local": window_end_local.replace(tzinfo=None),
            "start_utc": window_start_utc.replace(tzinfo=None), 
            "end_utc": window_end_utc.replace(tzinfo=None),
            "offset_min": offset_minutes
        }

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
                bucket_idx,
                SUM(is_entry) AS entries,
                SUM(is_exit)  AS exits
            FROM (
                SELECT
                    DATEDIFF(DAY, :start_local_date, DATEADD(MINUTE, :offset_min, event_time)) AS bucket_idx,
                    CASE WHEN gate LIKE '%entry%' OR gate LIKE '%in%' THEN 1 ELSE 0 END AS is_entry,
                    CASE WHEN gate LIKE '%exit%'  OR gate LIKE '%out%' THEN 1 ELSE 0 END AS is_exit
                FROM entry_exit_log
                WHERE event_time >= :start_utc
                  AND event_time <  :end_utc
                  AND is_test = 0
            ) AS t
            GROUP BY bucket_idx
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
                bucket_idx,
                SUM(is_entry) AS entries,
                SUM(is_exit)  AS exits
            FROM (
                SELECT
                    DATEDIFF(DAY, :start_local_date, DATEADD(MINUTE, :offset_min, event_time)) AS bucket_idx,
                    CASE WHEN gate LIKE '%entry%' OR gate LIKE '%in%' THEN 1 ELSE 0 END AS is_entry,
                    CASE WHEN gate LIKE '%exit%'  OR gate LIKE '%out%' THEN 1 ELSE 0 END AS is_exit
                FROM entry_exit_log
                WHERE event_time >= :start_utc
                  AND event_time <  :end_utc
                  AND is_test = 0
            ) AS t
            GROUP BY bucket_idx
        """
        params = {
            "start_local_date": window_start_local.date(),
            "offset_min": offset_minutes,
            "start_utc": window_start_utc,
            "end_utc": window_end_utc,
        }

    print(f"DEBUG: traffic_chart SQL: {sql}")
    db_results = rows(db, sql, params)
    for row in db_results:
        idx = row["bucket_idx"]
        if idx is not None and 0 <= idx < len(full_labels):
            full_labels[idx]["entries"] = row["entries"]
            full_labels[idx]["exits"] = row["exits"]
    return full_labels
 
 
# Values that mean "no type" and are counted as "other".
_NO_VEHICLE_TYPE = ("", "unknown", "other")


@router.get("/vehicle-types", response_model=VehicleTypeDistribution)
async def vehicle_type_distribution(
    date_from: Optional[date] = Query(None, description="First entry day (inclusive), facility-local. Omit both for today."),
    date_to: Optional[date] = Query(None, description="Last entry day (inclusive), facility-local."),
    db: Session = Depends(get_db),
):
    """Vehicle Type Distribution donut: cars that ENTERED in the range, by
    type (registry type first, else the session's). A car with no type
    (NULL, empty or 'unknown') counts as `other`. Types come from the data,
    lower-case, most first; `other` is always last, `count: 0` included.
    Same date picker as /kpis (no dates = today), so `total` equals
    /kpis.total_enter for the same range."""
    date_from, date_to = _page_range(date_from, date_to)
    params = {"start": _midnight(date_from), "end": _midnight(date_to + timedelta(days=1))}

    grouped = rows(db, f"""
        SELECT LOWER(LTRIM(RTRIM({VEHICLE_TYPE_EXPR}))) AS vehicle_type, COUNT(*) AS n
        FROM parking_sessions ps
        {VEHICLE_JOIN}
        WHERE ps.entry_time >= :start AND ps.entry_time < :end
        GROUP BY LOWER(LTRIM(RTRIM({VEHICLE_TYPE_EXPR})))
    """, params)

    counts: dict[str, int] = {}
    other = 0
    for r in grouped:
        t, n = r["vehicle_type"], int(r["n"])
        if t is None or t in _NO_VEHICLE_TYPE:
            other += n
        else:
            counts[t] = counts.get(t, 0) + n
    total = sum(counts.values()) + other
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])) + [("other", other)]
    return VehicleTypeDistribution(
        date_from=date_from,
        date_to=date_to,
        total=total,
        items=[
            VehicleTypeCount(vehicle_type=t, count=n, pct=round(n / total * 100, 1) if total else 0.0)
            for t, n in ordered
        ],
    )


# Sort keys of the Entry/Exit list, one SQL expression each — only these
# fixed strings ever reach ORDER BY. `duration` mirrors _live_duration_seconds
# so a row sorts by the stay it displays: the stored value once closed, live
# elapsed time while open.
_ENTRY_EXIT_SORT = {
    EntryExitSort.time: "COALESCE(ps.exit_time, ps.entry_time)",
    EntryExitSort.entry_time: "ps.entry_time",
    EntryExitSort.exit_time: "ps.exit_time",
    EntryExitSort.type: "CASE WHEN ps.exit_time IS NULL THEN 0 ELSE 1 END",
    EntryExitSort.plate: plate_display_sort_expr("ps.plate_number"),
    EntryExitSort.floor: "ps.floor",
    EntryExitSort.gate: "COALESCE(ps.exit_camera_id, ps.entry_camera_id)",
    EntryExitSort.duration: _duration_sql(now_param="sort_now"),
}


def _entry_exit_order(sort_by: Optional[EntryExitSort], sort_dir: SortDir, params: dict) -> str:
    """ORDER BY body for the Entry/Exit list and CSV. No `sort_by` keeps the
    historical newest-entry-first order. ps.id breaks ties so paging is stable."""
    if sort_by is None:
        return "ps.entry_time DESC, ps.id DESC"
    if sort_by is EntryExitSort.duration:
        params["sort_now"] = facility_now_naive()
    return order_by_nulls_last(_ENTRY_EXIT_SORT[sort_by], sort_dir.value.upper(), "ps.id")


_SORT_BY_DOC = ("Column to sort by, applied before paging: time (exit time, else entry "
                "time) | entry_time | exit_time | type | plate (as displayed, digits "
                "first) | floor | gate | duration (open visits: live). Empty values sort "
                "last either way. Omit for newest entry first.")
_SORT_DIR_DOC = "asc | desc (default). Ignored without sort_by."


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
    # Exit-axis sibling of date_from/date_to: filters on the day the car LEFT.
    # Drill-down for the Exits KPI (/entry-exit/kpis.total_exit).
    exit_date_from: Optional[date] = Query(None),
    exit_date_to: Optional[date] = Query(None),
    min_duration_seconds: Optional[int] = Query(None, ge=0),
    max_duration_seconds: Optional[int] = Query(None, ge=0),
    sort_by: Optional[EntryExitSort] = Query(None, description=_SORT_BY_DOC),
    sort_dir: SortDir = Query(SortDir.desc, description=_SORT_DIR_DOC),
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
        plate_clause = plate_search_clause("ps.plate_number", search, params)
        clauses.append(
            f"({plate_clause} OR {OWNER_NAME_EXPR} LIKE :search "
            f"OR {VEHICLE_TITLE_EXPR} LIKE :search)"
        )
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
        # Match the vehicle's CURRENT employee status (same source the detail
        # page shows), not the frozen parking_sessions snapshot.
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
    if date_from:
        clauses.append("CAST(ps.entry_time AS DATE) >= :date_from")
        params["date_from"] = str(date_from)
    if date_to:
        clauses.append("CAST(ps.entry_time AS DATE) <= :date_to")
        params["date_to"] = str(date_to)
    if exit_date_from:
        clauses.append("CAST(ps.exit_time AS DATE) >= :exit_date_from")
        params["exit_date_from"] = str(exit_date_from)
    if exit_date_to:
        clauses.append("CAST(ps.exit_time AS DATE) <= :exit_date_to")
        params["exit_date_to"] = str(exit_date_to)
    # Live duration, so an open visit matches on its elapsed stay.
    if min_duration_seconds is not None or max_duration_seconds is not None:
        params["now_naive"] = facility_now_naive()
    if min_duration_seconds is not None:
        clauses.append(f"({_duration_sql()}) >= :min_dur")
        params["min_dur"] = min_duration_seconds
    if max_duration_seconds is not None:
        clauses.append(f"({_duration_sql()}) <= :max_dur")
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
            {IS_EMPLOYEE_EXPR}  AS is_employee
        FROM parking_sessions ps
        {VEHICLE_JOIN}
        LEFT JOIN parking_slots pk ON pk.slot_id = ps.slot_id
        WHERE {where}
        ORDER BY {_entry_exit_order(sort_by, sort_dir, params)}
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
    status: Optional[ParkingSessionStatus] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    # Exit-axis sibling of date_from/date_to: filters on the day the car LEFT.
    # Drill-down for the Exits KPI (/entry-exit/kpis.total_exit).
    exit_date_from: Optional[date] = Query(None),
    exit_date_to: Optional[date] = Query(None),
    min_duration_seconds: Optional[int] = Query(None, ge=0),
    max_duration_seconds: Optional[int] = Query(None, ge=0),
    sort_by: Optional[EntryExitSort] = Query(None, description=_SORT_BY_DOC),
    sort_dir: SortDir = Query(SortDir.desc, description=_SORT_DIR_DOC),
    db: Session = Depends(get_db),
):
    schema = _floor_schema()
    ps_floor_id = "ps.floor_id" if schema["parking_sessions_floor_id"] else "NULL"
    clauses = ["1=1"]
    params: dict = {}
    if search:
        plate_clause = plate_search_clause("ps.plate_number", search, params)
        clauses.append(
            f"({plate_clause} OR {OWNER_NAME_EXPR} LIKE :search "
            f"OR {VEHICLE_TITLE_EXPR} LIKE :search)"
        )
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
    if date_from:
        clauses.append("CAST(ps.entry_time AS DATE) >= :date_from")
        params["date_from"] = str(date_from)
    if date_to:
        clauses.append("CAST(ps.entry_time AS DATE) <= :date_to")
        params["date_to"] = str(date_to)
    if exit_date_from:
        clauses.append("CAST(ps.exit_time AS DATE) >= :exit_date_from")
        params["exit_date_from"] = str(exit_date_from)
    if exit_date_to:
        clauses.append("CAST(ps.exit_time AS DATE) <= :exit_date_to")
        params["exit_date_to"] = str(exit_date_to)
    # Live duration, so an open visit matches on its elapsed stay.
    if min_duration_seconds is not None or max_duration_seconds is not None:
        params["now_naive"] = facility_now_naive()
    if min_duration_seconds is not None:
        clauses.append(f"({_duration_sql()}) >= :min_dur")
        params["min_dur"] = min_duration_seconds
    if max_duration_seconds is not None:
        clauses.append(f"({_duration_sql()}) <= :max_dur")
        params["max_dur"] = max_duration_seconds

    # Open sessions have no duration_seconds yet. Report elapsed-so-far instead of a
    # blank cell, matching the live-elapsed rule /entry-exit/kpis uses for
    # avg_stay_minutes. facility_now_naive() (not GETUTCDATE()) because the DB stores
    # facility-local naive timestamps — GETUTCDATE() goes negative when local is ahead.
    params["now_naive"] = facility_now_naive()

    data = rows(db, f"""
        SELECT
            ps.plate_number                                  AS [Plate Number],
            {OWNER_NAME_EXPR}                                AS [Owner],
            {VEHICLE_TYPE_EXPR}                              AS [Vehicle Type],
            {IS_EMPLOYEE_EXPR}                               AS [Employee],
            ps.status                                        AS [Status],
            ps.entry_time                                    AS [Entry Time],
            ps.exit_time                                     AS [Exit Time],
            ({_duration_sql()}) / 60                         AS [Duration (min)],
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
        ORDER BY {_entry_exit_order(sort_by, sort_dir, params)}
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
    # Exit-axis sibling of date_from/date_to: filters on the day the car LEFT.
    # Drill-down for the Exits KPI (/entry-exit/kpis.total_exit).
    exit_date_from: Optional[date] = Query(None),
    exit_date_to: Optional[date] = Query(None),
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
    if exit_date_from:
        clauses.append("CAST(ps.exit_time AS DATE) >= :exit_date_from")
        params["exit_date_from"] = str(exit_date_from)
    if exit_date_to:
        clauses.append("CAST(ps.exit_time AS DATE) <= :exit_date_to")
        params["exit_date_to"] = str(exit_date_to)
    # Live duration, so an open visit matches on its elapsed stay.
    if min_duration_seconds is not None or max_duration_seconds is not None:
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