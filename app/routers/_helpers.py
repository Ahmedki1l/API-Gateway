"""Shared router helpers — small utilities the routers reuse.

Currently hosts the floor-resolution helpers introduced by WS-8 (the floor +
slot-PK refactor). Endpoints accept either a `floor_id` integer or the legacy
`floor` name string; this module turns "whichever the caller sent" into the
integer key the SQL needs.

**Schema-compatibility shim** (same convention as
`app/routers/alerts.py:_alerts_extra_cols` and
`app/routers/camera_feeds.py:_camera_feeds_introspect`). The gateway must
keep working BOTH before AND after the WS-8 migration ships, because the
upstream PMS-AI Alembic migration `c8d9e0f1a2b3` may not have run on every
deployment yet. `_floor_schema()` probes `INFORMATION_SCHEMA` for the new
table/columns and lets each router branch its SQL — `floor_id` columns
become `NULL AS floor_id`, the `LEFT JOIN floors` becomes empty, and
`?floor_id=` filters silently fall back to the legacy `?floor=` name
filter when the integer column doesn't exist yet.
"""
from functools import lru_cache
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal, scalar


@lru_cache(maxsize=1)
def _floor_schema() -> dict:
    """Probe which WS-8 floor-refactor tables/columns exist in the DB.

    Cached for the lifetime of the process — table/column existence doesn't
    change at runtime. Restart the gateway after running
    `sql/bootstrap.sql`'s WS-8 section (or the PMS-AI Alembic migration) so
    this cache rebuilds.
    """
    db = SessionLocal()
    try:
        def has_table(name: str) -> bool:
            return bool(scalar(
                db,
                "SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = :n",
                {"n": name},
            ))

        def has_col(table: str, col: str) -> bool:
            return bool(scalar(
                db,
                "SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_NAME = :t AND COLUMN_NAME = :c",
                {"t": table, "c": col},
            ))

        return {
            "floors_table":                       has_table("floors"),
            "parking_slots_id":                   has_col("parking_slots", "id"),
            "parking_slots_floor_id":             has_col("parking_slots", "floor_id"),
            "parking_sessions_floor_id":          has_col("parking_sessions", "floor_id"),
            "parking_sessions_parking_slot_id":   has_col("parking_sessions", "parking_slot_id"),
            # `cameras.floor` (string) and `cameras.watches_floor` (string)
            # are NOT universally present — older deployments predate
            # Phase 4A's cameras-table schema. The integer `_id` columns
            # were added by WS-8. All four are probed independently.
            "cameras_floor":                      has_col("cameras", "floor"),
            "cameras_watches_floor":              has_col("cameras", "watches_floor"),
            "cameras_floor_id":                   has_col("cameras", "floor_id"),
            "cameras_watches_floor_id":           has_col("cameras", "watches_floor_id"),
            "cameras_role":                       has_col("cameras", "role"),
            "cameras_watches_slots_json":         has_col("cameras", "watches_slots_json"),
            "cameras_notes":                      has_col("cameras", "notes"),
            "cameras_last_check_at":              has_col("cameras", "last_check_at"),
            "cameras_last_seen_at":               has_col("cameras", "last_seen_at"),
            "cameras_last_status":                has_col("cameras", "last_status"),
            "alerts_floor_id":                    has_col("alerts", "floor_id"),
            "alerts_parking_slot_id":             has_col("alerts", "parking_slot_id"),
            "slot_status_parking_slot_id":        has_col("slot_status", "parking_slot_id"),
            "intrusions_parking_slot_id":         has_col("intrusions", "parking_slot_id"),
            "floor_occupancy_floor_id":           has_col("floor_occupancy", "floor_id"),
        }
    finally:
        db.close()


def floor_id_col(table_alias: str, col_present: bool, *, alias: str = "floor_id") -> str:
    """Emit a SELECT expression for the floor_id column with a NULL fallback
    when the underlying column doesn't exist yet (pre-WS-8 DB)."""
    if col_present:
        return f"{table_alias}.floor_id AS {alias}"
    return f"NULL AS {alias}"


def floors_join_sql(*, key_expr: str, alias: str = "f") -> str:
    """Emit a `LEFT JOIN floors` clause when the floors table exists,
    empty string otherwise. Used to populate `f.id AS floor_id` from a
    name-based lookup at query time."""
    if _floor_schema()["floors_table"]:
        return f"LEFT JOIN floors {alias} ON {alias}.name = {key_expr}"
    return ""


def floors_join_id_select(alias: str = "f") -> str:
    """Companion to `floors_join_sql`: emits `f.id AS floor_id` when the join
    is live, `NULL AS floor_id` when the floors table is missing."""
    if _floor_schema()["floors_table"]:
        return f"{alias}.id AS floor_id"
    return "NULL AS floor_id"


def resolve_floor_id(
    db: Session,
    *,
    floor_id: Optional[int] = None,
    floor_name: Optional[str] = None,
) -> Optional[int]:
    """Return floors.id given whichever side the caller provided.

    Precedence: `floor_id` wins when both are sent. Returns None when neither
    was sent (no filter — caller intends "all floors"). Raises 404 when a
    `floor_name` is sent but no row in `floors` has that name.

    **Pre-WS-8 DB tolerance:** when the `floors` table doesn't exist yet,
    returns the integer `floor_id` as-is when the caller passed one (might
    be 0 rows in the SQL, but won't crash); returns None when the caller
    passed only a name (so the caller falls back to filtering on the legacy
    `floor` string column).
    """
    if floor_id is not None:
        return floor_id
    if floor_name is not None:
        if not _floor_schema()["floors_table"]:
            # Pre-migration: no floors table to look up. Caller falls back to
            # the legacy WHERE clause on the string `floor` column.
            return None
        row = scalar(db, "SELECT id FROM floors WHERE name = :n", {"n": floor_name})
        if row is None:
            raise HTTPException(404, f"Floor '{floor_name}' not found")
        return row
    return None


def resolve_floor_name(db: Session, floor_id: Optional[int]) -> Optional[str]:
    """Reverse lookup — given a floor id, return its name. Returns None if id
    is None (no filter) or if the floors table doesn't exist yet."""
    if floor_id is None:
        return None
    if not _floor_schema()["floors_table"]:
        return None
    row = scalar(db, "SELECT name FROM floors WHERE id = :i", {"i": floor_id})
    if row is None:
        raise HTTPException(404, f"Floor id {floor_id} not found")
    return row
