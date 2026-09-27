"""End-of-day slot occupancy — one `dbo.slot_hourly_occupancy` row per slot per
facility-local hour, written a whole completed day at a time (table:
Damanat-DB-Migrator 0012).

The seconds come from `_occupied_seconds_sql`, the same time-weighted
slot_status query behind the live occupancy reports, at the same hour grain.
Reusing it rather than re-deriving it is the point: the reports read these rows
for finished days instead of re-scanning slot_status, and must get the same
numbers they would have computed live.

Each row is stamped with the working hours of its day (is_working_hour,
working_hour_from/to), taken from the window log — the window in force on that
day, not today's, so a day stored late still gets its own. The stamp is never
updated afterwards: history keeps the window it was measured under. The
seconds are stored for every hour regardless, so the reports can still cut any
other window from the same rows.

All 24 hours of every slot are stored, zeros included, so a day is either
fully stored or absent — the reports rely on that to decide which days they
can read and which they must compute live.

Days on which VA wrote no slot_status rows at all are skipped rather than
stored. The query carries each slot's last known state into the window, so
across a VA outage a slot last seen OCCUPIED would read occupied for every
missing hour.

Only completed days are computed — today is still changing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import facility_now_naive
from app.database import rows, scalar
from app.routers._helpers import _floor_schema
from app.routers.occupancy import _history_filter, _occupied_seconds_sql, _slot_type_excl
from app.services.report_settings import WindowHistory, get_window_history

log = logging.getLogger(__name__)

_INSERT = text("""
    INSERT INTO dbo.slot_hourly_occupancy (
        occupancy_hour, slot_id, parking_slot_id, floor, floor_id,
        occupied_seconds, is_working_hour, working_hour_from, working_hour_to
    ) VALUES (
        :occupancy_hour, :slot_id, :parking_slot_id, :floor, :floor_id,
        :occupied_seconds, :is_working_hour, :working_hour_from, :working_hour_to
    )
""")


@dataclass(frozen=True)
class DayResult:
    day: date
    status: Literal["written", "skipped_no_data"]
    slots: int = 0


def yesterday() -> date:
    """The most recent completed facility-local day."""
    return facility_now_naive().date() - timedelta(days=1)


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min)
    return start, start + timedelta(days=1)


def _slots(db: Session) -> list[dict]:
    """Every real parking space — the same filter as the live reports: no
    violation zones, no special_zone/roi rows."""
    schema = _floor_schema()
    id_col = "pk.id" if schema.get("parking_slots_id") else "NULL"
    floor_id_col = "pk.floor_id" if schema.get("parking_slots_floor_id") else "NULL"
    return rows(db, f"""
        SELECT pk.slot_id, {id_col} AS parking_slot_id, pk.floor, {floor_id_col} AS floor_id
        FROM parking_slots pk
        WHERE pk.is_violation_zone = 0
          {_slot_type_excl('pk')}
        ORDER BY pk.slot_id
    """)


def compute_day(db: Session, day: date, history: Optional[WindowHistory] = None) -> DayResult:
    """Compute and store the 24 hours of one day for every slot, replacing any
    rows the day already has. Commits. Raises on a DB error — the caller
    decides whether to retry. `history` saves re-reading the window log when
    computing many days."""
    if day >= facility_now_naive().date():
        raise ValueError(f"{day} is not a completed day yet")
    start, end = _day_bounds(day)
    params = {"start": start, "end": end}

    if scalar(db, """
        SELECT TOP 1 1 FROM slot_status WHERE time >= :start AND time < :end
    """, params) is None:
        # Debug, not info: these days are re-checked on every run, and the job
        # reports the skipped count in its own summary line.
        log.debug("slot occupancy %s: no slot_status rows (VA down?) - skipped", day)
        return DayResult(day, "skipped_no_data")

    # slot_id -> {hour: occupied seconds}
    floor_clause, q = _history_filter(db, start, end, "hour", None, None)
    occupied: dict[str, dict[int, int]] = {}
    for r in rows(db, _occupied_seconds_sql("hour", floor_clause, by_slot=True), q):
        occupied.setdefault(r["slot_id"], {})[r["bucket_start"].hour] = int(
            r["total_occupied_seconds"] or 0
        )

    rule = (history or get_window_history(db)).rule_for(day)
    slots = _slots(db)
    records = [
        {
            "occupancy_hour": start + timedelta(hours=h),
            "slot_id": slot["slot_id"],
            "parking_slot_id": slot["parking_slot_id"],
            "floor": slot["floor"],
            "floor_id": slot["floor_id"],
            "occupied_seconds": occupied.get(slot["slot_id"], {}).get(h, 0),
            "is_working_hour": 1 if rule.counts(h) else 0,
            "working_hour_from": rule.hour_from,
            "working_hour_to": rule.hour_to,
        }
        for slot in slots
        for h in range(24)
    ]

    # Replace the whole day in one transaction, so it is never half-written.
    try:
        db.execute(text("""
            DELETE FROM dbo.slot_hourly_occupancy
            WHERE occupancy_hour >= :start AND occupancy_hour < :end
        """), params)
        if records:
            db.execute(_INSERT, records)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return DayResult(day, "written", slots=len(slots))


def compute_range(db: Session, first: date, last: date) -> list[DayResult]:
    """Recompute every day in [first, last], overwriting what is stored."""
    results = []
    history = get_window_history(db)
    day = first
    while day <= last:
        results.append(compute_day(db, day, history))
        day += timedelta(days=1)
    return results


def missing_days(db: Session, through: Optional[date] = None) -> list[date]:
    """Days from the first slot_status row up to `through` (default: yesterday)
    that have no stored rows. Days skipped for having no data stay "missing" and
    are re-checked each time — a single COUNT, so cheap — which also means a day
    whose data arrives late gets picked up."""
    through = through or yesterday()
    first = scalar(db, "SELECT CAST(MIN(time) AS DATE) FROM slot_status")
    if first is None or first > through:
        return []
    have = {
        r["d"] for r in rows(db, """
            SELECT DISTINCT CAST(occupancy_hour AS DATE) AS d
            FROM dbo.slot_hourly_occupancy
            WHERE occupancy_hour >= :a AND occupancy_hour < :b
        """, {"a": first, "b": through + timedelta(days=1)})
    }
    days, day = [], first
    while day <= through:
        if day not in have:
            days.append(day)
        day += timedelta(days=1)
    return days


def backfill(db: Session, through: Optional[date] = None) -> list[DayResult]:
    """Compute every missing day. Days already stored are left alone."""
    history = get_window_history(db)
    return [compute_day(db, day, history) for day in missing_days(db, through)]
