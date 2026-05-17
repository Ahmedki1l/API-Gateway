from typing import Optional
from io import StringIO
import csv

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db, scalar, rows
from app.routers._helpers import (
    _floor_schema,
    resolve_floor_id,
    resolve_floor_name,
)
from app.schemas import (
    FloorOccupancy,
    FloorSlotGroup,
    OccupancyKPIs,
    OccupancyTotals,
    PagedResponse,
    SlotDetail,
    SlotListItem,
    ZoneItem,
)
from app.schemas_enums import ReservationType, StrictQueryBool
from app.services.snapshots import resolve_snapshot_url
from app.services.upstream import get_live_slots
from app.shared import build_paged


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

router = APIRouter(prefix="/occupancy", tags=["Occupancy"])

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
            ss.plate_number     AS current_plate,
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
            ss.plate_number AS current_plate,
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
    slice_ = floor_rows[start:start + page_size]
    # WS-8: pass floor_id (integer) so _build_floor_occupancy uses the indexed FK directly.
    items = [_build_floor_occupancy(db, floor=f["name"], floor_id=f.get("id")) for f in slice_]
    return build_paged(items, total, page, page_size)


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
            ss.plate_number     AS current_plate,
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
            ss.plate_number     AS current_plate,
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