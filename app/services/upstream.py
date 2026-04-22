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
SSE_TIMEOUT = httpx.Timeout(10.0, read=None)


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


async def _iter_sse_events(
    client: httpx.AsyncClient,
    path: str,
    emit_connected_event: bool = False,
) -> AsyncIterator[dict]:
    response: httpx.Response | None = None
    stream_context = None
    stream_entered = False
    try:
        stream_context = client.stream(
            "GET",
            path,
            headers={"Accept": "text/event-stream"},
            timeout=SSE_TIMEOUT,
        )
        response = await stream_context.__aenter__()
        stream_entered = True
        if not response.is_success:
            return

        if emit_connected_event:
            yield {
                "alert_id": None,
                "alert_type": "connection_established",
                "severity": "info",
                "is_alert": False,
            }

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
    except Exception as e:
        print(f"[upstream] SSE stream ended for {path}: {e}")
        return
    finally:
        if response is not None:
            await response.aclose()
            print(f"[upstream] SSE response closed for {path}")
        if stream_entered:
            await stream_context.__aexit__(None, None, None)


async def iter_system1_alert_events() -> AsyncIterator[dict]:
    iterator = _iter_sse_events(
        _system1,
        "/api/v1/alerts/stream",
        emit_connected_event=True,
    )
    try:
        async for event in iterator:
            yield event
    finally:
        await iterator.aclose()


async def iter_system2_alert_events() -> AsyncIterator[dict]:
    iterator = _iter_sse_events(_system2, "/api/alerts/stream")
    try:
        async for event in iterator:
            yield event
    finally:
        await iterator.aclose()
