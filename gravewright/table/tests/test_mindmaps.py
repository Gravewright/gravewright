"""Mind-map graphs preserve authorization, private links and concurrent edits."""

from copy import deepcopy
from datetime import timedelta
import json
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase, override_settings
from django.utils import timezone

from api import mindmaps
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership, StreamerLink
from gravewright.journals.services import JournalError
from gravewright.maps.models import Broadcast, Scene
from gravewright.maps.services import MapError
from gravewright.modules.frontend import invoke
from gravewright.modules.packages import ModuleFailure
from gravewright.table import mindmaps as service
from gravewright.table.models import MindMap, MindMapReceipt, ProgressClock


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class MindMapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gm = User.objects.create(email='mind-gm@example.test', name='GM', role='owner')
        cls.editor = User.objects.create(email='mind-editor@example.test', name='Editor')
        cls.reader = User.objects.create(email='mind-reader@example.test', name='Reader')
        cls.streamer = User.objects.create(email='mind-streamer@example.test', name='Streamer')
        cls.outsider = User.objects.create(email='mind-outsider@example.test', name='Outsider')
        cls.campaign = Campaign.objects.create(owner=cls.gm, name='Mind-map campaign')
        cls.foreign = Campaign.objects.create(owner=cls.gm, name='Other mind-map campaign')
        for user, role in ((cls.gm, 'gm'), (cls.editor, 'player'), (cls.reader, 'player'), (cls.streamer, 'streamer')):
            Membership.objects.create(campaign=cls.campaign, user=user, role=role)
        Membership.objects.create(campaign=cls.foreign, user=cls.gm, role='gm')
        StreamerLink.objects.create(campaign=cls.campaign, guest=cls.streamer, digest='mind-test-streamer',
                                    expires_at=timezone.now() + timedelta(hours=1))
        cls.scene = Scene.objects.create(campaign=cls.campaign, name='Broadcast', width=500, height=500)
        cls.hidden_scene = Scene.objects.create(campaign=cls.campaign, name='GM scene', visibility='gm', width=500, height=500)
        Broadcast.objects.create(campaign=cls.campaign, scene=cls.scene)
        cls.clock = ProgressClock.objects.create(campaign=cls.campaign, name='PRIVATE_RESOURCE_NAME')
        cls.public_clock = ProgressClock.objects.create(campaign=cls.campaign, name='Public progress', visibility='players')

    def command(self, action, payload, user=None, rid=None):
        return mindmaps.command(self.campaign.pk, (user or self.gm).pk, action, payload, rid or uuid4())

    def graph(self, *, links=None):
        root, child = str(uuid4()), str(uuid4())
        return {'nodes': [{'id': root, 'label': 'Central idea', 'links': links or []},
                          {'id': child, 'parentId': root, 'label': 'A branch', 'x': 300, 'y': 60}],
                'edges': [{'id': str(uuid4()), 'from': root, 'to': child, 'label': 'Relationship'}]}

    def create(self, **extra):
        return self.command('create', {'name': 'Investigation', 'document': self.graph(), **extra})['mindmap']

    def read(self, row, user=None):
        return mindmaps.read(self.campaign.pk, (user or self.gm).pk, row['id'])

    def test_private_default_public_read_and_explicit_editor_access(self):
        private = self.create()
        shared = self.create(name='Public', visibility='players')
        collaborative = self.create(name='Private collaboration', editorIds=[str(self.editor.pk)])
        for user, expected in ((self.gm, {private['id'], shared['id'], collaborative['id']}),
                               (self.editor, {shared['id'], collaborative['id']}),
                               (self.reader, {shared['id']}), (self.streamer, {shared['id']})):
            data = mindmaps.state(self.campaign.pk, user.pk)
            self.assertEqual({row['id'] for row in data['mindmaps']}, expected)
            for row in data['mindmaps']:
                self.assertEqual(row['canConfigure'], user == self.gm)
                self.assertEqual(row['canEdit'], user == self.gm or user == self.editor and row['id'] == collaborative['id'])
                self.assertEqual('editorIds' in row, user == self.gm)
        self.assertEqual({row['id'] for row in mindmaps.state(self.campaign.pk, self.gm.pk)['editors']},
                         {str(self.editor.pk), str(self.reader.pk)})

    def test_authorized_player_can_edit_graph_and_name_but_cannot_change_access_or_delete(self):
        row = self.create(editorIds=[str(self.editor.pk)])
        graph = deepcopy(row['document'])
        graph['nodes'][0]['label'] = 'Player-authored clue'
        updated = self.command('update', {'id': row['id'], 'version': 1, 'name': 'Collaborative notes',
                                          'document': graph}, self.editor)['mindmap']
        self.assertEqual(updated['version'], 2)
        self.assertEqual(updated['document']['nodes'][0]['label'], 'Player-authored clue')
        for changes in ({'visibility': 'players'}, {'editorIds': []}, {'scopeSceneId': None}):
            with self.subTest(changes=changes), self.assertRaises(MapError):
                self.command('update', {'id': row['id'], 'version': 2, **changes}, self.editor)
        with self.assertRaises(MapError):
            self.command('delete', {'id': row['id'], 'version': 2}, self.editor)
        self.assertEqual(MindMap.objects.get(pk=row['id']).version, 2)

    def test_readers_streamers_and_outsiders_cannot_mutate(self):
        row = self.create(visibility='players')
        for user in (self.reader, self.streamer, self.outsider):
            for action, payload in (('create', {'name': 'Forged'}), ('update', {'id': row['id'], 'version': 1, 'name': 'Forged'}),
                                     ('node', {'id': row['id'], 'version': 1, 'nodeId': row['document']['nodes'][0]['id'],
                                               'patch': {'completed': True}}), ('delete', {'id': row['id'], 'version': 1})):
                with self.subTest(user=user.name, action=action), self.assertRaises((MapError, JournalError)):
                    self.command(action, payload, user)
        self.assertEqual(MindMap.objects.get(pk=row['id']).version, 1)

    def test_live_revocation_removes_access_and_rejects_receipt_replay(self):
        row = self.create(editorIds=[str(self.editor.pk)])
        rid = uuid4()
        payload = {'id': row['id'], 'version': 1, 'name': 'Player edit'}
        first = self.command('update', payload, self.editor, rid)
        self.assertEqual(self.command('update', payload, self.editor, rid), first)
        self.command('update', {'id': row['id'], 'version': 2, 'editorIds': []})
        for read in (lambda: self.read(row, self.editor), lambda: self.command('update', payload, self.editor, rid)):
            with self.assertRaises(MapError):
                read()
        self.assertEqual(MindMap.objects.get(pk=row['id']).name, 'Player edit')

    def test_scope_checks_hide_private_scenes_even_for_collaborating_players(self):
        global_map = self.create()
        scoped = self.create(scopeSceneId=str(self.scene.pk), visibility='players')
        hidden = self.create(scopeSceneId=str(self.hidden_scene.pk), editorIds=[str(self.editor.pk)])
        state = mindmaps.state(self.campaign.pk, self.editor.pk)
        self.assertEqual([row['id'] for row in state['mindmaps']], [scoped['id']])
        self.assertNotIn(hidden['id'], str(state))
        with self.assertRaises(MapError):
            self.read(hidden, self.editor)
        self.assertEqual(len(mindmaps.state(self.campaign.pk, self.gm.pk, self.scene.pk)['mindmaps']), 2)
        with self.assertRaises(MapError):
            self.command('update', {'id': hidden['id'], 'version': 1, 'sceneId': str(self.scene.pk), 'name': 'Wrong scope'})
        self.assertIsNone(self.read(global_map)['sceneId'])

    def test_private_link_identity_names_and_urls_are_absent_from_player_payload(self):
        graph = self.graph(links=[{'kind': 'clock', 'id': str(self.clock.pk)}, {'kind': 'clock', 'id': str(self.public_clock.pk)}])
        row = self.create(document=graph, editorIds=[str(self.editor.pk)], visibility='players')
        player = self.read(row, self.editor)
        link = player['document']['nodes'][0]['links'][0]
        self.assertEqual(set(link), {'unavailable', 'key'})
        self.assertTrue(link['unavailable'])
        self.assertNotIn(str(self.clock.pk), json.dumps(player))
        self.assertNotIn(self.clock.name, json.dumps(player))
        self.assertEqual(player['document']['nodes'][0]['links'][1]['label'], self.public_clock.name)
        player['document']['nodes'][0]['notes'] = 'An authorized editor can keep an unavailable link'
        self.command('update', {'id': row['id'], 'version': 1, 'document': player['document']}, self.editor)
        stored = MindMap.objects.get(pk=row['id'])
        self.assertEqual(stored.document['nodes'][0]['links'][0], {'kind': 'clock', 'id': str(self.clock.pk)})

    def test_redacted_link_tokens_cannot_be_forged_transplanted_or_used_with_stale_version(self):
        row = self.create(document=self.graph(links=[{'kind': 'clock', 'id': str(self.clock.pk)}]), editorIds=[str(self.editor.pk)])
        player = self.read(row, self.editor)
        for tamper in ('forge', 'transplant'):
            graph = deepcopy(player['document'])
            if tamper == 'forge':
                graph['nodes'][0]['links'][0]['key'] = '0' * 64
            else:
                graph['nodes'][1]['links'] = graph['nodes'][0]['links']
            with self.subTest(tamper=tamper), self.assertRaises(MapError):
                self.command('update', {'id': row['id'], 'version': 1, 'document': graph}, self.editor)
        self.command('node', {'id': row['id'], 'version': 1, 'nodeId': player['document']['nodes'][0]['id'], 'patch': {'completed': True}})
        with self.assertRaises(MapError):
            self.command('update', {'id': row['id'], 'version': 1, 'document': player['document']}, self.editor)
        self.assertEqual(player['document']['nodes'][0]['links'][0]['key'],
                         self.read(row, self.editor)['document']['nodes'][0]['links'][0]['key'])

    def test_link_access_is_rechecked_on_reads_and_receipt_replays(self):
        row = self.create(document=self.graph(links=[{'kind': 'clock', 'id': str(self.public_clock.pk)}]), editorIds=[str(self.editor.pk)])
        rid = uuid4()
        payload = {'id': row['id'], 'version': 1, 'name': 'A player retry'}
        self.command('update', payload, self.editor, rid)
        ProgressClock.objects.filter(pk=self.public_clock.pk).update(visibility='gm', name='REVOKED_NAME')
        for result in (self.read(row, self.editor), self.command('update', payload, self.editor, rid)['mindmap']):
            serialized = json.dumps(result)
            self.assertNotIn(str(self.public_clock.pk), serialized)
            self.assertNotIn('Public progress', serialized)
            self.assertNotIn('REVOKED_NAME', serialized)

    def test_new_hidden_foreign_missing_and_forged_display_links_are_rejected(self):
        foreign = ProgressClock.objects.create(campaign=self.foreign, name='FOREIGN_SECRET', visibility='players')
        row = self.create(editorIds=[str(self.editor.pk)])
        for target in (self.clock.pk, foreign.pk, uuid4()):
            with self.subTest(target=target), self.assertRaises(MapError):
                self.command('update', {'id': row['id'], 'version': 1,
                    'document': self.graph(links=[{'kind': 'clock', 'id': str(target), 'label': 'Forged safe name'}])}, self.editor)
        with self.assertRaises(MapError):
            self.create(document=self.graph(links=[{'kind': 'clock', 'id': str(foreign.pk)}]))

    def test_graph_structure_types_limits_and_cycles_are_validated_atomically(self):
        row = self.create()
        cases = []
        for value in (True, None, {}, 'x', float('inf'), 100001):
            graph = self.graph()
            graph['nodes'][0]['x'] = value
            cases.append(graph)
        graph = self.graph(); graph['nodes'][0]['parentId'] = graph['nodes'][1]['id']; cases.append(graph)
        graph = self.graph(); graph['nodes'][0]['parentId'] = str(uuid4()); cases.append(graph)
        graph = self.graph(); graph['nodes'].append(deepcopy(graph['nodes'][0])); cases.append(graph)
        graph = self.graph(); graph['edges'][0]['to'] = str(uuid4()); cases.append(graph)
        graph = self.graph(); graph['nodes'][0]['completed'] = 1; cases.append(graph)
        graph = self.graph(); graph['nodes'][0]['notes'] = 'x' * 8001; cases.append(graph)
        graph = self.graph(); graph['nodes'][0]['label'] = ' '; cases.append(graph)
        graph = self.graph(); graph['nodes'][0]['script'] = '<script>'; cases.append(graph)
        graph = self.graph(); graph['nodes'][0]['links'] = [{}] * 17; cases.append(graph)
        for graph in cases:
            with self.subTest(graph=repr(graph)[:100]), self.assertRaises(MapError):
                self.command('update', {'id': row['id'], 'version': 1, 'document': graph})
        self.assertEqual(MindMap.objects.get(pk=row['id']).version, 1)
        self.assertEqual(MindMapReceipt.objects.count(), 1)

    def test_node_patch_preserves_other_topics_and_rejects_cycles_and_stale_revisions(self):
        row = self.create(editorIds=[str(self.editor.pk)])
        root, child = row['document']['nodes']
        updated = self.command('node', {'id': row['id'], 'version': 1, 'nodeId': child['id'],
                              'patch': {'completed': True, 'collapsed': True}}, self.editor)['mindmap']
        self.assertTrue(updated['document']['nodes'][1]['completed'])
        self.assertEqual(updated['document']['nodes'][0], root)
        for version in (True, '2', 1, None):
            with self.subTest(version=version), self.assertRaises(MapError) as error:
                self.command('node', {'id': row['id'], 'version': version, 'nodeId': child['id'], 'patch': {'completed': False}})
            self.assertEqual(error.exception.code, 'conflict')
        with self.assertRaises(MapError):
            self.command('node', {'id': row['id'], 'version': 2, 'nodeId': root['id'], 'patch': {'parentId': child['id']}})

    def test_editor_list_is_strict_and_cannot_grant_streamers_or_other_campaigns(self):
        for editors in (None, True, [str(self.streamer.pk)], [str(self.outsider.pk)], [str(self.gm.pk)],
                        [str(self.editor.pk)] * 2, ['bad']):
            with self.subTest(editors=editors), self.assertRaises(MapError):
                self.create(editorIds=editors)
        self.assertFalse(MindMap.objects.exists())

    def test_domain_notifications_are_after_commit_and_retries_do_not_publish_again(self):
        rid = uuid4()
        payload = {'name': 'Committed graph'}
        with patch('gravewright.realtime.dispatch.send') as send:
            with self.captureOnCommitCallbacks(execute=True):
                first = self.command('create', payload, rid=rid)
                send.assert_not_called()
            send.assert_called_once_with(self.campaign.pk, {'type': 'room.resources', 'module': 'mindmaps'})
            self.command('create', payload, rid=rid)
            self.assertEqual(send.call_count, 1)
        self.assertEqual(first['version'], 1)
        self.assertEqual(MindMap.objects.count(), 1)

    def test_campaign_map_limit_is_independent_of_other_campaigns(self):
        MindMap.objects.bulk_create([MindMap(campaign=self.campaign, name=f'Map {i}', document=deepcopy(service.DEFAULT_DOCUMENT))
                                     for i in range(64)])
        with self.assertRaises(MapError):
            self.create()
        self.assertEqual(mindmaps.command(self.foreign.pk, self.gm.pk, 'create', {'name': 'Independent'}, uuid4())['version'], 1)

    def test_native_sdk_reads_share_permissions_and_bound_scene_contexts(self):
        row = self.create(visibility='players')
        self.assertEqual(invoke(self.campaign.pk, self.reader.pk, 'mindmaps', 'read', {'id': row['id']})['id'], row['id'])
        with self.assertRaises(ModuleFailure) as error:
            invoke(self.campaign.pk, self.gm.pk, 'mindmaps', 'create', {'name': 'Wrong scope',
                'scopeSceneId': str(self.hidden_scene.pk)}, uuid4(), self.scene.pk)
        self.assertEqual(error.exception.code, 'stale_context')
        with self.assertRaises(ModuleFailure):
            invoke(self.campaign.pk, self.reader.pk, 'mindmaps', 'resources', {'userId': str(self.gm.pk)})
        for method in ('read', 'state', 'resources', 'resolve'):
            with self.subTest(method=method), self.assertRaises(ModuleFailure):
                invoke(self.campaign.pk, self.gm.pk, 'mindmaps', method,
                       {'sceneId': str(self.scene.pk), 'mapId': str(self.hidden_scene.pk), 'id': row['id']})

    def test_native_read_http_route_uses_auth_and_no_store(self):
        row = self.create(visibility='players')
        base = f'/api/containers/{self.campaign.pk}/mindmaps-read/read'
        self.assertEqual(self.client.get(base, {'payload': json.dumps({'id': row['id']})}).status_code, 403)
        self.client.force_login(self.reader)
        response = self.client.get(base, {'payload': json.dumps({'id': row['id']})})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['id'], row['id'])
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(self.client.get(base, {'payload': '[]'}).status_code, 400)
        self.assertEqual(self.client.get(base, {'payload': '{broken'}).status_code, 400)
