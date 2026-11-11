"""Separate lanes per socket: samples and pongs never wait behind commands."""

import asyncio
from datetime import timedelta
import json
import threading
from unittest.mock import patch
import uuid

from channels.db import database_sync_to_async as db
from django.conf import settings
from django.test import Client, TransactionTestCase, override_settings
from django.utils import timezone

from gravewright.accounts.models import User
from gravewright.actors.models import Actor
from gravewright.campaigns.models import Membership, StreamerLink
from gravewright.maps import cursors
from gravewright.maps.models import Broadcast, Scene
from gravewright.realtime import consumers, services
from gravewright.realtime.consumers import TableConsumer
from gravewright.realtime.models import PresenceConnection
from gravewright.realtime.tests import test_sockets as sockets
from gravewright.tokens import services as token_services
from gravewright.tokens.models import Token

ACK = {"tokens": []}


class Gate:
    """Hold a synchronous call on its worker thread until the test opens the gate."""

    def __init__(self):
        self.entered, self.opened = threading.Event(), threading.Event()
        self.calls, self.threads = [], []

    def wrap(self, then, first_only=True):
        def run(*args, **kwargs):
            self.calls.append(args)
            self.threads.append(threading.get_ident())
            if not first_only or len(self.calls) == 1:
                self.entered.set()
                self.opened.wait(10)
            return then(*args, **kwargs)
        return run

    async def wait(self):
        return await asyncio.to_thread(self.entered.wait, 5)


class Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
                   GRAVEWRIGHT_HEARTBEAT_SECONDS=.1, GRAVEWRIGHT_PRESENCE_TTL=2,
                   ALLOWED_HOSTS=['testserver'])
class SocketLaneTests(TransactionTestCase):
    socket = sockets.SocketTests.socket
    event = sockets.SocketTests.event
    finish = sockets.SocketTests.finish

    def setUp(self):
        sockets.SocketTests.setUp(self)
        self.scene = Scene.objects.create(campaign=self.campaign, name='Room', width=512, height=512,
                                          visibility='players')
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        actor = Actor.objects.create(campaign=self.campaign, name='Traveler', data={},
                                     permissions={'default': 'read'})
        self.token = Token.objects.create(scene=self.scene, actor=actor)
        self.gate = Gate()

    def tearDown(self):
        self.gate.opened.set()

    async def joined(self, user, *subscriptions):
        socket = self.socket(user)
        self.assertTrue((await socket.connect(timeout=5))[0])
        await self.event(socket, 'chat.history')
        for kind, reply in subscriptions:
            await socket.send_json_to({'type': kind, 'payload': {'mapId': str(self.scene.pk)}})
            await self.event(socket, reply)
        return socket

    async def collect(self, socket, seconds, kinds):
        """Read frames for a while without letting a receive timeout cancel the app."""
        frames, loop = [], asyncio.get_running_loop()
        end = loop.time() + seconds
        while loop.time() < end:
            if await socket.receive_nothing(timeout=.05, interval=.01):
                continue
            message = await socket.receive_json_from(timeout=1)
            if message['type'] == 'session.ping':
                await socket.send_json_to({'type': 'session.pong'})
            elif message['type'] in kinds:
                frames.append(message)
        return frames

    async def closed_with(self, socket):
        for _ in range(500):
            message = await socket.receive_output(timeout=3)
            if message['type'] == 'websocket.close':
                return message.get('code')
        self.fail('The socket was not closed')

    def command(self, kind='tokens.command'):
        return {'type': kind, 'payload': {'requestId': str(uuid.uuid4()), 'action': 'move', 'data': {}}}

    def cursor(self, x):
        return {'type': 'maps.cursor', 'payload': {'mapId': str(self.scene.pk), 'position': {'x': x, 'y': 10}}}

    def drag(self, stream, phase, x=1):
        # Previews carry the token revision, as the board does.
        return {'type': 'token.drag', 'payload': {'stream': stream, 'mapId': str(self.scene.pk), 'phase': phase,
                'positions': [{'id': str(self.token.pk), 'gridX': x, 'gridY': 1, 'version': self.token.version}]
                if phase == 'update' else []}}

    async def test_pong_renews_while_command_blocked(self):
        renewed = threading.Event()
        real_renew = services.renew

        def renew(*args, **kwargs):
            renewed.set()
            return real_renew(*args, **kwargs)
        try:
            socket = await self.joined(self.gm)
            with patch('gravewright.tokens.services.command', side_effect=self.gate.wrap(lambda *a: ACK)), \
                    patch('gravewright.realtime.services.renew', side_effect=renew):
                await socket.send_json_to(self.command())
                self.assertTrue(await self.gate.wait())
                renewed.clear()
                # Leases renew in the second half of their lifetime (1 s of the 2 s test TTL).
                await asyncio.sleep(1.1)
                await socket.send_json_to({'type': 'session.pong'})
                self.assertTrue(await asyncio.to_thread(renewed.wait, 2))
                self.assertFalse(self.gate.opened.is_set())
                self.gate.opened.set()
                await self.event(socket, 'tokens.ack')
        finally:
            await self.finish()

    async def test_cursor_reaches_peer_while_sender_command_blocked(self):
        try:
            player = await self.joined(self.player, ('maps.layers', 'maps.layers'))
            gm = await self.joined(self.gm, ('maps.layers', 'maps.layers'))
            with patch('gravewright.tokens.services.command', side_effect=self.gate.wrap(lambda *a: ACK)):
                await gm.send_json_to(self.command())
                self.assertTrue(await self.gate.wait())
                await gm.send_json_to(self.cursor(40))
                packet = await self.event(player, 'maps.cursor')
                self.assertEqual(packet['position'], {'x': 40, 'y': 10})
                self.assertFalse(self.gate.opened.is_set())
                self.gate.opened.set()
                await self.event(gm, 'tokens.ack')
        finally:
            await self.finish()

    async def test_cursor_reaches_a_busy_recipient(self):
        try:
            player = await self.joined(self.player, ('maps.layers', 'maps.layers'))
            gm = await self.joined(self.gm, ('maps.layers', 'maps.layers'))
            with patch('gravewright.maps.services.command', side_effect=self.gate.wrap(lambda *a: {})):
                await player.send_json_to(self.command('maps.command'))
                self.assertTrue(await self.gate.wait())
                await gm.send_json_to(self.cursor(50))
                self.assertEqual((await self.event(player, 'maps.cursor'))['position']['x'], 50)
                self.assertFalse(self.gate.opened.is_set())
                self.gate.opened.set()
                await self.event(player, 'maps.ack')
        finally:
            await self.finish()

    async def test_cursor_samples_are_conflated(self):
        clock = Clock()
        # The fake clock covers the whole connection: rate and throttle state use it.
        self.enterContext(patch.object(consumers, 'monotonic', clock))
        try:
            player = await self.joined(self.player, ('maps.layers', 'maps.layers'))
            gm = await self.joined(self.gm, ('maps.layers', 'maps.layers'))
            with patch.object(cursors, 'project', side_effect=self.gate.wrap(cursors.project)):
                await gm.send_json_to(self.cursor(10))
                self.assertTrue(await self.gate.wait())
                for x in (20, 30, 40, 50):
                    clock.now += .1  # arrival times past the 75 ms input throttle
                    await gm.send_json_to(self.cursor(x))
                    await asyncio.sleep(.01)  # let the reader admit it at this time
                await asyncio.sleep(.1)
                self.gate.opened.set()
                frames = await self.collect(player, 1, {'maps.cursor'})
            self.assertEqual([call[1]['position']['x'] for call in self.gate.calls], [10, 50])
            self.assertEqual([frame['payload']['position']['x'] for frame in frames], [10, 50])
        finally:
            await self.finish()

    async def test_drag_end_is_never_dropped_and_keeps_order(self):
        first, second = str(uuid.uuid4()), str(uuid.uuid4())
        try:
            player = await self.joined(self.player, ('tokens.sync', 'tokens.state'))
            gm = await self.joined(self.gm, ('tokens.sync', 'tokens.state'))
            with patch.object(token_services, 'preview', side_effect=self.gate.wrap(token_services.preview)):
                await gm.send_json_to(self.drag(first, 'update'))
                self.assertTrue(await self.gate.wait())
                await gm.send_json_to(self.drag(first, 'end'))
                await gm.send_json_to(self.drag(second, 'update', 2))
                await asyncio.sleep(.1)
                self.gate.opened.set()
                frames = await self.collect(player, 1, {'token.drag'})
            self.assertEqual([(f['payload']['stream'], f['payload']['phase']) for f in frames],
                             [(first, 'update'), (first, 'end'), (second, 'update')])
        finally:
            await self.finish()

    async def test_viewport_latest_wins(self):
        calls, entered, opened = [], asyncio.Event(), asyncio.Event()

        async def viewport(consumer, payload):
            calls.append(('viewport', payload['generation']))
            if len(calls) == 1:
                entered.set()
                await opened.wait()

        async def stop(consumer, wait=True):
            calls.append(('stop',))
        try:
            gm = await self.joined(self.gm)
            with patch.object(TableConsumer, 'scene_viewport', viewport), \
                    patch.object(TableConsumer, 'stop_stream', stop):
                for frames, expected in (
                        ([{'generation': 2}, None], ('stop',)),
                        ([None, {'generation': 3}], ('viewport', 3))):
                    calls.clear(), entered.clear(), opened.clear()
                    await gm.send_json_to({'type': 'scene.viewport', 'payload': {'generation': 1}})
                    await asyncio.wait_for(entered.wait(), 3)
                    for payload in frames:
                        await gm.send_json_to({'type': 'scene.viewport.stop', 'payload': {}} if payload is None
                                              else {'type': 'scene.viewport', 'payload': payload})
                    await asyncio.sleep(.1)
                    opened.set()
                    await self.collect(gm, .3, set())
                    self.assertEqual(calls, [('viewport', 1), expected])
        finally:
            await self.finish()

    async def test_commands_keep_order(self):
        order = []

        def command(campaign, user, action, data, request_id):
            order.append(request_id)
            return {}
        try:
            gm = await self.joined(self.gm)
            messages = [self.command('maps.command') for _ in range(3)]
            with patch('gravewright.maps.services.command', side_effect=command):
                for message in messages:
                    await gm.send_json_to(message)
                acks = [(await self.event(gm, 'maps.ack'))['requestId'] for _ in messages]
            expected = [message['payload']['requestId'] for message in messages]
            self.assertEqual((order, acks), (expected, expected))
        finally:
            await self.finish()

    async def test_rate_limit_uses_arrival_time(self):
        clock = Clock()
        try:
            with patch.object(consumers, 'monotonic', clock):
                gm = await self.joined(self.gm)
                messages = [self.command('maps.command') for _ in range(60)]
                with patch('gravewright.maps.services.command', side_effect=self.gate.wrap(lambda *a: {})):
                    await gm.send_json_to(messages[0])
                    self.assertTrue(await self.gate.wait())
                    for message in messages[1:]:
                        clock.now += .06  # 16.7 commands per second, below the 20/s limit
                        await gm.send_json_to(message)
                        # Let the reader admit this frame at the current (fake) arrival time.
                        await asyncio.sleep(.005)
                    await asyncio.sleep(.2)
                    self.gate.opened.set()
                    acks = set()
                    while len(acks) < len(messages):
                        output = await gm.receive_output(timeout=3)
                        if output['type'] == 'websocket.close':
                            self.fail(f"Closed with {output.get('code')} after {len(acks)} acknowledgements")
                        frame = json.loads(output['text'])
                        if frame['type'] == 'session.ping':
                            await gm.send_json_to({'type': 'session.pong'})
                        elif frame['type'] == 'maps.ack':
                            acks.add(frame['payload']['requestId'])
            self.assertEqual(acks, {message['payload']['requestId'] for message in messages})
        finally:
            await self.finish()

    async def test_burst_over_limit_still_closes_4429(self):
        clock = Clock()
        with patch.object(consumers, 'monotonic', clock):
            gm = self.socket(self.gm)
            self.assertTrue((await gm.connect(timeout=5))[0])
            for _ in range(settings.WS_BURST_COMMANDS + 1):
                await gm.send_json_to({'type': 'api.watch'})
            self.assertEqual(await self.closed_with(gm), 4429)
            await gm.disconnect()

    async def test_inbox_overflow_closes_4429(self):
        try:
            gm = await self.joined(self.gm)
            with patch.object(consumers, 'INBOX_LIMIT', 3), \
                    patch('gravewright.maps.services.command', side_effect=self.gate.wrap(lambda *a: {})):
                await gm.send_json_to(self.command('maps.command'))
                self.assertTrue(await self.gate.wait())
                for _ in range(5):
                    await gm.send_json_to(self.command('maps.command'))
                self.assertEqual(await self.closed_with(gm), 4429)
                self.gate.opened.set()
        finally:
            await self.finish()

    async def test_ephemeral_lane_uses_its_own_thread(self):
        commands, samples = Gate(), Gate()
        samples.opened.set()
        try:
            await self.joined(self.player, ('maps.layers', 'maps.layers'))
            gm = await self.joined(self.gm, ('maps.layers', 'maps.layers'))
            with patch('gravewright.tokens.services.command', side_effect=commands.wrap(lambda *a: ACK)), \
                    patch.object(cursors, 'project', side_effect=samples.wrap(cursors.project)):
                await gm.send_json_to(self.command())
                self.assertTrue(await commands.wait())
                await gm.send_json_to(self.cursor(30))
                self.assertTrue(await samples.wait())
                commands.opened.set()
                await self.event(gm, 'tokens.ack')
                await gm.send_json_to(self.command())
                await self.event(gm, 'tokens.ack')
            self.assertEqual(len(set(commands.threads)), 1)
            self.assertNotEqual(commands.threads[0], samples.threads[0])
        finally:
            commands.opened.set()
            await self.finish()

    async def test_streamer_cannot_write_through_ephemeral_lane(self):
        def streamer():
            user = User.objects.create_user('lane-streamer@example.test', 'password-12345', name='Stream')
            Membership.objects.create(campaign=self.campaign, user=user, role='streamer')
            StreamerLink.objects.create(campaign=self.campaign, guest=user, digest='b' * 64,
                                        expires_at=timezone.now() + timedelta(hours=1))
            client = Client()
            client.force_login(user)
            self.cookies[user.pk] = (f'{settings.SESSION_COOKIE_NAME}='
                                     f'{client.cookies[settings.SESSION_COOKIE_NAME].value}').encode()
            return user
        user = await db(streamer)()
        try:
            gm = await self.joined(self.gm, ('maps.layers', 'maps.layers'))
            viewer = await self.joined(user, ('maps.layers', 'maps.layers'))
            await viewer.send_json_to(self.cursor(20))
            self.assertEqual((await self.event(viewer, 'error'))['code'], 'read_only')
            await viewer.send_json_to(self.drag(str(uuid.uuid4()), 'update'))
            self.assertEqual((await self.event(viewer, 'error'))['code'], 'read_only')
            self.assertEqual(await self.collect(gm, .4, {'maps.cursor', 'token.drag'}), [])
        finally:
            await self.finish()

    async def test_tokens_sync_during_drag_drops_stale_packet(self):
        other = await db(Scene.objects.create)(campaign=self.campaign, name='Other', width=512, height=512)
        stream = str(uuid.uuid4())
        try:
            player = await self.joined(self.player, ('tokens.sync', 'tokens.state'))
            gm = await self.joined(self.gm, ('tokens.sync', 'tokens.state'))
            with patch.object(token_services, 'preview', side_effect=self.gate.wrap(token_services.preview)):
                await gm.send_json_to(self.drag(stream, 'update'))
                self.assertTrue(await self.gate.wait())
                await gm.send_json_to({'type': 'tokens.sync', 'payload': {'mapId': str(other.pk)}})
                await self.event(gm, 'tokens.state', lambda p: p['mapId'] == str(other.pk))
                self.gate.opened.set()
                self.assertEqual(await self.collect(player, .5, {'token.drag'}), [])
        finally:
            await self.finish()

    async def test_disconnect_with_blocked_ephemeral_work_cleans_up(self):
        await self.joined(self.player, ('maps.layers', 'maps.layers'))
        gm = await self.joined(self.gm, ('maps.layers', 'maps.layers'))
        with patch.object(cursors, 'project', side_effect=self.gate.wrap(cursors.project)):
            await gm.send_json_to(self.cursor(30))
            self.assertTrue(await self.gate.wait())
            leases = await db(PresenceConnection.objects.count)()
            await gm.disconnect(timeout=consumers.DEPART_TIMEOUT + 2)
            self.sockets.remove(gm)
            self.assertEqual(await db(PresenceConnection.objects.count)(), leases - 1)
            self.gate.opened.set()
            for _ in range(40):
                lanes = [task for task in asyncio.all_tasks()
                         if task.get_name() in ('gravewright-ephemeral', 'gravewright-presence') and not task.done()]
                if len(lanes) == 2:  # only the player's lanes remain
                    break
                await asyncio.sleep(.05)
            self.assertEqual(len(lanes), 2)
        await self.finish()
