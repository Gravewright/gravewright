import uuid
from unittest.mock import patch
from channels.db import database_sync_to_async as db
from django.test import override_settings, TransactionTestCase
from gravewright.realtime.tests import test_sockets as fixtures
from gravewright.chat.models import Message
from gravewright.dice.models import Submission
from gravewright.dice.engine import evaluate


# Reuse only the socket fixtures, not the parent test methods.
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
    GRAVEWRIGHT_HEARTBEAT_SECONDS=.1, GRAVEWRIGHT_PRESENCE_TTL=3, ALLOWED_HOSTS=['testserver'])
class DiceTests(TransactionTestCase):
    setUp = fixtures.SocketTests.setUp
    socket = fixtures.SocketTests.socket
    event = fixtures.SocketTests.event
    finish = fixtures.SocketTests.finish

    async def command(self, socket, **values):
        payload = {'expression': '4d1', 'requestId': str(uuid.uuid4()), **values}
        await socket.send_json_to({'type': 'dice.roll', 'payload': payload})
        return payload

    async def test_roll_is_authoritative_persistent_and_idempotent(self):
        socket = self.socket(self.player)
        try:
            self.assertTrue((await socket.connect())[0]); await self.event(socket, 'chat.history')
            payload = await self.command(socket, total=999, result={'value':999}, repeat=2, label='<b>Stats</b>')
            message = (await self.event(socket, 'dice.ack'))['message']
            self.assertEqual(message['roll']['result']['value']['value'], 4)
            self.assertEqual(len(message['roll']['batch']), 2)
            self.assertIn('&lt;b&gt;', message['html'])
            self.assertIn('dice-result__batch', message['html'])
            await socket.send_json_to({'type':'dice.roll','payload':payload})
            self.assertEqual((await self.event(socket, 'dice.ack'))['message']['id'],message['id'])
            self.assertEqual(await db(Message.objects.count)(),1)
            await socket.send_json_to({'type':'chat.sync'})
            self.assertEqual((await self.event(socket,'chat.history'))['messages'][0]['roll'],message['roll'])
        finally:
            await self.finish()

    async def test_secret_roll_is_filtered_live_and_in_history(self):
        from gravewright.campaigns.models import Membership
        await db(Membership.objects.create)(campaign=self.campaign,user=self.outsider)
        gm, author, other = self.socket(self.gm), self.socket(self.player), self.socket(self.outsider)
        try:
            for s in [gm,author,other]:
                self.assertTrue((await s.connect())[0]); await self.event(s,'chat.history')
            await self.command(author,visibility='gm')
            await self.event(author,'dice.ack')
            self.assertTrue((await self.event(gm,'chat.message'))['roll']['secret'])
            # Queue a public marker after the secret; other must receive it first.
            await self.command(author,label='Public')
            await self.event(author,'dice.ack')
            self.assertEqual((await self.event(other,'chat.message'))['text'],'Public')
            for s, count in [(gm,2),(author,2),(other,1)]:
                await s.send_json_to({'type':'chat.sync'})
                self.assertEqual(len((await self.event(s,'chat.history'))['messages']),count)
        finally:
            await self.finish()

    async def test_invalid_rolls_and_forged_campaign_create_no_message(self):
        socket=self.socket(self.player)
        try:
            self.assertTrue((await socket.connect())[0]); await self.event(socket,'chat.history')
            for invalid in [{'expression':'1d0'},{'expression':'1d1!'},{'expression':'1d6L'},
                            {'repeat':True},{'repeat':13},{'label':'x'*49},{'visibility':'private'},
                            {'expression':'x'*513}]:
                await self.command(socket,**invalid); await self.event(socket,'dice.error')
            await self.command(socket,tableId=str(self.other.pk))
            self.assertEqual((await self.event(socket,'error'))['code'],'not_a_member')
            self.assertEqual(await db(Message.objects.count)(),0)
        finally:
            await self.finish()

    async def test_access_is_rechecked_after_engine_finishes(self):
        from django.contrib.sessions.models import Session
        def revoke(expression, repeat):
            result=evaluate(expression,repeat)
            Session.objects.filter(session_key=self.sessions[self.player.pk]).delete()
            return result
        socket=self.socket(self.player)
        try:
            self.assertTrue((await socket.connect())[0]); await self.event(socket,'chat.history')
            with patch('gravewright.realtime.consumers.evaluate',revoke):
                await self.command(socket)
                for _ in range(100):
                    frame=await socket.receive_output(timeout=3)
                    if frame['type']=='websocket.close':break
                else:self.fail('Revoked socket remained open')
            self.assertEqual(await db(Message.objects.count)(),0)
        finally:
            await self.finish()

    async def test_two_tabs_cannot_execute_the_same_request_twice(self):
        import time
        def delayed(expression, repeat):
            time.sleep(.3)
            return evaluate(expression, repeat)
        one,two=self.socket(self.player),self.socket(self.player)
        try:
            for s in [one,two]:
                self.assertTrue((await s.connect())[0]);await self.event(s,'chat.history')
            with patch('gravewright.realtime.consumers.evaluate',side_effect=delayed) as engine:
                payload=await self.command(one)
                # Wait for the durable claim before retrying from the other tab.
                import asyncio
                for _ in range(100):
                    if await db(Submission.objects.exists)(): break
                    await asyncio.sleep(.01)
                await two.send_json_to({'type':'dice.roll','payload':payload})
                self.assertEqual((await self.event(two,'dice.error'))['code'],'roll_in_progress')
                first=(await self.event(one,'dice.ack'))['message']
                await two.send_json_to({'type':'dice.roll','payload':payload})
                self.assertEqual((await self.event(two,'dice.ack'))['message']['id'],first['id'])
                self.assertEqual(engine.call_count,1)
        finally:
            await self.finish()
