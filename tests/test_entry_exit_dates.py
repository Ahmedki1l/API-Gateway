"""HTTP regressions executing list/count/export SQL against local SQLite fixtures.

Only SQL Server date-cast, pagination and DATEDIFF syntax is adapted for SQLite.
"""
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
    'CAMERAS_ENCRYPTION_KEY': base64.urlsafe_b64encode(bytes(32)).decode(),
    'CAMERAS_INTERNAL_TOKEN': 'unused', 'PREFIX': '',
}):
    with patch('sqlalchemy.create_engine'):
        from app.routers import entry_exit
        from app.database import get_db


class EntryExitDateTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.create_function('DATEDIFF', 3, lambda _, a, b: int(
            (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds()))
        self.db.executescript('''
            CREATE TABLE vehicles (id INTEGER, plate_number TEXT, owner_name TEXT,
                vehicle_type TEXT, is_employee INTEGER);
            CREATE TABLE parking_slots (slot_id TEXT, slot_name TEXT);
            CREATE TABLE parking_sessions (
                id INTEGER, vehicle_id INTEGER, plate_number TEXT, status TEXT,
                entry_time TEXT, exit_time TEXT, duration_seconds INTEGER,
                floor TEXT, floor_id INTEGER, slot_id TEXT, slot_number TEXT,
                parked_at TEXT, slot_left_at TEXT, entry_camera_id TEXT,
                exit_camera_id TEXT, slot_camera_id TEXT, entry_snapshot_path TEXT,
                exit_snapshot_path TEXT, slot_snapshot_path TEXT,
                vehicle_type TEXT, is_employee INTEGER);
        ''')
        fixtures = [
            (1, 'overnight', 'closed', '2026-09-15 20:00:00', '2026-09-16 00:00:00'),
            (2, 'same-day', 'closed', '2026-09-16 08:00:00', '2026-09-16 23:59:59'),
            (3, 'next-day', 'closed', '2026-09-16 09:00:00', '2026-09-17 00:00:00'),
            (4, 'previous-day', 'closed', '2026-09-15 08:00:00', '2026-09-15 23:59:59'),
            (5, 'open', 'open', '2026-09-16 10:00:00', None),
            (6, 'missing-exit', 'closed', '2026-09-16 11:00:00', None),
        ]
        self.db.executemany('INSERT INTO parking_sessions '
            '(id,plate_number,status,entry_time,exit_time,duration_seconds) '
            'VALUES (?,?,?,?,?,3600)', fixtures)
        self.addCleanup(self.db.close)
        for replacement in [
            patch.object(entry_exit, '_floor_schema', return_value={'parking_sessions_floor_id': True}),
            patch.object(entry_exit, 'scalar', self.scalar),
            patch.object(entry_exit, 'rows', self.rows),
        ]:
            replacement.start()
            self.addCleanup(replacement.stop)
        app = FastAPI()
        app.include_router(entry_exit.router)
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test')

    async def asyncTearDown(self):
        await self.client.aclose()

    def execute(self, sql, params):
        sql = re.sub(r'CAST\((ps\.\w+) AS DATE\)', r'date(\1)', sql)
        sql = sql.replace('OFFSET :offset ROWS FETCH NEXT :page_size ROWS ONLY',
                          'LIMIT :page_size OFFSET :offset')
        sql = sql.replace('DATEDIFF(SECOND,', "DATEDIFF('SECOND',")
        return self.db.execute(sql, params)

    def scalar(self, db, sql, params):
        return self.execute(sql, params).fetchone()[0]

    def rows(self, db, sql, params):
        result = [dict(row) for row in self.execute(sql, params)]
        for row in result:
            for key in ('entry_time', 'exit_time', 'parked_at', 'slot_left_at'):
                if row.get(key):
                    row[key] = datetime.fromisoformat(row[key])
        return result

    async def assert_results(self, params, expected):
        response = await self.client.get('/entry-exit/', params=params)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['total_count'], len(expected))
        self.assertEqual({row['plate_number'] for row in body['items']}, expected)
        exported = await self.client.get('/entry-exit/export/csv', params=params)
        self.assertEqual(exported.status_code, 200, exported.text)
        records = list(csv.DictReader(io.StringIO(exported.text.lstrip('\ufeff'))))
        self.assertEqual({row['Plate Number'] for row in records}, expected)

    async def test_closed_uses_exit_day_including_overnight_and_boundaries(self):
        await self.assert_results({'status': 'closed', 'date_from': '2026-09-16',
            'date_to': '2026-09-16'}, {'overnight', 'same-day'})

    async def test_one_sided_exit_date_filters(self):
        await self.assert_results({'status': 'closed', 'date_from': '2026-09-16'},
            {'overnight', 'same-day', 'next-day'})
        await self.assert_results({'status': 'closed', 'date_to': '2026-09-16'},
            {'overnight', 'same-day', 'previous-day'})

    async def test_entry_date_behavior_is_preserved(self):
        await self.assert_results({'date_from': '2026-09-16', 'date_to': '2026-09-16'},
            {'same-day', 'next-day', 'open', 'missing-exit'})
        await self.assert_results({'status': 'open', 'date_from': '2026-09-16',
            'date_to': '2026-09-16'}, {'open'})

    async def test_closed_without_dates_preserves_existing_population(self):
        await self.assert_results({'status': 'closed'},
            {'overnight', 'same-day', 'next-day', 'previous-day', 'missing-exit'})
