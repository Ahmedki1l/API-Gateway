from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db, scalar, rows
from app.routers._helpers import _floor_schema
from app.routers.entry_exit import _live_duration_seconds
from app.services.snapshots import resolve_snapshot_url
from app.schemas import (
    EntityActionResponse,
    EntryExitEvent,
    PagedResponse,
    VehicleCreate,
    VehicleDetail,
    VehicleEvent,
    VehicleItem,
    VehicleKPIs,
    VehicleListItem,
    VehicleUpdate,
)
from app.shared import build_paged, stream_csv

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])

_UNREGISTERED_NOTE_MARKER = "Not registered"


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
            {floor_expr}    AS floor,
            {floor_id_expr} AS floor_id
        FROM vehicles v
        LEFT JOIN (
            SELECT
                plate_number,
                parked_at,
                status,
                floor,
                {ps_floor_id_col},
                ROW_NUMBER() OVER (PARTITION BY plate_number ORDER BY entry_time DESC) AS rn
            FROM parking_sessions
            WHERE status = 'open'
        ) ps ON ps.plate_number = v.plate_number AND ps.rn = 1
        WHERE v.id = :id
    """, {"id": vehicle_id})
    return result[0] if result else None


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

    vehicle_id: Optional[int] = None
    if existing_vehicle:
        vehicle_id = existing_vehicle[0]["id"]
        merged_notes = _merge_vehicle_notes(existing_vehicle[0].get("notes"), body.notes)

        db.execute(text("""
            UPDATE vehicles
            SET owner_name = :owner,
                employee_id = :emp_id,
                vehicle_type = :vtype,
                title = :title,
                is_employee = :is_employee,
                phone = :phone,
                email = :email,
                notes = :notes,
                is_registered = 1,
                registered_at = GETDATE()
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
        })
        response.status_code = status.HTTP_200_OK
    else:
        db.execute(text("""
            INSERT INTO vehicles
                (plate_number, owner_name, employee_id, vehicle_type, title, is_employee, phone, email, notes, is_registered, registered_at)
            VALUES
                (:plate, :owner, :emp_id, :vtype, :title, :is_employee, :phone, :email, :notes, 1, GETDATE())
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
    return item


# ── GET /vehicles/kpis ────────────────────────────────────────────────────────
@router.get("/kpis", response_model=VehicleKPIs)
async def vehicle_kpis(db: Session = Depends(get_db)):
    cols = _vehicle_extra_cols(db)

    total  = scalar(db, "SELECT COUNT(*) FROM vehicles")
    active = scalar(db,
        "SELECT COUNT(DISTINCT plate_number) FROM parking_sessions WHERE status = 'open'")
    employee = scalar(db, "SELECT COUNT(*) FROM vehicles WHERE is_employee = 1") \
               if cols["is_employee"] else 0

    return VehicleKPIs(
        total_vehicles=total or 0,
        active_vehicles=active or 0,
        employee_vehicles=employee or 0,
    )


# ── GET /vehicles ─────────────────────────────────────────────────────────────
@router.get("/", response_model=PagedResponse[VehicleItem])
async def get_vehicles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="plate or owner name"),
    is_employee: Optional[bool] = Query(None),
    vehicle_type: Optional[str] = Query(None),
    is_registered: Optional[bool] = Query(
        None,
        description=(
            "true  → only plates that exist as a row in the `vehicles` registry\n"
            "false → only plates seen in parking_sessions but never registered\n"
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
    db: Session = Depends(get_db),
):
    """All-plates view: UNION of the `vehicles` registry and any plate that has
    ever generated a parking_sessions row. Unregistered plates surface with
    `id = null`, `is_registered = false`, and whatever data is available from
    the most recent parking session. The `?is_currently_parked=true` filter
    matches all 14-style "active now" plates regardless of registration —
    fixing the previous mismatch where /vehicles count < active-vehicles count.
    """
    cols    = _vehicle_extra_cols(db)
    schema  = _floor_schema()
    clauses = ["1=1"]
    params: dict = {}

    if search:
        clauses.append("(ap.plate_number LIKE :search OR v.owner_name LIKE :search)")
        params["search"] = f"%{search}%"
    if vehicle_type:
        clauses.append("COALESCE(v.vehicle_type, ps.vehicle_type) = :vehicle_type")
        params["vehicle_type"] = vehicle_type
    if is_registered is True:
        clauses.append("v.id IS NOT NULL")
    elif is_registered is False:
        clauses.append("v.id IS NULL")
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

    # CTE: every plate the system has ever observed — registry ∪ parking_sessions.
    all_plates_cte = """
        WITH all_plates AS (
            SELECT plate_number FROM dbo.vehicles
            UNION
            SELECT DISTINCT plate_number FROM dbo.parking_sessions WHERE plate_number IS NOT NULL
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

    items = rows(db, f"""
        {all_plates_cte}
        SELECT
            v.id,
            ap.plate_number,
            v.owner_name,
            COALESCE(v.vehicle_type, ps.vehicle_type) AS vehicle_type,
            v.employee_id,
            v.title,
            -- Reflect whether the plate has a registry row, not just the v.is_registered flag
            CASE WHEN v.id IS NOT NULL THEN 1 ELSE 0 END AS is_registered,
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
        ORDER BY
            CASE WHEN ps.parked_at IS NOT NULL THEN 0 ELSE 1 END,
            ps.parked_at DESC,
            v.registered_at DESC,
            ap.plate_number
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

    set_clause = ", ".join(f"{k} = :{k}" for k in safe_updates)
    safe_updates["vehicle_id"] = vehicle_id

    result = db.execute(
        text(f"UPDATE vehicles SET {set_clause} WHERE id = :vehicle_id"),
        safe_updates,
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "Vehicle not found")

    item = _fetch_vehicle_list_item(db, vehicle_id)
    if item is None:
        raise HTTPException(500, "Vehicle updated but could not be re-read")
    return item


# ── DELETE /vehicles/{vehicle_id} ──────────────────────────────────────────────
@router.delete("/{vehicle_id}", response_model=EntityActionResponse)
async def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
):
    result = db.execute(
        text("DELETE FROM vehicles WHERE id = :vehicle_id"),
        {"vehicle_id": vehicle_id},
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
    is_registered: Optional[bool] = Query(None),
    is_employee: Optional[bool] = Query(None),
    is_currently_parked: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """CSV export of vehicles. Filter set matches `GET /vehicles/` so the CSV
    download mirrors what's on screen."""
    cols = _vehicle_extra_cols(db)
    clauses = ["1=1"]
    params: dict = {}
    if search:
        clauses.append("(v.plate_number LIKE :search OR v.owner_name LIKE :search)")
        params["search"] = f"%{search}%"
    if vehicle_type:
        clauses.append("v.vehicle_type = :vehicle_type")
        params["vehicle_type"] = vehicle_type
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
        ORDER BY v.registered_at DESC
    """, params)

    headers = ["Plate Number", "Owner Name", "Vehicle Type", "Employee ID",
               "Title", "Registered", "Is Employee", "Registered At",
               "Currently Parked", "Parked At", "Floor",
               "Current Slot ID", "Current Slot Name", "Notes"]
    return stream_csv(data, headers, filename="vehicles.csv")


# ── GET /vehicles/{vehicle_id} ────────────────────────────────────────────────
# Declared LAST so FastAPI matches the specific routes (/kpis, /export/csv) first.
@router.get("/{vehicle_id}", response_model=VehicleDetail)
async def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
):
    """Return a vehicle by id with its full parking-event history (entries + exits).
    For filtered/paginated event queries, use GET /entry-exit/by-vehicle/{vehicle_id}.
    """
    cols = _vehicle_extra_cols(db)
    schema = _floor_schema()

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
        WHERE v.id = :vehicle_id
    """, {"vehicle_id": vehicle_id})

    if not vehicle_rows:
        raise HTTPException(404, "Vehicle not found")

    v = vehicle_rows[0]
    plate = v["plate_number"]

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

    vehicle_pk = v["id"]
    v_owner = v.get("owner_name")
    v_type = v.get("vehicle_type")
    v_is_emp = bool(v["is_employee"]) if v.get("is_employee") is not None else None
    events = [
        _event_from_row(
            r, plate, vehicle_pk,
            owner_name=v_owner,
            vehicle_type=v_type,
            is_employee=v_is_emp,
        )
        for r in event_rows
    ]
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
        current_event=current_event,
        parked_at=current_event.parked_at if current_event else None,
        parking_status=current_event.status if current_event else None,
        floor=current_event.floor if current_event else None,
        floor_id=current_event.floor_id if current_event else None,
        events_total=events_total,
        events=events,
    )
