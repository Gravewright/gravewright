"""The server scheduler runs without browsers and drains safely at shutdown."""

import asyncio
import os
import threading
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.test import override_settings

from gravewright.maps.delay_worker import DelayWorker, DelayWorkerMiddleware, process_pending


class DelayWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_repeated_passes_need_no_requests_and_notifications_use_the_host_loop(self):
        main_thread = threading.get_ident()
        done, seen = asyncio.Event(), []

        async def notify():
            seen.append(threading.get_ident())
            if len(seen) == 3:
                done.set()

        def process():
            async_to_sync(notify)()

        worker = DelayWorker(process, interval=.01)
        worker.start()
        task = worker.task
        worker.start()
        self.assertIs(worker.task, task)
        try:
            await asyncio.wait_for(done.wait(), 2)
        finally:
            await worker.stop()
        self.assertGreaterEqual(len(seen), 3)
        self.assertEqual(set(seen), {main_thread})
        self.assertIsNone(worker.task)

    async def test_shutdown_waits_for_the_current_transaction_to_finish(self):
        entered, release = threading.Event(), threading.Event()

        def process():
            entered.set()
            release.wait(timeout=3)

        worker = DelayWorker(process, interval=.01)
        worker.start()
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            stop = asyncio.create_task(worker.stop())
            await asyncio.sleep(.01)
            self.assertFalse(stop.done())
            release.set()
            await asyncio.wait_for(stop, 2)
        finally:
            release.set()
            await worker.stop()
        self.assertIsNone(worker.task)

    async def test_operational_errors_are_reported_and_do_not_abandon_the_worker(self):
        entered = asyncio.Event()

        async def notify():
            entered.set()

        def process():
            async_to_sync(notify)()
            raise OSError('synthetic database failure')

        worker = DelayWorker(process)
        with self.assertLogs('gravewright.maps.delay_worker', level='ERROR') as logs:
            worker.start()
            try:
                await asyncio.wait_for(entered.wait(), 2)
                await asyncio.sleep(.01)
                self.assertFalse(worker.task.done())
            finally:
                await worker.stop()
        self.assertIn('synthetic database failure', '\n'.join(logs.output))

    @override_settings(GRAVEWRIGHT_AUTOMATION_WORKER_ENABLED=False)
    async def test_explicitly_disabled_worker_never_starts(self):
        worker = DelayWorker(lambda: self.fail('Disabled worker ran'))
        worker.start()
        self.assertIsNone(worker.task)
        await worker.stop()

    async def test_asgi_lifespan_starts_once_and_stops_without_an_http_connection(self):
        events, messages = [], asyncio.Queue()

        class Worker:
            def start(self):
                events.append('start')

            async def stop(self):
                events.append('stop')

        async def unexpected(*args):
            self.fail('Lifespan was forwarded to HTTP routing')

        async def send(message):
            events.append(message['type'])

        with patch.object(DelayWorkerMiddleware, 'bind_daphne'):
            app = DelayWorkerMiddleware(unexpected, worker=Worker())
        messages.put_nowait({'type': 'lifespan.startup'})
        messages.put_nowait({'type': 'lifespan.shutdown'})
        await app({'type': 'lifespan'}, messages.get, send)
        self.assertEqual(events[:4], ['start', 'lifespan.startup.complete', 'stop', 'lifespan.shutdown.complete'])

    async def test_daphne_registers_startup_and_shutdown_without_starting_during_import(self):
        callbacks, shutdown, events = [], [], []

        class Worker:
            def start(self):
                events.append('start')

            async def stop(self):
                events.append('stop')

        async def application(scope, receive, send):
            events.append(scope['type'])

        reactor = SimpleNamespace(_asyncioEventloop=asyncio.get_running_loop(),
            callWhenRunning=callbacks.append, addSystemEventTrigger=lambda *args: shutdown.append(args))
        with patch.dict('sys.modules', {'twisted.internet.reactor': reactor}):
            app = DelayWorkerMiddleware(application, worker=Worker())
            await app({'type': 'http'}, None, None)
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(events, ['http'])
        callbacks[0]()
        await asyncio.sleep(0)
        self.assertEqual(events, ['http', 'start'])
        self.assertEqual(shutdown[0][:2], ('before', 'shutdown'))
        shutdown[0][2]()
        await asyncio.sleep(0)
        self.assertEqual(events, ['http', 'start', 'stop'])


class DelayConnectionTests(unittest.TestCase):
    def test_update_maintenance_keeps_waits_dormant_until_the_host_is_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            flag = Path(directory) / 'maintenance'
            flag.touch()
            with patch.dict(os.environ, {'GRAVEWRIGHT_MANAGED_STATE': directory}), \
                    patch('gravewright.maps.blueprint_delays.process_due_delays', return_value={}) as process:
                self.assertIsNone(process_pending())
                process.assert_not_called()
                flag.unlink()
                self.assertEqual(process_pending(), {})
                process.assert_called_once_with(limit=20)

    def test_each_pass_closes_its_database_connections_even_on_failure(self):
        with patch('gravewright.maps.delay_worker.close_old_connections') as before, \
                patch('gravewright.maps.delay_worker.connections.close_all') as after, \
                patch('gravewright.maps.blueprint_delays.process_due_delays', side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):
                process_pending()
        before.assert_called_once()
        after.assert_called_once()
