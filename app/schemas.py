"""
Pydantic v2 response schemas — the exact contract the frontend receives.

Phase 2 target state:
  - Zones are gone (Floor is the only spatial grouping).
  - Three-tier references: `plate_number` → `vehicle_id` → `vehicle_event_id`
    on Slot, Alert, ActiveVehicle, EntryExitEvent.
  - Rich detail DTOs (SlotDetail, AlertDetail, FloorDetail) give the frontend
    everything a screen needs in one fetch.
  - Camera carries `role` + `watches_floor`/`watches_slots`.
  - SSE alert stream emits AlertStreamEvent.
"""
from datetime import datetime
from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")

CameraRoleLiteral = Literal["entry", "exit", "floor_counting", "slot_detection", "other"]


# ── Shared envelope ───────────────────────────────────────────────────────────
class SuccessResponse(BaseModel):
    """Bare success flag for endpoints that don't echo back any entity."""
    success: bool = True


class EntityActionResponse(BaseModel):
    """For DELETE/PATCH endpoints that confirm success and echo the affected id.
    `id` is `int | str` because some entities key on int (alerts, vehicles)
    while others key on string business keys (cameras: camera_id, slots: slot_id)."""
    success: bool = True
    id: int | str


class PagedResponse(BaseModel, Generic[T]):
    total_count: int
    page: int
    page_size: int
    items: list[T]


# ── Reference types (reusable building blocks) ───────────────────────────────
class VehicleRef(BaseModel):
    # `id` is optional because the same vehicle concept covers BOTH registered
    # vehicles (rows in the `vehicles` table) and plates that have only ever
    # appeared in `parking_sessions`. Unregistered plates have null id; the
    # frontend should key on plate_number for those.
    id: Optional[int] = None
    plate_number: str
    owner_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    is_employee: Optional[bool] = None
    employee_id: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_registered: bool = False
    registered_at: Optional[datetime] = None
    notes: Optional[str] = None
    # Mirror of `vehicles.current_slot_id` — written by PMS-AI on every
    # bind-slot (parking_session_service.py:141), cleared on unbind (:178-179).
    # Faster than digging into current_event for "where is plate X right now?"
    # current_slot_name is resolved via LEFT JOIN parking_slots.
    current_slot_id: Optional[str] = None
    current_slot_name: Optional[str] = None


class SlotRef(BaseModel):
    # Phase-1 of WS-8 floor refactor; integer PK from `parking_slots.id`.
    # Optional during rollout — legacy rows backfilled to non-null but stay Optional
    # until the destructive cutover phase removes the string-keyed slot_id.
    id: Optional[int] = None
    slot_id: str
    slot_name: Optional[str] = None
    floor: Optional[str] = None
    # Phase-1 of WS-8 floor refactor; populated alongside `floor` while both keys live.
    floor_id: Optional[int] = None
    is_available: bool = True
    is_violation_slot: bool = False
    polygon: Optional[list] = None


class CameraRef(BaseModel):
    id: int
    camera_id: str
    name: Optional[str] = None
    floor: Optional[str] = None
    # Phase-1 of WS-8 floor refactor; populated alongside `floor` while both keys live.
    floor_id: Optional[int] = None
    role: CameraRoleLiteral = "other"
    watches_floor: Optional[str] = None
    # Phase-1 of WS-8 floor refactor; populated alongside `watches_floor` while both keys live.
    watches_floor_id: Optional[int] = None
    watches_slots: Optional[list[str]] = None


# ── Dashboard ─────────────────────────────────────────────────────────────────
class SystemStatus(BaseModel):
    """One upstream's connectivity snapshot for the dashboard's AI-status card.

    `name` is the human-readable label ("PMS-AI", "VideoAnalytics") so the
    frontend can render the row directly without mapping a key like
    `system1` → "PMS-AI" itself. `health` collapses the upstream's raw
    status string into a small vocabulary the UI styles consistently
    (`healthy` / `degraded` / `unreachable`).
    """
    name: str
    health: str
    # `timestamp`: whatever the upstream's /health endpoint reports (might be
    # null when the upstream is unreachable).
    timestamp: Optional[str] = None
    # `last_connected_at`: the most recent successful connection from the
    # Gateway side. Survives upstream outages — useful for "last seen at …" UI.
    last_connected_at: Optional[datetime] = None


class AIStatusResponse(BaseModel):
    """Aggregate health across the upstream AI services. `overall_health` is
    derived from the per-system healths: `healthy` when every system is up,
    `down` when none are, `degraded` in between."""
    overall_health: str
    issues: list[dict]
    systems: list[SystemStatus]


class DashboardKPIs(BaseModel):
    total_unique_plates: int
    plates_seen_today: int
    active_now: int
    open_alerts: int


class ActiveVehicle(BaseModel):
    plate_number: str
    vehicle_id: Optional[int] = None
    entry_time: Optional[datetime] = None
    owner_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    is_employee: Optional[bool] = None
    floor: Optional[str] = None
    # Phase-1 of WS-8 floor refactor; populated alongside `floor` while both keys live.
    floor_id: Optional[int] = None
    slot_id: Optional[str] = None
    slot_name: Optional[str] = None
    vehicle_event_id: Optional[int] = None
    thumbnail_url: Optional[str] = None


# ── Events: CameraEvent → EntryExitEvent → VehicleEvent ──────────────────────
class CameraEvent(BaseModel):
    """Raw Hikvision trigger. Only `anpr` and `linedetection` consumed."""
    id: int
    camera_id: str
    event_type: Literal["anpr", "linedetection"]
    trigger_time: datetime
    event_state: Optional[Literal["active", "inactive"]] = None
    plate_number: Optional[str] = None
    snapshot_url: Optional[str] = None
    device_serial: Optional[str] = None
    channel_id: Optional[int] = None
    channel_name: Optional[str] = None
    region_id: Optional[str] = None
    status: Literal["processed", "dropped"] = "processed"
    drop_reason: Optional[str] = None
    produced_entry_exit_id: Optional[int] = None
    produced_floor_delta: Optional[int] = None
    created_at: Optional[datetime] = None


class EntryExitEvent(BaseModel):
    """Atomic gate crossing — reusable standalone and nested in VehicleEvent."""
    id: Optional[int] = None
    plate_number: str
    vehicle_id: Optional[int] = None
    direction: Literal["entry", "exit"]
    camera_id: Optional[str] = None
    event_time: Optional[datetime] = None
    snapshot_url: Optional[str] = None
    matched_entry_id: Optional[int] = None
    vehicle_event_id: Optional[int] = None
    camera_event_id: Optional[int] = None
    plate_confidence: Optional[float] = None


class VehicleEvent(BaseModel):
    """Complete parking event — nested entry + optional exit + slot binding.

    Includes denormalized vehicle metadata (owner_name / vehicle_type /
    is_employee) so the entry-exit list can render rows without a second fetch
    against /vehicles/{id}. These three fields are joined in at query time
    from the `vehicles` table (or the parking_sessions row itself when the
    plate isn't registered)."""
    id: int
    vehicle_id: Optional[int] = None
    plate_number: str
    # Vehicle metadata (denormalized — null for unregistered plates)
    owner_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    is_employee: Optional[bool] = None
    status: Optional[str] = None  # "open" | "closed" | "overstay"
    entry: EntryExitEvent
    exit: Optional[EntryExitEvent] = None
    duration_seconds: Optional[int] = None
    slot_id: Optional[str] = None
    slot_name: Optional[str] = None
    slot_number: Optional[str] = None
    floor: Optional[str] = None
    # Phase-1 of WS-8 floor refactor; populated alongside `floor` while both keys live.
    floor_id: Optional[int] = None
    parked_at: Optional[datetime] = None
    slot_left_at: Optional[datetime] = None
    slot_camera_id: Optional[str] = None
    slot_snapshot_url: Optional[str] = None


# ── Alerts ────────────────────────────────────────────────────────────────────
class AlertStats(BaseModel):
    active_alerts: int
    critical_violations: int
    resolved_today: int


class AlertItem(BaseModel):
    """Canonical alert row — denormalized join over vehicles/slots/cameras.
    Same shape used by list rows, stream events, and detail (which extends it)."""
    id: int
    alert_type: Optional[str] = None
    severity: Optional[str] = None
    event_type: Optional[str] = None
    camera_id: Optional[str] = None
    plate_number: Optional[str] = None
    vehicle_id: Optional[int] = None
    owner_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    slot_id: Optional[str] = None
    slot_name: Optional[str] = None
    floor: Optional[str] = None
    # Phase-1 of WS-8 floor refactor; populated alongside `floor` while both keys live.
    floor_id: Optional[int] = None
    vehicle_event_id: Optional[int] = None
    triggering_camera_event_id: Optional[int] = None
    description: Optional[str] = None
    location: Optional[str] = None
    snapshot_url: Optional[str] = None
    triggered_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    is_resolved: Optional[bool] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None


class AlertStreamEventLite(BaseModel):
    """The actual SSE payload shape emitted by /alerts/stream.

    Lean by design — real-time consumers want a small, predictable wire format.
    For the rich joined shape (owner_name, vehicle_event_id, audit columns,
    description, etc.) the frontend should fetch `GET /alerts/{id}` after
    receiving an event with that id.

    Field naming aligns with `AlertItem` so a streamed event and a list row
    share the same key vocabulary (`triggered_at`, not `timestamp`)."""
    id: Optional[int] = None
    source_system: Literal["gateway", "pms_ai", "video_analytics", "test_system"]
    alert_type: Optional[str] = None
    severity: Optional[str] = None
    slot_id: Optional[str] = None
    slot_name: Optional[str] = None
    plate_number: Optional[str] = None
    camera_id: Optional[str] = None
    floor: Optional[str] = None
    # Phase-1 of WS-8 floor refactor; populated alongside `floor` while both keys live.
    floor_id: Optional[int] = None
    snapshot_url: Optional[str] = None
    triggered_at: Optional[str] = None
    is_alert: bool = True  # false for keep-alive / connection_established


# Back-compat: keep the old name pointing at the new lite shape so any importer
# (incl. external SDK clients) stays happy. Phase 4C deletes this alias.
AlertStreamEvent = AlertStreamEventLite


class AlertDetail(AlertItem):
    """One fetch gives the frontend everything for the alert detail view."""
    vehicle: Optional[VehicleRef] = None
    slot: Optional[SlotRef] = None
    camera: Optional[CameraRef] = None
    vehicle_event: Optional[VehicleEvent] = None
    related_alerts: list[AlertItem] = []


class AlertResolve(BaseModel):
    """Body for PATCH /alerts/{id}/resolve."""
    resolution_notes: Optional[str] = None


class VehicleEventDetail(VehicleEvent):
    """GET /entry-exit/{id} response — VehicleEvent + joined vehicle/slot/camera
    refs + alerts raised during this parking event."""
    vehicle: Optional[VehicleRef] = None
    slot: Optional[dict] = None
    entry_camera: Optional[CameraRef] = None
    exit_camera: Optional[CameraRef] = None
    alerts: list[AlertItem] = []


# ── Entry / Exit ──────────────────────────────────────────────────────────────
class EntryExitKPIs(BaseModel):
    total_vehicles_today: int
    currently_parked: int
    avg_stay_minutes: float
    overstays: int


class TrafficBucket(BaseModel):
    label: str | int
    entries: int
    exits: int


# ── Vehicles ──────────────────────────────────────────────────────────────────
class VehicleKPIs(BaseModel):
    total_vehicles: int
    active_vehicles: int
    employee_vehicles: int


class VehicleCreate(BaseModel):
    plate_number: str
    owner_name: Optional[str] = None
    employee_id: Optional[str] = None
    vehicle_type: Optional[str] = None
    title: Optional[str] = None
    is_employee: Optional[bool] = False
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


class VehicleUpdate(BaseModel):
    plate_number: Optional[str] = None
    owner_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None
    is_employee: Optional[bool] = False
    phone: Optional[str] = None
    email: Optional[str] = None


class VehicleListItem(VehicleRef):
    """List row — VehicleRef + current-parking context.
    Phase 2 keeps the flat `parked_at`/`parking_status`/`floor` fields so the
    existing `/vehicles/` list endpoint keeps working without router SQL surgery.
    `current_event` is the target nested shape; it's populated once routers build
    a full VehicleEvent per row (deferred task)."""
    parked_at: Optional[datetime] = None
    parking_status: Optional[str] = None
    floor: Optional[str] = None
    # Phase-1 of WS-8 floor refactor; populated alongside `floor` while both keys live.
    floor_id: Optional[int] = None
    current_event: Optional[VehicleEvent] = None


# Back-compat alias so existing Gateway router imports keep working.
VehicleItem = VehicleListItem


class VehicleStats(BaseModel):
    total_visits: int = 0
    total_parked_seconds: int = 0
    avg_stay_seconds: float = 0.0


class VehicleDetail(VehicleListItem):
    """Detail response for `GET /vehicles/{id}`. Inherits the flat
    current-parking fields (`parked_at`, `parking_status`, `floor`,
    `floor_id`) and `current_event` from `VehicleListItem`, then adds the
    detail-only enrichments below."""
    is_currently_parked: bool = False
    events_total: int = 0
    events: list[VehicleEvent] = []
    recent_alerts: list[AlertItem] = []
    stats: Optional[VehicleStats] = None


# ── Occupancy — floor + slot ─────────────────────────────────────────────────
class OccupancyKPIs(BaseModel):
    total_spots: int
    available_spots: int
    # Primary occupied count — same data source as /occupancy/floors[].current_count
    # (line-crossing counters in zone_occupancy / floor_occupancy). This is the
    # number ops trusts; the UI should display this as "occupied".
    occupied_spots: int
    # Secondary occupied count from VA's slot-status table (computer-vision).
    # When `slot_occupied_spots != occupied_spots` the two sources have drifted;
    # the dashboard can surface this as a reconciliation warning.
    slot_occupied_spots: int = 0
    overall_utilization: float
    total_vehicles: int


class OccupancyTotals(BaseModel):
    """Replaces the synthetic `GARAGE-TOTAL` zone_occupancy row — same semantics,
    computed on the fly."""
    total_slots: int
    occupied_slots: int
    available_slots: int
    overall_utilization: float
    total_vehicles: int


class FloorOccupancy(BaseModel):
    """One floor's occupancy — reconciles the two independent data sources
    (PMS-AI line crossings vs. VA slot aggregation)."""
    # Phase-1 of WS-8 floor refactor; integer PK from `floors.id`. The
    # canonical floor identifier — every other DTO (slot, alert, vehicle,
    # camera) refers to a floor via `floor_id`, so FloorOccupancy uses the
    # same field name. Pairs with `floor: str` business-key while both live.
    floor_id: Optional[int] = None
    floor: str
    max_capacity: int
    current_count: int
    available: int
    utilization: float
    data_source: Literal["line_crossing", "slot_aggregation"] = "line_crossing"
    last_updated: Optional[datetime] = None
    camera_id: Optional[str] = None
    slot_occupancy_count: int = 0
    slot_occupancy_source: Literal["va_cv"] = "va_cv"
    reconciled: bool = True
    # `cars_in_floor` is the line-crossing count (cars that entered the floor
    # via the entry camera and haven't been counted exiting). `slots_occupied`
    # is `slot_occupancy_count` aliased — VA's CV count of slots whose latest
    # status is non-vacant. When `cars_in_floor > slots_occupied` the gap is
    # cars that entered but aren't parked yet (driving around / blocking
    # aisles / line-crossing drift). When equal, the floor is reconciled.
    cars_in_floor: int = 0
    slots_occupied: int = 0
    cars_unparked: int = 0  # max(cars_in_floor - slots_occupied, 0)


class SlotOccupancy(BaseModel):
    """Current occupancy of a slot. Null on SlotDetail when state is VACANT."""
    state: Literal["VACANT", "ENTERING", "OCCUPIED", "LEAVING"]
    plate_number: Optional[str] = None
    vehicle_id: Optional[int] = None
    vehicle_event_id: Optional[int] = None
    since: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    snapshot_url: Optional[str] = None


class LastOccupant(BaseModel):
    """Populated on SlotDetail when current is None — shows last car that parked."""
    plate_number: str
    vehicle_id: Optional[int] = None
    vehicle_event_id: Optional[int] = None
    left_at: datetime


class SlotDetail(SlotRef):
    current: Optional[SlotOccupancy] = None
    last_occupant: Optional[LastOccupant] = None
    watched_by: Optional[CameraRef] = None
    recent_events: list[VehicleEvent] = []
    recent_alerts: list[AlertItem] = []
    stats: Optional[dict] = None


class FloorDetail(FloorOccupancy):
    """Forward-compat enrichment shape for GET /occupancy/floors/{floor}.
    Currently unwired — the endpoint returns plain `FloorOccupancy`. Wire this
    when the frontend wants per-floor `slots[]`, `current_vehicles[]`, and
    `recent_alerts[]` in a single fetch."""
    slots: list[SlotDetail] = []
    current_vehicles: list[VehicleListItem] = []
    recent_alerts: list[AlertItem] = []


class SlotListItem(BaseModel):
    """Flat slot row used by /occupancy/slots and /occupancy/slots/by-floor.
    Lighter than `SlotDetail` (no nested current/last_occupant/recent_*)
    because list views just need the latest VA status to color the grid."""
    slot_id: str
    slot_name: Optional[str] = None
    floor: Optional[str] = None
    # Phase-1 of WS-8 floor refactor; populated alongside `floor` while both keys live.
    floor_id: Optional[int] = None
    is_available: Optional[bool] = None
    is_violation_slot: Optional[bool] = Field(
        default=None,
        validation_alias="is_violation_zone",
        serialization_alias="is_violation_slot",
    )
    current_plate: Optional[str] = None
    current_status: Optional[str] = None
    status_updated_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}


class FloorSlotGroup(BaseModel):
    """Response shape for GET /occupancy/slots/by-floor — one group per floor
    with the slot list inline. Replaces the deprecated `?grouped=true` query
    param shape on the legacy /occupancy/slots endpoint."""
    floor: str
    # Phase-1 of WS-8 floor refactor; populated alongside `floor` while both keys live.
    floor_id: Optional[int] = None
    slots: list[SlotListItem]


# Deprecated — kept so Phase 1 callers of /occupancy/zones still compile.
# Populated identically to FloorOccupancy; Phase 4C removes the alias entirely.
class ZoneItem(BaseModel):
    id: Optional[int] = None
    zone_id: str
    zone_name: Optional[str] = None
    floor: Optional[str] = None
    # Phase-1 of WS-8 floor refactor; populated alongside `floor` while both keys live.
    floor_id: Optional[int] = None
    camera_id: Optional[str] = None
    max_capacity: int
    current_count: Optional[int] = None
    last_updated: Optional[datetime] = None
    occupied: int
    available: int
    utilization: float


# ── Cameras ───────────────────────────────────────────────────────────────────
_DEFAULT_RTSP_PATH = "/Streaming/Channels/101"


class CameraItem(CameraRef):
    """Full camera detail — extends CameraRef with hardware + operational fields."""
    ip_address: str
    rtsp_port: int
    rtsp_path: str
    username: Optional[str] = None
    has_password: bool
    rtsp_url_masked: str
    enabled: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_check_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    last_status: Optional[str] = None
    is_online: bool


class CameraDetail(CameraItem):
    """Forward-compat enrichment shape for GET /cameras/{id}.
    Currently unwired — the endpoint returns plain `CameraItem`. Wire this
    when the frontend wants `recent_events[]` + `stats` in a single fetch."""
    recent_events: list[CameraEvent] = []
    stats: Optional[dict] = None


class CameraCreate(BaseModel):
    camera_id: str = Field(..., min_length=1, max_length=50)
    name: Optional[str] = None
    floor: Optional[str] = None
    # Phase-1 of WS-8 floor refactor; create requests can use either `floor` or `floor_id`.
    floor_id: Optional[int] = None
    role: CameraRoleLiteral = "other"
    watches_floor: Optional[str] = None
    # Phase-1 of WS-8 floor refactor; create requests can use either `watches_floor` or `watches_floor_id`.
    watches_floor_id: Optional[int] = None
    watches_slots: Optional[list[str]] = None
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
    # Phase-1 of WS-8 floor refactor; update requests can use either `floor` or `floor_id`.
    floor_id: Optional[int] = None
    role: Optional[CameraRoleLiteral] = None
    watches_floor: Optional[str] = None
    # Phase-1 of WS-8 floor refactor; update requests can use either `watches_floor` or `watches_floor_id`.
    watches_floor_id: Optional[int] = None
    watches_slots: Optional[list[str]] = None
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
    username: Optional[str] = None
    password: Optional[str] = None
    rtsp_url: str


class CameraWithCredentials(CameraItem):
    password: Optional[str] = None
    rtsp_url: str


class CameraInternalListResponse(BaseModel):
    total: int
    fetched_at: datetime
    cameras: list[CameraWithCredentials]
    decryption_errors: list[dict]


# ── Camera live-feed (HLS) ────────────────────────────────────────────────────
# Returned by GET /cameras/{id}/feed. The Gateway opens a session against the
# camera-server and surfaces only the playable HLS URL + bookkeeping IDs;
# RTSP credentials and direct camera-server endpoints are never exposed.
class CameraFeed(BaseModel):
    id: int
    camera_id: str
    display_name: Optional[str] = None
    stream: str
    session_id: str
    hls_url: str
    embed_url: str
    expires_at: str


class CameraFeedClosed(BaseModel):
    session_id: str
    closed: bool


class CameraKPIs(BaseModel):
    total: int
    enabled: int
    disabled: int
    online: int
    offline: int
    by_floor: dict[str, int]


class CameraCheckResult(BaseModel):
    camera_id: str
    is_online: bool
    last_status: Optional[str] = None
    last_check_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None


class CameraFeedItem(BaseModel):
    id: Optional[int] = None
    camera_id: Optional[str] = None
    location_label: Optional[str] = None
    event_description: Optional[str] = None
    detection_source: Optional[str] = None
    plate_number: Optional[str] = None
    snapshot_url: Optional[str] = None
    timestamp: Optional[datetime] = None
