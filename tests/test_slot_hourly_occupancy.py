"""Integration tests for dbo.slot_hourly_occupancy and everything that uses it.

Runs against the database in .env (local damanat_pms) — it needs migrator 0012
applied and slot_status data. Tests that change the table put it back the way
they found it (a day is re-computed, which the idempotency test proves gives
identical rows).

    pytest tests/test_slot_hourly_occupancy.py -v -p no:cacheprovider

Layers covered:
  1. the table itself      — migration 0012 shape, constraints, stored data
  2. services/daily_occupancy.py — compute_day / missing_days / backfill
  3. routers/occupancy.py  — _stored_days / _floor_hour_buckets
  4. the 5 report endpoints — same JSON with and without the table
  5. services/daily_occupancy_job.py — schedule, lock, run_once, start
  6. working-hours history — report_settings_history + trigger, the stamps,
     and "changing the window never rewrites past days"
"""
import asyncio
import os
import sys
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, engine, rows, scalar  # noqa: E402
from app.routers import occupancy  # noqa: E402
from app.services import daily_occupancy, daily_occupancy_job  # noqa: E402
from app.services.report_settings import (  # noqa: E402
    DayRule, ReportWindow, WindowHistory, get_window_history,
)

TABLE = "dbo.slot_hourly_occupancy"
REPORTS = ["kpis", "trend", "heatmap", "by-location", "summary"]


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


@pytest.fixture(scope="module")
def facts():
    """What the local data looks like, so the tests don't hardcode dates."""
    s = SessionLocal()
    try:
        if scalar(s, "SELECT OBJECT_ID('dbo.slot_hourly_occupancy', 'U')") is None:
            pytest.skip("slot_hourly_occupancy missing - run the migrator (0012)")
        stored = sorted(r["d"] for r in rows(s, f"""
            SELECT DISTINCT CAST(occupancy_hour AS DATE) AS d FROM {TABLE}"""))
        if len(stored) < 3:
            pytest.skip("need at least 3 stored days - let the job backfill first")
        data_days = {r["d"] for r in rows(s, """
            SELECT DISTINCT CAST(time AS DATE) AS d FROM slot_status""")}
        first = scalar(s, "SELECT CAST(MIN(time) AS DATE) FROM slot_status")
        slots = len(daily_occupancy._slots(s))
        return {
            "stored": stored,
            "first_data_day": first,
            "data_days": data_days,
            "slots": slots,
            # A completed day with no slot_status rows (VA down), if there is one.
            "no_data_day": next(
                (first + timedelta(days=i)
                 for i in range((daily_occupancy.yesterday() - first).days + 1)
                 if first + timedelta(days=i) not in data_days),
                None,
            ),
        }
    finally:
        s.close()


@pytest.fixture
def mid_day(facts):
    """A stored day from the middle of the history. Tests may delete it; it is
    re-computed afterwards, whatever happened."""
    day = facts["stored"][len(facts["stored"]) // 2]
    yield day
    s = SessionLocal()
    try:
        daily_occupancy.compute_day(s, day)
    finally:
        s.close()


def _day_rows(db, day):
    return rows(db, f"""
        SELECT occupancy_hour, slot_id, parking_slot_id, floor, floor_id,
               occupied_seconds, is_working_hour, working_hour_from,
               working_hour_to, occupancy_pct
        FROM {TABLE}
        WHERE occupancy_hour >= :a AND occupancy_hour < :b
        ORDER BY occupancy_hour, slot_id
    """, {"a": day, "b": day + timedelta(days=1)})


def _live_buckets(db, start, end):
    """The pre-table way: one live slot_status query over the whole range."""
    clause, params = occupancy._history_filter(db, start, end, "hour", None, None)
    found = rows(db, occupancy._occupied_seconds_sql("hour", clause, by_slot=False), params)
    return sorted(
        ({"floor": r["floor"], "bucket_start": r["bucket_start"],
          "total_occupied_seconds": int(r["total_occupied_seconds"] or 0)}
         for r in found if r["total_occupied_seconds"]),
        key=lambda r: (r["bucket_start"], r["floor"] or ""),
    )


def _at(day, hour=0, minute=0):
    return datetime.combine(day, datetime.min.time()) + timedelta(hours=hour, minutes=minute)


# ── 1. the table (migrator 0012) ─────────────────────────────────────────────

class TestTable:
    def test_columns(self, db):
        cols = {r["name"]: r for r in rows(db, """
            SELECT c.name, t.name AS type, c.is_nullable
            FROM sys.columns c JOIN sys.types t ON t.user_type_id = c.user_type_id
            WHERE c.object_id = OBJECT_ID('dbo.slot_hourly_occupancy')
        """)}
        assert {n: (c["type"], bool(c["is_nullable"])) for n, c in cols.items()} == {
            "occupancy_hour": ("datetime2", False),
            "slot_id": ("varchar", False),
            "parking_slot_id": ("int", True),
            "floor": ("varchar", True),
            "floor_id": ("int", True),
            "occupied_seconds": ("smallint", False),
            "is_working_hour": ("bit", False),
            "working_hour_from": ("tinyint", False),
            "working_hour_to": ("tinyint", False),
            "occupancy_pct": ("decimal", True),
            "computed_at": ("datetime2", False),
        }

    def test_primary_key_is_hour_then_slot(self, db):
        keys = [r["name"] for r in rows(db, """
            SELECT c.name FROM sys.indexes i
            JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
            JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
            WHERE i.object_id = OBJECT_ID('dbo.slot_hourly_occupancy') AND i.is_primary_key = 1
            ORDER BY ic.key_ordinal
        """)]
        assert keys == ["occupancy_hour", "slot_id"]

    def test_slot_index_exists(self, db):
        assert scalar(db, """
            SELECT COUNT(*) FROM sys.indexes
            WHERE object_id = OBJECT_ID('dbo.slot_hourly_occupancy')
              AND name = 'ix_slot_hourly_occupancy_slot_hour'
        """) == 1

    def test_daily_table_dropped(self, db):
        assert scalar(db, "SELECT OBJECT_ID('dbo.slot_daily_occupancy', 'U')") is None

    @pytest.mark.parametrize("bad", [
        {"hour": datetime(2000, 1, 1, 0, 0), "secs": 3601, "hf": 7, "ht": 18},
        {"hour": datetime(2000, 1, 1, 0, 0), "secs": -1, "hf": 7, "ht": 18},
        {"hour": datetime(2000, 1, 1, 0, 30), "secs": 0, "hf": 7, "ht": 18},
        {"hour": datetime(2000, 1, 1, 0, 0, 5), "secs": 0, "hf": 7, "ht": 18},
        {"hour": datetime(2000, 1, 1, 0, 0), "secs": 0, "hf": 18, "ht": 7},
        {"hour": datetime(2000, 1, 1, 0, 0), "secs": 0, "hf": 7, "ht": 25},
    ], ids=["seconds>3600", "seconds<0", "not-on-hour(min)", "not-on-hour(sec)",
            "from>=to", "to>24"])
    def test_check_constraint_rejects(self, db, bad):
        with pytest.raises(Exception, match="CK_slot_hourly_occupancy_values"):
            db.execute(text(f"""
                INSERT INTO {TABLE} (occupancy_hour, slot_id, occupied_seconds,
                                     is_working_hour, working_hour_from, working_hour_to)
                VALUES (:hour, 'TEST-SLOT', :secs, 1, :hf, :ht)
            """), bad)
        db.rollback()

    @pytest.mark.parametrize("secs,working,expected", [
        (2700, 1, 75.00), (1000, 1, 27.78), (3600, 1, 100.00), (0, 1, 0.00),
        (2700, 0, None),
    ])
    def test_occupancy_pct_is_computed(self, db, secs, working, expected):
        """SQL Server fills occupancy_pct: seconds/36 in working hours, NULL
        outside them (a not-measured hour, not an empty one)."""
        db.execute(text(f"""
            INSERT INTO {TABLE} (occupancy_hour, slot_id, occupied_seconds,
                                 is_working_hour, working_hour_from, working_hour_to)
            VALUES ('2000-01-01T10:00:00', 'TEST-SLOT', :s, :w, 7, 18)
        """), {"s": secs, "w": working})
        got = scalar(db, f"SELECT occupancy_pct FROM {TABLE} WHERE slot_id = 'TEST-SLOT'")
        db.rollback()
        assert (None if got is None else float(got)) == expected

    def test_transition_count_dropped(self, db):
        assert scalar(db, """
            SELECT COUNT(*) FROM sys.columns
            WHERE object_id = OBJECT_ID('dbo.slot_hourly_occupancy') AND name = 'transition_count'
        """) == 0

    def test_primary_key_rejects_duplicate(self, db):
        insert = text(f"""
            INSERT INTO {TABLE} (occupancy_hour, slot_id, occupied_seconds,
                                 is_working_hour, working_hour_from, working_hour_to)
            VALUES ('2000-01-01T00:00:00', 'TEST-SLOT', 0, 1, 7, 18)
        """)
        db.execute(insert)
        with pytest.raises(Exception, match="PK_slot_hourly_occupancy"):
            db.execute(insert)
        db.rollback()   # nothing was committed
        assert scalar(db, f"SELECT COUNT(*) FROM {TABLE} WHERE slot_id = 'TEST-SLOT'") == 0


# ── 2. the stored data ───────────────────────────────────────────────────────

class TestStoredData:
    def test_every_stored_day_is_whole(self, db, facts):
        """A day is all slots x 24 hours or absent - the reports rely on it."""
        per_day = rows(db, f"""
            SELECT CAST(occupancy_hour AS DATE) AS d, COUNT(*) AS n,
                   COUNT(DISTINCT slot_id) AS s, COUNT(DISTINCT occupancy_hour) AS h
            FROM {TABLE} GROUP BY CAST(occupancy_hour AS DATE)
        """)
        bad = [r for r in per_day if (r["n"], r["s"], r["h"]) != (facts["slots"] * 24, facts["slots"], 24)]
        assert bad == []

    def test_no_day_without_slot_status(self, facts):
        assert set(facts["stored"]) <= facts["data_days"]

    def test_no_today_or_future(self, db):
        today = daily_occupancy.facility_now_naive().date()
        assert scalar(db, f"SELECT COUNT(*) FROM {TABLE} WHERE occupancy_hour >= :t",
                      {"t": today}) == 0

    def test_stamps_follow_the_window_log(self, db, facts):
        """Every stored hour carries its day's window from the log, and
        occupancy_pct is NULL exactly outside working hours."""
        history = get_window_history(db)
        for day in facts["stored"]:
            rule = history.rule_for(day)
            for r in _day_rows(db, day):
                h = r["occupancy_hour"].hour
                assert (r["is_working_hour"], r["working_hour_from"], r["working_hour_to"]) == \
                       (rule.counts(h), rule.hour_from, rule.hour_to), (day, h)
                if rule.counts(h):
                    assert float(r["occupancy_pct"]) == round(r["occupied_seconds"] / 36, 2)
                else:
                    assert r["occupancy_pct"] is None

    def test_slot_metadata_matches_parking_slots(self, db, facts):
        day = facts["stored"][-1]
        slots = {s["slot_id"]: s for s in daily_occupancy._slots(db)}
        for r in _day_rows(db, day):
            s = slots[r["slot_id"]]
            assert (r["floor"], r["floor_id"], r["parking_slot_id"]) == \
                   (s["floor"], s["floor_id"], s["parking_slot_id"])


# ── 3. services/daily_occupancy.py ───────────────────────────────────────────

class TestService:
    def test_refuses_today_and_future(self, db):
        today = daily_occupancy.facility_now_naive().date()
        for day in (today, today + timedelta(days=1)):
            with pytest.raises(ValueError, match="not a completed day"):
                daily_occupancy.compute_day(db, day)

    def test_yesterday(self):
        assert daily_occupancy.yesterday() == \
            daily_occupancy.facility_now_naive().date() - timedelta(days=1)

    def test_no_data_day_is_skipped_not_stored(self, db, facts):
        day = facts["no_data_day"] or (facts["first_data_day"] - timedelta(days=1))
        result = daily_occupancy.compute_day(db, day)
        assert result.status == "skipped_no_data"
        assert _day_rows(db, day) == []

    def test_recompute_is_idempotent(self, db, mid_day):
        before = _day_rows(db, mid_day)
        result = daily_occupancy.compute_day(db, mid_day)
        assert result.status == "written"
        assert result.slots * 24 == len(before)
        assert _day_rows(db, mid_day) == before

    def test_stored_hours_equal_live_per_slot(self, db, mid_day):
        """The stored rows are exactly what the live query says for that day."""
        start, end = _at(mid_day), _at(mid_day + timedelta(days=1))
        clause, params = occupancy._history_filter(db, start, end, "hour", None, None)
        live = {(r["slot_id"], r["bucket_start"]): int(r["total_occupied_seconds"] or 0)
                for r in rows(db, occupancy._occupied_seconds_sql("hour", clause, by_slot=True), params)}
        stored = {(r["slot_id"], r["occupancy_hour"]): r["occupied_seconds"]
                  for r in _day_rows(db, mid_day)}
        assert {k: v for k, v in stored.items() if v} == {k: v for k, v in live.items() if v}

    def test_missing_days_and_backfill(self, db, facts, mid_day):
        assert mid_day not in daily_occupancy.missing_days(db)
        db.execute(text(f"DELETE FROM {TABLE} WHERE occupancy_hour >= :a AND occupancy_hour < :b"),
                   {"a": mid_day, "b": mid_day + timedelta(days=1)})
        db.commit()
        missing = daily_occupancy.missing_days(db)
        assert mid_day in missing
        assert set(missing).isdisjoint(set(facts["stored"]) - {mid_day})

        results = daily_occupancy.backfill(db)
        written = [r.day for r in results if r.status == "written"]
        assert written == [mid_day]
        assert all(r.status == "skipped_no_data" for r in results if r.day != mid_day)
        assert len(_day_rows(db, mid_day)) == facts["slots"] * 24

    def test_missing_days_through(self, db, facts):
        assert daily_occupancy.missing_days(db, through=facts["first_data_day"] - timedelta(days=1)) == []

    def test_compute_range(self, db, facts):
        a, b = facts["stored"][0], facts["stored"][1]
        before = _day_rows(db, a) + _day_rows(db, b)
        results = daily_occupancy.compute_range(db, a, b)
        assert [r.day for r in results] == [a, b]
        assert _day_rows(db, a) + _day_rows(db, b) == before

    def test_failed_write_leaves_day_untouched(self, db, mid_day, monkeypatch):
        """DELETE + INSERT are one transaction: a failing INSERT must not leave
        the day deleted."""
        before = _day_rows(db, mid_day)
        monkeypatch.setattr(daily_occupancy, "_INSERT", text("INSERT INTO dbo.no_such_table VALUES (1)"))
        with pytest.raises(Exception):
            daily_occupancy.compute_day(db, mid_day)
        assert _day_rows(db, mid_day) == before


# ── 4. routers/occupancy.py helpers ──────────────────────────────────────────

class TestReportHelpers:
    def test_stored_days(self, db, facts):
        s = facts["stored"]
        assert set(occupancy._stored_days(db, s[0], s[-1])) == set(s)

    def test_stored_days_degrades_when_table_unreadable(self, db, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("Invalid object name 'dbo.slot_hourly_occupancy'")
        monkeypatch.setattr(occupancy, "rows", boom)
        assert occupancy._stored_days(db, date(2026, 1, 1), date(2026, 1, 2)) == {}

    def test_ranges_match_live(self, db, facts):
        s = facts["stored"]
        first, mid, last = s[0], s[len(s) // 2], s[-1]
        today = daily_occupancy.facility_now_naive().date()
        cases = {
            "one stored day": (_at(mid), _at(mid + timedelta(days=1))),
            "whole history": (_at(first), _at(last + timedelta(days=1))),
            "mid-hour both ends": (_at(mid, 14, 30), _at(mid + timedelta(days=2), 9, 15)),
            "inside one hour": (_at(mid, 10, 5), _at(mid, 10, 50)),
            "cross midnight": (_at(mid, 22), _at(mid + timedelta(days=1), 3)),
            "stored into unstored": (_at(last - timedelta(days=1)), _at(last + timedelta(days=5))),
            "before any data": (_at(first - timedelta(days=3)), _at(first + timedelta(days=1))),
            "yesterday to now": (_at(today - timedelta(days=1)), daily_occupancy.facility_now_naive()),
        }
        for name, (a, b) in cases.items():
            assert occupancy._floor_hour_buckets(db, a, b) == _live_buckets(db, a, b), name

    def test_hole_in_the_middle_matches_live(self, db, facts, mid_day):
        """A range with an unstored day between stored ones mixes both paths."""
        db.execute(text(f"DELETE FROM {TABLE} WHERE occupancy_hour >= :a AND occupancy_hour < :b"),
                   {"a": mid_day, "b": mid_day + timedelta(days=1)})
        db.commit()
        a, b = _at(mid_day - timedelta(days=2)), _at(mid_day + timedelta(days=3))
        assert occupancy._floor_hour_buckets(db, a, b) == _live_buckets(db, a, b)

    def test_stored_path_is_used(self, db, facts, monkeypatch):
        """A stored range must not run the live slot_status query at all."""
        def no_live(*a, **k):
            raise AssertionError("live query ran for a stored range")
        monkeypatch.setattr(occupancy, "_occupied_seconds_sql", no_live)
        mid = facts["stored"][len(facts["stored"]) // 2]
        assert occupancy._floor_hour_buckets(db, _at(mid), _at(mid + timedelta(days=1)))


# ── 5. the report endpoints ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    # No `with`: the lifespan (camera monitor, occupancy job) is not started.
    return TestClient(app)


class TestEndpoints:
    @pytest.mark.parametrize("report", REPORTS)
    @pytest.mark.parametrize("extra", [
        "", "&business_hours=false", "&hour_from=9&hour_to=16",
    ], ids=["default", "24h", "9-16"])
    def test_same_json_with_and_without_table(self, client, facts, monkeypatch, report, extra):
        s = facts["stored"]
        # Starts mid-hour on a busy morning: a live 10:15-11:00 stretch, then a
        # stored run whose first hour has cars in it (a midnight start would
        # hide a lost first hour behind an empty garage).
        url = (f"/occupancy/history/{report}?start_time={_at(s[1], 10, 15).isoformat()}"
               f"&end_time={_at(s[-1] + timedelta(days=1), 12, 30).isoformat()}{extra}")
        with_table = client.get(url)
        assert with_table.status_code == 200, with_table.text
        monkeypatch.setattr(occupancy, "_stored_days", lambda *a, **k: {})
        live = client.get(url)
        assert live.status_code == 200
        assert with_table.json() == live.json()

    def test_trend_grains(self, client, facts, monkeypatch):
        s = facts["stored"]
        base = f"start_time={_at(s[0]).isoformat()}&end_time={_at(s[-1]).isoformat()}"
        for grain in ("hour", "day", "week", "month", "weekday"):
            url = f"/occupancy/history/trend?{base}&grain={grain}"
            a = client.get(url)
            assert a.status_code == 200, (grain, a.text)
            with monkeypatch.context() as m:
                m.setattr(occupancy, "_stored_days", lambda *a, **k: {})
                assert client.get(url).json() == a.json(), grain

    def test_bad_range_still_400(self, client):
        r = client.get("/occupancy/history/kpis?start_time=2026-07-10T00:00:00"
                       "&end_time=2026-07-09T00:00:00")
        assert r.status_code == 400

    def test_reports_survive_missing_table(self, client, facts, monkeypatch):
        """Gateway deployed before migrator 0012: reports compute live, no 500."""
        real_rows = occupancy.rows

        def rows_without_table(db, sql, *a, **k):
            if "slot_hourly_occupancy" in sql:
                raise RuntimeError("Invalid object name 'dbo.slot_hourly_occupancy'")
            return real_rows(db, sql, *a, **k)
        s = facts["stored"]
        url = (f"/occupancy/history/kpis?start_time={_at(s[0]).isoformat()}"
               f"&end_time={_at(s[2]).isoformat()}")
        good = client.get(url).json()
        monkeypatch.setattr(occupancy, "rows", rows_without_table)
        r = client.get(url)
        assert r.status_code == 200
        assert r.json() == good


# ── 6. services/daily_occupancy_job.py ───────────────────────────────────────

class TestJob:
    @pytest.mark.parametrize("now,expected", [
        (datetime(2026, 9, 27, 0, 5), datetime(2026, 9, 27, 0, 10)),
        (datetime(2026, 9, 27, 0, 10), datetime(2026, 9, 28, 0, 10)),   # strictly after
        (datetime(2026, 9, 27, 15, 0), datetime(2026, 9, 28, 0, 10)),
        (datetime(2026, 12, 31, 23, 59), datetime(2027, 1, 1, 0, 10)),
    ])
    def test_next_run_after(self, now, expected):
        assert daily_occupancy_job.next_run_after(now, 0, 10) == expected

    @pytest.mark.parametrize("h,m,expected", [
        (2, 30, (2, 30)), (24, 0, (0, 10)), (0, 60, (0, 10)), (-1, 5, (0, 10)),
    ])
    def test_run_at_falls_back(self, monkeypatch, h, m, expected):
        monkeypatch.setattr(daily_occupancy_job.settings, "daily_occupancy_run_hour", h)
        monkeypatch.setattr(daily_occupancy_job.settings, "daily_occupancy_run_minute", m)
        assert daily_occupancy_job._run_at() == expected

    def test_lock_busy_when_another_pod_holds_it(self):
        with engine.connect() as other:
            with other.begin():
                other.execute(text("""
                    EXEC sp_getapplock @Resource = :r, @LockMode = 'Exclusive',
                                       @LockOwner = 'Transaction', @LockTimeout = 0
                """), {"r": daily_occupancy_job.LOCK_RESOURCE})
                with pytest.raises(daily_occupancy_job.LockBusy):
                    daily_occupancy_job.run_locked(lambda db: None)
        # Released with the other transaction: now it is ours.
        assert daily_occupancy_job.run_locked(lambda db: "ran") == "ran"

    def test_lock_released_after_error(self):
        with pytest.raises(ZeroDivisionError):
            daily_occupancy_job.run_locked(lambda db: 1 / 0)
        assert daily_occupancy_job.run_locked(lambda db: "ran") == "ran"

    def test_run_once_nothing_to_do(self, monkeypatch):
        monkeypatch.setattr(daily_occupancy, "backfill", lambda db: [])
        daily_occupancy_job.run_once("test", backfill=True)
        st = daily_occupancy_job.status
        assert (st.running, st.last_error, st.last_days_written, st.last_trigger) == \
               (False, None, 0, "test")

    def test_run_once_never_raises(self, monkeypatch):
        def boom(db):
            raise RuntimeError("db exploded")
        monkeypatch.setattr(daily_occupancy, "backfill", boom)
        daily_occupancy_job.run_once("test", backfill=True)
        assert daily_occupancy_job.status.last_error == "RuntimeError: db exploded"
        assert daily_occupancy_job.status.running is False

    def test_run_once_reports_lock_busy(self):
        with engine.connect() as other:
            with other.begin():
                other.execute(text("""
                    EXEC sp_getapplock @Resource = :r, @LockMode = 'Exclusive',
                                       @LockOwner = 'Transaction', @LockTimeout = 0
                """), {"r": daily_occupancy_job.LOCK_RESOURCE})
                daily_occupancy_job.run_once("test", backfill=True)
        assert daily_occupancy_job.status.last_lock_busy is True
        assert daily_occupancy_job.status.last_error is None

    def test_run_once_counts(self, monkeypatch):
        DR = daily_occupancy.DayResult
        results = [DR(date(2026, 7, 1), "written", 35),
                   DR(date(2026, 7, 2), "skipped_no_data")]
        monkeypatch.setattr(daily_occupancy, "backfill", lambda db: results)
        daily_occupancy_job.run_once("test", backfill=True)
        st = daily_occupancy_job.status
        assert (st.last_days_written, st.last_days_skipped_no_data, st.last_skipped_days) == \
               (1, 1, ["2026-07-02"])

    def test_backfill_off_only_yesterday(self, db, monkeypatch):
        """With backfill off the job touches yesterday only, and only if missing."""
        called = []
        monkeypatch.setattr(daily_occupancy, "backfill", lambda db: called.append("backfill"))
        monkeypatch.setattr(daily_occupancy, "missing_days", lambda db, through: [])
        assert daily_occupancy_job._work(db, backfill=False) == []
        y = daily_occupancy.yesterday()
        monkeypatch.setattr(daily_occupancy, "missing_days", lambda db, through: [through])
        monkeypatch.setattr(daily_occupancy, "compute_day",
                            lambda db, day: daily_occupancy.DayResult(day, "skipped_no_data"))
        assert [r.day for r in daily_occupancy_job._work(db, backfill=False)] == [y]
        assert called == []

    def test_start_disabled_starts_nothing(self, monkeypatch):
        monkeypatch.setattr(daily_occupancy_job.settings, "daily_occupancy_enabled", False)

        async def go():
            daily_occupancy_job.start()
            return daily_occupancy_job._task
        assert asyncio.run(go()) is None
        assert daily_occupancy_job.status.enabled is False

    def test_loop_runs_startup_then_nightly_then_stops(self, monkeypatch):
        """Startup run, then sleep to the next run time and run nightly; stop()
        cancels cleanly. The clock and the run are faked."""
        runs = []
        monkeypatch.setattr(daily_occupancy_job, "STARTUP_DELAY_SECONDS", 0)
        monkeypatch.setattr(daily_occupancy_job.settings, "daily_occupancy_enabled", True)
        monkeypatch.setattr(daily_occupancy_job, "run_once", lambda trigger, backfill: runs.append(trigger))
        # The "next run" is always 50 ms away.
        monkeypatch.setattr(daily_occupancy_job, "next_run_after",
                            lambda now, h, m: now + timedelta(milliseconds=50))

        async def go():
            daily_occupancy_job.start()
            await asyncio.sleep(0.4)
            await daily_occupancy_job.stop()
        asyncio.run(go())
        assert runs[0] == "startup"
        assert "nightly" in runs
        assert daily_occupancy_job._task is None


# ── 7. working-hours history ─────────────────────────────────────────────────

def _w(h_from, h_to, days=range(7), enabled=True):
    return ReportWindow(enabled=enabled, hour_from=h_from, hour_to=h_to,
                        weekdays=frozenset(days), source="db")


class TestWindowHistoryRules:
    """Pure logic: which window applies to which day."""
    A, B, C = _w(7, 18), _w(9, 16, days=[6, 0, 1, 2, 3]), _w(8, 17)
    CHANGE = datetime(2026, 7, 10, 15, 0)     # B takes over mid-afternoon

    def hist(self, current=None):
        return WindowHistory(current or self.B, [(datetime(2000, 1, 1), self.A), (self.CHANGE, self.B)])

    def test_day_before_change_keeps_old_window(self):
        assert self.hist().window_for(date(2026, 7, 9)) == self.A

    def test_change_during_a_day_applies_to_that_whole_day(self):
        assert self.hist().window_for(date(2026, 7, 10)) == self.B

    def test_days_after_last_change_use_current(self):
        assert self.hist(current=self.C).window_for(date(2026, 7, 11)) == self.C

    def test_log_behind_settings_only_affects_later_days(self):
        # current (C) disagrees with the last log row (B): the past still uses the log.
        assert self.hist(current=self.C).window_for(date(2026, 7, 9)) == self.A

    def test_before_first_entry_uses_earliest(self):
        h = WindowHistory(self.C, [(datetime(2026, 7, 1), self.A), (self.CHANGE, self.B)])
        assert h.window_for(date(2026, 6, 1)) == self.A

    def test_empty_log_uses_current(self):
        assert WindowHistory(self.C, []).window_for(date(2020, 1, 1)) == self.C

    def test_rules(self):
        h = self.hist()
        assert h.rule_for(date(2026, 7, 9)) == DayRule(True, 7, 18)
        assert h.rule_for(date(2026, 7, 10)) == DayRule(False, 9, 16)   # a Friday, not in Sun..Thu
        assert h.rule_for(date(2026, 7, 12)) == DayRule(True, 9, 16)    # Sunday
        off = WindowHistory(_w(7, 18, enabled=False), [])
        assert off.rule_for(date(2026, 7, 10)) == DayRule(True, 0, 24)
        assert DayRule(True, 7, 18).counts(7) and not DayRule(True, 7, 18).counts(18)
        assert not DayRule(False, 7, 18).counts(10)


_META = {"start_time", "end_time", "total_capacity", "business_hours_applied",
         "business_hour_from", "business_hour_to", "business_days"}


def _strip_meta(payload):
    return {k: v for k, v in payload.items() if k not in _META}


@pytest.fixture
def settings_guard():
    """Puts report_settings, the history log and any re-stamped days back as
    they were. Tests append days they re-computed to the yielded list."""
    s = SessionLocal()
    saved = rows(s, "SELECT * FROM dbo.report_settings WHERE id = 1")[0]
    max_id = scalar(s, "SELECT ISNULL(MAX(id), 0) FROM dbo.report_settings_history")
    s.close()
    touched: list = []
    yield touched
    s = SessionLocal()
    try:
        s.execute(text("""
            UPDATE dbo.report_settings
               SET business_hours_enabled = :e, business_hour_from = :f,
                   business_hour_to = :t, business_days = :d,
                   updated_at = :u, updated_by = :b
             WHERE id = 1
        """), {"e": saved["business_hours_enabled"], "f": saved["business_hour_from"],
               "t": saved["business_hour_to"], "d": saved["business_days"],
               "u": saved["updated_at"], "b": saved["updated_by"]})
        # After the restore, so the restore's own trigger row goes too.
        s.execute(text("DELETE FROM dbo.report_settings_history WHERE id > :m"), {"m": max_id})
        s.commit()
        for day in sorted(set(touched)):
            daily_occupancy.compute_day(s, day)
    finally:
        s.close()


def _log_change(db, local_from: datetime, h_from, h_to, days):
    """Backdate a window change, as if it had been saved at `local_from`."""
    from app.config import facility_tz
    db.execute(text("""
        INSERT INTO dbo.report_settings_history
            (valid_from_utc, business_hours_enabled, business_hour_from,
             business_hour_to, business_days, changed_by)
        VALUES (:v, 1, :f, :t, :d, 'pytest')
    """), {"v": local_from - facility_tz().utcoffset(None), "f": h_from, "t": h_to, "d": days})
    db.commit()


def _stamps(db, day):
    return {(r["is_working_hour"], r["working_hour_from"], r["working_hour_to"])
            for r in _day_rows(db, day)}


class TestWorkingHoursHistory:
    def test_seed_row_covers_all_history(self, db):
        first = rows(db, "SELECT TOP 1 * FROM dbo.report_settings_history ORDER BY valid_from_utc, id")[0]
        assert first["valid_from_utc"] == datetime(2000, 1, 1)

    def test_trigger_logs_real_changes_only(self, db, settings_guard):
        def count():
            return scalar(db, "SELECT COUNT(*) FROM dbo.report_settings_history")
        before = count()
        db.execute(text("UPDATE dbo.report_settings SET business_hour_from = 9, business_hour_to = 16 WHERE id = 1"))
        db.commit()
        assert count() == before + 1
        last = rows(db, "SELECT TOP 1 * FROM dbo.report_settings_history ORDER BY id DESC")[0]
        assert (last["business_hour_from"], last["business_hour_to"]) == (9, 16)
        # Saving the same window again, or changing only who saved it: no row.
        db.execute(text("UPDATE dbo.report_settings SET business_hour_from = 9 WHERE id = 1"))
        db.execute(text("UPDATE dbo.report_settings SET updated_by = N'someone' WHERE id = 1"))
        db.commit()
        assert count() == before + 1

    def test_put_changes_today_not_the_past(self, client, db, facts, settings_guard):
        """Saving new hours leaves every stored day's figures untouched; only
        the caption (the current window) and today onwards change."""
        s = facts["stored"]
        qs = f"start_time={_at(s[0]).isoformat()}&end_time={_at(s[-1] + timedelta(days=1)).isoformat()}"
        before = {r: client.get(f"/occupancy/history/{r}?{qs}").json() for r in REPORTS}

        put = client.put("/settings/report", json={
            "business_hours_enabled": True, "business_hour_from": 9,
            "business_hour_to": 16, "business_days": ["Sun", "Mon", "Tue", "Wed", "Thu"],
        })
        assert put.status_code == 200, put.text

        for r in REPORTS:
            after = client.get(f"/occupancy/history/{r}?{qs}").json()
            assert _strip_meta(after) == _strip_meta(before[r]), r
            assert (after["business_hour_from"], after["business_hour_to"]) == (9, 16)

        # Re-computing an old day keeps its old stamp; today uses the new hours.
        day = s[len(s) // 2]
        settings_guard.append(day)
        old = _stamps(db, day)
        daily_occupancy.compute_day(db, day)
        assert _stamps(db, day) == old
        today = daily_occupancy.facility_now_naive().date()
        assert get_window_history(db).rule_for(today).hour_from == 9

    def test_backdated_window_applies_to_its_days_only(self, client, db, facts, settings_guard):
        """Hours were 9-16 Sun..Thu for one day, then changed back. That day is
        stamped 9-16, its neighbours keep the original, and the reports count
        each day by its own hours - identically whether the day is read from
        the table or computed live."""
        s = facts["stored"]
        day = s[len(s) // 2]
        orig = rows(db, "SELECT * FROM dbo.report_settings WHERE id = 1")[0]
        o_from, o_to = orig["business_hour_from"], orig["business_hour_to"]
        _log_change(db, _at(day, 12), 9, 16, "Sun,Mon,Tue,Wed,Thu")
        _log_change(db, _at(day + timedelta(days=1), 12), o_from, o_to, orig["business_days"])
        around = [day - timedelta(days=1), day, day + timedelta(days=1)]
        settings_guard.extend(around)
        for d in around:
            daily_occupancy.compute_day(db, d)

        hours = {d: {(r["working_hour_from"], r["working_hour_to"]) for r in _day_rows(db, d)} for d in around}
        assert hours[day] == {(9, 16)}
        assert hours[around[0]] == hours[around[2]] == {(o_from, o_to)}
        working = {r["occupancy_hour"].hour for r in _day_rows(db, day) if r["is_working_hour"]}
        assert working == (set(range(9, 16)) if day.weekday() in (6, 0, 1, 2, 3) else set())

        qs = (f"start_time={_at(day - timedelta(days=3)).isoformat()}"
              f"&end_time={_at(day + timedelta(days=4)).isoformat()}")
        for extra in ("", "&hour_from=8&hour_to=12", "&business_hours=false"):
            for r in REPORTS:
                url = f"/occupancy/history/{r}?{qs}{extra}"
                with_table = client.get(url)
                assert with_table.status_code == 200, with_table.text
                with pytest.MonkeyPatch.context() as m:
                    m.setattr(occupancy, "_stored_days", lambda *a, **k: {})
                    assert client.get(url).json() == with_table.json(), (r, extra)

        # The default view really uses per-day hours: it differs from forcing
        # the original window onto every day.
        per_day = client.get(f"/occupancy/history/kpis?{qs}").json()
        forced = client.get(f"/occupancy/history/kpis?{qs}&hour_from={o_from}&hour_to={o_to}").json()
        assert per_day["overall_utilization"] != forced["overall_utilization"]

        # The heatmap rows cover every hour that counted on some day.
        heat = client.get(f"/occupancy/history/heatmap?{qs}").json()
        assert (heat["rows"][0]["hour_from"], heat["rows"][-1]["hour_to"]) == (o_from, o_to)

    def test_stored_stamps_win_over_a_later_log_edit(self, client, db, facts, settings_guard):
        """Option A: a stored day is the record. If the log is edited afterwards
        (a backdated row, a manual fix), days already stored keep the hours they
        were stored under until someone re-computes them on purpose."""
        s = facts["stored"]
        day = s[len(s) // 2]
        qs = f"start_time={_at(day).isoformat()}&end_time={_at(day + timedelta(days=1)).isoformat()}"
        before = {r: client.get(f"/occupancy/history/{r}?{qs}").json() for r in REPORTS}
        orig = rows(db, "SELECT * FROM dbo.report_settings WHERE id = 1")[0]
        _log_change(db, _at(day, 9), 10, 12, "Mon,Tue,Wed,Thu,Fri,Sat,Sun")
        _log_change(db, _at(day + timedelta(days=1), 9), orig["business_hour_from"],
                    orig["business_hour_to"], orig["business_days"])
        assert get_window_history(db).rule_for(day) == DayRule(True, 10, 12)   # the log now says 10-12
        for r in REPORTS:
            assert client.get(f"/occupancy/history/{r}?{qs}").json() == before[r], r


# ── 8. Peak Hours default range (Occupancy page) ─────────────────────────────

class TestPeakHoursDefault:
    NOW = datetime(2026, 7, 29, 15, 30)    # a Wednesday afternoon with data

    def test_default_is_today_and_the_6_days_before(self, client, monkeypatch):
        monkeypatch.setattr(occupancy, "facility_now_naive", lambda: self.NOW)
        r = client.get("/occupancy/history/heatmap?block_hours=4&business_hours=false")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["start_time"].startswith("2026-07-23T00:00:00")
        assert body["end_time"].startswith("2026-07-29T15:30:00")
        assert [row["label"] for row in body["rows"]] == [
            "00:00-04:00", "04:00-08:00", "08:00-12:00",
            "12:00-16:00", "16:00-20:00", "20:00-24:00"]
        today = self.NOW.weekday()
        for cell in body["cells"]:
            later_today = cell["weekday_index"] == today and cell["row_index"] >= 4   # 16:00 onwards
            if later_today:
                assert cell["occupancy"] is None and cell["days_sampled"] == 0
            else:
                # every weekday column is exactly one date
                assert cell["days_sampled"] == 1, cell

        explicit = client.get("/occupancy/history/heatmap?block_hours=4&business_hours=false"
                              "&start_time=2026-07-23T00:00:00&end_time=2026-07-29T15:30:00")
        assert explicit.json() == body

    def test_one_edge_only_is_rejected(self, client):
        r = client.get("/occupancy/history/heatmap?start_time=2026-07-23T00:00:00")
        assert r.status_code == 400
