"""Custom Reports -> Entry/Exit Report: the cards and the table.

A separate screen from the Entry/Exit page, with its own definitions: every
number is over the visits that match ALL the filters, so the cards follow the
table. GET /entry-exit/ and /entry-exit/kpis are not touched.
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import facility_now_naive, localize_naive
from app.database import get_db, rows
from app.schemas import EntryExitReportKPIs, EntryExitReportRow, PagedResponse
from app.schemas_enums import EntryExitReportSort, SortDir
from app.shared import build_paged, order_by_nulls_last, plate_display_sort_expr, plate_search_clause

from app.routers.prefix_injection import (get_prefix)
prefix = get_prefix() + "/entry-exit/reports"

router = APIRouter(prefix=prefix, tags=["Entry/Exit"])

# Stay length: live for a car still inside, else the stored duration when
# positive, else exit - entry. Non-positive stays read as no duration.
_STAY = """CASE
    WHEN ps.exit_time IS NULL THEN DATEDIFF(SECOND, ps.entry_time, :now)
    WHEN ps.duration_seconds > 0 THEN ps.duration_seconds
    ELSE DATEDIFF(SECOND, ps.entry_time, ps.exit_time) END"""
# Overstay = still inside at the first local midnight after entry, whether
# the car has left since or not. The same rule as the Overstays cards.
_IS_OVERSTAY = """CASE WHEN COALESCE(ps.exit_time, :now)
    > DATEADD(DAY, 1, CAST(CAST(ps.entry_time AS DATE) AS DATETIME2)) THEN 1 ELSE 0 END"""
# Location as displayed: "B1 - B10 CTO", or whichever half exists. A visit
# with a slot but no floor takes the slot's floor.
_FLOOR = "COALESCE(ps.floor, pk.floor)"
_SLOT = "COALESCE(pk.slot_name, ps.slot_number)"
_LOCATION = f"""CASE
    WHEN {_FLOOR} IS NOT NULL AND {_SLOT} IS NOT NULL THEN {_FLOOR} + ' - ' + {_SLOT}
    ELSE COALESCE({_FLOOR}, {_SLOT}) END"""

# Over the derived table `r` below. Only these fixed strings reach ORDER BY.
_SORT_BY = {
    EntryExitReportSort.time: "r.entry_time",
    EntryExitReportSort.plate: plate_display_sort_expr("NULLIF(r.plate_number, '')"),
    EntryExitReportSort.location: "r.location",
    EntryExitReportSort.duration: "r.duration_seconds",
}

_DATE_FROM_DOC = "First entry day (inclusive), facility-local. Omit both for all time."
_DATE_TO_DOC = "Last entry day (inclusive), facility-local."
_LOCATION_DOC = "A floor: ground | b1 | b2 (case-insensitive). Visits with no floor match no location."


def _visits_sql(date_from, date_to, search, location) -> tuple[str, dict]:
    """`(sql, params)`: one row per visit (parking_sessions row) matching the
    filters, with its display columns. Both endpoints read it, so the cards
    always describe exactly the table's rows."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must not be after date_to")
    clauses = ["1=1"]
    params: dict = {"now": facility_now_naive()}
    # A plain range on entry_time (stored facility-local) keeps the index usable.
    if date_from:
        clauses.append("ps.entry_time >= :start")
        params["start"] = datetime.combine(date_from, datetime.min.time())
    if date_to:
        clauses.append("ps.entry_time < :end")
        params["end"] = datetime.combine(date_to + timedelta(days=1), datetime.min.time())
    if search:
        clauses.append(plate_search_clause("ps.plate_number", search, params))
    if location:
        clauses.append(f"UPPER({_FLOOR}) = UPPER(:location)")
        params["location"] = location.strip()
    return f"""
        SELECT v.*, CASE WHEN v.stay_seconds > 0 THEN v.stay_seconds END AS duration_seconds
        FROM (
            SELECT ps.id, ps.plate_number, ps.entry_time, ps.exit_time, {_FLOOR} AS floor,
                   {_SLOT} AS slot_name, {_LOCATION} AS location,
                   {_STAY} AS stay_seconds, {_IS_OVERSTAY} AS is_overstay
            FROM parking_sessions ps
            LEFT JOIN parking_slots pk ON pk.slot_id = ps.slot_id
            WHERE {" AND ".join(clauses)}
        ) v
    """, params


@router.get("/activity/kpis", response_model=EntryExitReportKPIs)
async def entry_exit_report_kpis(
    date_from: Optional[date] = Query(None, description=_DATE_FROM_DOC),
    date_to: Optional[date] = Query(None, description=_DATE_TO_DOC),
    search: Optional[str] = Query(None, description="Plate contains (either digit/letter order)."),
    location: Optional[str] = Query(None, description=_LOCATION_DOC),
    db: Session = Depends(get_db),
):
    """Entry/Exit Report cards, over every visit matching the filters (all
    of them, not the current page).

    - `total_entries`: matching visits = `total_count` of the table.
    - `total_exits`: those that have an exit. Counted on the ENTRY day, unlike
      /entry-exit/kpis, so `net_vehicles` = entries - exits holds.
    - `net_vehicles`: entries - exits = matching visits with no exit yet.
    - `avg_stay_minutes`: mean stay of visits with a positive stay, in whole
      minutes; a car still inside counts up to now.
    - `overstays`: visits still inside at a local midnight after entry, left
      since or not (one per visit)."""
    sql, params = _visits_sql(date_from, date_to, search, location)
    k = rows(db, f"""
        SELECT COUNT(*) AS total_entries,
               SUM(CASE WHEN r.exit_time IS NOT NULL THEN 1 ELSE 0 END) AS total_exits,
               AVG(CAST(r.duration_seconds AS FLOAT)) AS avg_stay_seconds,
               SUM(r.is_overstay) AS overstays
        FROM ({sql}) r
    """, params)[0]
    entries, exits = k["total_entries"] or 0, k["total_exits"] or 0
    return EntryExitReportKPIs(
        date_from=date_from,
        date_to=date_to,
        total_entries=entries,
        total_exits=exits,
        net_vehicles=entries - exits,
        avg_stay_minutes=round((k["avg_stay_seconds"] or 0) / 60),
        overstays=k["overstays"] or 0,
    )


@router.get("/activity", response_model=PagedResponse[EntryExitReportRow])
async def entry_exit_report_list(
    date_from: Optional[date] = Query(None, description=_DATE_FROM_DOC),
    date_to: Optional[date] = Query(None, description=_DATE_TO_DOC),
    search: Optional[str] = Query(None, description="Plate contains (either digit/letter order)."),
    location: Optional[str] = Query(None, description=_LOCATION_DOC),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100, description="The screen sends 5, 10, 25 or 50."),
    sort_by: Optional[EntryExitReportSort] = Query(
        None, description="time (entry) | plate (as displayed, digits first) | location | duration. "
                          "Applied before paging; empty values sort last. Omit for newest entry first."),
    sort_dir: SortDir = Query(SortDir.desc, description="asc | desc (default). Only with sort_by."),
    db: Session = Depends(get_db),
):
    """Entry/Exit Report table: one row per visit matching the filters.

    `type` is exit once the car has left, else entry. `status` is overstay
    when `is_overstay` (even after the car left), else completed when it has
    an exit, else parking. Type and status are independent."""
    sql, params = _visits_sql(date_from, date_to, search, location)
    params.update(offset=(page - 1) * page_size, page_size=page_size)
    if sort_by is None:
        order = "r.entry_time DESC, r.id DESC"
    else:
        order = order_by_nulls_last(_SORT_BY[sort_by], sort_dir.value.upper(), "r.id")
    found = rows(db, f"""
        SELECT r.*, COUNT(*) OVER () AS total_count
        FROM ({sql}) r
        ORDER BY {order}
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)
    total = found[0]["total_count"] if found else _count(db, sql, params)

    items = []
    for r in found:
        exited = r["exit_time"] is not None
        overstay = bool(r["is_overstay"])
        items.append(EntryExitReportRow(
            id=r["id"],
            plate_number=r["plate_number"],
            entry={"event_time": localize_naive(r["entry_time"])},
            exit={"event_time": localize_naive(r["exit_time"])} if exited else None,
            type="exit" if exited else "entry",
            floor=r["floor"],
            slot_name=r["slot_name"],
            location=r["location"],
            duration_seconds=r["duration_seconds"],
            is_overstay=overstay,
            status="overstay" if overstay else ("completed" if exited else "parking"),
        ))
    return build_paged(items, total, page, page_size)


def _count(db: Session, sql: str, params: dict) -> int:
    """total_count when the page came back empty (a page past the end)."""
    return rows(db, f"SELECT COUNT(*) AS n FROM ({sql}) r", params)[0]["n"] or 0
