from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db, scalar, rows
from app.shared import build_paged

router = APIRouter(prefix="/camera-feeds", tags=["Camera Feeds"])

@router.get("/")
async def get_camera_feeds(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    location_label: Optional[str] = Query(None, description="Filter by location_label"),
    detection_source: Optional[str] = Query(None, description="Filter by detection_source"),
    plate_number: Optional[str] = Query(None, description="Filter by plate_number"),
    db: Session = Depends(get_db),
):
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

    items = rows(db, f"""
        SELECT 
            location_label,
            event_description,
            detection_source,
            plate_number,
            snapshot_path,
            timestamp
        FROM camera_feeds
        WHERE {where}
        ORDER BY timestamp DESC
        OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY
    """, params)

    return build_paged(items, total or 0, page, page_size)
