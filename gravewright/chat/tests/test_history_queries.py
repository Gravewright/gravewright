"""Chat history loads private recipients without one query per message."""

import uuid

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.chat import services
from gravewright.chat.models import Message, Recipient


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class HistoryQueryTests(TestCase):
    def setUp(self):
        self.gm = User.objects.create_user('history-gm@example.test', 'password-12345', name='GM')
        self.player = User.objects.create_user('history-player@example.test', 'password-12345', name='Player')
        self.campaign = Campaign.objects.create(owner=self.gm, name='History')
        Membership.objects.create(campaign=self.campaign, user=self.gm, role='gm')
        Membership.objects.create(campaign=self.campaign, user=self.player, role='player')

    def whispers(self, count):
        for index in range(count):
            message = Message.objects.create(campaign=self.campaign, author=self.gm, author_name='GM',
                                             text=f'Whisper {index}', request_id=uuid.uuid4(),
                                             visibility='whisper')
            Recipient.objects.bulk_create([Recipient(message=message, user=self.gm),
                                           Recipient(message=message, user=self.player)])
        Message.objects.create(campaign=self.campaign, author=self.player, author_name='Player',
                               text='Public', request_id=uuid.uuid4(), visibility='public')

    def queries(self):
        with CaptureQueriesContext(connection) as captured:
            history = services.history(self.campaign.pk, self.player.pk)
        return len(captured), history

    def test_history_query_count_is_constant(self):
        self.whispers(5)
        few, history = self.queries()
        self.assertEqual(len(history), 6)
        self.whispers(45)
        many, history = self.queries()
        self.assertEqual(len(history), 52)  # 50 whispers and two public messages
        self.assertEqual(few, many)

    def test_history_serialization_is_unchanged(self):
        self.whispers(1)
        _, history = self.queries()
        whisper, public = history
        self.assertEqual(whisper['target_names'], ['Player'])
        # The audience is a membership list; its order was never meaningful.
        self.assertEqual(sorted(whisper['audience']), sorted([str(self.gm.pk), str(self.player.pk)]))
        self.assertIsNone(public['audience'])
        self.assertEqual(public['target_names'], [])
        # A single message (for example a live delivery) is serialized the same way.
        row = Message.objects.get(text='Whisper 0')
        self.assertEqual(services.public_message(row), whisper)
