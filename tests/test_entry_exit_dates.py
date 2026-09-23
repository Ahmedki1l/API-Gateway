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
from sqlalchemy import text
from sqlalchemy.dialects.mssql.pyodbc import MSDialect_pyodbc

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
        def datediff(unit, start, end):
            delta = datetime.fromisoformat(end) - datetime.fromisoformat(start)
            return int(delta.total_seconds() / {'SECOND': 1, 'HOUR': 3600, 'DAY': 86400}[unit])
        self.db.create_function('DATEDIFF', 3, datediff)
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
        for unit in ('SECOND', 'HOUR', 'DAY'):
            sql = sql.replace(f'DATEDIFF({unit},', f"DATEDIFF('{unit}',")
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

    async def test_exit_kpi_uses_departure_day_and_matches_closed_list(self):
        response = await self.client.get('/entry-exit/kpis',
                                         params={'target_date': '2026-09-16'})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body['total_exit'], 2)
        self.assertEqual(body['total_enter'], 4)
        self.assertEqual(body['avg_stay_minutes'], 60.0)
        listing = await self.client.get('/entry-exit/', params={
            'status': 'closed', 'date_from': '2026-09-16', 'date_to': '2026-09-16'})
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertEqual(body['total_exit'], listing.json()['total_count'])

    async def test_default_exit_kpi_uses_current_facility_day(self):
        with patch.object(entry_exit, 'facility_today_utc',
                          return_value=datetime(2026, 9, 16)):
            response = await self.client.get('/entry-exit/kpis')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['total_exit'], 2)

    async def test_exit_kpi_returns_zero_for_day_without_departures(self):
        response = await self.client.get('/entry-exit/kpis',
                                         params={'target_date': '2026-09-18'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['total_exit'], 0)

    async def test_duration_list_export_and_completed_average_agree(self):
        self.db.execute('DELETE FROM parking_sessions')
        self.db.executemany('INSERT INTO parking_sessions '
            '(id,plate_number,status,entry_time,exit_time,parked_at,duration_seconds) '
            'VALUES (?,?,?,?,?,?,?)', [
                (10, 'computed', 'closed', '2026-09-15 23:45:00', '2026-09-16 00:15:30', None, None),
                (11, 'stored', 'closed', '2026-09-16 08:00:00', '2026-09-16 09:00:00', None, 1200),
                (12, 'live', 'open', '2026-09-16 11:50:00', None, None, 9999),
                (13, 'slot-start', 'closed', None, '2026-09-16 10:05:00', '2026-09-16 10:00:00', None),
                (14, 'negative-clock', 'closed', '2026-09-16 11:00:00', '2026-09-16 10:59:00', None, None),
            ])
        with patch.object(entry_exit, 'facility_now_naive', return_value=datetime(2026, 9, 16, 12)):
            listing = await self.client.get('/entry-exit/')
            exported = await self.client.get('/entry-exit/export/csv')
            kpi = await self.client.get('/entry-exit/kpis', params={'target_date': '2026-09-16'})
        for response in (listing, exported, kpi):
            self.assertEqual(response.status_code, 200, response.text)
        durations = {row['plate_number']: row['duration_seconds'] for row in listing.json()['items']}
        self.assertEqual(durations, {'computed': 1830, 'stored': 1200, 'live': 600,
                                    'slot-start': 300, 'negative-clock': 0})
        csv_rows = list(csv.DictReader(io.StringIO(exported.text.lstrip('\ufeff'))))
        self.assertEqual({row['Plate Number']: float(row['Duration (min)']) for row in csv_rows},
                         {plate: seconds / 60 for plate, seconds in durations.items()})
        self.assertEqual(kpi.json()['avg_stay_minutes'], 13.9)

    async def test_duration_filters_use_effective_duration_in_list_and_csv(self):
        self.db.execute('UPDATE parking_sessions SET duration_seconds = NULL WHERE id=1')
        with patch.object(entry_exit, 'facility_now_naive', return_value=datetime(2026, 9, 16, 12)):
            await self.assert_results({'status': 'closed', 'min_duration_seconds': 14400,
                                       'max_duration_seconds': 14400}, {'overnight'})

    async def test_traffic_operating_day_uses_local_boundaries_without_utc_guessing(self):
        self.db.execute('CREATE TABLE entry_exit_log (event_time TEXT, gate TEXT, is_test INTEGER)')
        self.db.executemany('INSERT INTO entry_exit_log VALUES (?,?,?)', [
            ('2026-09-21 07:59:59', 'entry', 0),
            ('2026-09-21 08:00:00', 'entry', 0),
            ('2026-09-21 21:30:00', 'exit', 0),
            ('2026-09-22 07:59:59', 'exit', 0),
            ('2026-09-22 08:00:00', 'entry', 0),
            ('2026-09-21 09:00:00', 'entry', 1),
        ])
        with patch.object(entry_exit, 'facility_now_naive', return_value=datetime(2026, 9, 22, 7, 59)):
            response = await self.client.get('/entry-exit/traffic', params={'period': 'daily'})
        self.assertEqual(response.status_code, 200, response.text)
        buckets = response.json()
        self.assertEqual(len(buckets), 24)
        self.assertEqual(buckets[0], {'label': '08:00', 'entries': 1, 'exits': 0})
        self.assertEqual(buckets[13], {'label': '21:00', 'entries': 0, 'exits': 1})
        self.assertEqual(buckets[23], {'label': '07:00', 'entries': 0, 'exits': 1})
        self.assertEqual(sum(b['entries'] for b in buckets), 1)
        self.assertEqual(sum(b['exits'] for b in buckets), 2)
        with patch.object(entry_exit, 'facility_now_naive', return_value=datetime(2026, 9, 22, 8)):
            response = await self.client.get('/entry-exit/traffic', params={'period': 'daily'})
        self.assertEqual(response.json()[0]['entries'], 1)
        self.assertEqual(sum(b['exits'] for b in response.json()), 0)

    async def test_weekly_and_monthly_traffic_keep_late_local_events_on_their_date(self):
        self.db.execute('CREATE TABLE entry_exit_log (event_time TEXT, gate TEXT, is_test INTEGER)')
        self.db.executemany('INSERT INTO entry_exit_log VALUES (?,?,0)', [
            ('2026-09-21 23:30:00', 'exit'), ('2026-09-22 00:00:00', 'entry'),
        ])
        with patch.object(entry_exit, 'facility_now_naive', return_value=datetime(2026, 9, 22, 12)):
            for period, count in [('weekly', 7), ('monthly', 30)]:
                response = await self.client.get('/entry-exit/traffic', params={'period': period})
                self.assertEqual(response.status_code, 200, response.text)
                buckets = response.json()
                self.assertEqual(len(buckets), count)
                self.assertEqual(buckets[-2]['exits'], 1)
                self.assertEqual(buckets[-1]['entries'], 1)
                self.assertEqual(buckets[-1]['exits'], 0)
        self.assertEqual((await self.client.get('/entry-exit/traffic', params={'period': 'bogus'})).status_code, 422)

    async def test_traffic_grouping_has_no_distinct_odbc_parameter_expressions(self):
        # The production failure occurs before rows are read, even on an empty day.
        self.db.execute('CREATE TABLE entry_exit_log (event_time TEXT, gate TEXT, is_test INTEGER)')
        for period, count in [('daily', 24), ('weekly', 7), ('monthly', 30)]:
            with self.subTest(period=period):
                with patch.object(entry_exit, 'rows', wraps=self.rows) as query:
                    response = await self.client.get('/entry-exit/traffic', params={'period': period})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(len(response.json()), count)
                self.assertTrue(all(b['entries'] == b['exits'] == 0 for b in response.json()))
                sql = query.call_args.args[1]
                compiled = text(sql).compile(dialect=MSDialect_pyodbc(paramstyle='qmark'))
                # SQLite accepts the old query. Inspect actual ODBC SQL to catch
                # repeated parameterized grouping expressions that it cannot reject.
                grouping = str(compiled).upper().split('GROUP BY', 1)[1]
                self.assertNotIn('?', grouping)
                self.assertNotIn('EVENT_TIME', grouping)
