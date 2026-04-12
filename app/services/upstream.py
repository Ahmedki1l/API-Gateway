"""
Thin async HTTP clients for the two upstream systems.
Both are used as FastAPI dependencies so they share a single httpx.AsyncClient
per process (connection pooling).
"""

import json
from collections.abc import AsyncIterator

import httpx

from app.config import settings

_system1 = httpx.AsyncClient(base_url=settings.system1_base_url, timeout=10.0)
_system2 = httpx.AsyncClient(base_url=settings.system2_base_url, timeout=10.0)


async def get_system1_health() -> dict:
    try:
        r = await _system1.get("/api/v1/health")
        return r.json()
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


async def get_system2_health() -> dict:
    try:
        r = await _system2.get("/api/health")
        return r.json()
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


async def get_live_vehicles() -> list[dict]:
    try:
        r = await _system2.get("/api/vehicles")
        return r.json() if r.is_success else []
    except Exception:
        return []


async def get_live_slots() -> list[dict]:
    try:
        r = await _system2.get("/api/slots")
        return r.json() if r.is_success else []
    except Exception:
        return []


async def get_system2_stats() -> dict:
    try:
        r = await _system2.get("/api/stats")
        return r.json() if r.is_success else {}
    except Exception:
        return {}


async def _iter_sse_events(client: httpx.AsyncClient, path: str) -> AsyncIterator[dict]:
    try:
        async with client.stream("GET", path, headers={"Accept": "text/event-stream"}) as response:
            if not response.is_success:
                return

            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if not payload:
                    continue
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    data = {"raw_data": payload}

                if isinstance(data, dict):
                    yield data
    except Exception:
        return


async def iter_system1_alert_events() -> AsyncIterator[dict]:
    async for event in _iter_sse_events(_system1, "/api/v1/alerts/stream"):
        yield event


async def iter_system2_alert_events() -> AsyncIterator[dict]:
    async for event in _iter_sse_events(_system2, "/api/alerts/stream"):
        yield event
