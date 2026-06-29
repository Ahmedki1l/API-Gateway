"""Canonical string enums shared across routers.

Defined once here so the same vocabulary lives in:
- the OpenAPI spec (Swagger / `/docs` shows the allowed values),
- query-param validation (FastAPI returns 422 for typos instead of silently
  returning empty results),
- response-model field types where the value is meaningfully constrained.

All enums inherit `str, Enum` so they serialize as their string value and
plug into `Query(...)` / `Field(...)` annotations directly.

Also exposes `StrictQueryBool` — a query-param boolean that accepts ONLY
the strings `"true"` or `"false"` (rejects `"1"`, `"0"`, `"yes"`, `"on"`,
etc.). Use when the operator wants the contract to be strict on boolean
filters.
"""
from enum import Enum
from typing import Annotated

from pydantic import BeforeValidator


def _strict_query_bool(v):
    """Accept only `true` / `false` strings (case-insensitive) or actual
    Python booleans. Rejects integers, `"1"` / `"0"`, `"yes"` / `"no"`."""
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s == "true":
            return True
        if s == "false":
            return False
    raise ValueError("must be 'true' or 'false'")


# Use on query params where you want strict bool input from URL strings.
# `StrictBool` (Pydantic) only accepts Python bools — fine for JSON bodies,
# wrong for query params (where everything arrives as a string).
StrictQueryBool = Annotated[bool, BeforeValidator(_strict_query_bool)]


class AlertSeverity(str, Enum):
    """Alert urgency. Sourced from `alerts.severity` column (post-schema-v2)
    or derived from `alert_type` on pre-migration deployments — see
    `routers/alerts.py:_alert_query_bits` for the CASE expression."""
    critical = "critical"
    warning = "warning"
    info = "info"


class AlertType(str, Enum):
    """Canonical alert categories raised by System 1 / System 2.

    Values mirror the production CASE branches in
    `routers/alerts.py:_alert_query_bits` and the dashboard critical-alert
    SQL. Extend here when upstream services start emitting a new alert_type.
    """
    violence = "violence"
    intrusion = "intrusion"
    vehicle_intrusion = "vehicle_intrusion"
    vehicle_violation = "vehicle_violation"
    named_slot_violation = "named_slot_violation"
    special_needs_violation = "special_needs_violation"
    unknown_vehicle = "unknown_vehicle"
    overstay = "overstay"
    capacity_exceeded = "capacity_exceeded"


class ParkingSessionStatus(str, Enum):
    """`parking_sessions.status` values — the lifecycle of a parking event."""
    open = "open"
    closed = "closed"
    overstay = "overstay"
    unknown_exit = "unknown_exit"


class EntryExitDirection(str, Enum):
    """Gate-crossing direction on entry_exit_log / VehicleEvent rows."""
    entry = "entry"
    exit = "exit"


class ReservationType(str, Enum):
    """`parking_slots.reservation_type` — operator-facing slot classification.
    Pre-WS-8 migration normalised values to uppercase (see bootstrap section 4g)."""
    GENERAL = "GENERAL"
    SPECIAL = "SPECIAL"
    EMPLOYEE = "EMPLOYEE"


class SlotType(str, Enum):
    """`parking_slots.slot_type` — internal occupancy-filter class. `regular`
    is the only countable type; `special_zone` / `roi` are virtual zones."""
    regular = "regular"
    special_zone = "special_zone"
    roi = "roi"


class CameraArea(str, Enum):
    """`cameras.area` — physical sub-zone a camera is mounted in. Fixed
    vocabulary: each floor (B1/B2) is split into sections A/B/C plus its RAMP."""
    B1_A = "B1-A"
    B1_B = "B1-B"
    B1_C = "B1-C"
    B1_RAMP = "B1-RAMP"
    B2_A = "B2-A"
    B2_B = "B2-B"
    B2_C = "B2-C"
    B2_RAMP = "B2-RAMP"


class CameraRole(str, Enum):
    """`cameras.role` — what a camera is wired to do in the deployment.
    Mirrors `schemas.CameraRoleLiteral`; keep both in sync."""
    entry = "entry"
    exit = "exit"
    floor_counting = "floor_counting"
    slot_detection = "slot_detection"
    other = "other"
