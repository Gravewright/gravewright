"""Typed journal links survive portable copies, selective imports and history."""

from copy import deepcopy
from uuid import uuid4

from django.core.files.base import ContentFile
from django.test import TestCase

from gravewright.accounts.models import User
from gravewright.accounts.services import AuthError
from gravewright.actors.models import Actor
from gravewright.campaigns.models import Campaign, Membership
from gravewright.chat.models import Message
from gravewright.compendiums.models import Pack, Entry
from gravewright.journals.models import Asset, BoardEntry, Journal, Revision
from gravewright.maps.models import Scene, Tile
from gravewright.table.models import MindMap, ProgressClock

from .archives import export_campaign, import_campaign, read_archive
from . import test_clue_archives as fixtures
from .journal_archives import references


class JournalResourceArchiveTests(TestCase):
    rewrite_archive = staticmethod(fixtures.ClueArchiveTests.rewrite_archive)

    def setUp(self):
        self.gm = User.objects.create(email='journal-link-archive@example.test', name='GM')
        self.campaign = Campaign.objects.create(owner=self.gm, name='Typed journal archive')
        Membership.objects.create(campaign=self.campaign, user=self.gm, role='gm')
        self.scene = Scene.objects.create(campaign=self.campaign, name='Scene', width=200, height=200)
        self.tile = Tile.objects.create(scene=self.scene, lod=0, x=0, y=0, file='')
        self.actor = Actor.objects.create(campaign=self.campaign, name='Actor')
        self.clock = ProgressClock.objects.create(campaign=self.campaign, name='Clock')
        self.text = 'Authored identity ' + str(self.clock.pk)
        self.target = Journal.objects.create(campaign=self.campaign, creator=self.gm, title='Linked page',
            data={'sections': [{'id': str(self.clock.pk), 'title': 'A local UUID-looking page', 'kind': 'text'}]})
        self.board = Journal.objects.create(campaign=self.campaign, creator=self.gm, title='Board', type='quest_board')
        self.quest = Journal.objects.create(campaign=self.campaign, creator=self.gm, title='Quest', type='quest')
        self.board_entry = BoardEntry.objects.create(board=self.board, quest=self.quest)
        self.pack = Pack.objects.create(campaign=self.campaign, name='Pack')
        self.entry = Entry.objects.create(pack=self.pack, name='Entry', kind='actor')
        self.mindmap = MindMap.objects.create(campaign=self.campaign, name='Mind map', document={'nodes': [], 'edges': []})
        self.message = Message.objects.create(campaign=self.campaign, author=self.gm, author_name='GM',
                                             text='Synthetic message', request_id=uuid4())
        self.source = Journal.objects.create(campaign=self.campaign, creator=self.gm, title=self.text)
        self.asset = Asset.objects.create(journal=self.source, uploader=self.gm, name='Synthetic attachment',
            content_type='image/png', file=ContentFile(b'Synthetic test-only bytes', name='synthetic.png'))
        self.refs = [
            {'kind': 'actor', 'id': str(self.actor.pk)},
            {'kind': 'journal', 'id': str(self.source.pk)},
            {'kind': 'journal-page', 'id': str(self.target.pk), 'pageId': str(self.clock.pk)},
            {'kind': 'journal-asset', 'id': str(self.asset.pk)},
            {'kind': 'scene', 'id': str(self.scene.pk)},
            {'kind': 'scene-tile', 'id': str(self.tile.pk)},
            {'kind': 'clock', 'id': str(self.clock.pk)},
            {'kind': 'quest-board-entry', 'id': str(self.board_entry.pk)},
            {'kind': 'compendium-entry', 'id': str(self.pack.pk) + '/' + str(self.entry.pk)},
            {'kind': 'mindmap', 'id': str(self.mindmap.pk)},
            {'kind': 'chat-message', 'id': str(self.message.pk)},
        ]
        nodes = [{'type': 'text', 'text': self.text}] + [
            {'type': 'gwResourceLink', 'attrs': {'reference': ref}} for ref in self.refs]
        self.data = {'content': {'format': 'gw-journal-doc-v1', 'version': 1,
            'doc': {'type': 'doc', 'content': [{'type': 'paragraph', 'content': nodes}]}},
            'cover': {'assetId': str(self.asset.pk), 'src': '/game/journal/asset/' + str(self.asset.pk)},
            'chapters': [
                {'id': str(self.actor.pk), 'name': self.text, 'parentId': None, 'sortOrder': 10},
                {'id': str(self.clock.pk), 'name': 'An empty child', 'parentId': str(self.actor.pk), 'sortOrder': 10},
                {'id': 'empty-root', 'name': 'An empty root', 'parentId': None, 'sortOrder': 20},
            ],
            'sections': [{'id': str(self.clock.pk), 'title': self.text, 'kind': 'text',
                'chapterId': str(self.actor.pk), 'category': self.text,
                'content': {'format': 'gw-journal-doc-v1', 'version': 1, 'doc': {'type': 'doc', 'content': []}}}]}
        self.source.data = deepcopy(self.data)
        self.source.save(update_fields=['data'])
        self.revision = Revision.objects.create(campaign=self.campaign, journal_id=self.source.pk, author=self.gm,
            reason='update', title=self.text, type='diary', visibility='private', data=deepcopy(self.data), version=1)

    def mapped_refs(self, row):
        return {node['attrs']['reference']['kind']: node['attrs']['reference'] for node in references(row.data)}

    def test_copy_rebinds_uuid_numeric_composite_links_and_preserves_authored_text_and_local_page_ids(self):
        clone = import_campaign(export_campaign(self.campaign), self.gm, 'Copied journal links')
        journal = Journal.objects.get(campaign=clone, title=self.text)
        refs = self.mapped_refs(journal)
        self.assertEqual(journal.data['content']['doc']['content'][0]['content'][0]['text'], self.text)
        self.assertEqual(journal.data['sections'][0]['id'], str(self.clock.pk))
        self.assertEqual(journal.data['sections'][0]['title'], self.text)
        self.assertEqual(journal.data['chapters'], self.data['chapters'])
        self.assertEqual(journal.data['sections'][0]['chapterId'], str(self.actor.pk))
        self.assertEqual(refs['journal']['id'], str(journal.pk))
        self.assertEqual(refs['actor']['id'], str(Actor.objects.get(campaign=clone).pk))
        self.assertEqual(refs['clock']['id'], str(ProgressClock.objects.get(campaign=clone).pk))
        self.assertEqual(refs['scene-tile']['id'], str(Tile.objects.get(scene__campaign=clone).pk))
        self.assertEqual(refs['quest-board-entry']['id'], str(BoardEntry.objects.get(board__campaign=clone).pk))
        self.assertEqual(refs['journal-page']['id'], str(Journal.objects.get(campaign=clone, title='Linked page').pk))
        self.assertEqual(refs['journal-page']['pageId'], str(self.clock.pk))
        self.assertEqual(Journal.objects.get(campaign=clone, title='Linked page').data['sections'][0]['id'], str(self.clock.pk))
        pack = Pack.objects.get(campaign=clone)
        self.assertEqual(refs['compendium-entry']['id'], str(pack.pk) + '/' + str(Entry.objects.get(pack=pack).pk))
        self.assertEqual(refs['mindmap']['id'], str(MindMap.objects.get(campaign=clone).pk))
        asset = Asset.objects.get(journal=journal)
        self.assertEqual(refs['journal-asset']['id'], str(asset.pk))
        self.assertEqual(journal.data['cover'], {'assetId': str(asset.pk), 'src': '/game/journal/asset/' + str(asset.pk)})
        revision = Revision.objects.get(campaign=clone)
        self.assertEqual(self.mapped_refs(revision), refs)
        self.assertEqual(revision.data['content']['doc']['content'][0]['content'][0]['text'], self.text)
        self.assertEqual(revision.data['chapters'], self.data['chapters'])
        self.assertEqual(revision.data['sections'][0]['chapterId'], str(self.actor.pk))
        self.assertFalse(Message.objects.filter(campaign=clone, pk=refs['chat-message']['id']).exists())

    def test_snapshot_keeps_saved_references_and_authored_content_exact(self):
        raw = export_campaign(self.campaign, snapshot=True)
        Journal.objects.filter(pk=self.source.pk).update(data={}, title='Changed')
        import_campaign(raw, self.gm, target=self.campaign)
        source = Journal.objects.get(pk=self.source.pk)
        self.assertEqual(source.data, self.data)
        self.assertEqual(source.title, self.text)
        self.assertEqual(Revision.objects.get(pk=self.revision.pk).data, self.data)

    def test_selective_merge_never_reuses_excluded_source_resource_ids(self):
        raw = export_campaign(self.campaign, {'scenes': False, 'clocks': False, 'compendiums': False, 'mindmaps': False})
        import_campaign(raw, self.gm, target=self.campaign, merge=True)
        copied = Journal.objects.filter(campaign=self.campaign, title=self.text).exclude(pk=self.source.pk).get()
        refs = self.mapped_refs(copied)
        for kind in ('scene', 'scene-tile', 'clock', 'compendium-entry', 'mindmap', 'chat-message'):
            self.assertNotEqual(refs[kind]['id'], next(ref['id'] for ref in self.refs if ref['kind'] == kind))
        self.assertFalse(Tile.objects.filter(pk=refs['scene-tile']['id']).exists())
        self.assertFalse(ProgressClock.objects.filter(pk=refs['clock']['id']).exists())
        self.assertEqual(copied.data['chapters'], self.data['chapters'])
        self.assertEqual(copied.data['sections'][0]['chapterId'], str(self.actor.pk))
        self.assertEqual(self.mapped_refs(Revision.objects.filter(campaign=self.campaign).exclude(pk=self.revision.pk).get()), refs)

    def test_malformed_chapter_trees_are_rejected_before_snapshot_replaces_data(self):
        raw = export_campaign(self.campaign, snapshot=True)
        for variant in ('cycle', 'missing-parent', 'dangling-page', 'duplicate', 'depth', 'limit',
                        'page-limit', 'duplicate-page', 'colliding-page', 'invalid-data'):
            with self.subTest(variant=variant):
                def change(payload):
                    row = next(record for record in payload['records'] if record['model'] == 'gravewright_journals.journal'
                               and str(record['pk']) == str(self.source.pk))
                    data = row['fields']['data']
                    if variant == 'cycle':
                        data['chapters'][0]['parentId'] = data['chapters'][1]['id']
                    elif variant == 'missing-parent':
                        data['chapters'][0]['parentId'] = 'absent'
                    elif variant == 'dangling-page':
                        data['sections'][0]['chapterId'] = 'absent'
                    elif variant == 'duplicate':
                        data['chapters'].append(deepcopy(data['chapters'][0]))
                    elif variant == 'depth':
                        data['chapters'] = [{'id': f'level_{i}', 'name': f'Level {i}',
                            'parentId': f'level_{i - 1}' if i else None, 'sortOrder': i} for i in range(9)]
                        data['sections'][0]['chapterId'] = 'level_8'
                    elif variant == 'limit':
                        data['chapters'] = [{'id': f'chapter_{i}', 'name': f'Chapter {i}',
                            'parentId': None, 'sortOrder': i} for i in range(129)]
                        data['sections'][0]['chapterId'] = None
                    elif variant == 'page-limit':
                        data['sections'] = [{'id': f'page_{i}', 'chapterId': None} for i in range(65)]
                    elif variant == 'duplicate-page':
                        data['sections'].append(deepcopy(data['sections'][0]))
                    elif variant == 'colliding-page':
                        data['sections'] = [{'id': 'p' * 40 + suffix, 'chapterId': None} for suffix in ('1', '2')]
                    else:
                        row['fields']['data'] = []
                with self.assertRaises(AuthError):
                    import_campaign(self.rewrite_archive(raw, change), self.gm, target=self.campaign)
                self.assertEqual(Journal.objects.get(pk=self.source.pk).data, self.data)
                self.assertEqual(Revision.objects.get(pk=self.revision.pk).data, self.data)

    def test_malformed_or_projected_link_metadata_is_rejected_before_target_changes(self):
        raw = export_campaign(self.campaign, snapshot=True)
        for invalid in ({'kind': 'actor', 'id': 'bad'}, {'kind': 'scene-tile', 'id': '0'},
                        {'unavailable': True, 'key': 'forged'}, {'kind': 'clock', 'id': str(self.clock.pk), 'label': 'Forged'}):
            with self.subTest(invalid=invalid):
                def change(payload):
                    row = next(record for record in payload['records'] if record['model'] == 'gravewright_journals.journal'
                               and str(record['pk']) == str(self.source.pk))
                    next(references(row['fields']['data']))['attrs']['reference'] = invalid
                with self.assertRaises(AuthError):
                    import_campaign(self.rewrite_archive(raw, change), self.gm, target=self.campaign)
                self.assertEqual(Journal.objects.get(pk=self.source.pk).data, self.data)

    def test_invalid_historical_chapter_assignment_is_rejected_before_restore(self):
        raw = export_campaign(self.campaign, snapshot=True)
        def change(payload):
            row = next(record for record in payload['records'] if record['model'] == 'gravewright_journals.revision'
                       and str(record['pk']) == str(self.revision.pk))
            row['fields']['data']['sections'][0]['chapterId'] = 'absent'
        with self.assertRaises(AuthError):
            import_campaign(self.rewrite_archive(raw, change), self.gm, target=self.campaign)
        self.assertEqual(Journal.objects.get(pk=self.source.pk).data, self.data)
        self.assertEqual(Revision.objects.get(pk=self.revision.pk).data, self.data)
