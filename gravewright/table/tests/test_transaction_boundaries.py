"""Compendium reads and import preparation run without SQLite's write reservation."""

from pathlib import Path
from tempfile import TemporaryDirectory
import threading
from unittest.mock import patch
import uuid

from django.core.files.base import ContentFile
from django.db import connection, transaction
from django.db.models import F
from django.test import TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext

from gravewright.accounts.models import User
from gravewright.accounts.services import AuthError
from gravewright.campaigns.models import Campaign, Membership
from gravewright.compendiums import services as compendiums
from gravewright.compendiums.models import Entry, Pack
from gravewright.maps.models import Receipt
from gravewright.maps.services import MapError
from gravewright.table import domain


def immediate(queries):
    return [query['sql'] for query in queries if 'BEGIN IMMEDIATE' in query['sql']]


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CompendiumTransactionBoundaryTests(TransactionTestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix='gravewright-boundaries-')
        self.addCleanup(temporary.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=Path(temporary.name) / 'media'))
        self.gm = User.objects.create_user('boundary-gm@example.test', 'password-12345', name='GM')
        self.player = User.objects.create_user('boundary-player@example.test', 'password-12345', name='Player')
        self.campaign = Campaign.objects.create(owner=self.gm, name='Boundaries')
        Membership.objects.create(campaign=self.campaign, user=self.gm, role='gm')
        Membership.objects.create(campaign=self.campaign, user=self.player, role='player')
        self.pack = Pack.objects.create(campaign=self.campaign, name='Synthetic', shared=True)
        self.entry = Entry.objects.create(pack=self.pack, name='Synthetic entry', kind='item',
                                          data={'name': 'Synthetic item', 'type': 'gear', 'data': {'weight': 1}})

    def read(self, user, request_id=None):
        return domain.command(self.campaign.pk, user.pk, 'compendiums', 'read',
                              {'packId': str(self.pack.pk), 'id': str(self.entry.pk)},
                              request_id or str(uuid.uuid4()))

    def test_compendium_read_does_not_begin_immediate(self):
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.read(self.gm)['id'], str(self.entry.pk))
        self.assertEqual(immediate(queries), [])

    def test_compendium_write_still_begins_immediate(self):
        with CaptureQueriesContext(connection) as queries:
            domain.command(self.campaign.pk, self.gm.pk, 'compendiums', 'configure',
                           {'packId': str(self.pack.pk), 'version': self.pack.version, 'name': 'Renamed'},
                           str(uuid.uuid4()))
        self.assertEqual(len(immediate(queries)), 1)

    def test_compendium_read_completes_while_writer_holds_lock(self):
        holding, release, done = threading.Event(), threading.Event(), {}

        def writer():
            try:
                with transaction.atomic():
                    Pack.objects.filter(pk=self.pack.pk).update(version=F('version') + 1)
                    holding.set()
                    release.wait(10)
            finally:
                connection.close()

        def reader():
            try:
                done['entry'] = self.read(self.player)
            finally:
                connection.close()

        writing = threading.Thread(target=writer)
        writing.start()
        try:
            self.assertTrue(holding.wait(5))
            reading = threading.Thread(target=reader)
            reading.start()
            reading.join(3)
            # The read neither waits for nor needs the writer's reservation.
            self.assertFalse(reading.is_alive())
            self.assertEqual(done['entry']['id'], str(self.entry.pk))
        finally:
            release.set()
            writing.join(10)

    def test_compendium_read_rechecks_live_grants_with_reused_request_id(self):
        request_id = str(uuid.uuid4())
        self.assertEqual(self.read(self.player, request_id)['id'], str(self.entry.pk))
        Pack.objects.filter(pk=self.pack.pk).update(shared=False)
        with self.assertRaises(MapError):
            self.read(self.player, request_id)

    def test_compendium_read_creates_no_receipt_or_notification(self):
        # Outside a transaction, on_commit callbacks would run immediately.
        with patch('gravewright.realtime.dispatch.send') as send:
            self.read(self.player)
        send.assert_not_called()
        self.assertFalse(Receipt.objects.exists())

    def import_entry(self):
        return domain.command(self.campaign.pk, self.gm.pk, 'compendiums', 'import',
                              {'packId': str(self.pack.pk), 'id': str(self.entry.pk)}, str(uuid.uuid4()))

    def test_import_prepares_files_before_the_write_lock(self):
        seen = []
        real = compendiums.prepare_import

        def prepare(who, payload):
            seen.append(connection.in_atomic_block)
            return real(who, payload)
        with patch.object(compendiums, 'prepare_import', side_effect=prepare):
            result = self.import_entry()
        self.assertEqual(seen, [False])
        self.assertEqual(result['kind'], 'item')
        self.assertEqual(Receipt.objects.count(), 1)

    def test_import_conflicts_when_the_entry_changed_after_preparation(self):
        real = compendiums.prepare_import

        def prepare(who, payload):
            prepared = real(who, payload)
            Entry.objects.filter(pk=self.entry.pk).update(version=F('version') + 1)
            return prepared
        with patch.object(compendiums, 'prepare_import', side_effect=prepare):
            with self.assertRaises(MapError) as raised:
                self.import_entry()
        self.assertEqual(raised.exception.code, 'conflict')
        self.assertFalse(Receipt.objects.exists())

    def test_invalid_archive_is_rejected_without_the_write_lock(self):
        self.entry.bundle.save('invalid.zip', ContentFile(b'not a zip archive'))
        with CaptureQueriesContext(connection) as queries:
            with self.assertRaises(AuthError):
                self.import_entry()
        self.assertEqual(immediate(queries), [])
        self.assertFalse(Receipt.objects.exists())
