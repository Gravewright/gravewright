"""Presence leases: no write per pong, no global cleanup per pong, no vanishing sockets."""

import asyncio
from datetime import timedelta
import threading
from unittest.mock import patch
import uuid

from channels.db import database_sync_to_async as db
from django.db import connection
from django.test import TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from gravewright.realtime import consumers, services
from gravewright.realtime.models import PresenceConnection
from gravewright.realtime.tests import test_sockets as sockets


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
                   GRAVEWRIGHT_HEARTBEAT_SECONDS=.1, GRAVEWRIGHT_PRESENCE_TTL=2,
                   ALLOWED_HOSTS=['testserver'])
class PresenceLeaseTests(TransactionTestCase):
    setUp = sockets.SocketTests.setUp
    socket = sockets.SocketTests.socket
    event = sockets.SocketTests.event
    finish = sockets.SocketTests.finish

    def tearDown(self):
        consumers._last_lease_cleanup = 0.0

    async def joined(self, user):
        socket = self.socket(user)
        self.assertTrue((await socket.connect(timeout=5))[0])
        await self.event(socket, 'chat.history')
        return socket

    def test_renew_recreates_deleted_lease(self):
        lease = services.arrive(self.player_member)
        PresenceConnection.objects.filter(pk=lease).delete()
        self.assertTrue(services.renew(lease, self.player_member.pk))
        self.assertTrue(PresenceConnection.objects.filter(pk=lease, membership=self.player_member).exists())
        self.assertEqual([row['id'] for row in services.roster(self.campaign.pk)['members']], [str(self.player.pk)])
        self.assertFalse(services.renew(lease, self.player_member.pk))  # an existing lease is only extended

    def test_cleanup_reads_before_writing(self):
        services.arrive(self.player_member)
        with CaptureQueriesContext(connection) as queries:
            self.assertFalse(services.remove_expired())
        self.assertFalse([query for query in queries if query['sql'].startswith('DELETE')])
        PresenceConnection.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertTrue(services.remove_expired())
        self.assertFalse(PresenceConnection.objects.exists())

    async def test_pongs_in_the_first_half_of_a_lease_do_not_write(self):
        calls = []
        real = services.renew
        try:
            socket = await self.joined(self.player)
            with patch.object(services, 'renew', side_effect=lambda *a, **k: calls.append(a) or real(*a, **k)):
                for _ in range(5):  # within the first half of the 2-second test lease
                    await socket.send_json_to({'type': 'session.pong'})
                await asyncio.sleep(.2)
                self.assertEqual(calls, [])
                await asyncio.sleep(1)  # past half the lease: the next pong renews once
                await socket.send_json_to({'type': 'session.pong'})
                await socket.send_json_to({'type': 'session.pong'})
                await asyncio.sleep(.3)
            self.assertEqual(len(calls), 1)
        finally:
            await self.finish()

    async def test_pong_never_deletes_expired_rows(self):
        stale = await db(PresenceConnection.objects.create)(
            membership=self.player_member, expires_at=timezone.now() - timedelta(seconds=5))

        async def no_cleanup(consumer):
            return None
        try:
            # Only the pong path runs while upkeep cleanup is switched off.
            with patch.object(consumers.TableConsumer, 'remove_expired_leases', no_cleanup):
                socket = await self.joined(self.gm)
                await asyncio.sleep(1.1)  # past half the lease, so this pong renews
                await socket.send_json_to({'type': 'session.pong'})
                await asyncio.sleep(.3)
                self.assertTrue(await db(PresenceConnection.objects.filter(pk=stale.pk).exists)())
            # Heartbeat upkeep removes it.
            for _ in range(30):
                if not await db(PresenceConnection.objects.filter(pk=stale.pk).exists)():
                    break
                await asyncio.sleep(.1)
            self.assertFalse(await db(PresenceConnection.objects.filter(pk=stale.pk).exists)())
        finally:
            await self.finish()

    async def test_presence_survives_a_command_longer_than_the_ttl(self):
        entered, release = threading.Event(), threading.Event()

        def blocked(*_args, **_kwargs):
            entered.set()
            release.wait(10)
            return {'tokens': []}
        try:
            player = await self.joined(self.player)
            gm = await self.joined(self.gm)
            with patch('gravewright.tokens.services.command', side_effect=blocked):
                await player.send_json_to({'type': 'tokens.command', 'payload': {
                    'requestId': str(uuid.uuid4()), 'action': 'move', 'data': {}}})
                self.assertTrue(await asyncio.to_thread(entered.wait, 5))
                # Longer than the 2-second lease; pongs keep flowing and the GM's
                # upkeep keeps removing expired leases.
                for _ in range(15):
                    await player.send_json_to({'type': 'session.pong'})
                    consumers._last_lease_cleanup = 0.0
                    await asyncio.sleep(.2)
                release.set()
                await self.event(player, 'tokens.ack')
            presence = await self.event(gm, 'table.presence', lambda p: len(p['members']) == 2)
            self.assertEqual({row['id'] for row in presence['members']}, {str(self.gm.pk), str(self.player.pk)})
        finally:
            release.set()
            await self.finish()

    async def test_depart_removes_lease_and_publishes(self):
        try:
            gm = await self.joined(self.gm)
            player = await self.joined(self.player)
            await self.event(gm, 'table.presence', lambda p: len(p['members']) == 2)
            await player.disconnect()
            self.sockets.remove(player)
            presence = await self.event(gm, 'table.presence', lambda p: len(p['members']) == 1)
            self.assertEqual([row['id'] for row in presence['members']], [str(self.gm.pk)])
            self.assertEqual(await db(PresenceConnection.objects.filter(membership=self.player_member).count)(), 0)
        finally:
            await self.finish()

    async def test_second_socket_keeps_user_present(self):
        try:
            gm = await self.joined(self.gm)
            first, second = await self.joined(self.player), await self.joined(self.player)
            await first.disconnect()
            self.sockets.remove(first)
            await asyncio.sleep(.3)
            roster = await db(services.roster)(self.campaign.pk)
            self.assertIn(str(self.player.pk), [row['id'] for row in roster['members']])
            self.assertEqual(await db(PresenceConnection.objects.filter(membership=self.player_member).count)(), 1)
            await self.event(gm, 'table.presence', lambda p: str(self.player.pk) in str(p))
            await second.send_json_to({'type': 'api.watch'})
        finally:
            await self.finish()
