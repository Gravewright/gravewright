"""Projection admission keeps ordering, authorization and cancellation boundaries."""

import asyncio
import gc
import threading
import weakref
from unittest.mock import AsyncMock, patch

from django.test import SimpleTestCase, TransactionTestCase, override_settings

from gravewright.realtime import metrics, projection_reads
from gravewright.realtime.consumers import TableConsumer
from gravewright.realtime.models import PresenceConnection
from gravewright.realtime.tests import test_socket_lanes as socket_fixtures
from gravewright.tokens import services as token_services


@override_settings(GRAVEWRIGHT_REALTIME_PROJECTION_CONCURRENCY=2)
class ProjectionReadTests(SimpleTestCase):
    async def test_shared_limit_bounds_work_from_independent_callers(self):
        active, peak = 0, 0
        entered, release = asyncio.Event(), asyncio.Event()

        async def work():
            nonlocal active, peak
            active += 1
            peak = max(active, peak)
            if active == 2:
                entered.set()
            await release.wait()
            active -= 1
            return 'state'

        jobs = [asyncio.create_task(projection_reads.read(work, AsyncMock(return_value=True))) for _ in range(5)]
        try:
            await asyncio.wait_for(entered.wait(), 2)
            await asyncio.sleep(0)
            self.assertEqual(active, 2)
        finally:
            release.set()
        self.assertEqual(await asyncio.gather(*jobs), ['state'] * 5)
        self.assertEqual(peak, 2)

    @override_settings(GRAVEWRIGHT_REALTIME_PROJECTION_CONCURRENCY=0)
    async def test_zero_disables_admission_without_disabling_authorization(self):
        entered, release = [], asyncio.Event()

        async def work():
            entered.append(True)
            await release.wait()
            return 'state'

        jobs = [asyncio.create_task(projection_reads.read(work, AsyncMock(return_value=True))) for _ in range(5)]
        try:
            await asyncio.sleep(0)
            self.assertEqual(len(entered), 5)
            denied = AsyncMock()
            self.assertIs(await projection_reads.read(denied, AsyncMock(return_value=False)), projection_reads.DENIED)
            denied.assert_not_awaited()
        finally:
            release.set()
            await asyncio.gather(*jobs)

    @override_settings(GRAVEWRIGHT_REALTIME_PROJECTION_CONCURRENCY=1)
    async def test_cancelled_waiter_does_not_start_work_or_leak_permit(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def blocked():
            entered.set()
            await release.wait()

        first = asyncio.create_task(projection_reads.read(blocked, AsyncMock(return_value=True)))
        try:
            await asyncio.wait_for(entered.wait(), 2)
            work = AsyncMock()
            waiting = asyncio.create_task(projection_reads.read(work, AsyncMock(return_value=True)))
            await asyncio.sleep(0)
            waiting.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await waiting
            work.assert_not_awaited()
        finally:
            release.set()
            await first
        self.assertEqual(await projection_reads.read(AsyncMock(return_value='next'), AsyncMock(return_value=True)), 'next')

    @override_settings(GRAVEWRIGHT_REALTIME_PROJECTION_CONCURRENCY=1)
    async def test_cancelled_running_sync_read_keeps_slot_until_thread_finishes(self):
        loop = asyncio.get_running_loop()
        entered, next_entered = asyncio.Event(), asyncio.Event()
        release = threading.Event()

        def blocked():
            loop.call_soon_threadsafe(entered.set)
            if not release.wait(5):
                raise TimeoutError('The test did not release the reader.')
            return 'old'

        async def next_read():
            next_entered.set()
            return 'new'

        first = asyncio.create_task(projection_reads.read(
            metrics.database_sync_to_async(blocked, thread_sensitive=False), AsyncMock(return_value=True)))
        following = None
        try:
            await asyncio.wait_for(entered.wait(), 2)
            first.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(first, .5)
            following = asyncio.create_task(projection_reads.read(next_read, AsyncMock(return_value=True)))
            await asyncio.sleep(.02)
            self.assertFalse(next_entered.is_set())
        finally:
            release.set()
            if following is not None:
                self.assertEqual(await asyncio.wait_for(following, 2), 'new')
            await asyncio.gather(first, return_exceptions=True)

    @override_settings(GRAVEWRIGHT_REALTIME_PROJECTION_CONCURRENCY=1)
    async def test_reauthorization_after_wait_prevents_read_and_returns_permit(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def blocked():
            entered.set()
            await release.wait()

        first = asyncio.create_task(projection_reads.read(blocked, AsyncMock(return_value=True)))
        await asyncio.wait_for(entered.wait(), 2)
        authorized = AsyncMock(return_value=True)
        work = AsyncMock()
        waiting = asyncio.create_task(projection_reads.read(work, authorized))
        await asyncio.sleep(0)
        authorized.return_value = False
        release.set()
        try:
            self.assertIs(await asyncio.wait_for(waiting, 2), projection_reads.DENIED)
            work.assert_not_awaited()
            self.assertEqual(await projection_reads.read(AsyncMock(return_value='next'), AsyncMock(return_value=True)), 'next')
        finally:
            release.set()
            await first

    @override_settings(GRAVEWRIGHT_REALTIME_PROJECTION_CONCURRENCY=1)
    async def test_failed_and_abandoned_reads_release_slots_and_report_errors(self):
        error = RuntimeError('synthetic failure')
        with self.assertRaisesRegex(RuntimeError, 'synthetic failure'):
            await projection_reads.read(AsyncMock(side_effect=error), AsyncMock(return_value=True))
        entered, release = asyncio.Event(), asyncio.Event()

        async def blocked():
            entered.set()
            await release.wait()
            raise error

        job = asyncio.create_task(projection_reads.read(blocked, AsyncMock(return_value=True)))
        await asyncio.wait_for(entered.wait(), 2)
        job.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await job
        with self.assertLogs(projection_reads.logger, 'ERROR') as logs:
            release.set()
            self.assertEqual(await projection_reads.read(AsyncMock(return_value='next'), AsyncMock(return_value=True)), 'next')
        self.assertIn('recipient stopped waiting', logs.output[0])

    def test_contended_gates_do_not_leak_or_cross_event_loops(self):
        async def exercise():
            gate = projection_reads.gate_for_loop(1)
            entered, release = asyncio.Event(), asyncio.Event()

            async def blocked():
                entered.set()
                await release.wait()

            first = asyncio.create_task(gate.read(blocked, AsyncMock(return_value=True)))
            await entered.wait()
            second = asyncio.create_task(gate.read(AsyncMock(return_value='next'), AsyncMock(return_value=True)))
            await asyncio.sleep(0)
            release.set()
            self.assertEqual((await asyncio.gather(first, second))[1], 'next')
            return weakref.ref(asyncio.get_running_loop()), weakref.ref(gate)

        references = [asyncio.run(exercise()), asyncio.run(exercise())]
        gc.collect()
        self.assertTrue(all(reference() is None for pair in references for reference in pair))


@override_settings(GRAVEWRIGHT_REALTIME_PROJECTION_CONCURRENCY=1)
class ConsumerProjectionReadTests(SimpleTestCase):
    def consumer(self):
        consumer = TableConsumer()
        consumer.campaign_id = 'campaign'
        consumer.user_id = 'user'
        consumer.token_map_id = 'scene'
        consumer.socket_closed = asyncio.Event()
        consumer.authorized = AsyncMock(return_value=True)
        consumer.emit_projection = AsyncMock()
        consumer.notify_api = AsyncMock()
        return consumer

    async def test_revoked_access_during_read_prevents_delivery(self):
        consumer = self.consumer()

        def read(*args):
            consumer.authorized.return_value = False
            return {'mapId': 'scene', 'tokens': []}

        with patch('gravewright.tokens.services.state', side_effect=read):
            await consumer.room_tokens({'refresh_audio': False, 'refresh_combat': False})
        consumer.emit_projection.assert_not_awaited()

    async def test_projection_lock_keeps_subscription_unchanged_through_read_and_send(self):
        consumer = self.consumer()
        entered, release = asyncio.Event(), asyncio.Event()
        switched = asyncio.Event()

        async def hold_send(*args):
            entered.set()
            await release.wait()

        async def switch():
            async with consumer.projection('tokens'):
                consumer.token_map_id = 'other'
                switched.set()

        consumer.emit_projection.side_effect = hold_send
        with patch('gravewright.tokens.services.state', return_value={'mapId': 'scene', 'tokens': []}):
            delivery = asyncio.create_task(consumer.room_tokens({'refresh_audio': False, 'refresh_combat': False}))
            await asyncio.wait_for(entered.wait(), 2)
            change = asyncio.create_task(switch())
            try:
                await asyncio.sleep(0)
                self.assertFalse(switched.is_set())
                self.assertEqual(consumer.token_map_id, 'scene')
            finally:
                release.set()
                await asyncio.gather(delivery, change)
        self.assertEqual(consumer.token_map_id, 'other')


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
                   GRAVEWRIGHT_HEARTBEAT_SECONDS=.1, GRAVEWRIGHT_PRESENCE_TTL=20,
                   GRAVEWRIGHT_REALTIME_PROJECTION_CONCURRENCY=1, ALLOWED_HOSTS=['testserver'])
class ProjectionReadSocketTests(TransactionTestCase):
    setUp = socket_fixtures.SocketLaneTests.setUp
    tearDown = socket_fixtures.SocketLaneTests.tearDown
    socket = socket_fixtures.SocketLaneTests.socket
    event = socket_fixtures.SocketLaneTests.event
    finish = socket_fixtures.SocketLaneTests.finish
    joined = socket_fixtures.SocketLaneTests.joined
    publish = socket_fixtures.SocketLaneTests.publish

    async def test_disconnect_leaves_read_running_without_blocking_loop_or_releasing_slot(self):
        loop = asyncio.get_running_loop()
        entered, finished, next_entered = asyncio.Event(), asyncio.Event(), asyncio.Event()
        release = threading.Event()
        real = token_services.state

        def read(campaign, user, scene):
            if user == self.gm.pk:
                loop.call_soon_threadsafe(entered.set)
                try:
                    if not release.wait(8):
                        raise TimeoutError('The test did not release the projection.')
                    return real(campaign, user, scene)
                finally:
                    loop.call_soon_threadsafe(finished.set)
            loop.call_soon_threadsafe(next_entered.set)
            return real(campaign, user, scene)

        # A separate thread bounds failures even if executor cleanup were to block
        # the event loop; the assertion below then rejects the delayed disconnect.
        watchdog = threading.Timer(5, release.set)
        watchdog.daemon = True
        try:
            gm = await self.joined(self.gm, ('tokens.sync', 'tokens.state'))
            player = await self.joined(self.player)
            with patch.object(token_services, 'state', side_effect=read):
                await self.publish({'type': 'room.tokens', 'refresh_audio': False, 'refresh_combat': False})
                await asyncio.wait_for(entered.wait(), 2)
                watchdog.start()
                await player.send_json_to({'type': 'tokens.sync', 'payload': {'mapId': str(self.scene.pk)}})
                await gm.disconnect(timeout=2)
                self.sockets.remove(gm)
                self.assertFalse(release.is_set(), 'Disconnect must finish before the projection thread does.')
                self.assertEqual(await metrics.database_sync_to_async(PresenceConnection.objects.count)(), 1)
                await asyncio.sleep(.02)
                self.assertFalse(next_entered.is_set(), 'The abandoned read still owns the only permit.')
                release.set()
                await self.event(player, 'tokens.state')
                self.assertTrue(next_entered.is_set())
        finally:
            watchdog.cancel()
            release.set()
            if entered.is_set():
                await asyncio.wait_for(finished.wait(), 3)
            await self.finish()
