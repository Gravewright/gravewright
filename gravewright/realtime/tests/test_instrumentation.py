"""Slow-handler warnings measured on real sockets, without logging user content."""

import asyncio
import re
import time
from unittest.mock import patch
import uuid

from django.db import connection
from django.test import TransactionTestCase, override_settings

from gravewright.realtime import metrics
from gravewright.realtime.consumers import TableConsumer
from gravewright.realtime.tests import test_sockets as sockets

ACK = {"tokens": [], "createdIds": []}


def slow(seconds, value):
    def command(*_args, **_kwargs):
        time.sleep(seconds)
        with connection.cursor() as cursor:  # one real statement for the SQL counters
            cursor.execute('SELECT 1')
        return value
    return command


def field(record, name):
    return float(re.search(rf"{name}=([\d.]+)", record).group(1))


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
                   GRAVEWRIGHT_HEARTBEAT_SECONDS=.1, GRAVEWRIGHT_PRESENCE_TTL=2,
                   ALLOWED_HOSTS=['testserver'])
class InstrumentationTests(TransactionTestCase):
    setUp = sockets.SocketTests.setUp
    socket = sockets.SocketTests.socket
    event = sockets.SocketTests.event
    finish = sockets.SocketTests.finish

    async def joined(self, user):
        socket = self.socket(user)
        self.assertTrue((await socket.connect(timeout=5))[0])
        await self.event(socket, 'chat.history')
        return socket

    def command(self, request_id):
        return {'type': 'tokens.command', 'payload': {'requestId': request_id, 'action': 'move', 'data': {}}}

    @override_settings(GRAVEWRIGHT_REALTIME_SLOW_MS=50)
    async def test_slow_handler_logs_once_with_breakdown(self):
        try:
            socket = await self.joined(self.gm)
            request_id = str(uuid.uuid4())
            with patch('gravewright.tokens.services.command', side_effect=slow(.1, ACK)), \
                    self.assertLogs(metrics.logger, 'WARNING') as logs:
                await socket.send_json_to(self.command(request_id))
                await self.event(socket, 'tokens.ack')
            records = [line for line in logs.output if 'name=tokens.command' in line]
            self.assertEqual(len(records), 1)
            self.assertIn('kind=command', records[0])
            self.assertGreaterEqual(field(records[0], 'handler_ms'), 100)
            # The command's own statement is counted; the acknowledgement is one frame.
            self.assertGreaterEqual(field(records[0], 'sql_count'), 1)
            self.assertEqual(field(records[0], 'frames'), 1)
            self.assertGreater(field(records[0], 'bytes'), 0)
        finally:
            await self.finish()

    @override_settings(GRAVEWRIGHT_REALTIME_SLOW_MS=5000)
    async def test_fast_handler_does_not_log(self):
        try:
            socket = await self.joined(self.gm)
            with patch('gravewright.tokens.services.command', return_value=ACK), \
                    self.assertNoLogs(metrics.logger, 'WARNING'):
                await socket.send_json_to(self.command(str(uuid.uuid4())))
                await self.event(socket, 'tokens.ack')
        finally:
            await self.finish()

    @override_settings(GRAVEWRIGHT_REALTIME_SLOW_MS=50)
    async def test_queue_wait_is_measured(self):
        try:
            socket = await self.joined(self.gm)
            first, second = str(uuid.uuid4()), str(uuid.uuid4())
            commands = iter([slow(.2, ACK), slow(0, ACK)])
            with patch('gravewright.tokens.services.command',
                       side_effect=lambda *a, **k: next(commands)(*a, **k)), \
                    self.assertLogs(metrics.logger, 'WARNING') as logs:
                await socket.send_json_to(self.command(first))
                await socket.send_json_to(self.command(second))
                await self.event(socket, 'tokens.ack', lambda p: p['requestId'] == second)
            records = [line for line in logs.output if 'name=tokens.command' in line]
            self.assertEqual(len(records), 2)
            self.assertGreaterEqual(field(records[1], 'queue_ms'), 150)
        finally:
            await self.finish()

    @override_settings(GRAVEWRIGHT_REALTIME_SLOW_MS=50)
    async def test_log_never_contains_payload(self):
        try:
            socket = await self.joined(self.gm)
            request_id = str(uuid.uuid4())
            entry = {'id': '1', 'tableId': str(self.campaign.pk), 'text': 'SEGREDO-123'}
            with patch('gravewright.chat.services.say', side_effect=slow(.1, (entry, True))), \
                    self.assertLogs(metrics.logger, 'WARNING') as logs:
                await socket.send_json_to({'type': 'chat.say', 'payload': {
                    'requestId': request_id, 'text': 'SEGREDO-123'}})
                await self.event(socket, 'chat.ack')
            output = ' '.join(logs.output)
            self.assertIn('name=chat.say', output)
            self.assertNotIn('SEGREDO', output)
            self.assertNotIn(request_id, output)
        finally:
            await self.finish()

    @override_settings(GRAVEWRIGHT_REALTIME_SLOW_MS=50)
    async def test_unknown_client_types_are_not_logged_verbatim(self):
        original = TableConsumer.authorized

        async def delayed(consumer):
            await asyncio.sleep(.1)
            return await original(consumer)
        try:
            socket = await self.joined(self.gm)
            with patch.object(TableConsumer, 'authorized', delayed), \
                    self.assertLogs(metrics.logger, 'WARNING') as logs:
                await socket.send_json_to({'type': 'SEGREDO-TYPE', 'payload': {}})
                await self.event(socket, 'error', lambda p: p.get('code') == 'unknown_command')
            output = ' '.join(logs.output)
            self.assertIn('name=unknown', output)
            self.assertNotIn('SEGREDO', output)
        finally:
            await self.finish()
