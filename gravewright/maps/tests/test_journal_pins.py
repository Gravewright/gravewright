import uuid
from django.test import TestCase, override_settings
from gravewright.realtime.tests import test_sockets as fixtures
from gravewright.maps import services
from gravewright.maps.models import Scene, SceneObject, Broadcast
from gravewright.journals.models import Journal, BoardEntry
from gravewright.journals.services import JournalError
from gravewright.journals import services as journals
from gravewright.journals.data import normalize_diary_data, empty_data_for


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class JournalPinTests(TestCase):
    def setUp(self):
        fixtures.SocketTests.setUp(self)
        self.scene = Scene.objects.create(campaign=self.campaign, name='Locations', width=800, height=600)
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        self.journal = Journal.objects.create(campaign=self.campaign, title='Travel', visibility='shared',
            data=normalize_diary_data({'sections': [
                {'id': 'market', 'title': 'Market', 'kind': 'text'},
                {'id': 'secret', 'title': 'Hidden vault', 'kind': 'text', 'audience': 'gm'}]}))

    def command(self, action, data, user=None):
        return services.command(self.campaign.pk, (user or self.gm).pk, 'objects',
            {'mapId': str(self.scene.pk), 'area': 'journalPins', 'action': action, 'data': data}, str(uuid.uuid4()))

    def create(self, **data):
        return self.command('create', {'journalId': str(self.journal.pk), 'pageId': 'market', 'x': 100, 'y': 200, **data})['journalPin']

    def state(self, user):
        return services.layer_state(self.campaign.pk, user.pk, self.scene.pk)['journalPins']

    def test_private_share_move_conflict_delete_and_persistence(self):
        pin = self.create()
        self.assertEqual(self.state(self.player), [])
        self.assertEqual(self.state(self.gm)[0]['pageId'], 'market')
        changed = self.command('update', {'id': pin['id'], 'version': pin['version'], 'public': True, 'x': 315.5})['journalPin']
        self.assertEqual(self.state(self.player)[0]['label'], 'Market')
        self.assertEqual(self.state(self.player)[0]['x'], 315.5)
        self.assertEqual(SceneObject.objects.get(pk=pin['id']).data['journalId'], str(self.journal.pk))
        with self.assertRaises(services.MapError):
            self.command('delete', {'id': pin['id'], 'version': pin['version']})
        self.command('delete', {'id': pin['id'], 'version': changed['version']})
        self.assertEqual(self.state(self.gm), [])

    def test_page_and_document_permissions_are_applied_before_serialization(self):
        self.create(public=True)
        self.create(pageId='secret', public=True)
        self.assertEqual(len(self.state(self.gm)), 2)
        self.assertEqual([p['label'] for p in self.state(self.player)], ['Market'])
        self.journal.visibility = 'private'; self.journal.save()
        self.assertEqual(self.state(self.player), [])
        self.journal.delete()
        self.assertEqual(self.state(self.gm), [])

    def test_cross_campaign_missing_page_invalid_values_and_player_edits_rejected(self):
        other = Journal.objects.create(campaign=self.other, title='Other campaign')
        for data in [{'journalId': str(other.pk)}, {'pageId': 'missing'}, {'x': float('nan')}, {'public': 'true'}]:
            with self.assertRaises((services.MapError, JournalError)):
                self.create(**data)
        self.assertEqual(SceneObject.objects.count(), 0)
        with self.assertRaises(services.MapError):
            self.command('create', {'journalId': str(self.journal.pk), 'x': 1, 'y': 2}, self.player)
        pin = self.create()
        for action in ['update', 'delete']:
            with self.assertRaises(services.MapError):
                self.command(action, {'id': pin['id'], 'version': pin['version'], 'public': True}, self.player)

    def test_quest_board_access_and_live_labels(self):
        quest = Journal.objects.create(campaign=self.campaign, title='Missing courier', type='quest', data={**empty_data_for('quest'), 'status': 'available'})
        board = Journal.objects.create(campaign=self.campaign, title='Jobs', type='quest_board', visibility='shared', data=empty_data_for('quest_board'))
        BoardEntry.objects.create(board=board, quest=quest)
        self.create(journalId=str(quest.pk), pageId='', public=True)
        self.assertEqual(self.state(self.player)[0]['label'], 'Missing courier')
        quest.title = 'Courier found'; quest.save()
        self.assertEqual(self.state(self.player)[0]['label'], 'Courier found')
        board.delete()
        self.assertEqual(self.state(self.player), [])

    def test_removed_pages_and_deleted_journals_clean_up_locations(self):
        self.create()
        self.create(pageId='')
        result = journals.command(self.campaign.pk, self.gm.pk, 'update', {
            'journal_id': str(self.journal.pk), 'version': self.journal.version,
            'title': self.journal.title, 'data': {'sections': []}}, str(uuid.uuid4()))
        self.assertTrue(result['map_locations_changed'])
        self.assertEqual(SceneObject.objects.filter(scene=self.scene).count(), 1)
        self.assertEqual(self.state(self.gm)[0]['pageId'], '')
        result = journals.command(self.campaign.pk, self.gm.pk, 'delete', {
            'journal_id': str(self.journal.pk)}, str(uuid.uuid4()))
        self.assertTrue(result['map_locations_changed'])
        self.assertFalse(SceneObject.objects.filter(scene=self.scene).exists())
