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
from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator


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


def _facility_naive(dt: datetime) -> datetime:
    """Drop any UTC offset a client attached, keeping the wall-clock digits.

    Every timestamp in this API is facility-local NAIVE, because that is what
    the DB stores (see `config.facility_tz`). Pydantic happily parses a
    trailing `Z` into a tz-AWARE datetime, which then meets a naive
    `slot_status.time` from SQL Server and raises
    `TypeError: can't compare offset-naive and offset-aware datetimes`
    somewhere deep in the report maths — a 500, not a 422.

    We strip rather than convert. A browser calling `.toISOString()` on a date
    picker sends the LOCAL day already stamped with `Z`: a KSA-local midnight
    that genuinely meant an instant would arrive as `...T21:00:00.000Z`, not
    `...T00:00:00.000Z`. Converting would silently shift every report 3 hours
    off the operator's calendar. The digits are the intent; the offset is
    noise, so `2026-08-01T00:00:00.000Z`, `2026-08-01T00:00:00+03:00` and
    `2026-08-01T00:00:00` all mean the same facility-local midnight.

    If a caller ever needs true-UTC instants, that is a NEW explicit param
    (`tz=utc`), not a reinterpretation of this one."""
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


# Use on every datetime query param. Accepts naive input unchanged and
# tolerates `Z` / `+HH:MM` instead of 500ing on it.
FacilityNaiveDatetime = Annotated[datetime, AfterValidator(_facility_naive)]


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


class FloorSort(str, Enum):
    """`GET /occupancy/floors?sort=` ordering. `default` keeps the
    `floors.sort_order` layout; the utilization orders rank floors by
    `FloorOccupancy.utilization` (VA slot-status headline)."""
    default = "default"
    most_occupied = "most_occupied"
    least_occupied = "least_occupied"


class OccupancyTrendGrain(str, Enum):
    """`GET /occupancy/history/trend?grain=` x-axis bucketing.

    The frontend picks this — the backend never infers a grain from how long
    the range happens to be, because the same range is drawn differently on a
    wide dashboard and a phone.

    `weekday` is the odd one out: it is not a time series but seven Mon..Sun
    averages (Q5), so its points carry no `bucket_start` and the chart always
    has exactly 7 bars. The other four are chronological, one point per
    calendar bucket that the range actually touches."""
    hour = "hour"
    day = "day"
    week = "week"
    month = "month"
    weekday = "weekday"


class CameraArea(str, Enum):
    """`cameras.area` — physical sub-zone a camera is mounted in. Each floor
    (B1/B2) is split into sections A/B/C plus its RAMP; the gate cameras sit
    outside that grid and get their own two values.

    This is the vocabulary for WRITES and for the `?area=` filter. Responses
    do NOT enforce it — see `schemas.CameraRef.area`. Keep in sync with
    `schemas.CameraAreaLiteral`."""
    B1_A = "B1-A"
    B1_B = "B1-B"
    B1_C = "B1-C"
    RAMP_UP = "RAMP-UP"
    B2_A = "B2-A"
    B2_B = "B2-B"
    B2_C = "B2-C"
    RAMP_DOWN = "RAMP-DOWN"
    GATE_ENTRY = "GATE-ENTRY"
    GATE_EXIT = "GATE-EXIT"


class CameraRole(str, Enum):
    """`cameras.role` — what a camera is wired to do in the deployment.
    Mirrors `schemas.CameraRoleLiteral`; keep both in sync."""
    entry = "entry"
    exit = "exit"
    floor_counting = "floor_counting"
    slot_detection = "slot_detection"
    other = "other"
