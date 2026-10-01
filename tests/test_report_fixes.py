"""Fixes to four report endpoints, and the overstay report's new path.

  /occupancy/history/trend   no range -> all 24 hours by default (the Dashboard's
                             "Last 24 Hours" line); the saved window still applies
                             with a range or when asked for.
  /occupancy/history/kpis    peak_occupancy counts only hours inside the reporting
                             window, like Overall Utilization and Maximum Occupancy.
  /alerts/summary            resolved=all: every alert in the range in one call.
  /alerts/stats              previous{} for the equally long period before the range.
  /alerts/reports/overstay-violations   moved from /reports/overstay-violations.

Runs against the database in .env. Read-only.

    pytest tests/test_report_fixes.py -v -p no:cacheprovider
"""
import os
import sys
from datetime import date, datetime, timedelta

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.routers import occupancy  # noqa: E402
from app.services.report_settings import DayRule  # noqa: E402

RANGE = {"date_from": "2026-07-05", "date_to": "2026-08-04"}
MONTH = {"start_time": "2026-07-05T00:00:00", "end_time": "2026-08-05T00:00:00"}


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


# ── /occupancy/history/trend ─────────────────────────────────────────────────

class TestTrendDefault:
    def test_no_range_is_24_hours(self, client):
        j = client.get("/occupancy/history/trend").json()
        assert j["business_hours_applied"] is False
        assert j["grain"] == "hour" and len(j["points"]) == 24

    def test_window_on_request(self, client):
        j = client.get("/occupancy/history/trend", params={"business_hours": "true"}).json()
        assert j["business_hours_applied"] is True and len(j["points"]) < 24

    def test_hour_override_still_applies(self, client):
        j = client.get("/occupancy/history/trend", params={"hour_from": 9, "hour_to": 12}).json()
        assert (j["business_hours_applied"], j["business_hour_from"], j["business_hour_to"]) == (True, 9, 12)
        assert len(j["points"]) <= 3

    def test_range_keeps_saved_window(self, client):
        saved = client.get("/settings/report").json()
        j = client.get("/occupancy/history/trend", params=MONTH).json()
        assert j["business_hours_applied"] is saved["business_hours_enabled"]
        assert j["grain"] == "weekday" and len(j["points"]) == 7

    def test_other_widgets_default_unchanged(self, client):
        saved = client.get("/settings/report").json()
        assert client.get("/occupancy/history/kpis").json()["business_hours_applied"] is saved["business_hours_enabled"]

    def test_half_range_400(self, client):
        assert client.get("/occupancy/history/trend", params={"start_time": MONTH["start_time"]}).status_code == 400


# ── /occupancy/history/kpis peak ─────────────────────────────────────────────

def _base(occ: dict, h_from=0, h_to=24, days=1, cap=10):
    """Synthetic _ReportBase from MON 00:00: occ maps (day, hour) -> occupied slots."""
    start = datetime(2026, 7, 6)
    base = occupancy._ReportBase(
        start_time=start, end_time=start + timedelta(days=days),
        capacity_by_floor={"G": cap}, total_capacity=cap,
        buckets=[{"floor": "G", "bucket_start": start + timedelta(days=d, hours=h),
                  "total_occupied_seconds": n * 3600} for (d, h), n in sorted(occ.items())],
        applied=(h_from, h_to) != (0, 24), h_from=h_from, h_to=h_to, days=frozenset(range(7)),
        day_rules={(start + timedelta(days=d)).date(): DayRule(True, h_from, h_to) for d in range(days)},
        offered_seconds=0.0, day_offered={},
    )
    cursor = start
    while cursor < base.end_time:
        base.offered_seconds += base.counted_span(cursor)
        cursor += timedelta(hours=1)
    return base


class TestKpisPeak:
    def test_hour_outside_window_is_not_the_peak(self):
        # 20:00 is full, but the window is 07-18: the peak is 11:00 at 40%.
        k = occupancy._report_kpis(_base({(0, 20): 10, (0, 11): 4}, h_from=7, h_to=18))
        assert (k.peak_occupancy, k.peak_occupancy_at.hour) == (40.0, 11)

    def test_24h_still_sees_every_hour(self):
        k = occupancy._report_kpis(_base({(0, 20): 10, (0, 11): 4}))
        assert (k.peak_occupancy, k.peak_occupancy_at.hour) == (100.0, 20)

    def test_nothing_counted_is_zero(self):
        k = occupancy._report_kpis(_base({(0, 20): 10}, h_from=7, h_to=18))
        assert (k.peak_occupancy, k.peak_occupancy_at) == (0.0, None)

    @pytest.mark.parametrize("extra", [{}, {"business_hours": "false"}, {"hour_from": 9, "hour_to": 16}],
                             ids=["saved-window", "24h", "9-16"])
    def test_matches_peak_hours_max_occupancy(self, client, extra):
        """Occupancy tab Peak Occupancy = Peak Hours tab Maximum Occupancy, any window."""
        q = {**MONTH, **extra}
        k = client.get("/occupancy/history/kpis", params=q).json()
        p = client.get("/occupancy/history/peak-hours/kpis", params=q).json()
        assert (k["peak_occupancy"], k["peak_occupancy_at"]) == (p["max_occupancy"], p["max_occupancy_at"])
        if "hour_from" in extra:
            assert 9 <= int(k["peak_occupancy_at"][11:13]) < 16


# ── /alerts/summary resolved=all ─────────────────────────────────────────────

class TestSummaryAll:
    @pytest.mark.parametrize("rng", [{}, RANGE], ids=["all-time", "range"])
    def test_all_equals_stats_total(self, client, rng):
        s = client.get("/alerts/summary", params={**rng, "resolved": "all"}).json()
        st = client.get("/alerts/stats", params=rng).json()
        assert s["total"] == st["total_alerts"] == sum(t["count"] for t in s["by_type"])

    def test_all_is_active_plus_resolved_per_type(self, client):
        def counts(r):
            return {t["alert_type"]: t["count"] for t in
                    client.get("/alerts/summary", params={**RANGE, "resolved": r}).json()["by_type"]}
        a, f, t = counts("all"), counts("false"), counts("true")
        assert a == {k: f.get(k, 0) + t.get(k, 0) for k in a}

    def test_default_still_active_only(self, client):
        assert client.get("/alerts/summary").json()["total"] == client.get("/alerts/stats").json()["active_alerts"]

    def test_all_combines_with_filters(self, client):
        s = client.get("/alerts/summary", params={**RANGE, "resolved": "all", "severity": "critical"}).json()
        assert s["total"] == client.get("/alerts/", params={**RANGE, "severity": "critical", "page_size": 1}).json()["total_count"]

    def test_bad_value_422(self, client):
        assert client.get("/alerts/summary", params={"resolved": "maybe"}).status_code == 422

    def test_no_placeholder_labels(self, client):
        names = [t["display_name"] for t in client.get("/alerts/summary", params={"resolved": "all"}).json()["by_type"]]
        assert all(n and n.lower() != "string" for n in names), names


# ── /alerts/stats previous ───────────────────────────────────────────────────

class TestStatsPrevious:
    def test_previous_is_the_period_before(self, client):
        st = client.get("/alerts/stats", params=RANGE).json()
        assert (st["previous_from"], st["previous_to"]) == ("2026-06-04", "2026-07-04")
        before = client.get("/alerts/stats", params={"date_from": "2026-06-04", "date_to": "2026-07-04"}).json()
        assert st["previous"] == {k: before[k] for k in
                                  ("total_alerts", "critical_alerts", "high_alerts", "resolved_total", "active_alerts")}

    def test_one_day_compares_with_yesterday(self, client):
        st = client.get("/alerts/stats", params={"date_from": "2026-08-04", "date_to": "2026-08-04"}).json()
        assert (st["previous_from"], st["previous_to"]) == ("2026-08-03", "2026-08-03")
        y = client.get("/alerts/", params={"date_from": "2026-08-03", "date_to": "2026-08-03", "page_size": 1}).json()
        assert st["previous"]["total_alerts"] == y["total_count"]

    @pytest.mark.parametrize("rng", [{}, {"date_from": "2026-08-01"}], ids=["all-time", "open-ended"])
    def test_no_previous_without_both_dates(self, client, rng):
        st = client.get("/alerts/stats", params=rng).json()
        assert st["previous"] is None and st["previous_from"] is None

    def test_current_numbers_unchanged(self, client):
        st = client.get("/alerts/stats", params=RANGE).json()
        assert st["total_alerts"] == client.get("/alerts/", params={**RANGE, "page_size": 1}).json()["total_count"]


# ── the report's new path ────────────────────────────────────────────────────

class TestOverstayReportPath:
    def test_new_path(self, client):
        r = client.get("/alerts/reports/overstay-violations/kpis", params=RANGE)
        assert r.status_code == 200
        j = r.json()
        assert j["total_violations"] == j["overstays"] + j["no_parking"] + j["other"]
        rows = client.get("/alerts/reports/overstay-violations", params=RANGE).json()
        assert rows["total_count"] == j["total_violations"]

    def test_old_path_gone(self, client):
        assert client.get("/reports/overstay-violations", params=RANGE).status_code == 404

    def test_not_swallowed_by_alert_id_route(self, client):
        # /alerts/{alert_id} must not catch it (it would 422 on a non-int id).
        assert client.get("/alerts/reports/overstay-violations").status_code == 200
        assert client.get("/alerts/reports/overstay-violations/kpis").status_code == 200
