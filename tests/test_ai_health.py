"""Offline regression checks for the dashboard's exact-HTTP-200 contract.

Run: python -m unittest discover -s tests -p 'test_ai_health.py'
Only upstream HTTP and the unused DB engine are replaced at I/O boundaries.
"""
import asyncio
import base64
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import httpx
from fastapi import FastAPI

with patch.dict(os.environ, {
    'CAMERAS_ENCRYPTION_KEY': base64.urlsafe_b64encode(bytes(32)).decode(),
    'CAMERAS_INTERNAL_TOKEN': 'health-test-unused',
    'SYSTEM1_BASE_URL': 'http://pms.test',
    'SYSTEM2_BASE_URL': 'http://va.test',
    'PREFIX': '',
}):
    # The dashboard module also defines SQL-backed endpoints, but this route
    # must never create a database connection during the health tests.
    with patch('sqlalchemy.create_engine'):
        from app.routers import dashboard
        from app.services import upstream


class AIHealthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.responses = {
            'pms.test': httpx.Response(200, json={'status': 'ok'}),
            'va.test': httpx.Response(200, json={'status': 'ok'}),
        }
        self.seen = []

        async def respond(request):
            self.seen.append((request.url.host, request.url.path))
            response = self.responses[request.url.host]
            if isinstance(response, Exception):
                raise response
            return response

        self.pms = httpx.AsyncClient(base_url='http://pms.test', transport=httpx.MockTransport(respond))
        self.va = httpx.AsyncClient(base_url='http://va.test', transport=httpx.MockTransport(respond))
        self.patches = [patch.object(upstream, '_system1', self.pms),
                        patch.object(upstream, '_system2', self.va),
                        patch.object(upstream, '_system1_last_connected_at', None),
                        patch.object(upstream, '_system2_last_connected_at', None)]
        for replacement in self.patches:
            replacement.start()
            self.addCleanup(replacement.stop)
        app = FastAPI()
        app.include_router(dashboard.router)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://gateway.test')

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.pms.aclose()
        await self.va.aclose()

    async def snapshot(self):
        response = await self.client.get('/dashboard/ai-status')
        self.assertEqual(response.status_code, 200)
        return response.json()

    async def test_http_200_passes_independently_of_body(self):
        for response in [httpx.Response(200, json={'status': 'degraded', 'failures': ['ignored']}),
                         httpx.Response(200, json={'status': ['invalid'], 'timestamp': {'invalid': True}}),
                         httpx.Response(200, text='not JSON')]:
            with self.subTest(body=response.text):
                self.responses['pms.test'] = response
                result = await self.snapshot()
                self.assertEqual(result['overall_health'], 'healthy')
                self.assertEqual(result['issues'], [])
                self.assertTrue(all(s['health'] == 'healthy' for s in result['systems']))

    async def test_non_200_never_passes_even_with_ok_body(self):
        for code in [201, 204, 302, 401, 500, 503]:
            with self.subTest(code=code):
                self.responses['va.test'] = httpx.Response(code, json={'status': 'ok'})
                result = await self.snapshot()
                self.assertEqual(result['overall_health'], 'degraded')
                self.assertEqual(result['systems'][0]['health'], 'healthy')
                self.assertEqual(result['systems'][1]['health'], 'unreachable')
                self.assertIn(str(code), result['issues'][0]['reason'])
                self.assertIsNone(result['systems'][1]['last_connected_at'])

    async def test_transport_failure_preserves_other_services_result(self):
        for exc in [httpx.ReadTimeout(''), httpx.ConnectError('connection failed')]:
            with self.subTest(error=type(exc).__name__):
                self.responses['pms.test'] = exc
                result = await self.snapshot()
                self.assertEqual(result['overall_health'], 'degraded')
                self.assertEqual(result['systems'][1]['health'], 'healthy')
                self.assertIn(type(exc).__name__, result['issues'][0]['reason'])
        self.responses['va.test'] = httpx.Response(503)
        self.assertEqual((await self.snapshot())['overall_health'], 'down')

    async def test_last_connection_only_tracks_http_200_health_checks(self):
        old = datetime(2026, 9, 1, tzinfo=timezone.utc)
        upstream._system2_last_connected_at = old
        await upstream.get_live_vehicles()
        await upstream.get_live_slots()
        await upstream.get_system2_stats()
        self.assertEqual(upstream.get_system2_last_connected_at(), old)
        self.responses['va.test'] = httpx.Response(503)
        await self.snapshot()
        self.assertEqual(upstream.get_system2_last_connected_at(), old)
        self.responses['va.test'] = httpx.Response(200, json={'status': 'unhealthy'})
        result = await self.snapshot()
        self.assertEqual(result['overall_health'], 'healthy')
        self.assertGreater(upstream.get_system2_last_connected_at(), old)

    async def test_both_probes_start_before_either_finishes(self):
        started = set()
        both_started = asyncio.Event()

        async def barrier(request):
            started.add(request.url.host)
            if len(started) == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), timeout=1)
            return httpx.Response(200)

        async with httpx.AsyncClient(base_url='http://pms.test', transport=httpx.MockTransport(barrier)) as pms:
            async with httpx.AsyncClient(base_url='http://va.test', transport=httpx.MockTransport(barrier)) as va:
                with patch.object(upstream, '_system1', pms), patch.object(upstream, '_system2', va):
                    self.assertEqual((await self.snapshot())['overall_health'], 'healthy')
        self.assertEqual(started, {'pms.test', 'va.test'})

    async def test_stalled_probe_is_cancelled_at_deadline(self):
        cancelled = asyncio.Event()

        async def stall(request):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        async with httpx.AsyncClient(base_url='http://va.test', transport=httpx.MockTransport(stall)) as va:
            with patch.object(upstream, '_system2', va), patch.object(upstream, 'HEALTH_TIMEOUT', 0.05):
                result = await asyncio.wait_for(self.snapshot(), timeout=1)
        self.assertTrue(cancelled.is_set())
        self.assertEqual(result['systems'][0]['health'], 'healthy')
        self.assertEqual(result['systems'][1]['health'], 'unreachable')
        self.assertIn('TimeoutError', result['issues'][0]['reason'])
        self.assertIn(('pms.test', '/api/v1/health'), self.seen)


if __name__ == '__main__':
    unittest.main()
