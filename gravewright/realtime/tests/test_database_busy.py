"""SQLite contention keeps the socket open; the browser retries with the same request ID."""

import asyncio
from unittest.mock import patch
import uuid

from channels.db import database_sync_to_async as db
from channels.layers import get_channel_layer
from django.db import OperationalError
from django.test import TransactionTestCase, override_settings

from gravewright.actors.models import Actor
from gravewright.chat.models import Message
from gravewright.dice import services as dice
from gravewright.dice.models import Submission
from gravewright.maps.models import Receipt, Scene
from gravewright.realtime import metrics
from gravewright.realtime.models import PresenceConnection
from gravewright.realtime.tests import test_sockets as sockets
from gravewright.tokens import services as token_services
from gravewright.tokens.models import Token


def locked():
    return OperationalError('database is locked')


def once(then):
    """Fail the first call with SQLite contention, then delegate."""
    calls = []

    def side_effect(*args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            raise locked()
        return then(*args, **kwargs)
    return side_effect


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
                   GRAVEWRIGHT_HEARTBEAT_SECONDS=.1, GRAVEWRIGHT_PRESENCE_TTL=2,
                   ALLOWED_HOSTS=['testserver'])
class DatabaseBusyTests(TransactionTestCase):
    setUp = sockets.SocketTests.setUp
    socket = sockets.SocketTests.socket
    event = sockets.SocketTests.event
    finish = sockets.SocketTests.finish

    async def joined(self, user):
        socket = self.socket(user)
        self.assertTrue((await socket.connect(timeout=5))[0])
        await self.event(socket, 'chat.history')
        return socket

    async def open(self, socket):
        """The socket still answers and keeps its presence lease."""
        await socket.send_json_to({'type': 'lobby.sync'})
        self.assertTrue(await db(PresenceConnection.objects.exists)())

    async def test_locked_command_returns_busy_and_keeps_socket(self):
        cases = [
            ('tokens.command', 'gravewright.tokens.services.command', {'tokens': []},
             'tokens.error', 'tokens.ack', {'action': 'move', 'data': {}}),
            ('actors.command', 'gravewright.actors.services.command', {},
             'actors.error', 'actors.ack', {'action': 'actor.update', 'data': {}}),
            ('maps.command', 'gravewright.maps.services.command', {},
             'maps.error', 'maps.ack', {'action': 'activate', 'data': {}}),
            ('journals.command', 'gravewright.journals.services.command', {},
             'journals.error', 'journals.ack', {'action': 'update', 'data': {}}),
            ('resources.command', 'gravewright.table.domain.command', {},
             'resources.error', 'resources.ack', {'module': 'audio', 'action': 'play', 'data': {}}),
        ]
        try:
            socket = await self.joined(self.gm)
            for kind, target, result, error_type, ack_type, payload in cases:
                with self.subTest(kind=kind), patch(target, side_effect=once(lambda *a, **k: result)):
                    request_id = str(uuid.uuid4())
                    message = {'type': kind, 'payload': {**payload, 'requestId': request_id}}
                    await socket.send_json_to(message)
                    error = await self.event(socket, error_type)
                    self.assertEqual((error['code'], error['requestId']), ('busy', request_id))
                    if kind == 'resources.command':
                        self.assertEqual(error['module'], 'audio')
                    await socket.send_json_to(message)
                    ack = await self.event(socket, ack_type)
                    self.assertEqual(ack['requestId'], request_id)
            await self.open(socket)
        finally:
            await self.finish()

    async def test_locked_chat_returns_busy_on_the_error_channel(self):
        try:
            socket = await self.joined(self.gm)
            request_id = str(uuid.uuid4())
            entry = {'id': '1', 'tableId': str(self.campaign.pk)}
            with patch('gravewright.chat.services.say', side_effect=once(lambda *a: (entry, True))):
                message = {'type': 'chat.say', 'payload': {'requestId': request_id, 'text': 'hello'}}
                await socket.send_json_to(message)
                error = await self.event(socket, 'error')
                self.assertEqual((error['code'], error['requestId']), ('busy', request_id))
                await socket.send_json_to(message)
                self.assertEqual((await self.event(socket, 'chat.ack'))['requestId'], request_id)
            await self.open(socket)
        finally:
            await self.finish()

    def token_fixture(self):
        scene = Scene.objects.create(campaign=self.campaign, name='Room', width=512, height=512)
        actor = Actor.objects.create(campaign=self.campaign, name='Traveler', data={},
                                     permissions={'default': 'read'})
        return scene, Token.objects.create(scene=scene, actor=actor)

    async def test_busy_retry_with_the_same_request_id_applies_once(self):
        scene, token = await db(self.token_fixture)()
        real = token_services._write_command
        try:
            socket = await self.joined(self.gm)
            request_id = str(uuid.uuid4())
            message = {'type': 'tokens.command', 'payload': {'requestId': request_id, 'action': 'move', 'data': {
                'mapId': str(scene.pk), 'id': str(token.pk), 'gridX': 2, 'gridY': 1,
                'expectedVersion': token.version}}}
            with patch.object(token_services, '_write_command', side_effect=once(real)):
                await socket.send_json_to(message)
                self.assertEqual((await self.event(socket, 'tokens.error'))['code'], 'busy')
                await socket.send_json_to(message)
                await self.event(socket, 'tokens.ack', lambda p: p['requestId'] == request_id)
            # A retry after the acknowledgement replays the receipt instead of moving again.
            await socket.send_json_to(message)
            await self.event(socket, 'tokens.ack', lambda p: p['requestId'] == request_id)
        finally:
            await self.finish()
        self.assertEqual(await db(Receipt.objects.filter(request_id=request_id).count)(), 1)
        moved = await db(Token.objects.get)(pk=token.pk)
        self.assertEqual((moved.grid_x, moved.grid_y, moved.version), (2, 1, token.version + 1))

    async def test_non_lock_operational_error_still_fails_loudly(self):
        socket = self.socket(self.gm)
        self.assertTrue((await socket.connect(timeout=5))[0])
        await self.event(socket, 'chat.history')
        with patch('gravewright.tokens.services.command', side_effect=OperationalError('disk I/O error')):
            await socket.send_json_to({'type': 'tokens.command', 'payload': {
                'requestId': str(uuid.uuid4()), 'action': 'move', 'data': {}}})
            with self.assertRaises(OperationalError):
                for _ in range(100):
                    await socket.receive_json_from(timeout=3)

    async def test_dice_busy_releases_the_claim_and_the_retry_rolls_once(self):
        request_id = str(uuid.uuid4())
        message = {'type': 'dice.roll', 'payload': {'expression': '1d1', 'requestId': request_id}}
        try:
            socket = await self.joined(self.gm)
            with patch.object(dice, 'complete', side_effect=once(dice.complete)):
                await socket.send_json_to(message)
                error = await self.event(socket, 'dice.error')
                self.assertEqual((error['code'], error['requestId']), ('busy', request_id))
                self.assertFalse(await db(Submission.objects.filter(request_id=request_id).exists)())
                await socket.send_json_to(message)
                await self.event(socket, 'dice.ack', lambda p: p['requestId'] == request_id)
        finally:
            await self.finish()
        self.assertEqual(await db(Message.objects.filter(request_id=request_id).count)(), 1)

    async def test_dice_release_failure_falls_back_to_claim_expiry(self):
        request_id = str(uuid.uuid4())
        message = {'type': 'dice.roll', 'payload': {'expression': '1d1', 'requestId': request_id}}
        try:
            socket = await self.joined(self.gm)
            with patch.object(dice, 'complete', side_effect=locked()), \
                    patch.object(dice, 'release', side_effect=locked()):
                await socket.send_json_to(message)
                self.assertEqual((await self.event(socket, 'dice.error'))['code'], 'busy')
                self.assertTrue(await db(Submission.objects.filter(request_id=request_id).exists)())
                await socket.send_json_to(message)
                self.assertEqual((await self.event(socket, 'dice.error'))['code'], 'roll_in_progress')
        finally:
            await self.finish()

    async def test_release_keeps_a_claim_whose_message_was_committed(self):
        request_id = uuid.uuid4()

        def committed():
            from django.utils import timezone
            from datetime import timedelta
            claim = Submission.objects.create(campaign=self.campaign, author=self.gm, request_id=request_id,
                                              expires_at=timezone.now() + timedelta(seconds=15))
            Message.objects.create(campaign=self.campaign, author=self.gm, author_name='GM', text='',
                                   request_id=request_id, visibility='public', roll={'result': 1})
            dice.release(claim.pk)
            return Submission.objects.filter(pk=claim.pk).exists()
        self.assertTrue(await db(committed)())

    async def test_delivery_lock_keeps_socket_and_replays_on_upkeep(self):
        scene = await db(Scene.objects.create)(campaign=self.campaign, name='Room', width=512, height=512)
        real = token_services.state
        try:
            socket = await self.joined(self.gm)
            await socket.send_json_to({'type': 'tokens.sync', 'payload': {'mapId': str(scene.pk)}})
            await self.event(socket, 'tokens.state')
            with patch.object(token_services, 'state', side_effect=once(real)) as state, \
                    self.assertLogs(metrics.logger, 'WARNING') as logs:
                # A real change, so the replayed projection differs from the one sent.
                await db(Token.objects.create)(scene=scene, actor=await db(Actor.objects.create)(
                    campaign=self.campaign, name='Arrival', data={}, permissions={'default': 'read'}))
                await get_channel_layer().group_send(f'table.{self.campaign.pk.hex}', {'type': 'room.tokens'})
                projection = await self.event(socket, 'tokens.state')
                self.assertEqual(projection['mapId'], str(scene.pk))
                self.assertEqual(state.call_count, 2)
            self.assertIn('database busy kind=delivery name=room.tokens', ' '.join(logs.output))
            await self.open(socket)
        finally:
            await self.finish()

    async def test_locked_sync_is_replayed_on_upkeep(self):
        real = __import__('gravewright.actors.services', fromlist=['state']).state
        try:
            socket = await self.joined(self.gm)
            with patch('gravewright.actors.services.state', side_effect=once(real)) as state:
                await socket.send_json_to({'type': 'actors.sync'})
                await self.event(socket, 'actors.state')
                self.assertEqual(state.call_count, 2)
            await self.open(socket)
        finally:
            await self.finish()

    async def test_heartbeat_upkeep_lock_keeps_socket(self):
        try:
            socket = await self.joined(self.gm)
            with patch('gravewright.realtime.services.roster', side_effect=locked()) as roster:
                # Several 0.1-second beats meet the lock (well within the 2-second TTL).
                await asyncio.sleep(.6)
                self.assertGreaterEqual(roster.call_count, 3)
            presence = await self.event(socket, 'table.presence')
            self.assertEqual([row['id'] for row in presence['members']], [str(self.gm.pk)])
        finally:
            await self.finish()

    async def test_database_busy_is_logged_without_payload(self):
        try:
            socket = await self.joined(self.gm)
            with patch('gravewright.chat.services.say', side_effect=locked()), \
                    self.assertLogs(metrics.logger, 'WARNING') as logs:
                await socket.send_json_to({'type': 'chat.say', 'payload': {
                    'requestId': str(uuid.uuid4()), 'text': 'SEGREDO-123'}})
                await self.event(socket, 'error')
            output = ' '.join(logs.output)
            self.assertIn('database busy kind=command name=chat.say', output)
            self.assertNotIn('SEGREDO', output)
        finally:
            await self.finish()
