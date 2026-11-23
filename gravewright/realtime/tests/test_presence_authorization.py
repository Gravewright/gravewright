"""Authorization expiry does not advance a still-fresh presence lease."""

import asyncio
from time import monotonic
from unittest.mock import AsyncMock, patch

from channels.db import database_sync_to_async as db
from django.contrib.sessions.models import Session
from django.db import OperationalError
from django.test import TransactionTestCase, override_settings

from gravewright.realtime import services
from gravewright.realtime.models import PresenceConnection
from gravewright.realtime.tests import test_scene_update_priority as priority


class OnePong:
    """Stop the lane after one pong without waiting for a timer."""

    used = False

    async def wait(self):
        if self.used:
            raise asyncio.CancelledError
        self.used = True

    def clear(self):
        pass


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   ALLOWED_HOSTS=['testserver'], GRAVEWRIGHT_PRESENCE_TTL=20)
class PresenceAuthorizationTests(TransactionTestCase):
    setUp = priority.SceneUpdatePriorityTests.setUp
    consumer = priority.SceneUpdatePriorityTests.consumer

    async def peer(self):
        peer = self.consumer(self.player)
        peer.member = self.player_membership
        peer.connection_id = await db(services.arrive)(peer.member)
        peer.lease_renew_after = monotonic() + 10
        peer.authorization = None
        peer.publish_presence = AsyncMock()
        return peer

    async def pong(self, peer):
        peer.presence_due = OnePong()
        try:
            await peer.presence_lane()
        except asyncio.CancelledError:
            pass

    async def test_expired_authorization_revalidates_without_extending_fresh_lease(self):
        peer = await self.peer()
        due = peer.lease_renew_after
        lease = await db(PresenceConnection.objects.get)(pk=peer.connection_id)
        with patch.object(services, 'renew', wraps=services.renew) as renew, \
                patch.object(services, 'authorization', wraps=services.authorization) as authorize:
            await self.pong(peer)
            authorize.assert_called_once()
            renew.assert_not_called()
            self.assertTrue(peer.authorization_cached())
            self.assertEqual(peer.lease_renew_after, due)
            self.assertEqual((await db(PresenceConnection.objects.get)(pk=peer.connection_id)).expires_at,
                             lease.expires_at)
            # Once due, cached authorization still permits the actual renewal.
            peer.lease_renew_after = 0
            await self.pong(peer)
            renew.assert_called_once_with(peer.connection_id, peer.member.pk)
            authorize.assert_called_once()
        self.assertGreater(peer.lease_renew_after, monotonic())
        peer.publish_presence.assert_not_awaited()
        peer.close.assert_not_awaited()

    async def test_expired_session_closes_even_while_the_lease_is_fresh(self):
        peer = await self.peer()
        await db(Session.objects.filter(session_key=peer.session_key).delete)()
        with patch.object(services, 'renew', wraps=services.renew) as renew:
            await self.pong(peer)
            renew.assert_not_called()
        peer.close.assert_awaited_once_with(code=4403)

    async def test_removed_member_closes_even_while_the_lease_is_fresh(self):
        peer = await self.peer()
        await db(self.player_membership.delete)()
        with patch.object(services, 'renew', wraps=services.renew) as renew:
            await self.pong(peer)
            renew.assert_not_called()
        peer.close.assert_awaited_once_with(code=4403)

    async def test_busy_authorization_does_not_postpone_renewal(self):
        peer = await self.peer()
        due = peer.lease_renew_after
        with patch.object(services, 'authorization', side_effect=OperationalError('database is locked')):
            await self.pong(peer)
        self.assertEqual(peer.lease_renew_after, due)
        self.assertFalse(peer.authorization_cached())
        peer.close.assert_not_awaited()
        await self.pong(peer)
        self.assertTrue(peer.authorization_cached())
        self.assertEqual(peer.lease_renew_after, due)

    async def test_due_deleted_lease_is_recreated_and_announced(self):
        peer = await self.peer()
        await db(PresenceConnection.objects.filter(pk=peer.connection_id).delete)()
        peer.lease_renew_after = 0
        await self.pong(peer)
        self.assertTrue(await db(PresenceConnection.objects.filter(pk=peer.connection_id).exists)())
        peer.publish_presence.assert_awaited_once()
        peer.close.assert_not_awaited()
