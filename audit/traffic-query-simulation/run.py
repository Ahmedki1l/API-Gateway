"""Synthetic HTTP simulation; SQLite execution plus actual ODBC compilation, not SQL Server."""
import asyncio
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from test_entry_exit_dates import EntryExitDateTests, entry_exit
from app.config import settings
from sqlalchemy import text
from sqlalchemy.dialects.mssql.pyodbc import MSDialect_pyodbc

async def main():
    harness = EntryExitDateTests()
    await harness.asyncSetUp()
    results = []
    try:
        harness.db.execute('CREATE TABLE entry_exit_log (event_time TEXT, gate TEXT, is_test INTEGER)')
        rng = random.Random(230926)
        # Fixed reproducible traffic, including both sides of a year boundary.
        origin = datetime(2026, 12, 1)
        events = [(origin + timedelta(seconds=rng.randrange(40 * 86400)),
                   rng.choice(['entry', 'exit']), int(rng.random() < 0.1)) for _ in range(4000)]
        for now in [datetime(2027, 1, 1, 7, 59, 59), datetime(2027, 1, 1, 8),
                    datetime(2027, 1, 1, 23, 59, 59)]:
            for start_hour in [0, 8, 23]:
                for period, count in [('daily', 24), ('weekly', 7), ('monthly', 30)]:
                    start = now.replace(hour=start_hour if period == 'daily' else 0, minute=0, second=0)
                    if period == 'daily':
                        if now < start:
                            start -= timedelta(days=1)
                        step = timedelta(hours=1)
                    else:
                        start -= timedelta(days=count - 1)
                        step = timedelta(days=1)
                    end = start + count * step
                    boundary_events = [(start-timedelta(seconds=1), 'entry', 0),
                        (start, 'entry', 0), (start, 'exit', 0),
                        (end-timedelta(seconds=1), 'exit', 0), (end, 'entry', 0),
                        (start, 'entry', 1)]
                    for empty in [False, True]:
                        sample = [] if empty else events + boundary_events
                        harness.db.execute('DELETE FROM entry_exit_log')
                        harness.db.executemany('INSERT INTO entry_exit_log VALUES (?,?,?)',
                            [(t.isoformat(' '), gate, test) for t, gate, test in sample])
                        expected = [{'entries': 0, 'exits': 0} for _ in range(count)]
                        for timestamp, gate, test in sample:
                            if not test and start <= timestamp < end:
                                expected[(timestamp-start)//step]['entries' if gate == 'entry' else 'exits'] += 1
                        with patch.object(entry_exit, 'facility_now_naive', return_value=now), \
                             patch.object(settings, 'traffic_day_start_hour', start_hour), \
                             patch.object(entry_exit, 'rows', wraps=harness.rows) as query:
                            response = await harness.client.get('/entry-exit/traffic', params={'period': period})
                        assert response.status_code == 200, response.text
                        actual = response.json()
                        assert len(actual) == count
                        assert [{'entries': b['entries'], 'exits': b['exits']} for b in actual] == expected
                        assert len({b['label'] for b in actual}) == count
                        compiled = str(text(query.call_args.args[1]).compile(dialect=MSDialect_pyodbc(paramstyle='qmark')))
                        assert '?' not in compiled.upper().split('GROUP BY', 1)[1]
                        results.append({'period': period, 'now': now.isoformat(), 'start_hour': start_hour,
                            'empty': empty, 'events': len(sample), 'buckets': count, 'status': response.status_code,
                            'entries': sum(b['entries'] for b in actual), 'exits': sum(b['exits'] for b in actual)})
        report = {'backend': 'SQLite with DATEDIFF adapter; pyodbc dialect compilation',
                  'real_sql_server_execution': False, 'seed': 230926, 'passed': len(results), 'cases': results}
        Path(__file__).with_name('results.json').write_text(json.dumps(report, indent=2)+'\n')
        print(f'PASS: {len(results)} HTTP simulations; all bucket counts match independent expectations.')
    finally:
        await harness.asyncTearDown()
        harness.doCleanups()

asyncio.run(main())
