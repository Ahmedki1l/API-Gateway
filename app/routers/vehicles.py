from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import facility_now_naive, facility_today_utc, localize_naive
from app.database import get_db, scalar, rows
from app.routers._helpers import _floor_schema, resolve_floor_id
from app.routers.alerts import (
    _alert_query_bits,
    _alerts_extra_cols,
    _where as _alert_where,
    alert_item_fixup,
    alert_items_sql,
)
from app.routers.entry_exit import (
    IS_EMPLOYEE_EXPR,
    OWNER_NAME_EXPR,
    VEHICLE_JOIN,
    VEHICLE_TYPE_EXPR,
    _event_from_row as _session_event,
    _live_duration_seconds,
)
from app.routers.occupancy import currently_parked_count
from app.services.alert_auto_resolve import auto_resolve_alerts_for_vehicle
from app.services.snapshots import resolve_snapshot_url
from app.schemas import (
    AlertItem,
    EntityActionResponse,
    EntryExitEvent,
    GateRead,
    HistorySection,
    PagedResponse,
    SlotSighting,
    VehicleCreate,
    VehicleDetail,
    VehicleEvent,
    VehicleItem,
    VehicleKPIs,
    VehicleListItem,
    VehicleHistory,
    VehicleHistoryCurrent,
    VehicleHistorySummary,
    VehicleRef,
    VehicleTimelineItem,
    VehicleUpdate,
)
from app.schemas_enums import AlertSeverity, EntryExitDirection, ParkingSessionStatus, SortDir, VehicleSort
from app.shared import (
    build_paged,
    normalize_plate_term,
    order_by_nulls_last,
    plate_display_sort_expr,
    plate_exact_forms,
    plate_in_clause,
    plate_search_clause,
    stream_csv,
)

from app.routers.prefix_injection import (get_prefix)
prefix = get_prefix() + "/vehicles"

router = APIRouter(prefix=prefix, tags=["Vehicles"])

_UNREGISTERED_NOTE_MARKER = "Not registered"


def _is_overstay(status: Optional[str], entry_time) -> bool:
    """A still-open (or already-flagged-overstay) session whose entry predates
    facility-local midnight today is overstaying. Single source of truth shared
    by the list builder, the write-response builder, the detail builder, and
    `_event_from_row` so the Vehicles tab and Entry/Exit tab agree on the flag.
    Mirrors entry_exit.py:_event_from_row."""
    if status not in ("open", "overstay") or entry_time is None:
        return False
    return entry_time < facility_today_utc().replace(tzinfo=None)


def _split_vehicle_note_parts(note: Optional[str]) -> list[str]:
    if note is None:
        return []
    return [
        part.strip()
        for part in note.split(",")
        if part.strip() and part.strip() != _UNREGISTERED_NOTE_MARKER
    ]


def _merge_vehicle_notes(existing_note: Optional[str], incoming_note: Optional[str]) -> Optional[str]:
    merged: list[str] = []
    seen: set[str] = set()

    for part in [*_split_vehicle_note_parts(existing_note), *_split_vehicle_note_parts(incoming_note)]:
        key = part.casefold()
        if key in seen:
            continue
        seen.add(key)
        merged.append(part)

    return ", ".join(merged) if merged else None


def _fetch_vehicle_list_item(db: Session, vehicle_id: int) -> Optional[dict]:
    """Re-fetch a vehicle by id in the same shape /vehicles/ list rows have.
    Used by POST/PUT to return the canonical `VehicleListItem` after a write
    instead of a raw SELECT * dict (which has a different field set)."""
    cols = _vehicle_extra_cols(db)
    schema = _floor_schema()
    extra = (
        (", v.is_employee" if cols["is_employee"] else ", NULL AS is_employee") +
        (", v.phone"       if cols["phone"]       else ", NULL AS phone")       +
        (", v.email"       if cols["email"]       else ", NULL AS email")
    )
    # WS-8.E: subquery grabs floor_id alongside floor; outer SELECT surfaces it.
    # Pre-WS-8 DB tolerance: when ps.floor_id doesn't exist yet, emit NULL.
    ps_floor_id_col   = "floor_id" if schema["parking_sessions_floor_id"] else "NULL AS floor_id"
    ps_outer_floor_id = "ps.floor_id" if schema["parking_sessions_floor_id"] else "NULL"
    # Prefer v.floor / v.floor_id (the canonical "where is the car right
    # now" answer) and fall back to the parking_sessions JOIN for legacy
    # DBs without the new vehicles columns.
    floor_expr = "COALESCE(v.floor, ps.floor)" if cols["v_floor"] else "ps.floor"
    floor_id_expr = (
        f"COALESCE(v.floor_id, {ps_outer_floor_id})"
        if cols["v_floor_id"] else f"{ps_outer_floor_id}"
    )
    result = rows(db, f"""
        SELECT
            v.id,
            v.plate_number,
            v.owner_name,
            v.vehicle_type,
            v.employee_id,
            v.title,
            CAST(v.is_registered AS BIT) AS is_registered,
            v.registered_at,
            v.notes
            {extra},
            ps.parked_at,
            ps.status      AS parking_status,
            ps.entry_time,
            {floor_expr}    AS floor,
            {floor_id_expr} AS floor_id
        FROM vehicles v
        LEFT JOIN (
            SELECT
                plate_number,
                parked_at,
                status,
                entry_time,
                floor,
                {ps_floor_id_col},
                ROW_NUMBER() OVER (PARTITION BY plate_number ORDER BY entry_time DESC) AS rn
            FROM parking_sessions
            WHERE status = 'open'
        ) ps ON ps.plate_number = v.plate_number AND ps.rn = 1
        WHERE v.id = :id
    """, {"id": vehicle_id})
    if not result:
        return None
    row = result[0]
    row["is_overstay"] = _is_overstay(row.get("parking_status"), row.get("entry_time"))
    return row


def _vehicle_extra_cols(db: Session) -> dict:
    """Check which post-migration columns exist — in Python, never in SQL."""
    def exists(col):
        n = scalar(db, """
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'vehicles' AND COLUMN_NAME = :c
        """, {"c": col})
        return (n or 0) > 0
    return {
        "is_employee":     exists("is_employee"),
        "phone":           exists("phone"),
        "email":           exists("email"),
        # current_slot_id is added by PMS-AI's alembic migration
        # c1d2e3f4a5b6_vehicles_add_current_slot_id; keep an INFORMATION_SCHEMA
        # probe so the Gateway tolerates DBs where that migration hasn't run.
        "current_slot_id": exists("current_slot_id"),
        # vehicles.floor / floor_id added by migrate_vehicles_add_floor_last_seen.sql.
        # VA writes them on every track confirmation; PMS-AI bind_slot/close_session
        # keep them synced. Probe so older DBs without the migration still serve responses.
        "v_floor":         exists("floor"),
        "v_floor_id":      exists("floor_id"),
    }


def _event_from_row(
    r: dict,
    plate_number: str,
    vehicle_id: Optional[int],
    *,
    owner_name: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    is_employee: Optional[bool] = None,
) -> VehicleEvent:
    """Build a VehicleEvent (with nested entry + optional exit EntryExitEvents)
    from a parking_sessions row. `direction` is implicit — entry always exists,
    exit is populated when exit_time is not null. Vehicle-level fields are
    passed in by the caller (denormalized so /vehicles/{id} events match the
    shape served by /entry-exit/)."""
    is_overstay = _is_overstay(r.get("status"), r.get("entry_time"))
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
    return VehicleEvent(
        id=r["id"],
        vehicle_id=vehicle_id,
        plate_number=plate_number,
        owner_name=owner_name,
        vehicle_type=vehicle_type,
        is_employee=is_employee,
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
        parked_at=r.get("parked_at"),
        slot_left_at=r.get("slot_left_at"),
        slot_camera_id=r.get("slot_camera_id"),
        slot_snapshot_url=resolve_snapshot_url(r.get("slot_snapshot_path")),
    )


# ── POST /vehicles ────────────────────────────────────────────────────────────
@router.post("/", response_model=VehicleListItem, status_code=201)
async def create_vehicle(
    body: VehicleCreate,
    response: Response,
    db: Session = Depends(get_db),
):
    existing_vehicle = rows(
        db,
        """
        SELECT TOP 1 id, notes
        FROM vehicles
        WHERE plate_number = :plate
        ORDER BY id
        """,
        {"plate": body.plate_number},
    )

    is_registered_int = 1 if body.is_registered else 0

    vehicle_id: Optional[int] = None
    if existing_vehicle:
        vehicle_id = existing_vehicle[0]["id"]
        merged_notes = _merge_vehicle_notes(existing_vehicle[0].get("notes"), body.notes)

        # Stamp registered_at only when the caller is registering the plate; on an
        # explicit unregister, preserve the historical "first registered at" timestamp.
        registered_at_set = ", registered_at = GETDATE()" if body.is_registered else ""

        db.execute(text(f"""
            UPDATE vehicles
            SET owner_name = :owner,
                employee_id = :emp_id,
                vehicle_type = :vtype,
                title = COALESCE(:title, title),
                is_employee = :is_employee,
                phone = :phone,
                email = :email,
                notes = :notes,
                is_registered = :is_registered{registered_at_set}
            WHERE id = :vehicle_id
        """), {
            "vehicle_id": vehicle_id,
            "owner": body.owner_name,
            "emp_id": body.employee_id,
            "vtype": body.vehicle_type,
            "title": body.title,
            "is_employee": body.is_employee,
            "phone": body.phone,
            "email": body.email,
            "notes": merged_notes,
            "is_registered": is_registered_int,
        })
        response.status_code = status.HTTP_200_OK
    else:
        db.execute(text("""
            INSERT INTO vehicles
                (plate_number, owner_name, employee_id, vehicle_type, title, is_employee, phone, email, notes, is_registered, registered_at)
            VALUES
                (:plate, :owner, :emp_id, :vtype, COALESCE(:title, ''), :is_employee, :phone, :email, :notes,
                 :is_registered,
                 CASE WHEN :is_registered = 1 THEN GETDATE() ELSE NULL END)
        """), {
            "plate":  body.plate_number,
            "owner":  body.owner_name,
            "emp_id": body.employee_id,
            "vtype":  body.vehicle_type,
            "title":  body.title,
            "is_employee": body.is_employee,
            "phone":  body.phone,
            "email":  body.email,
            "notes":  body.notes,
            "is_registered": is_registered_int,
        })
        response.status_code = status.HTTP_201_CREATED
    db.commit()

    if vehicle_id is None:
        vehicle_id = scalar(db, "SELECT id FROM vehicles WHERE plate_number = :p", {"p": body.plate_number})
    if vehicle_id is None:
        # Should never happen — INSERT just succeeded — but raise a clean error.
        raise HTTPException(500, "Vehicle saved but could not be re-read")
    item = _fetch_vehicle_list_item(db, vehicle_id)
    if item is None:
        raise HTTPException(500, "Vehicle saved but could not be re-read")
    # A newly-registered / newly-titled plate can clear alerts raised before
    # the registry knew about it — see services/alert_auto_resolve.py.
    item["auto_resolved_alert_ids"] = auto_resolve_alerts_for_vehicle(db, body.plate_number)
    return item


# ── GET /vehicles/kpis ────────────────────────────────────────────────────────
@router.get("/kpis", response_model=VehicleKPIs)
async def vehicle_kpis(db: Session = Depends(get_db)):
    cols = _vehicle_extra_cols(db)

    employee = (
        scalar(db, "SELECT COUNT(*) FROM vehicles WHERE is_employee = 1") or 0
    ) if cols["is_employee"] else 0

    registered = scalar(db, """
        SELECT COUNT(*) FROM vehicles
        WHERE is_registered = 1
          AND (is_employee = 0 OR is_employee IS NULL)
    """) or 0 if cols["is_employee"] else (
        scalar(db, "SELECT COUNT(*) FROM vehicles WHERE is_registered = 1") or 0
    )

    unregistered = scalar(db, """
        SELECT COUNT(*) FROM vehicles
        WHERE (is_registered = 0 OR is_registered IS NULL)
          AND (is_employee = 0 OR is_employee IS NULL)
    """) or 0 if cols["is_employee"] else (
        scalar(db, "SELECT COUNT(*) FROM vehicles WHERE is_registered = 0 OR is_registered IS NULL") or 0
    )

    total = registered + unregistered + employee

    # Same helper as /dashboard/kpis, so the two screens never disagree.
    currently_parked = currently_parked_count(db)
    floors_count = scalar(db, "SELECT COUNT(*) FROM floors WHERE is_active = 1") or 0

    return VehicleKPIs(
        total_vehicles=total,
        unregistered=unregistered,
        registered=registered,
        employee=employee,
        currently_parked=currently_parked,
        floors_count=floors_count,
    )


# ── GET /vehicles ─────────────────────────────────────────────────────────────
def _vehicle_order(sort_by: VehicleSort, sort_dir: SortDir, *,
                   plate: str, vehicle_type: str, floor: str) -> str:
    """ORDER BY body for the Vehicles list and CSV, whose queries alias the
    plate / type / floor differently. Only these fixed expressions ever reach
    ORDER BY. The plate breaks ties (one registry row per plate) so paging is
    stable."""
    keys = {
        VehicleSort.plate: plate_display_sort_expr(plate),
        # The table shows "Unregistered" instead of a name, so those go last.
        VehicleSort.owner: "CASE WHEN COALESCE(v.is_registered, 0) = 1 "
                           "THEN NULLIF(LTRIM(RTRIM(v.owner_name)), '') END",
        VehicleSort.vehicle_type: f"NULLIF({vehicle_type}, 'unknown')",
        VehicleSort.floor: floor,
        VehicleSort.status: "CASE WHEN COALESCE(v.is_registered, 0) = 1 THEN 0 ELSE 1 END",
        VehicleSort.registered_at: "v.registered_at",
        VehicleSort.parked_at: "ps.parked_at",
    }
    return order_by_nulls_last(keys[sort_by], sort_dir.value.upper(), plate)


_VEHICLE_SORT_DOC = ("Column to sort by, applied before paging: plate (as displayed, "
                     "digits first) | owner (unregistered last) | vehicle_type | floor | "
                     "status (asc: registered first) | registered_at | parked_at. Empty "
                     "values sort last either way. Omit for parked cars first, newest "
                     "registration next.")
_SORT_DIR_DOC = "asc | desc (default). Ignored without sort_by."


@router.get("/", response_model=PagedResponse[VehicleItem])
async def get_vehicles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="plate, owner name, or title"),
    is_employee: Optional[bool] = Query(None),
    vehicle_type: Optional[str] = Query(None),
    title: Optional[str] = Query(None, description="exact-match filter on vehicle title"),
    is_registered: Optional[bool] = Query(
        None,
        description=(
            "true  → only plates an operator registered\n"
            "false → only plates PMS-AI auto-created on first sighting\n"
            "null  → all plates"
        ),
    ),
    is_currently_parked: Optional[bool] = Query(
        None,
        description=(
            "true  → only plates with an open parking_sessions row right now\n"
            "false → only plates NOT currently parked\n"
            "null  → all plates (default)"
        ),
    ),
    sort_by: Optional[VehicleSort] = Query(None, description=_VEHICLE_SORT_DOC),
    sort_dir: SortDir = Query(SortDir.desc, description=_SORT_DIR_DOC),
    db: Session = Depends(get_db),
):
    """Registry view: one row per plate in the `vehicles` table, enriched with
    its current parking session when it has one.

    Every row therefore carries a real `id` — which is what DELETE and PUT
    need, and why this list never emits `id = null`. (`VehicleRef.id` stays
    Optional: other endpoints build vehicle-shaped payloads for plates that
    have no registry row.)

    Registered and unregistered plates both appear. PMS-AI writes an
    `is_registered = 0` placeholder for every unknown plate it sees, so an
    unregistered car is an ordinary registry row, not a session-only ghost.
    `?is_currently_parked=true` still matches every "active now" plate for the
    same reason: a car cannot hold an open session without PMS-AI having put it
    in `vehicles` first, so this count does not fall behind the
    active-vehicles count the way the pre-UNION version did.

    Deleting a vehicle removes it from this list for good while leaving its
    Entry/Exit and parking-session history untouched — see delete_vehicle.
    """
    cols    = _vehicle_extra_cols(db)
    schema  = _floor_schema()
    clauses = ["1=1"]
    params: dict = {}

    if search:
        # Plate matches dash/space- AND order-insensitively (the full "4918-AVD"
        # as displayed finds the stored "AVD-4918"); owner/title match raw term.
        plate_clause = plate_search_clause("ap.plate_number", search, params)
        clauses.append(f"({plate_clause} OR v.owner_name LIKE :search OR v.title LIKE :search)")
        params["search"] = f"%{search}%"
    if vehicle_type:
        clauses.append("COALESCE(v.vehicle_type, ps.vehicle_type) = :vehicle_type")
        params["vehicle_type"] = vehicle_type
    if title:
        clauses.append("v.title = :title")
        params["title"] = title
    if is_registered is True:
        clauses.append("v.is_registered = 1")
    elif is_registered is False:
        clauses.append("(v.id IS NULL OR v.is_registered = 0)")
    if is_employee is not None and cols["is_employee"]:
        # Filter on the registry's flag when present; falls back to the session row.
        clauses.append("COALESCE(v.is_employee, ps.is_employee) = :is_employee")
        params["is_employee"] = 1 if is_employee else 0
    if is_currently_parked is True:
        # Match plates with any open parking_sessions row (ps subquery already filters status='open');
        # parked_at can be NULL until VA assigns a slot, so we key on plate_number to match /dashboard/kpis.active_now.
        clauses.append("ps.plate_number IS NOT NULL")
    elif is_currently_parked is False:
        clauses.append("ps.parked_at IS NULL")

    where = " AND ".join(clauses)

    # CTE: the registry, and only the registry.
    #
    # This used to be `dbo.vehicles UNION dbo.parking_sessions.plate_number`, so
    # a plate with parking history but no registry row still appeared, with
    # `id = null`. That made DELETE /vehicles/{id} unable to do its job: the
    # endpoint drops the `vehicles` row and deliberately keeps the history, so a
    # deleted plate came straight back through the parking_sessions half — on
    # screen, with a null id, which the frontend then re-submitted as
    # `DELETE /vehicles/null` (a 422). Deleting a car has to make it disappear.
    #
    # Dropping that half costs nothing on a current database. PMS-AI's
    # `vehicle_service.ensure_unregistered_vehicle()` runs on every entry path
    # and creates a registry row for any plate it does not recognise, so a car
    # that parks is already in `vehicles` by the time it has a session. The only
    # plates the UNION contributed on its own were therefore the deleted ones,
    # plus any rows predating that logic — and those stay readable on the
    # Entry/Exit tab, which reads parking_sessions directly.
    all_plates_cte = """
        WITH all_plates AS (
            SELECT plate_number FROM dbo.vehicles
        )
    """

    # WS-8.E: floor_id added to the subquery so the outer SELECT can surface it.
    # Pre-WS-8 DB tolerance: when ps.floor_id doesn't exist yet, emit NULL.
    ps_floor_id_col   = "floor_id" if schema["parking_sessions_floor_id"] else "NULL AS floor_id"
    ps_outer_floor_id = "ps.floor_id" if schema["parking_sessions_floor_id"] else "NULL"

    # current_slot_id is added by PMS-AI's alembic migration; the JOIN to
    # parking_slots lets us surface a human-readable slot name without an
    # extra round-trip. When the column doesn't exist, emit NULL and skip the JOIN.
    if cols["current_slot_id"]:
        slot_join   = "LEFT JOIN dbo.parking_slots cs ON cs.slot_id = v.current_slot_id"
        slot_select = "v.current_slot_id, cs.slot_name AS current_slot_name"
    else:
        slot_join   = ""
        slot_select = "NULL AS current_slot_id, NULL AS current_slot_name"

    # Shared FROM/JOIN — used by both COUNT and SELECT so they stay consistent.
    # The `ps` subquery pulls the latest open parking_sessions row per plate
    # plus the columns needed to build a `VehicleEvent` for `current_event`.
    base_from = f"""
        FROM all_plates ap
        LEFT JOIN dbo.vehicles v ON v.plate_number = ap.plate_number
        LEFT JOIN (
            SELECT
                id,
                plate_number,
                parked_at,
                status,
                floor,
                {ps_floor_id_col},
                vehicle_type,
                is_employee,
                entry_time,
                exit_time,
                slot_id,
                slot_number,
                slot_left_at,
                entry_camera_id,
                exit_camera_id,
                entry_snapshot_path,
                exit_snapshot_path,
                slot_camera_id,
                slot_snapshot_path,
                duration_seconds,
                ROW_NUMBER() OVER (PARTITION BY plate_number ORDER BY entry_time DESC) AS rn
            FROM dbo.parking_sessions
            WHERE status = 'open'
        ) ps ON ps.plate_number = ap.plate_number AND ps.rn = 1
        LEFT JOIN dbo.parking_slots pk ON pk.slot_id = ps.slot_id
        {slot_join}
    """

    total = scalar(
        db,
        f"{all_plates_cte} SELECT COUNT(*) {base_from} WHERE {where}",
        params,
    )

    params["offset"]    = (page - 1) * page_size
    params["page_size"] = page_size

    extra = (
        (", v.is_employee" if cols["is_employee"] else ", NULL AS is_employee") +
        (", v.phone"       if cols["phone"]       else ", NULL AS phone")       +
        (", v.email"       if cols["email"]       else ", NULL AS email")
    )

    # `floor` / `floor_id` are now real columns on `vehicles`
    # (migrate_vehicles_add_floor_last_seen.sql). VA writes them on every
    # track confirmation; PMS-AI bind/close keep them synced. We prefer
    # v.* (the canonical "where is the car right now" answer) and fall
    # back to the parking_sessions JOIN only when v.* is missing — covers
    # legacy DBs and rows VA hasn't observed yet.
    floor_expr = "COALESCE(v.floor, ps.floor)" if cols["v_floor"] else "ps.floor"
    floor_id_expr = (
        f"COALESCE(v.floor_id, {ps_outer_floor_id})"
        if cols["v_floor_id"] else f"{ps_outer_floor_id}"
    )

    order_by = (
        "CASE WHEN ps.parked_at IS NOT NULL THEN 0 ELSE 1 END, ps.parked_at DESC, "
        "v.registered_at DESC, ap.plate_number"
        if sort_by is None else
        _vehicle_order(sort_by, sort_dir, plate="ap.plate_number",
                       vehicle_type="COALESCE(v.vehicle_type, ps.vehicle_type)", floor=floor_expr)
    )

    items = rows(db, f"""
        {all_plates_cte}
        SELECT
            v.id,
            ap.plate_number,
            v.owner_name,
            COALESCE(v.vehicle_type, ps.vehicle_type) AS vehicle_type,
            v.employee_id,
            v.title,
            CAST(COALESCE(v.is_registered, 0) AS BIT) AS is_registered,
            v.registered_at,
            v.notes
            {extra},
            ps.parked_at,
            ps.status      AS parking_status,
            {floor_expr}   AS floor,
            {floor_id_expr} AS floor_id,
            {slot_select},
            ps.id          AS session_id,
            ps.entry_time,
            ps.exit_time,
            ps.slot_id,
            COALESCE(pk.slot_name, ps.slot_number) AS slot_name,
            ps.slot_number,
            ps.slot_left_at,
            ps.entry_camera_id,
            ps.exit_camera_id,
            ps.entry_snapshot_path,
            ps.exit_snapshot_path,
            ps.slot_camera_id,
            ps.slot_snapshot_path,
            ps.duration_seconds
        {base_from}
        WHERE {where}
        ORDER BY {order_by}
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)

    # Build `current_event: VehicleEvent` per row when an open parking_sessions
    # row exists. Reshape keys: `_event_from_row` expects the session id under
    # "id" and the session status under "status"; the outer SELECT aliases them
    # as `session_id` and `parking_status` to avoid colliding with the vehicle PK.
    # When the car has been unbound from its slot but is still in the garage
    # (slot_left_at IS NOT NULL, session still open), the session row retains
    # slot_id as a historical record. For the API contract — current_event
    # describes where the car *currently* is — we blank out slot fields in
    # that window so they match `vehicle.current_slot_id` (which PMS-AI's
    # unbind clears on the vehicles row).
    for r in items:
        if r.get("session_id") and r.get("parking_status") == "open":
            slot_left = r.get("slot_left_at") is not None
            event_row = {
                "id":                  r["session_id"],
                "status":              r.get("parking_status"),
                "entry_time":          r.get("entry_time"),
                "exit_time":           r.get("exit_time"),
                "entry_camera_id":     r.get("entry_camera_id"),
                "exit_camera_id":      r.get("exit_camera_id"),
                "entry_snapshot_path": r.get("entry_snapshot_path"),
                "exit_snapshot_path":  r.get("exit_snapshot_path"),
                "slot_id":             None if slot_left else r.get("slot_id"),
                "slot_name":           None if slot_left else r.get("slot_name"),
                "slot_number":         None if slot_left else r.get("slot_number"),
                "floor":               None if slot_left else r.get("floor"),
                "floor_id":            None if slot_left else r.get("floor_id"),
                "parked_at":           r.get("parked_at"),
                "slot_left_at":        r.get("slot_left_at"),
                "slot_camera_id":      r.get("slot_camera_id"),
                "slot_snapshot_path":  r.get("slot_snapshot_path"),
                "duration_seconds":    r.get("duration_seconds"),
            }
            r["current_event"] = _event_from_row(
                event_row,
                plate_number=r["plate_number"],
                vehicle_id=r.get("id"),
                owner_name=r.get("owner_name"),
                vehicle_type=r.get("vehicle_type"),
                is_employee=bool(r["is_employee"]) if r.get("is_employee") is not None else None,
            )
        else:
            r["current_event"] = None
        # Surface the overstay flag at the row level (mirrors current_event) so
        # the Vehicles tab can render the red overstay indicator like Entry/Exit.
        r["is_overstay"] = r["current_event"].is_overstay if r["current_event"] else False

    return build_paged(items, total or 0, page, page_size)


# ── PUT /vehicles/{vehicle_id} ────────────────────────────────────────────────
@router.put("/{vehicle_id}", response_model=VehicleListItem)
async def update_vehicle(
    vehicle_id: int,
    body: VehicleUpdate,
    db: Session = Depends(get_db),
):
    cols    = _vehicle_extra_cols(db)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields provided to update")

    post_migration = {"is_employee", "phone", "email"}
    safe_updates = {
        k: v for k, v in updates.items()
        if k not in post_migration or cols.get(k)
    }

    if not safe_updates:
        raise HTTPException(400, "No applicable fields — run System 1 migration first")

    # plate uniqueness check BEFORE the update
    if "plate_number" in safe_updates:
        conflict = scalar(db,
            "SELECT COUNT(*) FROM vehicles WHERE plate_number = :p AND id != :id",
            {"p": safe_updates["plate_number"], "id": vehicle_id})
        if conflict:
            raise HTTPException(400,
                f"Plate '{safe_updates['plate_number']}' is already registered to another vehicle")

    # Promotion (false/null → true): strip the "Not registered" marker from notes
    # and stamp registered_at. Read current state so a true → true edit doesn't
    # reset registered_at; the cleanup only runs on an actual transition.
    stamp_registered_at = False
    if safe_updates.get("is_registered") is True:
        current = rows(
            db,
            "SELECT is_registered, notes FROM vehicles WHERE id = :id",
            {"id": vehicle_id},
        )
        if not current:
            raise HTTPException(404, "Vehicle not found")
        if not current[0].get("is_registered"):
            base_notes = safe_updates.get("notes", current[0].get("notes"))
            safe_updates["notes"] = _merge_vehicle_notes(None, base_notes)
            stamp_registered_at = True

    if "is_registered" in safe_updates:
        safe_updates["is_registered"] = 1 if safe_updates["is_registered"] else 0

    set_parts = [f"{k} = :{k}" for k in safe_updates]
    if stamp_registered_at:
        set_parts.append("registered_at = GETDATE()")
    safe_updates["vehicle_id"] = vehicle_id

    result = db.execute(
        text(f"UPDATE vehicles SET {', '.join(set_parts)} WHERE id = :vehicle_id"),
        safe_updates,
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "Vehicle not found")

    item = _fetch_vehicle_list_item(db, vehicle_id)
    if item is None:
        raise HTTPException(500, "Vehicle updated but could not be re-read")
    # Re-evaluate this plate's open violations against the edited registry row:
    # setting `title = 'CEO'` on the car parked in a CEO slot clears the alert.
    item["auto_resolved_alert_ids"] = auto_resolve_alerts_for_vehicle(db, item["plate_number"])
    return item


# ── DELETE /vehicles/{vehicle_id} ──────────────────────────────────────────────
@router.delete("/{vehicle_id}", response_model=EntityActionResponse)
async def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
):
    """Delete a vehicle from the registry, keeping its Entry/Exit history.

    History is *detached*, never cascaded. Rows in `parking_sessions` and
    `entry_exit_log` are keyed on `plate_number` (NOT NULL in both) and carry
    `vehicle_id` only as a nullable convenience link, so setting that link to
    NULL satisfies the ON DELETE NO ACTION foreign keys without dropping a
    single event. An earlier implementation cascade-deleted the history along
    with the car; that is what this must not do.

    The detached rows stay readable: `dashboard.py` and `entry_exit.py` both
    LEFT JOIN vehicles on `plate_number` whenever `vehicle_id IS NULL`. Past
    events lose their owner name/title while no vehicle row exists for the
    plate, and pick it back up automatically if the plate is ever re-registered.
    """
    # Existence check up front, so a bad id 404s before any UPDATE runs.
    exists = scalar(db, "SELECT COUNT(*) FROM vehicles WHERE id = :vid", {"vid": vehicle_id})
    if not exists:
        raise HTTPException(404, "Vehicle not found")

    # Detach history, don't delete it.
    db.execute(
        text("UPDATE parking_sessions SET vehicle_id = NULL WHERE vehicle_id = :vid"),
        {"vid": vehicle_id},
    )
    db.execute(
        text("UPDATE entry_exit_log SET vehicle_id = NULL WHERE vehicle_id = :vid"),
        {"vid": vehicle_id},
    )

    # Unlink any alerts that referenced it so the alert rows survive too.
    has_alerts_vehicle_id = (scalar(db, """
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'alerts' AND COLUMN_NAME = 'vehicle_id'
    """) or 0) > 0
    if has_alerts_vehicle_id:
        db.execute(
            text("UPDATE alerts SET vehicle_id = NULL WHERE vehicle_id = :vid"),
            {"vid": vehicle_id},
        )

    result = db.execute(
        text("DELETE FROM vehicles WHERE id = :vid"),
        {"vid": vehicle_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Vehicle not found")
    return EntityActionResponse(id=vehicle_id)


# ── GET /vehicles/export/csv ──────────────────────────────────────────────────
@router.get("/export/csv")
async def export_vehicles_csv(
    search: Optional[str] = Query(None),
    vehicle_type: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
    is_registered: Optional[bool] = Query(None),
    is_employee: Optional[bool] = Query(None),
    is_currently_parked: Optional[bool] = Query(None),
    sort_by: Optional[VehicleSort] = Query(None, description=_VEHICLE_SORT_DOC),
    sort_dir: SortDir = Query(SortDir.desc, description=_SORT_DIR_DOC),
    db: Session = Depends(get_db),
):
    """CSV export of vehicles. Filter set matches `GET /vehicles/` so the CSV
    download mirrors what's on screen."""
    cols = _vehicle_extra_cols(db)
    clauses = ["1=1"]
    params: dict = {}
    if search:
        plate_clause = plate_search_clause("v.plate_number", search, params)
        clauses.append(f"({plate_clause} OR v.owner_name LIKE :search OR v.title LIKE :search)")
        params["search"] = f"%{search}%"
    if vehicle_type:
        clauses.append("v.vehicle_type = :vehicle_type")
        params["vehicle_type"] = vehicle_type
    if title:
        clauses.append("v.title = :title")
        params["title"] = title
    if is_registered is not None:
        clauses.append("v.is_registered = :is_registered")
        params["is_registered"] = 1 if is_registered else 0
    if is_employee is not None and cols["is_employee"]:
        clauses.append("v.is_employee = :is_employee")
        params["is_employee"] = 1 if is_employee else 0
    if is_currently_parked is True:
        clauses.append("ps.parked_at IS NOT NULL")
    elif is_currently_parked is False:
        clauses.append("ps.parked_at IS NULL")

    is_emp_col = "v.is_employee" if cols["is_employee"] else "NULL"

    if cols["current_slot_id"]:
        slot_join_csv   = "LEFT JOIN parking_slots cs ON cs.slot_id = v.current_slot_id"
        slot_select_csv = "v.current_slot_id  AS [Current Slot ID], cs.slot_name AS [Current Slot Name]"
    else:
        slot_join_csv   = ""
        slot_select_csv = "NULL AS [Current Slot ID], NULL AS [Current Slot Name]"

    order_by = (
        "v.registered_at DESC" if sort_by is None else
        _vehicle_order(sort_by, sort_dir, plate="v.plate_number",
                       vehicle_type="v.vehicle_type", floor="ps.floor")
    )

    data = rows(db, f"""
        SELECT
            v.plate_number  AS [Plate Number],
            v.owner_name    AS [Owner Name],
            v.vehicle_type  AS [Vehicle Type],
            v.employee_id   AS [Employee ID],
            v.title         AS [Title],
            v.is_registered AS [Registered],
            {is_emp_col}    AS [Is Employee],
            v.registered_at AS [Registered At],
            CASE WHEN ps.parked_at IS NOT NULL THEN 1 ELSE 0 END AS [Currently Parked],
            ps.parked_at    AS [Parked At],
            ps.floor        AS [Floor],
            {slot_select_csv},
            v.notes         AS [Notes]
        FROM vehicles v
        LEFT JOIN (
            SELECT
                plate_number,
                parked_at,
                floor,
                ROW_NUMBER() OVER (PARTITION BY plate_number ORDER BY entry_time DESC) AS rn
            FROM parking_sessions
            WHERE status = 'open'
        ) ps ON ps.plate_number = v.plate_number AND ps.rn = 1
        {slot_join_csv}
        WHERE {" AND ".join(clauses)}
        ORDER BY {order_by}
    """, params)

    headers = ["Plate Number", "Owner Name", "Vehicle Type", "Employee ID",
               "Title", "Registered", "Is Employee", "Registered At",
               "Currently Parked", "Parked At", "Floor",
               "Current Slot ID", "Current Slot Name", "Notes"]
    return stream_csv(data, headers, filename="vehicles.csv")


def _fetch_vehicle_events(
    db: Session,
    plate: str,
    vehicle_pk: Optional[int],
    *,
    owner_name: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    is_employee: Optional[bool] = None,
) -> tuple[int, list[VehicleEvent]]:
    """Pull a plate's parking-event history (bounded TOP 500) and return
    `(events_total, events)`. Shared by registered and unregistered plate
    lookups so the event shape is identical in both cases.
    """
    schema = _floor_schema()
    events_total = scalar(
        db,
        "SELECT COUNT(*) FROM parking_sessions ps WHERE ps.plate_number = :plate",
        {"plate": plate},
    ) or 0

    # Bounded fetch — TOP 500 to avoid runaway responses on a high-volume plate.
    # If the caller needs more, paginate via /entry-exit/by-vehicle/{id}.
    # WS-8.E: ps.floor_id added so VehicleEvent.floor_id populates on the detail.
    # Pre-WS-8 DB tolerance: when ps.floor_id doesn't exist yet, emit NULL.
    ps_event_floor_id = "ps.floor_id" if schema["parking_sessions_floor_id"] else "NULL AS floor_id"
    event_rows = rows(db, f"""
        SELECT TOP 500
            ps.id,
            ps.status,
            ps.entry_time,
            ps.exit_time,
            ps.duration_seconds,
            ps.floor,
            {ps_event_floor_id},
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
            ps.slot_snapshot_path
        FROM parking_sessions ps
        LEFT JOIN parking_slots pk ON pk.slot_id = ps.slot_id
        WHERE ps.plate_number = :plate
        ORDER BY ps.entry_time DESC
    """, {"plate": plate})

    events = [
        _event_from_row(
            r, plate, vehicle_pk,
            owner_name=owner_name,
            vehicle_type=vehicle_type,
            is_employee=is_employee,
        )
        for r in event_rows
    ]
    return events_total, events


def _fetch_vehicle_detail(
    db: Session,
    where_clause: str,
    where_params: dict,
) -> Optional[VehicleDetail]:
    """Fetch a single vehicle by an arbitrary WHERE clause (id, plate, …),
    bundle its parking-event history, and return the full `VehicleDetail`.

    Returns None when the row doesn't exist — callers raise 404 themselves
    so the message can name the missing identifier.

    Shared by GET /vehicles/{id} and GET /vehicles/by-plate/{plate}.
    """
    cols = _vehicle_extra_cols(db)

    extra_cols = (
        (", v.is_employee" if cols["is_employee"] else ", NULL AS is_employee") +
        (", v.phone"       if cols["phone"]       else ", NULL AS phone")       +
        (", v.email"       if cols["email"]       else ", NULL AS email")
    )

    if cols["current_slot_id"]:
        slot_join_d   = "LEFT JOIN dbo.parking_slots cs ON cs.slot_id = v.current_slot_id"
        slot_select_d = ", v.current_slot_id, cs.slot_name AS current_slot_name"
    else:
        slot_join_d   = ""
        slot_select_d = ", NULL AS current_slot_id, NULL AS current_slot_name"

    vehicle_rows = rows(db, f"""
        SELECT
            v.id,
            v.plate_number,
            v.owner_name,
            v.vehicle_type,
            v.employee_id,
            v.title,
            v.is_registered,
            v.registered_at,
            v.notes
            {extra_cols}
            {slot_select_d}
        FROM vehicles v
        {slot_join_d}
        WHERE {where_clause}
    """, where_params)

    if not vehicle_rows:
        return None

    v = vehicle_rows[0]
    plate = v["plate_number"]
    vehicle_pk = v["id"]
    v_owner = v.get("owner_name")
    v_type = v.get("vehicle_type")
    v_is_emp = bool(v["is_employee"]) if v.get("is_employee") is not None else None

    events_total, events = _fetch_vehicle_events(
        db, plate, vehicle_pk,
        owner_name=v_owner,
        vehicle_type=v_type,
        is_employee=v_is_emp,
    )
    current_event = next((e for e in events if e.status == "open"), None)

    return VehicleDetail(
        id=v["id"],
        plate_number=v["plate_number"],
        owner_name=v.get("owner_name"),
        vehicle_type=v.get("vehicle_type"),
        employee_id=v.get("employee_id"),
        title=v.get("title"),
        is_registered=bool(v["is_registered"]) if v.get("is_registered") is not None else None,
        registered_at=v.get("registered_at"),
        notes=v.get("notes"),
        is_employee=bool(v["is_employee"]) if v.get("is_employee") is not None else None,
        phone=v.get("phone"),
        email=v.get("email"),
        current_slot_id=v.get("current_slot_id"),
        current_slot_name=v.get("current_slot_name"),
        is_currently_parked=current_event is not None,
        is_overstay=current_event.is_overstay if current_event else False,
        current_event=current_event,
        parked_at=current_event.parked_at if current_event else None,
        parking_status=current_event.status if current_event else None,
        floor=current_event.floor if current_event else None,
        floor_id=current_event.floor_id if current_event else None,
        events_total=events_total,
        events=events,
    )


# ── GET /vehicles/history ─────────────────────────────────────────────────────
# Everything the database knows about one plate: registry row, where it is
# now, and its visits / alerts / gate reads / slot sightings in a date range.

_HISTORY_SECTIONS = ("sessions", "alerts", "gate_reads", "slots")
_HISTORY_INCLUDE = _HISTORY_SECTIONS + ("timeline",)


def _parse_include(include: Optional[str]) -> set[str]:
    if not include:
        return set(_HISTORY_SECTIONS)
    wanted = {p.strip().lower() for p in include.split(",") if p.strip()}
    unknown = wanted - set(_HISTORY_INCLUDE)
    if unknown:
        raise HTTPException(400, f"Unknown include value(s): {', '.join(sorted(unknown))}. "
                                 f"Allowed: {', '.join(_HISTORY_INCLUDE)}")
    return wanted


def _range_clause(column: str, start, end, clauses: list, params: dict, key: str) -> None:
    if start is not None:
        clauses.append(f"{column} >= :{key}_start")
        params[f"{key}_start"] = start
    if end is not None:
        clauses.append(f"{column} < :{key}_end")
        params[f"{key}_end"] = end


def _fmt_duration(seconds: Optional[int]) -> str:
    if seconds is None:
        return ""
    h, m = divmod(int(seconds) // 60, 60)
    return f"{h}h {m}m" if h else f"{m}m"


def _limit_sql(limit: Optional[int], params: dict) -> str:
    if limit is None:
        return ""
    params["lim"] = limit
    return "OFFSET 0 ROWS FETCH NEXT :lim ROWS ONLY"


@dataclass
class _HistoryQuery:
    """One request's plate + range + filters, resolved once."""
    forms: list[str]
    start: Optional[datetime]
    end: Optional[datetime]
    session_status: Optional[ParkingSessionStatus]
    alert_type: Optional[str]
    severity: Optional[AlertSeverity]
    resolved: Optional[bool]
    gate: Optional[EntryExitDirection]
    camera_id: Optional[str]
    floor: Optional[str]
    floor_id: Optional[int]
    open_only: bool = False


def _history_sessions(db: Session, q: _HistoryQuery, limit: Optional[int]) -> HistorySection:
    schema = _floor_schema()
    params: dict = {}
    clauses = [plate_in_clause("ps.plate_number", q.forms, params)]
    _range_clause("ps.entry_time", q.start, q.end, clauses, params, "r")
    if q.open_only:
        clauses.append("ps.status IN ('open', 'overstay')")
    if q.session_status == ParkingSessionStatus.overstay:
        # Same rule as the Entry/Exit list's overstay filter.
        clauses.append("ps.status IN ('open', 'overstay') AND ps.entry_time < :overstay_cutoff")
        params["overstay_cutoff"] = facility_today_utc()
    elif q.session_status:
        clauses.append("ps.status = :status")
        params["status"] = q.session_status.value
    if q.floor_id is not None and schema["parking_sessions_floor_id"]:
        clauses.append("ps.floor_id = :floor_id")
        params["floor_id"] = q.floor_id
    elif q.floor:
        clauses.append("ps.floor = :floor")
        params["floor"] = q.floor
    where = " AND ".join(clauses)

    total = scalar(db, f"SELECT COUNT(*) FROM parking_sessions ps WHERE {where}", params) or 0
    ps_floor_id = "ps.floor_id" if schema["parking_sessions_floor_id"] else "NULL"
    found = rows(db, f"""
        SELECT
            ps.id, ps.vehicle_id, ps.plate_number, ps.status,
            ps.entry_time, ps.exit_time, ps.duration_seconds,
            ps.floor, {ps_floor_id} AS floor_id,
            ps.slot_id, COALESCE(pk.slot_name, ps.slot_number) AS slot_name, ps.slot_number,
            ps.parked_at, ps.slot_left_at,
            ps.entry_camera_id, ps.exit_camera_id, ps.slot_camera_id,
            ps.entry_snapshot_path, ps.exit_snapshot_path, ps.slot_snapshot_path,
            {OWNER_NAME_EXPR}   AS owner_name,
            {VEHICLE_TYPE_EXPR} AS vehicle_type,
            {IS_EMPLOYEE_EXPR}  AS is_employee
        FROM parking_sessions ps
        {VEHICLE_JOIN}
        LEFT JOIN parking_slots pk ON pk.slot_id = ps.slot_id
        WHERE {where}
        ORDER BY ps.entry_time DESC, ps.id DESC
        {_limit_sql(limit, params)}
    """, params)
    return HistorySection[VehicleEvent](
        total=total, items=[_session_event(r, r["plate_number"]) for r in found],
    )


def _history_alerts(db: Session, q: _HistoryQuery, limit: Optional[int]) -> HistorySection:
    cols = _alerts_extra_cols()
    bits = _alert_query_bits(cols)
    schema = _floor_schema()
    where, params = _alert_where(
        None, q.severity, q.alert_type, q.resolved, None, None, cols,
        floor_id=q.floor_id, floor=q.floor,
    )
    clauses = [where, plate_in_clause("a.plate_number", q.forms, params)]
    _range_clause("a.triggered_at", q.start, q.end, clauses, params, "r")
    where = " AND ".join(clauses)

    select_from, floors_join = alert_items_sql(cols, schema)
    total = scalar(db, f"""
        SELECT COUNT(*) FROM alerts a
        {bits["slot_join"]}
        LEFT JOIN cameras c ON c.camera_id = a.camera_id
        {floors_join}
        WHERE {where}
    """, params) or 0
    found = rows(db, f"""
        {select_from}
        WHERE {where}
        ORDER BY a.triggered_at DESC, a.id DESC
        {_limit_sql(limit, params)}
    """, params)
    return HistorySection[AlertItem](total=total, items=[alert_item_fixup(r) for r in found])


def _history_gate_reads(db: Session, q: _HistoryQuery, limit: Optional[int]) -> HistorySection:
    params: dict = {}
    clauses = ["g.is_test = 0", plate_in_clause("g.plate_number", q.forms, params)]
    _range_clause("g.event_time", q.start, q.end, clauses, params, "r")
    if q.gate:
        clauses.append("g.gate = :gate")
        params["gate"] = q.gate.value
    if q.camera_id:
        clauses.append("g.camera_id = :camera_id")
        params["camera_id"] = q.camera_id
    where = " AND ".join(clauses)

    total = scalar(db, f"SELECT COUNT(*) FROM entry_exit_log g WHERE {where}", params) or 0
    found = rows(db, f"""
        SELECT g.id, g.plate_number, g.gate, g.camera_id, g.event_time, g.snapshot_path,
               g.plate_confidence, g.matched_entry_id, g.parking_duration
        FROM entry_exit_log g
        WHERE {where}
        ORDER BY g.event_time DESC, g.id DESC
        {_limit_sql(limit, params)}
    """, params)
    return HistorySection[GateRead](total=total, items=[
        GateRead(
            id=r["id"], plate_number=r["plate_number"], gate=r.get("gate"),
            camera_id=r.get("camera_id"), event_time=localize_naive(r.get("event_time")),
            snapshot_url=resolve_snapshot_url(r.get("snapshot_path")),
            plate_confidence=r.get("plate_confidence"),
            matched_entry_id=r.get("matched_entry_id"),
            parking_duration_seconds=r.get("parking_duration"),
        )
        for r in found
    ])


def _history_slots(db: Session, q: _HistoryQuery, limit: Optional[int]) -> HistorySection:
    """slot_status readings that name this plate, merged into sightings.

    Each reading lasts until the NEXT reading of the same slot (whatever it
    says). When that next reading is this car again, the two are one sighting.
    slot_status has no plate index; a plate has few readings, so every one is
    fetched and merged here, then cut to `limit`."""
    schema = _floor_schema()
    params: dict = {}
    clauses = [plate_in_clause("ss.plate_number", q.forms, params)]
    _range_clause("ss.time", q.start, q.end, clauses, params, "r")
    if q.floor:
        clauses.append("pk.floor = :floor")
        params["floor"] = q.floor
    elif q.floor_id is not None and schema["floors_table"]:
        clauses.append("pk.floor = (SELECT name FROM floors WHERE id = :floor_id)")
        params["floor_id"] = q.floor_id

    found = rows(db, f"""
        SELECT ss.id, ss.slot_id, ss.status, ss.time,
               pk.slot_name, pk.floor,
               nx.id AS next_id, nx.time AS next_time
        FROM slot_status ss
        LEFT JOIN parking_slots pk ON pk.slot_id = ss.slot_id
        OUTER APPLY (
            SELECT TOP 1 s2.id, s2.time
            FROM slot_status s2
            WHERE s2.slot_id = ss.slot_id
              AND (s2.time > ss.time OR (s2.time = ss.time AND s2.id > ss.id))
            ORDER BY s2.time, s2.id
        ) nx
        WHERE {" AND ".join(clauses)}
        ORDER BY ss.slot_id, ss.time, ss.id
    """, params)

    sightings: list[dict] = []
    by_next: dict[int, dict] = {}     # next reading's id -> the sighting it continues
    for r in found:
        s = by_next.pop(r["id"], None)
        if s is None:
            s = {"slot_id": r["slot_id"], "slot_name": r.get("slot_name"), "floor": r.get("floor"),
                 "status": r.get("status"), "seen_from": r["time"], "observations": 0}
            sightings.append(s)
        s["observations"] += 1
        s["seen_until"] = r.get("next_time")
        if r.get("next_id") is not None:
            by_next[r["next_id"]] = s

    sightings.sort(key=lambda s: s["seen_from"], reverse=True)
    shown = sightings if limit is None else sightings[:limit]
    return HistorySection[SlotSighting](total=len(sightings), items=[
        SlotSighting(
            **{k: s[k] for k in ("slot_id", "slot_name", "floor", "status", "observations")},
            seen_from=localize_naive(s["seen_from"]),
            seen_until=localize_naive(s["seen_until"]),
            duration_seconds=(
                int((s["seen_until"] - s["seen_from"]).total_seconds())
                if s["seen_until"] is not None else None
            ),
        )
        for s in shown
    ])


def _history_summary(db: Session, q: _HistoryQuery) -> VehicleHistorySummary:
    """Range only — the section filters are deliberately not applied."""
    def where(column: str, alias_clauses: list[str], params: dict) -> str:
        clauses = list(alias_clauses)
        _range_clause(column, q.start, q.end, clauses, params, "r")
        return " AND ".join(clauses)

    p: dict = {"now": facility_now_naive(), "midnight": facility_today_utc()}
    s = rows(db, f"""
        SELECT COUNT(*) AS visits,
               SUM(CASE WHEN (exit_time IS NULL AND entry_time < :midnight)
                          OR exit_time >= DATEADD(DAY, 1, CAST(CAST(entry_time AS DATE) AS DATETIME2))
                        THEN 1 ELSE 0 END) AS overstays,
               SUM(CAST(COALESCE(duration_seconds, DATEDIFF(SECOND, entry_time, :now)) AS BIGINT)) AS parked,
               AVG(CAST(COALESCE(duration_seconds, DATEDIFF(SECOND, entry_time, :now)) AS FLOAT)) AS avg_sec,
               MIN(entry_time) AS first_at,
               MAX(COALESCE(exit_time, entry_time)) AS last_at
        FROM parking_sessions
        WHERE {where("entry_time", [plate_in_clause("plate_number", q.forms, p)], p)}
    """, p)[0]

    p = {}
    a = rows(db, f"""
        SELECT COUNT(*) AS n, SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END) AS open_n,
               MIN(triggered_at) AS first_at, MAX(triggered_at) AS last_at
        FROM alerts
        WHERE {where("triggered_at", ["is_test = 0", plate_in_clause("plate_number", q.forms, p)], p)}
    """, p)[0]

    p = {}
    g = rows(db, f"""
        SELECT COUNT(*) AS n, MIN(event_time) AS first_at, MAX(event_time) AS last_at
        FROM entry_exit_log
        WHERE {where("event_time", ["is_test = 0", plate_in_clause("plate_number", q.forms, p)], p)}
    """, p)[0]

    p = {}
    sl = rows(db, f"""
        SELECT COUNT(*) AS n, MIN(time) AS first_at, MAX(time) AS last_at
        FROM slot_status
        WHERE {where("time", [plate_in_clause("plate_number", q.forms, p)], p)}
    """, p)[0]

    firsts = [x["first_at"] for x in (s, a, g, sl) if x["first_at"] is not None]
    lasts = [x["last_at"] for x in (s, a, g, sl) if x["last_at"] is not None]
    return VehicleHistorySummary(
        visits=s["visits"] or 0,
        overstays=s["overstays"] or 0,
        total_parked_seconds=int(s["parked"] or 0),
        avg_stay_minutes=round((s["avg_sec"] or 0) / 60, 1),
        alerts=a["n"] or 0,
        open_alerts=a["open_n"] or 0,
        gate_reads=g["n"] or 0,
        slot_sightings=sl["n"] or 0,
        first_seen_at=localize_naive(min(firsts)) if firsts else None,
        last_seen_at=localize_naive(max(lasts)) if lasts else None,
    )


def _history_current(db: Session, q: _HistoryQuery, vehicle: Optional[VehicleRef]) -> VehicleHistoryCurrent:
    """Now, regardless of the range and filters."""
    open_q = _HistoryQuery(**{**q.__dict__, "start": None, "end": None, "session_status": None,
                              "floor": None, "floor_id": None, "open_only": True})
    params: dict = {}
    plate_clause = plate_in_clause("ps.plate_number", q.forms, params)
    open_count = scalar(db, f"""
        SELECT COUNT(*) FROM parking_sessions ps
        WHERE {plate_clause} AND ps.status IN ('open', 'overstay')
    """, params) or 0
    newest_open = None
    if open_count:
        newest_open = _history_sessions(db, open_q, 1).items[0]

    params = {}
    open_alerts = scalar(db, f"""
        SELECT COUNT(*) FROM alerts
        WHERE is_test = 0 AND is_resolved = 0 AND {plate_in_clause("plate_number", q.forms, params)}
    """, params) or 0

    slot_id = (newest_open.slot_id if newest_open else None) or (vehicle.current_slot_id if vehicle else None)
    slot_name = (newest_open.slot_name if newest_open and newest_open.slot_id else None) or (
        vehicle.current_slot_name if vehicle and vehicle.current_slot_id == slot_id else None
    )
    return VehicleHistoryCurrent(
        is_inside=newest_open is not None,
        open_session=newest_open,
        open_sessions_count=open_count,
        current_slot_id=slot_id,
        current_slot_name=slot_name,
        open_alerts=open_alerts,
    )


def _history_vehicle(db: Session, forms: list[str]) -> Optional[VehicleRef]:
    cols = _vehicle_extra_cols(db)
    extra = (
        (", v.is_employee" if cols["is_employee"] else ", NULL AS is_employee") +
        (", v.phone"       if cols["phone"]       else ", NULL AS phone") +
        (", v.email"       if cols["email"]       else ", NULL AS email")
    )
    if cols["current_slot_id"]:
        slot_join = "LEFT JOIN dbo.parking_slots cs ON cs.slot_id = v.current_slot_id"
        slot_sel = ", v.current_slot_id, cs.slot_name AS current_slot_name"
    else:
        slot_join, slot_sel = "", ", NULL AS current_slot_id, NULL AS current_slot_name"
    params: dict = {}
    found = rows(db, f"""
        SELECT TOP 1 v.id, v.plate_number, v.owner_name, v.vehicle_type, v.employee_id,
               v.title, v.is_registered, v.registered_at, v.notes {extra} {slot_sel}
        FROM vehicles v
        {slot_join}
        WHERE {plate_in_clause("v.plate_number", forms, params)}
    """, params)
    if not found:
        return None
    v = found[0]
    return VehicleRef(**{**v, "is_registered": bool(v.get("is_registered"))})


def _history_timeline(sections: dict[str, HistorySection], limit: Optional[int]) -> list[VehicleTimelineItem]:
    """All sections merged, newest first. Built from the sections' newest
    `limit` rows, which always hold the newest `limit` events overall (an exit
    of a visit older than those is the one edge left out)."""
    out: list[VehicleTimelineItem] = []
    for e in sections["sessions"].items:
        out.append(VehicleTimelineItem(
            at=e.entry.event_time, kind="entry", ref_id=str(e.id), camera_id=e.entry.camera_id,
            floor=e.floor, text=f"Entered (visit #{e.id})", snapshot_url=e.entry.snapshot_url,
        ))
        if e.parked_at and e.slot_id:
            out.append(VehicleTimelineItem(
                at=e.parked_at, kind="parked", ref_id=str(e.id), slot_id=e.slot_id, floor=e.floor,
                camera_id=e.slot_camera_id, text=f"Parked in {e.slot_name or e.slot_id}",
                snapshot_url=e.slot_snapshot_url,
            ))
        if e.exit:
            out.append(VehicleTimelineItem(
                at=e.exit.event_time, kind="exit", ref_id=str(e.id), camera_id=e.exit.camera_id,
                floor=e.floor, text=f"Exited after {_fmt_duration(e.duration_seconds)} (visit #{e.id})",
                snapshot_url=e.exit.snapshot_url,
            ))
    for a in sections["alerts"].items:
        label = (a.alert_type or "alert").replace("_", " ")
        out.append(VehicleTimelineItem(
            at=a.triggered_at, kind="alert", ref_id=str(a.id), camera_id=a.camera_id,
            slot_id=a.slot_id, floor=a.floor, severity=a.severity, snapshot_url=a.snapshot_url,
            text=f"Alert: {label}" + (f" at {a.location}" if a.location else ""),
        ))
        if a.is_resolved and a.resolved_at:
            out.append(VehicleTimelineItem(
                at=a.resolved_at, kind="alert_resolved", ref_id=str(a.id),
                severity=a.severity, text=f"Alert resolved: {label}",
            ))
    for g in sections["gate_reads"].items:
        conf = f", confidence {g.plate_confidence:g}" if g.plate_confidence is not None else ""
        out.append(VehicleTimelineItem(
            at=g.event_time, kind="gate_read", ref_id=str(g.id), camera_id=g.camera_id,
            snapshot_url=g.snapshot_url,
            text=f"Plate read at {g.gate or 'gate'} ({g.camera_id}{conf})",
        ))
    for s in sections["slots"].items:
        out.append(VehicleTimelineItem(
            at=s.seen_from, kind="slot", ref_id=s.slot_id, slot_id=s.slot_id, floor=s.floor,
            text=f"Seen in {s.slot_name or s.slot_id}"
                 + (f" for {_fmt_duration(s.duration_seconds)}" if s.duration_seconds is not None else ""),
        ))
    out = [t for t in out if t.at is not None]
    out.sort(key=lambda t: t.at, reverse=True)
    return out if limit is None else out[:limit]


def _history_query(
    plate, date_from, date_to, session_status, alert_type, severity, resolved,
    gate, camera_id, floor, floor_id, db,
) -> _HistoryQuery:
    forms = plate_exact_forms(plate)
    if not forms:
        raise HTTPException(400, "plate must contain letters or digits")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(400, "date_from must not be after date_to")
    return _HistoryQuery(
        forms=forms,
        start=datetime.combine(date_from, datetime.min.time()) if date_from else None,
        end=datetime.combine(date_to + timedelta(days=1), datetime.min.time()) if date_to else None,
        session_status=session_status, alert_type=alert_type, severity=severity, resolved=resolved,
        gate=gate, camera_id=camera_id, floor=floor,
        floor_id=resolve_floor_id(db, floor_id=floor_id, floor_name=floor),
    )


_PLATE_Q = Query(..., min_length=2, max_length=20,
                 description="One plate, either display order; dashes/spaces ignored. Exact match only.")
_HIST_DATE_FROM = Query(None, description="First day (inclusive), facility-local. Omit both for all time.")
_HIST_DATE_TO = Query(None, description="Last day (inclusive), facility-local.")
_SESSION_STATUS_Q = Query(None, description="Visits only.")
_ALERT_TYPE_Q = Query(None, description="Alerts only.")
_SEVERITY_Q = Query(None, description="Alerts only.")
_RESOLVED_Q = Query(None, description="Alerts only. Omit for both.")
_GATE_Q = Query(None, description="Gate reads only.")
_CAMERA_Q = Query(None, description="Gate reads only.")
_FLOOR_Q = Query(None, description="Visits, alerts and slot history.")
_FLOOR_ID_Q = Query(None, description="Visits, alerts and slot history; wins over `floor`.")


@router.get("/history", response_model=VehicleHistory)
async def vehicle_history(
    plate: str = _PLATE_Q,
    date_from: Optional[date] = _HIST_DATE_FROM,
    date_to: Optional[date] = _HIST_DATE_TO,
    include: Optional[str] = Query(
        None,
        description="Comma list of sessions, alerts, gate_reads, slots, timeline. "
                    "Default: the four sections, no timeline.",
    ),
    limit: int = Query(50, ge=1, le=500, description="Newest items per section (and in the timeline)."),
    session_status: Optional[ParkingSessionStatus] = _SESSION_STATUS_Q,
    alert_type: Optional[str] = _ALERT_TYPE_Q,
    severity: Optional[AlertSeverity] = _SEVERITY_Q,
    resolved: Optional[bool] = _RESOLVED_Q,
    gate: Optional[EntryExitDirection] = _GATE_Q,
    camera_id: Optional[str] = _CAMERA_Q,
    floor: Optional[str] = _FLOOR_Q,
    floor_id: Optional[int] = _FLOOR_ID_Q,
    db: Session = Depends(get_db),
):
    """Everything about one plate, registered or not.

    - `vehicle`: the registry row, or null.
    - `current`: inside right now? Open visit, slot, open alerts. Ignores the
      range and the filters.
    - `summary`: counts for the range. Ignores the filters.
    - `sessions` / `alerts` / `gate_reads` / `slot_history`: newest `limit`
      of each, with `total`; range and filters apply. Null when not in `include`.
    - `timeline`: only with `include=timeline`; the same records merged into
      one newest-first list, capped at `limit`.
    """
    wanted = _parse_include(include)
    q = _history_query(plate, date_from, date_to, session_status, alert_type, severity,
                       resolved, gate, camera_id, floor, floor_id, db)

    need = set(_HISTORY_SECTIONS) if "timeline" in wanted else wanted & set(_HISTORY_SECTIONS)
    fetch = {"sessions": _history_sessions, "alerts": _history_alerts,
             "gate_reads": _history_gate_reads, "slots": _history_slots}
    sections = {name: fetch[name](db, q, limit) for name in need}

    vehicle = _history_vehicle(db, q.forms)
    summary = _history_summary(db, q)
    current = _history_current(db, q, vehicle)

    matched = set()
    if vehicle:
        matched.add(vehicle.plate_number)
    for sec in sections.values():
        matched.update(i.plate_number for i in sec.items if getattr(i, "plate_number", None))
    if current.open_session:
        matched.add(current.open_session.plate_number)

    found = bool(vehicle or current.is_inside or summary.visits or summary.alerts
                 or summary.gate_reads or summary.slot_sightings)
    return VehicleHistory(
        plate=plate,
        matched_plates=sorted(matched),
        found=found,
        date_from=date_from,
        date_to=date_to,
        vehicle=vehicle,
        current=current,
        summary=summary,
        sessions=sections["sessions"] if "sessions" in wanted else None,
        alerts=sections["alerts"] if "alerts" in wanted else None,
        gate_reads=sections["gate_reads"] if "gate_reads" in wanted else None,
        slot_history=sections["slots"] if "slots" in wanted else None,
        timeline=_history_timeline(sections, limit) if "timeline" in wanted else None,
    )


@router.get("/history/export/csv")
async def export_vehicle_history_csv(
    plate: str = _PLATE_Q,
    date_from: Optional[date] = _HIST_DATE_FROM,
    date_to: Optional[date] = _HIST_DATE_TO,
    session_status: Optional[ParkingSessionStatus] = _SESSION_STATUS_Q,
    alert_type: Optional[str] = _ALERT_TYPE_Q,
    severity: Optional[AlertSeverity] = _SEVERITY_Q,
    resolved: Optional[bool] = _RESOLVED_Q,
    gate: Optional[EntryExitDirection] = _GATE_Q,
    camera_id: Optional[str] = _CAMERA_Q,
    floor: Optional[str] = _FLOOR_Q,
    floor_id: Optional[int] = _FLOOR_ID_Q,
    db: Session = Depends(get_db),
):
    """The full timeline (no `limit`) for the same plate, range and filters
    as GET /vehicles/history, one row per event."""
    q = _history_query(plate, date_from, date_to, session_status, alert_type, severity,
                       resolved, gate, camera_id, floor, floor_id, db)
    sections = {
        "sessions": _history_sessions(db, q, None),
        "alerts": _history_alerts(db, q, None),
        "gate_reads": _history_gate_reads(db, q, None),
        "slots": _history_slots(db, q, None),
    }
    data = [
        {
            "Time": t.at.strftime("%Y-%m-%d %H:%M:%S") if t.at else "",
            "Event": t.kind, "Reference": t.ref_id, "Details": t.text,
            "Camera": t.camera_id, "Slot": t.slot_id, "Floor": t.floor, "Severity": t.severity,
        }
        for t in _history_timeline(sections, None)
    ]
    headers = ["Time", "Event", "Reference", "Details", "Camera", "Slot", "Floor", "Severity"]
    safe = normalize_plate_term(plate) or "plate"
    return stream_csv(data, headers, filename=f"vehicle-history-{safe}.csv")


# ── GET /vehicles/by-plate/{plate_number} ─────────────────────────────────────
# Declared BEFORE /{vehicle_id} so FastAPI matches it cleanly. The int-typed
# `/{vehicle_id}` wouldn't catch `by-plate/...` anyway (different shape), but
# the explicit ordering keeps the routing intent visible.
@router.get("/by-plate/{plate_number}", response_model=VehicleDetail)
async def get_vehicle_by_plate(
    plate_number: str = Path(..., min_length=2, max_length=20),
    db: Session = Depends(get_db),
):
    """Look up a vehicle by its plate number. Same response shape as
    GET /vehicles/{id} — full detail with parking-event history.

    Returns rows whether `is_registered` is true or false, as long as the
    plate has a row in the `vehicles` table — the returned `id` is what
    the frontend uses for PUT / DELETE follow-ups. Returns 404 when no row
    exists in `vehicles` for that plate, even if `parking_sessions`
    contains the plate (an id-less response would leave the row unusable
    for management operations).
    """
    detail = _fetch_vehicle_detail(
        db,
        "v.plate_number = :plate",
        {"plate": plate_number},
    )
    if detail is None:
        raise HTTPException(404, f"Vehicle with plate '{plate_number}' not found")
    return detail


# ── GET /vehicles/{vehicle_id} ────────────────────────────────────────────────
# Declared LAST so FastAPI matches the specific routes (/kpis, /export/csv,
# /by-plate/...) first.
@router.get("/{vehicle_id}", response_model=VehicleDetail)
async def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
):
    """Return a vehicle by id with its full parking-event history (entries + exits).
    For filtered/paginated event queries, use GET /entry-exit/by-vehicle/{vehicle_id}.
    """
    detail = _fetch_vehicle_detail(
        db,
        "v.id = :vehicle_id",
        {"vehicle_id": vehicle_id},
    )
    if detail is None:
        raise HTTPException(404, "Vehicle not found")
    return detail
