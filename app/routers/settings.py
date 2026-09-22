"""
Runtime-editable settings — the reporting window and per-alert-type severity /
on-off. Both live in tables created by Damanat-DB-Migrator 0010:

  dbo.report_settings  single row; read by the occupancy reports on every
                       request (services/report_settings.py), so a PUT here
                       applies on the next report call.
  dbo.alert_types      one row per alert type. PMS-AI and VideoAnalytics are
                       the readers — they decide severity and whether to record
                       an alert when they create it. The Gateway only edits.

Access control follows the rest of the Gateway: none at the API; the frontend
decides who sees the settings screens.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import WEEKDAY_NAMES, parse_business_days
from app.database import get_db, rows, scalar
from app.schemas import (
    ALERT_LEVELS,
    AlertTypeSetting,
    AlertTypeUpdate,
    ReportSettings,
    ReportSettingsUpdate,
)
from app.services.report_settings import ReportWindow, get_report_window

from app.routers.prefix_injection import (get_prefix)
prefix = get_prefix() + "/settings"

router = APIRouter(prefix=prefix, tags=["Settings"])

_ALERT_TYPE_COLS = (
    "alert_type, display_name, severity, enabled, source, updated_at, updated_by"
)


def _require_table(db: Session, table: str) -> None:
    """A write (or an alert-types read) needs the real table — there is no
    sensible fallback to edit. Say exactly what is missing instead of 500ing."""
    if scalar(db, "SELECT OBJECT_ID(:t, N'U')", {"t": f"dbo.{table}"}) is None:
        raise HTTPException(
            status_code=503,
            detail=f"dbo.{table} does not exist — run Damanat-DB-Migrator "
                   f"(migration 0010) against this database.",
        )


def _to_report_settings(w: ReportWindow) -> ReportSettings:
    return ReportSettings(
        business_hours_enabled=w.enabled,
        business_hour_from=w.hour_from,
        business_hour_to=w.hour_to,
        business_days=w.day_names,
        source=w.source,
        updated_at=w.updated_at,
        updated_by=w.updated_by,
    )


# ── Reporting window ──────────────────────────────────────────────────────────
@router.get("/report", response_model=ReportSettings)
async def get_report_settings(db: Session = Depends(get_db)):
    """The window the occupancy reports use when a request doesn't override it.
    Falls back to the .env values (`source: "env"`) before migration 0010."""
    return _to_report_settings(get_report_window(db))


@router.put("/report", response_model=ReportSettings)
async def update_report_settings(body: ReportSettingsUpdate, db: Session = Depends(get_db)):
    try:
        weekdays = parse_business_days(",".join(body.business_days), "business_days")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _require_table(db, "report_settings")

    params = {
        "enabled": 1 if body.business_hours_enabled else 0,
        "hour_from": body.business_hour_from,
        "hour_to": body.business_hour_to,
        # Stored canonical (Mon..Sun order, three-letter) whatever the caller sent.
        "days": ",".join(WEEKDAY_NAMES[i] for i in sorted(weekdays)),
        "by": body.updated_by,
    }
    updated = db.execute(text("""
        UPDATE dbo.report_settings
           SET business_hours_enabled = :enabled,
               business_hour_from     = :hour_from,
               business_hour_to       = :hour_to,
               business_days          = :days,
               updated_at             = SYSUTCDATETIME(),
               updated_by             = :by
         WHERE id = 1
    """), params)
    if updated.rowcount == 0:
        db.execute(text("""
            INSERT INTO dbo.report_settings
                (id, business_hours_enabled, business_hour_from, business_hour_to,
                 business_days, updated_by)
            VALUES (1, :enabled, :hour_from, :hour_to, :days, :by)
        """), params)
    db.commit()
    return _to_report_settings(get_report_window(db))


# ── Alert types ───────────────────────────────────────────────────────────────
@router.get("/alert-types", response_model=list[AlertTypeSetting])
async def list_alert_types(db: Session = Depends(get_db)):
    _require_table(db, "alert_types")
    return rows(db, f"SELECT {_ALERT_TYPE_COLS} FROM dbo.alert_types ORDER BY display_name")


@router.get("/alert-types/severities", response_model=list[str])
async def list_alert_severities():
    """The severity levels an alert type can be set to, most urgent first."""
    return list(ALERT_LEVELS)


@router.patch("/alert-types/{alert_type}", response_model=AlertTypeSetting)
async def update_alert_type(
    alert_type: str, body: AlertTypeUpdate, db: Session = Depends(get_db),
):
    """Change severity, enabled and/or display_name. PMS-AI and VideoAnalytics
    apply the change to alerts they create from then on; existing alerts keep
    the severity they were raised with."""
    _require_table(db, "alert_types")

    # An explicit null means "not changing" — every column here is NOT NULL.
    changes = {
        k: v for k, v in body.model_dump(exclude_unset=True).items()
        if v is not None and k != "updated_by"
    }
    if not changes:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of severity, enabled, display_name",
        )
    if not scalar(db, "SELECT COUNT(*) FROM dbo.alert_types WHERE alert_type = :t",
                  {"t": alert_type}):
        raise HTTPException(status_code=404, detail=f"Alert type '{alert_type}' not found")

    if "enabled" in changes:
        changes["enabled"] = 1 if changes["enabled"] else 0
    sets = ", ".join(f"{col} = :{col}" for col in changes)
    db.execute(
        text(f"""
            UPDATE dbo.alert_types
               SET {sets}, updated_at = SYSUTCDATETIME(), updated_by = :updated_by
             WHERE alert_type = :alert_type
        """),
        {**changes, "updated_by": body.updated_by, "alert_type": alert_type},
    )
    db.commit()
    return rows(
        db, f"SELECT {_ALERT_TYPE_COLS} FROM dbo.alert_types WHERE alert_type = :t",
        {"t": alert_type},
    )[0]
