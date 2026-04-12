"""
Thin async HTTP clients for the two upstream systems.
Both are used as FastAPI dependencies so they share a single httpx.AsyncClient
per process (connection pooling).
"""
import httpx
from app.config import settings

# ── shared clients (created once at import time) ──────────────────────────────
_system1 = httpx.AsyncClient(base_url=settings.system1_base_url, timeout=10.0)
_system2 = httpx.AsyncClient(base_url=settings.system2_base_url, timeout=10.0)


# ── System 1 — Damanat-PMS-AI ─────────────────────────────────────────────────
async def get_system1_health() -> dict:
    try:
        r = await _system1.get("/api/v1/health")
        return r.json()
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


# ── System 2 — Damanat-PMS-VideoAnalytics ────────────────────────────────────
async def get_system2_health() -> dict:
    try:
        r = await _system2.get("/api/health")
        return r.json()
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


async def get_live_vehicles() -> list[dict]:
    """Returns the live parked-vehicles list from System 2."""
    try:
        r = await _system2.get("/api/vehicles")
        return r.json() if r.is_success else []
    except Exception:
        return []


async def get_live_slots() -> list[dict]:
    """Returns current slot states from System 2."""
    try:
        r = await _system2.get("/api/slots")
        return r.json() if r.is_success else []
    except Exception:
        return []


async def get_system2_stats() -> dict:
    """Returns utilisation stats from System 2."""
    try:
        r = await _system2.get("/api/stats")
        return r.json() if r.is_success else {}
    except Exception:
        return {}
