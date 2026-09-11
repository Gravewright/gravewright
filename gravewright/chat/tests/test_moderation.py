import uuid
from channels.db import database_sync_to_async as db
from django.test import TransactionTestCase, override_settings
from gravewright.realtime.tests import test_sockets as fixtures
from gravewright.chat import services
from gravewright.chat.models import Message
from gravewright.accounts.services import AuthError


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
    ALLOWED_HOSTS=['testserver'], GRAVEWRIGHT_HEARTBEAT_SECONDS=.1)
class ModerationTests(TransactionTestCase):
    setUp = fixtures.SocketTests.setUp
    socket = fixtures.SocketTests.socket
    event = fixtures.SocketTests.event
    finish = fixtures.SocketTests.finish

    def test_commands_audiences_and_deleted_retry(self):
        entry = services.send(self.campaign.pk, self.player.pk, '/gm Secret', uuid.uuid4())
        self.assertEqual(set(entry['audience']), {str(self.gm.pk), str(self.player.pk)})
        emote = services.send(self.campaign.pk, self.player.pk, '/me draws a sword', uuid.uuid4())
        self.assertIn('<em>draws a sword</em>', emote['html'])
        for user in (self.player, self.outsider):
            with self.assertRaises(AuthError): services.remove(self.campaign.pk, user.pk)
        request = uuid.uuid4()
        entry = services.send(self.campaign.pk, self.player.pk, 'Remove me', request)
        foreign = Message.objects.create(campaign=self.other, author=self.outsider, author_name='Other', text='Other table', request_id=uuid.uuid4())
        self.assertEqual(services.remove(self.campaign.pk, self.gm.pk, foreign.pk)['removed'], 0)
        services.remove(self.campaign.pk, self.gm.pk, entry['id'])
        self.assertTrue(services.send(self.campaign.pk, self.player.pk, 'Remove me', request)['deleted'])
        self.assertFalse(Message.objects.filter(pk=entry['id']).get().text)
        self.assertNotIn(entry['id'], [m['id'] for m in services.history(self.campaign.pk, self.player.pk)])

    async def test_socket_moderation_is_gm_only_and_refreshes_every_client(self):
        gm, player = self.socket(self.gm), self.socket(self.player)
        try:
            for socket in (gm, player):
                self.assertTrue((await socket.connect(timeout=5))[0])
                await self.event(socket, 'chat.history')
            entry = await db(services.send)(self.campaign.pk, self.player.pk, 'Message', uuid.uuid4())
            for socket in (gm, player): await self.event(socket, 'chat.message')
            await player.send_json_to({'type':'chat.clear'})
            self.assertEqual((await self.event(player, 'error'))['code'], 'gm_required')
            await gm.send_json_to({'type':'chat.delete', 'payload':{'messageId':entry['id']}})
            for socket in (gm, player):
                self.assertEqual((await self.event(socket, 'chat.history'))['messages'], [])
            for text in ('One', 'Two'):
                await db(services.send)(self.campaign.pk, self.player.pk, text, uuid.uuid4())
                for socket in (gm, player): await self.event(socket, 'chat.message')
            await gm.send_json_to({'type':'chat.clear'})
            for socket in (gm, player):
                self.assertEqual((await self.event(socket, 'chat.history'))['messages'], [])
        finally:
            await self.finish()
