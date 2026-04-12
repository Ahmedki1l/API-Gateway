from datetime import date
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db, scalar, rows
from app.shared import build_paged, stream_csv

router = APIRouter(prefix="/alerts", tags=["Alerts"])


# ── Column existence — checked once per process, cached forever ───────────────
@lru_cache(maxsize=None)
def _alerts_extra_cols() -> dict:
    """
    Checks which post-migration columns exist on the alerts table.
    Result is cached for the process lifetime — restart gateway after migration.
    """
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        def exists(col):
            n = db.execute(text("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'alerts' AND COLUMN_NAME = :c
            """), {"c": col}).scalar()
            return (n or 0) > 0
        return {
            "severity":         exists("severity"),
            "location_display": exists("location_display"),
        }
    finally:
        db.close()


def _severity_expr(cols: dict) -> str:
    if cols["severity"]:
        return "a.severity"
    return (
        "CASE "
        "WHEN a.alert_type IN ('violence','intrusion') THEN 'critical' "
        "WHEN a.alert_type IN ('unknown_vehicle','named_slot_violation','overstay') THEN 'warning' "
        "ELSE 'info' END"
    )


def _location_expr(cols: dict) -> str:
    if cols["location_display"]:
        return "a.location_display"
    return (
        "CASE "
        "WHEN a.slot_number IS NOT NULL THEN 'Slot ' + a.slot_number "
        "WHEN a.zone_name   IS NOT NULL THEN a.zone_name "
        "ELSE a.camera_id END"
    )


# ── WHERE builder ─────────────────────────────────────────────────────────────
def _where(search, severity, alert_type, resolved, date_from, date_to, cols):
    clauses = ["a.is_test = 0"]
    params: dict = {}

    if search:
        clauses.append(
            "(a.plate_number LIKE :search"
            " OR a.zone_name LIKE :search"
            " OR a.description LIKE :search)"
        )
        params["search"] = f"%{search}%"

    if severity:
        if cols["severity"]:
            clauses.append("a.severity = :severity")
            params["severity"] = severity
        else:
            if severity == "critical":
                clauses.append("a.alert_type IN ('violence','intrusion')")
            elif severity == "warning":
                clauses.append("a.alert_type IN ('unknown_vehicle','named_slot_violation','overstay')")
            else:
                clauses.append("a.alert_type NOT IN ('violence','intrusion','unknown_vehicle','named_slot_violation','overstay')")

    if alert_type:
        clauses.append("a.alert_type = :alert_type")
        params["alert_type"] = alert_type

    if resolved is not None:
        clauses.append("a.is_resolved = :resolved")
        params["resolved"] = 1 if resolved else 0

    if date_from:
        clauses.append("CAST(a.triggered_at AS DATE) >= :date_from")
        params["date_from"] = str(date_from)

    if date_to:
        clauses.append("CAST(a.triggered_at AS DATE) <= :date_to")
        params["date_to"] = str(date_to)

    return " AND ".join(clauses), params


# ── 1. Stats ──────────────────────────────────────────────────────────────────
@router.get("/stats")
async def alert_stats(db: Session = Depends(get_db)):
    cols = _alerts_extra_cols()

    if cols["severity"]:
        critical_sql = "SELECT COUNT(*) FROM alerts WHERE is_resolved=0 AND is_test=0 AND severity='critical'"
    else:
        critical_sql = "SELECT COUNT(*) FROM alerts WHERE is_resolved=0 AND is_test=0 AND alert_type IN ('violence','intrusion')"

    return {
        "active_alerts":      scalar(db, "SELECT COUNT(*) FROM alerts WHERE is_resolved=0 AND is_test=0"),
        "critical_violations": scalar(db, critical_sql),
        "resolved_today":      scalar(db, """
            SELECT COUNT(*) FROM alerts
            WHERE is_resolved=1 AND is_test=0
              AND CAST(resolved_at AS DATE) = CAST(GETDATE() AS DATE)
        """),
    }


# ── 2. Paginated list ─────────────────────────────────────────────────────────
@router.get("/")
async def get_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    cols  = _alerts_extra_cols()
    where, params = _where(search, severity, alert_type, resolved, date_from, date_to, cols)
    offset = (page - 1) * page_size
    total  = scalar(db, f"SELECT COUNT(*) FROM alerts a WHERE {where}", params)

    params["offset"]    = offset
    params["page_size"] = page_size

    sev_expr = _severity_expr(cols)
    loc_expr = _location_expr(cols)

    items = rows(db, f"""
        SELECT
            a.id,
            a.alert_type,
            a.event_type,
            {sev_expr}  AS severity,
            a.plate_number,
            a.camera_id,
            a.zone_id,
            a.zone_name,
            a.region_id,
            a.slot_number,
            {loc_expr}  AS location_display,
            a.description,
            a.snapshot_path,
            a.is_resolved,
            a.resolved_at,
            a.triggered_at,
            v.owner_name,
            v.vehicle_type
        FROM alerts a
        LEFT JOIN vehicles v ON v.plate_number = a.plate_number
        WHERE {where}
        ORDER BY a.triggered_at DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)

    return build_paged(items, total or 0, page, page_size)


# ── 3. Resolve ────────────────────────────────────────────────────────────────
@router.patch("/{alert_id}/resolve")
async def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    result = db.execute(
        text("UPDATE alerts SET is_resolved=1, resolved_at=GETDATE() WHERE id=:id AND is_resolved=0"),
        {"id": alert_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Alert not found or already resolved")
    return {"success": True, "alert_id": alert_id}


# ── 4. Delete ─────────────────────────────────────────────────────────────────
@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    result = db.execute(text("DELETE FROM alerts WHERE id=:id"), {"id": alert_id})
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Alert not found")
    return {"success": True, "alert_id": alert_id}


# ── 5. CSV export ─────────────────────────────────────────────────────────────
@router.get("/export/csv")
async def export_alerts_csv(
    search: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    cols  = _alerts_extra_cols()
    where, params = _where(search, severity, alert_type, resolved, date_from, date_to, cols)
    sev_expr = _severity_expr(cols)
    loc_expr = _location_expr(cols)

    data = rows(db, f"""
        SELECT
            a.id            AS [ID],
            a.plate_number  AS [Plate Number],
            v.owner_name    AS [Owner],
            a.alert_type    AS [Type],
            a.event_type    AS [Event Type],
            {sev_expr}      AS [Severity],
            {loc_expr}      AS [Location],
            a.description   AS [Description],
            a.snapshot_path AS [Snapshot],
            a.triggered_at  AS [Triggered At],
            a.is_resolved   AS [Resolved],
            a.resolved_at   AS [Resolved At]
        FROM alerts a
        LEFT JOIN vehicles v ON v.plate_number = a.plate_number
        WHERE {where}
        ORDER BY a.triggered_at DESC
    """, params)

    headers = ["ID", "Plate Number", "Owner", "Type", "Event Type", "Severity",
               "Location", "Description", "Snapshot", "Triggered At", "Resolved", "Resolved At"]
    return stream_csv(data, headers, filename="alerts.csv")
