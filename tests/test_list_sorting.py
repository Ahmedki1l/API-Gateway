"""Server-side sorting on GET /entry-exit/ and GET /vehicles/ (+ their CSVs).

`sort_by` + `sort_dir` apply BEFORE paging, so every page is a slice of one
globally sorted list. Each test walks every page and checks, from the response
fields the table actually renders:
  * the rows are in order (empty values last in both directions);
  * no row is repeated or lost across page boundaries (stable paging).

Runs against the database in .env. Read-only.

    pytest tests/test_list_sorting.py -v -p no:cacheprovider
"""
import csv
import io
import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# A month with ~600 visits: several pages, fast enough to walk for every key.
RANGE = {"date_from": "2026-07-05", "date_to": "2026-08-04"}
PAGE = 100


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _walk(client, path, **params):
    """Every item of a paged list, in page order."""
    items, page = [], 1
    while True:
        r = client.get(path, params={**params, "page": page, "page_size": PAGE})
        assert r.status_code == 200, r.text
        j = r.json()
        items += j["items"]
        if page * PAGE >= j["total_count"]:
            assert len(items) == j["total_count"]
            return items
        page += 1


def _display_plate(p: str) -> str:
    """How the frontend shows a stored plate: NJS-7894 -> 7894-NJS."""
    if "-" in p:
        a, b = p.split("-", 1)
        return f"{b}-{a}"
    return p


def _ts(s):
    return datetime.fromisoformat(s) if s else None


def _txt(s):
    return s.casefold() if s else None


def _assert_sorted(keys, direction, label):
    """Non-empty keys monotonic in `direction`, then every empty key."""
    present = [k for k in keys if k is not None]
    first_empty = next((i for i, k in enumerate(keys) if k is None), len(keys))
    assert all(k is None for k in keys[first_empty:]), f"{label}: empty values not last"
    want = sorted(present, reverse=(direction == "desc"))
    assert present == want, f"{label}: out of order at " + str(
        next(i for i, (a, b) in enumerate(zip(present, want)) if a != b))


# ── /entry-exit/ ─────────────────────────────────────────────────────────────

def _ee_time(i):
    return _ts((i["exit"] or {}).get("event_time") or i["entry"]["event_time"])


ENTRY_EXIT_KEYS = {
    "time": _ee_time,
    "entry_time": lambda i: _ts(i["entry"]["event_time"]),
    "exit_time": lambda i: _ts((i["exit"] or {}).get("event_time")),
    "type": lambda i: 1 if i["exit"] else 0,
    "plate": lambda i: _txt(_display_plate(i["plate_number"])),
    "floor": lambda i: _txt(i["floor"]),
    "gate": lambda i: _txt((i["exit"] or {}).get("camera_id") or i["entry"]["camera_id"]),
    "duration": lambda i: i["duration_seconds"],
}


@pytest.fixture(scope="module")
def ee_ids(client):
    return sorted(i["id"] for i in _walk(client, "/entry-exit/", **RANGE))


class TestEntryExitSort:
    @pytest.mark.parametrize("direction", ["asc", "desc"])
    @pytest.mark.parametrize("key", list(ENTRY_EXIT_KEYS))
    def test_sorted_across_pages(self, client, ee_ids, key, direction):
        items = _walk(client, "/entry-exit/", **RANGE, sort_by=key, sort_dir=direction)
        assert sorted(i["id"] for i in items) == ee_ids, "rows repeated or lost across pages"
        _assert_sorted([ENTRY_EXIT_KEYS[key](i) for i in items], direction, key)

    def test_ties_broken_by_id(self, client):
        # Many visits share a floor: inside one floor the id must run the same way.
        items = _walk(client, "/entry-exit/", **RANGE, sort_by="floor", sort_dir="asc")
        for f in {i["floor"] for i in items}:
            ids = [i["id"] for i in items if i["floor"] == f]
            assert ids == sorted(ids), f

    def test_default_order_unchanged(self, client):
        items = _walk(client, "/entry-exit/", **RANGE)
        _assert_sorted([_ts(i["entry"]["event_time"]) for i in items], "desc", "default")

    def test_sort_dir_alone_is_ignored(self, client):
        a = client.get("/entry-exit/", params={**RANGE, "page_size": 50}).json()["items"]
        b = client.get("/entry-exit/", params={**RANGE, "page_size": 50, "sort_dir": "asc"}).json()["items"]
        assert [i["id"] for i in a] == [i["id"] for i in b]

    def test_sort_combines_with_filters(self, client):
        items = _walk(client, "/entry-exit/", **RANGE, status="closed", sort_by="duration", sort_dir="asc")
        assert items and all(i["status"] == "closed" for i in items)
        _assert_sorted([i["duration_seconds"] for i in items], "asc", "closed by duration")

    def test_open_visits_sort_by_live_duration(self, client):
        items = _walk(client, "/entry-exit/", sort_by="duration", sort_dir="desc")
        open_ = [i for i in items if i["status"] == "open"]
        if not open_:
            pytest.skip("no open visits in the DB")
        # Open for weeks, so they outlast every closed stay.
        assert items[0]["status"] == "open"

    @pytest.mark.parametrize("bad", [{"sort_by": "entry_time; DROP TABLE x"}, {"sort_by": "owner"},
                                     {"sort_by": "time", "sort_dir": "up"}])
    def test_unknown_values_rejected(self, client, bad):
        assert client.get("/entry-exit/", params=bad).status_code == 422

    def test_csv_follows_sort(self, client):
        params = {**RANGE, "sort_by": "plate", "sort_dir": "asc"}
        listed = [i["plate_number"] for i in _walk(client, "/entry-exit/", **params)]
        r = client.get("/entry-exit/export/csv", params=params)
        assert r.status_code == 200
        exported = [row["Plate Number"] for row in csv.DictReader(io.StringIO(r.text.lstrip("﻿")))]
        assert exported == listed


# ── /vehicles/ ───────────────────────────────────────────────────────────────

VEHICLE_KEYS = {
    "plate": lambda v: _txt(_display_plate(v["plate_number"])),
    "owner": lambda v: _txt((v["owner_name"] or "").strip()) if v["is_registered"] else None,
    "vehicle_type": lambda v: None if v["vehicle_type"] in (None, "unknown") else _txt(v["vehicle_type"]),
    "floor": lambda v: _txt(v["floor"]),
    "status": lambda v: 0 if v["is_registered"] else 1,
    "registered_at": lambda v: _ts(v["registered_at"]),
    "parked_at": lambda v: _ts(v["parked_at"]),
}


@pytest.fixture(scope="module")
def vehicle_ids(client):
    return sorted(v["id"] for v in _walk(client, "/vehicles/"))


class TestVehicleSort:
    @pytest.mark.parametrize("direction", ["asc", "desc"])
    @pytest.mark.parametrize("key", list(VEHICLE_KEYS))
    def test_sorted_across_pages(self, client, vehicle_ids, key, direction, monkeypatch):
        monkeypatch.setattr(sys.modules[__name__], "PAGE", 25)   # ~100 plates -> 4 pages
        items = _walk(client, "/vehicles/", sort_by=key, sort_dir=direction)
        assert sorted(v["id"] for v in items) == vehicle_ids, "rows repeated or lost across pages"
        _assert_sorted([VEHICLE_KEYS[key](v) for v in items], direction, key)

    def test_owner_puts_unregistered_last_both_ways(self, client):
        for d in ("asc", "desc"):
            items = _walk(client, "/vehicles/", sort_by="owner", sort_dir=d)
            regs = [v["is_registered"] for v in items]
            assert regs == sorted(regs, reverse=True), d

    def test_sort_combines_with_filters(self, client):
        items = _walk(client, "/vehicles/", is_employee="true", sort_by="plate", sort_dir="asc")
        assert items and all(v["is_employee"] for v in items)
        _assert_sorted([VEHICLE_KEYS["plate"](v) for v in items], "asc", "employees by plate")

    def test_default_order_unchanged(self, client):
        items = _walk(client, "/vehicles/")
        parked = [v["parked_at"] is not None for v in items]
        assert parked == sorted(parked, reverse=True), "parked cars no longer first"

    @pytest.mark.parametrize("bad", [{"sort_by": "plate_number"}, {"sort_by": "plate", "sort_dir": "down"}])
    def test_unknown_values_rejected(self, client, bad):
        assert client.get("/vehicles/", params=bad).status_code == 422

    def test_csv_follows_sort(self, client):
        params = {"sort_by": "plate", "sort_dir": "desc"}
        listed = [v["plate_number"] for v in _walk(client, "/vehicles/", **params)]
        r = client.get("/vehicles/export/csv", params=params)
        assert r.status_code == 200
        exported = [row["Plate Number"] for row in csv.DictReader(io.StringIO(r.text.lstrip("﻿")))]
        assert exported == listed


# ── /alerts/ ─────────────────────────────────────────────────────────────────

# 519 alerts: 28 active, 53 with a plate, 6 types, 3 severities.
ALERT_RANGE = {"date_from": "2026-07-26", "date_to": "2026-07-28"}
_RANK = {"critical": 4, "high": 3, "medium": 2, "warning": 2, "low": 1, "info": 1}

ALERT_KEYS = {
    "triggered_at": lambda a: _ts(a["triggered_at"]),
    "resolved_at": lambda a: _ts(a["resolved_at"]),
    "type": lambda a: _txt(a["alert_type"]),
    "plate": lambda a: _txt(_display_plate(a["plate_number"])) if a["plate_number"] else None,
    "location": lambda a: _txt(a["floor"] or a["location"]),
    "severity": lambda a: _RANK.get(a["severity"]),
    "status": lambda a: 1 if a["is_resolved"] else 0,
}


@pytest.fixture(scope="module")
def alert_ids(client):
    return sorted(a["id"] for a in _walk(client, "/alerts/", **ALERT_RANGE))


class TestAlertSort:
    @pytest.mark.parametrize("direction", ["asc", "desc"])
    @pytest.mark.parametrize("key", list(ALERT_KEYS))
    def test_sorted_across_pages(self, client, alert_ids, key, direction):
        items = _walk(client, "/alerts/", **ALERT_RANGE, sort_by=key, sort_dir=direction)
        assert sorted(a["id"] for a in items) == alert_ids, "rows repeated or lost across pages"
        _assert_sorted([ALERT_KEYS[key](a) for a in items], direction, key)

    def test_severity_desc_is_critical_first(self, client):
        items = _walk(client, "/alerts/", **ALERT_RANGE, sort_by="severity", sort_dir="desc")
        assert items[0]["severity"] == "critical"
        assert _RANK[items[-1]["severity"]] == min(_RANK[a["severity"]] for a in items)

    def test_status_asc_is_active_first(self, client):
        items = _walk(client, "/alerts/", **ALERT_RANGE, sort_by="status", sort_dir="asc")
        flags = [a["is_resolved"] for a in items]
        assert flags == sorted(flags) and not flags[0] and flags[-1]

    def test_sort_by_overrides_legacy_sort(self, client):
        a = client.get("/alerts/", params={**ALERT_RANGE, "sort": "resolved_at",
                                            "sort_by": "plate", "sort_dir": "asc", "page_size": 100}).json()["items"]
        b = client.get("/alerts/", params={**ALERT_RANGE, "sort_by": "plate", "sort_dir": "asc",
                                            "page_size": 100}).json()["items"]
        assert [x["id"] for x in a] == [x["id"] for x in b]

    def test_legacy_sort_unchanged(self, client):
        items = _walk(client, "/alerts/", **ALERT_RANGE, resolved="true", sort="resolved_at")
        _assert_sorted([_ts(a["resolved_at"]) for a in items], "desc", "sort=resolved_at")
        items = _walk(client, "/alerts/", **ALERT_RANGE)
        _assert_sorted([_ts(a["triggered_at"]) for a in items], "desc", "default")

    def test_sort_combines_with_filters(self, client):
        items = _walk(client, "/alerts/", **ALERT_RANGE, severity="critical", resolved="false",
                      sort_by="location", sort_dir="asc")
        assert items and all(a["severity"] == "critical" and not a["is_resolved"] for a in items)
        _assert_sorted([ALERT_KEYS["location"](a) for a in items], "asc", "filtered by location")

    @pytest.mark.parametrize("bad", [{"sort_by": "priority"}, {"sort_by": "severity", "sort_dir": "high"}])
    def test_unknown_values_rejected(self, client, bad):
        assert client.get("/alerts/", params=bad).status_code == 422

    @pytest.mark.parametrize("key", ["severity", "location", "plate"])
    def test_csv_follows_sort(self, client, key):
        params = {**ALERT_RANGE, "sort_by": key, "sort_dir": "asc"}
        listed = [a["id"] for a in _walk(client, "/alerts/", **params)]
        r = client.get("/alerts/export/csv", params=params)
        assert r.status_code == 200
        rows_ = list(csv.DictReader(io.StringIO(r.text.lstrip("﻿"))))
        assert [int(row["ID"]) for row in rows_] == listed

    def test_sorted_csv_has_the_same_columns_and_values(self, client):
        plain = list(csv.DictReader(io.StringIO(
            client.get("/alerts/export/csv", params=ALERT_RANGE).text.lstrip("﻿"))))
        srt = list(csv.DictReader(io.StringIO(
            client.get("/alerts/export/csv", params={**ALERT_RANGE, "sort_by": "triggered_at"}).text.lstrip("﻿"))))
        assert list(plain[0]) == list(srt[0])
        assert {r["ID"]: r for r in plain} == {r["ID"]: r for r in srt}
