from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db, rows, scalar
from app.schemas import CameraFeedItem, PagedResponse
from app.services.snapshots import resolve_snapshot_url
from app.shared import build_paged

router = APIRouter(prefix="/camera-feeds", tags=["Camera Feeds"])


@lru_cache(maxsize=1)
def _camera_feeds_introspect() -> dict:
    """Probe INFORMATION_SCHEMA once for `camera_feeds` shape.

    Returns:
      {
        "exists": bool,                # is the table present at all?
        "has_id": bool,                # bootstrap.sql adds a surrogate `id` PK
        "has_camera_id": bool,         # bootstrap.sql column; older dumps may lack it
      }

    Older databases (created before bootstrap.sql) may not have this table or
    may have a stripped-down version. Rather than 500ing on every request the
    Gateway:
      - returns an empty paged response when the table is missing
      - emits NULL placeholders for columns that don't exist

    Cached for the lifetime of the process — restart after running
    sql/bootstrap.sql.
    """
    db = SessionLocal()
    try:
        n = scalar(db, """
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'camera_feeds'
        """)
        if not (n or 0):
            return {"exists": False, "has_id": False, "has_camera_id": False}

        def col_exists(name: str) -> bool:
            return (scalar(db, """
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'camera_feeds' AND COLUMN_NAME = :c
            """, {"c": name}) or 0) > 0

        return {
            "exists": True,
            "has_id": col_exists("id"),
            "has_camera_id": col_exists("camera_id"),
        }
    except Exception:
        return {"exists": False, "has_id": False, "has_camera_id": False}
    finally:
        db.close()


@router.get("/", response_model=PagedResponse[CameraFeedItem])
async def get_camera_feeds(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    location_label: Optional[str] = Query(None, description="Filter by location_label"),
    detection_source: Optional[str] = Query(None, description="Filter by detection_source"),
    plate_number: Optional[str] = Query(None, description="Filter by plate_number"),
    db: Session = Depends(get_db),
):
    info = _camera_feeds_introspect()
    if not info["exists"]:
        # Table not bootstrapped yet — return an empty page instead of 500ing.
        return build_paged([], 0, page, page_size)

    clauses = ["1=1"]
    params: dict = {}

    if location_label:
        clauses.append("location_label LIKE :location_label")
        params["location_label"] = f"%{location_label}%"
    if detection_source:
        clauses.append("detection_source = :detection_source")
        params["detection_source"] = detection_source
    if plate_number:
        clauses.append("plate_number LIKE :plate_number")
        params["plate_number"] = f"%{plate_number}%"

    where = " AND ".join(clauses)
    total = scalar(db, f"SELECT COUNT(*) FROM camera_feeds WHERE {where}", params)

    params["offset"] = (page - 1) * page_size
    params["page_size"] = page_size

    id_col        = "id"        if info["has_id"]        else "NULL AS id"
    camera_id_col = "camera_id" if info["has_camera_id"] else "NULL AS camera_id"

    items = rows(db, f"""
        SELECT
            {id_col},
            {camera_id_col},
            location_label,
            event_description,
            detection_source,
            plate_number,
            snapshot_path AS snapshot_url,
            timestamp
        FROM camera_feeds
        WHERE {where}
        ORDER BY timestamp DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)

    for it in items:
        it["snapshot_url"] = resolve_snapshot_url(it.get("snapshot_url"))

    return build_paged(items, total or 0, page, page_size)
