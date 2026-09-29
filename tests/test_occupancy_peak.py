"""Reports · Peak Hours Analysis — three endpoints, one per widget:

  GET /occupancy/history/peak-hours/kpis      Peak Hour, Maximum Occupancy, Peak Day, Peak-Hour Entries
  GET /occupancy/history/peak-hours/by-floor  the pie: average occupancy per floor
  GET /occupancy/history/peak-hours/by-hour   Occupancy by Hour bars

Peak Hour = the MODE of the daily peak hours: each day votes for its own
busiest hour, the most-voted hour wins (client rule: Sat/Mon/Tue peak at 8,
the rest of the week at 18 -> 18).

Two layers:
  1. the calculations on a synthetic _ReportBase — every rule, tie-break and
     window edge, no database;
  2. the endpoints on the database in .env — agreement with the other report
     endpoints that must say the same thing. Read-only.

    pytest tests/test_occupancy_peak.py -v -p no:cacheprovider
"""
import os
import sys
from collections import Counter
from datetime import date, datetime, timedelta

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, scalar  # noqa: E402
from app.routers import occupancy  # noqa: E402
from app.services.report_settings import DayRule  # noqa: E402

HOUR = 3600
MON = date(2026, 7, 6)   # a Monday
KPIS = "/occupancy/history/peak-hours/kpis"
BY_FLOOR = "/occupancy/history/peak-hours/by-floor"
BY_HOUR = "/occupancy/history/peak-hours/by-hour"


# ── 1. the calculations, on synthetic data ───────────────────────────────────

def _base(start: date, days: int, occ: dict, h_from=0, h_to=24, off_days=(), floors=None):
    """A _ReportBase over `days` whole days from `start`. `occ` maps
    (day_index, hour) -> occupied slots for that whole hour, on floor "G", or
    (day_index, hour, floor) -> slots when `floors` ({floor: capacity}) is given."""
    floors = floors or {"G": 10}
    s = datetime.combine(start, datetime.min.time())
    buckets = []
    for key, slots in sorted(occ.items()):
        i, h, f = key if len(key) == 3 else (*key, "G")
        if slots:
            buckets.append({"floor": f, "bucket_start": s + timedelta(days=i, hours=h),
                            "total_occupied_seconds": slots * HOUR})
    rules = {start + timedelta(days=i): DayRule((start + timedelta(days=i)).weekday() not in off_days, h_from, h_to)
             for i in range(days)}
    base = occupancy._ReportBase(
        start_time=s, end_time=s + timedelta(days=days),
        capacity_by_floor=floors, total_capacity=sum(floors.values()),
        buckets=buckets, applied=(h_from, h_to) != (0, 24), h_from=h_from, h_to=h_to,
        days=frozenset(range(7)) - set(off_days), day_rules=rules, offered_seconds=0.0, day_offered={},
    )
    # The denominators _report_base() walks in after construction.
    cursor = s
    while cursor < base.end_time:
        span = base.counted_span(cursor)
        base.offered_seconds += span
        if span:
            base.day_offered[cursor.date()] = base.day_offered.get(cursor.date(), 0.0) + span
        cursor += timedelta(hours=1)
    return base


@pytest.fixture
def entries(monkeypatch):
    """Stub the parking_sessions query: {(date, hour): n}."""
    data: dict = {}

    def fake_rows(db, sql, params=None):
        assert "parking_sessions" in sql
        return [{"d": d, "n": n} for (d, h), n in data.items() if h == params["h"]]
    monkeypatch.setattr(occupancy, "rows", fake_rows)
    return data


def _kpis(base):
    return occupancy._report_peak_kpis(None, base)


def _votes(base):
    return occupancy._peak_vote(occupancy._peak_days(base, occupancy._counted_hours(base)))


class TestPeakHourVote:
    def test_client_example_week(self, entries):
        # Mon..Sun. Sat/Mon/Tue peak at 8, Wed/Thu/Fri/Sun at 18.
        occ = {}
        for i in range(7):
            occ[(i, 8)] = occ[(i, 18)] = 4
            occ[(i, 8 if (MON + timedelta(days=i)).weekday() in (0, 1, 5) else 18)] = 9
        base = _base(MON, 7, occ)
        r = _kpis(base)
        assert (r.peak_hour, r.peak_hour_label) == (18, "6:00 PM")
        assert (r.peak_hour_days, r.days_counted) == (4, 7)
        assert [(h, n) for h, n, _ in _votes(base)] == [(18, 4), (8, 3)]

    def test_mode_not_busiest_hour(self, entries):
        # One full 8 AM day must not beat three ordinary 6 PM days.
        r = _kpis(_base(MON, 4, {(0, 8): 10, (1, 18): 5, (2, 18): 5, (3, 18): 5}))
        assert r.peak_hour == 18
        assert r.max_occupancy == 100.0 and r.max_occupancy_at.hour == 8

    def test_same_rule_for_a_month(self, entries):
        # Jul 6 - Aug 4: the 4 Wednesdays + 4 Fridays peak at 15, the other 22 at 10.
        occ = {(i, 15 if (MON + timedelta(days=i)).weekday() in (2, 4) else 10): 6 for i in range(30)}
        base = _base(MON, 30, occ)
        r = _kpis(base)
        assert (r.peak_hour, r.peak_hour_days, r.days_counted) == (10, 22, 30)
        assert [(h, n) for h, n, _ in _votes(base)] == [(10, 22), (15, 8)]

    def test_tie_goes_to_higher_average_peak(self, entries):
        base = _base(MON, 4, {(0, 8): 5, (1, 8): 5, (2, 18): 7, (3, 18): 7})
        assert _kpis(base).peak_hour == 18
        assert [(h, n, round(a, 1)) for h, n, a in _votes(base)] == [(18, 2, 70.0), (8, 2, 50.0)]

    def test_full_tie_goes_to_earlier_hour(self, entries):
        assert _kpis(_base(MON, 2, {(0, 18): 6, (1, 8): 6})).peak_hour == 8

    def test_tie_inside_a_day_goes_to_earlier_hour(self, entries):
        assert _kpis(_base(MON, 1, {(0, 9): 10, (0, 14): 10})).peak_hour == 9

    def test_day_without_parking_does_not_vote(self, entries):
        r = _kpis(_base(MON, 3, {(0, 8): 3, (2, 8): 3}))
        assert r.days_counted == 2


class TestWindow:
    def test_excluded_hour_never_wins(self, entries):
        occ = {}
        for i in range(3):
            occ[(i, 20)] = 10                 # busiest, but outside 07-18
            occ[(i, 11)] = 4
        r = _kpis(_base(MON, 3, occ, h_from=7, h_to=18))
        assert (r.peak_hour, r.max_occupancy) == (11, 40.0)

    def test_parking_only_outside_window_does_not_vote(self, entries):
        r = _kpis(_base(MON, 2, {(0, 22): 10, (1, 11): 2}, h_from=7, h_to=18))
        assert (r.days_counted, r.peak_hour) == (1, 11)

    def test_non_working_day_does_not_vote(self, entries):
        # Fri (4) and Sat (5) are off and are the only 15:00 days.
        occ = {(i, 15 if i in (4, 5) else 9): 5 for i in range(7)}
        r = _kpis(_base(MON, 7, occ, off_days=(4, 5)))
        assert (r.peak_hour, r.days_counted) == (9, 5)

    def test_empty_range(self, entries):
        r = _kpis(_base(MON, 3, {}))
        assert r.peak_hour is None and r.peak_hour_label is None and r.peak_day is None
        assert (r.days_counted, r.peak_hour_entries, r.max_occupancy) == (0, 0, 0.0)

    def test_no_capacity(self, entries):
        base = _base(MON, 1, {(0, 9): 1})
        base.total_capacity = 0
        assert _kpis(base).peak_hour is None
        assert occupancy._report_peak_by_hour(base, 2).peak_index is None


class TestPeakDayAndEntries:
    def test_peak_day_is_highest_day_average(self, entries):
        # Day 1 has the busiest single hour, day 2 the higher average.
        r = _kpis(_base(MON, 3, {(0, 9): 2, (1, 9): 10, (2, 9): 6, (2, 10): 6, (2, 11): 6}))
        assert r.peak_day == MON + timedelta(days=2)
        assert r.peak_day_occupancy == round(18 / (10 * 24) * 100, 1)

    def test_peak_day_label_weekday_up_to_a_week(self, entries):
        assert _kpis(_base(MON, 7, {(3, 9): 5})).peak_day_label == "Thursday"

    def test_peak_day_label_date_beyond_a_week(self, entries):
        assert _kpis(_base(MON, 8, {(3, 9): 5})).peak_day_label == "July 9, 2026"

    def test_hour_labels(self):
        assert [occupancy._hour_label(h) for h in (0, 8, 12, 18, 23)] == \
            ["12:00 AM", "8:00 AM", "12:00 PM", "6:00 PM", "11:00 PM"]

    def test_entries_only_on_days_that_count_the_hour(self, entries):
        occ = {(i, 9): 5 for i in range(5)}
        for i in range(5):
            entries[(MON + timedelta(days=i), 9)] = 10
        entries[(MON, 14)] = 99               # another hour: ignored
        r = _kpis(_base(MON, 5, occ, off_days=(4,)))    # Fri off -> its 10 don't count
        assert (r.peak_hour, r.peak_hour_entries) == (9, 40)


class TestByFloor:
    FLOORS = {"Ground": 8, "B1": 12, "B2": 15}

    def test_average_and_share(self):
        # One day: Ground 4 slots x 12h, B1 6 x 12h, B2 0.
        occ = {}
        for h in range(12):
            occ[(0, h, "Ground")] = 4
            occ[(0, h, "B1")] = 6
        r = occupancy._report_peak_by_floor(_base(MON, 1, occ, floors=self.FLOORS))
        got = {i.floor: (i.label, i.capacity, i.avg_occupancy, i.occupied_share_pct) for i in r.items}
        assert got == {
            "Ground": ("Ground", 8, 25.0, 40.0),        # 48 / (8*24);  48 / 120
            "B1": ("Basement 1", 12, 25.0, 60.0),       # 72 / (12*24); 72 / 120
            "B2": ("Basement 2", 15, 0.0, 0.0),         # still a slice
        }
        assert r.items[0].floor == "Ground"

    def test_window_excludes_hours(self):
        occ = {(0, 20, "Ground"): 8, (0, 10, "B1"): 12}
        r = occupancy._report_peak_by_floor(_base(MON, 1, occ, h_from=7, h_to=18, floors=self.FLOORS))
        assert {i.floor: i.occupied_share_pct for i in r.items} == {"Ground": 0.0, "B1": 100.0, "B2": 0.0}

    def test_empty_range_keeps_every_floor(self):
        r = occupancy._report_peak_by_floor(_base(MON, 2, {}, floors=self.FLOORS))
        assert [(i.floor, i.avg_occupancy, i.occupied_share_pct) for i in r.items] == \
            [("Ground", 0.0, 0.0), ("B1", 0.0, 0.0), ("B2", 0.0, 0.0)]


class TestByHour:
    def test_bars_are_mean_of_days(self):
        # 2 days, step 2: 08-10 is 5 slots both hours on day 1, nothing on day 2 -> mean(50, 0) = 25.
        r = occupancy._report_peak_by_hour(_base(MON, 2, {(0, 8): 5, (0, 9): 5}), 2)
        assert len(r.bars) == 12 and r.step_hours == 2
        bar = r.bars[4]
        assert (bar.hour_from, bar.hour_to, bar.label, bar.occupancy, bar.days_sampled) == (8, 10, "8:00 AM", 25.0, 2)
        assert r.peak_index == 4
        assert all(b.occupancy == 0.0 for b in r.bars if b.index != 4)

    def test_bars_follow_window_last_bar_shorter(self):
        r = occupancy._report_peak_by_hour(_base(MON, 1, {(0, 17): 10}, h_from=7, h_to=18), 2)
        assert [(b.hour_from, b.hour_to) for b in r.bars] == [(7, 9), (9, 11), (11, 13), (13, 15), (15, 17), (17, 18)]
        assert r.bars[-1].occupancy == 100.0 and r.peak_index == 5

    def test_off_days_do_not_sample(self):
        r = occupancy._report_peak_by_hour(_base(MON, 7, {(4, 9): 10}, off_days=(4, 5)), 24)
        assert r.bars[0].days_sampled == 5 and r.bars[0].occupancy == 0.0


# ── 2. the endpoints, against the database in .env ───────────────────────────

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)   # no `with`: background jobs are not started


@pytest.fixture(scope="module")
def month():
    """The last 31 whole days that have slot_status data."""
    s = SessionLocal()
    try:
        last = scalar(s, "SELECT CAST(MAX(time) AS DATE) FROM slot_status")
        if last is None:
            pytest.skip("no slot_status data")
        first = last - timedelta(days=30)
        return (datetime.combine(first, datetime.min.time()),
                datetime.combine(last + timedelta(days=1), datetime.min.time()))
    finally:
        s.close()


def _q(rng, extra=""):
    return f"start_time={rng[0].isoformat()}&end_time={rng[1].isoformat()}{extra}"


@pytest.fixture(scope="module", params=["", "&business_hours=false", "&hour_from=9&hour_to=16"],
                ids=["saved-window", "24h", "9-16"])
def window(request):
    return request.param


class TestKpisEndpoint:
    def test_shape(self, client, month, window):
        r = client.get(f"{KPIS}?{_q(month, window)}")
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["peak_hour"] is not None, "the month has parking; expected a peak"
        assert 0 < j["peak_hour_days"] <= j["days_counted"] <= 31
        assert set(j) >= {"peak_hour", "max_occupancy", "peak_day", "peak_hour_entries"}
        assert not set(j) & {"votes", "days", "bars", "items"}, "KPIs only — charts have their own endpoints"

    def test_vote_agrees_with_hourly_trend(self, client, month, window):
        """Recompute the vote from /history/trend?grain=hour (a different code
        path) and get the same Peak Hour, days and voters."""
        k = client.get(f"{KPIS}?{_q(month, window)}").json()
        trend = client.get(f"/occupancy/history/trend?{_q(month, window)}&grain=hour").json()["points"]
        by_day: dict = {}
        for p in trend:
            by_day.setdefault(p["bucket_start"][:10], []).append(p)
        peaks = {}
        for d, pts in by_day.items():
            if any(p["occupancy"] for p in pts):
                best = max(pts, key=lambda p: p["occupancy"])
                peaks[d] = int(best["bucket_start"][11:13])
        tally = Counter(peaks.values())
        top = max(tally.values())
        assert k["days_counted"] == len(peaks)
        assert k["peak_hour_days"] == top
        assert tally[k["peak_hour"]] == top
        assert k["max_occupancy"] == max(p["occupancy"] for p in trend if p["occupancy"] is not None)

    def test_peak_day_agrees_with_daily_trend(self, client, month, window):
        k = client.get(f"{KPIS}?{_q(month, window)}").json()
        daily = {p["bucket_start"][:10]: p["occupancy"] for p in
                 client.get(f"/occupancy/history/trend?{_q(month, window)}&grain=day").json()["points"]}
        assert k["peak_day_occupancy"] == daily[k["peak_day"]] == max(v for v in daily.values() if v is not None)

    def test_entries_agree_with_entry_exit_peak_hours(self, client, month):
        k = client.get(f"{KPIS}?{_q(month, '&business_hours=false')}").json()
        ee = client.get(f"/entry-exit/peak-hours?date_from={month[0].date()}"
                        f"&date_to={(month[1] - timedelta(days=1)).date()}").json()
        assert k["peak_hour_entries"] == ee["items"][k["peak_hour"]]["entries"]

    def test_entries_agree_with_sql(self, client, month, window):
        k = client.get(f"{KPIS}?{_q(month, window)}").json()
        if len(k["business_days"]) != 7:
            pytest.skip("saved window excludes weekdays; the SQL below counts every day")
        s = SessionLocal()
        try:
            total = scalar(s, """
                SELECT COUNT(*) FROM parking_sessions
                WHERE entry_time >= :a AND entry_time < :b AND DATEPART(HOUR, entry_time) = :h""",
                {"a": month[0], "b": month[1], "h": k["peak_hour"]})
        finally:
            s.close()
        assert k["peak_hour_entries"] == total

    def test_max_equals_occupancy_tab_peak_on_24h(self, client, month):
        q = _q(month, "&business_hours=false")
        k = client.get(f"{KPIS}?{q}").json()
        tab1 = client.get(f"/occupancy/history/kpis?{q}").json()
        assert (k["max_occupancy"], k["max_occupancy_at"]) == (tab1["peak_occupancy"], tab1["peak_occupancy_at"])

    def test_window_echo(self, client, month):
        k = client.get(f"{KPIS}?{_q(month, '&hour_from=9&hour_to=16')}").json()
        assert (k["business_hours_applied"], k["business_hour_from"], k["business_hour_to"]) == (True, 9, 16)
        assert 9 <= k["peak_hour"] < 16


class TestByFloorEndpoint:
    def test_matches_by_location_and_shares_sum(self, client, month, window):
        pie = client.get(f"{BY_FLOOR}?{_q(month, window)}")
        assert pie.status_code == 200, pie.text
        items = pie.json()["items"]
        loc = client.get(f"/occupancy/history/by-location?{_q(month, window)}").json()["items"]
        assert [(i["floor"], i["label"], i["capacity"], i["avg_occupancy"]) for i in items] == \
            [(i["floor"], i["label"], i["capacity"], i["utilization"]) for i in loc]
        assert abs(sum(i["occupied_share_pct"] for i in items) - 100) <= 0.2

    def test_shares_follow_capacity_times_average(self, client, month, window):
        items = client.get(f"{BY_FLOOR}?{_q(month, window)}").json()["items"]
        weight = {i["floor"]: i["capacity"] * i["avg_occupancy"] for i in items}
        total = sum(weight.values())
        for i in items:
            assert abs(i["occupied_share_pct"] - weight[i["floor"]] / total * 100) < 0.3, i


class TestByHourEndpoint:
    def test_default_step_is_two_hours(self, client, month):
        j = client.get(f"{BY_HOUR}?{_q(month, '&business_hours=false')}").json()
        assert j["step_hours"] == 2 and len(j["bars"]) == 12
        assert [b["label"] for b in j["bars"]][:4] == ["12:00 AM", "2:00 AM", "4:00 AM", "6:00 AM"]

    def test_bars_pool_the_heatmap_weekdays(self, client, month, window):
        """Each bar = mean over every day; the heatmap row = the same days split
        by weekday, so bar == days-weighted mean of the row's 7 cells."""
        bars = client.get(f"{BY_HOUR}?{_q(month, window)}&step_hours=2").json()["bars"]
        hm = client.get(f"/occupancy/history/heatmap?{_q(month, window)}&block_hours=2").json()
        assert [(b["hour_from"], b["hour_to"]) for b in bars] == [(r["hour_from"], r["hour_to"]) for r in hm["rows"]]
        for b in bars:
            cells = [c for c in hm["cells"] if c["row_index"] == b["index"] and c["occupancy"] is not None]
            assert b["days_sampled"] == sum(c["days_sampled"] for c in cells)
            if cells:
                pooled = sum(c["occupancy"] * c["days_sampled"] for c in cells) / b["days_sampled"]
                assert abs(b["occupancy"] - pooled) <= 0.1, (b, pooled)

    def test_peak_index_is_highest_bar(self, client, month, window):
        j = client.get(f"{BY_HOUR}?{_q(month, window)}").json()
        measured = [b for b in j["bars"] if b["occupancy"] is not None]
        assert j["bars"][j["peak_index"]]["occupancy"] == max(b["occupancy"] for b in measured)


class TestAllThree:
    @pytest.mark.parametrize("path", [KPIS, BY_FLOOR, BY_HOUR])
    def test_same_json_with_and_without_stored_table(self, client, month, window, path, monkeypatch):
        url = f"{path}?{_q(month, window)}"
        stored = client.get(url).json()
        monkeypatch.setattr(occupancy, "_stored_days", lambda *a, **k: {})
        assert client.get(url).json() == stored

    @pytest.mark.parametrize("path", [KPIS, BY_FLOOR, BY_HOUR])
    def test_default_range_is_last_24h(self, client, path):
        assert client.get(path).status_code == 200

    @pytest.mark.parametrize("path", [KPIS, BY_FLOOR, BY_HOUR])
    @pytest.mark.parametrize("qs", [
        "start_time=2026-07-10T00:00:00&end_time=2026-07-09T00:00:00",
        "start_time=2026-07-10T00:00:00",
        "start_time=2026-07-01T00:00:00&end_time=2026-07-02T00:00:00&hour_from=18&hour_to=9",
    ], ids=["reversed", "half-range", "bad-window"])
    def test_bad_input_400(self, client, path, qs):
        assert client.get(f"{path}?{qs}").status_code == 400

    def test_bad_step_422(self, client):
        assert client.get(f"{BY_HOUR}?step_hours=0").status_code == 422

    def test_old_merged_path_is_gone(self, client):
        assert client.get("/occupancy/history/peak").status_code in (404, 405)
