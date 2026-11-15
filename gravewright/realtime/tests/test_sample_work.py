"""Work a socket no longer repeats: scene reads for samples, unchanged chat
history, and dependent projections on a subscription change."""

import asyncio
import threading
from unittest.mock import AsyncMock, patch
import uuid

from autobahn.exception import Disconnected

from channels.db import database_sync_to_async as db
from channels.layers import get_channel_layer
from django.test import SimpleTestCase, TransactionTestCase, override_settings

from gravewright.chat import services as chat_services
from gravewright.maps import cursors
from gravewright.maps.models import Scene
from gravewright.maps.services import MapError
from gravewright.realtime import access, scene_stream
from gravewright.realtime.consumers import TableConsumer
from gravewright.realtime.scene_stream import SceneStreamMixin
from gravewright.realtime.tests import test_socket_lanes as lanes
from gravewright.table import domain


class Counter:
    """Count calls to a function while still running it."""

    def __init__(self, then):
        self.then, self.calls = then, []

    def __call__(self, *args, **kwargs):
        self.calls.append(args)
        return self.then(*args, **kwargs)


class SceneAnswerTests(SimpleTestCase):
    """The reuse rule itself, without sockets."""

    def setUp(self):
        self.stream = SceneStreamMixin()
        self.stream.init_stream()
        self.reads = []

    def read(self, value="scene"):
        def run():
            self.reads.append(value)
            return value
        return run

    async def test_an_answer_is_reused_until_forgotten(self):
        self.assertEqual(await self.stream.scene_answer("a", self.read()), "scene")
        self.assertEqual(await self.stream.scene_answer("a", self.read()), "scene")
        self.assertEqual(len(self.reads), 1)
        self.stream.forget_scenes()
        await self.stream.scene_answer("a", self.read())
        self.assertEqual(len(self.reads), 2)

    async def test_an_answer_expires(self):
        now = [100.0]
        with patch.object(scene_stream, "monotonic", lambda: now[0]):
            await self.stream.scene_answer("a", self.read())
            now[0] += self.stream.scene_answer_ttl - .01
            await self.stream.scene_answer("a", self.read())
            self.assertEqual(len(self.reads), 1)
            now[0] += .02
            await self.stream.scene_answer("a", self.read())
        self.assertEqual(len(self.reads), 2)

    async def test_an_access_change_in_this_process_reads_again(self):
        await self.stream.scene_answer("a", self.read())
        with patch.object(access, "_epoch", access.epoch() + 1):
            await self.stream.scene_answer("a", self.read())
        self.assertEqual(len(self.reads), 2)

    async def test_a_read_that_started_before_forgetting_is_not_stored(self):
        def forgotten_meanwhile():
            # The event loop handled a server event while this read ran.
            self.stream.forget_scenes()
            self.reads.append("stale")
            return "stale"
        await self.stream.scene_answer("a", forgotten_meanwhile)
        self.assertEqual(await self.stream.scene_answer("a", self.read("fresh")), "fresh")

    async def test_a_refusal_forgets_every_answer(self):
        await self.stream.scene_answer("a", self.read())

        def refused():
            raise MapError("Scene not found or access denied.", "not_found")
        with self.assertRaises(MapError):
            await self.stream.scene_answer("b", refused)
        await self.stream.scene_answer("a", self.read())
        self.assertEqual(len(self.reads), 2)

    async def test_an_unhashable_identifier_is_never_reused(self):
        for _ in range(2):
            await self.stream.scene_answer(("scene", ["not", "an", "id"]), self.read())
        self.assertEqual(len(self.reads), 2)


class ClosingSocketTests(SimpleTestCase):
    async def test_a_frame_sent_while_the_socket_closes_is_dropped(self):
        # Fast sample lanes can send between Daphne's closing handshake and the
        # disconnect event; that must not fail the lane.
        consumer = TableConsumer()
        consumer.send = AsyncMock(side_effect=Disconnected('Attempt to send on a closed protocol'))
        await consumer.emit('maps.cursor', {'position': None})
        consumer.send.assert_awaited_once()


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
                   GRAVEWRIGHT_HEARTBEAT_SECONDS=.1, GRAVEWRIGHT_PRESENCE_TTL=2,
                   ALLOWED_HOSTS=['testserver'])
class SampleWorkTests(TransactionTestCase):
    setUp = lanes.SocketLaneTests.setUp
    tearDown = lanes.SocketLaneTests.tearDown
    socket = lanes.SocketLaneTests.socket
    event = lanes.SocketLaneTests.event
    finish = lanes.SocketLaneTests.finish
    joined = lanes.SocketLaneTests.joined
    collect = lanes.SocketLaneTests.collect
    cursor = lanes.SocketLaneTests.cursor

    async def publish(self, event):
        await get_channel_layer().group_send(f'table.{self.campaign.pk.hex}', event)

    async def cursors_at(self, socket, sender, positions):
        """Send each position after the 75 ms input throttle; positions the socket saw."""
        for x in positions:
            await sender.send_json_to(self.cursor(x))
            await asyncio.sleep(.1)
        return [frame['payload']['position']['x']
                for frame in await self.collect(socket, .4, {'maps.cursor'})]

    async def test_cursor_relay_reads_each_scene_once(self):
        reads = Counter(scene_stream.scene_for)
        identities = Counter(cursors.identity)
        try:
            player = await self.joined(self.player, ('maps.layers', 'maps.layers'))
            gm = await self.joined(self.gm, ('maps.layers', 'maps.layers'))
            with patch.object(scene_stream, 'scene_for', reads), patch.object(cursors, 'identity', identities):
                self.assertEqual(await self.cursors_at(player, gm, (10, 20, 30, 40)), [10, 20, 30, 40])
            # One read for the recipient and one for the sender's pointer identity.
            self.assertEqual([args[1] for args in reads.calls], [self.player.pk])
            self.assertEqual(len(identities.calls), 1)
        finally:
            await self.finish()

    async def test_a_scene_announcement_stops_the_relay_at_once(self):
        try:
            player = await self.joined(self.player, ('maps.layers', 'maps.layers'))
            gm = await self.joined(self.gm, ('maps.layers', 'maps.layers'))
            self.assertEqual(await self.cursors_at(player, gm, (10,)), [10])
            await db(Scene.objects.filter(pk=self.scene.pk).update)(visibility='gm')
            # As maps.views announces scene changes after commit.
            await self.publish({'type': 'room.maps'})
            self.assertEqual(await self.cursors_at(player, gm, (20, 30)), [])
        finally:
            await self.finish()

    async def test_subscription_changes_do_not_recompute_audio_or_combat(self):
        states = Counter(domain.state)
        try:
            player = await self.joined(self.player)
            await player.send_json_to({'type': 'api.watch'})
            for module in ('audio', 'combat'):
                await player.send_json_to({'type': 'resources.sync',
                                           'payload': {'module': module, 'sceneId': str(self.scene.pk)}})
                await self.event(player, 'resources.state', lambda p, m=module: p['module'] == m)
            with patch.object(domain, 'state', states):
                await player.send_json_to({'type': 'tokens.sync', 'payload': {'mapId': str(self.scene.pk)}})
                await player.send_json_to({'type': 'maps.layers', 'payload': {'mapId': str(self.scene.pk)}})
                frames = await self.collect(player, .8, {'api.changed', 'tokens.state', 'maps.layers'})
            self.assertEqual([frame['type'] for frame in frames if frame['type'] != 'api.changed'],
                             ['tokens.state', 'maps.layers'])
            self.assertEqual(states.calls, [])
            # Extensions still hear the same invalidations as before.
            self.assertEqual(sorted(frame['payload']['domain'] for frame in frames if frame['type'] == 'api.changed'),
                             ['audio', 'audio', 'combat', 'maps.layers', 'tokens'])
        finally:
            await self.finish()

    async def test_unchanged_chat_history_is_not_sent_again(self):
        try:
            player = await self.joined(self.player)
            await self.publish({'type': 'room.chat_refresh'})
            self.assertEqual(await self.collect(player, .4, {'chat.history'}), [])
            # A live message changes what the browser shows: the next history is whole.
            await player.send_json_to({'type': 'chat.say', 'payload': {'text': 'Hello', 'requestId': str(uuid.uuid4())}})
            await self.event(player, 'chat.ack')
            await self.publish({'type': 'room.chat_refresh'})
            frames = await self.collect(player, .4, {'chat.history'})
            self.assertEqual(len(frames), 1)
            self.assertIn('Hello', frames[0]['payload']['messages'][-1]['html'])
            await self.publish({'type': 'room.chat_refresh'})
            self.assertEqual(await self.collect(player, .4, {'chat.history'}), [])
            # A subscription always receives the complete history.
            await player.send_json_to({'type': 'chat.sync', 'payload': {}})
            self.assertEqual(len(await self.collect(player, .4, {'chat.history'})), 1)
        finally:
            await self.finish()

    def hold_history(self):
        """Patch chat history so the first read waits, after reading, until released."""
        read, release, real = threading.Event(), threading.Event(), chat_services.history

        def history(*args):
            result = real(*args)
            if not read.is_set():
                read.set()
                release.wait(10)
            return result
        self.addCleanup(release.set)
        return patch.object(chat_services, 'history', history), read, release

    async def order(self, socket, kinds):
        return [frame['type'] for frame in await self.collect(socket, .6, kinds)]

    async def test_a_live_message_never_precedes_an_older_history(self):
        try:
            player = await self.joined(self.player)
            gm = await self.joined(self.gm)
            held, read, release = self.hold_history()
            with held:
                await player.send_json_to({'type': 'chat.sync', 'payload': {}})
                self.assertTrue(await asyncio.to_thread(read.wait, 5))
                # Committed after the player's history was read.
                await gm.send_json_to({'type': 'chat.say', 'payload': {'text': 'Later', 'requestId': str(uuid.uuid4())}})
                await self.event(gm, 'chat.ack')
                await asyncio.sleep(.3)
                release.set()
                self.assertEqual(await self.order(player, {'chat.history', 'chat.message'}),
                                 ['chat.history', 'chat.message'])
        finally:
            await self.finish()

    async def test_an_acknowledgement_never_precedes_an_older_history(self):
        try:
            player = await self.joined(self.player)
            # After a live message the next history is sent, so its order is observable.
            await player.send_json_to({'type': 'chat.say', 'payload': {'text': 'First', 'requestId': str(uuid.uuid4())}})
            await self.event(player, 'chat.ack')
            held, read, release = self.hold_history()
            with held:
                # A scene list refresh rereads chat history on the delivery lane.
                await self.publish({'type': 'room.maps'})
                self.assertTrue(await asyncio.to_thread(read.wait, 5))
                await player.send_json_to({'type': 'chat.say', 'payload': {'text': 'Mine', 'requestId': str(uuid.uuid4())}})
                await asyncio.sleep(.3)
                release.set()
                self.assertEqual(await self.order(player, {'chat.history', 'chat.ack'}),
                                 ['chat.history', 'chat.ack'])
        finally:
            await self.finish()
