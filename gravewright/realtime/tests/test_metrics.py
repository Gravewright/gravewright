"""Regression coverage for realtime observations without user-content logging."""

import asyncio
import os
from unittest.mock import patch

from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase, override_settings

from config.engine import configure
from gravewright.realtime import metrics


class MetricsConfigurationTests(SimpleTestCase):
    def test_default_disabled_and_invalid_thresholds(self):
        with patch.dict(os.environ):
            os.environ.pop('GRAVEWRIGHT_REALTIME_SLOW_MS', None)
            self.assertEqual(configure()['GRAVEWRIGHT_REALTIME_SLOW_MS'], 500)
        for value in ('0', '12'):
            with patch.dict(os.environ, {'GRAVEWRIGHT_REALTIME_SLOW_MS': value}):
                self.assertEqual(configure()['GRAVEWRIGHT_REALTIME_SLOW_MS'], int(value))
        for value in ('-1', 'invalid'):
            with patch.dict(os.environ, {'GRAVEWRIGHT_REALTIME_SLOW_MS': value}):
                with self.assertRaises(ValueError):
                    configure()

    @override_settings(GRAVEWRIGHT_REALTIME_SLOW_MS=10)
    def test_warning_includes_queue_sql_and_wire_cost_without_content(self):
        with patch.object(metrics, 'monotonic', side_effect=[2, 2.025]):
            with self.assertLogs(metrics.logger, 'WARNING') as logs:
                with metrics.handler('private message', arrived_at=1.9) as measured:
                    metrics.frame('á-secret')
                    metrics.database_busy()
        self.assertAlmostEqual(measured.queue_ms, 100)
        self.assertAlmostEqual(measured.handler_ms, 25)
        self.assertEqual((measured.frames, measured.bytes, measured.lock_errors), (1, 9, 1))
        output = ' '.join(logs.output)
        self.assertIn('database busy kind=handler', output)
        self.assertIn('sql_count=0', output)
        self.assertNotIn('private', output)
        self.assertNotIn('secret', output)

    @override_settings(GRAVEWRIGHT_REALTIME_SLOW_MS=0)
    def test_disable_slow_warning_keeps_busy_warning_and_restores_context(self):
        with self.assertLogs(metrics.logger, 'WARNING') as logs:
            with metrics.handler('command'):
                metrics.database_busy()
        self.assertEqual(len(logs.output), 1)
        self.assertIsNone(metrics._current.get())


class MetricsDatabaseTests(TransactionTestCase):
    @override_settings(GRAVEWRIGHT_REALTIME_SLOW_MS=0)
    async def test_queries_cross_thread_boundary_and_concurrent_handlers_stay_separate(self):
        def query():
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                return cursor.fetchone()[0]

        async def operation(count):
            with metrics.handler('command') as measured:
                for _ in range(count):
                    self.assertEqual(await metrics.database_sync_to_async(query)(), 1)
                    await asyncio.sleep(0)
                metrics.frame(b'{}')
            return measured

        first, second = await asyncio.gather(operation(1), operation(3))
        self.assertEqual((first.sql_count, second.sql_count), (1, 3))
        self.assertEqual((first.frames, second.frames), (1, 1))
        self.assertGreaterEqual(first.sql_ms, 0)
        self.assertIsNone(metrics._current.get())
