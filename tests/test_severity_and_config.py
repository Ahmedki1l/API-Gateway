"""Review fixes 1-3.

1+2. Old-scale severities. PMS-AI and VideoAnalytics still WRITE critical /
     warning / info (migrator 0013). The Gateway reads those as the type's
     configured severity in dbo.alert_types (fixed warning->medium, info->low
     only for an unconfigured type), and uses that ONE value for the badge,
     the ?severity= filter, the cards, the donut, the sort and the CSV.
3.   A bad REPORT_BUSINESS_* value warns and falls back — it never stops the
     Gateway from booting.

Inserts marker alerts on an empty past day and deletes exactly those ids
afterwards (never by pattern).

    pytest tests/test_severity_and_config.py -v -p no:cacheprovider
"""
import csv
import io
import os
import sys

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, rows, scalar  # noqa: E402

DAY = "2025-05-14"
RANGE = {"date_from": DAY, "date_to": DAY}

# alert_type, stored severity, the level the Gateway must read it as.
# Configured in dbo.alert_types: vehicle_violation / unknown_vehicle critical,
# vehicle_intrusion high, capacity_exceeded / silent_entry medium. `intrusion`
# has no row there.
ALERTS = [
    ("vehicle_violation", "info",     "critical"),   # the 382-row case 0013 was written for
    ("vehicle_intrusion", "critical", "high"),       # old-scale critical of a high type
    ("unknown_vehicle",   "warning",  "critical"),
    ("capacity_exceeded", "warning",  "medium"),
    ("silent_entry",      "info",     "medium"),
    ("vehicle_intrusion", "high",     "high"),       # new scale: kept
    ("capacity_exceeded", "low",      "low"),        # new scale, below the type's level: kept
    ("intrusion",         "info",     "low"),        # unconfigured: fixed map
    ("intrusion",         "warning",  "medium"),
    ("intrusion",         "critical", "critical"),
]
EXPECTED = {lvl: sum(1 for *_, e in ALERTS if e == lvl) for lvl in ("critical", "high", "medium", "low")}

_ids: list[int] = []


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def data():
    db = SessionLocal()
    configured = {r["alert_type"]: r["severity"] for r in rows(db, "SELECT alert_type, severity FROM dbo.alert_types")}
    want = {"vehicle_violation": "critical", "unknown_vehicle": "critical", "vehicle_intrusion": "high",
            "capacity_exceeded": "medium", "silent_entry": "medium"}
    if any(configured.get(k) != v for k, v in want.items()) or "intrusion" in configured:
        db.close()
        pytest.skip(f"dbo.alert_types differs from what the cases assume: {configured}")
    if scalar(db, "SELECT COUNT(*) FROM alerts WHERE CAST(triggered_at AS DATE) = :d", {"d": DAY}):
        db.close()
        pytest.skip(f"alerts already has rows on {DAY}")
    try:
        for i, (atype, sev, _) in enumerate(ALERTS):
            _ids.append(db.execute(text("""
                INSERT INTO alerts (alert_type, camera_id, plate_number, triggered_at, is_resolved, severity, is_test)
                OUTPUT INSERTED.id
                VALUES (:a, 'CAM-TEST', :p, :t, 0, :s, 0)
            """), {"a": atype, "p": f"TSEV-{i:02d}", "t": f"{DAY} 10:{i:02d}:00", "s": sev}).scalar())
        db.commit()
        yield
    finally:
        db.rollback()
        if _ids:
            db.execute(text(f"DELETE FROM alerts WHERE id IN ({', '.join(map(str, _ids))})"))
            db.commit()
        db.close()


def _listed(client, **params):
    r = client.get("/alerts/", params={**RANGE, "page_size": 100, **params})
    assert r.status_code == 200, r.text
    return r.json()


class TestReadAsConfiguredLevel:
    def test_each_row_shows_its_level(self, client):
        by_id = {a["id"]: a["severity"] for a in _listed(client)["items"]}
        assert [by_id[i] for i in _ids] == [e for *_, e in ALERTS]

    @pytest.mark.parametrize("level", ["critical", "high", "medium", "low"])
    def test_filter_finds_old_scale_rows(self, client, level):
        got = _listed(client, severity=level)
        assert got["total_count"] == EXPECTED[level]
        assert all(a["severity"] == level for a in got["items"])

    @pytest.mark.parametrize("legacy,level", [("warning", "medium"), ("info", "low")])
    def test_old_filter_values_still_work(self, client, legacy, level):
        assert _listed(client, severity=legacy)["total_count"] == EXPECTED[level]

    def test_cards_and_donut_match_the_filter(self, client):
        st = client.get("/alerts/stats", params=RANGE).json()
        bp = {i["severity"]: i["count"] for i in client.get("/alerts/by-priority", params=RANGE).json()["items"]}
        assert (st["total_alerts"], st["critical_alerts"], st["high_alerts"]) == \
            (len(ALERTS), EXPECTED["critical"], EXPECTED["high"])
        assert bp == EXPECTED
        for level, n in bp.items():
            assert _listed(client, severity=level)["total_count"] == n, level

    def test_severity_sort_uses_the_same_level(self, client):
        items = _listed(client, sort_by="severity", sort_dir="desc")["items"]
        rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        ranks = [rank[a["severity"]] for a in items]
        assert ranks == sorted(ranks, reverse=True)

    def test_csv_shows_the_same_level(self, client):
        for params in ({}, {"sort_by": "triggered_at"}):
            r = client.get("/alerts/export/csv", params={**RANGE, **params})
            got = {int(row["ID"]): row["Severity"] for row in csv.DictReader(io.StringIO(r.text.lstrip("﻿")))}
            assert [got[i] for i in _ids] == [e for *_, e in ALERTS], params

    def test_summary_counts_by_type(self, client):
        s = {t["alert_type"]: t["count"] for t in
             client.get("/alerts/summary", params={**RANGE, "resolved": "all"}).json()["by_type"]}
        assert s["vehicle_intrusion"] == 2 and s["capacity_exceeded"] == 2
        crit = client.get("/alerts/summary", params={**RANGE, "resolved": "all", "severity": "critical"}).json()
        assert crit["total"] == EXPECTED["critical"]

    def test_fixed_map_without_alert_types_table(self):
        """A DB before migrator 0010: old values fall back to warning->medium,
        info->low, critical stays; new-scale values are kept."""
        from app.routers.alerts import _stored_severity_expr
        db = SessionLocal()
        try:
            got = {r["id"]: r["s"] for r in rows(db, f"""
                SELECT a.id, {_stored_severity_expr({"alert_types_table": False})} AS s
                FROM alerts a WHERE a.id IN ({', '.join(map(str, _ids))})""")}
        finally:
            db.close()
        fixed = {"info": "low", "warning": "medium", "critical": "critical",
                 "high": "high", "medium": "medium", "low": "low"}
        assert [got[i] for i in _ids] == [fixed[s] for _, s, _ in ALERTS]


# ── 3. REPORT_BUSINESS_* never stop the Gateway ──────────────────────────────

_KEYS = ("REPORT_BUSINESS_HOURS_ENABLED", "REPORT_BUSINESS_HOUR_FROM",
         "REPORT_BUSINESS_HOUR_TO", "REPORT_BUSINESS_DAYS")


def _settings(monkeypatch, **env):
    from app.config import Settings
    for k in _KEYS:
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    # Required secrets unrelated to these checks.
    monkeypatch.setenv("CAMERAS_ENCRYPTION_KEY", os.environ.get("CAMERAS_ENCRYPTION_KEY", "test-key"))
    monkeypatch.setenv("CAMERAS_INTERNAL_TOKEN", os.environ.get("CAMERAS_INTERNAL_TOKEN", "test-token"))
    # _env_file=None: only the variables set here, not the developer's .env.
    return Settings(_env_file=None)


class TestReportSettingsDegrade:
    @pytest.mark.parametrize("env,expected", [
        ({"REPORT_BUSINESS_HOUR_FROM": "18", "REPORT_BUSINESS_HOUR_TO": "7"}, (True, 7, 18)),
        ({"REPORT_BUSINESS_HOUR_FROM": "24"}, (True, 7, 18)),
        ({"REPORT_BUSINESS_HOUR_TO": "0"}, (True, 7, 18)),
        ({"REPORT_BUSINESS_HOUR_TO": "25"}, (True, 7, 18)),
        ({"REPORT_BUSINESS_HOUR_FROM": "abc"}, (True, 7, 18)),
        ({"REPORT_BUSINESS_HOURS_ENABLED": "maybe"}, (True, 7, 18)),
    ], ids=["from>=to", "from=24", "to=0", "to=25", "not-a-number", "bad-bool"])
    def test_bad_value_falls_back(self, monkeypatch, capsys, env, expected):
        s = _settings(monkeypatch, **env)
        assert (s.report_business_hours_enabled, s.report_business_hour_from, s.report_business_hour_to) == expected
        assert "[config] invalid" in capsys.readouterr().out

    def test_bad_days_fall_back_to_all_week(self, monkeypatch, capsys):
        s = _settings(monkeypatch, REPORT_BUSINESS_DAYS="Sunday,Xyz")
        assert s.business_weekdays == frozenset(range(7))
        assert "REPORT_BUSINESS_DAYS" in capsys.readouterr().out

    @pytest.mark.parametrize("env,expected", [
        ({"REPORT_BUSINESS_HOUR_FROM": "9", "REPORT_BUSINESS_HOUR_TO": "24"}, (True, 9, 24)),
        ({"REPORT_BUSINESS_HOUR_FROM": "0", "REPORT_BUSINESS_HOUR_TO": "1"}, (True, 0, 1)),
        ({"REPORT_BUSINESS_HOURS_ENABLED": "false"}, (False, 7, 18)),
    ], ids=["to=24", "0-1", "disabled"])
    def test_valid_values_kept(self, monkeypatch, capsys, env, expected):
        s = _settings(monkeypatch, **env)
        assert (s.report_business_hours_enabled, s.report_business_hour_from, s.report_business_hour_to) == expected
        assert "[config] invalid" not in capsys.readouterr().out

    def test_valid_days_kept(self, monkeypatch):
        s = _settings(monkeypatch, REPORT_BUSINESS_DAYS="Sun,Mon,Tue,Wed,Thu")
        assert s.business_weekdays == frozenset({6, 0, 1, 2, 3})
