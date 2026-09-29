import asyncio
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional
 
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
 
from app.config import localize_naive
from app.database import get_db, rows, scalar
from app.routers._helpers import _floor_schema, resolve_floor_id
from app.services.snapshots import resolve_snapshot_url
from app.schemas import (
    AlertDetail,
    AlertItem,
    AlertPriorityCount,
    AlertsByPriority,
    AlertStats,
    AlertStatsCounts,
    AlertSummary,
    AlertTypeCount,
    CameraRef,
    EntityActionResponse,
    PagedResponse,
    SlotRef,
    SuccessResponse,
    VehicleRef,
)
from app.schemas_enums import (
    LEGACY_SEVERITY, AlertSeverity, AlertSort, AlertSortBy, AlertType, ResolvedFilter, SortDir,
)
from app.services.auth import require_internal_token
from app.services.upstream import iter_system1_alert_events, iter_system2_alert_events
from app.services.bus import alerts_bus
from app.shared import build_paged, order_by_nulls_last, plate_display_sort_expr, stream_csv

from app.routers.prefix_injection import (get_prefix)
 
def _fix_ts(dt, alert_type: str = ""):
    """Attach facility-local tz to a naive DB timestamp for serialisation."""
    return localize_naive(dt)

prefix = get_prefix() + "/alerts"

router = APIRouter(prefix=prefix, tags=["Alerts"])
 
 
@lru_cache(maxsize=None)
def _alerts_extra_cols() -> dict:
    """Cached probe of which optional columns exist on dbo.alerts. Drives
    the conditional SELECT bits below — missing columns become `NULL AS col`
    so the response shape stays stable.

    The audit columns (vehicle_id, vehicle_event_id, triggering_camera_event_id,
    resolved_by, resolution_notes) only appear after the Phase 4A migration
    has run; the original columns (severity, location_display, slot_id) come
    from the older fix_system1_schema.sql."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        def exists(col: str) -> bool:
            n = db.execute(text("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'alerts' AND COLUMN_NAME = :c
            """), {"c": col}).scalar()
            return (n or 0) > 0

        return {
            # Phase 1 columns
            "severity":         exists("severity"),
            "location_display": exists("location_display"),
            "slot_id":          exists("slot_id"),
            # Phase 4A audit columns
            "vehicle_id":                  exists("vehicle_id"),
            "vehicle_event_id":            exists("vehicle_event_id"),
            "triggering_camera_event_id":  exists("triggering_camera_event_id"),
            "resolved_by":                 exists("resolved_by"),
            "resolution_notes":            exists("resolution_notes"),
            # Always present in current schema but probed for completeness
            "event_type":                  exists("event_type"),
            # dbo.alert_types (migrator 0010): each type's configured severity,
            # which old-scale values are read as (see _alert_query_bits).
            "alert_types_table": bool(db.execute(text(
                "SELECT CASE WHEN OBJECT_ID(N'dbo.alert_types', N'U') IS NULL THEN 0 ELSE 1 END"
            )).scalar()),
        }
    finally:
        db.close()
 

# Python mirror of the severity CASE in `_alert_query_bits` below, for the
# pre-migration DB where `alerts.severity` doesn't exist AND the type has zero
# rows — SQL can't report a severity for a bucket it returned no rows for, but
# the summary card still needs one to colour the (empty) legend entry.
_CRITICAL_TYPES = frozenset({
    "violence", "intrusion", "vehicle_intrusion", "vehicle_violation",
    "named_slot_violation", "special_needs_violation",
})
_WARNING_TYPES = frozenset({"unknown_vehicle", "overstay", "capacity_exceeded"})


def _static_severity(alert_type: str) -> str:
    if alert_type in _CRITICAL_TYPES:
        return "critical"
    if alert_type in _WARNING_TYPES:
        return "warning"
    return "info"


def _humanize_type(alert_type: str) -> str:
    """'unknown_vehicle' -> 'Unknown Vehicle': the label for a type that
    dbo.alert_types does not name."""
    return alert_type.replace("_", " ").strip().title() or "Unknown"


def _alert_type_settings(db: Session) -> Optional[list[dict]]:
    """The rows of dbo.alert_types (display name + configured severity), in
    display order. None when the table is absent (migrator 0010 not run) —
    callers then keep their built-in type list."""
    try:
        return rows(db, """
            SELECT alert_type, display_name, severity
            FROM dbo.alert_types
            ORDER BY display_name
        """)
    except Exception:  # noqa: BLE001 — an add-on must not break the alerts page
        db.rollback()
        return None


def _stored_severity_expr(cols: dict) -> str:
    """The 4-level severity of a row with a real `alerts.severity` column.

    A value on the 4-level scale (high / medium / low) is the level. PMS-AI and
    VideoAnalytics still WRITE the old scale (critical / warning / info), so
    those — and NULL — are read as the type's configured severity in
    dbo.alert_types, which is what migrator 0013 did to the rows that existed
    then. 'critical' is on both scales, and every service still writes the old
    one, so it is translated too. A type with no configured severity, or a DB
    without dbo.alert_types, falls back to warning -> medium, info -> low
    (LEGACY_SEVERITY); anything else stays as stored.

    One expression for the badge, the `?severity=` filter, the cards, the
    donut, the sort and the CSV, so they cannot disagree. It is a scalar
    subquery on the alert_types primary key, so a query that GROUPs or
    aggregates on it must do so over a derived table (SQL Server rejects a
    subquery in GROUP BY or inside MIN())."""
    fallback = ("CASE a.severity WHEN 'warning' THEN 'medium' WHEN 'info' THEN 'low' "
                "WHEN 'critical' THEN 'critical' ELSE COALESCE(a.severity, 'critical') END")
    if not cols.get("alert_types_table"):
        return f"({fallback})"
    return ("(CASE WHEN a.severity IN ('high', 'medium', 'low') THEN a.severity "
            "ELSE COALESCE((SELECT ats.severity FROM dbo.alert_types ats "
            f"WHERE ats.alert_type = a.alert_type), {fallback}) END)")


def _alert_query_bits(cols: dict) -> dict[str, str]:
    """
    Build SQL expression fragments based on which columns exist in the alerts table.
    parking_slots is always joined to get the real human-readable slot_name.
    """
    if cols["slot_id"]:
        # alerts has its own slot_id foreign key → join parking_slots directly
        slot_join = """
            LEFT JOIN parking_slots pk ON pk.slot_id = a.slot_id
        """
        slot_id_expr   = "a.slot_id"
        slot_name_expr = "COALESCE(pk.slot_name, a.slot_number, a.slot_id)"
        zone_id_expr   = "a.zone_id"
        zone_name_expr = "a.zone_name"
    else:
        # pre-migration: zone_id on alerts is the closest thing to a slot reference
        slot_join = """
            LEFT JOIN parking_slots pk ON pk.slot_id = a.zone_id
        """
        slot_id_expr   = "a.zone_id"
        slot_name_expr = "COALESCE(pk.slot_name, a.slot_number, a.zone_id)"
        zone_id_expr   = "a.zone_id"
        zone_name_expr = "a.zone_name"
 
    severity_expr = (
        _stored_severity_expr(cols)
        if cols["severity"]
        else (
            "CASE "
            # `named_slot_violation` was renamed to `vehicle_intrusion` (canonical)
            # but legacy rows survive until the migration in
            # sql/migrate_named_slot_violation_to_vehicle_intrusion.sql runs.
            # Keep the legacy name in the critical bucket so historical rows
            # render with the correct severity in the meantime.
            "WHEN a.alert_type IN ('violence','intrusion','vehicle_intrusion','vehicle_violation','named_slot_violation','special_needs_violation') THEN 'critical' "
            "WHEN a.alert_type IN ('unknown_vehicle','overstay','capacity_exceeded') THEN 'warning' "
            "ELSE 'info' END"
        )
    )
 
    location_expr = (
        "a.location_display"
        if cols["location_display"]
        else (
            f"CASE "
            f"WHEN {slot_name_expr} IS NOT NULL THEN {slot_name_expr} "
            f"WHEN {zone_name_expr} IS NOT NULL THEN {zone_name_expr} "
            f"ELSE a.camera_id END"
        )
    )
 
    return {
        "slot_join":       slot_join,
        "slot_id_expr":    slot_id_expr,
        "slot_name_expr":  slot_name_expr,
        "zone_id_expr":    zone_id_expr,
        "zone_name_expr":  zone_name_expr,
        "severity_expr":   severity_expr,
        "location_expr":   location_expr,
    }
 
 
def _where(search, severity, alert_type, resolved, date_from, date_to, cols, floor_id=None, floor=None):
    bits = _alert_query_bits(cols)
    schema = _floor_schema()
    clauses = ["a.is_test = 0"]
    params: dict = {}

    if search:
        clauses.append(
            "("
            "a.plate_number LIKE :search OR "
            f"{bits['slot_id_expr']} LIKE :search OR "
            f"{bits['slot_name_expr']} LIKE :search OR "
            f"{bits['zone_name_expr']} LIKE :search OR "
            "a.description LIKE :search"
            ")"
        )
        params["search"] = f"%{search}%"

    if severity:
        # The 4-level scale; old-scale values filter as their new level.
        level = getattr(severity, "value", severity)
        level = LEGACY_SEVERITY.get(level, level)
        if cols["severity"]:
            # The same expression the rows display: an old-scale value that
            # reads as `level` must match too (see _stored_severity_expr).
            clauses.append(f"{bits['severity_expr']} = :severity")
            params["severity"] = level
        else:
            # No severity column: severity is derived from alert_type in three
            # buckets (see _alert_query_bits) — critical, warning (= medium)
            # and info (= low). Nothing derives to high.
            if level == "critical":
                # `named_slot_violation` is the legacy name for `vehicle_intrusion`
                # (still present on historical rows until migration runs); both map
                # to critical.
                clauses.append("a.alert_type IN ('violence','intrusion','vehicle_intrusion','vehicle_violation','named_slot_violation','special_needs_violation')")
            elif level == "medium":
                clauses.append("a.alert_type IN ('unknown_vehicle','overstay','capacity_exceeded')")
            elif level == "low":
                clauses.append("a.alert_type NOT IN ('violence','intrusion','vehicle_intrusion','vehicle_violation','named_slot_violation','special_needs_violation','unknown_vehicle','overstay','capacity_exceeded')")
            else:
                clauses.append("1 = 0")

    if alert_type:
        clauses.append("a.alert_type = :alert_type")
        params["alert_type"] = alert_type

    if resolved is not None:
        clauses.append("a.is_resolved = :resolved")
        params["resolved"] = 1 if resolved else 0

    # Whole days, both ends inclusive. Compared as a plain range rather than
    # CAST(triggered_at AS DATE), so SQL Server can use the triggered_at index
    # instead of converting every row.
    if date_from:
        clauses.append("a.triggered_at >= :date_from")
        params["date_from"] = datetime.combine(date_from, datetime.min.time())

    if date_to:
        clauses.append("a.triggered_at < :date_to_next")
        params["date_to_next"] = datetime.combine(date_to + timedelta(days=1), datetime.min.time())

    # WS-8: build IN-list from columns that actually exist in this DB.
    # Older deployments don't have `cameras.watches_floor`.
    floor_targets = ["pk.floor"]
    if schema["cameras_watches_floor"]:
        floor_targets.append("c.watches_floor")
    floor_in_list = ", ".join(floor_targets)

    if floor_id is not None and schema["floors_table"]:
        # WS-8: filter by floor name resolved from id; matches the COALESCE on floor used in SELECT.
        clauses.append(
            "(SELECT name FROM floors WHERE id = :floor_id) "
            f"IN ({floor_in_list})"
        )
        params["floor_id"] = floor_id
    elif floor:
        # Pre-migration fallback (or legacy callers): match the legacy string `floor`
        # against the available floor columns.
        clauses.append(f":floor IN ({floor_in_list})")
        params["floor"] = floor

    return " AND ".join(clauses), params
 
 

def _normalize_stream_event(source_system: str, payload: dict) -> dict:
    """Translate an upstream SSE payload (PMS-AI, VideoAnalytics, or
    in-process test bus) into the canonical `AlertStreamEventLite` shape.

    Field renames applied:
      - upstream `alert_id` → wire `id`
      - upstream `snapshot_path` → wire `snapshot_url`
      - upstream `timestamp` → wire `triggered_at`  (G-2 fix; keeps SSE
        events using the same field vocabulary as the REST list/detail views)
    """
    slot_name = payload.get("slot_name")
    if not slot_name and payload.get("slot_number"):
        slot_name = str(payload["slot_number"])

    ts_raw = payload.get("triggered_at") or payload.get("timestamp")

    return {
        "id":            payload.get("id") or payload.get("alert_id"),
        "source_system": source_system,
        "alert_type":    payload.get("alert_type"),
        "severity":      payload.get("severity", "info"),
        "slot_id":       payload.get("slot_id"),
        "slot_name":     slot_name,
        "zone_id":       payload.get("zone_id"),
        "plate_number":  payload.get("plate_number"),
        "camera_id":     payload.get("camera_id"),
        "floor":         payload.get("floor"),
        # WS-8: floor_id on the SSE wire — populated when upstream supplies it; None otherwise.
        "floor_id":      payload.get("floor_id"),
        "snapshot_url":  resolve_snapshot_url(payload.get("snapshot_url") or payload.get("snapshot_path")),
        "triggered_at":  ts_raw,
        "is_alert":      payload.get("is_alert", True),
    }
 
 
async def _pump(source_system: str, iterator, queue: asyncio.Queue):
    try:
        async for event in iterator:
            await queue.put((source_system, event))
        await queue.put((source_system, None))
    except asyncio.CancelledError:
        raise
    finally:
        aclose = getattr(iterator, "aclose", None)
        if aclose:
            await aclose()
 
 
PRIORITY_LEVELS = ("critical", "high", "medium", "low")

# GET /alerts/ ordering. id breaks ties so paging is stable; unresolved rows
# (NULL resolved_at) sort after every resolved one.
_ORDER_BY = {
    AlertSort.triggered_at: "a.triggered_at DESC, a.id DESC",
    AlertSort.resolved_at: "CASE WHEN a.resolved_at IS NULL THEN 1 ELSE 0 END, "
                           "a.resolved_at DESC, a.id DESC",
}


# `sort_by` keys, over the columns of alert_items_sql() — the values the table
# renders — read from a derived table `t`, because SQL Server does not allow a
# SELECT alias inside an ORDER BY expression. Only these fixed strings ever
# reach ORDER BY.
_SORT_BY = {
    AlertSortBy.triggered_at: "t.triggered_at",
    AlertSortBy.resolved_at: "t.resolved_at",
    AlertSortBy.type: "t.alert_type",
    AlertSortBy.plate: plate_display_sort_expr("NULLIF(t.plate_number, '')"),
    # The Location column shows the floor, with slot / camera beneath it.
    AlertSortBy.location: "COALESCE(t.floor, t.location)",
    # Rank, so desc = most severe first. Legacy warning/info rank as medium/low.
    AlertSortBy.severity: "CASE t.severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 "
                          "WHEN 'medium' THEN 2 WHEN 'warning' THEN 2 "
                          "WHEN 'low' THEN 1 WHEN 'info' THEN 1 END",
    AlertSortBy.status: "CASE WHEN t.is_resolved = 1 THEN 1 ELSE 0 END",
}

_SORT_BY_DOC = ("Column to sort by, applied before paging; overrides `sort`: triggered_at "
                "| resolved_at | type | plate (as displayed, digits first) | location "
                "(floor, else location) | severity (desc = critical first) | status "
                "(asc = active first). Empty values sort last either way.")
_SORT_DIR_DOC = "asc | desc (default). Only with sort_by."


def _sorted_items_sql(select_from: str, where: str, sort_by: AlertSortBy, sort_dir: SortDir) -> str:
    """alert_items_sql() rows matching `where`, ordered by `sort_by`; the
    caller appends OFFSET/FETCH when paging. t.id breaks ties so paging is
    stable."""
    return f"""
        SELECT t.* FROM (
            {select_from}
            WHERE {where}
        ) t
        ORDER BY {order_by_nulls_last(_SORT_BY[sort_by], sort_dir.value.upper(), "t.id")}
    """


@dataclass
class _RangeCounts:
    total: int = 0
    active: int = 0
    critical_active: int = 0
    per_level: dict = field(default_factory=lambda: dict.fromkeys(PRIORITY_LEVELS, 0))


def _range_counts(db: Session, date_from: Optional[date], date_to: Optional[date]) -> _RangeCounts:
    """Alerts TRIGGERED in [date_from, date_to] (all time without dates),
    resolved since or not, counted by priority and status in one query. The
    same rows `GET /alerts/?date_from=&date_to=` lists. Old-scale values
    (warning / info) count as medium / low. Shared by /stats and /by-priority
    so the cards and the donut cannot disagree."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must not be after date_to")
    cols = _alerts_extra_cols()
    bits = _alert_query_bits(cols)
    where, params = _where(None, None, None, None, date_from, date_to, cols)
    grouped = rows(db, f"""
        SELECT severity, resolved, COUNT(*) AS n
        FROM (
            SELECT {bits["severity_expr"]} AS severity, a.is_resolved AS resolved
            FROM alerts a
            WHERE {where}
        ) t
        GROUP BY severity, resolved
    """, params)

    c = _RangeCounts()
    for r in grouped:
        n = int(r["n"])
        level = LEGACY_SEVERITY.get(r["severity"], r["severity"])
        c.total += n
        if not r["resolved"]:
            c.active += n
            if level == "critical":
                c.critical_active += n
        if level in c.per_level:
            c.per_level[level] += n
    return c


_DATE_FROM = Query(None, description="First day (inclusive), facility-local. Omit both for all time.")
_DATE_TO = Query(None, description="Last day (inclusive), facility-local.")


@router.get("/stats", response_model=AlertStats)
async def alert_stats(
    date_from: Optional[date] = _DATE_FROM,
    date_to: Optional[date] = _DATE_TO,
    db: Session = Depends(get_db),
):
    """Alerts page KPI cards: Total, Critical, High, Resolved — for the alerts
    triggered in the range (all time without dates), resolved or not.

    `previous` holds the same cards for the equally long period right before
    the range (yesterday, for one day) so the frontend can draw the "vs"
    arrows; it needs both dates — all time has no previous period.

    `active_alerts` and `critical_violations` (still open) are kept for older
    callers."""
    c = _range_counts(db, date_from, date_to)
    prev = prev_from = prev_to = None
    if date_from and date_to:
        prev_to = date_from - timedelta(days=1)
        prev_from = prev_to - (date_to - date_from)
        p = _range_counts(db, prev_from, prev_to)
        prev = AlertStatsCounts(
            total_alerts=p.total,
            critical_alerts=p.per_level["critical"],
            high_alerts=p.per_level["high"],
            resolved_total=p.total - p.active,
            active_alerts=p.active,
        )
    return AlertStats(
        date_from=date_from,
        date_to=date_to,
        total_alerts=c.total,
        critical_alerts=c.per_level["critical"],
        high_alerts=c.per_level["high"],
        resolved_total=c.total - c.active,
        active_alerts=c.active,
        critical_violations=c.critical_active,
        previous=prev,
        previous_from=prev_from,
        previous_to=prev_to,
    )


@router.get("/by-priority", response_model=AlertsByPriority)
async def alerts_by_priority(
    date_from: Optional[date] = _DATE_FROM,
    date_to: Optional[date] = _DATE_TO,
    db: Session = Depends(get_db),
):
    """Alerts by Priority donut — the same alerts as /stats, split into the
    four levels. `items` always has all four, most urgent first, `count: 0`
    included; `pct` is each level's share of `total`, the centre number."""
    c = _range_counts(db, date_from, date_to)
    return AlertsByPriority(
        date_from=date_from,
        date_to=date_to,
        total=c.total,
        items=[
            AlertPriorityCount(
                severity=level, count=n,
                pct=round(n / c.total * 100, 1) if c.total else 0.0,
            )
            for level, n in c.per_level.items()
        ],
    )


@router.get("/summary", response_model=AlertSummary)
async def alert_summary(
    resolved: ResolvedFilter = Query(
        ResolvedFilter.false,
        description=(
            "`false` (default): active alerts only — the Dashboard's Alerts "
            "Summary, matching `/alerts/stats.active_alerts`. `true`: resolved "
            "only. `all`: every alert triggered in the range, resolved or not — "
            "the Alerts page's Alerts by Type, matching `/alerts/stats.total_alerts`."
        ),
    ),
    severity: Optional[AlertSeverity] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    floor: Optional[str] = Query(None),
    floor_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Per-alert_type counts for the Alerts Summary donut.

    Single GROUP BY rather than the N-round-trip alternative of calling
    GET /alerts/?alert_type=X&page_size=1 once per AlertType and reading
    `total_count`.

    Filters are the same builder the list endpoint uses (`_where`), so every
    slice is drill-down-exact: `?alert_type=<slice.alert_type>` plus the same
    filters returns precisely the rows counted here.

    Slice names and colours come from dbo.alert_types (the settings screen):
    `display_name` is the label to show, `severity` the configured level, so a
    rename or re-level there shows on the donut at once. Every type in that
    table is listed, `count: 0` included, so the legend keeps a stable order
    and colour assignment across refreshes; the card filters to `count > 0`
    before rendering. A type with rows but no settings entry (a legacy name
    such as `named_slot_violation`, or a new type) is appended with its stored
    severity and a label made from its name — never dropped. Merging legacy
    names into their successor would break the drill-down, since the list
    endpoint filters on the raw column.

    Without dbo.alert_types, the built-in type list and severity map are used
    as before."""
    cols = _alerts_extra_cols()
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=floor)
    resolved_flag = {ResolvedFilter.false: False, ResolvedFilter.true: True, ResolvedFilter.all: None}[resolved]
    where, params = _where(
        search, severity, None, resolved_flag, date_from, date_to, cols,
        floor_id=resolved_floor_id, floor=floor,
    )
    total, by_type = _summary_by_type(db, where, params, cols)
    return AlertSummary(total=total, by_type=by_type)


_RANKED_LEVELS = {1: "critical", 2: "high", 3: "medium", 4: "low"}


def _summary_by_type(db: Session, where: str, params: dict, cols: dict) -> tuple[int, list[AlertTypeCount]]:
    """`(total, by_type)` for the alerts matching `where` — the Alerts Summary
    donut. Shared by /summary and GET /alerts/reports/overstay-violations."""
    bits = _alert_query_bits(cols)
    schema = _floor_schema()

    # Same JOINs as the list endpoint's COUNT query — `_where` may reference
    # pk.floor / c.watches_floor, so they have to be in scope even when no
    # floor filter is active.
    floors_join = ""
    if schema["floors_table"]:
        floor_parts = ["pk.floor"]
        if schema["cameras_watches_floor"]:
            floor_parts.append("c.watches_floor")
        floor_expr = (
            f"COALESCE({', '.join(floor_parts)})"
            if len(floor_parts) > 1
            else floor_parts[0]
        )
        floors_join = f"LEFT JOIN floors f ON f.name = {floor_expr}"

    grouped = rows(db, f"""
        SELECT alert_type,
               MIN(CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                                 WHEN 'medium' THEN 3 WHEN 'warning' THEN 3
                                 WHEN 'low' THEN 4 WHEN 'info' THEN 4 END) AS severity_rank,
               COUNT(*) AS count
        FROM (
            SELECT a.alert_type, {bits["severity_expr"]} AS severity
            FROM alerts a
            {bits["slot_join"]}
            LEFT JOIN cameras c ON c.camera_id = a.camera_id
            {floors_join}
            WHERE {where}
        ) t
        GROUP BY alert_type
    """, params)

    # A type's rows can hold mixed levels (e.g. an operator re-levelled it);
    # the slice takes the most urgent one, by rank rather than alphabetically.
    # Only used without dbo.alert_types — with it, the configured level wins.
    counts = {
        (r.get("alert_type") or ""): (r.get("count") or 0, _RANKED_LEVELS.get(r.get("severity_rank")))
        for r in grouped
    }

    by_type: list[AlertTypeCount] = []
    configured = _alert_type_settings(db)
    if configured is not None:
        for t in configured:
            count, _ = counts.pop(t["alert_type"], (0, None))
            by_type.append(AlertTypeCount(
                alert_type=t["alert_type"],
                display_name=t["display_name"] or _humanize_type(t["alert_type"]),
                count=count,
                severity=t["severity"],
            ))
    else:
        for known in AlertType:
            count, sev = counts.pop(known.value, (0, None))
            by_type.append(AlertTypeCount(
                alert_type=known.value,
                display_name=_humanize_type(known.value),
                count=count,
                severity=sev or _static_severity(known.value),
            ))
    # Types with alerts but no entry above — appended rather than dropped, so
    # the card can't silently under-report.
    for atype, (count, sev) in counts.items():
        by_type.append(AlertTypeCount(
            alert_type=atype,
            display_name=_humanize_type(atype),
            count=count,
            severity=sev or _static_severity(atype),
        ))

    # Queried independently of the slices — see AlertSummary docstring.
    total = scalar(db, f"""
        SELECT COUNT(*) FROM alerts a
        {bits["slot_join"]}
        LEFT JOIN cameras c ON c.camera_id = a.camera_id
        {floors_join}
        WHERE {where}
    """, params) or 0

    return total, by_type


def alert_items_sql(cols: dict, schema: dict) -> tuple[str, str]:
    """`(select_from, floors_join)` for AlertItem rows: the caller appends
    WHERE / ORDER BY and passes each row through `alert_item_fixup`.
    `floors_join` is for a COUNT that must see the same floor columns.
    Shared by GET /alerts/ and GET /vehicles/history."""
    bits = _alert_query_bits(cols)
    # Audit columns are conditional on the Phase 4A migration. Emit NULL
    # placeholders when missing so the response shape stays stable for the
    # frontend regardless of DB version (G-6 fix). vehicle_id falls back to
    # v.id (joined from vehicles) when alerts.vehicle_id is null/missing.
    vehicle_id_col = (
        "COALESCE(a.vehicle_id, v.id) AS vehicle_id"
        if cols["vehicle_id"]
        else "v.id AS vehicle_id"
    )
    audit_cols = (
        (", a.vehicle_event_id"           if cols["vehicle_event_id"]           else ", NULL AS vehicle_event_id") +
        (", a.triggering_camera_event_id" if cols["triggering_camera_event_id"] else ", NULL AS triggering_camera_event_id") +
        (", a.resolved_by"                if cols["resolved_by"]                else ", NULL AS resolved_by") +
        (", a.resolution_notes"           if cols["resolution_notes"]           else ", NULL AS resolution_notes")
    )
    event_type_col = "a.event_type" if cols["event_type"] else "NULL AS event_type"

    # WS-8 schema-compat: build the floor expression from the columns that
    # actually exist. Older DBs predate `cameras.watches_floor`, so skip it
    # rather than 500 on `Invalid column name 'watches_floor'`.
    floor_parts = ["pk.floor"]
    if schema["cameras_watches_floor"]:
        floor_parts.append("c.watches_floor")
    floor_expr = (
        f"COALESCE({', '.join(floor_parts)})"
        if len(floor_parts) > 1
        else floor_parts[0]
    )

    # WS-8: floors LEFT JOIN is conditional on the floors table existing (Pattern B).
    if schema["floors_table"]:
        floors_join = f"LEFT JOIN floors f ON f.name = {floor_expr}"
        floor_id_select = "f.id                                AS floor_id"
    else:
        floors_join = ""
        floor_id_select = "NULL                                AS floor_id"

    select_from = f"""
        SELECT
            a.id,
            a.alert_type,
            {bits["severity_expr"]}  AS severity,
            {event_type_col},
            a.camera_id,
            a.plate_number,
            {vehicle_id_col},
            {bits["slot_id_expr"]}   AS slot_id,
            {bits["slot_name_expr"]} AS slot_name,
            a.zone_id,
            {floor_expr}             AS floor,
            {floor_id_select},
            {bits["location_expr"]}  AS location,
            a.description,
            a.snapshot_path          AS snapshot_url,
            a.is_resolved,
            a.resolved_at,
            a.triggered_at,
            v.owner_name,
            v.vehicle_type
            {audit_cols}
        FROM alerts a
        {bits["slot_join"]}
        -- G-6: populate vehicle_id / owner_name / vehicle_type
        LEFT JOIN vehicles v ON v.plate_number = a.plate_number
        -- G-6: fall through to camera's watched-floor when alerts/parking_slots have no floor
        LEFT JOIN cameras c ON c.camera_id = a.camera_id
        -- WS-8: integer floor_id alongside the legacy `floor` name string.
        {floors_join}
    """
    return select_from, floors_join


def alert_item_fixup(it: dict) -> dict:
    atype = it.get("alert_type", "")
    it["snapshot_url"] = resolve_snapshot_url(it.get("snapshot_url"))
    it["triggered_at"] = _fix_ts(it.get("triggered_at"), atype)
    it["resolved_at"]  = _fix_ts(it.get("resolved_at"),  atype)
    return it


@router.get("/", response_model=PagedResponse[AlertItem])
async def get_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    severity: Optional[AlertSeverity] = Query(None),
    alert_type: Optional[AlertType] = Query(None),
    resolved: Optional[bool] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    floor: Optional[str] = Query(None),
    floor_id: Optional[int] = Query(None),
    sort: AlertSort = Query(
        AlertSort.triggered_at,
        description="`triggered_at` (default): newest raised first. `resolved_at`: most "
                    "recently resolved first — for Recent Resolved Alerts, with resolved=true.",
    ),
    sort_by: Optional[AlertSortBy] = Query(None, description=_SORT_BY_DOC),
    sort_dir: SortDir = Query(SortDir.desc, description=_SORT_DIR_DOC),
    db: Session = Depends(get_db),
):
    cols = _alerts_extra_cols()
    bits = _alert_query_bits(cols)
    # WS-8 schema-compat shim — branch on each probe so SQL is tolerant of pre-migration DB.
    schema = _floor_schema()
    # WS-8: resolve either floor_id or floor name once; pass the integer to the WHERE builder.
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=floor)
    where, params = _where(
        search, severity, alert_type, resolved, date_from, date_to, cols,
        floor_id=resolved_floor_id, floor=floor,
    )
    params["offset"]    = (page - 1) * page_size
    params["page_size"] = page_size
 
    select_from, floors_join = alert_items_sql(cols, schema)

    # WS-8: total query needs the JOINs that the WHERE may reference (cameras/parking_slots).
    total = scalar(db, f"""
        SELECT COUNT(*) FROM alerts a
        {bits["slot_join"]}
        LEFT JOIN cameras c ON c.camera_id = a.camera_id
        {floors_join}
        WHERE {where}
    """, params)
    if sort_by is None:
        items_sql = f"""
            {select_from}
            WHERE {where}
            ORDER BY {_ORDER_BY[sort]}
        """
    else:
        items_sql = _sorted_items_sql(select_from, where, sort_by, sort_dir)
    items = rows(db, items_sql + " OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY", params)
    for it in items:
        alert_item_fixup(it)
    return build_paged(items, total or 0, page, page_size)
 
 
ALERT_TEMPLATES = [
    {"alert_type": "violence", "severity": "critical", "description": "Suspicious activity detected in Zone A"},
    {"alert_type": "intrusion", "severity": "critical", "description": "Unauthorized person in restricted area"},
    {"alert_type": "vehicle_intrusion", "severity": "critical", "description": "Unknown vehicle entered restricted zone"},
    {"alert_type": "vehicle_violation", "severity": "critical", "description": "Illegal parking maneuver detected"},
    {"alert_type": "unknown_vehicle", "severity": "warning", "description": "Unregistered plate detected: ABC-123", "plate_number": "ABC-123"},
    {"alert_type": "vehicle_intrusion", "severity": "critical", "description": "Visitor parked in CEO reserved slot", "slot_id": "CEO-01", "slot_name": "CEO Reserved"},
    {"alert_type": "special_needs_violation", "severity": "critical", "description": "Unauthorized vehicle in special needs slot"},
    {"alert_type": "overstay", "severity": "warning", "description": "Vehicle exceeded 24h limit", "plate_number": "XYZ-999"},
    {"alert_type": "capacity_exceeded", "severity": "info", "description": "Floor 1 is at 95% capacity", "floor": "1"},
]


@router.get("/stream")
async def stream_alerts(request: Request):
    async def event_stream():
        client_queue: asyncio.Queue = asyncio.Queue()
        bus_queue = alerts_bus.subscribe()
        
        async def _bus_pump():
            try:
                while True:
                    event = await bus_queue.get()
                    await client_queue.put(("test_system", event))
            except asyncio.CancelledError:
                pass
            finally:
                alerts_bus.unsubscribe(bus_queue)

        async def _heartbeat():
            try:
                while True:
                    await asyncio.sleep(15)
                    await client_queue.put(("gateway", "heartbeat"))
            except asyncio.CancelledError:
                pass

        tasks = [
            asyncio.create_task(_pump("pms_ai", iter_system1_alert_events(), client_queue)),
            asyncio.create_task(_pump("video_analytics", iter_system2_alert_events(), client_queue)),
            asyncio.create_task(_bus_pump()),
            asyncio.create_task(_heartbeat()),
        ]

        try:
            # connection_established frame — same shape as AlertStreamEventLite.
            yield "data: " + json.dumps({
                "id":            None,
                "source_system": "gateway",
                "alert_type":    "connection_established",
                "severity":      "info",
                "slot_id":       None,
                "slot_name":     None,
                "plate_number":  None,
                "camera_id":     None,
                "floor":         None,
                # WS-8: floor_id mirrors `floor: None` on the keep-alive frame.
                "floor_id":      None,
                "snapshot_url":  None,
                "triggered_at":  None,
                "is_alert":      False,
            }) + "\n\n"
 
            while True:
                if await request.is_disconnected():
                    break

                try:
                    source_system, payload = await asyncio.wait_for(client_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                if payload is None:
                    continue
                
                if payload == "heartbeat":
                    yield ": keep-alive\n\n"
                    continue

                normalized = _normalize_stream_event(source_system, payload)
                yield "data: " + json.dumps(normalized, default=str) + "\n\n"
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
 
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )

@router.get("/test/start", dependencies=[Depends(require_internal_token)])
async def start_continuous_test(interval: float = Query(1.0, ge=0.5, le=60.0)):
    """Start an infinite loop of random test alerts every {interval} seconds.
    Gated behind `X-Internal-Token` so anyone who finds /docs in production
    can't flood the dashboard."""
    alerts_bus.start_test_stream(ALERT_TEMPLATES, interval=interval)
    return {"status": "continuous_stream_started", "interval": interval}


@router.get("/test/stop", dependencies=[Depends(require_internal_token)])
async def stop_continuous_test():
    """Stop the infinite loop of random test alerts.
    Gated behind `X-Internal-Token` (see /test/start)."""
    alerts_bus.stop_test_stream()
    return {"status": "continuous_stream_stopped"}


@router.get("/{alert_id}", response_model=AlertDetail)
async def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """Single-alert detail view — AlertItem + fully-joined vehicle/slot/camera refs
    and related alerts (same plate or slot, within the last 7 days)."""
    cols = _alerts_extra_cols()
    bits = _alert_query_bits(cols)
    # WS-8 schema-compat shim — branch on each probe.
    schema = _floor_schema()

    # G-6: same join shape as the list query so vehicle/floor/camera fields populate.
    vehicle_event_id_col = (
        "a.vehicle_event_id" if cols["vehicle_event_id"] else "NULL AS vehicle_event_id"
    )
    triggering_camera_event_id_col = (
        "a.triggering_camera_event_id"
        if cols["triggering_camera_event_id"]
        else "NULL AS triggering_camera_event_id"
    )
    resolved_by_col = (
        "a.resolved_by" if cols["resolved_by"] else "NULL AS resolved_by"
    )
    resolution_notes_col = (
        "a.resolution_notes" if cols["resolution_notes"] else "NULL AS resolution_notes"
    )
    event_type_col = "a.event_type" if cols["event_type"] else "NULL AS event_type"
    vehicle_id_col = (
        "COALESCE(a.vehicle_id, v.id) AS vehicle_id"
        if cols["vehicle_id"]
        else "v.id AS vehicle_id"
    )

    # WS-8: build floor expression + floors join from columns that exist.
    # Older DBs predate `cameras.watches_floor`, so build the COALESCE
    # dynamically to avoid `Invalid column name`.
    floor_parts = ["pk.floor"]
    if schema["cameras_watches_floor"]:
        floor_parts.append("c.watches_floor")
    floor_expr = (
        f"COALESCE({', '.join(floor_parts)})"
        if len(floor_parts) > 1
        else floor_parts[0]
    )
    if schema["floors_table"]:
        floors_join = f"LEFT JOIN floors f ON f.name = {floor_expr}"
        floor_id_select = "f.id                                AS floor_id"
    else:
        floors_join = ""
        floor_id_select = "NULL                                AS floor_id"

    # WS-8: every `c.<col>` referenced from cameras is conditional on the
    # column actually existing. Older deployments are missing role,
    # watches_floor, watches_slots_json (Phase 4A additions).
    cam_area_col        = "c.area"               if schema["cameras_area"]               else "NULL"
    cam_floor_col       = "c.floor"              if schema["cameras_floor"]              else "NULL"
    cam_role_col        = "c.role"               if schema["cameras_role"]               else "NULL"
    cam_watches_floor_col = "c.watches_floor"    if schema["cameras_watches_floor"]      else "NULL"
    cam_watches_slots_col = "c.watches_slots_json" if schema["cameras_watches_slots_json"] else "NULL"
    alert_rows = rows(db, f"""
        SELECT
            a.id,
            a.alert_type,
            {bits["severity_expr"]}  AS severity,
            {event_type_col},
            a.plate_number,
            {bits["slot_id_expr"]}   AS slot_id,
            {bits["slot_name_expr"]} AS slot_name,
            a.zone_id,
            {floor_expr}             AS floor,
            {floor_id_select},
            {bits["location_expr"]}  AS location,
            a.camera_id,
            a.description,
            a.snapshot_path          AS snapshot_url,
            a.is_resolved,
            a.resolved_at,
            a.triggered_at,
            {vehicle_id_col},
            {vehicle_event_id_col},
            {triggering_camera_event_id_col},
            {resolved_by_col},
            {resolution_notes_col},
            v.owner_name,
            v.vehicle_type,
            v.employee_id,
            v.title,
            v.phone,
            v.email,
            v.is_employee,
            v.is_registered,
            v.registered_at,
            v.notes,
            c.id                     AS camera_pk,
            c.name                   AS camera_name,
            {cam_area_col}           AS camera_area,
            {cam_floor_col}          AS camera_floor,
            {cam_role_col}           AS camera_role,
            {cam_watches_floor_col}  AS camera_watches_floor,
            {cam_watches_slots_col}  AS camera_watches_slots_json
        FROM alerts a
        {bits["slot_join"]}
        -- G-6: join vehicles + cameras for vehicle/floor/camera fall-through
        LEFT JOIN vehicles v ON v.plate_number = a.plate_number
        LEFT JOIN cameras c ON c.camera_id = a.camera_id
        -- WS-8: integer floor_id alongside the COALESCE'd floor name.
        {floors_join}
        WHERE a.id = :id AND a.is_test = 0
    """, {"id": alert_id})

    if not alert_rows:
        raise HTTPException(404, "Alert not found")

    a = alert_rows[0]

    vehicle = None
    if a.get("vehicle_id"):
        vehicle = VehicleRef(
            id=a["vehicle_id"],
            plate_number=a["plate_number"],
            owner_name=a.get("owner_name"),
            vehicle_type=a.get("vehicle_type"),
            is_employee=a.get("is_employee"),
            employee_id=a.get("employee_id"),
            title=a.get("title"),
            phone=a.get("phone"),
            email=a.get("email"),
            is_registered=bool(a.get("is_registered")) if a.get("is_registered") is not None else False,
            registered_at=a.get("registered_at"),
            notes=a.get("notes"),
        )

    slot = None
    if a.get("slot_id"):
        # WS-8: surface integer id + floor_id from parking_slots so SlotRef carries them
        # (NULL fallback when columns missing — Pattern A).
        ps_id_col = "id" if schema["parking_slots_id"] else "NULL AS id"
        ps_floor_id_col = "floor_id" if schema["parking_slots_floor_id"] else "NULL AS floor_id"
        slot_rows = rows(db, f"""
            SELECT {ps_id_col}, slot_id, slot_name, floor, {ps_floor_id_col}, is_available, is_violation_zone, polygon
            FROM parking_slots WHERE slot_id = :sid
        """, {"sid": a["slot_id"]})
        if slot_rows:
            s = slot_rows[0]
            # parking_slots.polygon is stored as a JSON-encoded string (NVARCHAR);
            # SlotRef.polygon expects list[...] | None.  Parse defensively.
            raw_polygon = s.get("polygon")
            if isinstance(raw_polygon, str):
                try:
                    parsed_polygon = json.loads(raw_polygon)
                    if not isinstance(parsed_polygon, list):
                        parsed_polygon = None
                except (ValueError, TypeError):
                    parsed_polygon = None
            elif isinstance(raw_polygon, list):
                parsed_polygon = raw_polygon
            else:
                parsed_polygon = None
            slot = SlotRef(
                id=s.get("id"),
                slot_id=s["slot_id"],
                slot_name=s.get("slot_name"),
                floor=s.get("floor"),
                floor_id=s.get("floor_id"),
                is_available=bool(s.get("is_available")) if s.get("is_available") is not None else True,
                is_violation_slot=bool(s.get("is_violation_zone")) if s.get("is_violation_zone") is not None else False,
                polygon=parsed_polygon,
            )

    camera = None
    if a.get("camera_pk") and a.get("camera_id"):
        watches_slots = None
        raw_slots = a.get("camera_watches_slots_json")
        if raw_slots:
            try:
                parsed = json.loads(raw_slots)
                if isinstance(parsed, list):
                    watches_slots = [str(x) for x in parsed]
            except (TypeError, ValueError):
                watches_slots = None
        camera = CameraRef(
            id=a["camera_pk"],
            camera_id=a["camera_id"],
            name=a.get("camera_name"),
            area=a.get("camera_area"),
            floor=a.get("camera_floor"),
            role=a.get("camera_role") or "other",
            watches_floor=a.get("camera_watches_floor"),
            watches_slots=watches_slots,
        )

    # vehicle_event: only populated when alerts row carries a session FK
    vehicle_event = None
    ve_id = a.get("vehicle_event_id")
    if ve_id:
        from app.routers.entry_exit import _event_from_row
        ve_rows = rows(db, """
            SELECT TOP 1
                ps.id, ps.vehicle_id, ps.plate_number,
                ps.is_employee, ps.entry_time, ps.exit_time,
                ps.duration_seconds, ps.entry_camera_id, ps.exit_camera_id,
                ps.entry_snapshot_path, ps.exit_snapshot_path,
                ps.floor, ps.slot_id, ps.slot_number, ps.parked_at, ps.slot_left_at,
                ps.slot_camera_id, ps.slot_snapshot_path, ps.status,
                pk.slot_name AS slot_name,
                v.owner_name, v.vehicle_type
            FROM parking_sessions ps
            LEFT JOIN parking_slots pk ON pk.slot_id = ps.slot_id
            LEFT JOIN vehicles v ON v.plate_number = ps.plate_number
            WHERE ps.id = :ve_id
        """, {"ve_id": ve_id})
        if ve_rows:
            vehicle_event = _event_from_row(ve_rows[0], ve_rows[0].get("plate_number"))

    # Related alerts — same plate OR same slot, last 7 days, excluding this alert
    related = rows(db, f"""
        SELECT TOP 10
            a.id,
            a.alert_type,
            {bits["severity_expr"]} AS severity,
            a.plate_number,
            {bits["slot_id_expr"]}   AS slot_id,
            {bits["slot_name_expr"]} AS slot_name,
            a.description,
            a.triggered_at,
            a.is_resolved,
            a.resolved_at
        FROM alerts a
        {bits["slot_join"]}
        WHERE a.id != :id
          AND a.is_test = 0
          AND a.triggered_at >= DATEADD(DAY, -7, :triggered_at)
          AND (
              (a.plate_number IS NOT NULL AND a.plate_number = :plate)
              OR ({bits["slot_id_expr"]} IS NOT NULL AND {bits["slot_id_expr"]} = :slot)
          )
        ORDER BY a.triggered_at DESC, a.id DESC
    """, {"id": alert_id, "plate": a.get("plate_number"), "slot": a.get("slot_id"),
          "triggered_at": a["triggered_at"]})

    # Floor preference: explicit slot.floor → camera.watches_floor (G-6 fall-through)
    floor_value = (slot.floor if slot else None) or a.get("floor")

    return AlertDetail(
        id=a["id"],
        alert_type=a.get("alert_type"),
        severity=a.get("severity"),
        event_type=a.get("event_type"),
        camera_id=a.get("camera_id"),
        plate_number=a.get("plate_number"),
        vehicle_id=a.get("vehicle_id"),
        owner_name=a.get("owner_name"),
        vehicle_type=a.get("vehicle_type"),
        slot_id=a.get("slot_id"),
        slot_name=a.get("slot_name"),
        zone_id=a.get("zone_id"),
        floor=floor_value,
        # WS-8: integer floor_id from the floors LEFT JOIN, alongside the legacy `floor` name.
        floor_id=a.get("floor_id"),
        vehicle_event_id=a.get("vehicle_event_id"),
        triggering_camera_event_id=a.get("triggering_camera_event_id"),
        description=a.get("description"),
        location=a.get("location"),
        snapshot_url=resolve_snapshot_url(a.get("snapshot_url")),
        triggered_at=_fix_ts(a.get("triggered_at"), a.get("alert_type", "")),
        resolved_at=_fix_ts(a.get("resolved_at"),  a.get("alert_type", "")),
        is_resolved=a.get("is_resolved"),
        resolved_by=a.get("resolved_by"),
        resolution_notes=a.get("resolution_notes"),
        vehicle=vehicle,
        slot=slot,
        camera=camera,
        vehicle_event=vehicle_event,
        related_alerts=[AlertItem(**r) for r in related],
    )


@router.patch("/{alert_id}/resolve", response_model=EntityActionResponse)
async def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    result = db.execute(
        text("UPDATE alerts SET is_resolved=1, resolved_at=GETDATE() WHERE id=:id AND is_resolved=0"),
        {"id": alert_id},
    )
    db.commit()
    if result.rowcount == 0:
        # Tell the two cases apart: a second operator resolving the same alert
        # should hear "already done", not "does not exist".
        found = rows(db, "SELECT resolved_at FROM alerts WHERE id = :id", {"id": alert_id})
        if not found:
            raise HTTPException(404, "Alert not found")
        at = found[0]["resolved_at"]
        raise HTTPException(
            409,
            f"Alert was already resolved at {at:%Y-%m-%d %H:%M}" if at else "Alert was already resolved",
        )
    return EntityActionResponse(id=alert_id)


@router.delete("/{alert_id}", response_model=EntityActionResponse)
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    result = db.execute(text("DELETE FROM alerts WHERE id=:id"), {"id": alert_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Alert not found")
    return EntityActionResponse(id=alert_id)
 
 
def _unsorted_csv_rows(db: Session, bits: dict, where: str, params: dict) -> list[dict]:
    """The export's historical query and order: newest raised first."""
    return rows(db, f"""
        SELECT
            a.id                     AS [ID],
            a.plate_number           AS [Plate Number],
            v.owner_name             AS [Owner],
            a.alert_type             AS [Type],
            {bits["severity_expr"]}  AS [Severity],
            {bits["slot_id_expr"]}   AS [Slot ID],
            {bits["slot_name_expr"]} AS [Slot Name],
            {bits["location_expr"]}  AS [Location],
            a.camera_id              AS [Camera],
            a.description            AS [Description],
            a.snapshot_path          AS [Snapshot URL],
            a.triggered_at           AS [Triggered At],
            a.is_resolved            AS [Resolved],
            a.resolved_at            AS [Resolved At]
        FROM alerts a
        {bits["slot_join"]}
        LEFT JOIN vehicles v ON v.plate_number = a.plate_number
        WHERE {where}
        ORDER BY a.triggered_at DESC, a.id DESC
    """, params)


@router.get("/export/csv")
async def export_alerts_csv(
    search: Optional[str] = Query(None),
    severity: Optional[AlertSeverity] = Query(None),
    alert_type: Optional[AlertType] = Query(None),
    resolved: Optional[bool] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    sort_by: Optional[AlertSortBy] = Query(None, description=_SORT_BY_DOC),
    sort_dir: SortDir = Query(SortDir.desc, description=_SORT_DIR_DOC),
    db: Session = Depends(get_db),
):
    cols = _alerts_extra_cols()
    bits = _alert_query_bits(cols)
    where, params = _where(search, severity, alert_type, resolved, date_from, date_to, cols)
 
    if sort_by is not None:
        # Sorted export: the list's own rows and order, so the file matches the
        # table (including the floor a Location sort goes by).
        select_from, _ = alert_items_sql(cols, _floor_schema())
        data = [{
            "ID": r["id"], "Plate Number": r["plate_number"], "Owner": r["owner_name"],
            "Type": r["alert_type"], "Severity": r["severity"], "Slot ID": r["slot_id"],
            "Slot Name": r["slot_name"], "Location": r["location"], "Camera": r["camera_id"],
            "Description": r["description"], "Snapshot URL": r["snapshot_url"],
            "Triggered At": r["triggered_at"], "Resolved": r["is_resolved"],
            "Resolved At": r["resolved_at"],
        } for r in rows(db, _sorted_items_sql(select_from, where, sort_by, sort_dir), params)]
    else:
        data = _unsorted_csv_rows(db, bits, where, params)

    for row in data:
        row["Snapshot URL"] = resolve_snapshot_url(row.get("Snapshot URL"))
        atype = row.get("Type", "")
        row["Triggered At"] = _fix_ts(row.get("Triggered At"), atype)
        row["Resolved At"]  = _fix_ts(row.get("Resolved At"),  atype)
    headers = [
        "ID", "Plate Number", "Owner", "Type", "Severity",
        "Slot ID", "Slot Name", "Location", "Camera",
        "Description", "Snapshot URL", "Triggered At", "Resolved", "Resolved At",
    ]
    return stream_csv(data, headers, filename="alerts.csv")
