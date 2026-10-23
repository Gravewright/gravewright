"""The browser clue domain retains live GM authority and mounted scene identity."""

import uuid
from unittest.mock import patch

from django.test import TestCase

from gravewright.campaigns.models import Membership
from gravewright.modules.frontend import invoke
from gravewright.modules.packages import ModuleFailure
from gravewright.table.models import ClueReceipt, ProgressClue
from gravewright.table.tests import test_clues as fixtures


class ClueFrontendTests(TestCase):
    setUpTestData = fixtures.ProgressClueTests.__dict__['setUpTestData']

    def call(self, method, payload=None, request_id=None):
        return self.client.post(f'/api/tables/{self.campaign.pk}/api', {
            'domain': 'clues', 'method': method, 'payload': payload or {},
            'requestId': str(request_id or uuid.uuid4()),
        }, content_type='application/json')

    def test_browser_mutations_keep_receipts_and_require_fresh_explicit_revisions(self):
        self.client.force_login(self.gm)
        request_id = uuid.uuid4()
        payload = {'name': 'Browser clue', 'segments': 8, 'gmNotes': 'Private browser notes',
                   'scopeSceneId': None, 'sceneId': str(self.scene.pk), 'mapId': str(self.scene.pk)}
        with patch('gravewright.realtime.dispatch.send') as send, self.captureOnCommitCallbacks(execute=True):
            first = self.call('create', payload, request_id)
        self.assertEqual(first.status_code, 200, first.content)
        clue = first.json()['value']['clue']
        self.assertIsNone(clue['sceneId'])
        self.assertEqual(send.call_args.args[1], {'type': 'room.resources', 'module': 'clues'})
        self.assertEqual(self.call('create', payload, request_id).json(), first.json())
        self.assertEqual(ProgressClue.objects.count(), 1)
        revealed = self.call('reveal', {'id': clue['id'], 'version': 1})
        self.assertEqual(revealed.status_code, 200, revealed.content)
        self.assertEqual((revealed.json()['value']['clue']['value'], revealed.json()['value']['clue']['visibility']), (8, 'players'))
        conflict = self.call('hide', {'id': clue['id'], 'version': 1})
        self.assertEqual(conflict.status_code, 409, conflict.content)
        self.assertEqual(self.call('hide', {'id': clue['id'], 'version': 2}).status_code, 200)

    def test_player_browser_filters_partial_private_foreign_records_and_private_notes(self):
        ProgressClue.objects.create(campaign=self.campaign, name='Never discovered', content='UNREVEALED_CONTENT', value=3)
        ProgressClue.objects.create(campaign=self.campaign, name='Hidden complete', visibility='gm', value=4)
        ProgressClue.objects.create(campaign=self.foreign, name='Foreign campaign', value=4)
        public = ProgressClue.objects.create(campaign=self.campaign, name='Public clue', content='Public content',
                                             gm_notes='NEVER_PUBLIC_NOTES', value=4)
        self.client.force_login(self.player)
        response = self.call('state')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([clue['id'] for clue in response.json()['value']['clues']], [str(public.pk)])
        for secret in ('Never discovered', 'UNREVEALED_CONTENT', 'Hidden complete', 'Foreign campaign', 'NEVER_PUBLIC_NOTES', 'gmNotes'):
            self.assertNotIn(secret, response.content.decode())
        for method in ('create', 'update', 'advance', 'reset', 'delete', 'reveal', 'hide'):
            payload = {'name': 'Forbidden'} if method == 'create' else {'id': str(public.pk), 'version': 1,
                       **({'delta': 1} if method == 'advance' else {})}
            with self.subTest(method=method):
                self.assertEqual(self.call(method, payload).status_code, 403)

    def test_mounted_scene_can_only_create_or_move_within_its_authorized_scope(self):
        for target in (self.other_scene, self.foreign_scene):
            with self.subTest(target=target.pk), self.assertRaises(ModuleFailure) as rejected:
                invoke(self.campaign.pk, self.gm.pk, 'clues', 'create', {
                    'name': 'Bound clue', 'scopeSceneId': str(target.pk),
                }, uuid.uuid4(), scene_id=str(self.scene.pk))
            self.assertEqual(rejected.exception.code, 'stale_context')
        for target in (None, str(self.scene.pk)):
            result = invoke(self.campaign.pk, self.gm.pk, 'clues', 'create', {
                'name': 'Authorized clue', 'scopeSceneId': target,
            }, uuid.uuid4(), scene_id=str(self.scene.pk))
            self.assertEqual(result['clue']['sceneId'], target)

    def test_mounted_context_does_not_move_global_clues_and_cannot_edit_another_scene(self):
        clue = ProgressClue.objects.create(campaign=self.campaign, name='Global clue')
        result = invoke(self.campaign.pk, self.gm.pk, 'clues', 'update', {
            'id': str(clue.pk), 'version': 1, 'name': 'Changed global clue',
        }, uuid.uuid4(), scene_id=str(self.scene.pk))
        self.assertIsNone(result['clue']['sceneId'])
        scoped = ProgressClue.objects.create(campaign=self.campaign, scene=self.other_scene, name='Other scope')
        with self.assertRaises(ModuleFailure) as rejected:
            invoke(self.campaign.pk, self.gm.pk, 'clues', 'reveal', {
                'id': str(scoped.pk), 'version': 1,
            }, uuid.uuid4(), scene_id=str(self.scene.pk))
        self.assertEqual(rejected.exception.code, 'not_found')
        scoped.refresh_from_db()
        self.assertEqual((scoped.value, scoped.version), (0, 1))

    def test_streamer_native_read_route_only_delivers_discovered_clues_without_notes(self):
        ProgressClue.objects.create(campaign=self.campaign, name='Partial clue')
        public = ProgressClue.objects.create(campaign=self.campaign, name='Revealed clue', gm_notes='SECRET_NOTES', value=4)
        self.client.force_login(self.streamer)
        response = self.client.get(f'/api/containers/{self.campaign.pk}/modules-native/clues', {'sceneId': str(self.scene.pk)})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([clue['id'] for clue in response.json()['clues']], [str(public.pk)])
        self.assertFalse(response.json()['clues'][0]['canEdit'] or response.json()['clues'][0]['canConfigure'])
        self.assertNotIn('SECRET_NOTES', response.content.decode())
        self.assertNotIn('gmNotes', response.json()['clues'][0])
        self.assertEqual(self.call('hide', {'id': str(public.pk), 'version': 1}).status_code, 403)
        public.refresh_from_db()
        self.assertEqual(public.visibility, 'players')

    def test_private_receipt_cannot_replay_after_downgrade_directly_or_through_another_domain(self):
        self.client.force_login(self.gm)
        request_id = uuid.uuid4()
        payload = {'name': 'PRIVATE_CLUE_RECEIPT', 'gmNotes': 'PRIVATE_CLUE_NOTES'}
        created = self.call('create', payload, request_id)
        self.assertEqual(created.status_code, 200, created.content)
        self.assertEqual(ClueReceipt.objects.filter(request_id=request_id).count(), 1)
        Membership.objects.filter(campaign=self.campaign, user=self.gm).update(role='player')
        responses = [self.call('create', payload, request_id)]
        for domain, method, data in (('items', 'create', {'name': 'Other', 'type': 'unused'}),
                                     ('clocks', 'create', {'name': 'Other'})):
            responses.append(self.client.post(f'/api/tables/{self.campaign.pk}/api', {
                'domain': domain, 'method': method, 'payload': data, 'requestId': str(request_id),
            }, content_type='application/json'))
        for response in responses:
            self.assertEqual(response.status_code, 403, response.content)
            self.assertNotIn('PRIVATE_CLUE', response.content.decode())
