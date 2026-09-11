import asyncio
from datetime import timedelta
import uuid

from channels.db import database_sync_to_async as db
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import Client, TransactionTestCase, override_settings
from django.utils import timezone

from config.asgi import application
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.chat.models import Message
from gravewright.realtime.models import PresenceConnection


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
                   GRAVEWRIGHT_HEARTBEAT_SECONDS=.1, GRAVEWRIGHT_PRESENCE_TTL=2,
                   ALLOWED_HOSTS=['testserver'])
class SocketTests(TransactionTestCase):
    def setUp(self):
        self.gm = User.objects.create_user('gm@example.test', 'password-12345', name='GM', role='owner')
        self.player = User.objects.create_user('player@example.test', 'password-12345', name='Player')
        self.outsider = User.objects.create_user('outsider@example.test', 'password-12345', name='Other')
        self.campaign = Campaign.objects.create(owner=self.gm, name='Main table')
        self.other = Campaign.objects.create(owner=self.gm, name='Other table')
        Membership.objects.create(campaign=self.campaign, user=self.gm, role='gm')
        self.player_member = Membership.objects.create(campaign=self.campaign, user=self.player)
        Membership.objects.create(campaign=self.other, user=self.outsider)
        self.cookies = {}
        self.sessions = {}
        for user in (self.gm, self.player, self.outsider):
            client = Client()
            client.force_login(user)
            self.sessions[user.pk] = client.session.session_key
            self.cookies[user.pk] = f'{settings.SESSION_COOKIE_NAME}={client.cookies[settings.SESSION_COOKIE_NAME].value}'.encode()
        self.sockets = []

    def socket(self, user=None, campaign=None, origin=b'http://testserver'):
        headers = [(b'host', b'testserver')]
        if origin is not None:
            headers.append((b'origin', origin))
        if user:
            headers.append((b'cookie', self.cookies[user.pk]))
        socket = WebsocketCommunicator(application, f'/ws/tables/{(campaign or self.campaign).pk}/', headers=headers)
        self.sockets.append(socket)
        return socket

    async def event(self, socket, kind, predicate=lambda p: True):
        for _ in range(100):
            result = await socket.receive_json_from(timeout=3)
            if result['type'] == 'session.ping':
                await socket.send_json_to({'type': 'session.pong'})
            elif result['type'] == kind and predicate(result['payload']):
                return result['payload']
        self.fail(f'No {kind} event matched')

    async def finish(self):
        for socket in self.sockets:
            await socket.disconnect()

    async def test_handshake_rejects_anonymous_foreign_origin_and_nonmembers(self):
        try:
            for socket in [self.socket(), self.socket(self.outsider), self.socket(self.gm, origin=b'https://evil.test'),
                           self.socket(self.gm, origin=None), self.socket(self.gm, origin=b'http://testserver:9999')]:
                accepted, code = await socket.connect(timeout=5)
                self.assertFalse(accepted)
                self.assertEqual(code, 4403)
        finally:
            await self.finish()
        self.assertEqual(await db(PresenceConnection.objects.count)(), 0)

    @override_settings(GRAVEWRIGHT_PUBLIC_ORIGIN='https://testserver')
    async def test_public_https_origin_preserves_session_and_membership_checks(self):
        try:
            for socket in (self.socket(origin=b'https://testserver'),
                           self.socket(self.outsider, origin=b'https://testserver')):
                self.assertEqual(await socket.connect(timeout=5), (False, 4403))
            gm = self.socket(self.gm, origin=b'https://testserver')
            self.assertTrue((await gm.connect(timeout=5))[0])
            await self.event(gm, 'table.joined')
        finally:
            await self.finish()

    async def test_presence_deduplicates_tabs_and_removes_last_connection(self):
        gm, one, two = self.socket(self.gm), self.socket(self.player), self.socket(self.player)
        try:
            for socket in (gm, one, two):
                self.assertTrue((await socket.connect(timeout=5))[0])
                await self.event(socket, 'table.joined')
            payload = await self.event(gm, 'table.presence', lambda p: len(p['members']) == 2)
            self.assertEqual([m['name'] for m in payload['members']], ['GM', 'Player'])
            self.assertEqual([m['role'] for m in payload['members']], ['gm', 'player'])
            self.assertNotIn('email', str(payload))
            await one.disconnect(); self.sockets.remove(one)
            self.assertEqual(len((await self.event(gm, 'table.presence'))['members']), 2)
            await two.disconnect(); self.sockets.remove(two)
            payload = await self.event(gm, 'table.presence', lambda p: len(p['members']) == 1)
            self.assertEqual(payload['members'][0]['name'], 'GM')
        finally:
            await self.finish()
        self.assertEqual(await db(PresenceConnection.objects.count)(), 0)

    async def test_chat_history_escaping_idempotence_and_campaign_isolation(self):
        gm, player, outsider = self.socket(self.gm), self.socket(self.player), self.socket(self.outsider, self.other)
        try:
            for socket in (gm, player, outsider):
                self.assertTrue((await socket.connect(timeout=5))[0])
                await self.event(socket, 'chat.history')
            request_id = str(uuid.uuid4())
            command = {'type': 'chat.say', 'payload': {'text': '<img src=x onerror=alert(1)>', 'requestId': request_id,
                                                       'from': {'name': 'FORGED'}}}
            await player.send_json_to(command)
            entry = await self.event(gm, 'chat.message')
            self.assertEqual(entry['from']['name'], 'Player')
            self.assertIn('&lt;img', entry['html'])
            self.assertNotIn('<img', entry['html'])
            ack = await self.event(player, 'chat.ack')
            self.assertEqual(ack['message']['id'], entry['id'])
            await player.send_json_to(command)
            await self.event(player, 'chat.ack')
            self.assertEqual(await db(Message.objects.count)(), 1)
            await outsider.send_json_to({'type': 'chat.sync'})
            self.assertEqual((await self.event(outsider, 'chat.history'))['messages'], [])
            await player.disconnect(); self.sockets.remove(player)
            reconnect = self.socket(self.player)
            self.assertTrue((await reconnect.connect(timeout=5))[0])
            self.assertEqual((await self.event(reconnect, 'chat.history'))['messages'][0]['id'], entry['id'])
        finally:
            await self.finish()

    async def test_validation_flood_limit_and_cross_campaign_commands(self):
        socket = self.socket(self.player)
        try:
            self.assertTrue((await socket.connect(timeout=5))[0])
            await self.event(socket, 'table.joined')
            await socket.send_to(text_data='{bad json')
            self.assertEqual((await self.event(socket, 'error'))['code'], 'invalid_input')
            for text in ['', ' ', 'x' * 2001, ['bad']]:
                await socket.send_json_to({'type': 'chat.say', 'payload': {'text': text, 'requestId': str(uuid.uuid4())}})
                await self.event(socket, 'error')
            await socket.send_json_to({'type': 'chat.say', 'payload': {'text': 'Forbidden', 'requestId': str(uuid.uuid4()), 'tableId': str(self.other.pk)}})
            self.assertEqual((await self.event(socket, 'error'))['code'], 'not_a_member')
            for index in range(20):
                await socket.send_json_to({'type': 'chat.say', 'payload': {'text': f'Message {index}', 'requestId': str(uuid.uuid4())}})
                await self.event(socket, 'chat.ack')
            await socket.send_json_to({'type': 'chat.say', 'payload': {'text': 'Too fast', 'requestId': str(uuid.uuid4())}})
            self.assertEqual((await self.event(socket, 'error'))['code'], 'too_many_messages')
            self.assertEqual(await db(Message.objects.count)(), 20)
        finally:
            await self.finish()

    async def test_open_socket_loses_access_when_session_or_membership_changes(self):
        for mutation in ('logout', 'password', 'membership'):
            socket = self.socket(self.player)
            self.assertTrue((await socket.connect(timeout=5))[0])
            await self.event(socket, 'chat.history')
            if mutation == 'logout':
                await db(Session.objects.filter(session_key=self.sessions[self.player.pk]).update)(expire_date=timezone.now()-timedelta(seconds=1))
            elif mutation == 'password':
                await db(User.objects.filter(pk=self.player.pk).update)(password='changed')
            else:
                await db(Membership.objects.filter(pk=self.player_member.pk).delete)()
            # Buffered non-sensitive presence events may precede the close frame.
            for _ in range(30):
                frame = await socket.receive_output(timeout=3)
                if frame['type'] == 'websocket.close':
                    self.assertEqual(frame['code'], 4403)
                    break
            else:
                self.fail('Revoked socket stayed connected')
            await socket.disconnect(); self.sockets.remove(socket)
            if mutation != 'membership':
                def login_again():
                    self.player.refresh_from_db()
                    client = Client(); client.force_login(self.player)
                    self.sessions[self.player.pk] = client.session.session_key
                    self.cookies[self.player.pk] = f'{settings.SESSION_COOKIE_NAME}={client.cookies[settings.SESSION_COOKIE_NAME].value}'.encode()
                await db(login_again)()
        self.assertEqual(await db(PresenceConnection.objects.count)(), 0)

    async def test_expired_lease_does_not_appear_online(self):
        PresenceConnectionCreate = db(PresenceConnection.objects.create)
        await PresenceConnectionCreate(membership_id=self.player_member.pk, expires_at=timezone.now()-timedelta(seconds=1))
        gm = self.socket(self.gm)
        try:
            self.assertTrue((await gm.connect(timeout=5))[0])
            payload = await self.event(gm, 'table.presence')
            self.assertEqual([m['name'] for m in payload['members']], ['GM'])
        finally:
            await self.finish()

    async def test_history_returns_only_latest_hundred_in_order(self):
        await db(Message.objects.bulk_create)([
            Message(campaign=self.campaign, author=self.gm, author_name='GM',
                    text=f'Line {index}', request_id=uuid.uuid4()) for index in range(105)
        ])
        socket = self.socket(self.player)
        try:
            self.assertTrue((await socket.connect())[0])
            entries = (await self.event(socket, 'chat.history'))['messages']
            self.assertEqual(len(entries), 100)
            self.assertEqual(entries[0]['text'], 'Line 5')
            self.assertEqual(entries[-1]['text'], 'Line 104')
            self.assertEqual(await db(Message.objects.count)(), 105)
        finally:
            await self.finish()

    async def test_unresponsive_client_is_closed_and_lease_removed(self):
        socket = self.socket(self.player)
        try:
            self.assertTrue((await socket.connect())[0])
            # Consume ping frames without answering: simulate a suspended client.
            for _ in range(100):
                frame = await socket.receive_output(timeout=3)
                if frame['type'] == 'websocket.close':
                    self.assertEqual(frame['code'], 4000)
                    break
            else:
                self.fail('Client without heartbeat remained connected')
        finally:
            await self.finish()
        self.assertEqual(await db(PresenceConnection.objects.count)(), 0)
