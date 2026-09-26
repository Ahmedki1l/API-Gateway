"""Scheduler for the end-of-day slot occupancy table (services/daily_occupancy.py).

Lifecycle, started from the FastAPI lifespan next to camera_monitor:

  startup   after a short delay, fill in every missing completed day (when
            backfill is on) — this is also what catches up a midnight the
            Gateway was down for
  nightly   at the configured run time, facility-local, the same missing-days
            pass, which by then includes yesterday

The schedule (enabled / run time / backfill) is DAILY_OCCUPANCY_* in .env,
read once at startup — changing it needs a Gateway restart. Between runs the
task just sleeps: it does no work and no DB reads until the next run time.

Several Gateway pods may run this. Each run takes a SQL Server application lock
first (`sp_getapplock`, no wait); a pod that does not get it skips the run, and
since a day is always written whole, a repeat would be harmless anyway. The lock
is owned by a transaction on a dedicated connection, so SQL Server releases it
when that transaction ends — including when the pod dies mid-run — and a crashed
pod can never leave the job locked.

DB work runs in a worker thread (pyodbc is synchronous), and every error is
caught and logged: a failure here must never take the Gateway down. The next
run retries.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional, TypeVar

from sqlalchemy import text

from app.config import facility_now_naive, settings
from app.database import SessionLocal, engine
from app.services import daily_occupancy

T = TypeVar("T")

LOCK_RESOURCE = "damanat_slot_daily_occupancy"
STARTUP_DELAY_SECONDS = 30   # let the Gateway finish booting before the backfill
_DEFAULT_RUN_AT = (0, 10)


@dataclass
class JobStatus:
    """Schedule in force and last-run bookkeeping, surfaced by the status endpoint."""
    enabled: Optional[bool] = None
    run_at: Optional[str] = None           # "HH:MM" facility-local
    backfill: Optional[bool] = None
    running: bool = False
    last_run_started_at: Optional[datetime] = None
    last_run_finished_at: Optional[datetime] = None
    last_trigger: Optional[str] = None
    last_days_written: int = 0
    last_days_skipped_no_data: int = 0
    last_skipped_days: list = field(default_factory=list)
    last_lock_busy: bool = False
    last_error: Optional[str] = None
    next_run_at: Optional[datetime] = None


status = JobStatus()
_task: Optional[asyncio.Task] = None


class LockBusy(Exception):
    """Another process holds the job lock."""


def run_locked(fn: Callable[..., T]) -> T:
    """Run `fn(db)` while holding the job lock. Raises LockBusy if another
    process holds it. Blocking — call from a worker thread."""
    with engine.connect() as lock_conn:
        with lock_conn.begin():
            got = lock_conn.execute(text("""
                SET NOCOUNT ON;
                DECLARE @r INT;
                EXEC @r = sp_getapplock @Resource = :r, @LockMode = 'Exclusive',
                                        @LockOwner = 'Transaction', @LockTimeout = 0;
                SELECT @r;
            """), {"r": LOCK_RESOURCE}).scalar()
            if got is None or got < 0:
                raise LockBusy(LOCK_RESOURCE)
            db = SessionLocal()
            try:
                return fn(db)
            finally:
                db.close()
        # Leaving the transaction releases the lock.


def _run_at() -> tuple[int, int]:
    # A bad .env time must not stop the Gateway: warn and use the default.
    h, m = settings.daily_occupancy_run_hour, settings.daily_occupancy_run_minute
    if 0 <= h <= 23 and 0 <= m <= 59:
        return h, m
    print(f"[daily_occupancy] invalid run time {h}:{m} - using 00:10")
    return _DEFAULT_RUN_AT


def next_run_after(now: datetime, hour: int, minute: int) -> datetime:
    """The next HH:MM strictly after `now` (both facility-local naive)."""
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


def _work(db, backfill: bool) -> list:
    if backfill:
        return daily_occupancy.backfill(db)
    # Backfill off: only yesterday, and only if it is not stored yet.
    day = daily_occupancy.yesterday()
    if day in daily_occupancy.missing_days(db, through=day):
        return [daily_occupancy.compute_day(db, day)]
    return []


def run_once(trigger: str, backfill: Optional[bool] = None) -> None:
    """One scheduled pass. Blocking; never raises. `backfill` defaults to
    DAILY_OCCUPANCY_BACKFILL."""
    if backfill is None:
        backfill = settings.daily_occupancy_backfill
    status.running = True
    status.last_trigger = trigger
    status.last_run_started_at = facility_now_naive()
    status.last_lock_busy = False
    status.last_error = None
    try:
        results = run_locked(lambda db: _work(db, backfill))
        written = [r.day for r in results if r.status == "written"]
        skipped = [r.day for r in results if r.status == "skipped_no_data"]
        status.last_days_written = len(written)
        status.last_days_skipped_no_data = len(skipped)
        status.last_skipped_days = [d.isoformat() for d in skipped]
        if written or skipped:
            span = f" ({written[0]} .. {written[-1]})" if written else ""
            print(f"[daily_occupancy] {trigger}: wrote {len(written)} day(s){span}, "
                  f"skipped {len(skipped)} with no slot_status data")
    except LockBusy:
        status.last_lock_busy = True
        print(f"[daily_occupancy] {trigger}: another instance is running it - skipped")
    except Exception as exc:  # noqa: BLE001 — must never escape into the loop
        status.last_error = f"{type(exc).__name__}: {exc}"
        print(f"[daily_occupancy] {trigger} failed: {exc!r}")
    finally:
        status.running = False
        status.last_run_finished_at = facility_now_naive()


async def _loop() -> None:
    h, m = _run_at()
    backfill = settings.daily_occupancy_backfill
    status.enabled, status.backfill = True, backfill
    status.run_at = f"{h:02d}:{m:02d}"
    try:
        await asyncio.sleep(STARTUP_DELAY_SECONDS)
        print(f"[daily_occupancy] started (nightly at {status.run_at} facility-local, "
              f"backfill={backfill})")
        await asyncio.to_thread(run_once, "startup", backfill)

        while True:
            target = next_run_after(facility_now_naive(), h, m)
            status.next_run_at = target
            # One long sleep. Re-checked on waking in case the wall clock moved
            # (NTP) and asyncio's monotonic timer woke us a little early.
            while (now := facility_now_naive()) < target:
                await asyncio.sleep((target - now).total_seconds())
            await asyncio.to_thread(run_once, "nightly", backfill)
    except asyncio.CancelledError:
        print("[daily_occupancy] cancelled - shutting down")
        raise


def start() -> None:
    """Spawn the scheduler. Idempotent — call from FastAPI lifespan startup.
    With DAILY_OCCUPANCY_ENABLED=false no task is started at all."""
    global _task
    if _task and not _task.done():
        return
    if not settings.daily_occupancy_enabled:
        status.enabled = False
        print("[daily_occupancy] disabled (DAILY_OCCUPANCY_ENABLED=false)")
        return
    _task = asyncio.create_task(_loop(), name="daily_occupancy")


async def stop() -> None:
    """Cancel the scheduler. A run already in its worker thread finishes on its
    own; its day is written in one transaction, so it is never left half-done."""
    global _task
    if _task is None:
        return
    _task.cancel()
    try:
        await _task
    except (asyncio.CancelledError, Exception):
        pass
    _task = None
