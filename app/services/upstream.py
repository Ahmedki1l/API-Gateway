"""
Thin async HTTP clients for the two upstream systems.
Both are used as FastAPI dependencies so they share a single httpx.AsyncClient
per process (connection pooling).

The SSE iterators (`iter_system{1,2}_alert_events`) are wrapped in a
per-path circuit breaker (`_SSEBackoff`) so an unreachable upstream doesn't
trigger a tight reconnect loop — each failure increments a counter, and
after 5 failures within 30s the iterator yields nothing and waits 60s
before allowing another attempt. A successful connection resets the counter.
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import settings

_system1 = httpx.AsyncClient(base_url=settings.system1_base_url, timeout=10.0)
_system2 = httpx.AsyncClient(base_url=settings.system2_base_url, timeout=10.0)
SSE_TIMEOUT = httpx.Timeout(10.0, read=None)


# ── SSE upstream circuit breaker (G-22) ─────────────────────────────────────
# Per-(client, path) failure tracking. When an upstream becomes unreachable
# the alerts router was reconnecting on every SSE consumer reconnect (~20
# attempts/min in dev when PMS-AI/VA are offline). The breaker collapses
# that to one attempt every 60s after a short ramp-up.
SSE_FAILURE_THRESHOLD = 5            # failures before tripping
SSE_FAILURE_WINDOW_SEC = 30.0        # window over which failures count
SSE_BACKOFF_SEC = 60.0               # wait this long after tripping


class _SSEBackoff:
    __slots__ = ("failures", "first_failure_ts", "trip_ts")

    def __init__(self) -> None:
        self.failures: int = 0
        self.first_failure_ts: float = 0.0
        self.trip_ts: float = 0.0  # when the breaker tripped (0 = closed)

    def should_attempt(self) -> bool:
        """False if we're inside the backoff window."""
        if self.trip_ts == 0.0:
            return True
        return (time.monotonic() - self.trip_ts) >= SSE_BACKOFF_SEC

    def record_failure(self) -> None:
        now = time.monotonic()
        if self.failures == 0 or (now - self.first_failure_ts) > SSE_FAILURE_WINDOW_SEC:
            # Start (or restart) the failure window.
            self.failures = 1
            self.first_failure_ts = now
            self.trip_ts = 0.0
            return
        self.failures += 1
        if self.failures >= SSE_FAILURE_THRESHOLD:
            self.trip_ts = now

    def record_success(self) -> None:
        self.failures = 0
        self.first_failure_ts = 0.0
        self.trip_ts = 0.0


# Module-level breakers — one per upstream SSE endpoint.
_sse_breaker_system1 = _SSEBackoff()
_sse_breaker_system2 = _SSEBackoff()

# Last successful (2xx) connection timestamp per upstream — survives only for
# the lifetime of the Gateway process. The dashboard uses these to surface a
# "system was last seen at …" indicator even after the upstream goes down.
_system1_last_connected_at: Optional[datetime] = None
_system2_last_connected_at: Optional[datetime] = None


def get_system1_last_connected_at() -> Optional[datetime]:
    return _system1_last_connected_at


def get_system2_last_connected_at() -> Optional[datetime]:
    return _system2_last_connected_at


async def get_system1_health() -> dict:
    global _system1_last_connected_at
    try:
        r = await _system1.get("/api/v1/health")
        if r.is_success:
            _system1_last_connected_at = datetime.now(timezone.utc)
        return r.json()
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


async def get_system2_health() -> dict:
    global _system2_last_connected_at
    try:
        r = await _system2.get("/api/health")
        if r.is_success:
            _system2_last_connected_at = datetime.now(timezone.utc)
        return r.json()
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


async def get_live_vehicles() -> list[dict]:
    global _system2_last_connected_at
    try:
        r = await _system2.get("/api/vehicles")
        if r.is_success:
            _system2_last_connected_at = datetime.now(timezone.utc)
            return r.json()
        return []
    except Exception:
        return []


async def get_live_slots() -> list[dict]:
    global _system2_last_connected_at
    try:
        r = await _system2.get("/api/slots")
        if r.is_success:
            _system2_last_connected_at = datetime.now(timezone.utc)
            return r.json()
        return []
    except Exception:
        return []


async def get_system2_stats() -> dict:
    global _system2_last_connected_at
    try:
        r = await _system2.get("/api/stats")
        if r.is_success:
            _system2_last_connected_at = datetime.now(timezone.utc)
            return r.json()
        return {}
    except Exception:
        return {}


async def _iter_sse_events(
    client: httpx.AsyncClient,
    path: str,
    breaker: _SSEBackoff,
    emit_connected_event: bool = False,
) -> AsyncIterator[dict]:
    """Subscribe to the upstream's SSE feed and yield each event dict.

    On any error (TCP refused, DNS failure, non-2xx response, json parse
    error during the stream), record a failure on the circuit breaker and
    return. The caller's reconnect logic will check `breaker.should_attempt()`
    next time and short-circuit if we're inside the backoff window."""
    if not breaker.should_attempt():
        # Trip is still open — don't even try. Sleep a bit so a re-subscribing
        # client doesn't loop on this iterator's immediate return.
        await asyncio.sleep(min(SSE_BACKOFF_SEC, 5.0))
        return

    response: httpx.Response | None = None
    stream_context = None
    stream_entered = False
    connected = False
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
            breaker.record_failure()
            return
        # Successful HTTP handshake — reset the failure counter so a single
        # post-connect read error doesn't trip the breaker.
        breaker.record_success()
        connected = True

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
        if not connected:
            breaker.record_failure()
            print(f"[upstream] SSE connect failed for {path}: {e} "
                  f"(breaker: {breaker.failures} failures, "
                  f"tripped={breaker.trip_ts > 0})")
        else:
            print(f"[upstream] SSE stream ended for {path}: {e}")
        return
    finally:
        if response is not None:
            await response.aclose()
        if stream_entered:
            await stream_context.__aexit__(None, None, None)


async def iter_system1_alert_events() -> AsyncIterator[dict]:
    iterator = _iter_sse_events(
        _system1,
        "/api/v1/alerts/stream",
        _sse_breaker_system1,
        emit_connected_event=True,
    )
    try:
        async for event in iterator:
            yield event
    finally:
        await iterator.aclose()


async def iter_system2_alert_events() -> AsyncIterator[dict]:
    iterator = _iter_sse_events(_system2, "/api/alerts/stream", _sse_breaker_system2)
    try:
        async for event in iterator:
            yield event
    finally:
        await iterator.aclose()
