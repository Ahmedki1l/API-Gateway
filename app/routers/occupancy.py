from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Annotated, Optional
from io import StringIO
import csv

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, scalar, rows
from app.routers._helpers import (
    _floor_schema,
    resolve_floor_id,
    resolve_floor_name,
)
from app.schemas import (
    FloorOccupancy,
    FloorSlotGroup,
    History,
    OccupancyKPIs,
    OccupancyLocationItem,
    OccupancyLocationResponse,
    OccupancyReportKpis,
    OccupancyReportSummary,
    OccupancyTrendPoint,
    OccupancyTrendResponse,
    OccupancyTotals,
    PagedResponse,
    SlotDetail,
    SlotListItem,
    ZoneItem,
)
from app.schemas_enums import (
    FacilityNaiveDatetime,
    FloorSort,
    OccupancyTrendGrain,
    ReservationType,
    StrictQueryBool,
)
from app.services.snapshots import resolve_snapshot_url
from app.services.upstream import get_live_slots
from app.shared import build_paged


from app.routers.prefix_injection import (get_prefix)
prefix = get_prefix() + "/occupancy"


# Latest slot_status per slot_id — reused by /floors, /slots/{id}, etc.
_LATEST_STATUS_JOIN = """
    LEFT JOIN slot_status ss ON ss.slot_id = pk.slot_id
        AND ss.time = (SELECT MAX(time) FROM slot_status WHERE slot_id = pk.slot_id)
"""


def _is_occupied(status: Optional[str]) -> bool:
    """Slot-status semantics — VA's state machine emits VACANT/ENTERING/OCCUPIED/LEAVING,
    plus legacy 'empty'/'available'/'free'. Anything else counts as occupied."""
    if not status:
        return False
    s = status.upper()
    return s not in ("VACANT", "EMPTY", "AVAILABLE", "FREE")


def _slot_type_excl(alias: str = "") -> str:
    """SQL AND-fragment that excludes non-parking slot types (special_zone, roi).
    Returns empty string when the slot_type column doesn't exist yet — schema-compat
    shim so the gateway keeps working on pre-migration databases."""
    if not _floor_schema().get("parking_slots_slot_type"):
        return ""
    p = f"{alias}." if alias else ""
    return f"AND {p}slot_type NOT IN ('special_zone', 'roi')"


def _monitored_only(alias: str = "") -> str:
    """SQL AND-fragment restricting to monitored slots (`is_monitored = 1`).
    Empty string when the column doesn't exist yet — pre-migration DBs have no
    blind-spot rows, so the filter is a no-op."""
    if not _floor_schema().get("parking_slots_is_monitored"):
        return ""
    p = f"{alias}." if alias else ""
    return f"AND {p}is_monitored = 1"


def _monitored_col(alias: str = "") -> str:
    """SELECT expression for `is_monitored` with a pre-migration fallback of
    `1 AS is_monitored` (every existing slot is treated as monitored before
    the column ships)."""
    if not _floor_schema().get("parking_slots_is_monitored"):
        return "1 AS is_monitored"
    p = f"{alias}." if alias else ""
    return f"{p}is_monitored"


def _current_plate_col(slots_alias: str = "pk", status_alias: str = "ss") -> str:
    """SELECT expression for `current_plate`, the plate of the car parked in
    this slot right now.

    Source of truth is `parking_slots.current_plate`, written by the ALPR
    pipeline. `slot_status.plate_number` is VideoAnalytics' own column and
    carries `''` on every occupied slot — VA reports occupancy, not identity —
    so it is only used as a fallback on databases that predate the
    `parking_slots` ALPR columns.

    `NULLIF` on both branches keeps "no plate" as a single value (NULL) at the
    API boundary rather than leaking `''` to the frontend.
    """
    if _floor_schema().get("parking_slots_current_plate"):
        p = f"{slots_alias}." if slots_alias else ""
        return f"NULLIF({p}current_plate, '') AS current_plate"
    p = f"{status_alias}." if status_alias else ""
    return f"NULLIF({p}plate_number, '') AS current_plate"


# Alert types that represent a "violation against this specific slot". An
# unresolved alert of any of these types makes the slot's
# `has_active_violation` flip to true. Includes the slot-targeted violations
# from the AlertType enum; `intrusion` (general, area-level) is excluded.
_VIOLATION_ALERT_TYPES = (
    "'vehicle_violation', 'named_slot_violation', "
    "'special_needs_violation', 'vehicle_intrusion'"
)


def _active_violation_cols(alias: str = "pk") -> str:
    """SELECT expression producing three correlated columns:
      `active_violation_type` — alert_type of the most-recent unresolved,
         non-test violation alert on this slot (NULL when none).
      `active_violation_severity` — severity of the same alert (NULL when
         none). Reads `alerts.severity` when the column exists; falls back
         to the literal `'critical'` (the gateway's default for the four
         violation alert types — see `alerts.py:_alert_query_bits`).
      `has_active_violation` — 0/1 BIT mirroring the same EXISTS check.
         Kept as an FE convenience flag; the model_validator on SlotRef /
         SlotListItem re-derives it from `active_violation_type` so the
         two fields can never disagree at the API boundary.

    Used by every slot list/detail SELECT so the frontend can recolor slots
    with live violations, surface the type as a tooltip, and pick a colour
    intensity per severity."""
    # Late import to dodge a startup-time circular: occupancy is imported by
    # dashboard, which already imports alerts; the alerts module pulls in
    # SQLAlchemy types that would cycle if loaded eagerly here.
    from app.routers.alerts import _alerts_extra_cols
    p = f"{alias}." if alias else ""
    cols = _alerts_extra_cols()
    sev_expr = "a.severity" if cols["severity"] else "'critical'"
    return f"""(SELECT TOP 1 a.alert_type
        FROM alerts a
        WHERE a.slot_id = {p}slot_id
          AND a.is_resolved = 0
          AND a.is_test = 0
          AND a.alert_type IN ({_VIOLATION_ALERT_TYPES})
        ORDER BY a.triggered_at DESC
    ) AS active_violation_type,
    (SELECT TOP 1 {sev_expr}
        FROM alerts a
        WHERE a.slot_id = {p}slot_id
          AND a.is_resolved = 0
          AND a.is_test = 0
          AND a.alert_type IN ({_VIOLATION_ALERT_TYPES})
        ORDER BY a.triggered_at DESC
    ) AS active_violation_severity,
    CASE WHEN EXISTS (
        SELECT 1 FROM alerts a
        WHERE a.slot_id = {p}slot_id
          AND a.is_resolved = 0
          AND a.is_test = 0
          AND a.alert_type IN ({_VIOLATION_ALERT_TYPES})
    ) THEN 1 ELSE 0 END AS has_active_violation"""



router = APIRouter(prefix=prefix, tags=["Occupancy"])

# zone_occupancy real columns:
#   id, zone_id, camera_id, current_count, max_capacity,
#   last_updated, zone_name, floor
#
# parking_slots real columns:
#   slot_id, slot_name, floor, polygon, is_available, is_violation_zone,
#   slot_type, reservation_type, reserved_for
#   + WS-8 additions: id (INT PK), floor_id (FK → floors)
#
# slot_status real columns:
#   id, slot_id, plate_number, status, time


@router.get("/kpis", response_model=OccupancyKPIs)
async def occupancy_kpis(db: Session = Depends(get_db)):
    """Garage-wide occupancy summary — slot-status driven.

    Counts cover **monitored slots only** — unmonitored (blind) slots are
    excluded from `available_slots` and `occupied_slots` because VA can't
    observe them. `total_slots` still counts both for inventory purposes;
    `unmonitored_slots` is exposed separately so the FE can render the
    "Uncovered Slots" hint card.

    `available_slots = monitored_slots − occupied_slots` (not
    `total_slots − occupied_slots`), so "available" reflects what VA can
    actually fill, not the inventory gap. The shared `coverage_note`
    string explains this distinction to operators.
    """
    total_slots = scalar(
        db,
        f"SELECT COUNT(*) FROM parking_slots WHERE is_violation_zone = 0 {_slot_type_excl()}",
    ) or 0

    monitored_slots = scalar(
        db,
        f"SELECT COUNT(*) FROM parking_slots WHERE is_violation_zone = 0 {_slot_type_excl()} {_monitored_only()}",
    ) or 0
    unmonitored_slots = max(total_slots - monitored_slots, 0)

    # Slot-status latest row per slot, restricted to monitored rows. VA can't
    # observe an unmonitored slot, so it can't show as occupied here.
    occupied_slots = scalar(db, f"""
        SELECT COUNT(*) FROM parking_slots pk
        {_LATEST_STATUS_JOIN}
        WHERE pk.is_violation_zone = 0
          {_slot_type_excl('pk')}
          {_monitored_only('pk')}
          AND ss.status IS NOT NULL
          AND ss.status NOT IN ('empty', 'available', 'free', 'VACANT')
    """) or 0

    # Coverage-aware: "available" is monitored − occupied, not total − occupied.
    available_slots = max(monitored_slots - occupied_slots, 0)
    overall_utilization = round(occupied_slots / total_slots * 100, 1) if total_slots else 0.0

    active_vehicles = scalar(
        db, "SELECT COUNT(DISTINCT plate_number) FROM parking_sessions WHERE status = 'open'"
    )

    return OccupancyKPIs(
        total_slots=total_slots,
        available_slots=available_slots,
        occupied_slots=occupied_slots,
        overall_utilization=overall_utilization,
        total_vehicles=active_vehicles or 0,
        monitored_slots=monitored_slots,
        unmonitored_slots=unmonitored_slots,
    )


@router.get("/zones", response_model=PagedResponse[ZoneItem], deprecated=True)
async def get_zones(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="zone name or floor"),
    floor: Optional[str] = Query(None),
    floor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """DEPRECATED — use /occupancy/floors. Removed in Phase 4C.

    Read-only as of PR 2: max_capacity is computed live (not written back to
    zone_occupancy.max_capacity on every read like the legacy implementation
    did). The floor-based truth source is `_build_floor_occupancy()` —
    zone_occupancy is read but never UPDATEd here."""
    # WS-8 schema-compat shim: tolerate pre-migration DB without floors table /
    # floor_id columns. Pattern A/B/C/D — branch on each probe.
    schema = _floor_schema()
    # resolve_floor_id already returns None when floors table is missing and
    # only a name was sent; guard the integer path on column presence.
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=floor)
    # WS-8: drop hardcoded B1/B2 — derive max_capacity per floor + GARAGE-TOTAL via a single GROUP BY.
    if schema["floors_table"] and schema["parking_slots_floor_id"]:
        floor_counts = rows(
            db,
            f"""
            SELECT f.name AS floor_name, COUNT(*) AS cnt
            FROM parking_slots ps JOIN floors f ON f.id = ps.floor_id
            WHERE ps.is_violation_zone = 0
              {_slot_type_excl('ps')}
            GROUP BY f.name
            """,
        )
    else:
        # Pre-migration fallback: group by the legacy `floor` string column.
        floor_counts = rows(
            db,
            f"""
            SELECT ps.floor AS floor_name, COUNT(*) AS cnt
            FROM parking_slots ps
            WHERE ps.floor IS NOT NULL
              AND ps.is_violation_zone = 0
              {_slot_type_excl('ps')}
            GROUP BY ps.floor
            """,
        )
    live_max_by_zone: dict[str, int] = {}
    total_max = 0
    for fc in floor_counts:
        cnt = int(fc.get("cnt") or 0)
        live_max_by_zone[f"{fc['floor_name']}-PARKING"] = cnt
        total_max += cnt
    live_max_by_zone["GARAGE-TOTAL"] = total_max

    # Filtering
    clauses = ["1=1"]
    params: dict = {}

    if search:
        clauses.append("(zo.zone_name LIKE :search OR CAST(zo.floor AS NVARCHAR) LIKE :search OR zo.zone_id LIKE :search)")
        params["search"] = f"%{search}%"

    if resolved_floor_id is not None and schema["floors_table"]:
        # WS-8: filter by integer floor_id via the floors join (subquery on floors).
        clauses.append("zo.floor = (SELECT name FROM floors WHERE id = :floor_id)")
        params["floor_id"] = resolved_floor_id
    elif floor:
        # Pre-migration fallback (or legacy callers): filter on string floor name.
        clauses.append("zo.floor = :floor")
        params["floor"] = floor

    where = " AND ".join(clauses)

    total = scalar(
        db,
        f"SELECT COUNT(*) FROM zone_occupancy zo WHERE {where}",
        params,
    )

    params["offset"] = (page - 1) * page_size
    params["page_size"] = page_size

    # Fetch zones (read-only). max_capacity from zone_occupancy is overridden
    # by live_max_by_zone below, so a stale value in the table is harmless.
    # WS-8: LEFT JOIN floors so each row carries the integer floor_id.
    if schema["floors_table"]:
        floors_join = "LEFT JOIN floors f ON f.name = zo.floor"
        floor_id_select = "f.id AS floor_id"
    else:
        floors_join = ""
        floor_id_select = "NULL AS floor_id"
    zone_rows = rows(
        db,
        f"""
        SELECT
            zo.id,
            zo.zone_id,
            zo.zone_name,
            zo.floor,
            {floor_id_select},
            zo.camera_id,
            zo.max_capacity,
            zo.current_count,
            zo.last_updated
        FROM zone_occupancy zo
        {floors_join}
        WHERE {where}
        ORDER BY zo.floor, zo.zone_name
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
        """,
        params,
    )

    # Replace persisted max_capacity with the live value for known zones
    for z in zone_rows:
        live = live_max_by_zone.get(z["zone_id"])
        if live is not None:
            z["max_capacity"] = live

    # =========================
    # 🔹 STEP 5: Live slots overlay
    # =========================
    live_slots = await get_live_slots()

    live_by_zone: dict[str, int] = {}
    for slot in live_slots:
        zid = str(slot.get("zone_id") or slot.get("zone") or "")
        if zid:
            live_by_zone[zid] = live_by_zone.get(zid, 0) + (
                1 if slot.get("status") not in ("empty", "available", "free") else 0
            )

    # =========================
    # 🔹 STEP 6: Build response
    # =========================
    items = []
    for z in zone_rows:
        zid = str(z["zone_id"])

        occupied = live_by_zone.get(zid, z["current_count"] or 0)
        capacity = max(z["max_capacity"] or 0, 1)

        items.append({
            **z,
            "occupied": occupied,
            "available": max(capacity - occupied, 0),
            "utilization": round(occupied / capacity * 100, 1),
        })

    return build_paged(items, total or 0, page, page_size)

@router.get("/slots", response_model=PagedResponse[SlotListItem])
async def get_slots(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    floor: Optional[str] = Query(None),
    floor_id: Optional[int] = Query(None),
    is_available: Optional[bool] = Query(None),
    is_monitored: Optional[StrictQueryBool] = Query(
        None,
        description=(
            "Filter by camera coverage. Accepts only `true` or `false` "
            "(case-insensitive). `true` = VA covers this slot, `false` = "
            "blind spot. Rejects `1` / `0` / `yes` / `no`."
        ),
    ),
    reservation_type: Optional[ReservationType] = Query(None),
    db: Session = Depends(get_db),
):
    """Paginated slot grid — joins parking_slots with the latest slot_status row.

    G-4: the legacy `?grouped=true` shape was removed; consumers that want
    the per-floor grouping should call `/occupancy/slots/by-floor` instead,
    which returns `list[FloorSlotGroup]` and is the canonical home for that
    view. This endpoint always returns a `PagedResponse[SlotListItem]`.

    Violation-zone rows (is_violation_zone = 1) are permanently excluded —
    they are alert trigger areas, not real parking spaces.
    """
    # WS-8 schema-compat shim — branch on each probe (Pattern A + C).
    schema = _floor_schema()
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=floor)
    # Violation zones are excluded unconditionally from this endpoint.
    clauses = ["ps.is_violation_zone = 0"]
    params: dict = {}

    if resolved_floor_id is not None and schema["parking_slots_floor_id"]:
        # Hybrid filter — match by integer when row was backfilled, else fall
        # through to the legacy string `floor` for rows whose floor_id is NULL.
        floor_name_for_filter = floor or resolve_floor_name(db, resolved_floor_id)
        if floor_name_for_filter:
            clauses.append("(ps.floor_id = :floor_id OR (ps.floor_id IS NULL AND ps.floor = :floor_name))")
            params["floor_id"] = resolved_floor_id
            params["floor_name"] = floor_name_for_filter
        else:
            clauses.append("ps.floor_id = :floor_id")
            params["floor_id"] = resolved_floor_id
    elif floor:
        clauses.append("ps.floor = :floor")
        params["floor"] = floor
    if is_available is not None:
        clauses.append("ps.is_available = :is_available")
        params["is_available"] = 1 if is_available else 0
    if is_monitored is not None and schema.get("parking_slots_is_monitored"):
        clauses.append("ps.is_monitored = :is_monitored")
        params["is_monitored"] = 1 if is_monitored else 0
    if reservation_type is not None and schema.get("parking_slots_reservation_type"):
        clauses.append("ps.reservation_type = :reservation_type")
        params["reservation_type"] = reservation_type

    slot_type_clause = _slot_type_excl("ps").lstrip("AND ").strip()
    if slot_type_clause:
        clauses.append(slot_type_clause)
    where = " AND ".join(clauses)
    total = scalar(db, f"SELECT COUNT(*) FROM parking_slots ps WHERE {where}", params)

    params["offset"]    = (page - 1) * page_size
    params["page_size"] = page_size

    # WS-8: surface ps.id (slot integer PK) and ps.floor_id alongside legacy keys
    # (NULL fallback when the columns don't exist yet). COALESCE pk.floor_id
    # with a name-based lookup so legacy un-backfilled rows still report a
    # populated floor_id when the floors table knows the name.
    ps_id_col = "ps.id" if schema["parking_slots_id"] else "NULL AS id"
    if schema["parking_slots_floor_id"] and schema["floors_table"]:
        ps_floor_id_col = "COALESCE(ps.floor_id, f_lookup.id) AS floor_id"
        floor_id_lookup_join = "LEFT JOIN floors f_lookup ON f_lookup.name = ps.floor"
    elif schema["parking_slots_floor_id"]:
        ps_floor_id_col = "ps.floor_id"
        floor_id_lookup_join = ""
    elif schema["floors_table"]:
        ps_floor_id_col = "f_lookup.id AS floor_id"
        floor_id_lookup_join = "LEFT JOIN floors f_lookup ON f_lookup.name = ps.floor"
    else:
        ps_floor_id_col = "NULL AS floor_id"
        floor_id_lookup_join = ""
    ps_category_col = "ps.reservation_type AS reservation_type" if schema.get("parking_slots_reservation_type") else "NULL AS reservation_type"
    ps_reserved_col  = "ps.reserved_for"     if schema.get("parking_slots_reserved_for")     else "NULL AS reserved_for"
    ps_monitored_col = _monitored_col("ps")
    items = rows(db, f"""
        SELECT
            {ps_id_col},
            ps.slot_id,
            ps.slot_name,
            ps.floor,
            {ps_floor_id_col},
            ps.is_available,
            ps.is_violation_zone,
            {ps_monitored_col},
            {_active_violation_cols('ps')},
            {ps_category_col},
            {ps_reserved_col},
            {_current_plate_col('ps')},
            ss.status           AS current_status,
            ss.time             AS status_updated_at
        FROM parking_slots ps
        LEFT JOIN slot_status ss ON ss.slot_id = ps.slot_id
            AND ss.time = (
                SELECT MAX(time) FROM slot_status WHERE slot_id = ps.slot_id
            )
        {floor_id_lookup_join}
        LEFT JOIN dbo.floors fo ON fo.name = ps.floor
        WHERE {where}
        -- Floor priority first (Ground=0, B1=1, B2=2 per migrate_floors_sort_order.sql),
        -- then natural-numeric portion of slot_id, then alphabetic tiebreaker.
        -- Produces "Ground/G1, B1/B1_CRO, B1/B2, ..., B1/B10, B1/B11_CFO, B2/B14, ..."
        -- instead of "B1/..., B2/..., Ground/..." which the old lex sort emitted.
        ORDER BY
            COALESCE(fo.sort_order, 999),
            ps.floor,
            CASE WHEN ps.slot_id LIKE '[A-Za-z][0-9]%'
                 THEN TRY_CAST(SUBSTRING(ps.slot_id, 2, PATINDEX('%[^0-9]%', SUBSTRING(ps.slot_id, 2, 100) + 'X') - 1) AS INT)
                 ELSE TRY_CAST(SUBSTRING(ps.slot_name, PATINDEX('%B[0-9]%', ps.slot_name) + 1, PATINDEX('%[^0-9]%', SUBSTRING(ps.slot_name, PATINDEX('%B[0-9]%', ps.slot_name) + 1, 100) + 'X') - 1) AS INT)
            END,
            ps.slot_id
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)

    return build_paged(items, total or 0, page, page_size)

@router.get("/export")
async def export_occupancy_csv(
    floor: Optional[str] = Query(None),
    floor_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None, description="filters slot_id / slot_name / floor"),
    db: Session = Depends(get_db),
):
    """CSV occupancy report. Filter set matches the corresponding `/occupancy/*`
    list endpoints so the download mirrors the on-screen view."""
    # WS-8 schema-compat shim.
    schema = _floor_schema()
    # WS-8: resolve floor_id (or floor name) to integer key, then back to name for legacy SQL filters.
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=floor)
    if resolved_floor_id is not None and floor is None and schema["floors_table"]:
        floor = resolve_floor_name(db, resolved_floor_id)
    output = StringIO()
    writer = csv.writer(output)

    # =========================
    # 1. KPI Section
    # =========================
    total_spots = scalar(
        db,
        f"SELECT COUNT(*) FROM parking_slots WHERE is_violation_zone = 0 {_slot_type_excl()}",
    )

    monitored_spots = scalar(
        db,
        f"SELECT COUNT(*) FROM parking_slots WHERE is_violation_zone = 0 {_slot_type_excl()} {_monitored_only()}",
    ) or 0
    unmonitored_spots = max((total_spots or 0) - monitored_spots, 0)

    occupied = scalar(db, f"""
        SELECT COUNT(DISTINCT ss.slot_id)
        FROM slot_status ss
        INNER JOIN (
            SELECT slot_id, MAX(time) AS latest
            FROM slot_status
            GROUP BY slot_id
        ) latest_ss
        ON latest_ss.slot_id = ss.slot_id
        AND latest_ss.latest = ss.time
        INNER JOIN parking_slots pk ON pk.slot_id = ss.slot_id
        WHERE pk.is_violation_zone = 0
          {_slot_type_excl('pk')}
          {_monitored_only('pk')}
          AND ss.status NOT IN ('empty', 'available', 'free')
    """) or 0

    available = max((total_spots or 0) - occupied, 0)
    utilization = round((occupied / total_spots) * 100, 1) if total_spots else 0

    writer.writerow(["=== OCCUPANCY KPIs ==="])
    writer.writerow(["total_spots", total_spots or 0])
    writer.writerow(["monitored_spots", monitored_spots])
    writer.writerow(["unmonitored_spots", unmonitored_spots])
    writer.writerow(["occupied_spots", occupied])
    writer.writerow(["available_spots", available])
    writer.writerow(["utilization %", utilization])
    writer.writerow([])

    # =========================
    # 2. Floors Section (replaces legacy Zones section)
    # =========================
    floor_rows = rows(db, f"""
        SELECT DISTINCT floor FROM parking_slots
        WHERE floor IS NOT NULL
          AND is_violation_zone = 0
          {_slot_type_excl()}
        ORDER BY floor
    """)
    floors = [r["floor"] for r in floor_rows if not floor or r["floor"] == floor]

    writer.writerow(["=== FLOORS ==="])
    writer.writerow([
        "floor",
        "camera_id",
        "max_capacity",
        "monitored_capacity",
        "unmonitored_count",
        "current_count",
        "slot_occupancy_count",
        "utilization %",
        "reconciled",
        "last_updated",
    ])

    for f_name in floors:
        fo = _build_floor_occupancy(db, f_name)
        writer.writerow([
            fo.floor,
            fo.camera_id,
            fo.max_capacity,
            fo.monitored_capacity,
            fo.unmonitored_count,
            fo.current_count,
            fo.slot_occupancy_count,
            fo.utilization,
            fo.reconciled,
            fo.last_updated,
        ])

    writer.writerow([])

    # =========================
    # 3. Slots Section
    # =========================
    slot_clauses = ["1=1"]
    slot_params = {}

    if floor:
        slot_clauses.append("ps.floor = :floor")
        slot_params["floor"] = floor
    if search:
        slot_clauses.append(
            "(ps.slot_id LIKE :search OR ps.slot_name LIKE :search OR ps.floor LIKE :search)"
        )
        slot_params["search"] = f"%{search}%"

    slot_clauses.insert(0, "ps.is_violation_zone = 0")
    slot_type_clause_csv = _slot_type_excl("ps").lstrip("AND ").strip()
    if slot_type_clause_csv:
        slot_clauses.append(slot_type_clause_csv)
    slot_where = " AND ".join(slot_clauses)

    exp_category_col = "ps.reservation_type AS reservation_type" if schema.get("parking_slots_reservation_type") else "NULL AS reservation_type"
    exp_reserved_col  = "ps.reserved_for"     if schema.get("parking_slots_reserved_for")     else "NULL AS reserved_for"
    exp_monitored_col = _monitored_col("ps")
    slots = rows(db, f"""
        SELECT
            ps.slot_id,
            ps.slot_name,
            ps.floor,
            ps.is_available,
            {exp_monitored_col},
            {_active_violation_cols('ps')},
            {exp_category_col},
            {exp_reserved_col},
            {_current_plate_col('ps')},
            ss.status AS current_status,
            ss.time AS status_updated_at
        FROM parking_slots ps
        LEFT JOIN slot_status ss
            ON ss.slot_id = ps.slot_id
            AND ss.time = (
                SELECT MAX(time)
                FROM slot_status
                WHERE slot_id = ps.slot_id
            )
        WHERE {slot_where}
        -- Natural sort — see /occupancy/slots query for rationale.
        ORDER BY
            ps.floor,
            CASE WHEN ps.slot_id LIKE '[A-Za-z][0-9]%'
                 THEN TRY_CAST(SUBSTRING(ps.slot_id, 2, PATINDEX('%[^0-9]%', SUBSTRING(ps.slot_id, 2, 100) + 'X') - 1) AS INT)
                 ELSE TRY_CAST(SUBSTRING(ps.slot_name, PATINDEX('%B[0-9]%', ps.slot_name) + 1, PATINDEX('%[^0-9]%', SUBSTRING(ps.slot_name, PATINDEX('%B[0-9]%', ps.slot_name) + 1, 100) + 'X') - 1) AS INT)
            END,
            ps.slot_id
    """, slot_params)

    writer.writerow(["=== SLOTS ==="])
    writer.writerow([
        "slot_id",
        "slot_name",
        "floor",
        "is_available",
        "is_monitored",
        "has_active_violation",
        "active_violation_type",
        "active_violation_severity",
        "reservation_type",
        "reserved_for",
        "current_plate",
        "current_status",
        "status_updated_at"
    ])

    for s in slots:
        writer.writerow([
            s["slot_id"],
            s["slot_name"],
            s["floor"],
            s["is_available"],
            s.get("is_monitored"),
            s.get("has_active_violation"),
            s.get("active_violation_type"),
            s.get("active_violation_severity"),
            s["reservation_type"],
            s["reserved_for"],
            s["current_plate"],
            s["current_status"],
            s["status_updated_at"],
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=occupancy_report.csv"
        }
    )


# ── NEW in Phase 2: floor-based endpoints (replace zone_occupancy mental model) ─
def _build_floor_occupancy(
    db: Session,
    floor: Optional[str] = None,
    floor_id: Optional[int] = None,
) -> FloorOccupancy:
    """Build a single FloorOccupancy row — reconciles PMS-AI line-crossing count
    (from zone_occupancy, Phase 4A will move to floor_occupancy table) with VA's
    slot aggregation (from slot_status). WS-8: callers may pass either the floor
    name string or the integer floor_id; both are resolved to the integer key."""
    # WS-8 schema-compat shim.
    schema = _floor_schema()
    # WS-8: resolve floor_id once and use it for all SQL filters; keep `floor` (name) for response.
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=floor)
    if resolved_floor_id is not None and floor is None and schema["floors_table"]:
        floor = resolve_floor_name(db, resolved_floor_id)

    # WS-8: filter parking_slots by integer floor_id when the column exists,
    # else fall back to the legacy string `floor` column.
    # max_capacity counts BOTH monitored and unmonitored rows — that's the
    # true floor size. monitored_capacity is the slice VA can observe.
    if schema["parking_slots_floor_id"] and resolved_floor_id is not None:
        max_capacity = scalar(
            db,
            f"SELECT COUNT(*) FROM parking_slots WHERE floor_id = :fid AND is_violation_zone = 0 {_slot_type_excl()}",
            {"fid": resolved_floor_id},
        ) or 0
        monitored_capacity = scalar(
            db,
            f"SELECT COUNT(*) FROM parking_slots WHERE floor_id = :fid AND is_violation_zone = 0 {_slot_type_excl()} {_monitored_only()}",
            {"fid": resolved_floor_id},
        ) or 0
    else:
        max_capacity = scalar(
            db,
            f"SELECT COUNT(*) FROM parking_slots WHERE floor = :f AND is_violation_zone = 0 {_slot_type_excl()}",
            {"f": floor},
        ) or 0
        monitored_capacity = scalar(
            db,
            f"SELECT COUNT(*) FROM parking_slots WHERE floor = :f AND is_violation_zone = 0 {_slot_type_excl()} {_monitored_only()}",
            {"f": floor},
        ) or 0
    unmonitored_count = max(max_capacity - monitored_capacity, 0)

    # slot_occupancy_count = monitored slots whose latest status is non-vacant.
    # Unmonitored slots have no slot_status rows so they could only contribute
    # NULL — filtering on `is_monitored = 1` makes the intent explicit and the
    # SQL stable as more shims accumulate.
    if schema["parking_slots_floor_id"] and resolved_floor_id is not None:
        slot_rows = rows(db, f"""
            SELECT pk.slot_id, ss.status
            FROM parking_slots pk
            {_LATEST_STATUS_JOIN}
            WHERE pk.floor_id = :fid
              AND pk.is_violation_zone = 0
              {_slot_type_excl('pk')}
              {_monitored_only('pk')}
        """, {"fid": resolved_floor_id})
    else:
        slot_rows = rows(db, f"""
            SELECT pk.slot_id, ss.status
            FROM parking_slots pk
            {_LATEST_STATUS_JOIN}
            WHERE pk.floor = :f
              AND pk.is_violation_zone = 0
              {_slot_type_excl('pk')}
              {_monitored_only('pk')}
        """, {"f": floor})
    slot_occupancy_count = sum(1 for r in slot_rows if _is_occupied(r.get("status")))

    # Line-crossing source (zone_occupancy is still the table of record until
    # Phase 4A migrates to floor_occupancy). `line_crossing_count` is exposed
    # as the per-source signal `cars_in_floor`; the headline `current_count`
    # uses the slot-status reading instead — see comment below.
    zo = rows(db, """
        SELECT camera_id, current_count, last_updated
        FROM zone_occupancy WHERE floor = :f AND zone_id != 'GARAGE-TOTAL'
    """, {"f": floor})
    if zo:
        z = zo[0]
        line_crossing_count = int(z.get("current_count") or 0)
        camera_id = z.get("camera_id")
        last_updated = z.get("last_updated")
    else:
        line_crossing_count = slot_occupancy_count
        camera_id = None
        last_updated = None

    # GA-3 alignment: `current_count` / `available` / `utilization` all use
    # the slot-status reading (visual ground truth from VA). Line-crossing
    # accumulates errors in both directions:
    #   - missed exit → cars_in_floor > slots_occupied (phantom-full)
    #   - missed entry → cars_in_floor < slots_occupied (the case the user
    #     just hit: 2 in floor / 4 in slots — physically impossible without
    #     a missed entry counter)
    # Slot-status mirrors what the operator sees on the live grid, so it's
    # always the more honest headline. The raw line-crossing reading lives
    # on `cars_in_floor` for transparency; `reconciled=False` flags drift.
    headline_occupied = slot_occupancy_count
    # Coverage-aware: "available" counts over monitored capacity only — the
    # operator can't fill a slot VA can't see. Utilization stays scaled to
    # the true floor size so it remains comparable across floors with
    # different blind-spot counts.
    available = max(monitored_capacity - headline_occupied, 0)
    utilization = round(headline_occupied / max_capacity * 100, 1) if max_capacity else 0.0

    return FloorOccupancy(
        # WS-8: floor_id is the canonical key (same vocabulary as every
        # other DTO that points at a floor).
        floor_id=resolved_floor_id,
        floor=floor,
        max_capacity=max_capacity,
        # `current_count` is the headline (slot-status); `cars_in_floor`
        # is the per-source line-crossing reading. They differ when the
        # two sources disagree.
        current_count=headline_occupied,
        available=available,
        utilization=utilization,
        data_source="slot_aggregation",
        last_updated=last_updated,
        camera_id=camera_id,
        slot_occupancy_count=slot_occupancy_count,
        slot_occupancy_source="va_cv",
        reconciled=(line_crossing_count == slot_occupancy_count),
        # Operator-facing breakdown: how many cars entered the floor vs.
        # how many slots are actually occupied. Gap = cars driving / blocking
        # aisles / line-crossing drift in either direction.
        cars_in_floor=line_crossing_count,
        slots_occupied=slot_occupancy_count,
        cars_unparked=max(line_crossing_count - slot_occupancy_count, 0),
        # Blind-spot breakdown: max_capacity is true floor size (monitored +
        # unmonitored); monitored_capacity is the slice VA covers.
        monitored_capacity=monitored_capacity,
        unmonitored_count=unmonitored_count,
    )


@router.get("/floors", response_model=PagedResponse[FloorOccupancy])
async def get_floors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: FloorSort = Query(
        FloorSort.default,
        description=(
            "`default` = floor layout order; `most_occupied` = highest "
            "utilization first; `least_occupied` = lowest utilization first."
        ),
    ),
    db: Session = Depends(get_db),
):
    """Per-floor occupancy. Replaces the zones model — floor is the only
    spatial grouping in this deployment (B1, B2)."""
    # WS-8 schema-compat shim — Pattern D: fall back to legacy DISTINCT on
    # parking_slots when the floors table doesn't exist yet.
    schema = _floor_schema()
    if schema["floors_table"]:
        # WS-8: source list of floors from the floors table.
        floor_rows = rows(db, """
            SELECT id, name FROM floors
            WHERE is_active = 1
            ORDER BY sort_order, name
        """)
    else:
        # Pre-migration fallback — DISTINCT floor names from parking_slots
        # (no integer id available; emit NULL).
        floor_rows = rows(db, """
            SELECT NULL AS id, floor AS name
            FROM parking_slots
            WHERE floor IS NOT NULL
            GROUP BY floor
            ORDER BY floor
        """)
    total = len(floor_rows)

    start = (page - 1) * page_size
    if sort is FloorSort.default:
        slice_ = floor_rows[start:start + page_size]
        # WS-8: pass floor_id (integer) so _build_floor_occupancy uses the indexed FK directly.
        items = [_build_floor_occupancy(db, floor=f["name"], floor_id=f.get("id")) for f in slice_]
        return build_paged(items, total, page, page_size)

    # Utilization is computed per floor in Python, so every floor has to be
    # built and ranked before slicing — otherwise each page sorts on its own.
    # Ties break on occupied count, then keep layout order (sort is stable).
    items = [_build_floor_occupancy(db, floor=f["name"], floor_id=f.get("id")) for f in floor_rows]
    items.sort(
        key=lambda fo: (fo.utilization, fo.current_count),
        reverse=sort is FloorSort.most_occupied,
    )
    return build_paged(items[start:start + page_size], total, page, page_size)


@router.get("/totals", response_model=OccupancyTotals)
async def get_occupancy_totals(db: Session = Depends(get_db)):
    """Garage-wide rollup — replaces the synthetic GARAGE-TOTAL zone_occupancy row.

    Counts cover monitored slots only (same convention as /occupancy/kpis):
    `available_slots = monitored_slots - occupied_slots`, not `total_slots -
    occupied_slots`, so "available" reflects what VA can actually fill.
    """
    total_slots = scalar(
        db,
        f"SELECT COUNT(*) FROM parking_slots WHERE is_violation_zone = 0 {_slot_type_excl()}",
    ) or 0

    # Monitored-only inventory for the available-slots denominator.
    monitored_total = scalar(
        db,
        f"SELECT COUNT(*) FROM parking_slots WHERE is_violation_zone = 0 {_slot_type_excl()} {_monitored_only()}",
    ) or 0

    # occupied_slots = distinct monitored slots with a non-vacant latest status.
    # Unmonitored rows have no slot_status events and must not count here.
    occupied_slots = scalar(db, f"""
        SELECT COUNT(*) FROM parking_slots pk
        {_LATEST_STATUS_JOIN}
        WHERE pk.is_violation_zone = 0
          {_slot_type_excl('pk')}
          {_monitored_only('pk')}
          AND ss.status IS NOT NULL
          AND ss.status NOT IN ('empty', 'available', 'free', 'VACANT')
    """) or 0

    total_vehicles = scalar(
        db, "SELECT COUNT(DISTINCT plate_number) FROM parking_sessions WHERE status = 'open'"
    ) or 0

    # Coverage-aware: monitored − occupied (not total − occupied).
    available_slots = max(monitored_total - occupied_slots, 0)
    overall = round(occupied_slots / total_slots * 100, 1) if total_slots else 0.0

    return OccupancyTotals(
        total_slots=total_slots,
        occupied_slots=occupied_slots,
        available_slots=available_slots,
        overall_utilization=overall,
        total_vehicles=total_vehicles,
    )


@router.get("/floors/{floor}", response_model=FloorOccupancy)
async def get_floor_detail(floor: str, db: Session = Depends(get_db)):
    """Single floor's occupancy snapshot. Slot list + recent activity are
    available via /occupancy/slots?floor={floor} and /alerts/?floor={floor}."""
    # WS-8: resolve_floor_id raises 404 itself when the name doesn't match any floors row.
    resolved_floor_id = resolve_floor_id(db, floor_name=floor)
    return _build_floor_occupancy(db, floor=floor, floor_id=resolved_floor_id)


@router.get("/slots/by-floor", response_model=list[FloorSlotGroup])
async def get_slots_by_floor(
    floor: Optional[str] = Query(None),
    floor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Slot grid grouped by floor. Replacement for the old /slots?grouped=true
    behavior — exposed at a dedicated URL so /slots can stay strictly paginated."""
    # WS-8 schema-compat shim — Pattern A + C.
    schema = _floor_schema()
    # WS-8: resolve either floor_id or floor name into the integer key for the WHERE clause.
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=floor)
    # Violation zones are permanently excluded from the slot grid.
    clauses = ["pk.is_violation_zone = 0"]
    params: dict = {}
    if resolved_floor_id is not None and schema["parking_slots_floor_id"]:
        # Hybrid filter — match by integer when the row was backfilled, else
        # fall through to the legacy string `floor` column for rows whose
        # floor_id hasn't been populated yet (transitional resilience).
        floor_name_for_filter = floor or resolve_floor_name(db, resolved_floor_id)
        if floor_name_for_filter:
            clauses.append("(pk.floor_id = :floor_id OR (pk.floor_id IS NULL AND pk.floor = :floor_name))")
            params["floor_id"] = resolved_floor_id
            params["floor_name"] = floor_name_for_filter
        else:
            clauses.append("pk.floor_id = :floor_id")
            params["floor_id"] = resolved_floor_id
    elif floor:
        clauses.append("pk.floor = :floor")
        params["floor"] = floor
    slot_type_clause_bf = _slot_type_excl("pk").lstrip("AND ").strip()
    if slot_type_clause_bf:
        clauses.append(slot_type_clause_bf)
    where = " AND ".join(clauses)

    # WS-8: surface pk.id and pk.floor_id alongside legacy keys (NULL fallback).
    # COALESCE pk.floor_id with a name-based lookup so the response always
    # returns a populated floor_id when the floors table knows the name —
    # frontend caches keyed on floor_id stay accurate even before the DB
    # backfill runs.
    pk_id_col = "pk.id" if schema["parking_slots_id"] else "NULL AS id"
    if schema["parking_slots_floor_id"] and schema["floors_table"]:
        pk_floor_id_col = "COALESCE(pk.floor_id, f_lookup.id) AS floor_id"
        floor_id_lookup_join = "LEFT JOIN floors f_lookup ON f_lookup.name = pk.floor"
    elif schema["parking_slots_floor_id"]:
        pk_floor_id_col = "pk.floor_id"
        floor_id_lookup_join = ""
    elif schema["floors_table"]:
        pk_floor_id_col = "f_lookup.id AS floor_id"
        floor_id_lookup_join = "LEFT JOIN floors f_lookup ON f_lookup.name = pk.floor"
    else:
        pk_floor_id_col = "NULL AS floor_id"
        floor_id_lookup_join = ""
    pk_category_col = "pk.reservation_type AS reservation_type" if schema.get("parking_slots_reservation_type") else "NULL AS reservation_type"
    pk_reserved_col  = "pk.reserved_for"     if schema.get("parking_slots_reserved_for")     else "NULL AS reserved_for"
    pk_monitored_col = _monitored_col("pk")
    data = rows(db, f"""
        SELECT
            {pk_id_col},
            pk.slot_id,
            pk.slot_name,
            pk.floor,
            {pk_floor_id_col},
            pk.is_available,
            pk.is_violation_zone,
            {pk_monitored_col},
            {_active_violation_cols('pk')},
            {pk_category_col},
            {pk_reserved_col},
            {_current_plate_col('pk')},
            ss.status           AS current_status,
            ss.time             AS status_updated_at
        FROM parking_slots pk
        {_LATEST_STATUS_JOIN}
        {floor_id_lookup_join}
        LEFT JOIN dbo.floors fo ON fo.name = pk.floor
        WHERE {where}
        -- Floor priority first (Ground, B1, B2 from floors.sort_order),
        -- then natural-numeric portion of slot_id, then alphabetic tiebreaker.
        -- Same shape as /occupancy/slots so the two endpoints stay consistent.
        ORDER BY
            COALESCE(fo.sort_order, 999),
            pk.floor,
            CASE WHEN pk.slot_id LIKE '[A-Za-z][0-9]%'
                 THEN TRY_CAST(SUBSTRING(pk.slot_id, 2, PATINDEX('%[^0-9]%', SUBSTRING(pk.slot_id, 2, 100) + 'X') - 1) AS INT)
                 ELSE TRY_CAST(SUBSTRING(pk.slot_name, PATINDEX('%B[0-9]%', pk.slot_name) + 1, PATINDEX('%[^0-9]%', SUBSTRING(pk.slot_name, PATINDEX('%B[0-9]%', pk.slot_name) + 1, 100) + 'X') - 1) AS INT)
            END,
            pk.slot_id
    """, params)

    # WS-8: track (floor_name, floor_id) pairs so each FloorSlotGroup carries both keys.
    floors_map: dict[str, list[SlotListItem]] = {}
    floor_id_by_name: dict[str, Optional[int]] = {}
    for row in data:
        f_name = row["floor"] or "Unassigned"
        floors_map.setdefault(f_name, []).append(SlotListItem.model_validate(row))
        floor_id_by_name.setdefault(f_name, row.get("floor_id"))

    return [
        FloorSlotGroup(floor=f_name, floor_id=floor_id_by_name.get(f_name), slots=slots)
        for f_name, slots in floors_map.items()
    ]


@router.get("/slots/{slot_id}", response_model=SlotDetail)
async def get_slot_detail(slot_id: str, db: Session = Depends(get_db)):
    """Single slot's full context — SlotRef + current occupancy + recent events
    + recent alerts. One fetch per view."""
    # WS-8 schema-compat shim — Pattern A: NULL fallback when columns missing.
    schema = _floor_schema()
    pk_id_col       = "pk.id"       if schema["parking_slots_id"]       else "NULL AS id"
    pk_floor_id_col = "pk.floor_id" if schema["parking_slots_floor_id"] else "NULL AS floor_id"
    pk_category_col = "pk.reservation_type AS reservation_type" if schema.get("parking_slots_reservation_type") else "NULL AS reservation_type"
    pk_reserved_col = "pk.reserved_for"     if schema.get("parking_slots_reserved_for")     else "NULL AS reserved_for"
    pk_monitored_col = _monitored_col("pk")
    slot_rows = rows(db, f"""
        SELECT
            {pk_id_col},
            pk.slot_id,
            pk.slot_name,
            pk.floor,
            {pk_floor_id_col},
            pk.is_available,
            pk.is_violation_zone AS is_violation_slot,
            {pk_monitored_col},
            {_active_violation_cols('pk')},
            {pk_category_col},
            {pk_reserved_col},
            pk.polygon,
            {_current_plate_col('pk')},
            ss.status           AS current_status,
            ss.time             AS status_updated_at
        FROM parking_slots pk
        {_LATEST_STATUS_JOIN}
        WHERE pk.slot_id = :slot_id
    """, {"slot_id": slot_id})

    if not slot_rows:
        from fastapi import HTTPException
        raise HTTPException(404, f"Slot '{slot_id}' not found")

    s = slot_rows[0]
    current = None
    last_occupant = None

    status = s.get("current_status")
    if _is_occupied(status):
        # Map legacy statuses to canonical state machine vocabulary.
        canonical_state = {
            "OCCUPIED": "OCCUPIED",
            "ENTERING": "ENTERING",
            "LEAVING": "LEAVING",
        }.get((status or "").upper(), "OCCUPIED")

        # Look up vehicle + open event + most recent slot snapshot for this plate
        open_event = None
        vehicle_id = None
        snapshot_url: Optional[str] = None
        if s.get("current_plate"):
            ev_rows = rows(db, """
                SELECT TOP 1
                    ps.id,
                    ps.vehicle_id,
                    -- Prefer the slot-camera snapshot (parked-in-slot view); fall
                    -- back to the entry-camera snapshot when the slot camera
                    -- didn't capture one (G-9).
                    COALESCE(ps.slot_snapshot_path, ps.entry_snapshot_path) AS snapshot_url
                FROM parking_sessions ps
                WHERE ps.plate_number = :p AND ps.status = 'open'
                ORDER BY ps.entry_time DESC
            """, {"p": s["current_plate"]})
            if ev_rows:
                open_event = ev_rows[0]["id"]
                vehicle_id = ev_rows[0].get("vehicle_id")
                snapshot_url = resolve_snapshot_url(ev_rows[0].get("snapshot_url"))

        current = {
            "state": canonical_state,
            "plate_number": s.get("current_plate"),
            "vehicle_id": vehicle_id,
            "vehicle_event_id": open_event,
            "since": s.get("status_updated_at"),
            "last_seen_at": s.get("status_updated_at"),
            "snapshot_url": snapshot_url,
        }
    else:
        # Populate last_occupant from the most recent closed parking event on this slot
        last_rows = rows(db, """
            SELECT TOP 1 ps.plate_number, ps.vehicle_id, ps.id, ps.slot_left_at, ps.exit_time
            FROM parking_sessions ps
            WHERE ps.slot_id = :sid AND ps.status != 'open'
            ORDER BY COALESCE(ps.slot_left_at, ps.exit_time) DESC
        """, {"sid": slot_id})
        if last_rows:
            lo = last_rows[0]
            left_at = lo.get("slot_left_at") or lo.get("exit_time")
            if left_at:
                last_occupant = {
                    "plate_number": lo["plate_number"],
                    "vehicle_id": lo.get("vehicle_id"),
                    "vehicle_event_id": lo["id"],
                    "left_at": left_at,
                }

    # parking_slots.polygon is stored as a JSON-encoded string (NVARCHAR);
    # SlotRef.polygon expects list[...] | None. Parse defensively — a corrupt
    # row should not 500 the endpoint, just surface as null polygon.
    raw_polygon = s.get("polygon")
    if isinstance(raw_polygon, str):
        import json
        try:
            parsed_polygon = json.loads(raw_polygon)
            if not isinstance(parsed_polygon, list):
                parsed_polygon = None
        except (json.JSONDecodeError, ValueError):
            parsed_polygon = None
    elif isinstance(raw_polygon, list):
        parsed_polygon = raw_polygon
    else:
        parsed_polygon = None

    return SlotDetail(
        # WS-8: integer PK (parking_slots.id) plus floor_id alongside legacy string keys.
        id=s.get("id"),
        slot_id=s["slot_id"],
        slot_name=s.get("slot_name"),
        floor=s.get("floor"),
        floor_id=s.get("floor_id"),
        is_available=bool(s.get("is_available")) if s.get("is_available") is not None else True,
        is_violation_slot=bool(s.get("is_violation_slot")) if s.get("is_violation_slot") is not None else False,
        is_monitored=bool(s.get("is_monitored")) if s.get("is_monitored") is not None else True,
        has_active_violation=bool(s.get("has_active_violation")) if s.get("has_active_violation") is not None else False,
        active_violation_type=s.get("active_violation_type"),
        active_violation_severity=s.get("active_violation_severity"),
        reservation_type=s.get("reservation_type"),
        reserved_for=s.get("reserved_for"),
        polygon=parsed_polygon,
        current=current,
        last_occupant=last_occupant,
    )


# ── Occupancy history (time-weighted) ─────────────────────────────────────────
#
# `slot_status` is a *transition log*, not a sample: one row per state change.
# Occupied time is therefore the gap between a row whose status is occupied and
# the next row for the same slot. Three things have to be added to that raw log
# before it can be summed over an arbitrary window:
#
#   1. the state CARRIED IN — the last transition at or before the window start,
#      so a car that was already parked when the window opened is counted;
#   2. a CAP at the window end, so a slot still occupied when the window closes
#      has a finite interval instead of a NULL LEAD;
#   3. a BUCKET SPLIT — an interval crossing midnight belongs to two days, so
#      the seconds have to be attributed per calendar day, not to the day the
#      interval started on.
#
# Steps 1-2 are the CTE chain; step 3 is the join against `buckets`, which
# clamps each interval to each bucket it overlaps. This is the anchor query for
# Report 1 (avg + peak occupancy, occupancy trend, utilization by floor) — every
# other figure in Reports 1 and 2 is a different GROUP BY over the same rows.

# Occupied-state predicate. Mirrors `_is_occupied()`: VA's state machine emits
# VACANT/ENTERING/OCCUPIED/LEAVING and anything that is not a vacant synonym is
# occupied — so ENTERING and LEAVING count. `status = 'occupied'` would silently
# drop those two states.
_VACANT_STATUSES = "'empty', 'available', 'free', 'VACANT'"

# Whitelisted bucket grains → (T-SQL datepart, floor-to-grain anchor expression).
# Never interpolate a raw query param into the datepart slot.
_HISTORY_GRAINS = {
    "day": ("DAY", "CAST(CAST(:start_time AS DATE) AS DATETIME)"),
    "hour": ("HOUR", "DATEADD(HOUR, DATEDIFF(HOUR, 0, :start_time), 0)"),
}



def _occupied_seconds_sql(grain: str, floor_clause: str, by_slot: bool = True) -> str:
    """Build the time-weighted occupancy query for one bucket grain.

    `by_slot=True` returns one row per (slot, bucket); `by_slot=False` rolls the
    slots up and returns one row per (floor, bucket), which is what the report
    summary wants — 3 floors x 720 hours instead of 35 slots x 720 hours.

    Buckets with no occupancy are absent — the consumer sums, so a missing row
    and a zero row are equivalent.

    Do NOT name bind params inside the SQL comments below: SQLAlchemy's
    `text()` binds `:name` occurrences in comments too, and pyodbc then sees
    fewer `?` markers than parameters supplied.
    """
    datepart, anchor = _HISTORY_GRAINS[grain]
    slot_col = "o.slot_id," if by_slot else ""
    slot_group = "o.slot_id," if by_slot else ""
    slot_order = "o.slot_id," if by_slot else ""
    return f"""
    WITH floor_slots AS (
        SELECT pk.slot_id, pk.floor
        FROM parking_slots pk
        WHERE pk.is_violation_zone = 0
          {_slot_type_excl('pk')}
          {floor_clause}
    ),
    -- (1) state carried into the window: the last transition at or before the
    --     window start, re-stamped to the window start so the interval begins
    --     at the edge.
    carried AS (
        SELECT slot_id, status, CAST(:start_time AS DATETIME) AS time
        FROM (
            SELECT ss.slot_id, ss.status,
                   ROW_NUMBER() OVER (
                       PARTITION BY ss.slot_id ORDER BY ss.time DESC, ss.id DESC
                   ) AS rn
            FROM slot_status ss
            JOIN floor_slots fs ON fs.slot_id = ss.slot_id
            WHERE ss.time <= CAST(:start_time AS DATETIME)
        ) t
        WHERE rn = 1
    ),
    -- Strictly greater than the window start — `>=` would collide with the
    -- carried row and the LEAD tie-break would then be arbitrary.
    in_window AS (
        SELECT ss.slot_id, ss.status, ss.time
        FROM slot_status ss
        JOIN floor_slots fs ON fs.slot_id = ss.slot_id
        WHERE ss.time > CAST(:start_time AS DATETIME)
          AND ss.time < CAST(:end_time AS DATETIME)
    ),
    -- (2) cap so the final interval of each slot terminates at the window edge.
    window_cap AS (
        SELECT fs.slot_id, CAST(NULL AS VARCHAR(50)) AS status,
               CAST(:end_time AS DATETIME) AS time
        FROM floor_slots fs
    ),
    transitions AS (
        SELECT * FROM carried
        UNION ALL SELECT * FROM in_window
        UNION ALL SELECT * FROM window_cap
    ),
    intervals AS (
        SELECT slot_id, status, time AS seg_start,
               LEAD(time) OVER (PARTITION BY slot_id ORDER BY time) AS seg_end
        FROM transitions
    ),
    occupied AS (
        SELECT slot_id, seg_start, seg_end
        FROM intervals
        WHERE seg_end IS NOT NULL
          AND seg_end > seg_start
          AND status IS NOT NULL
          AND status NOT IN ({_VACANT_STATUSES})
    ),
    -- (3) bucket grid over the window, anchored to a calendar boundary.
    tally AS (
        SELECT TOP (:bucket_count)
               ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n
        FROM sys.all_objects a CROSS JOIN sys.all_objects b
    ),
    buckets AS (
        SELECT DATEADD({datepart}, n,     {anchor}) AS bucket_start,
               DATEADD({datepart}, n + 1, {anchor}) AS bucket_end
        FROM tally
    )
    SELECT
        {slot_col}
        fs.floor,
        b.bucket_start,
        SUM(DATEDIFF(
            SECOND,
            CASE WHEN o.seg_start > b.bucket_start THEN o.seg_start ELSE b.bucket_start END,
            CASE WHEN o.seg_end   < b.bucket_end   THEN o.seg_end   ELSE b.bucket_end   END
        )) AS total_occupied_seconds
    FROM occupied o
    JOIN buckets b
        ON o.seg_start < b.bucket_end
       AND o.seg_end   > b.bucket_start
    JOIN floor_slots fs ON fs.slot_id = o.slot_id
    GROUP BY {slot_group} fs.floor, b.bucket_start
    ORDER BY {slot_order} b.bucket_start
    """


def _history_filter(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    grain: str,
    floor: Optional[str],
    floor_id: Optional[int],
) -> tuple[str, dict]:
    """Shared plumbing for the history queries: the floor WHERE-fragment plus
    the bind params (window edges + bucket count for the requested grain).

    WS-8 schema-compat shim — same hybrid floor filter as /slots/by-floor:
    match on the integer key when the row was backfilled, else fall back to the
    legacy string `floor` column."""
    if grain == "hour":
        # Anchor is the floored hour, so count from there to cover a window that
        # starts mid-hour; +1 for the partial bucket at the tail.
        span = end_time - start_time.replace(minute=0, second=0, microsecond=0)
        bucket_count = int(span.total_seconds() // 3600) + 1
    else:
        # Buckets are calendar days, so count from the *dates*, not the
        # instants: a 06:00 → 06:00 window still touches two days.
        bucket_count = (end_time.date() - start_time.date()).days + 1

    params: dict = {
        "start_time": start_time,
        "end_time": end_time,
        "bucket_count": bucket_count,
    }

    schema = _floor_schema()
    resolved_floor_id = resolve_floor_id(db, floor_id=floor_id, floor_name=floor)
    floor_clause = ""
    if resolved_floor_id is not None and schema["parking_slots_floor_id"]:
        floor_name_for_filter = floor or resolve_floor_name(db, resolved_floor_id)
        if floor_name_for_filter:
            floor_clause = (
                "AND (pk.floor_id = :floor_id "
                "OR (pk.floor_id IS NULL AND pk.floor = :floor_name))"
            )
            params["floor_id"] = resolved_floor_id
            params["floor_name"] = floor_name_for_filter
        else:
            floor_clause = "AND pk.floor_id = :floor_id"
            params["floor_id"] = resolved_floor_id
    elif floor:
        floor_clause = "AND pk.floor = :floor"
        params["floor"] = floor
    return floor_clause, params


@router.get("/history/", response_model=list[History])
async def get_slot_history(
    start_time: Annotated[FacilityNaiveDatetime, Query(
        description="Window start, facility-local naive. A `Z` or `+HH:MM` offset "
                    "is accepted and IGNORED — the wall-clock digits are the window.",
    )],
    end_time: Annotated[FacilityNaiveDatetime, Query(
        description="Window end, exclusive. Same offset handling as start_time.",
    )],
    floor: Optional[str] = Query(None, description="Floor name, e.g. B1"),
    floor_id: Optional[int] = Query(None, description="floors.id (WS-8)"),
    db: Session = Depends(get_db),
):
    """Per-slot, per-day occupied seconds over an arbitrary window.

    Time-weighted (Q2): the seconds come from the `slot_status` transition log,
    not from hourly sampling, so a car that arrives and leaves between two hour
    boundaries is still counted. Intervals crossing midnight are split across
    both days.

    Roll-ups the caller derives from this:
      avg occupancy  = SUM(seconds) / (slot_count x window_seconds)
      per-floor      = same, grouped by `floor`, with per-floor denominators
      day-of-week    = mean of the daily averages per weekday (Q5)
    """
    if start_time >= end_time:
        raise HTTPException(status_code=400, detail="start_time must be before end_time")

    floor_clause, params = _history_filter(db, start_time, end_time, "day", floor, floor_id)
    result = rows(db, _occupied_seconds_sql("day", floor_clause), params)

    return [
        History(
            slot_id=r["slot_id"],
            floor=r.get("floor"),
            total_occupied_seconds=int(r["total_occupied_seconds"] or 0),
            date=r["bucket_start"].date(),
        )
        for r in result
    ]


# Display labels for the "Utilization by Location" bars. The DB floor keys are
# terse; the design labels the basements in full. Unknown floors pass through
# unchanged rather than being dropped.
_FLOOR_LABELS = {"Ground": "Ground", "B1": "Basement 1", "B2": "Basement 2"}

_WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


# ── Reports · Tab 1 ───────────────────────────────────────────────────────────
# One endpoint per widget, all under /occupancy/history/ next to the per-slot
# `GET /occupancy/history/` above -- same series, different roll-up, so they
# share a base path:
#   /history/kpis, /history/trend, /history/by-location
# plus /history/summary, a composition of the three for callers that want the
# whole tab in one request.
#
# Splitting them costs three (floor x hour) passes instead of one, and buys:
#   * the KPI row paints without waiting on the charts;
#   * the trend chart re-fetches at a new grain without re-computing the KPIs;
#   * a chart that fails takes down one widget, not the whole tab.
# Every widget still runs the SAME window arithmetic over the SAME query, so
# the figures agree as long as the caller sends identical query params to all
# three — which it must.


@dataclass
class _ReportBase:
    """The shared (floor x hour) pass plus the reporting-window arithmetic that
    every Tab 1 widget needs. Built once per request by `_report_base()`."""
    start_time: datetime
    end_time: datetime
    capacity_by_floor: dict
    total_capacity: int
    buckets: list           # rows of (floor, bucket_start, total_occupied_seconds)
    applied: bool           # business-hours window in force?
    h_from: int
    h_to: int
    days: frozenset         # operating weekday indices
    offered_seconds: float  # garage-wide countable seconds in the window
    day_offered: dict       # date -> countable seconds of that calendar day

    def counted_span(self, hour_start: datetime) -> float:
        """Seconds of this hour bucket that count toward the denominators.

        Zero when the bucket falls outside the operating window — an excluded
        hour is NOT a 0% hour, it is a not-measured hour, so it must leave both
        numerator and denominator rather than dragging the average down.
        Business hours are whole hours, so a bucket is entirely in or entirely
        out; only the request's own edges can clip one."""
        if self.applied and (hour_start.weekday() not in self.days
                             or not (self.h_from <= hour_start.hour < self.h_to)):
            return 0.0
        span = (min(hour_start + timedelta(hours=1), self.end_time)
                - max(hour_start, self.start_time)).total_seconds()
        return max(span, 0.0)

    def window_meta(self) -> dict:
        """The `OccupancyReportWindow` fields, echoed by all three widgets so a
        chart can caption itself instead of hardcoding a window that drifts
        from the deployment's .env."""
        return dict(
            start_time=self.start_time,
            end_time=self.end_time,
            total_capacity=self.total_capacity,
            business_hours_applied=self.applied,
            business_hour_from=self.h_from if self.applied else None,
            business_hour_to=self.h_to if self.applied else None,
            business_days=[_WEEKDAY_NAMES[i] for i in sorted(self.days)],
        )


def _report_base(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    business_hours: Optional[bool],
    hour_from: Optional[int],
    hour_to: Optional[int],
) -> _ReportBase:
    """Validate the range, resolve the reporting window, and run the one
    (floor x hour) occupancy pass the widgets share."""
    if start_time >= end_time:
        raise HTTPException(status_code=400, detail="start_time must be before end_time")

    # ── Reporting window ──────────────────────────────────────────────────────
    # Per-request params win over .env; omitting them uses the configured
    # defaults. Passing hour_from/hour_to alone implies business_hours=true, so
    # a caller can A/B two windows without touching the deployment.
    applied = settings.report_business_hours_enabled if business_hours is None else business_hours
    if hour_from is not None or hour_to is not None:
        applied = True if business_hours is None else business_hours
    h_from = hour_from if hour_from is not None else settings.report_business_hour_from
    h_to = hour_to if hour_to is not None else settings.report_business_hour_to
    if applied and h_from >= h_to:
        raise HTTPException(status_code=400, detail="hour_from must be less than hour_to")
    days = settings.business_weekdays if applied else frozenset(range(7))

    # Denominators: slot counts per floor, and their total. Violation zones and
    # non-parking slot types are excluded, exactly as everywhere else.
    capacity_rows = rows(db, f"""
        SELECT pk.floor, COUNT(*) AS capacity
        FROM parking_slots pk
        WHERE pk.is_violation_zone = 0
          {_slot_type_excl('pk')}
        GROUP BY pk.floor
    """)
    capacity_by_floor = {r["floor"]: int(r["capacity"]) for r in capacity_rows}
    total_capacity = sum(capacity_by_floor.values())

    # No inventory — every ratio would divide by zero. Skip the scan entirely
    # and let each widget return a well-formed empty payload rather than 500ing.
    buckets: list = []
    if total_capacity:
        floor_clause, params = _history_filter(db, start_time, end_time, "hour", None, None)
        buckets = rows(db, _occupied_seconds_sql("hour", floor_clause, by_slot=False), params)

    base = _ReportBase(
        start_time=start_time, end_time=end_time,
        capacity_by_floor=capacity_by_floor, total_capacity=total_capacity,
        buckets=buckets, applied=applied, h_from=h_from, h_to=h_to, days=days,
        offered_seconds=0.0, day_offered={},
    )

    # Every hour bucket in the range, occupied or not — the denominators must
    # include hours where nothing was parked. Walked once here so no widget
    # re-derives it (and gets it subtly different).
    cursor = start_time.replace(minute=0, second=0, microsecond=0)
    while cursor < end_time:
        span = base.counted_span(cursor)
        if span:
            base.offered_seconds += span
            d = cursor.date()
            base.day_offered[d] = base.day_offered.get(d, 0.0) + span
        cursor += timedelta(hours=1)

    return base


def _report_base_dep(
    start_time: Annotated[FacilityNaiveDatetime, Query(
        description="Window start, facility-local naive. A `Z` or `+HH:MM` offset "
                    "is accepted and IGNORED — the wall-clock digits are the window.",
    )],
    end_time: Annotated[FacilityNaiveDatetime, Query(
        description="Window end, exclusive. Same offset handling as start_time.",
    )],
    business_hours: Optional[bool] = Query(
        None,
        description="Restrict percentages to operating hours. Omit to use "
                    "REPORT_BUSINESS_HOURS_ENABLED from .env.",
    ),
    hour_from: Optional[int] = Query(
        None, ge=0, le=23,
        description="Override REPORT_BUSINESS_HOUR_FROM for this request only.",
    ),
    hour_to: Optional[int] = Query(
        None, ge=1, le=24,
        description="Override REPORT_BUSINESS_HOUR_TO (exclusive) for this request only.",
    ),
    db: Session = Depends(get_db),
) -> _ReportBase:
    """Declares the query contract shared by all four Tab 1 endpoints in one
    place, so the widgets cannot drift apart on parameter names, defaults or
    validation — which would silently produce charts that disagree."""
    return _report_base(db, start_time, end_time, business_hours, hour_from, hour_to)


# ── KPI cards ─────────────────────────────────────────────────────────────────

def _report_kpis(base: _ReportBase) -> OccupancyReportKpis:
    if not base.total_capacity:
        return OccupancyReportKpis(
            overall_utilization=0.0, peak_occupancy=0.0, peak_occupancy_at=None,
            parking_captured_pct=100.0, **base.window_meta(),
        )

    # KPI 1 — overall utilization: occupied slot-seconds / (slots x counted time).
    total_seconds = sum(
        int(b["total_occupied_seconds"] or 0)
        for b in base.buckets if base.counted_span(b["bucket_start"])
    )
    overall_utilization = (
        round(total_seconds / (base.total_capacity * base.offered_seconds) * 100, 1)
        if base.offered_seconds else 0.0
    )

    # Honesty check on the number above: what share of all parking that actually
    # happened in this date range falls inside the reporting window. A narrow
    # window flatters utilization precisely by discarding real activity, so the
    # two figures have to be read together.
    all_seconds = sum(int(b["total_occupied_seconds"] or 0) for b in base.buckets)
    parking_captured_pct = round(total_seconds / all_seconds * 100, 1) if all_seconds else 100.0

    # KPI 2 — peak: the hour bucket with the most occupied slot-seconds
    # garage-wide. Each bucket's denominator is its own clamped length, so a
    # partial hour at either window edge is not penalised.
    per_hour: dict = {}
    for b in base.buckets:
        per_hour[b["bucket_start"]] = (
            per_hour.get(b["bucket_start"], 0) + int(b["total_occupied_seconds"] or 0)
        )

    peak_occupancy = 0.0
    peak_occupancy_at: Optional[datetime] = None
    for hour_start, secs in per_hour.items():
        hour_end = hour_start + timedelta(hours=1)
        span = (min(hour_end, base.end_time) - max(hour_start, base.start_time)).total_seconds()
        if span <= 0:
            continue
        pct = secs / (base.total_capacity * span) * 100
        if pct > peak_occupancy:
            peak_occupancy = pct
            peak_occupancy_at = hour_start
    peak_occupancy = round(min(peak_occupancy, 100.0), 1)

    return OccupancyReportKpis(
        overall_utilization=overall_utilization,
        peak_occupancy=peak_occupancy,
        peak_occupancy_at=peak_occupancy_at,
        parking_captured_pct=parking_captured_pct,
        **base.window_meta(),
    )


@router.get("/history/kpis", response_model=OccupancyReportKpis)
async def occupancy_report_kpis(base: _ReportBase = Depends(_report_base_dep)):
    """Report 1 — the three KPI cards only: Overall Utilization, Peak
    Occupancy, Total Capacity.

    Definitions, per the settled decisions:
      * window is the full 24 hours, overnight included (Q1) unless
        `business_hours` narrows it — overnight hours sit near 0%, which pulls
        the averages down; that is intended;
      * occupancy is time-weighted, not hourly-sampled (Q2);
      * `peak_occupancy` is the busiest *hour* of the range, garage-wide.

    Cards NOT returned, deliberately: "Occupied Slots" (Q4) and "Utilization
    Rate" (Q3) were both removed. Screenshot 08 still renders five cards.
    """
    return _report_kpis(base)


# ── Occupancy Trend chart ─────────────────────────────────────────────────────

# A chart with more points than pixels is not a chart. Refusing is better than
# streaming 26k points the FE will silently downsample into a different figure.
_MAX_TREND_POINTS = 2000


def _trend_bucket(grain: OccupancyTrendGrain, hour_start: datetime):
    """Map an hour bucket onto its trend bucket.

    Returns `(sort_key, label, bucket_start, bucket_end)`. The key is always
    orderable, so the caller sorts the dict keys and gets chronological points
    for free."""
    d = hour_start.date()
    if grain is OccupancyTrendGrain.hour:
        return (hour_start, hour_start.strftime("%Y-%m-%d %H:00"),
                hour_start, hour_start + timedelta(hours=1))
    if grain is OccupancyTrendGrain.day:
        start = datetime(d.year, d.month, d.day)
        return d, d.isoformat(), start, start + timedelta(days=1)
    if grain is OccupancyTrendGrain.week:
        # ISO weeks, Monday-anchored — matches the Mon..Sun weekday grain, so
        # switching between the two never re-slices the days differently.
        monday = d - timedelta(days=d.weekday())
        iso_year, iso_week, _ = monday.isocalendar()
        start = datetime(monday.year, monday.month, monday.day)
        return monday, f"{iso_year}-W{iso_week:02d}", start, start + timedelta(days=7)
    if grain is OccupancyTrendGrain.month:
        first = d.replace(day=1)
        # day=1 + 32 days always lands in the next month, whatever its length.
        nxt = (first + timedelta(days=32)).replace(day=1)
        start = datetime(first.year, first.month, 1)
        return first, first.strftime("%Y-%m"), start, datetime(nxt.year, nxt.month, 1)
    raise ValueError(f"unhandled grain {grain}")


def _report_trend(base: _ReportBase, grain: OccupancyTrendGrain) -> list[OccupancyTrendPoint]:
    if grain is OccupancyTrendGrain.weekday:
        return _report_trend_weekday(base)

    if not base.total_capacity:
        return []

    # Denominator grid first: a bucket exists because the range covers it, not
    # because a car happened to park in it. Otherwise a quiet week would vanish
    # from the x-axis instead of reporting 0%.
    offered: dict = {}
    labels: dict = {}
    days_seen: dict = {}
    cursor = base.start_time.replace(minute=0, second=0, microsecond=0)
    while cursor < base.end_time:
        span = base.counted_span(cursor)
        if span:
            key, label, b_start, b_end = _trend_bucket(grain, cursor)
            offered[key] = offered.get(key, 0.0) + span
            labels[key] = (label, b_start, b_end)
            days_seen.setdefault(key, set()).add(cursor.date())
        cursor += timedelta(hours=1)

    if len(offered) > _MAX_TREND_POINTS:
        raise HTTPException(
            status_code=400,
            detail=f"grain '{grain.value}' yields {len(offered)} points for this range "
                   f"(max {_MAX_TREND_POINTS}); pick a coarser grain or a shorter range",
        )

    occupied: dict = {}
    for b in base.buckets:
        hour_start = b["bucket_start"]
        if base.counted_span(hour_start):
            key, _, _, _ = _trend_bucket(grain, hour_start)
            occupied[key] = occupied.get(key, 0) + int(b["total_occupied_seconds"] or 0)

    points = []
    for i, key in enumerate(sorted(offered)):
        label, b_start, b_end = labels[key]
        denom = base.total_capacity * offered[key]
        points.append(OccupancyTrendPoint(
            label=label,
            index=i,
            bucket_start=b_start,
            bucket_end=b_end,
            occupancy=round(occupied.get(key, 0) / denom * 100, 1) if denom else None,
            days_sampled=len(days_seen[key]),
        ))
    return points


def _report_trend_weekday(base: _ReportBase) -> list[OccupancyTrendPoint]:
    """The Mon..Sun grain: 7 bars, each the mean of the daily averages for
    every occurrence of that weekday in the range (Q5).

    Mean-of-daily-averages, not a pooled ratio, so a partial day at a window
    edge still counts as one observation. At a 7-day range each weekday occurs
    once and the two definitions coincide."""
    if not base.total_capacity:
        return [
            OccupancyTrendPoint(label=n, index=i, weekday=n, weekday_index=i,
                                occupancy=None, days_sampled=0)
            for i, n in enumerate(_WEEKDAY_NAMES)
        ]

    # Hours roll up to days, days average per weekday. Each day's denominator
    # is only the part of that day inside the window, so a range that starts at
    # noon doesn't report a half-empty first day.
    per_day: dict = {}
    for b in base.buckets:
        if base.counted_span(b["bucket_start"]):
            d = b["bucket_start"].date()
            per_day[d] = per_day.get(d, 0) + int(b["total_occupied_seconds"] or 0)

    by_weekday: dict = {i: [] for i in range(7)}
    cursor = base.start_time.date()
    while cursor <= (base.end_time - timedelta(microseconds=1)).date():
        # A day outside the operating week contributes no offered seconds, so it
        # is skipped entirely — its weekday bar reports null, not 0%.
        offered = base.day_offered.get(cursor, 0.0)
        if offered > 0:
            by_weekday[cursor.weekday()].append(
                per_day.get(cursor, 0) / (base.total_capacity * offered) * 100
            )
        cursor += timedelta(days=1)

    return [
        OccupancyTrendPoint(
            label=_WEEKDAY_NAMES[i],
            index=i,
            weekday=_WEEKDAY_NAMES[i],
            weekday_index=i,
            # None, not 0.0, when the range never covered this weekday — a
            # zero bar would read as "empty garage" instead of "no data".
            occupancy=round(sum(by_weekday[i]) / len(by_weekday[i]), 1) if by_weekday[i] else None,
            days_sampled=len(by_weekday[i]),
        )
        for i in range(7)
    ]


@router.get("/history/trend", response_model=OccupancyTrendResponse)
async def occupancy_report_trend(
    grain: OccupancyTrendGrain = Query(
        OccupancyTrendGrain.weekday,
        description="X-axis bucketing, chosen by the frontend: hour | day | week "
                    "| month | weekday. `weekday` returns 7 Mon..Sun averages "
                    "and no bucket_start; the rest return a chronological "
                    "series with one point per bucket the range touches.",
    ),
    base: _ReportBase = Depends(_report_base_dep),
):
    """Report 1 — the Occupancy Trend chart alone, at the grain the caller asks
    for. The backend never infers a grain from the range length; the frontend
    knows how much x-axis it has.

    The chart subtitle follows `grain`: "Average occupancy by day of week" for
    `weekday`, "Occupancy over time" for the chronological grains.

    Buckets are emitted for the whole range, not just the ones with parking, so
    a quiet day reports 0% instead of disappearing from the axis. `occupancy`
    is null only when the bucket was never measured — the chart must draw a gap
    there, not a zero-height bar. Time-weighted, not hourly-sampled (Q2).
    """
    return OccupancyTrendResponse(
        grain=grain.value,
        points=_report_trend(base, grain),
        **base.window_meta(),
    )


# ── Utilization by Location chart ─────────────────────────────────────────────

def _report_by_location(base: _ReportBase) -> list[OccupancyLocationItem]:
    if not base.total_capacity:
        return []

    per_floor: dict = {}
    for b in base.buckets:
        if base.counted_span(b["bucket_start"]):
            per_floor[b["floor"]] = per_floor.get(b["floor"], 0) + int(b["total_occupied_seconds"] or 0)

    return [
        OccupancyLocationItem(
            floor=name,
            label=_FLOOR_LABELS.get(name, name),
            capacity=cap,
            utilization=(
                round(per_floor.get(name, 0) / (cap * base.offered_seconds) * 100, 1)
                if cap and base.offered_seconds else 0.0
            ),
        )
        # Floors with no occupancy still get a zero bar — the chart's bar count
        # must not change with the date range.
        for name, cap in sorted(base.capacity_by_floor.items(), key=lambda kv: kv[0] != "Ground")
    ]


@router.get("/history/by-location", response_model=OccupancyLocationResponse)
async def occupancy_report_by_location(base: _ReportBase = Depends(_report_base_dep)):
    """Report 1 — the Utilization by Location bars alone.

    Averaged over the range with PER-FLOOR denominators (Q6) — Ground 8, B1 12,
    B2 15, not 35. This is not the live snapshot that `/occupancy/floors`
    returns, and the two differ whenever the range is not "right now".
    """
    return OccupancyLocationResponse(
        items=_report_by_location(base),
        **base.window_meta(),
    )


# ── Whole-tab composition (legacy) ────────────────────────────────────────────

@router.get("/history/summary", response_model=OccupancyReportSummary, deprecated=True)
async def occupancy_report_summary(base: _ReportBase = Depends(_report_base_dep)):
    """Report 1 — the whole Occupancy & Utilization tab in one call.

    DEPRECATED: superseded by `/history/kpis`, `/history/trend` and
    `/history/by-location`. Kept so existing callers keep working; it is a
    straight composition of the three over one shared `slot_status` pass, so it
    cannot disagree with them.

    Its `trend` is fixed at the `weekday` grain — the split endpoint is the
    only way to ask for a different one.
    """
    kpis = _report_kpis(base)
    return OccupancyReportSummary(
        start_time=base.start_time,
        end_time=base.end_time,
        overall_utilization=kpis.overall_utilization,
        peak_occupancy=kpis.peak_occupancy,
        peak_occupancy_at=kpis.peak_occupancy_at,
        total_capacity=base.total_capacity,
        trend=_report_trend(base, OccupancyTrendGrain.weekday),
        by_location=_report_by_location(base),
        business_hours_applied=base.applied,
        business_hour_from=base.h_from if base.applied else None,
        business_hour_to=base.h_to if base.applied else None,
        business_days=[_WEEKDAY_NAMES[i] for i in sorted(base.days)],
        parking_captured_pct=kpis.parking_captured_pct,
    )
