"""
Pydantic v2 response schemas.
These define the exact contract the frontend receives — never expose raw SQL columns.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ── Shared ────────────────────────────────────────────────────────────────────
class PagedResponse(BaseModel):
    total_count: int
    page: int
    page_size: int
    items: list


# ── Dashboard ─────────────────────────────────────────────────────────────────
class SystemStatus(BaseModel):
    status: Optional[str]
    timestamp: Optional[str]

class AIStatusResponse(BaseModel):
    online: bool
    issues: list[dict]
    system1: SystemStatus
    system2: SystemStatus

class DashboardKPIs(BaseModel):
    total_unique_plates: int
    active_now: int
    open_alerts: int

class ActiveVehicle(BaseModel):
    plate_number: str
    entry_time: Optional[datetime]
    owner_name: Optional[str]
    vehicle_type: Optional[str]
    is_employee: Optional[bool]
    slot: Optional[str]
    floor: Optional[str]
    zone: Optional[str]
    thumbnail_url: Optional[str]


# ── Alerts ────────────────────────────────────────────────────────────────────
class AlertStats(BaseModel):
    active_alerts: int
    critical_violations: int
    resolved_today: int

class AlertItem(BaseModel):
    id: int
    plate_number: Optional[str]
    owner_name: Optional[str]
    vehicle_type: Optional[str]
    alert_type: Optional[str]
    severity: Optional[str]
    slot_id: Optional[str]
    slot_name: Optional[str]
    zone_id: Optional[str]
    zone_name: Optional[str]
    location: Optional[str]
    description: Optional[str]
    screenshot_url: Optional[str]
    triggered_at: Optional[datetime]
    is_resolved: Optional[bool]
    resolved_at: Optional[datetime]


# ── Entry / Exit ──────────────────────────────────────────────────────────────
class EntryExitKPIs(BaseModel):
    total_vehicles: int
    currently_parked: int
    avg_stay_minutes: float
    overstays: int

class TrafficBucket(BaseModel):
    label: str | int
    entries: int
    exits: int

class VehicleEvent(BaseModel):
    id: int
    event_type: str
    entry_time: Optional[datetime]
    exit_time: Optional[datetime]
    floor: Optional[str]
    slot_id: Optional[str]
    slot: Optional[str]
    zone: Optional[str]
    screenshot_url: Optional[str]
    duration_minutes: Optional[int]

class VehicleWithEvents(BaseModel):
    plate_number: str
    owner_name: Optional[str]
    vehicle_type: Optional[str]
    is_employee: Optional[bool]
    events: list[VehicleEvent]


# ── Vehicles ──────────────────────────────────────────────────────────────────
class VehicleKPIs(BaseModel):
    total_vehicles: int
    active_vehicles: int
    employee_vehicles: int

class VehicleItem(BaseModel):
    id: int
    plate_number: str
    owner_name: Optional[str]
    vehicle_type: Optional[str]
    is_employee: Optional[bool]
    phone: Optional[str]
    email: Optional[str]
    notes: Optional[str]
    created_at: Optional[datetime]


class VehicleSession(BaseModel):
    id: int
    status: Optional[str]
    entry_time: Optional[datetime]
    exit_time: Optional[datetime]
    duration_seconds: Optional[int]
    duration_minutes: Optional[int]
    floor: Optional[str]
    slot_id: Optional[str]
    slot_name: Optional[str]
    zone_id: Optional[str]
    zone_name: Optional[str]
    slot_number: Optional[str]
    parked_at: Optional[datetime]
    slot_left_at: Optional[datetime]
    entry_camera_id: Optional[str]
    exit_camera_id: Optional[str]
    entry_snapshot_path: Optional[str]
    exit_snapshot_path: Optional[str]
    slot_snapshot_path: Optional[str]


class VehicleDetail(BaseModel):
    id: int
    plate_number: str
    owner_name: Optional[str]
    vehicle_type: Optional[str]
    employee_id: Optional[str]
    title: Optional[str]
    is_registered: Optional[bool]
    registered_at: Optional[datetime]
    notes: Optional[str]
    is_employee: Optional[bool]
    phone: Optional[str]
    email: Optional[str]
    is_currently_parked: bool
    current_session: Optional[VehicleSession]
    sessions_total: int
    sessions: list[VehicleSession]


# ── Occupancy ─────────────────────────────────────────────────────────────────
class OccupancyKPIs(BaseModel):
    total_spots: int
    available_spots: int
    occupied_spots: int
    overall_utilization: float
    total_vehicles: int

class ZoneItem(BaseModel):
    zone_id: str
    zone_name: Optional[str]
    floor: Optional[str]
    camera_id: Optional[str]
    max_capacity: int
    current_count: Optional[int]
    occupied: int
    available: int
    utilization: float


# ── Cameras ───────────────────────────────────────────────────────────────────
_DEFAULT_RTSP_PATH = "/Streaming/Channels/101"


class CameraItem(BaseModel):
    id: int
    camera_id: str
    name: Optional[str]
    floor: Optional[str]
    zone_id: Optional[str]
    ip_address: str
    rtsp_port: int
    rtsp_path: str
    username: Optional[str]
    has_password: bool
    rtsp_url_masked: str
    enabled: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_check_at: Optional[datetime]
    last_seen_at: Optional[datetime]
    last_status: Optional[str]
    is_online: bool


class CameraCreate(BaseModel):
    camera_id: str = Field(..., min_length=1, max_length=50)
    name: Optional[str] = None
    floor: Optional[str] = None
    zone_id: Optional[str] = None
    ip_address: str = Field(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:\-]+$")
    rtsp_port: int = Field(554, ge=1, le=65535)
    rtsp_path: str = _DEFAULT_RTSP_PATH
    username: Optional[str] = None
    password: Optional[str] = None
    enabled: bool = True
    notes: Optional[str] = None

    @field_validator("rtsp_path")
    @classmethod
    def _ensure_leading_slash(cls, v: str) -> str:
        if not v:
            return _DEFAULT_RTSP_PATH
        return v if v.startswith("/") else f"/{v}"


class CameraUpdate(BaseModel):
    # camera_id intentionally absent — renaming the business key would orphan event rows
    name: Optional[str] = None
    floor: Optional[str] = None
    zone_id: Optional[str] = None
    ip_address: Optional[str] = Field(None, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:\-]+$")
    rtsp_port: Optional[int] = Field(None, ge=1, le=65535)
    rtsp_path: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    enabled: Optional[bool] = None
    notes: Optional[str] = None

    @field_validator("rtsp_path")
    @classmethod
    def _ensure_leading_slash(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        return v if v.startswith("/") else f"/{v}"


class CameraCredentials(BaseModel):
    username: Optional[str]
    password: Optional[str]
    rtsp_url: str


class CameraWithCredentials(CameraItem):
    password: Optional[str]
    rtsp_url: str


class CameraInternalListResponse(BaseModel):
    total: int
    fetched_at: datetime
    cameras: list[CameraWithCredentials]
    decryption_errors: list[dict]


class CameraKPIs(BaseModel):
    total: int
    enabled: int
    disabled: int
    online: int
    offline: int
    by_floor: dict[str, int]
    by_status: dict[str, int]


class CameraCheckResult(BaseModel):
    camera_id: str
    is_online: bool
    last_status: Optional[str]
    last_check_at: Optional[datetime]
    last_seen_at: Optional[datetime]
