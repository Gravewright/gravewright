"""History restores retain native permissions, integrity and file ownership."""

from copy import deepcopy
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.core.files.base import ContentFile
from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from gravewright.campaigns import test_preparation as fixtures
from gravewright.campaigns.models import Membership
from gravewright.journals import data, history, services
from gravewright.journals.models import Asset, Journal, Receipt, Revision
from gravewright.table.models import DocumentAccess


class JournalHistoryTests(TestCase):
    setUp = fixtures.PreparationTests.setUp
    command = fixtures.PreparationTests.journal

    def create(self, title='Chronicle', kind='diary', **fields):
        result = self.command('create', {'title': title, 'journal_type': kind})
        journal = Journal.objects.get(pk=result['journal_id'])
        for key, value in fields.items():
            setattr(journal, key, value)
        if fields:
            journal.save()
        return journal

    def update(self, journal, **fields):
        journal.refresh_from_db()
        return self.command('update', {'journal_id': str(journal.pk), 'version': journal.version,
                                      'title': journal.title, 'visibility': journal.visibility,
                                      'data': journal.data, **fields})

    def restore(self, journal, revision, request_id=None, user=None):
        journal.refresh_from_db()
        return services.command(self.campaign.pk, (user or self.gm).pk, 'restore-revision', {
            'journal_id': str(journal.pk), 'version': journal.version, 'revision_id': str(revision.pk),
        }, request_id or uuid4())

    def asset_document(self, count=1):
        journal = self.create()
        assets, sections = [], []
        for index in range(count):
            asset = Asset.objects.create(journal=journal, uploader=self.gm, name=f'Synthetic page {index}',
                content_type='image/png', file=ContentFile(b'synthetic history fixture', name=f'history-{uuid4().hex}.png'))
            self.addCleanup(asset.file.storage.delete, asset.file.name)
            assets.append(asset)
            sections.append({'id': f'page-{index}', 'title': asset.name, 'kind': 'image', 'audience': 'public',
                             'assetId': str(asset.pk), 'src': '/game/journal/asset/' + str(asset.pk)})
        journal.data['sections'] = sections
        journal.data = data.normalize_diary_data(journal.data)
        journal.save(update_fields=['data'])
        return journal, assets

    def trash(self, journal):
        journal_id = journal.pk
        with self.captureOnCommitCallbacks(execute=True):
            self.command('delete', {'journal_id': str(journal_id)})
        return Revision.objects.get(journal_id=journal_id, reason='delete')

    def restore_deleted(self, revision, request_id=None):
        return services.command(self.campaign.pk, self.gm.pk, 'restore-deleted',
                                {'revision_id': str(revision.pk)}, request_id or uuid4())

    def test_restore_private_revision_synchronizes_default_grant_and_never_delivers_private_draft(self):
        private = data.empty_data_for('diary')
        private['content'] = fixtures.doc(fixtures.paragraph('UNPUBLISHED_PRIVATE_DRAFT'))
        journal = self.create(data=private)
        policy = DocumentAccess.objects.create(campaign=self.campaign, kind='journals', resource_id=str(journal.pk),
                                               grants={'default': 'none', str(self.player.pk): 'none'})
        self.update(journal, visibility='shared', data={'content': fixtures.doc(fixtures.paragraph('Published safe text'))})
        old = Revision.objects.get(journal_id=journal.pk, version=1)
        # A default public grant is authoritative when no per-user override exists.
        policy.refresh_from_db()
        policy.grants.pop(str(self.player.pk))
        policy.save()
        self.assertIn('Published safe text', str(services.state(self.campaign.pk, self.player.pk)))
        request_id = uuid4()
        with patch('gravewright.realtime.dispatch.send') as send, self.captureOnCommitCallbacks(execute=True):
            result = self.restore(journal, old, request_id)
            self.assertFalse(send.called)
        policy.refresh_from_db()
        journal.refresh_from_db()
        self.assertEqual((journal.visibility, policy.grants['default']), ('private', 'none'))
        self.assertEqual(services.state(self.campaign.pk, self.player.pk)['journals'], [])
        self.assertEqual(send.call_count, 1)
        self.assertNotIn('UNPUBLISHED_PRIVATE_DRAFT', str(send.call_args))
        with self.captureOnCommitCallbacks(execute=True), patch('gravewright.realtime.dispatch.send') as send:
            retry = services.command(self.campaign.pk, self.gm.pk, 'restore-revision', {
                'journal_id': str(journal.pk), 'version': 2, 'revision_id': str(old.pk)}, request_id)
        self.assertEqual(retry, result)
        send.assert_not_called()
        self.assertEqual(journal.version, 3)

    def test_restore_public_revision_preserves_user_overrides_and_other_campaign_policies(self):
        journal = self.create(visibility='shared')
        policy = DocumentAccess.objects.create(campaign=self.campaign, kind='journals', resource_id=str(journal.pk),
                                               grants={'default': 'read', str(self.player.pk): 'none'})
        foreign = DocumentAccess.objects.create(campaign=self.other, kind='journals', resource_id=str(journal.pk),
                                                grants={'default': 'none'})
        self.update(journal, visibility='private')
        self.restore(journal, Revision.objects.get(journal_id=journal.pk, version=1))
        policy.refresh_from_db()
        foreign.refresh_from_db()
        journal.refresh_from_db()
        self.assertEqual((journal.visibility, policy.grants), ('shared', {'default': 'read', str(self.player.pk): 'none'}))
        self.assertEqual(foreign.grants, {'default': 'none'})
        self.assertEqual(services.state(self.campaign.pk, self.player.pk)['journals'], [])

    def test_restore_repairs_existing_private_public_acl_mismatch_but_normal_updates_preserve_custom_defaults(self):
        private = data.empty_data_for('diary')
        private['content'] = fixtures.doc(fixtures.paragraph('PRIVATE_REVISION_FROM_OLD_STATE'))
        journal = self.create(data=private)
        self.update(journal, title='New private draft', data={'content': fixtures.doc(fixtures.paragraph('Current draft'))})
        old = Revision.objects.get(journal_id=journal.pk, version=1)
        policy = DocumentAccess.objects.create(campaign=self.campaign, kind='journals', resource_id=str(journal.pk),
                                               grants={'default': 'limited', str(self.gm.pk): 'owner'})
        self.update(journal, title='Ordinary private edit')
        policy.refresh_from_db()
        self.assertEqual(policy.grants['default'], 'limited')
        # Earlier buggy restores could leave this mismatch persisted on disk.
        policy.grants['default'] = 'read'
        policy.save(update_fields=['grants'])
        self.restore(journal, old)
        policy.refresh_from_db()
        journal.refresh_from_db()
        self.assertEqual((journal.visibility, policy.grants), ('private', {'default': 'none', str(self.gm.pk): 'owner'}))
        self.assertEqual(services.state(self.campaign.pk, self.player.pk)['journals'], [])
        self.assertIn('PRIVATE_REVISION_FROM_OLD_STATE', str(journal.data))

    def test_restoring_quest_cannot_introduce_a_cycle_or_cross_campaign_reference(self):
        first, second = self.create(kind='quest'), self.create(kind='quest')
        self.command('prerequisites', {'journal_id': str(first.pk), 'version': 1, 'prerequisites': [str(second.pk)]})
        Revision.objects.filter(journal_id=first.pk).update(created_at=timezone.now() - timedelta(minutes=6))
        self.command('prerequisites', {'journal_id': str(first.pk), 'version': 2, 'prerequisites': []})
        old = Revision.objects.get(journal_id=first.pk, version=2)
        self.command('prerequisites', {'journal_id': str(second.pk), 'version': 1, 'prerequisites': [str(first.pk)]})
        before = (Revision.objects.count(), Receipt.objects.count())
        with self.assertRaisesMessage(services.JournalError, 'cycle'):
            self.restore(first, old)
        first.refresh_from_db()
        self.assertEqual((first.version, first.data['prerequisites']), (3, []))
        self.assertEqual((Revision.objects.count(), Receipt.objects.count()), before)
        foreign = Journal.objects.create(campaign=self.other, title='Other campaign quest', type='quest', data=data.empty_data_for('quest'))
        old.data['prerequisites'] = [str(foreign.pk)]
        old.save(update_fields=['data'])
        with self.assertRaisesMessage(services.JournalError, 'Prerequisite quest not found'):
            self.restore(first, old)

    def test_restoring_deleted_quest_cannot_introduce_a_cycle(self):
        first, second = self.create(kind='quest'), self.create(kind='quest')
        self.command('prerequisites', {'journal_id': str(first.pk), 'version': 1, 'prerequisites': [str(second.pk)]})
        deleted = self.trash(first)
        # The other quest can retain this link while its prerequisite is in trash.
        second.data['prerequisites'] = [str(first.pk)]
        second.save(update_fields=['data'])
        with self.assertRaisesMessage(services.JournalError, 'cycle'):
            self.restore_deleted(deleted)
        self.assertFalse(Journal.objects.filter(pk=deleted.journal_id).exists())
        self.assertTrue(Revision.objects.filter(pk=deleted.pk).exists())

    def test_restoring_revision_checks_physical_files_and_live_asset_ownership(self):
        journal, assets = self.asset_document()
        self.update(journal, data=data.empty_data_for('diary'))
        old = Revision.objects.get(journal_id=journal.pk, version=1)
        assets[0].file.storage.delete(assets[0].file.name)
        with self.assertRaisesMessage(services.JournalError, 'files that were removed'):
            self.restore(journal, old)
        journal.refresh_from_db()
        self.assertEqual((journal.version, journal.data['sections']), (2, []))
        foreign = self.create()
        Asset.objects.filter(pk=assets[0].pk).update(journal=foreign)
        with self.assertRaises(services.JournalError):
            self.restore(journal, old)

    def test_missing_second_retained_file_rejects_whole_restore_and_keeps_trash_receipts_and_files(self):
        journal, assets = self.asset_document(2)
        deleted = self.trash(journal)
        assets[1].file.storage.delete(assets[1].file.name)
        before = Receipt.objects.count()
        with patch('gravewright.realtime.dispatch.send') as send, self.captureOnCommitCallbacks(execute=True):
            with self.assertRaisesMessage(services.JournalError, 'files that are missing'):
                self.restore_deleted(deleted)
        send.assert_not_called()
        self.assertFalse(Journal.objects.filter(pk=deleted.journal_id).exists())
        self.assertFalse(Asset.objects.filter(journal_id=deleted.journal_id).exists())
        self.assertTrue(Revision.objects.filter(pk=deleted.pk).exists())
        self.assertEqual(Receipt.objects.count(), before)
        self.assertTrue(assets[0].file.storage.exists(assets[0].file.name))

    def test_invalid_duplicate_or_colliding_retained_ids_never_create_a_partial_journal(self):
        journal, assets = self.asset_document()
        deleted = self.trash(journal)
        original = deepcopy(deleted.retained)
        other = self.create()
        live = Asset.objects.create(journal=other, name='Live asset', content_type='image/png', file=assets[0].file.name)
        for variant in ('invalid', 'duplicate', 'collision'):
            retained = deepcopy(original)
            if variant == 'invalid':
                retained['assets'][0]['id'] = 'not-a-uuid'
            elif variant == 'duplicate':
                retained['assets'].append(deepcopy(retained['assets'][0]))
            else:
                retained['assets'][0]['id'] = str(live.pk)
            deleted.retained = retained
            deleted.save(update_fields=['retained'])
            with self.subTest(variant=variant), self.assertRaises(services.JournalError):
                self.restore_deleted(deleted)
            self.assertFalse(Journal.objects.filter(pk=deleted.journal_id).exists())
            self.assertTrue(Revision.objects.filter(pk=deleted.pk).exists())
            self.assertTrue(Asset.objects.filter(pk=live.pk).exists())

    def test_successful_restore_keeps_files_when_revision_is_deleted_and_retry_is_once(self):
        journal, assets = self.asset_document(2)
        deleted = self.trash(journal)
        request_id = uuid4()
        with self.captureOnCommitCallbacks(execute=True), patch('gravewright.realtime.dispatch.send') as send:
            restored = self.restore_deleted(deleted, request_id)
        self.assertTrue(restored['restored'])
        self.assertFalse(Revision.objects.filter(pk=deleted.pk).exists())
        self.assertEqual(set(Asset.objects.filter(journal_id=deleted.journal_id).values_list('pk', flat=True)), {asset.pk for asset in assets})
        self.assertTrue(all(asset.file.storage.exists(asset.file.name) for asset in assets))
        with self.captureOnCommitCallbacks(execute=True), patch('gravewright.realtime.dispatch.send') as send:
            self.assertEqual(self.restore_deleted(deleted, request_id), restored)
        send.assert_not_called()

    def test_purge_releases_files_only_after_commit_and_retry_has_no_second_callback(self):
        journal, assets = self.asset_document()
        deleted = self.trash(journal)
        request_id = uuid4()
        with self.captureOnCommitCallbacks(execute=True):
            result = services.command(self.campaign.pk, self.gm.pk, 'trash-purge', {'revision_id': str(deleted.pk)}, request_id)
            self.assertTrue(assets[0].file.storage.exists(assets[0].file.name))
        self.assertFalse(assets[0].file.storage.exists(assets[0].file.name))
        with self.captureOnCommitCallbacks(execute=True), patch('gravewright.realtime.dispatch.send') as send:
            self.assertEqual(services.command(self.campaign.pk, self.gm.pk, 'trash-purge', {'revision_id': str(deleted.pk)}, request_id), result)
        send.assert_not_called()

    def test_rollback_keeps_retained_revision_and_file_and_discards_callbacks(self):
        journal, assets = self.asset_document()
        deleted = self.trash(journal)
        before = Receipt.objects.count()
        with self.captureOnCommitCallbacks(execute=True), patch('gravewright.realtime.dispatch.send') as send:
            with self.assertRaises(RuntimeError), transaction.atomic():
                self.command('trash-purge', {'revision_id': str(deleted.pk)})
                raise RuntimeError('Synthetic rollback')
        send.assert_not_called()
        self.assertTrue(Revision.objects.filter(pk=deleted.pk).exists())
        self.assertTrue(assets[0].file.storage.exists(assets[0].file.name))
        self.assertEqual(Receipt.objects.count(), before)

    def test_campaign_deletion_releases_trashed_files_but_rollback_preserves_them(self):
        journal, assets = self.asset_document()
        deleted = self.trash(journal)
        campaign_id = self.campaign.pk
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError), transaction.atomic():
                self.campaign.delete()
                raise RuntimeError('Synthetic rollback')
        self.assertTrue(Revision.objects.filter(pk=deleted.pk).exists())
        self.assertTrue(assets[0].file.storage.exists(assets[0].file.name))
        self.campaign.pk = campaign_id
        self.campaign.refresh_from_db()
        with self.captureOnCommitCallbacks(execute=True):
            self.campaign.delete()
            self.assertTrue(assets[0].file.storage.exists(assets[0].file.name))
        self.assertFalse(assets[0].file.storage.exists(assets[0].file.name))

    def test_restore_rollback_keeps_trash_and_files_without_receipt_or_notification(self):
        journal, assets = self.asset_document(2)
        deleted = self.trash(journal)
        before = Receipt.objects.count()
        request_id = uuid4()
        with patch('gravewright.realtime.dispatch.send') as send, self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError), transaction.atomic():
                self.restore_deleted(deleted, request_id)
                raise RuntimeError('Synthetic rollback')
        send.assert_not_called()
        self.assertTrue(Revision.objects.filter(pk=deleted.pk).exists())
        self.assertFalse(Journal.objects.filter(pk=deleted.journal_id).exists())
        self.assertFalse(Asset.objects.filter(journal_id=deleted.journal_id).exists())
        self.assertEqual(Receipt.objects.count(), before)
        self.assertTrue(all(asset.file.storage.exists(asset.file.name) for asset in assets))
        self.assertTrue(self.restore_deleted(deleted, request_id)['restored'])

    def test_purge_is_campaign_scoped_and_preserves_a_file_owned_by_another_revision(self):
        journal, assets = self.asset_document()
        deleted = self.trash(journal)
        another = Revision.objects.create(campaign=self.other, journal_id=deleted.journal_id, reason='delete',
            title='Other retained owner', type='diary', visibility='private', data={}, version=1,
            retained=deepcopy(deleted.retained))
        with self.captureOnCommitCallbacks(execute=True):
            self.command('trash-purge', {'revision_id': str(deleted.pk)})
        self.assertTrue(Revision.objects.filter(pk=another.pk).exists())
        self.assertTrue(assets[0].file.storage.exists(assets[0].file.name))
        with self.captureOnCommitCallbacks(execute=True):
            another.delete()
        self.assertFalse(assets[0].file.storage.exists(assets[0].file.name))

    def test_cleanup_rechecks_live_ownership_created_later_in_the_same_transaction(self):
        journal, assets = self.asset_document()
        deleted = self.trash(journal)
        other = self.create()
        with self.captureOnCommitCallbacks(execute=True), transaction.atomic():
            self.command('trash-purge', {'revision_id': str(deleted.pk)})
            live = Asset.objects.create(journal=other, name='New live owner', content_type='image/png', file=assets[0].file.name)
        self.assertTrue(assets[0].file.storage.exists(assets[0].file.name))
        with self.captureOnCommitCallbacks(execute=True):
            live.delete()
        self.assertFalse(assets[0].file.storage.exists(assets[0].file.name))

    def test_players_cannot_restore_or_purge_history_and_failed_commands_create_no_receipts(self):
        journal = self.create()
        self.update(journal)
        old = Revision.objects.get(journal_id=journal.pk)
        self.command('access', {'journal_id': str(journal.pk), 'target_user_id': str(self.player.pk), 'access_level': 'owner'})
        before = Receipt.objects.count()
        with self.assertRaises(services.JournalError):
            self.restore(journal, old, user=self.player)
        deleted = self.trash(journal)
        for action in ('restore-deleted', 'trash-purge'):
            with self.subTest(action=action), self.assertRaises(services.JournalError):
                services.command(self.campaign.pk, self.player.pk, action, {'revision_id': str(deleted.pk)}, uuid4())
        self.assertEqual(Receipt.objects.count(), before + 1)

    def test_coalescing_restores_are_undoable_and_trash_limit_cleans_the_evicted_files(self):
        journal, assets = self.asset_document()
        self.update(journal, title='One')
        self.update(journal, title='Two')
        self.assertEqual(Revision.objects.filter(journal_id=journal.pk, reason='update').count(), 1)
        old = Revision.objects.get(journal_id=journal.pk)
        self.restore(journal, old)
        undo = Revision.objects.filter(journal_id=journal.pk, reason='update').first()
        self.assertEqual(undo.title, 'Two')
        self.restore(journal, undo)
        journal.refresh_from_db()
        self.assertEqual(journal.title, 'Two')
        deleted = self.trash(journal)
        with patch('gravewright.journals.history.TRASH_LIMIT', 2), self.captureOnCommitCallbacks(execute=True):
            for index in range(2):
                next_journal = self.create(title=f'New trash {index}')
                self.command('delete', {'journal_id': str(next_journal.pk)})
        self.assertFalse(Revision.objects.filter(journal_id=deleted.journal_id).exists())
        self.assertEqual(Revision.objects.filter(reason='delete').count(), 2)
        self.assertFalse(assets[0].file.storage.exists(assets[0].file.name))
