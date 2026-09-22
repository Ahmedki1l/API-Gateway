"""SQLite-backed regression tests for the Entry/Exit and Alerts query contracts."""
import base64
import csv
import io
import os
import re
import sqlite3
import unittest
from datetime import datetime
from unittest.mock import patch

import httpx
from fastapi import FastAPI

with patch.dict(os.environ, {
    "CAMERAS_ENCRYPTION_KEY": base64.urlsafe_b64encode(bytes(32)).decode(),
    "CAMERAS_INTERNAL_TOKEN": "unused", "PREFIX": "",
}):
    with patch("sqlalchemy.create_engine"):
        from app.routers import alerts, entry_exit
        from app.database import get_db


class SqliteSessionAdapter:
    """Adapts SQLAlchemy TextClause writes used by alert mutations for SQLite."""

    def __init__(self, connection):
        self.connection = connection

    def execute(self, statement, params):
        sql = str(statement).replace("GETDATE()", "CURRENT_TIMESTAMP")
        return self.connection.execute(sql, params)

    def commit(self):
        self.connection.commit()


class TitleSearchAndSessionSortingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.create_function("DATEDIFF", 3, lambda _, a, b: int(
            (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds()))
        self.db.executescript("""
            CREATE TABLE vehicles (
                id INTEGER, plate_number TEXT, owner_name TEXT,
                vehicle_type TEXT, is_employee INTEGER, title TEXT
            );
            CREATE TABLE parking_slots (slot_id TEXT, slot_name TEXT, floor TEXT);
            CREATE TABLE parking_sessions (
                id INTEGER, vehicle_id INTEGER, plate_number TEXT, status TEXT,
                entry_time TEXT, exit_time TEXT, duration_seconds INTEGER,
                floor TEXT, floor_id INTEGER, slot_id TEXT, slot_number TEXT,
                parked_at TEXT, slot_left_at TEXT, entry_camera_id TEXT,
                exit_camera_id TEXT, slot_camera_id TEXT, entry_snapshot_path TEXT,
                exit_snapshot_path TEXT, slot_snapshot_path TEXT,
                vehicle_type TEXT, is_employee INTEGER
            );
            CREATE TABLE alerts (
                id INTEGER, alert_type TEXT, camera_id TEXT, zone_id TEXT,
                zone_name TEXT, slot_number TEXT, description TEXT,
                snapshot_path TEXT, is_test INTEGER, is_resolved INTEGER,
                resolved_at TEXT, triggered_at TEXT, plate_number TEXT
            );
            CREATE TABLE cameras (camera_id TEXT);
        """)
        self.db.executemany(
            "INSERT INTO vehicles VALUES (?,?,?,?,?,?)",
            [
                (1, "A-100", "Alice", "car", 0, "Chief title"),
                (2, "B-200", "Bob", "car", 0, "Visitor title"),
                (3, "C-300", "Carol", "car", 0, ""),
                (4, "D-400", "Dana", "car", 0, "Night title"),
                (5, "E-500", "Evan", "car", 0, ""),
            ],
        )
        self.db.executemany(
            """INSERT INTO parking_sessions
               (id, vehicle_id, plate_number, status, entry_time, exit_time,
                duration_seconds, vehicle_type, is_employee)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            [
                (1, None, "A-100", "open", "2026-09-16 09:00:00", None, 3600, "car", 0),
                (2, 2, "B-200", "closed", "2026-09-16 10:00:00", "2026-09-16 14:00:00", 3600, "car", 0),
                (3, None, "C-300", "closed", "2026-09-16 10:00:00", "2026-09-16 13:00:00", 3600, "car", 0),
                (4, None, "D-400", "closed", "2026-09-16 08:00:00", "2026-09-16 15:00:00", 3600, "car", 0),
                (5, None, "E-500", "open", None, None, 3600, "car", 0),
            ],
        )
        self.db.executemany(
            """INSERT INTO alerts
               (id, alert_type, camera_id, description, is_test, is_resolved,
                triggered_at, plate_number)
               VALUES (?,?,?,?,?,?,?,?)""",
            [
                (1, "overstay", "CAM-1", "duration threshold", 0, 0,
                 "2026-09-16 11:00:00", "A-100"),
                (2, "overstay", "CAM-1", "duration threshold", 0, 0,
                 "2026-09-16 10:00:00", "B-200"),
            ],
        )
        self.db.execute("INSERT INTO cameras VALUES ('CAM-1')")
        self.addCleanup(self.db.close)
        self.session = SqliteSessionAdapter(self.db)

        alert_cols = {
            "severity": False, "location_display": False, "slot_id": False,
            "vehicle_id": False, "vehicle_event_id": False,
            "triggering_camera_event_id": False, "resolved_by": False,
            "resolution_notes": False, "event_type": False,
        }
        for replacement in [
            patch.object(entry_exit, "_floor_schema", return_value={"parking_sessions_floor_id": True}),
            patch.object(entry_exit, "scalar", self.scalar),
            patch.object(entry_exit, "rows", self.rows),
            patch.object(alerts, "_floor_schema", return_value={"cameras_watches_floor": False, "floors_table": False}),
            patch.object(alerts, "_alerts_extra_cols", return_value=alert_cols),
            patch.object(alerts, "scalar", self.scalar),
            patch.object(alerts, "rows", self.rows),
        ]:
            replacement.start()
            self.addCleanup(replacement.stop)

        app = FastAPI()
        app.include_router(entry_exit.router)
        app.include_router(alerts.router)
        app.dependency_overrides[get_db] = lambda: self.session
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    def execute(self, sql, params):
        sql = re.sub(r"CAST\((ps\.\w+) AS DATE\)", r"date(\1)", sql)
        sql = sql.replace(
            "OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY",
            "LIMIT :page_size OFFSET :offset",
        )
        sql = sql.replace("DATEDIFF(SECOND,", "DATEDIFF('SECOND',")
        return self.db.execute(sql, params)

    def scalar(self, db, sql, params):
        return self.execute(sql, params).fetchone()[0]

    def rows(self, db, sql, params):
        result = [dict(row) for row in self.execute(sql, params)]
        for row in result:
            for key in (
                "entry_time", "exit_time", "parked_at", "slot_left_at",
                "triggered_at", "resolved_at", "Triggered At", "Resolved At",
            ):
                if row.get(key):
                    row[key] = datetime.fromisoformat(row[key])
        return result

    async def test_title_only_search_matches_entry_exit_list_count_and_csv(self):
        params = {"search": "Chief"}
        listed = await self.client.get("/entry-exit/", params=params)
        exported = await self.client.get("/entry-exit/export/csv", params=params)

        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(exported.status_code, 200, exported.text)
        self.assertEqual(listed.json()["total_count"], 1)
        self.assertEqual([item["plate_number"] for item in listed.json()["items"]], ["A-100"])
        records = list(csv.DictReader(io.StringIO(exported.text.lstrip("\ufeff"))))
        self.assertEqual([record["Plate Number"] for record in records], ["A-100"])

    async def test_title_only_search_matches_alert_list_count_and_csv(self):
        params = {"search": "Chief"}
        listed = await self.client.get("/alerts/", params=params)
        exported = await self.client.get("/alerts/export/csv", params=params)

        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(exported.status_code, 200, exported.text)
        self.assertEqual(listed.json()["total_count"], 1)
        self.assertEqual([item["plate_number"] for item in listed.json()["items"]], ["A-100"])
        records = list(csv.DictReader(io.StringIO(exported.text.lstrip("\ufeff"))))
        self.assertEqual([record["Plate Number"] for record in records], ["A-100"])

    async def test_historical_unidentified_filter_matches_list_and_csv(self):
        self.db.execute("UPDATE alerts SET alert_type='reserved_slot_unidentified' WHERE id=1")
        params = {"alert_type": "reserved_slot_unidentified"}
        listed = await self.client.get("/alerts/", params=params)
        exported = await self.client.get("/alerts/export/csv", params=params)

        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(exported.status_code, 200, exported.text)
        self.assertEqual(listed.json()["total_count"], 1)
        self.assertEqual([item["plate_number"] for item in listed.json()["items"]], ["A-100"])
        records = list(csv.DictReader(io.StringIO(exported.text.lstrip("\ufeff"))))
        self.assertEqual([record["Plate Number"] for record in records], ["A-100"])

    async def test_alerts_support_generic_resolve_and_delete(self):
        resolved = await self.client.patch("/alerts/1/resolve")
        self.assertEqual(resolved.status_code, 200, resolved.text)
        self.assertEqual(self.db.execute("SELECT is_resolved FROM alerts WHERE id=1").fetchone()[0], 1)

        deleted = await self.client.delete("/alerts/2")
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertIsNone(self.db.execute("SELECT id FROM alerts WHERE id=2").fetchone())

    async def test_cancelled_special_needs_review_is_not_an_available_api(self):
        for path in ("/alerts/", "/alerts/export/csv"):
            response = await self.client.get(path, params={"alert_type": "special_needs_review"})
            self.assertEqual(response.status_code, 422, response.text)
        review = await self.client.post("/alerts/1/special-needs-review", json={})
        self.assertEqual(review.status_code, 404, review.text)

    async def test_entry_sort_is_stable_across_pages_and_csv(self):
        params = {"sort_by": "entry_time", "sort_direction": "asc", "page_size": 2}
        first = await self.client.get("/entry-exit/", params={**params, "page": 1})
        second = await self.client.get("/entry-exit/", params={**params, "page": 2})
        third = await self.client.get("/entry-exit/", params={**params, "page": 3})
        exported = await self.client.get("/entry-exit/export/csv", params=params)
        default = await self.client.get("/entry-exit/", params={"page_size": 100})
        explicit_default = await self.client.get("/entry-exit/", params={
            "page_size": 100, "sort_by": "entry_time", "sort_direction": "desc",
        })

        for response in (first, second, third, exported, default, explicit_default):
            self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item["id"] for item in first.json()["items"]], [4, 1])
        self.assertEqual([item["id"] for item in second.json()["items"]], [2, 3])
        self.assertEqual([item["id"] for item in third.json()["items"]], [5])
        self.assertEqual(default.json()["items"], explicit_default.json()["items"])
        records = list(csv.DictReader(io.StringIO(exported.text.lstrip("\ufeff"))))
        self.assertEqual([record["Plate Number"] for record in records],
                         ["D-400", "A-100", "B-200", "C-300", "E-500"])

    async def test_exit_sort_keeps_nulls_last_in_both_directions(self):
        ascending = await self.client.get("/entry-exit/", params={
            "sort_by": "exit_time", "sort_direction": "asc", "page_size": 100,
        })
        descending = await self.client.get("/entry-exit/", params={
            "sort_by": "exit_time", "sort_direction": "desc", "page_size": 100,
        })

        self.assertEqual(ascending.status_code, 200, ascending.text)
        self.assertEqual(descending.status_code, 200, descending.text)
        self.assertEqual([item["id"] for item in ascending.json()["items"]], [3, 2, 4, 1, 5])
        self.assertEqual([item["id"] for item in descending.json()["items"]], [4, 2, 3, 5, 1])

    async def test_entry_sort_rejects_unknown_columns_and_directions(self):
        unknown_column = await self.client.get("/entry-exit/", params={
            "sort_by": "entry_time DESC; DROP TABLE parking_sessions",
        })
        unknown_direction = await self.client.get("/entry-exit/", params={"sort_direction": "sideways"})

        self.assertEqual(unknown_column.status_code, 422)
        self.assertEqual(unknown_direction.status_code, 422)

    async def test_filtered_kpis_follow_title_status_and_exit_date(self):
        params = {"search": "Night title", "status": "closed",
                  "date_from": "2026-09-16", "date_to": "2026-09-16"}
        listing = await self.client.get("/entry-exit/", params=params)
        stats = await self.client.get("/entry-exit/kpis", params={**params, "scope": "filtered"})
        self.assertEqual(stats.status_code, 200, stats.text)
        self.assertEqual(stats.json()["total_exit"], listing.json()["total_count"])
        self.assertEqual(stats.json()["total_enter"], 1)
        self.assertEqual(stats.json()["avg_stay_minutes"], 60)
        empty = await self.client.get("/entry-exit/kpis", params={
            "scope": "filtered", "search": "missing-title"})
        self.assertEqual(empty.json(), {"total_enter": 0, "total_exit": 0,
                                      "avg_stay_minutes": 0, "overstays": 0})

    async def test_weekly_alert_counters_preserve_history_and_week_boundaries(self):
        self.db.execute("DELETE FROM alerts")
        self.db.executemany("""INSERT INTO alerts
            (id, alert_type, triggered_at, is_resolved, is_test) VALUES (?,?,?,?,?)""", [
            (1, "vehicle_intrusion", "2026-09-20 23:59:59", 0, 0),
            (2, "vehicle_intrusion", "2026-09-21 00:00:00", 0, 0),
            (3, "overstay", "2026-09-27 23:59:59", 1, 0),
            (4, "vehicle_intrusion", "2026-09-28 00:00:00", 0, 0),
            (5, "vehicle_intrusion", "2026-09-22 12:00:00", 0, 1),
        ])
        with patch.object(alerts, "facility_now_naive", return_value=datetime(2026, 9, 22, 12)):
            weekly = await self.client.get("/alerts/stats", params={"period": "week"})
            all_time = await self.client.get("/alerts/stats")
        self.assertEqual(weekly.status_code, 200, weekly.text)
        self.assertEqual(weekly.json(), {"active_alerts": 1, "critical_violations": 1, "resolved_total": 1})
        self.assertEqual(all_time.json(), {"active_alerts": 3, "critical_violations": 3, "resolved_total": 1})
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM alerts").fetchone()[0], 5)
        invalid = await self.client.get("/alerts/stats", params={"period": "delete"})
        self.assertEqual(invalid.status_code, 422)
        self.db.execute("ALTER TABLE alerts ADD COLUMN severity TEXT")
        self.db.execute("UPDATE alerts SET severity='warning'")
        self.db.execute("UPDATE alerts SET severity='critical' WHERE id=2")
        with patch.object(alerts, "_alerts_extra_cols", return_value={"severity": True}), \
             patch.object(alerts, "facility_now_naive", return_value=datetime(2026, 9, 22, 12)):
            modern = await self.client.get("/alerts/stats", params={"period": "week"})
        self.assertEqual(modern.json(), weekly.json())
