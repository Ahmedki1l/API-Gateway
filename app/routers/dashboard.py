from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import localize_naive
from app.database import get_db, scalar, rows
from app.routers._helpers import _floor_schema
from app.routers.alerts import _alerts_extra_cols
from app.routers.occupancy import _slot_type_excl
from app.services.snapshots import resolve_snapshot_url
from app.schemas import (
    ActiveVehicle,
    AIStatusResponse,
    DashboardKPIs,
    SystemStatus,
)
from app.services.upstream import (
    get_live_vehicles,
    get_system1_health,
    get_system1_last_connected_at,
    get_system2_health,
    get_system2_last_connected_at,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
 
VEHICLE_JOIN = """
    LEFT JOIN vehicles v_id ON v_id.id = ps.vehicle_id
    LEFT JOIN vehicles v_plate ON ps.vehicle_id IS NULL AND v_plate.plate_number = ps.plate_number
"""
 
 
_HEALTHY_STATUSES = {"ok", "healthy"}


def _derive_health(raw_status: Optional[str]) -> str:
    """Collapse an upstream's raw `/health` `status` string into the small
    vocabulary the dashboard UI styles: `healthy` when the upstream reports
    ok/healthy, `unreachable` when nothing came back at all, otherwise the
    raw value (e.g. `degraded`) is passed through unchanged."""
    if raw_status in _HEALTHY_STATUSES:
        return "healthy"
    if not raw_status:
        return "unreachable"
    return raw_status


@router.get("/ai-status", response_model=AIStatusResponse)
async def ai_status():
    s1, s2 = await get_system1_health(), await get_system2_health()

    systems = [
        SystemStatus(
            name="PMS-AI",
            health=_derive_health(s1.get("status")),
            timestamp=s1.get("timestamp"),
            last_connected_at=get_system1_last_connected_at(),
        ),
        SystemStatus(
            name="VideoAnalytics",
            health=_derive_health(s2.get("status")),
            timestamp=s2.get("timestamp"),
            last_connected_at=get_system2_last_connected_at(),
        ),
    ]

    issues: list[dict] = []
    if s1.get("status") not in _HEALTHY_STATUSES:
        issues.append({"system": "PMS-AI", "reason": s1.get("error") or s1.get("status")})
    for failure in s1.get("failures", []):
        issues.append({"system": "PMS-AI", "reason": failure})
    if s2.get("status") not in _HEALTHY_STATUSES:
        issues.append({"system": "VideoAnalytics", "reason": s2.get("error") or s2.get("status")})

    healthy_count = sum(1 for sys in systems if sys.health == "healthy")
    if healthy_count == len(systems):
        overall = "healthy"
    elif healthy_count == 0:
        overall = "down"
    else:
        overall = "degraded"

    return AIStatusResponse(
        overall_health=overall,
        issues=issues,
        systems=systems,
    )


@router.get("/kpis", response_model=DashboardKPIs)
async def dashboard_kpis(db: Session = Depends(get_db)):
    slot_excl = _slot_type_excl()
    slot_excl_pk = _slot_type_excl("pk")

    total_slots = scalar(db, f"""
        SELECT COUNT(*) FROM parking_slots
        WHERE is_violation_zone = 0 {slot_excl}
    """)

    occupied_slots = scalar(db, f"""
        SELECT COUNT(*) FROM parking_slots pk
        LEFT JOIN slot_status ss
          ON ss.slot_id = pk.slot_id
          AND ss.time = (SELECT MAX(time) FROM slot_status WHERE slot_id = pk.slot_id)
        WHERE pk.is_violation_zone = 0
          {slot_excl_pk}
          AND ss.status IS NOT NULL
          AND UPPER(ss.status) NOT IN ('EMPTY', 'AVAILABLE', 'FREE', 'VACANT')
    """)

    occupied_slots = occupied_slots or 0
    free_slots = (total_slots or 0) - occupied_slots

    cols = _alerts_extra_cols()
    if cols["severity"]:
        critical_sql = "SELECT COUNT(*) FROM alerts WHERE is_resolved=0 AND is_test=0 AND severity='critical'"
    else:
        critical_sql = """
            SELECT COUNT(*) FROM alerts
            WHERE is_resolved=0 AND is_test=0
              AND alert_type IN ('violence','intrusion','vehicle_intrusion',
                                 'vehicle_violation','named_slot_violation','special_needs_violation')
        """
    critical_alerts = scalar(db, critical_sql)

    return DashboardKPIs(
        free_slots=free_slots,
        occupied_slots=occupied_slots,
        critical_alerts=critical_alerts or 0,
    )
 
 
@router.get("/active-vehicles", response_model=list[ActiveVehicle], deprecated=True)
async def active_vehicles(db: Session = Depends(get_db)):
    """Open parking sessions merged with live System 2 slot data.

    **Deprecated (G-20).** Prefer `GET /vehicles/?is_currently_parked=true`
    which returns the same set of currently-parked vehicles wrapped in the
    canonical `PagedResponse[VehicleListItem]` envelope (with filters,
    pagination, and CSV export). This endpoint is retained only so existing
    dashboards keep working while the frontend migrates; it will be removed
    in Phase 4C.
    """
    # WS-8.E: ps.floor_id added so ActiveVehicle.floor_id can populate.
    # Pre-WS-8 DB tolerance: when ps.floor_id doesn't exist yet, emit NULL.
    schema = _floor_schema()
    ps_floor_id_sel = "ps.floor_id" if schema["parking_sessions_floor_id"] else "NULL AS floor_id"
    sql_rows = rows(db, f"""
        SELECT
            ps.id                                       AS vehicle_event_id,
            ps.vehicle_id,
            ps.plate_number,
            ps.entry_time,
            ps.floor,
            {ps_floor_id_sel},
            ps.slot_id,
            COALESCE(pk.slot_name, ps.slot_number)      AS slot_name,
            ps.slot_number,
            ps.is_employee,
            ps.entry_snapshot_path,
            COALESCE(v_id.owner_name, v_plate.owner_name) AS owner_name,
            COALESCE(v_id.vehicle_type, v_plate.vehicle_type, ps.vehicle_type) AS vehicle_type
        FROM parking_sessions ps
    """ + VEHICLE_JOIN + """
        LEFT JOIN parking_slots pk ON pk.slot_id = ps.slot_id
        WHERE ps.status = 'open'
        ORDER BY ps.entry_time DESC
    """)

    sql_map = {r["plate_number"]: r for r in sql_rows}

    # Merge with System 2 live data (may have fresher slot/floor info)
    live = await get_live_vehicles()
    live_map = {v.get("plate_number") or v.get("plate"): v for v in live}

    result = []
    for plate, meta in sql_map.items():
        live_data = live_map.get(plate, {})
        result.append(ActiveVehicle(
            plate_number=plate,
            vehicle_id=meta.get("vehicle_id"),
            entry_time=localize_naive(meta["entry_time"]),
            owner_name=meta["owner_name"],
            vehicle_type=meta["vehicle_type"],
            is_employee=meta["is_employee"],
            floor=live_data.get("floor") or meta["floor"],
            # WS-8.E: integer-id sibling field; live System 2 may not include it
            # yet, so fall back to the session row's floor_id.
            floor_id=live_data.get("floor_id") or meta.get("floor_id"),
            # prefer live data for slot placement, fall back to session slot_id/name
            slot_id=live_data.get("slot_id") or meta.get("slot_id"),
            slot_name=live_data.get("slot_name") or meta.get("slot_name"),
            vehicle_event_id=meta.get("vehicle_event_id"),
            thumbnail_url=resolve_snapshot_url(live_data.get("thumbnail_url") or meta["entry_snapshot_path"]),
        ))

    return result