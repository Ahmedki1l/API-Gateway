"""SQLite contract tests for monitored-bay availability across Gateway surfaces."""
import base64
import csv
import io
import os
import re
import sqlite3
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI


with patch.dict(os.environ, {
    "CAMERAS_ENCRYPTION_KEY": base64.urlsafe_b64encode(bytes(32)).decode(),
    "CAMERAS_INTERNAL_TOKEN": "unused",
    "PREFIX": "",
}):
    with patch("sqlalchemy.create_engine"):
        from app.database import get_db
        from app.routers import _helpers, dashboard, occupancy


_SCHEMA = {
    "floors_table": True,
    "parking_slots_id": False,
    "parking_slots_floor_id": True,
    "parking_slots_slot_type": True,
    "parking_slots_reservation_type": False,
    "parking_slots_reserved_for": False,
    "parking_slots_is_monitored": True,
    "parking_slots_current_plate": False,
}


class MonitoredSlotAvailabilityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE floors (id INTEGER, name TEXT, is_active INTEGER, sort_order INTEGER);
            CREATE TABLE parking_slots (
                slot_id TEXT, slot_name TEXT, floor TEXT, floor_id INTEGER,
                is_violation_zone INTEGER, slot_type TEXT, is_monitored INTEGER,
                is_available INTEGER
            );
            CREATE TABLE slot_status (slot_id TEXT, status TEXT, time INTEGER);
            CREATE TABLE parking_sessions (plate_number TEXT, status TEXT);
            CREATE TABLE zone_occupancy (
                id INTEGER, zone_id TEXT, zone_name TEXT, floor TEXT,
                camera_id TEXT, max_capacity INTEGER, current_count INTEGER,
                last_updated TEXT
            );
            CREATE TABLE alerts (
                is_resolved INTEGER, is_test INTEGER, severity TEXT,
                triggered_at TEXT
            );
        """)
        self.db.executemany(
            "INSERT INTO floors VALUES (?,?,1,?)", [(1, "B1", 1), (2, "B2", 2)]
        )
        self.db.executemany(
            "INSERT INTO parking_slots VALUES (?,?,?,?,?,?,?,1)",
            [
                ("M1", "M1", "B1", 1, 0, "regular", 1),
                ("M2", "M2", "B1", 1, 0, "regular", 1),
                ("M3", "M3", "B1", 1, 0, "regular", 1),
                ("M4", "M4", "B1", 1, 0, "regular", 1),
                ("M5", "M5", "B1", 1, 0, "regular", 1),
                ("U1", "U1", "B1", 1, 0, "regular", 0),
                ("U2", "U2", "B2", 2, 0, "regular", 0),
                ("V1", "V1", "B1", 1, 1, "regular", 1),
                ("R1", "R1", "B1", 1, 0, "roi", 1),
            ],
        )
        self.db.executemany(
            "INSERT INTO slot_status VALUES (?,?,?)",
            [
                ("M1", "OCCUPIED", 1), ("M1", "VACANT", 2),
                ("M2", "LEAVING", 2), ("M3", "", 2),
                # Duplicate latest records must still count M4 as one occupied bay.
                ("M4", "OCCUPIED", 4), ("M4", "OCCUPIED", 4),
                # These stale occupied statuses belong to unmonitored bays.
                ("U1", "OCCUPIED", 99), ("U2", "OCCUPIED", 99),
                ("V1", "OCCUPIED", 99), ("R1", "OCCUPIED", 99),
            ],
        )
        self.db.executemany(
            "INSERT INTO zone_occupancy VALUES (?,?,?,?,?,?,?,?)",
            [
                (1, "B1-PARKING", "B1 Parking", "B1", "cam-b1", 99, 99, None),
                (2, "B2-PARKING", "B2 Parking", "B2", "cam-b2", 99, 99, None),
                (3, "GARAGE-TOTAL", "Garage", None, None, 99, 99, None),
                (4, "B1-WEST", "B1 West", "B1", "cam-b1-west", 99, 7, None),
                (5, "B1-EAST", "B1 East", "B1", "cam-b1-east", 99, 11, None),
                (6, "B1-UNMAPPED", "B1 Unmapped", "B1", "cam-b1-unmapped", 99, 13, None),
            ],
        )
        self.live_slots = [
            {"slot_id": "M1", "zone_id": "B1-WEST"},
            {"slot_id": "M2", "zone": "B1-WEST"},
            {"slot_id": "M3", "zone_id": "B1-EAST"},
            {"slot_id": "M4", "zone_id": "B1-EAST"},
            {"slot_id": "M5", "zone_id": "B1-EAST"},
        ]
        self.addCleanup(self.db.close)

        for replacement in [
            patch.object(occupancy, "_floor_schema", return_value=_SCHEMA),
            patch.object(dashboard, "_floor_schema", return_value=_SCHEMA),
            patch.object(_helpers, "_floor_schema", return_value=_SCHEMA),
            patch.object(occupancy, "rows", self.rows),
            patch.object(occupancy, "scalar", self.scalar),
            patch.object(_helpers, "scalar", self.scalar),
            patch.object(dashboard, "scalar", self.scalar),
            patch.object(dashboard, "_alerts_extra_cols", return_value={"severity": True}),
            patch.object(
                occupancy,
                "_active_violation_cols",
                return_value="NULL AS active_violation_type, NULL AS active_violation_severity, 0 AS has_active_violation",
            ),
            patch.object(occupancy, "get_live_slots", new=AsyncMock(return_value=self.live_slots)),
        ]:
            replacement.start()
            self.addCleanup(replacement.stop)

        app = FastAPI()
        app.include_router(dashboard.router)
        app.include_router(occupancy.router)
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )
        self.addAsyncCleanup(self.client.aclose)

    def execute(self, sql, params=None):
        sql = sql.replace("dbo.floors", "floors")
        sql = re.sub(
            r"OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY",
            "LIMIT :page_size OFFSET :offset",
            sql,
        )
        return self.db.execute(sql, params or {})

    def scalar(self, db, sql, params=None):
        return self.execute(sql, params).fetchone()[0]

    def rows(self, db, sql, params=None):
        # The export's detail-table natural sort is SQL Server-specific and
        # independent of its KPI calculation, which this fixture executes.
        if "FROM parking_slots ps" in sql and "status_updated_at" in sql:
            return []
        return [dict(row) for row in self.execute(sql, params)]

    async def get_json(self, path):
        response = await self.client.get(path)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_partial_coverage_is_consistent_across_all_availability_surfaces(self):
        dashboard_kpis = await self.get_json("/dashboard/kpis")
        occupancy_kpis = await self.get_json("/occupancy/kpis")
        totals = await self.get_json("/occupancy/totals")
        floors = await self.get_json("/occupancy/floors")
        zones = await self.get_json("/occupancy/zones")
        export = await self.client.get("/occupancy/export")
        self.assertEqual(export.status_code, 200, export.text)

        self.assertEqual(dashboard_kpis["total_slots"], 7)
        self.assertEqual(dashboard_kpis["occupied_slots"], 2)
        self.assertEqual(dashboard_kpis["free_slots"], 3)
        self.assertEqual(occupancy_kpis["monitored_slots"], 5)
        self.assertEqual(occupancy_kpis["unmonitored_slots"], 2)
        self.assertEqual(occupancy_kpis["available_slots"], 3)
        self.assertEqual(totals["available_slots"], 3)
        self.assertEqual({f["floor"]: f["available"] for f in floors["items"]}, {"B1": 3, "B2": 0})
        availability_by_zone = {z["zone_id"]: z["available"] for z in zones["items"]}
        self.assertEqual({zone_id: availability_by_zone[zone_id] for zone_id in [
            "B1-PARKING", "B2-PARKING", "GARAGE-TOTAL",
        ]}, {
            "B1-PARKING": 3, "B2-PARKING": 0, "GARAGE-TOTAL": 3,
        })

        report = list(csv.reader(io.StringIO(export.text)))
        kpis = dict(report[1:7])
        self.assertEqual(kpis["total_spots"], "7")
        self.assertEqual(kpis["monitored_spots"], "5")
        self.assertEqual(kpis["occupied_spots"], "2")
        self.assertEqual(kpis["available_spots"], "3")

    async def test_non_aggregate_same_floor_zones_use_live_slot_membership(self):
        zones = await self.get_json("/occupancy/zones")
        zones_by_id = {z["zone_id"]: z for z in zones["items"]}

        self.assertEqual(
            (zones_by_id["B1-PARKING"]["occupied"], zones_by_id["B1-PARKING"]["available"]),
            (2, 3),
        )
        self.assertEqual(
            (zones_by_id["GARAGE-TOTAL"]["occupied"], zones_by_id["GARAGE-TOTAL"]["available"]),
            (2, 3),
        )
        self.assertEqual(
            (zones_by_id["B1-WEST"]["occupied"], zones_by_id["B1-WEST"]["available"], zones_by_id["B1-WEST"]["current_count"]),
            (1, 1, 7),
        )
        self.assertEqual(
            (zones_by_id["B1-EAST"]["occupied"], zones_by_id["B1-EAST"]["available"], zones_by_id["B1-EAST"]["current_count"]),
            (1, 2, 11),
        )
        self.assertEqual(
            (zones_by_id["B1-UNMAPPED"]["occupied"], zones_by_id["B1-UNMAPPED"]["available"], zones_by_id["B1-UNMAPPED"]["current_count"]),
            (0, 0, 13),
        )

    async def test_all_monitored_uses_physical_total_only_for_inventory(self):
        self.db.execute("UPDATE parking_slots SET is_monitored = 1 WHERE is_violation_zone = 0 AND slot_type = 'regular'")
        dashboard_kpis = await self.get_json("/dashboard/kpis")
        occupancy_kpis = await self.get_json("/occupancy/kpis")
        self.assertEqual(dashboard_kpis["total_slots"], 7)
        self.assertEqual(dashboard_kpis["occupied_slots"], 4)
        self.assertEqual(dashboard_kpis["free_slots"], 3)
        self.assertEqual(occupancy_kpis["available_slots"], 3)

    async def test_no_monitored_slots_clamps_availability_to_zero(self):
        self.db.execute("UPDATE parking_slots SET is_monitored = 0")
        for path, key in [
            ("/dashboard/kpis", "free_slots"),
            ("/occupancy/kpis", "available_slots"),
            ("/occupancy/totals", "available_slots"),
        ]:
            self.assertEqual((await self.get_json(path))[key], 0)
        floors = await self.get_json("/occupancy/floors")
        self.assertTrue(all(f["available"] == 0 for f in floors["items"]))

    async def test_no_slots_returns_zero_inventory_and_availability(self):
        self.db.execute("DELETE FROM parking_slots")
        for path, total_key, available_key in [
            ("/dashboard/kpis", "total_slots", "free_slots"),
            ("/occupancy/kpis", "total_slots", "available_slots"),
            ("/occupancy/totals", "total_slots", "available_slots"),
        ]:
            body = await self.get_json(path)
            self.assertEqual(body[total_key], 0)
            self.assertEqual(body[available_key], 0)

    async def test_pre_schema_fallback_treats_every_slot_as_monitored(self):
        legacy_schema = {**_SCHEMA, "parking_slots_is_monitored": False}
        with patch.object(occupancy, "_floor_schema", return_value=legacy_schema):
            totals = await self.get_json("/occupancy/totals")
        self.assertEqual(totals["total_slots"], 7)
        self.assertEqual(totals["occupied_slots"], 4)
        self.assertEqual(totals["available_slots"], 3)

    async def test_large_zone_membership_stays_within_database_parameter_limit(self):
        membership = {row[0] for row in self.db.execute("SELECT slot_id FROM parking_slots")}
        membership.update(f"absent-{index}" for index in range(2200))

        def limited_rows(db, sql, params=None):
            if len(params or {}) > 2100:
                raise RuntimeError("database parameter limit exceeded")
            return self.rows(db, sql, params)

        with patch.object(occupancy, "rows", side_effect=limited_rows):
            counts = occupancy._monitored_slot_availability(self.db, slot_ids=membership)
        self.assertEqual(counts, (7, 5, 2, 3))
