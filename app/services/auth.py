"""Shared FastAPI auth dependencies.

Currently just `require_internal_token` — gates endpoints that should only be
reachable by trusted upstream services (e.g. VideoAnalytics calling
`/cameras/internal/all` to fetch decrypted RTSP credentials, or admin tools
calling the `/alerts/test/*` simulators).

The token lives in `settings.cameras_internal_token` (loaded from
CAMERAS_INTERNAL_TOKEN env var). If that's empty, the dependency returns 503
so the misconfiguration is loud rather than silent.
"""
from typing import Optional

from fastapi import Header, HTTPException

from app.config import settings


def require_internal_token(
    x_internal_token: Optional[str] = Header(default=None, alias="X-Internal-Token"),
) -> None:
    """FastAPI dependency. Raises 503 if the gateway has no token configured;
    raises 401 if the request didn't supply the matching token."""
    if not settings.cameras_internal_token:
        raise HTTPException(status_code=503, detail="Internal token not configured")
    if x_internal_token != settings.cameras_internal_token:
        raise HTTPException(status_code=401, detail="Missing or invalid X-Internal-Token")
