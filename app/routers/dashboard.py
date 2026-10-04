import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import facility_now_naive, facility_today_utc, localize_naive
from app.database import get_db, scalar, rows
from app.routers._helpers import _floor_schema
from app.routers.alerts import _alerts_extra_cols
from app.routers.entry_exit import _kpi_counts
from app.routers.occupancy import _monitored_slot_availability, currently_parked_count
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


from app.routers.prefix_injection import (get_prefix)
prefix = get_prefix() + "/dashboard"

router = APIRouter(prefix=prefix, tags=["Dashboard"])
 
VEHICLE_JOIN = """
    LEFT JOIN vehicles v_id ON v_id.id = ps.vehicle_id
    LEFT JOIN vehicles v_plate ON ps.vehicle_id IS NULL AND v_plate.plate_number = ps.plate_number
"""
 
 
_HEALTHY_STATUSES = {"ok", "healthy"}


def _issue_reasons(payload: dict) -> list[str]:
    """Why an upstream isn't healthy, in the upstream's own words.

    Both upstreams already explain themselves in the `/health` body and the
    dashboard was throwing that away: VideoAnalytics returns `health_reasons`
    (the engine's computed verdict — frozen streams named by camera id, a
    lagging processing loop with its age, an unreachable DB, entry_v2
    conditions when linked), yet `issues` carried only the bare word from
    `status`. "degraded" names no cause, so the banner sent whoever read it
    to the pod logs to learn what the payload had already said.

    `failures` is accepted alongside it for any upstream that words the same
    list differently. `error` (set by `_health_payload` for a non-2xx, or by
    the client for a transport failure) is the fallback when the upstream
    could not describe itself at all.
    """
    detail: list[str] = []
    for key in ("health_reasons", "failures"):
        value = payload.get(key) or []
        if isinstance(value, str):
            value = [value]
        detail.extend(str(v) for v in value if v)
    if detail:
        return detail
    return [payload.get("error") or payload.get("status") or "unreachable"]


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
    s1, s2 = await asyncio.gather(get_system1_health(), get_system2_health())

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
    for name, payload in (("PMS-AI", s1), ("VideoAnalytics", s2)):
        if payload.get("status") in _HEALTHY_STATUSES:
            continue
        issues.extend({"system": name, "reason": reason} for reason in _issue_reasons(payload))

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
    """Dashboard headline counters.

    `occupied_slots` / `on_slot` count monitored slots whose
    `parking_slots.is_available` is 0 — the flag the slot grid renders.
    `parked_vehicles` is open `parking_sessions` (line-crossing at the basement
    ramp) plus occupied Ground slots — Ground cars never cross the ramp line, so
    they only exist as VA slot occupancy. `off_slot` is open sessions minus the
    occupied B1 + B2 slots: basement cars VA can't place in a monitored slot
    (blind spot, unmarked area, or still driving).
    """
    # Coverage-aware, same as /occupancy/kpis and /occupancy/floors: a slot VA
    # can't see can't be offered as free, so free is monitored − occupied.
    total_slots, _monitored_slots, occupied_slots, free_slots = _monitored_slot_availability(db)
    occupancy_pct = round(occupied_slots / (total_slots or 1) * 100, 1)
    # Active floors only — the same set /occupancy/floors renders as bars, so
    # "Across N parkings" always matches the number of rows under it.
    floors_count = scalar(db, "SELECT COUNT(*) FROM floors WHERE is_active = 1")

    basement_occupied = (
        _monitored_slot_availability(db, floor="B1")[2]
        + _monitored_slot_availability(db, floor="B2")[2]
    )
    open_sessions = scalar(
        db, "SELECT COUNT(DISTINCT plate_number) FROM parking_sessions WHERE status = 'open'"
    ) or 0
    parked_vehicles = currently_parked_count(db)
    off_slot = max(open_sessions - basement_occupied, 0)

    # Entries / Exits / Overstays come from the very function behind
    # /entry-exit/kpis (default range = today), so the dashboard cards and the
    # Entry/Exit page can never show different numbers under the same label.
    # Entries: entered since local midnight. Exits: closed since local midnight
    # (exit axis). Overstays: inside at local midnight, including cars that
    # have left since.
    local_today = facility_now_naive().date()
    counts = _kpi_counts(db, local_today, local_today)
    entries_today = counts.total_enter
    exits_today = counts.total_exit
    overstays_today = counts.overstays
    cols = _alerts_extra_cols()
    # Dashboard critical-alerts card counts TODAY's unresolved criticals only
    # (facility-local midnight onward), matching how the Entry/Exit KPIs scope
    # "today" via facility_today_utc(). triggered_at follows the same UTC-naive
    # column convention the other today-windowed queries compare against.
    today_start = facility_today_utc()
    if cols["severity"]:
        critical_sql = """
            SELECT COUNT(*) FROM alerts
            WHERE is_resolved=0 AND is_test=0 AND severity='critical'
              AND triggered_at >= :today
        """
    else:
        critical_sql = """
            SELECT COUNT(*) FROM alerts
            WHERE is_resolved=0 AND is_test=0
              AND alert_type IN ('violence','intrusion','vehicle_intrusion',
                                 'vehicle_violation','named_slot_violation','special_needs_violation')
              AND triggered_at >= :today
        """
    critical_alerts = scalar(db, critical_sql, {"today": today_start})

    return DashboardKPIs(
        total_slots=total_slots or 0,
        floors_count=floors_count or 0,
        free_slots=free_slots,
        occupied_slots=occupied_slots,
        occupancy_pct=occupancy_pct,
        parked_vehicles=parked_vehicles,
        on_slot=occupied_slots,
        off_slot=off_slot,
        critical_alerts=critical_alerts or 0,
        entries_today=entries_today,
        exits_today=exits_today,
        overstays_today=overstays_today,
    )
 
 