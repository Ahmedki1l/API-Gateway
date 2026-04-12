"""
Pydantic v2 response schemas.
These define the exact contract the frontend receives — never expose raw SQL columns.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


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


# ── Occupancy ─────────────────────────────────────────────────────────────────
class OccupancyKPIs(BaseModel):
    total_spots: int
    available_spots: int
    occupied_spots: int
    overall_utilization: float
    total_vehicles: int

class ZoneItem(BaseModel):
    zone_id: int
    zone_name: Optional[str]
    floor: Optional[str]
    camera_id: Optional[str]
    max_capacity: int
    current_count: Optional[int]
    occupied: int
    available: int
    utilization: float
