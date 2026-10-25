import asyncio
import math

from django.test import TestCase, TransactionTestCase, override_settings

from gravewright.accounts.models import UserPreference
from gravewright.maps import cursors, services
from gravewright.maps.models import Broadcast, Scene
from gravewright.realtime.tests import test_sockets as fixtures
from .test_scene_audience import SceneAudienceTests


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CursorProjectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SceneAudienceTests.setUpTestData.__func__(cls)

    def test_identity_and_color_come_from_the_server(self):
        member = self.members[0]
        UserPreference.objects.create(user=member.user, ping_color='#123456')
        packet = cursors.project(member, {'mapId': str(self.first.pk), 'position': {'x': 10, 'y': 20},
            'userId': str(self.gm.pk), 'name': 'Forged', 'color': '#ffffff'})
        self.assertEqual(packet['userId'], str(member.user_id))
        self.assertEqual(packet['name'], 'One')
        self.assertEqual(packet['color'], '#123456')
        self.assertEqual(packet['position'], {'x': 10, 'y': 20})

    def test_invalid_coordinates_hidden_scenes_and_streamers_are_rejected(self):
        member = self.members[0]
        for point in (None, [], {'x': True, 'y': 1}, {'x': -1, 'y': 0}, {'x': 101, 'y': 0},
                      {'x': 1, 'y': math.inf}, {'x': math.nan, 'y': 0}, {'x': '1', 'y': 0}):
            with self.subTest(point=point), self.assertRaises(services.MapError):
                cursors.project(member, {'mapId': str(self.first.pk), 'position': point})
        for who, scene in ((member, self.second), (self.members[2], self.first)):
            with self.assertRaises(services.MapError):
                cursors.project(who, {'mapId': str(scene.pk), 'position': {'x': 1, 'y': 2}})


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
    ALLOWED_HOSTS=['testserver'], GRAVEWRIGHT_HEARTBEAT_SECONDS=30)
class CursorSocketTests(TransactionTestCase):
    socket = fixtures.SocketTests.socket
    event = fixtures.SocketTests.event
    finish = fixtures.SocketTests.finish

    def setUp(self):
        fixtures.SocketTests.setUp(self)
        self.scene = Scene.objects.create(campaign=self.campaign, name='Shared', width=100, height=100)
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        UserPreference.objects.create(user=self.player, ping_color='#123456')

    async def test_pointer_stream_has_own_rate_budget_and_hides_on_leave_and_disconnect(self):
        gm, player = self.socket(self.gm), self.socket(self.player)
        try:
            for socket in (gm, player):
                self.assertTrue((await socket.connect())[0])
                await self.event(socket, 'table.joined')
                await socket.send_json_to({'type': 'maps.layers', 'payload': {'mapId': str(self.scene.pk)}})
                await self.event(socket, 'maps.layers')
            packet = {'mapId': str(self.scene.pk), 'position': {'x': 20, 'y': 30}, 'name': 'Forged'}
            for _ in range(60):
                await player.send_json_to({'type': 'maps.cursor', 'payload': packet})
            received = await self.event(gm, 'maps.cursor')
            self.assertEqual(received['userId'], str(self.player.pk))
            self.assertEqual(received['color'], '#123456')
            self.assertEqual(received['name'], 'Player')
            await player.send_json_to({'type': 'maps.sync', 'payload': {}})
            self.assertEqual((await self.event(player, 'maps.state'))['activeMapId'], str(self.scene.pk))
            await player.send_json_to({'type': 'maps.cursor', 'payload': {'mapId': str(self.scene.pk), 'position': None}})
            self.assertIsNone((await self.event(gm, 'maps.cursor', lambda p: p['position'] is None))['position'])
            await asyncio.sleep(.1)
            await player.send_json_to({'type': 'maps.cursor', 'payload': packet})
            await self.event(gm, 'maps.cursor', lambda p: p['position'] is not None)
            await player.disconnect()
            self.sockets.remove(player)
            self.assertIsNone((await self.event(gm, 'maps.cursor'))['position'])
        finally:
            await self.finish()
