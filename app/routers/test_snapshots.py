"""Serves the snapshot URLs that /alerts/test/start puts on its fake alerts.

They copy the deployed upstreams' paths (see services/bus.py:test_snapshot_url)
and every file name is unique, so any name under these paths answers with a
sample image from static/test_alerts, the same one each time for one name.
In deployment the reverse proxy sends these paths to PMS-AI / VideoAnalytics,
so these routes only answer when the gateway is called directly.
"""
import zlib

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.bus import TEST_ALERT_IMAGES_DIR, list_test_alert_images

router = APIRouter(include_in_schema=False)


@router.get("/pms-ai/snapshots/{path:path}")
@router.get("/pms-video-analytics/snapshots/{path:path}")
async def test_alert_snapshot(path: str):
    images = list_test_alert_images()
    if not images:
        raise HTTPException(status_code=404, detail="No test alert images")
    return FileResponse(TEST_ALERT_IMAGES_DIR / images[zlib.crc32(path.encode()) % len(images)])
