"""The reporting window (business hours / days), resolved at request time.

`dbo.report_settings` (single row, id = 1, created by Damanat-DB-Migrator 0010)
is edited from the frontend via PUT /settings/report and read here on every
report request, so a change applies on the next call with no restart.

The .env values (`REPORT_BUSINESS_*`) are the fallback, never an error: a
missing table (migrator not run yet), a missing row, or a row that fails
validation all degrade to the .env window with a warning. A settings row must
never be able to take the reports down.

Past days use the window that was in force on them, not today's:
`dbo.report_settings_history` (Damanat-DB-Migrator 0012, appended by a trigger
on report_settings) records every window and when it took effect.
`WindowHistory.rule_for(day)` answers "which hours counted on this day" — the
end-of-day job stamps it on the rows it stores, and the reports use it for
days that are not stored.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal, Optional

from sqlalchemy.orm import Session

from app.config import WEEKDAY_NAMES, facility_tz, parse_business_days, settings
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


@dataclass(frozen=True)
class DayRule:
    """Which hours of one day count: hours [hour_from, hour_to) of a working
    day. Business hours turned off is the rule (True, 0, 24)."""
    working_day: bool
    hour_from: int
    hour_to: int

    def counts(self, hour: int) -> bool:
        return self.working_day and self.hour_from <= hour < self.hour_to


def day_rule(window: ReportWindow, day: date) -> DayRule:
    if not window.enabled:
        return DayRule(True, 0, 24)
    return DayRule(day.weekday() in window.weekdays, window.hour_from, window.hour_to)


class WindowHistory:
    """Every window from dbo.report_settings_history, in facility-local time.

    A day uses the window in force at its END: a change made during a day
    applies to that whole day, which is also what the end-of-day job sees when
    it stores the day after midnight. Days after the last change use `current`
    (the live report_settings window), so today can never disagree with the
    settings screen even if the log is behind."""

    def __init__(self, current: ReportWindow, entries: list[tuple[datetime, ReportWindow]]):
        self.current = current
        self.entries = entries          # (valid_from facility-local, window), oldest first

    def window_for(self, day: date) -> ReportWindow:
        day_end = datetime.combine(day + timedelta(days=1), datetime.min.time())
        if not self.entries or self.entries[-1][0] < day_end:
            # No change logged after this day: the current setting applies.
            return self.current
        in_force = [w for since, w in self.entries if since < day_end]
        # Before the first logged change, the earliest known window is the
        # best evidence there is.
        return in_force[-1] if in_force else self.entries[0][1]

    def rule_for(self, day: date) -> DayRule:
        return day_rule(self.window_for(day), day)


_HISTORY_SELECT = """
    SELECT valid_from_utc, business_hours_enabled, business_hour_from,
           business_hour_to, business_days
    FROM dbo.report_settings_history
    ORDER BY valid_from_utc, id
"""


def get_window_history(db: Session) -> WindowHistory:
    """The window log. Without the table (migrator 0012 not run) every day
    uses the current window — the behaviour before the log existed."""
    current = get_report_window(db)
    try:
        found = rows(db, _HISTORY_SELECT)
    except Exception as exc:  # noqa: BLE001 — table absent before migrator 0012
        db.rollback()
        log.warning("report_settings_history unreadable (%s); using the current window for every day", exc)
        return WindowHistory(current, [])

    offset = facility_tz().utcoffset(None)
    entries = []
    for r in found:
        try:
            hour_from, hour_to = int(r["business_hour_from"]), int(r["business_hour_to"])
            weekdays = validate_window(hour_from, hour_to, r["business_days"] or "")
        except (TypeError, ValueError) as exc:
            log.warning("report_settings_history row is invalid (%s); skipped", exc)
            continue
        entries.append((r["valid_from_utc"] + offset, ReportWindow(
            enabled=bool(r["business_hours_enabled"]), hour_from=hour_from,
            hour_to=hour_to, weekdays=weekdays, source="db",
        )))
    return WindowHistory(current, entries)
