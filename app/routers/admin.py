"""Admin endpoints — destructive operations gated by X-Internal-Token.

Right now this is just `POST /admin/reset` which wipes all transactional state
and leaves the structural definitions (floors, parking_slots, cameras, engine
config) intact. Replaces the ad-hoc `DELETE FROM ...` ritual between test
runs and demo resets.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

import logging

from app.database import get_db
from app.services.auth import require_internal_token

router = APIRouter(prefix="/admin", tags=["⚠️  Admin"])
logger = logging.getLogger(__name__)


# Order matters — wipe child rows before parents so FKs don't fire. Mirrors
# scripts/simulate/cleanup_test_data.py's proven sequence, extended to cover
# `intrusions` (transactional) and the state-resetting UPDATE pass below.
_DELETE_TABLES = (
    "alerts",
    "camera_feeds",
    "intrusions",
    "slot_status",
    "entry_exit_log",
    "parking_sessions",
    "vehicles",
)


# State-resetting UPDATEs run after the DELETEs. Each tuple is
# (label, sql) where label is what we report in the response.
_RESET_UPDATES = (
    (
        "zone_occupancy",
        # Zero the live counter; keep zone definitions + capacity. Stamp
        # last_updated so dashboards know the reset moment.
        "UPDATE dbo.zone_occupancy "
        "SET current_count = 0, last_updated = SYSUTCDATETIME()",
    ),
    (
        "parking_slots",
        # Free every slot and clear rolling slot snapshots — VA repopulates
        # both as soon as it sees the slots again.
        "UPDATE dbo.parking_slots "
        "SET is_available = 1, last_snapshot_path = NULL",
    ),
    (
        "cameras",
        # Clear liveness probe state. camera_monitor.py's next probe cycle
        # (default 60s) will repopulate; until then the dashboard shows
        # cameras as unknown rather than stale-online.
        "UPDATE dbo.cameras "
        "SET last_check_at = NULL, last_seen_at = NULL, last_status = NULL",
    ),
)


# Tables we never touch — surface their row counts so the caller can confirm
# the structural data is intact.
_PRESERVED_TABLES = (
    "floors",
    "parking_slots",
    "cameras",
    "config",
    "preprocessing_config",
    "zone_occupancy",
    "alembic_version",
)


_CONFIRM_TOKEN = "YES_WIPE_EVERYTHING"


@router.post(
    "/reset",
    summary="Wipe all transactional data; preserve floors/slots/cameras/config",
    dependencies=[Depends(require_internal_token)],
)
async def reset_database(
    confirm: Optional[str] = Query(
        None,
        description=(
            "Must be exactly 'YES_WIPE_EVERYTHING' to proceed. "
            "This is intentionally explicit to prevent accidental hits."
        ),
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Destructively reset the `damanat_pms` database to a clean operational
    state, preserving only structural rows (floors, slots, cameras, engine
    config). All transactional rows (alerts, sessions, entry/exit log, camera
    feeds, slot_status, vehicles, intrusions) are deleted, and stateful
    counters / flags on the preserved tables are reset.

    Requires the X-Internal-Token header AND a `?confirm=YES_WIPE_EVERYTHING`
    query parameter. Both must match — protects against accidental destructive
    hits even with a valid token.

    Returns a `ResetResponse`-shaped dict with row counts per table and a
    list of warnings (e.g. that PMS-AI / VA in-memory caches must be flushed
    by restarting those services to fully reset the system).
    """
    if confirm != _CONFIRM_TOKEN:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Reset refused. Pass ?confirm={_CONFIRM_TOKEN} to proceed. "
                "This endpoint deletes all transactional data."
            ),
        )

    deleted: dict[str, int] = {}
    reset: dict[str, int] = {}
    preserved: dict[str, int] = {}

    try:
        # Phase 1: DELETE the transactional tables in FK-safe order.
        for table in _DELETE_TABLES:
            result = db.execute(text(f"DELETE FROM dbo.{table}"))
            deleted[table] = result.rowcount or 0

        # Phase 2: UPDATE state-resetting passes on preserved tables.
        for label, sql in _RESET_UPDATES:
            result = db.execute(text(sql))
            reset[label] = result.rowcount or 0

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Reset failed; rolled back")
        raise HTTPException(status_code=500, detail=f"Reset failed: {exc!r}")

    # Phase 3: read row counts on preserved tables so the caller can confirm
    # the structural data is intact. These run outside the transaction since
    # they're observational.
    for table in _PRESERVED_TABLES:
        try:
            preserved[table] = db.execute(
                text(f"SELECT COUNT(*) FROM dbo.{table}")
            ).scalar() or 0
        except Exception:
            preserved[table] = -1  # table doesn't exist on this schema

    total_deleted = sum(deleted.values())
    logger.info(
        "Admin reset committed: deleted=%d rows across %d tables; "
        "reset state on %d tables",
        total_deleted, len(deleted), len(reset),
    )

    return {
        "deleted": deleted,
        "reset": reset,
        "preserved": preserved,
        "wiped_at": datetime.utcnow().isoformat() + "Z",
        "warnings": [
            "PMS-AI in-memory state (SQLAlchemy identity map, open sessions) "
            "is not affected — restart PMS-AI to fully reset.",
            "VideoAnalytics in-memory state (vehicle_registry._parked, "
            "_track_session_map, _recent_violators) is not affected — "
            "restart VA to fully reset.",
            "cameras.last_check_at / last_seen_at will repopulate within "
            "CAMERA_MONITOR_INTERVAL_SECONDS (default 60s) once the "
            "Gateway's camera_monitor runs its next probe cycle.",
        ],
    }
