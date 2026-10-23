"""Preparation, private history and retained files survive portable campaigns."""

from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import tempfile
from uuid import uuid4

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.accounts.services import AuthError
from gravewright.campaigns import preparation
from gravewright.campaigns.models import Campaign, CampaignEvent, Membership, PreparationBoard, SessionPlan
from gravewright.journals import data as shapes, services as journals
from gravewright.journals.models import Asset, Journal, Revision
from gravewright.maps.models import Scene

from .archives import export_campaign, import_campaign, read_archive
from . import test_clue_archives as archive_fixtures


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PreparationArchiveTests(TestCase):
    rewrite_archive = staticmethod(archive_fixtures.ClueArchiveTests.rewrite_archive)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.media = Path(directory.name)
        media = override_settings(MEDIA_ROOT=directory.name)
        media.enable(); self.addCleanup(media.disable)
        self.gm = User.objects.create(email='prep-copy@example.test', name='Synthetic GM', role='owner')
        self.co_gm = User.objects.create(email='prep-copy-co@example.test', name='Synthetic co-GM')
        self.campaign = Campaign.objects.create(owner=self.gm, name='Preparation archive source')
        Membership.objects.create(campaign=self.campaign, user=self.gm, role='gm')
        Membership.objects.create(campaign=self.campaign, user=self.co_gm, role='gm')
        self.scene = Scene.objects.create(campaign=self.campaign, name='Synthetic harbor', width=100, height=100)
        self.literal = 'Authored literal ' + str(self.scene.pk)
        self.journal = Journal.objects.create(campaign=self.campaign, creator=self.gm, title='History source',
            data={'content': {'format': 'gw-journal-doc-v1', 'version': 1, 'doc': {'type': 'doc', 'content': [
                {'type': 'paragraph', 'content': [{'type': 'text', 'text': self.literal},
                  {'type': 'text', 'text': 'Open scene', 'marks': [{'type': 'link', 'attrs': {
                    'href': f'/game/{self.campaign.pk}?document=scene:{self.scene.pk}'}}]}]}]}}})
        self.command('update', {'journal_id': str(self.journal.pk), 'version': 1, 'title': self.journal.title,
                                'data': {'content': shapes.empty_data_for('diary')['content']}})
        self.session = preparation.command(self.gm, self.campaign.pk, 'session-create', {
            'title': self.literal, 'notes': self.literal, 'scheduledFor': '2026-11-02',
            'steps': [{'kind': 'scene', 'refId': str(self.scene.pk)}, {'kind': 'note', 'label': self.literal}],
            'checklist': [{'text': self.literal}],
        }, uuid4())
        self.event = preparation.command(self.gm, self.campaign.pk, 'event-create', {
            'title': self.literal, 'worldDate': self.literal, 'description': self.literal,
            'links': [{'type': 'journal', 'id': str(self.journal.pk)}],
        }, uuid4())
        for gm, reference in ((self.gm, {'type': 'scene', 'id': str(self.scene.pk)}),
                              (self.co_gm, {'type': 'journal', 'id': str(self.journal.pk)})):
            preparation.command(gm, self.campaign.pk, 'board-update', {
                'revision': 0, 'widgets': ['session', 'pins'], 'pins': [reference],
            }, uuid4())
        self.deleted = Journal.objects.create(campaign=self.campaign, creator=self.gm, title='Trashed synthetic image')
        self.asset = Asset.objects.create(journal=self.deleted, uploader=self.gm, name='Synthetic page',
            content_type='image/png', file=ContentFile(b'synthetic review bytes', name='synthetic.png'))
        document = shapes.empty_data_for('diary')
        document['sections'] = [{'id': 'image-page', 'title': self.literal, 'kind': 'image', 'audience': 'public',
                                'assetId': str(self.asset.pk), 'src': '/game/journal/asset/' + str(self.asset.pk)}]
        self.deleted.data = shapes.normalize_diary_data(document)
        self.deleted.save()
        self.deleted_id, self.asset_id, self.file = self.deleted.pk, self.asset.pk, self.asset.file.name
        self.command('delete', {'journal_id': str(self.deleted.pk)})

    def command(self, action, payload, campaign=None):
        return journals.command((campaign or self.campaign).pk, self.gm.pk, action, payload, uuid4())

    def test_roundtrip_preserves_text_remaps_bindings_and_restores_trashed_files(self):
        raw = export_campaign(self.campaign)
        payload, _ = read_archive(raw)
        self.assertEqual(len(payload['preparation']['dashboards']), 2)
        self.assertIn(self.file, payload['files'])
        clone = import_campaign(raw, self.gm, 'Preparation copy')
        session = SessionPlan.objects.get(campaign=clone)
        scene = Scene.objects.get(campaign=clone)
        self.assertNotEqual(str(session.pk), self.session['id'])
        self.assertEqual((session.title, session.notes, session.checklist[0]['text'], session.steps[1]['label']), (self.literal,) * 4)
        self.assertEqual(session.steps[0]['refId'], str(scene.pk))
        event = CampaignEvent.objects.get(campaign=clone)
        self.assertEqual((event.title, event.world_date, event.description), (self.literal,) * 3)
        live = Journal.objects.get(campaign=clone)
        self.assertEqual(event.links[0]['id'], str(live.pk))
        board = PreparationBoard.objects.get(membership__campaign=clone)
        self.assertEqual(board.pins, [{'type': 'scene', 'id': str(scene.pk)}])
        revision = Revision.objects.get(campaign=clone, reason='update')
        text = revision.data['content']['doc']['content'][0]['content']
        self.assertEqual(text[0]['text'], self.literal)
        self.assertEqual(text[1]['marks'][0]['attrs']['href'], f'/game/{clone.pk}?document=scene:{scene.pk}')
        self.assertIsNone(revision.author_id)
        deleted = Revision.objects.get(campaign=clone, reason='delete')
        self.assertNotEqual(deleted.journal_id, self.deleted_id)
        self.assertNotEqual(deleted.retained['assets'][0]['id'], str(self.asset_id))
        self.assertNotEqual(deleted.retained['assets'][0]['file'], self.file)
        with self.captureOnCommitCallbacks(execute=True):
            restored = self.command('restore-deleted', {'revision_id': str(deleted.pk)}, clone)
        restored_asset = Asset.objects.get(journal_id=restored['journal_id'])
        with restored_asset.file.open('rb') as handle:
            self.assertEqual(handle.read(), b'synthetic review bytes')
        restored_row = Journal.objects.get(pk=restored['journal_id'])
        self.assertEqual(restored_row.data['sections'][0]['assetId'], str(restored_asset.pk))
        self.assertTrue(self.asset.file.storage.exists(self.file))

    def test_snapshot_restores_each_gms_board_history_and_preparation_after_changes(self):
        raw = export_campaign(self.campaign, snapshot=True)
        PreparationBoard.objects.filter(membership__campaign=self.campaign).update(widgets=['pending'])
        SessionPlan.objects.filter(campaign=self.campaign).update(notes='Changed after snapshot')
        CampaignEvent.objects.filter(campaign=self.campaign).delete()
        Revision.objects.filter(campaign=self.campaign, reason='update').delete()
        with self.captureOnCommitCallbacks(execute=True):
            restored = import_campaign(raw, self.gm, target=self.campaign)
        self.assertEqual(SessionPlan.objects.get(campaign=restored).notes, self.literal)
        self.assertEqual(CampaignEvent.objects.filter(campaign=restored).count(), 1)
        self.assertEqual(Revision.objects.filter(campaign=restored).count(), 2)
        self.assertEqual(PreparationBoard.objects.filter(membership__campaign=restored).count(), 2)
        for board in PreparationBoard.objects.filter(membership__campaign=restored):
            self.assertEqual(board.widgets, ['session', 'pins'])
        deleted = Revision.objects.get(campaign=restored, reason='delete')
        self.assertTrue(self.asset.file.storage.exists(deleted.retained['assets'][0]['file']))

    def test_old_archives_do_not_erase_preparation_or_history_they_never_stored(self):
        raw = self.rewrite_archive(export_campaign(self.campaign, snapshot=True), lambda payload: (
            payload.pop('preparation'), payload.update(records=[row for row in payload['records']
                if row['model'] not in {'gravewright_campaigns.sessionplan', 'gravewright_campaigns.campaignevent',
                                         'gravewright_journals.revision'}])))
        import_campaign(raw, self.gm, target=self.campaign)
        self.assertEqual(SessionPlan.objects.filter(campaign=self.campaign).count(), 1)
        self.assertEqual(Revision.objects.filter(campaign=self.campaign).count(), 2)
        self.assertEqual(PreparationBoard.objects.filter(membership__campaign=self.campaign).count(), 2)

    def test_omitted_resources_get_inert_bindings_and_omitted_preparation_is_not_copied(self):
        clone = import_campaign(export_campaign(self.campaign, {'scenes': False}), self.gm, 'Without scenes')
        self.assertNotEqual(SessionPlan.objects.get(campaign=clone).steps[0]['refId'], str(self.scene.pk))
        self.assertFalse(Scene.objects.filter(campaign=clone).exists())
        clone = import_campaign(export_campaign(self.campaign, {'preparation': False, 'journals': False}), self.gm, 'Without preparation')
        self.assertFalse(SessionPlan.objects.filter(campaign=clone).exists())
        self.assertFalse(PreparationBoard.objects.filter(membership__campaign=clone).exists())
        self.assertFalse(Revision.objects.filter(campaign=clone).exists())

    def test_malformed_metadata_or_lists_cannot_replace_campaign_state(self):
        raw = export_campaign(self.campaign, snapshot=True)
        before = (list(SessionPlan.objects.values()), list(Revision.objects.values()))
        def record(payload, label):
            return next(row for row in payload['records'] if row['model'] == label)['fields']
        cases = [
            lambda p: p.update(preparation=None),
            lambda p: p['preparation'].update(version=True),
            lambda p: p['preparation']['dashboards'][0].update(widgets=[{}]),
            lambda p: record(p, 'gravewright_campaigns.sessionplan').update(revision=True),
            lambda p: record(p, 'gravewright_campaigns.sessionplan').update(steps=[{'kind': 'scene'}]),
            lambda p: record(p, 'gravewright_campaigns.sessionplan').update(scheduled_for=True),
            lambda p: record(p, 'gravewright_journals.revision').update(visibility='everybody'),
        ]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(AuthError):
                import_campaign(self.rewrite_archive(raw, change), self.gm, target=self.campaign)
            self.assertEqual((list(SessionPlan.objects.values()), list(Revision.objects.values())), before)

    def test_retained_files_cannot_reference_paths_outside_the_archive(self):
        raw = export_campaign(self.campaign)
        def change(payload):
            deleted = next(row for row in payload['records'] if row['model'] == 'gravewright_journals.revision'
                           and row['fields']['reason'] == 'delete')
            deleted['fields']['retained']['assets'][0]['file'] = 'other-campaign/private.png'
        with self.assertRaises(AuthError):
            import_campaign(self.rewrite_archive(raw, change), self.gm, 'Rejected foreign file')
        self.assertEqual(Campaign.objects.count(), 1)

    def test_merge_preserves_existing_dashboard_and_checks_combined_limits(self):
        target = Campaign.objects.create(owner=self.gm, name='Existing preparation')
        member = Membership.objects.create(campaign=target, user=self.gm, role='gm')
        board = PreparationBoard.objects.create(membership=member, widgets=['pending'], revision=7)
        SessionPlan.objects.bulk_create([SessionPlan(campaign=target, title=f'Existing {index}') for index in range(200)])
        with self.assertRaises(AuthError):
            import_campaign(export_campaign(self.campaign), self.gm, target=target, merge=True)
        self.assertEqual(SessionPlan.objects.filter(campaign=target).count(), 200)
        SessionPlan.objects.filter(campaign=target).delete()
        import_campaign(export_campaign(self.campaign), self.gm, target=target, merge=True)
        board.refresh_from_db()
        self.assertEqual((board.widgets, board.revision), (['pending'], 7))
        self.assertEqual(SessionPlan.objects.filter(campaign=target).count(), 1)

    @override_settings(CAMPAIGN_CLONE_ENABLED=True)
    def test_native_clone_includes_retained_files_and_preparation(self):
        self.client.force_login(self.gm)
        response = self.client.post(f'/api/admin/campaigns/{self.campaign.pk}/clone/create', {
            'title': 'Native preparation copy', 'options': {'preparation': True},
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        campaign = Campaign.objects.get(pk=response.json()['campaignId'])
        self.assertEqual(SessionPlan.objects.filter(campaign=campaign).count(), 1)
        deleted = Revision.objects.get(campaign=campaign, reason='delete')
        self.assertTrue(self.asset.file.storage.exists(deleted.retained['assets'][0]['file']))

    def test_history_dates_and_order_survive_import(self):
        first = Revision.objects.get(campaign=self.campaign, reason='update')
        second = Revision.objects.create(campaign=self.campaign, journal_id=first.journal_id, reason='update',
            title=first.title, type=first.type, visibility=first.visibility, data=first.data, version=2)
        dates = [datetime(2001, 1, 1, microsecond=100, tzinfo=timezone.utc),
                 datetime(2001, 1, 1, microsecond=200, tzinfo=timezone.utc)]
        Revision.objects.filter(pk=first.pk).update(created_at=dates[0])
        Revision.objects.filter(pk=second.pk).update(created_at=dates[1])
        clone = import_campaign(export_campaign(self.campaign), self.gm, 'History chronology copy')
        rows = list(Revision.objects.filter(campaign=clone, reason='update'))
        self.assertEqual([row.version for row in rows], [2, 1])
        self.assertEqual([row.created_at for row in rows], dates[::-1])

    def test_duplicate_retained_owners_and_empty_file_names_are_rejected(self):
        raw = export_campaign(self.campaign)
        def empty_file(payload):
            row = next(row for row in payload['records'] if row['model'] == 'gravewright_journals.revision'
                       and row['fields']['reason'] == 'delete')
            row['fields']['retained']['assets'][0]['file'] = ''
        def duplicated_asset(payload):
            row = deepcopy(next(row for row in payload['records'] if row['model'] == 'gravewright_journals.revision'
                                and row['fields']['reason'] == 'delete'))
            row['pk'] = str(uuid4())
            row['fields']['journal_id'] = str(uuid4())
            payload['records'].append(row)
        for change in (empty_file, duplicated_asset):
            with self.subTest(change=change), self.assertRaises(AuthError):
                import_campaign(self.rewrite_archive(raw, change), self.gm, 'Rejected ownership')
        with self.assertRaises(AuthError):
            export_campaign(self.campaign, include_files=False)
        self.assertEqual(Campaign.objects.count(), 1)

    def test_imported_quest_cycles_are_rejected_atomically(self):
        first = Journal.objects.create(campaign=self.campaign, title='First quest', type='quest')
        second = Journal.objects.create(campaign=self.campaign, title='Second quest', type='quest',
                                        data={'prerequisites': [str(first.pk)]})
        first.data = {'prerequisites': [str(second.pk)]}
        first.save()
        with self.assertRaises(AuthError):
            import_campaign(export_campaign(self.campaign), self.gm, 'Rejected cycle')
        self.assertEqual(Campaign.objects.count(), 1)
