"""End-of-day slot occupancy — one `dbo.slot_daily_occupancy` row per slot per
facility-local day (table: Damanat-DB-Migrator 0011).

The seconds come from `_occupied_seconds_sql`, the same time-weighted
slot_status query behind the live occupancy reports, run at hour grain over
one day. Reusing it rather than re-deriving it is the point: a stored day and a
live report over the same day must agree to the second.

The reporting window is `dbo.report_settings` at the moment a day is computed
(falling back to .env), and it is stored on the row. Changing the settings does
not rewrite computed days — `compute_range()` does that on request.

Days on which VA wrote no slot_status rows at all are skipped rather than
stored. The query carries each slot's last known state into the window, so
across a VA outage a slot last seen OCCUPIED would read 100% occupied for every
missing day.

Only completed days are computed — today is still changing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import facility_now_naive
from app.database import rows, scalar
from app.routers._helpers import _floor_schema
from app.routers.occupancy import _history_filter, _occupied_seconds_sql, _slot_type_excl
from app.services.report_settings import ReportWindow, get_report_window

log = logging.getLogger(__name__)

_DAY_SECONDS = 86400

_INSERT = text("""
    INSERT INTO dbo.slot_daily_occupancy (
        occupancy_date, slot_id, parking_slot_id, floor, floor_id,
        occupied_seconds_24h, occupancy_pct_24h,
        is_working_day, business_hours_applied, window_hour_from, window_hour_to,
        window_seconds, occupied_seconds_window, occupancy_pct, transition_count
    ) VALUES (
        :occupancy_date, :slot_id, :parking_slot_id, :floor, :floor_id,
        :occupied_seconds_24h, :occupancy_pct_24h,
        :is_working_day, :business_hours_applied, :window_hour_from, :window_hour_to,
        :window_seconds, :occupied_seconds_window, :occupancy_pct, :transition_count
    )
""")


@dataclass(frozen=True)
class DayResult:
    day: date
    status: Literal["written", "skipped_no_data"]
    slots: int = 0
    transitions: int = 0


def yesterday() -> date:
    """The most recent completed facility-local day."""
    return facility_now_naive().date() - timedelta(days=1)


def _pct(part: int, whole: int) -> Decimal:
    return (Decimal(part) * 100 / Decimal(whole)).quantize(Decimal("0.01"), ROUND_HALF_UP)


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


def compute_day(db: Session, day: date, window: Optional[ReportWindow] = None) -> DayResult:
    """Compute and store one day for every slot, replacing any rows it already
    has. Commits. Raises on a DB error — the caller decides whether to retry."""
    if day >= facility_now_naive().date():
        raise ValueError(f"{day} is not a completed day yet")
    window = window or get_report_window(db)
    start, end = _day_bounds(day)
    params = {"start": start, "end": end}

    transitions_by_slot = {
        r["slot_id"]: int(r["n"]) for r in rows(db, """
            SELECT slot_id, COUNT(*) AS n FROM slot_status
            WHERE time >= :start AND time < :end
            GROUP BY slot_id
        """, params)
    }
    if not transitions_by_slot:
        # Debug, not info: these days are re-checked on every run, and the job
        # reports the skipped count in its own summary line.
        log.debug("daily occupancy %s: no slot_status rows (VA down?) - skipped", day)
        return DayResult(day, "skipped_no_data")

    # Per-slot, per-hour occupied seconds for the day.
    floor_clause, q = _history_filter(db, start, end, "hour", None, None)
    hourly: dict[str, dict[int, int]] = {}
    for r in rows(db, _occupied_seconds_sql("hour", floor_clause, by_slot=True), q):
        hourly.setdefault(r["slot_id"], {})[r["bucket_start"].hour] = int(
            r["total_occupied_seconds"] or 0
        )

    if window.enabled:
        working = day.weekday() in window.weekdays
        h_from, h_to = window.hour_from, window.hour_to
        window_seconds = (h_to - h_from) * 3600 if working else 0
    else:
        working, h_from, h_to, window_seconds = True, None, None, _DAY_SECONDS

    records = []
    for slot in _slots(db):
        by_hour = hourly.get(slot["slot_id"], {})
        occupied_24h = sum(by_hour.values())
        if not working:
            occupied_window = 0
        elif h_from is None:
            occupied_window = occupied_24h
        else:
            occupied_window = sum(s for h, s in by_hour.items() if h_from <= h < h_to)
        records.append({
            "occupancy_date": day,
            "slot_id": slot["slot_id"],
            "parking_slot_id": slot["parking_slot_id"],
            "floor": slot["floor"],
            "floor_id": slot["floor_id"],
            "occupied_seconds_24h": occupied_24h,
            "occupancy_pct_24h": _pct(occupied_24h, _DAY_SECONDS),
            "is_working_day": 1 if working else 0,
            "business_hours_applied": 1 if window.enabled else 0,
            "window_hour_from": h_from,
            "window_hour_to": h_to,
            "window_seconds": window_seconds,
            "occupied_seconds_window": occupied_window,
            "occupancy_pct": _pct(occupied_window, window_seconds) if working else None,
            "transition_count": transitions_by_slot.get(slot["slot_id"], 0),
        })

    # Replace the whole day in one transaction, so it is never half-written.
    try:
        db.execute(text("DELETE FROM dbo.slot_daily_occupancy WHERE occupancy_date = :d"),
                   {"d": day})
        if records:
            db.execute(_INSERT, records)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return DayResult(day, "written", slots=len(records),
                     transitions=sum(transitions_by_slot.values()))


def compute_range(db: Session, first: date, last: date) -> list[DayResult]:
    """Recompute every day in [first, last] with the CURRENT settings,
    overwriting what is stored. One settings read for the whole range."""
    window = get_report_window(db)
    results = []
    day = first
    while day <= last:
        results.append(compute_day(db, day, window))
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
        r["occupancy_date"] for r in rows(db, """
            SELECT DISTINCT occupancy_date FROM dbo.slot_daily_occupancy
            WHERE occupancy_date BETWEEN :a AND :b
        """, {"a": first, "b": through})
    }
    days, day = [], first
    while day <= through:
        if day not in have:
            days.append(day)
        day += timedelta(days=1)
    return days


def backfill(db: Session, through: Optional[date] = None) -> list[DayResult]:
    """Compute every missing day. Existing days are left as they were computed."""
    window = get_report_window(db)
    return [compute_day(db, day, window) for day in missing_days(db, through)]
