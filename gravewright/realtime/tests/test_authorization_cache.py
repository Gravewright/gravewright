"""Cached socket authorization: reused briefly, revoked immediately by access changes."""

import asyncio
from datetime import timedelta
from unittest.mock import patch

from channels.db import database_sync_to_async as db
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.test import Client, RequestFactory, TransactionTestCase, override_settings
from django.utils import timezone

from gravewright.accounts.models import User
from gravewright.actors.models import Actor
from gravewright.campaigns import streamer
from gravewright.campaigns.models import Campaign, Membership, StreamerLink
from gravewright.maps.models import Broadcast, Scene
from gravewright.realtime import access, consumers, dispatch, services
from gravewright.realtime.tests import test_sockets as sockets
from gravewright.tokens.models import Token


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
                   GRAVEWRIGHT_HEARTBEAT_SECONDS=.1, GRAVEWRIGHT_PRESENCE_TTL=60,
                   ALLOWED_HOSTS=['testserver'])
class AuthorizationCacheTests(TransactionTestCase):
    socket = sockets.SocketTests.socket
    event = sockets.SocketTests.event
    finish = sockets.SocketTests.finish

    def setUp(self):
        sockets.SocketTests.setUp(self)
        # The consumer's clock stands still: a cached authorization never expires by
        # itself, so every close below comes from an immediate invalidation.
        self.clock = Clock()
        self.enterContext(patch.object(consumers, 'monotonic', self.clock))
        real = services.authorization
        self.checks = []

        def authorization(*args, **kwargs):
            self.checks.append(args)
            return real(*args, **kwargs)
        self.enterContext(patch.object(services, 'authorization', side_effect=authorization))

    async def joined(self, user):
        socket = self.socket(user)
        self.assertTrue((await socket.connect(timeout=5))[0])
        await self.event(socket, 'chat.history')
        return socket

    async def closed_with(self, socket, seconds=2):
        loop = asyncio.get_running_loop()
        end = loop.time() + seconds
        while loop.time() < end:
            if await socket.receive_nothing(timeout=.05, interval=.01):
                await socket.send_json_to({'type': 'api.watch'})  # "the next frame"
                continue
            frame = await socket.receive_output(timeout=1)
            if frame['type'] == 'websocket.close':
                return frame.get('code')
            if 'session.ping' in frame.get('text', ''):
                await socket.send_json_to({'type': 'session.pong'})
        return None

    async def test_frames_within_ttl_reuse_authorization(self):
        try:
            socket = await self.joined(self.player)
            before = len(self.checks)
            for _ in range(10):
                await socket.send_json_to({'type': 'api.watch'})
            await socket.send_json_to({'type': 'lobby.sync'})
            await asyncio.sleep(.3)  # several heartbeat upkeeps also authorize
            self.assertEqual(len(self.checks), before)
        finally:
            await self.finish()

    async def test_ttl_expiry_revalidates(self):
        try:
            socket = await self.joined(self.player)
            before = len(self.checks)
            self.clock.now += consumers.AUTHORIZATION_TTL + .1
            await socket.send_json_to({'type': 'api.watch'})
            await asyncio.sleep(.2)
            self.assertGreater(len(self.checks), before)
        finally:
            await self.finish()

    async def assert_revocation_closes(self, user, change):
        socket = await self.joined(user)
        await db(change)()
        self.assertEqual(await self.closed_with(socket), 4403)
        await socket.disconnect()
        self.sockets.remove(socket)

    async def test_logout_closes_next_frame(self):
        def sign_out():
            request = RequestFactory().get('/')
            request.session = SessionStore(session_key=self.sessions[self.player.pk])
            request.user = User.objects.get(pk=self.player.pk)
            logout(request)
        await self.assert_revocation_closes(self.player, sign_out)

    async def test_session_delete_closes_next_frame(self):
        key = self.sessions[self.player.pk]
        await self.assert_revocation_closes(self.player, lambda: Session.objects.get(session_key=key).delete())

    async def test_password_change_closes_other_sessions(self):
        def change():
            user = User.objects.get(pk=self.player.pk)
            user.set_password('another-password-123')
            user.save()
        await self.assert_revocation_closes(self.player, change)

    async def test_membership_removed_closes_next_frame(self):
        await self.assert_revocation_closes(self.player, lambda: Membership.objects.filter(pk=self.player_member.pk).delete())

    async def test_user_deactivated_closes_next_frame(self):
        def deactivate():
            user = User.objects.get(pk=self.player.pk)
            user.is_active = False
            user.save()
        await self.assert_revocation_closes(self.player, deactivate)

    async def test_campaign_deleted_closes_next_frame(self):
        await self.assert_revocation_closes(self.player, lambda: Campaign.objects.get(pk=self.campaign.pk).delete())

    async def test_streamer_link_revoked_closes_next_frame(self):
        def guest():
            user = User.objects.create_user('cache-streamer@example.test', 'password-12345', name='Stream')
            Membership.objects.create(campaign=self.campaign, user=user, role='streamer')
            StreamerLink.objects.create(campaign=self.campaign, guest=user, digest='c' * 64,
                                        expires_at=timezone.now() + timedelta(hours=1))
            client = Client()
            client.force_login(user)
            self.cookies[user.pk] = (f'{settings.SESSION_COOKIE_NAME}='
                                     f'{client.cookies[settings.SESSION_COOKIE_NAME].value}').encode()
            return user
        user = await db(guest)()
        # streamer.revoke updates links with QuerySet.update and notifies explicitly.
        await self.assert_revocation_closes(user, lambda: streamer.revoke(self.gm, self.campaign.pk))

    async def test_session_expiry_is_checked_locally(self):
        key = self.sessions[self.player.pk]
        await db(Session.objects.filter(session_key=key).update)(expire_date=timezone.now() + timedelta(seconds=1))
        socket = await self.joined(self.player)
        await asyncio.sleep(1.2)
        # The TTL clock stands still; the cached session expiry still ends access.
        self.assertEqual(await self.closed_with(socket), 4403)
        await socket.disconnect()
        self.sockets.remove(socket)

    async def test_role_change_applies_to_next_projection(self):
        def scene():
            scene = Scene.objects.create(campaign=self.campaign, name='Room', width=512, height=512,
                                         visibility='players')
            Broadcast.objects.create(campaign=self.campaign, scene=scene)
            actor = Actor.objects.create(campaign=self.campaign, name='Ghost', data={}, permissions={})
            return scene, Token.objects.create(scene=scene, actor=actor, hidden=True)
        room, hidden = await db(scene)()
        try:
            socket = await self.joined(self.gm)
            await socket.send_json_to({'type': 'tokens.sync', 'payload': {'mapId': str(room.pk)}})
            state = await self.event(socket, 'tokens.state')
            self.assertIn(str(hidden.pk), str(state))

            def demote():
                member = Membership.objects.get(campaign=self.campaign, user=self.gm)
                member.role = 'player'
                member.save()
                dispatch.changed(self.campaign.pk, self.player.pk, 'tokens', 'configure', __import__('uuid').uuid4())
            await db(demote)()
            frame = await self.event(socket, 'tokens.state')
            self.assertEqual(frame['removes'], {'tokens': [str(hidden.pk)]})
        finally:
            await self.finish()

    async def test_cross_process_invalidation_event(self):
        try:
            await self.joined(self.player)
            before = len(self.checks)
            await get_channel_layer().group_send(access.user_group(self.player.pk), {'type': 'room.access'})
            await asyncio.sleep(.2)
            self.assertEqual(len(self.checks), before + 1)
        finally:
            await self.finish()
