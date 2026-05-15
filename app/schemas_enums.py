"""Canonical string enums shared across routers.

Defined once here so the same vocabulary lives in:
- the OpenAPI spec (Swagger / `/docs` shows the allowed values),
- query-param validation (FastAPI returns 422 for typos instead of silently
  returning empty results),
- response-model field types where the value is meaningfully constrained.

All enums inherit `str, Enum` so they serialize as their string value and
plug into `Query(...)` / `Field(...)` annotations directly.
"""
from enum import Enum


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


class CameraRole(str, Enum):
    """`cameras.role` — what a camera is wired to do in the deployment.
    Mirrors `schemas.CameraRoleLiteral`; keep both in sync."""
    entry = "entry"
    exit = "exit"
    floor_counting = "floor_counting"
    slot_detection = "slot_detection"
    other = "other"
