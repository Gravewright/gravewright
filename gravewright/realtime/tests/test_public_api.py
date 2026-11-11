"""Extensions must reach connected clients without a transport command."""
import uuid

from channels.db import database_sync_to_async as db
from django.test import TransactionTestCase, override_settings

from api import actors, chat
from gravewright.realtime.tests import test_sockets as fixtures


@override_settings(
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
    ALLOWED_HOSTS=['testserver'], GRAVEWRIGHT_HEARTBEAT_SECONDS=.1,
)
class PublicApiSocketTests(TransactionTestCase):
    setUp = fixtures.SocketTests.setUp
    socket = fixtures.SocketTests.socket
    event = fixtures.SocketTests.event
    finish = fixtures.SocketTests.finish

    async def test_direct_calls_publish_and_project_for_each_connected_user(self):
        gm, player = self.socket(self.gm), self.socket(self.player)
        try:
            for socket in (gm, player):
                self.assertTrue((await socket.connect(timeout=5))[0])
                await self.event(socket, 'chat.history')
                await socket.send_json_to({'type': 'actors.sync'})
                await self.event(socket, 'actors.state')
            entry = await db(chat.send)(self.campaign.pk, self.gm.pk,
                                        'Sent by an extension', uuid.uuid4())
            for socket in (gm, player):
                delivered = await self.event(socket, 'chat.message')
                self.assertEqual(delivered['id'], entry['id'])
            await db(actors.command)(self.campaign.pk, self.gm.pk, 'actor.create',
                                     {'name': 'Private extension actor'}, uuid.uuid4())
            visible = await self.event(gm, 'actors.state',
                                       lambda value: 'Private extension actor' in str(value))
            self.assertIn('Private extension actor', str(visible))
            # The player's projection did not change, so nothing is sent to it.
            for _ in range(20):
                if await player.receive_nothing(timeout=.05, interval=.01):
                    continue
                frame = await player.receive_json_from(timeout=1)
                if frame['type'] == 'session.ping':
                    await player.send_json_to({'type': 'session.pong'})
                self.assertNotIn('Private extension actor', str(frame))
        finally:
            await self.finish()
