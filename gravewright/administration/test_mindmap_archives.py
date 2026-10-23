"""Campaign copies preserve mind-map text and remap each resource namespace."""

from copy import deepcopy
from uuid import uuid4

from django.test import TestCase

from gravewright.accounts.models import User
from gravewright.accounts.services import AuthError
from gravewright.campaigns.models import Campaign, Membership
from gravewright.chat.models import Message
from gravewright.compendiums.models import Pack, Entry
from gravewright.journals.models import Journal, BoardEntry
from gravewright.maps.models import Scene, Tile
from gravewright.table.mindmaps import validate_document
from gravewright.table.models import MindMap, ProgressClock

from .archives import export_campaign, import_campaign, options, read_archive, remap_omitted_bindings
from . import test_clue_archives as clue_fixtures


class MindMapArchiveTests(TestCase):
    rewrite_archive = staticmethod(clue_fixtures.ClueArchiveTests.rewrite_archive)

    def setUp(self):
        self.user = User.objects.create(email='mind-archive@example.test', name='GM')
        self.player = User.objects.create(email='mind-archive-player@example.test', name='Editor')
        self.campaign = Campaign.objects.create(owner=self.user, name='Mind-map archive')
        Membership.objects.create(campaign=self.campaign, user=self.user, role='gm')
        Membership.objects.create(campaign=self.campaign, user=self.player, role='player')
        self.scene = Scene.objects.create(campaign=self.campaign, name='Linked scene', width=400, height=400)
        self.tile = Tile.objects.create(scene=self.scene, lod=0, x=0, y=0, file='')
        self.clock = ProgressClock.objects.create(campaign=self.campaign, name='Clock')
        self.journal = Journal.objects.create(campaign=self.campaign, creator=self.user, title='Quest', type='quest')
        self.board = Journal.objects.create(campaign=self.campaign, creator=self.user, title='Board', type='quest_board')
        self.entry = BoardEntry.objects.create(board=self.board, quest=self.journal)
        self.pack = Pack.objects.create(campaign=self.campaign, name='Content')
        self.pack_entry = Entry.objects.create(pack=self.pack, name='Entry', kind='actor')
        self.message = Message.objects.create(campaign=self.campaign, author=self.user, author_name='GM',
            text='A chat reference', request_id=uuid4())
        self.node_id = str(uuid4())
        self.text = 'Authored resource UUID: ' + str(self.clock.pk)
        self.graph = validate_document({'nodes': [{'id': self.node_id, 'label': self.text, 'notes': self.text,
            'links': [
                {'kind': 'scene', 'id': str(self.scene.pk)},
                {'kind': 'scene-tile', 'id': str(self.tile.pk)},
                {'kind': 'clock', 'id': str(self.clock.pk)},
                {'kind': 'quest-board-entry', 'id': str(self.entry.pk)},
                {'kind': 'journal-page', 'id': str(self.journal.pk), 'pageId': 'page_main'},
                {'kind': 'compendium-entry', 'id': str(self.pack.pk) + '/' + str(self.pack_entry.pk)},
                {'kind': 'chat-message', 'id': str(self.message.pk)},
            ]}], 'edges': []})
        self.row = MindMap.objects.create(campaign=self.campaign, name=self.text, document=deepcopy(self.graph),
                                         editor_ids=[str(self.player.pk)], version=5)
        self.scoped = MindMap.objects.create(campaign=self.campaign, scene=self.scene, name='Scene map', document={'nodes': [], 'edges': []})

    def test_portable_copy_remaps_typed_uuid_integer_composite_and_page_links_and_clears_editors(self):
        clone = import_campaign(export_campaign(self.campaign), self.user, 'Copied maps')
        row = MindMap.objects.get(campaign=clone, name=self.text)
        self.assertNotEqual(row.pk, self.row.pk)
        self.assertEqual(row.editor_ids, [])
        self.assertEqual(row.version, 5)
        node = row.document['nodes'][0]
        self.assertEqual((node['id'], node['label'], node['notes']), (self.node_id, self.text, self.text))
        refs = {ref['kind']: ref for ref in node['links']}
        self.assertEqual(refs['scene']['id'], str(Scene.objects.get(campaign=clone).pk))
        self.assertEqual(refs['scene-tile']['id'], str(Tile.objects.get(scene__campaign=clone).pk))
        self.assertEqual(refs['clock']['id'], str(ProgressClock.objects.get(campaign=clone).pk))
        self.assertEqual(refs['quest-board-entry']['id'], str(BoardEntry.objects.get(board__campaign=clone).pk))
        self.assertEqual(refs['journal-page']['id'], str(Journal.objects.get(campaign=clone, title='Quest').pk))
        self.assertEqual(refs['journal-page']['pageId'], 'page_main')
        pack = Pack.objects.get(campaign=clone)
        self.assertEqual(refs['compendium-entry']['id'], str(pack.pk) + '/' + str(Entry.objects.get(pack=pack).pk))
        self.assertNotEqual(refs['chat-message']['id'], str(self.message.pk))
        self.assertFalse(Message.objects.filter(campaign=clone, pk=refs['chat-message']['id']).exists())
        self.assertEqual(MindMap.objects.get(campaign=clone, name='Scene map').scene.campaign_id, clone.pk)

    def test_snapshot_restores_graph_identity_scope_and_editor_grants(self):
        raw = export_campaign(self.campaign, snapshot=True)
        MindMap.objects.filter(pk=self.row.pk).update(document={'nodes': [], 'edges': []}, editor_ids=[], version=6)
        MindMap.objects.filter(pk=self.scoped.pk).delete()
        import_campaign(raw, self.user, target=self.campaign)
        row = MindMap.objects.get(pk=self.row.pk)
        self.assertEqual(row.document, self.graph)
        self.assertEqual(row.editor_ids, [str(self.player.pk)])
        self.assertEqual(row.version, 5)
        self.assertEqual(MindMap.objects.get(pk=self.scoped.pk).scene_id, self.scene.pk)

    def test_selective_copy_omits_scoped_maps_and_keeps_excluded_links_inert(self):
        raw = export_campaign(self.campaign, {'scenes': False, 'clocks': False})
        clone = import_campaign(raw, self.user, 'Maps without source materials')
        self.assertEqual(MindMap.objects.filter(campaign=clone).count(), 1)
        row = MindMap.objects.get(campaign=clone)
        refs = {ref['kind']: ref for ref in row.document['nodes'][0]['links']}
        self.assertNotEqual(refs['scene']['id'], str(self.scene.pk))
        self.assertNotEqual(refs['clock']['id'], str(self.clock.pk))
        self.assertNotEqual(refs['scene-tile']['id'], str(self.tile.pk))
        self.assertTrue(options()['mindmaps'])
        no_maps = import_campaign(export_campaign(self.campaign, {'mindmaps': False}), self.user, 'No mind maps')
        self.assertFalse(MindMap.objects.filter(campaign=no_maps).exists())

    def test_invalid_graph_editor_scope_and_versions_fail_before_target_changes(self):
        raw = export_campaign(self.campaign, snapshot=True)
        before = list(MindMap.objects.filter(campaign=self.campaign).order_by('id').values())
        bad_document = deepcopy(self.graph)
        bad_document['nodes'][0]['parentId'] = self.node_id
        for change in ({'document': bad_document}, {'editor_ids': [str(self.player.pk)] * 2},
                       {'visibility': 'all'}, {'version': True}, {'scene': str(uuid4())}):
            def update(payload):
                next(row for row in payload['records'] if row['model'] == 'gravewright_table.mindmap')['fields'].update(change)
            with self.subTest(change=change), self.assertRaises(AuthError):
                import_campaign(self.rewrite_archive(raw, update), self.user, target=self.campaign)
            self.assertEqual(list(MindMap.objects.filter(campaign=self.campaign).order_by('id').values()), before)

    def test_missing_numeric_reference_cannot_rebind_to_existing_target_resource(self):
        target = Campaign.objects.create(owner=self.user, name='Existing target')
        Membership.objects.create(campaign=target, user=self.user, role='gm')
        unrelated = Message.objects.create(campaign=target, author=self.user, author_name='GM', text='Unrelated', request_id=uuid4())
        self.row.document['nodes'][0]['links'] = [{'kind': 'chat-message', 'id': str(unrelated.pk)}]
        self.row.save()
        imported = import_campaign(export_campaign(self.campaign), self.user, target=target, merge=True)
        row = MindMap.objects.get(campaign=imported, name=self.text)
        reference = row.document['nodes'][0]['links'][0]
        self.assertNotEqual(reference['id'], str(unrelated.pk))
        self.assertFalse(Message.objects.filter(pk=reference['id'], campaign=target).exists())

    def test_builder_bindings_remap_map_identity_but_preserve_topic_identity_and_authored_text(self):
        original = {'blueprint': {'graphs': {'interact': {'nodes': [
            {'id': 'open', 'type': 'openMindMap', 'mindMapId': str(self.row.pk), 'nodeId': self.node_id,
             'audience': {'scope': 'trigger'}},
            {'id': 'complete', 'type': 'mindMapNode', 'mindMapId': str(self.row.pk), 'nodeId': self.node_id, 'action': 'complete'}]}}}}
        copied = deepcopy(original)
        new_id = str(uuid4())
        remap_omitted_bindings({'model': 'gravewright_maps.sceneobject', 'fields': {'data': original}}, 'data', copied,
                              {('gravewright_table.mindmap', str(self.row.pk)): new_id}, {})
        for node in copied['blueprint']['graphs']['interact']['nodes']:
            self.assertEqual(node['mindMapId'], new_id)
            self.assertEqual(node['nodeId'], self.node_id)
