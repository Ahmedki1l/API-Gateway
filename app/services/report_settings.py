"""The reporting window (business hours / days), resolved at request time.

`dbo.report_settings` (single row, id = 1, created by Damanat-DB-Migrator 0010)
is edited from the frontend via PUT /settings/report and read here on every
report request, so a change applies on the next call with no restart.

The .env values (`REPORT_BUSINESS_*`) are the fallback, never an error: a
missing table (migrator not run yet), a missing row, or a row that fails
validation all degrade to the .env window with a warning. A settings row must
never be able to take the reports down.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

from sqlalchemy.orm import Session

from app.config import WEEKDAY_NAMES, parse_business_days, settings
from app.database import rows

log = logging.getLogger(__name__)

_SELECT = """
    SELECT business_hours_enabled, business_hour_from, business_hour_to,
           business_days, updated_at, updated_by
    FROM dbo.report_settings
    WHERE id = 1
"""


@dataclass(frozen=True)
class ReportWindow:
    enabled: bool
    hour_from: int          # inclusive, facility-local
    hour_to: int            # exclusive; 24 = end of day
    weekdays: frozenset     # Mon=0 .. Sun=6
    source: Literal["db", "env"]
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    @property
    def day_names(self) -> list[str]:
        return [WEEKDAY_NAMES[i] for i in sorted(self.weekdays)]


def env_window() -> ReportWindow:
    return ReportWindow(
        enabled=settings.report_business_hours_enabled,
        hour_from=settings.report_business_hour_from,
        hour_to=settings.report_business_hour_to,
        weekdays=settings.business_weekdays,
        source="env",
    )


def validate_window(hour_from: int, hour_to: int, days: str) -> frozenset:
    """Same rules as the .env validators in config.py. Returns the parsed
    weekdays; raises ValueError with an operator-readable message."""
    if not 0 <= hour_from <= 23:
        raise ValueError("business_hour_from must be between 0 and 23")
    if not 1 <= hour_to <= 24:
        raise ValueError("business_hour_to must be between 1 and 24")
    if hour_from >= hour_to:
        raise ValueError("business_hour_from must be less than business_hour_to")
    return parse_business_days(days, "business_days")


def get_report_window(db: Session) -> ReportWindow:
    try:
        found = rows(db, _SELECT)
    except Exception as exc:  # noqa: BLE001 — table absent before migrator 0010
        db.rollback()
        log.warning("report_settings unreadable (%s); using .env reporting window", exc)
        return env_window()
    if not found:
        return env_window()

    r = found[0]
    try:
        hour_from, hour_to = int(r["business_hour_from"]), int(r["business_hour_to"])
        weekdays = validate_window(hour_from, hour_to, r["business_days"] or "")
    except (TypeError, ValueError) as exc:
        log.warning("report_settings row is invalid (%s); using .env reporting window", exc)
        return env_window()

    return ReportWindow(
        enabled=bool(r["business_hours_enabled"]),
        hour_from=hour_from,
        hour_to=hour_to,
        weekdays=weekdays,
        source="db",
        updated_at=r["updated_at"],
        updated_by=r["updated_by"],
    )
