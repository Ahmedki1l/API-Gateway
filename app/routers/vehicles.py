from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db, scalar, rows
from app.schemas import VehicleDetail, VehicleSession
from app.shared import build_paged, stream_csv

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


class VehicleCreate(BaseModel):
    plate_number: str
    owner_name:   Optional[str] = None
    employee_id:  Optional[str] = None
    vehicle_type: Optional[str] = None
    title:        Optional[str] = None
    is_employee: Optional[bool] = False
    phone:        Optional[str] = None
    email:        Optional[str] = None
    notes:        Optional[str] = None
    


class VehicleUpdate(BaseModel):
    plate_number: Optional[str]  = None
    owner_name:   Optional[str]  = None
    vehicle_type: Optional[str]  = None
    title:        Optional[str]  = None
    notes:        Optional[str]  = None
    is_employee:  Optional[bool] = False  # requires System 1 migration
    phone:        Optional[str]  = None  # requires System 1 migration
    email:        Optional[str]  = None  # requires System 1 migration


def _vehicle_extra_cols(db: Session) -> dict:
    """Check which post-migration columns exist — in Python, never in SQL."""
    def exists(col):
        n = scalar(db, """
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'vehicles' AND COLUMN_NAME = :c
        """, {"c": col})
        return (n or 0) > 0
    return {
        "is_employee": exists("is_employee"),
        "phone":       exists("phone"),
        "email":       exists("email"),
    }


# ── POST /vehicles ────────────────────────────────────────────────────────────
@router.post("/")
async def create_vehicle(body: VehicleCreate, db: Session = Depends(get_db)):
    existing = scalar(db,
        "SELECT COUNT(*) FROM vehicles WHERE plate_number = :p",
        {"p": body.plate_number})
    if existing:
        raise HTTPException(400, f"Plate '{body.plate_number}' is already registered")

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
    db.commit()

    created = rows(db,
        "SELECT * FROM vehicles WHERE plate_number = :p",
        {"p": body.plate_number})
    return created[0] if created else {"success": True}


# ── GET /vehicles/kpis ────────────────────────────────────────────────────────
@router.get("/kpis")
async def vehicle_kpis(db: Session = Depends(get_db)):
    cols = _vehicle_extra_cols(db)

    total  = scalar(db, "SELECT COUNT(*) FROM vehicles")
    active = scalar(db,
        "SELECT COUNT(DISTINCT plate_number) FROM parking_sessions WHERE status = 'open'")
    employee = scalar(db, "SELECT COUNT(*) FROM vehicles WHERE is_employee = 1") \
               if cols["is_employee"] else 0

    return {
        "total_vehicles":    total    or 0,
        "active_vehicles":   active   or 0,
        "employee_vehicles": employee or 0,
    }


# ── GET /vehicles ─────────────────────────────────────────────────────────────
@router.get("/")
async def get_vehicles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="plate or owner name"),
    is_employee: Optional[bool] = Query(None),
    vehicle_type: Optional[str] = Query(None),
    is_registered: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    cols    = _vehicle_extra_cols(db)
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

    where = " AND ".join(clauses)
    total = scalar(db, f"SELECT COUNT(*) FROM vehicles v WHERE {where}", params)

    params["offset"]    = (page - 1) * page_size
    params["page_size"] = page_size

    extra = (
        (", v.is_employee" if cols["is_employee"] else ", NULL AS is_employee") +
        (", v.phone"       if cols["phone"]       else ", NULL AS phone")       +
        (", v.email"       if cols["email"]       else ", NULL AS email")
    )

    items = rows(db, f"""
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
            {extra},
            ps.parked_at,
            ps.status      AS parking_status,
            ps.floor,
            ps.zone_name   AS zone
        FROM vehicles v
        LEFT JOIN (
            SELECT
                plate_number,
                parked_at,
                status,
                floor,
                zone_name,
                ROW_NUMBER() OVER (PARTITION BY plate_number ORDER BY entry_time DESC) AS rn
            FROM parking_sessions
            WHERE status = 'open'
        ) ps ON ps.plate_number = v.plate_number AND ps.rn = 1
        WHERE {where}
        ORDER BY v.registered_at DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)

    return build_paged(items, total or 0, page, page_size)


# ── PUT /vehicles/{vehicle_id} ────────────────────────────────────────────────
@router.put("/{vehicle_id}")
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

    updated = rows(db, "SELECT * FROM vehicles WHERE id = :id", {"id": vehicle_id})
    return updated[0] if updated else {"success": True}


# ── DELETE /vehicles/{vehicle_id} ──────────────────────────────────────────────
@router.delete("/{vehicle_id}")
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
    return {"success": True}


# ── GET /vehicles/export/csv ──────────────────────────────────────────────────
@router.get("/export/csv")
async def export_vehicles_csv(
    search: Optional[str] = Query(None),
    vehicle_type: Optional[str] = Query(None),
    is_registered: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    clauses = ["1=1"]
    params: dict = {}
    if search:
        clauses.append("(plate_number LIKE :search OR owner_name LIKE :search)")
        params["search"] = f"%{search}%"
    if vehicle_type:
        clauses.append("vehicle_type = :vehicle_type")
        params["vehicle_type"] = vehicle_type
    if is_registered is not None:
        clauses.append("is_registered = :is_registered")
        params["is_registered"] = 1 if is_registered else 0

    data = rows(db, f"""
        SELECT
            plate_number  AS [Plate Number],
            owner_name    AS [Owner Name],
            vehicle_type  AS [Vehicle Type],
            employee_id   AS [Employee ID],
            title         AS [Title],
            is_registered AS [Registered],
            registered_at AS [Registered At],
            notes         AS [Notes]
        FROM vehicles
        WHERE {" AND ".join(clauses)}
        ORDER BY registered_at DESC
    """, params)

    headers = ["Plate Number", "Owner Name", "Vehicle Type", "Employee ID",
               "Title", "Registered", "Registered At", "Notes"]
    return stream_csv(data, headers, filename="vehicles.csv")


# ── GET /vehicles/{vehicle_id} ────────────────────────────────────────────────
# Declared LAST so FastAPI matches the specific routes (/kpis, /export/csv) first.
def _session_row_to_dict(r: dict) -> dict:
    duration_seconds = r.get("duration_seconds")
    return {
        "id": r["id"],
        "status": r.get("status"),
        "entry_time": r.get("entry_time"),
        "exit_time": r.get("exit_time"),
        "duration_seconds": duration_seconds,
        "duration_minutes": (duration_seconds // 60) if duration_seconds is not None else None,
        "floor": r.get("floor"),
        "slot_id": r.get("slot_id"),
        "slot_name": r.get("slot_name"),
        "zone_id": r.get("zone_id"),
        "zone_name": r.get("zone_name"),
        "slot_number": r.get("slot_number"),
        "parked_at": r.get("parked_at"),
        "slot_left_at": r.get("slot_left_at"),
        "entry_camera_id": r.get("entry_camera_id"),
        "exit_camera_id": r.get("exit_camera_id"),
        "entry_snapshot_path": r.get("entry_snapshot_path"),
        "exit_snapshot_path": r.get("exit_snapshot_path"),
        "slot_snapshot_path": r.get("slot_snapshot_path"),
    }


@router.get("/{vehicle_id}", response_model=VehicleDetail)
async def get_vehicle(
    vehicle_id: int,
    limit: int = Query(100, ge=1, le=500, description="max sessions to return (most recent first)"),
    date_from: Optional[date] = Query(None, description="filter sessions with entry_time >= this date"),
    date_to: Optional[date] = Query(None, description="filter sessions with entry_time <= this date"),
    db: Session = Depends(get_db),
):
    """Return a vehicle by id, with its parking-session history (entries + exits)."""
    cols = _vehicle_extra_cols(db)

    extra_cols = (
        (", v.is_employee" if cols["is_employee"] else ", NULL AS is_employee") +
        (", v.phone"       if cols["phone"]       else ", NULL AS phone")       +
        (", v.email"       if cols["email"]       else ", NULL AS email")
    )

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
        FROM vehicles v
        WHERE v.id = :vehicle_id
    """, {"vehicle_id": vehicle_id})

    if not vehicle_rows:
        raise HTTPException(404, "Vehicle not found")

    v = vehicle_rows[0]
    plate = v["plate_number"]

    session_clauses = ["ps.plate_number = :plate"]
    session_params: dict = {"plate": plate}
    if date_from:
        session_clauses.append("CAST(ps.entry_time AS DATE) >= :date_from")
        session_params["date_from"] = str(date_from)
    if date_to:
        session_clauses.append("CAST(ps.entry_time AS DATE) <= :date_to")
        session_params["date_to"] = str(date_to)
    session_where = " AND ".join(session_clauses)

    sessions_total = scalar(
        db,
        f"SELECT COUNT(*) FROM parking_sessions ps WHERE {session_where}",
        session_params,
    ) or 0

    session_params["limit"] = limit
    session_rows = rows(db, f"""
        SELECT
            ps.id,
            ps.status,
            ps.entry_time,
            ps.exit_time,
            ps.duration_seconds,
            ps.floor,
            ps.zone_id AS slot_id,
            COALESCE(pk.slot_name, ps.slot_number, ps.zone_id) AS slot_name,
            ps.zone_id,
            ps.zone_name,
            ps.slot_number,
            ps.parked_at,
            ps.slot_left_at,
            ps.entry_camera_id,
            ps.exit_camera_id,
            ps.entry_snapshot_path,
            ps.exit_snapshot_path,
            ps.slot_snapshot_path
        FROM parking_sessions ps
        LEFT JOIN parking_slots pk ON pk.slot_id = ps.zone_id
        WHERE {session_where}
        ORDER BY ps.entry_time DESC
        OFFSET 0 ROWS FETCH NEXT :limit ROWS ONLY
    """, session_params)

    sessions = [_session_row_to_dict(r) for r in session_rows]
    current_session = next(
        (VehicleSession(**s) for s in sessions if s["status"] == "open"),
        None,
    )

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
        is_currently_parked=current_session is not None,
        current_session=current_session,
        sessions_total=sessions_total,
        sessions=[VehicleSession(**s) for s in sessions],
    )