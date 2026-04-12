from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db, scalar, rows
from app.shared import build_paged, stream_csv

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])

# vehicles real columns:
#   id, plate_number, owner_name, vehicle_type, employese_id,
#   is_registered, registered_at, notes, title
# NOTE: is_employee, phone, email added by System 1 migration (ISNULL guarded below)


class VehicleUpdate(BaseModel):
    owner_name:   Optional[str]  = None
    vehicle_type: Optional[str]  = None
    is_employee:  Optional[bool] = None   # requires System 1 migration
    phone:        Optional[str]  = None   # requires System 1 migration
    email:        Optional[str]  = None   # requires System 1 migration
    notes:        Optional[str]  = None
    title:        Optional[str]  = None


@router.get("/kpis")
async def vehicle_kpis(db: Session = Depends(get_db)):
    total = scalar(db, "SELECT COUNT(*) FROM vehicles")

    active = scalar(db,
        "SELECT COUNT(DISTINCT plate_number) FROM parking_sessions WHERE status = 'open'")

    # is_employee may not exist yet — guard with COL_LENGTH
    employee = scalar(db, """
        SELECT CASE
            WHEN COL_LENGTH('vehicles','is_employee') IS NOT NULL
            THEN (SELECT COUNT(*) FROM vehicles WHERE is_employee = 1)
            ELSE 0
        END
    """)

    return {
        "total_vehicles":    total    or 0,
        "active_vehicles":   active   or 0,
        "employee_vehicles": employee or 0,
    }


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
    if is_employee is not None:
        # guard: only apply if column exists
        clauses.append("""
            (COL_LENGTH('vehicles','is_employee') IS NOT NULL
             AND is_employee = :is_employee)
        """)
        params["is_employee"] = 1 if is_employee else 0

    where = " AND ".join(clauses)
    total = scalar(db, f"SELECT COUNT(*) FROM vehicles WHERE {where}", params)

    params["offset"]    = (page - 1) * page_size
    params["page_size"] = page_size

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
            notes,
            -- post-migration columns (NULL if not migrated yet)
            CASE WHEN COL_LENGTH('vehicles','is_employee') IS NOT NULL
                 THEN is_employee ELSE NULL END   AS is_employee,
            CASE WHEN COL_LENGTH('vehicles','phone') IS NOT NULL
                 THEN phone ELSE NULL END          AS phone,
            CASE WHEN COL_LENGTH('vehicles','email') IS NOT NULL
                 THEN email ELSE NULL END          AS email
        FROM vehicles
        WHERE {where}
        ORDER BY registered_at DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)

    return build_paged(items, total or 0, page, page_size)


@router.put("/{vehicle_id}")
async def update_vehicle(
    vehicle_id: int,
    body: VehicleUpdate,
    db: Session = Depends(get_db),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields provided to update")

    # Remove post-migration fields if the column doesn't exist yet
    post_migration = {"is_employee", "phone", "email"}
    safe_updates = {}
    for k, v in updates.items():
        if k in post_migration:
            exists = scalar(db, f"SELECT COL_LENGTH('vehicles', '{k}')")
            if not exists:
                continue
        safe_updates[k] = v

    if not safe_updates:
        raise HTTPException(400, "No applicable fields — run System 1 migration first")

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
            plate_number    AS [Plate Number],
            owner_name      AS [Owner Name],
            vehicle_type    AS [Vehicle Type],
            employee_id     AS [Employee ID],
            title           AS [Title],
            is_registered   AS [Registered],
            registered_at   AS [Registered At],
            notes           AS [Notes]
        FROM vehicles
        WHERE {" AND ".join(clauses)}
        ORDER BY registered_at DESC
    """, params)

    headers = ["Plate Number", "Owner Name", "Vehicle Type", "Employee ID",
               "Title", "Registered", "Registered At", "Notes"]
    return stream_csv(data, headers, filename="vehicles.csv")
