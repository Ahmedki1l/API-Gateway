"""Report pages whose numbers mix sources, so no single tab router owns them."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import facility_now_naive, localize_naive
from app.database import get_db, rows, scalar
from app.routers._helpers import _floor_schema, resolve_floor_id
from app.routers.alerts import (
    _alert_type_settings, _alerts_extra_cols, _humanize_type, _summary_by_type,
    _where as _alert_where, alert_items_sql,
)
from app.routers.entry_exit import overstay_sessions_sql
from app.schemas import OverstayViolationsKPIs, PagedResponse, ViolationRow
from app.schemas_enums import SortDir, ViolationSortBy, ViolationType
from app.services.snapshots import resolve_snapshot_url
from app.shared import (
    build_paged, order_by_nulls_last, plate_display_sort_expr, plate_search_clause,
)

from app.routers.prefix_injection import (get_prefix)
# Lives under /alerts: the report is an alerts view (plus derived overstays).
prefix = get_prefix() + "/alerts/reports"

router = APIRouter(prefix=prefix, tags=["Alerts"])

# The alert types that are violations, by the card they count under. Listed,
# not matched on '%violation%': vehicle_intrusion (a car in someone else's
# reserved slot) lost the word when 0009 renamed named_slot_violation to it.
# unknown_vehicle, capacity_exceeded, silent_entry and
# reserved_slot_unidentified are operational alerts, not violations.
NO_PARKING_TYPES = ("vehicle_violation",)
OTHER_TYPES = ("special_needs_violation", "vehicle_intrusion", "named_slot_violation")
VIOLATION_TYPES = NO_PARKING_TYPES + OTHER_TYPES

# Over the union `u` below. Only these fixed strings ever reach ORDER BY.
_SORT_BY = {
    ViolationSortBy.plate: plate_display_sort_expr("NULLIF(u.plate_number, '')"),
    ViolationSortBy.location: "u.location",
    ViolationSortBy.duration: "u.duration_seconds",
}

_DATE_FROM_DOC = "First day (inclusive), facility-local. Omit both for all time."
_DATE_TO_DOC = "Last day (inclusive), facility-local."
_SEARCH_DOC = "Alerts: plate / slot / zone / description. Overstays: plate."
_PLATE_DOC = ("Plate only, either order (7894-NJS or NJS-7894), dashes / spaces "
              "ignored; a partial plate matches as a substring. Combines with search.")
_ALERT_TYPE_DOC = ("The row's violation_type; repeat for several "
                   "(?alert_type=overstay&alert_type=vehicle_violation). "
                   "vehicle_intrusion also matches legacy named_slot_violation. Omit for all.")

# A selected type -> the alert_type values it matches. Overstays are not
# alerts: they come from parking_sessions, so they map to nothing here.
_TYPE_ALERTS = {
    ViolationType.vehicle_violation: ("vehicle_violation",),
    ViolationType.special_needs_violation: ("special_needs_violation",),
    ViolationType.vehicle_intrusion: ("vehicle_intrusion", "named_slot_violation"),
    ViolationType.overstay: (),
}


def _sources(db: Session, date_from, date_to, floor, floor_id, search,
             plate_number=None, alert_type=None):
    """`(cols, where, params, overstay_sql)`: the violation alerts (`where`
    over `alerts a`) and the overstay stays (`overstay_sql`) that both
    endpoints count, for the same filters — so the cards always add up to
    the table's total_count."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must not be after date_to")
    cols = _alerts_extra_cols()
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=floor)
    where, params = _alert_where(
        search, None, None, None, date_from, date_to, cols,
        floor_id=resolved_floor_id, floor=floor,
    )
    types = VIOLATION_TYPES
    if alert_type:
        types = tuple(t for sel in alert_type for t in _TYPE_ALERTS[sel])
    # `types` holds fixed strings from this module only, never caller input.
    where += (f" AND a.alert_type IN ({', '.join(repr(t) for t in types)})"
              if types else " AND 1 = 0")
    if plate_number:
        where += " AND " + plate_search_clause("a.plate_number", plate_number, params, prefix="vpn")
    overstay_sql, overstay_params = overstay_sessions_sql(
        date_from, date_to, floor=floor, floor_id=resolved_floor_id, search=search,
        plate=plate_number,
    )
    if alert_type and ViolationType.overstay not in alert_type:
        overstay_sql = f"SELECT ov.* FROM ({overstay_sql}) ov WHERE 1 = 0"
    # Both builders bind floor / floor_id to the same values; nothing else overlaps.
    params.update(overstay_params)
    return cols, where, params, overstay_sql


@router.get("/overstay-violations/kpis", response_model=OverstayViolationsKPIs)
async def overstay_violations_kpis(
    date_from: Optional[date] = Query(None, description=_DATE_FROM_DOC),
    date_to: Optional[date] = Query(None, description=_DATE_TO_DOC),
    floor: Optional[str] = Query(None),
    floor_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None, description=_SEARCH_DOC),
    plate_number: Optional[str] = Query(None, description=_PLATE_DOC),
    alert_type: Optional[list[ViolationType]] = Query(None, description=_ALERT_TYPE_DOC),
    db: Session = Depends(get_db),
):
    """Overstay & Violations report — the cards.

    - `overstays`: every stay that was inside the garage at a local midnight
      in the range, from parking_sessions — one per stay, so a car that
      stayed two separate nights counts twice. (The Entry/Exit Overstays card
      counts distinct cars, so it can be lower.)
    - `no_parking`: `vehicle_violation` alerts triggered in the range.
    - `other`: `special_needs_violation` + `vehicle_intrusion` (+ the legacy
      `named_slot_violation`) alerts triggered in the range.
    - Alerts count whether resolved since or not. Other alert types are not
      violations and are left out.
    - `total_violations` = the three above = `total_count` of
      GET /alerts/reports/overstay-violations with the same filters.
    """
    cols, where, params, overstay_sql = _sources(
        db, date_from, date_to, floor, floor_id, search, plate_number, alert_type)
    _, by_type = _summary_by_type(db, where, params, cols)
    by_type = [t for t in by_type if t.alert_type in VIOLATION_TYPES]
    no_parking = sum(t.count for t in by_type if t.alert_type in NO_PARKING_TYPES)
    other = sum(t.count for t in by_type if t.alert_type in OTHER_TYPES)
    overstays = scalar(db, f"SELECT COUNT(*) FROM ({overstay_sql}) o", params) or 0
    return OverstayViolationsKPIs(
        date_from=date_from,
        date_to=date_to,
        total_violations=overstays + no_parking + other,
        overstays=overstays,
        no_parking=no_parking,
        other=other,
        by_type=by_type,
    )


@router.get("/overstay-violations", response_model=PagedResponse[ViolationRow])
async def overstay_violations_list(
    date_from: Optional[date] = Query(None, description=_DATE_FROM_DOC),
    date_to: Optional[date] = Query(None, description=_DATE_TO_DOC),
    floor: Optional[str] = Query(None),
    floor_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None, description=_SEARCH_DOC),
    plate_number: Optional[str] = Query(None, description=_PLATE_DOC),
    alert_type: Optional[list[ViolationType]] = Query(None, description=_ALERT_TYPE_DOC),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    sort_by: Optional[ViolationSortBy] = Query(
        None, description="plate (as displayed, digits first) | location | duration. "
                          "Applied before paging; empty values sort last. Omit for newest first."),
    sort_dir: SortDir = Query(SortDir.desc, description="asc | desc (default). Only with sort_by."),
    db: Session = Depends(get_db),
):
    """Overstay & Violations report — the Violation Details table: the
    violations the /kpis cards count, one row each (a violation alert, or one
    overnight stay), paged and sorted together.

    `location` is the zone / slot the violation happened in (Violation-B1,
    G1, B10 CTO), else the floor, else the camera; `floor` is also returned
    on its own."""
    cols, where, params, overstay_sql = _sources(
        db, date_from, date_to, floor, floor_id, search, plate_number, alert_type)
    alert_select, _ = alert_items_sql(cols, _floor_schema())
    union = f"""
        SELECT 'alert' AS source, t.id, t.alert_type AS violation_type,
               t.plate_number, t.floor, t.slot_name,
               COALESCE(t.slot_name, t.location, t.floor, t.camera_id) AS location,
               CASE WHEN t.resolved_at >= t.triggered_at
                    THEN DATEDIFF(SECOND, t.triggered_at, t.resolved_at) END AS duration_seconds,
               t.triggered_at AS occurred_at, t.snapshot_url
        FROM (
            {alert_select}
            WHERE {where}
        ) t
        UNION ALL
        SELECT 'overstay', o.id, 'overstay',
               o.plate_number, o.floor, COALESCE(pk.slot_name, o.slot_number),
               COALESCE(pk.slot_name, o.slot_number, o.floor),
               DATEDIFF(SECOND, o.over_from, COALESCE(o.exit_time, :now)),
               o.over_from, COALESCE(o.slot_snapshot_path, o.entry_snapshot_path)
        FROM ({overstay_sql}) o
        LEFT JOIN parking_slots pk ON pk.slot_id = o.slot_id
    """
    params.update(now=facility_now_naive(), offset=(page - 1) * page_size, page_size=page_size)
    total = scalar(db, f"SELECT COUNT(*) FROM ({union}) u", params) or 0
    if sort_by is None:
        order = "u.occurred_at DESC, u.source DESC, u.id DESC"
    else:
        order = order_by_nulls_last(_SORT_BY[sort_by], sort_dir.value.upper(), "u.source", "u.id")
    items = rows(db, f"""
        SELECT u.* FROM ({union}) u
        ORDER BY {order}
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)

    names = {t["alert_type"]: t["display_name"] for t in (_alert_type_settings(db) or [])}
    for it in items:
        atype = it["violation_type"]
        if it["source"] == "overstay":
            it["category"], it["display_name"] = "overstay", "Overstay"
        else:
            it["category"] = "no_parking" if atype in NO_PARKING_TYPES else "other"
            it["display_name"] = names.get(atype) or _humanize_type(atype)
        it["occurred_at"] = localize_naive(it["occurred_at"])
        it["snapshot_url"] = resolve_snapshot_url(it["snapshot_url"])
    return build_paged(items, total, page, page_size)
