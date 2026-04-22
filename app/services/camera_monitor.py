"""
Background TCP-reachability monitor for cameras.

Periodically opens a TCP connection to (ip_address, rtsp_port) for each enabled
camera and writes the result back to last_check_at / last_seen_at / last_status.

The check is intentionally TCP-only — that's the smallest signal that doesn't
need credentials and doesn't need an RTSP client. RTSP-level health (auth ok,
stream flowing) is out of scope.
"""
from __future__ import annotations

import asyncio
import socket
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal


def _classify_exception(exc: BaseException) -> str:
    if isinstance(exc, asyncio.TimeoutError):
        return "timeout"
    if isinstance(exc, ConnectionRefusedError):
        return "connection_refused"
    if isinstance(exc, socket.gaierror):
        return "dns_error"
    return "unreachable"


async def _probe_one(ip: str, port: int, timeout: float) -> tuple[bool, str]:
    """Open a TCP connection, immediately close. Returns (online, status)."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host=ip, port=port),
            timeout=timeout,
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True, "online"
    except BaseException as exc:  # noqa: BLE001 — we intentionally classify everything
        return False, _classify_exception(exc)


def _persist_result(camera_id: str, status: str, online: bool) -> None:
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        if online:
            db.execute(
                text(
                    "UPDATE cameras "
                    "SET last_check_at = :now, last_seen_at = :now, last_status = :status "
                    "WHERE camera_id = :camera_id"
                ),
                {"now": now, "status": status, "camera_id": camera_id},
            )
        else:
            db.execute(
                text(
                    "UPDATE cameras "
                    "SET last_check_at = :now, last_status = :status "
                    "WHERE camera_id = :camera_id"
                ),
                {"now": now, "status": status, "camera_id": camera_id},
            )
        db.commit()
    finally:
        db.close()


def _mark_disabled_cameras() -> None:
    """One-shot pass — set last_status='disabled' on rows whose status doesn't reflect that yet."""
    db = SessionLocal()
    try:
        db.execute(
            text(
                "UPDATE cameras SET last_status = 'disabled' "
                "WHERE enabled = 0 AND (last_status IS NULL OR last_status <> 'disabled')"
            )
        )
        db.commit()
    finally:
        db.close()


def _load_enabled_cameras() -> list[dict]:
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT camera_id, ip_address, rtsp_port FROM cameras WHERE enabled = 1")
        )
        cols = result.keys()
        return [dict(zip(cols, row)) for row in result.fetchall()]
    finally:
        db.close()


async def check_one(camera_id: str) -> Optional[dict]:
    """One-off poll for the /check-now endpoint.

    Returns {is_online, last_status, last_check_at, last_seen_at} or None if the camera
    isn't found or is disabled.
    """
    db = SessionLocal()
    try:
        result = db.execute(
            text(
                "SELECT camera_id, ip_address, rtsp_port, enabled, last_seen_at "
                "FROM cameras WHERE camera_id = :camera_id"
            ),
            {"camera_id": camera_id},
        )
        cols = result.keys()
        row = result.fetchone()
        if not row:
            return None
        camera = dict(zip(cols, row))
    finally:
        db.close()

    if not camera["enabled"]:
        _mark_disabled_cameras()
        return {
            "camera_id": camera_id,
            "is_online": False,
            "last_status": "disabled",
            "last_check_at": None,
            "last_seen_at": camera["last_seen_at"],
        }

    online, status = await _probe_one(
        ip=camera["ip_address"],
        port=int(camera["rtsp_port"]),
        timeout=settings.camera_monitor_tcp_timeout_seconds,
    )
    _persist_result(camera_id, status, online)

    db = SessionLocal()
    try:
        result = db.execute(
            text(
                "SELECT last_check_at, last_seen_at, last_status FROM cameras "
                "WHERE camera_id = :camera_id"
            ),
            {"camera_id": camera_id},
        )
        cols = result.keys()
        row = dict(zip(cols, result.fetchone()))
    finally:
        db.close()

    return {
        "camera_id": camera_id,
        "is_online": online,
        "last_status": row["last_status"],
        "last_check_at": row["last_check_at"],
        "last_seen_at": row["last_seen_at"],
    }


async def _tick(semaphore: asyncio.Semaphore) -> None:
    """One full polling pass over all enabled cameras."""
    cameras = _load_enabled_cameras()
    if not cameras:
        _mark_disabled_cameras()
        return

    async def _one(cam: dict) -> None:
        async with semaphore:
            online, status = await _probe_one(
                ip=cam["ip_address"],
                port=int(cam["rtsp_port"]),
                timeout=settings.camera_monitor_tcp_timeout_seconds,
            )
            _persist_result(cam["camera_id"], status, online)

    await asyncio.gather(*[_one(c) for c in cameras], return_exceptions=True)
    _mark_disabled_cameras()


async def _monitor_loop() -> None:
    semaphore = asyncio.Semaphore(settings.camera_monitor_concurrency)
    interval = settings.camera_monitor_interval_seconds
    print(f"[camera_monitor] started (interval={interval}s, concurrency={semaphore._value})")
    try:
        while True:
            try:
                await _tick(semaphore)
            except Exception as exc:  # noqa: BLE001
                print(f"[camera_monitor] tick error: {exc!r}")
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        print("[camera_monitor] cancelled — shutting down")
        raise


_monitor_task: Optional[asyncio.Task] = None


def start() -> None:
    """Spawn the monitor task. Idempotent — call from FastAPI lifespan startup."""
    global _monitor_task
    if not settings.camera_monitor_enabled:
        print("[camera_monitor] disabled via CAMERA_MONITOR_ENABLED=false")
        return
    if _monitor_task and not _monitor_task.done():
        return
    _monitor_task = asyncio.create_task(_monitor_loop(), name="camera_monitor")


async def stop() -> None:
    """Cancel and await the monitor task. Call from FastAPI lifespan shutdown."""
    global _monitor_task
    if _monitor_task is None:
        return
    _monitor_task.cancel()
    try:
        await _monitor_task
    except (asyncio.CancelledError, Exception):
        pass
    _monitor_task = None


def derive_is_online(last_seen_at: Optional[datetime]) -> bool:
    """The /cameras/ list derives this from last_seen_at + interval, not a stored column."""
    if last_seen_at is None:
        return False
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
    threshold = settings.camera_monitor_interval_seconds * 2
    age_seconds = (datetime.now(timezone.utc) - last_seen_at).total_seconds()
    return age_seconds < threshold
