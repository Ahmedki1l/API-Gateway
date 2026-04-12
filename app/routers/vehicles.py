from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db, scalar, rows
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
        clauses.append("(plate_number LIKE :search OR owner_name LIKE :search)")
        params["search"] = f"%{search}%"
    if vehicle_type:
        clauses.append("vehicle_type = :vehicle_type")
        params["vehicle_type"] = vehicle_type
    if is_registered is not None:
        clauses.append("is_registered = :is_registered")
        params["is_registered"] = 1 if is_registered else 0
    if is_employee is not None and cols["is_employee"]:
        clauses.append("is_employee = :is_employee")
        params["is_employee"] = 1 if is_employee else 0

    where = " AND ".join(clauses)
    total = scalar(db, f"SELECT COUNT(*) FROM vehicles WHERE {where}", params)

    params["offset"]    = (page - 1) * page_size
    params["page_size"] = page_size

    extra = (
        (", is_employee" if cols["is_employee"] else ", NULL AS is_employee") +
        (", phone"       if cols["phone"]       else ", NULL AS phone")       +
        (", email"       if cols["email"]       else ", NULL AS email")
    )

    items = rows(db, f"""
        SELECT
            id,
            plate_number,
            owner_name,
            vehicle_type,
            employee_id,
            title,
            is_registered,
            registered_at,
            notes
            {extra}
        FROM vehicles
        WHERE {where}
        ORDER BY registered_at DESC
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
