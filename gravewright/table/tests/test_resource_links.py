"""Resource links retain native recipient projections and typed identities."""

from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

from django.apps import apps
from django.test import TestCase

from gravewright.campaigns.models import Membership
from gravewright.maps.services import MapError
from gravewright.table import resource_links as links
from gravewright.table.tests import test_clocks as clock_fixtures


class ResourceReferenceTests(TestCase):
    def test_canonical_validation_rejects_display_data_and_unbounded_identifiers(self):
        value = str(uuid4())
        self.assertEqual(links.validate_reference({'kind': 'actor', 'id': value.upper()}), {'kind': 'actor', 'id': value})
        for ref in ({'kind': 'actor', 'id': value, 'label': 'Forged'},
                    {'kind': 'actor', 'id': value, 'pageId': 'secret'},
                    {'kind': 'journal-page', 'id': value},
                    {'kind': 'journal-page', 'id': value, 'pageId': 'bad\x00page'},
                    {'kind': 'chat-message', 'id': '0'}, {'kind': 'chat-message', 'id': str(2**63)},
                    {'kind': 'actor', 'id': '../private'}, {'kind': ['actor'], 'id': value},
                    {'kind': 'compendium-entry', 'id': value + '/foreign-name'},
                    {'kind': 'mindmap', 'id': value, 'unavailable': True}):
            with self.subTest(ref=ref), self.assertRaises(MapError):
                links.validate_reference(ref)
        pack = 'native:' + value
        self.assertEqual(links.validate_reference({'kind': 'compendium-entry', 'id': pack + '/spell.fire:rank_2'})['id'], pack + '/spell.fire:rank_2')
        self.assertEqual(links.validate_reference({'kind': 'scene-drawing', 'id': value + '/' + value})['id'], value + '/' + value)
        self.assertEqual(links.validate_reference({'kind': 'journal-page', 'id': value, 'pageId': 'A page/with dots. á'})['pageId'], 'A page/with dots. á')

    def test_registry_has_explicit_typed_archive_metadata_and_implemented_providers(self):
        self.assertGreaterEqual(len(links.RESOURCE_KINDS), 37)
        for kind, spec in links.RESOURCE_KINDS.items():
            with self.subTest(kind=kind):
                self.assertTrue(spec['model'].startswith('gravewright_'))
                self.assertTrue(spec['group'])
                self.assertTrue(hasattr(links.Resolver, '_' + spec['provider'].replace('-', '_')))
                self.assertIn(spec['identifier'], {'uuid', 'integer', 'pack', 'pack-entry', 'scene-fragment'})


class ResourceLinkTests(TestCase):
    setUpTestData = clock_fixtures.ProgressClockTests.__dict__['setUpTestData']

    def who(self, user=None):
        return Membership.objects.select_related('user', 'campaign').get(campaign=self.campaign, user=user or self.gm)

    def resolve(self, kind, row, user=None, **extra):
        return links.resolve(self.who(user), {'kind': kind, 'id': str(row.pk), **extra})

    def test_actor_item_and_folder_links_require_read_not_directory_only_access(self):
        from gravewright.actors.models import Actor, Asset, Folder
        from gravewright.items.models import Item, Folder as ItemFolder
        folder = Folder.objects.create(campaign=self.campaign, name='Read actor folder')
        actor = Actor.objects.create(campaign=self.campaign, folder=folder, name='Read actor', permissions={'default': 'read'})
        secret = Actor.objects.create(campaign=self.campaign, name='PRIVATE_ACTOR', permissions={'default': 'limited'})
        asset = Asset.objects.create(campaign=self.campaign, actor=actor, name='Read PDF', kind='pdf', file='synthetic.pdf')
        hidden = Asset.objects.create(campaign=self.campaign, actor=secret, name='PRIVATE_PDF', kind='pdf', file='private.pdf')
        reusable = Asset.objects.create(campaign=self.campaign, name='Reusable sheet PDF', kind='pdf', file='shared.pdf')
        actor.data = {'pdf': {'asset': str(reusable.pk)}}
        actor.save()
        item_folder = ItemFolder.objects.create(campaign=self.campaign, name='Read item folder')
        item = Item.objects.create(campaign=self.campaign, folder=item_folder, name='Read item', permissions={'default': 'read'})
        for kind, row in [('actor', actor), ('actor-asset', asset), ('actor-folder', folder), ('item', item), ('item-folder', item_folder)]:
            self.assertIsNotNone(self.resolve(kind, row, self.player))
        self.assertIsNone(self.resolve('actor', secret, self.player))
        self.assertIsNone(self.resolve('actor-asset', hidden, self.player))
        self.assertIsNotNone(self.resolve('actor-asset', reusable, self.player))
        foreign = Actor.objects.create(campaign=self.foreign, name='FOREIGN_ACTOR', permissions={'default': 'read'})
        self.assertIsNone(self.resolve('actor', foreign, self.player))
        result = links.catalog(self.who(self.player), kinds=['actor', 'actor-asset', 'item'])
        self.assertNotIn('PRIVATE_', str(result))
        self.assertNotIn('FOREIGN_', str(result))

    def test_journal_pages_assets_and_board_entries_follow_filtered_native_projection(self):
        from gravewright.journals.models import Journal, Asset, Folder, BoardEntry
        from gravewright.journals.documents import EMPTY_DOC
        folder = Folder.objects.create(campaign=self.campaign, name='Public folder')
        journal = Journal.objects.create(campaign=self.campaign, folder=folder, title='Shared journal', visibility='shared')
        public = Asset.objects.create(journal=journal, uploader=self.gm, name='Public attachment', file='public.png', content_type='image/png')
        private = Asset.objects.create(journal=journal, uploader=self.gm, name='PRIVATE_ATTACHMENT', file='private.png', content_type='image/png')
        def image(asset):
            value = deepcopy(EMPTY_DOC)
            value['doc']['content'] = [{'type': 'gwImage', 'attrs': {'src': f'/game/journal/asset/{asset.pk}', 'assetId': str(asset.pk)}}]
            return value
        journal.data = {'sections': [
            {'id': 'public-page', 'title': 'Public page', 'audience': 'public', 'content': image(public)},
            {'id': 'gm-page', 'title': 'PRIVATE_PAGE', 'audience': 'gm', 'content': image(private)}]}
        journal.save()
        self.assertIsNotNone(self.resolve('journal', journal, self.player))
        self.assertIsNotNone(self.resolve('journal-page', journal, self.player, pageId='public-page'))
        self.assertIsNone(self.resolve('journal-page', journal, self.player, pageId='gm-page'))
        self.assertIsNotNone(self.resolve('journal-asset', public, self.player))
        self.assertIsNone(self.resolve('journal-asset', private, self.player))
        self.assertIsNotNone(self.resolve('journal-folder', folder, self.player))
        board = Journal.objects.create(campaign=self.campaign, title='Public board', type='quest_board', visibility='shared')
        quest = Journal.objects.create(campaign=self.campaign, title='Quest card', type='quest', data={'status': 'available'})
        entry = BoardEntry.objects.create(board=board, quest=quest)
        self.assertIsNotNone(self.resolve('quest-board-entry', entry, self.player))
        quest.data = {'status': 'draft'}
        quest.save()
        self.assertIsNone(self.resolve('quest-board-entry', entry, self.player))

    def test_scene_objects_and_tokens_do_not_reveal_gm_layers_or_secret_barriers(self):
        from gravewright.maps.models import SceneObject, SceneState, Tile, MapAsset, AssetFolder, Folder
        from gravewright.maps.objects import wall
        from gravewright.actors.models import Actor
        from gravewright.tokens.models import Token
        from gravewright.combat.models import Encounter
        actor = Actor.objects.create(campaign=self.campaign, name='PRIVATE_ACTOR', permissions={})
        token = Token.objects.create(scene=self.scene, actor=actor, snapshot={'token': {'display': {'name': False}}}, linked=False)
        hidden_token = Token.objects.create(scene=self.scene, actor=actor, hidden=True)
        objects = []
        for kind in ['lights', 'particles', 'images', 'shaders', 'markers', 'journalPins', 'zones']:
            if kind in {'journalPins', 'zones'}:
                continue  # Their rich audience-specific validators are exercised separately.
            objects.append(SceneObject.objects.create(scene=self.scene, kind=kind, data={'name': 'Public ' + kind, 'layer': 'map'}))
        secret = SceneObject.objects.create(scene=self.scene, kind='images', data={'name': 'PRIVATE_IMAGE', 'layer': 'gm'})
        barrier = SceneObject.objects.create(scene=self.scene, kind='walls', data=wall({'x1': 0, 'y1': 0, 'x2': 100, 'y2': 0, 'presentation': 'secret', 'name': 'PRIVATE_DOOR'}))
        ordinary = SceneObject.objects.create(scene=self.scene, kind='walls', data=wall({'x1': 0, 'y1': 100, 'x2': 100, 'y2': 100, 'name': 'Ordinary wall'}))
        tile = Tile.objects.create(scene=self.scene, lod=0, x=0, y=0, file='tile.webp')
        drawing_id = str(uuid4())
        SceneState.objects.create(scene=self.scene, drawings={'rows': [{'id': drawing_id, 'name': 'Public drawing', 'audience': 'campaign'}]})
        Encounter.objects.create(scene=self.scene)
        resolver = links.Resolver(self.who(self.player))
        for row in objects + [ordinary]:
            self.assertIsNotNone(resolver.resolve({'kind': 'scene-object', 'id': str(row.pk)}))
        for row in [secret, barrier]:
            self.assertIsNone(resolver.resolve({'kind': 'scene-object', 'id': str(row.pk)}))
        self.assertEqual(resolver.resolve({'kind': 'token', 'id': str(token.pk)})['label'], 'Tokens')
        self.assertIsNone(resolver.resolve({'kind': 'token', 'id': str(hidden_token.pk)}))
        self.assertIsNotNone(self.resolve('scene', self.scene, self.player))
        self.assertIsNone(self.resolve('scene', self.hidden_scene, self.player))
        self.assertIsNotNone(self.resolve('scene-tile', tile, self.player))
        self.assertIsNotNone(resolver.resolve({'kind': 'encounter', 'id': str(self.scene.pk)}))
        self.assertIsNotNone(resolver.resolve({'kind': 'scene-drawing', 'id': f'{self.scene.pk}/{drawing_id}'}))
        folder = AssetFolder.objects.create(campaign=self.campaign, name='Public image folder')
        asset = MapAsset.objects.create(campaign=self.campaign, folder=folder, name='Visible image', width=10, height=10, file='image.png')
        SceneObject.objects.create(scene=self.scene, kind='images', data={'asset_id': str(asset.pk), 'layer': 'map'})
        self.assertIsNotNone(self.resolve('map-asset', asset, self.player))
        self.assertIsNotNone(self.resolve('asset-folder', folder, self.player))
        scene_folder = Folder.objects.create(campaign=self.campaign, label='GM scene folder')
        self.assertIsNotNone(self.resolve('scene-folder', scene_folder))
        self.assertIsNone(self.resolve('scene-folder', scene_folder, self.player))

    def test_progress_audio_cards_and_private_compendiums_keep_native_audiences(self):
        from gravewright.table.models import ProgressClock, ProgressClue
        from gravewright.audio.models import Track, Playlist
        from gravewright.cards.models import Deck, Card, DeckDefinition, CardAsset
        from gravewright.compendiums.models import Pack, Entry, EntryAsset
        clock = ProgressClock.objects.create(campaign=self.campaign, name='Public clock', visibility='players')
        clue = ProgressClue.objects.create(campaign=self.campaign, name='PRIVATE_CLUE', visibility='players', segments=4, value=3)
        self.assertIsNotNone(self.resolve('clock', clock, self.player))
        self.assertIsNone(self.resolve('clue', clue, self.player))
        clue.value = 4
        clue.save()
        self.assertIsNotNone(self.resolve('clue', clue, self.player))
        track = Track.objects.create(campaign=self.campaign, name='PRIVATE_TRACK', file='track.ogg', content_type='audio/ogg')
        playlist = Playlist.objects.create(campaign=self.campaign, name='PRIVATE_PLAYLIST')
        self.assertIsNotNone(self.resolve('track', track))
        self.assertIsNotNone(self.resolve('playlist', playlist))
        self.assertIsNone(self.resolve('track', track, self.player))
        self.assertIsNone(self.resolve('playlist', playlist, self.player))
        deck = Deck.objects.create(campaign=self.campaign, name='Public deck')
        private_card = Card.objects.create(deck=deck, name='PRIVATE_CARD', zone='hand', owner=self.gm)
        card = Card.objects.create(deck=deck, name='Player card', zone='hand', owner=self.player)
        definition = DeckDefinition.objects.create(campaign=self.campaign, name='PRIVATE_DEFINITION')
        asset = CardAsset.objects.create(campaign=self.campaign, uploader=self.gm, file='card.webp', purpose='card_front')
        self.assertIsNotNone(self.resolve('deck', deck, self.player))
        self.assertIsNotNone(self.resolve('card', card, self.player))
        self.assertIsNone(self.resolve('card', private_card, self.player))
        self.assertIsNotNone(self.resolve('deck-definition', definition))
        self.assertIsNotNone(self.resolve('card-asset', asset))
        self.assertIsNone(self.resolve('deck-definition', definition, self.player))
        pack = Pack.objects.create(campaign=self.campaign, name='PRIVATE_PACK')
        entry = Entry.objects.create(pack=pack, name='PRIVATE_ENTRY', kind='journal')
        entry_asset = EntryAsset.objects.create(entry=entry, source_id=uuid4(), kind='pdf', name='PRIVATE_ENTRY_ASSET', file='entry.pdf')
        reference = {'kind': 'compendium-entry', 'id': f'{pack.pk}/{entry.pk}'}
        self.assertIsNone(links.resolve(self.who(self.player), reference))
        self.assertIsNone(self.resolve('compendium-asset', entry_asset, self.player))
        pack.shared = True
        pack.save()
        self.assertIsNotNone(self.resolve('compendium', pack, self.player))
        self.assertEqual(links.resolve(self.who(self.player), reference)['label'], entry.name)
        self.assertIsNotNone(self.resolve('compendium-asset', entry_asset, self.player))

    def test_installed_opaque_compendium_entry_ids_use_authorized_native_catalog(self):
        pack_id = 'native:' + str(uuid4())
        reference = {'kind': 'compendium-entry', 'id': pack_id + '/spell.fire:rank_2'}
        projected = {'packs': [{'id': pack_id, 'name': 'Approved installed pack',
                               'entries': [{'id': 'spell.fire:rank_2', 'name': 'Approved entry'}]}]}
        with patch('gravewright.compendiums.services.state', return_value=projected) as native:
            self.assertEqual(links.resolve(self.who(self.player), reference)['label'], 'Approved entry')
            self.assertEqual(native.call_args.args[0].user_id, self.player.pk)
        with patch('gravewright.compendiums.services.state', return_value={'packs': []}):
            self.assertIsNone(links.resolve(self.who(self.player), reference))

    def test_installed_compendium_grants_and_revocations_are_checked_by_native_reader(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.conf import settings
        from django.test import override_settings
        from gravewright.compendiums.models import ContentAccess
        scratch_root = Path(settings.BASE_DIR) / 'data' / 'runner'
        scratch_root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=scratch_root) as directory:
            base = Path(directory) / 'synthetic'
            base.mkdir()
            (base / 'index.json').write_text(json.dumps({
                'name': 'Synthetic collection', 'campaigns': [str(self.campaign.pk)],
                'packs': [{'id': 'findings', 'type': 'journal_pack', 'label': 'Synthetic findings',
                           'entries': [{'id': 'finding.east:2', 'name': 'Approved finding'}]}],
            }), encoding='utf-8')
            with override_settings(GRAVEWRIGHT_CONTENT_ROOT=directory):
                resources = links.catalog(self.who(), kinds=['compendium-entry'])['resources']
                self.assertEqual(len(resources), 1)
                reference = {key: resources[0][key] for key in ('kind', 'id')}
                self.assertIsNone(links.resolve(self.who(self.player), reference))
                grant = ContentAccess.objects.create(campaign=self.campaign, collection='synthetic', pack='findings', role='player', level='read')
                self.assertEqual(links.resolve(self.who(self.player), reference)['label'], 'Approved finding')
                grant.delete()
                self.assertIsNone(links.resolve(self.who(self.player), reference))

    def test_all_special_scene_object_audiences_are_filtered_before_linking(self):
        from gravewright.maps.models import SceneObject
        from gravewright.maps.zones import clean
        from gravewright.journals.models import Journal
        from gravewright.audio.models import Track
        journal = Journal.objects.create(campaign=self.campaign, title='Visible journal', visibility='shared')
        visible_pin = SceneObject.objects.create(scene=self.scene, kind='journalPins', data={'public': True, 'journalId': str(journal.pk)})
        private_pin = SceneObject.objects.create(scene=self.scene, kind='journalPins', data={'public': False, 'journalId': str(journal.pk)})
        public_zone = SceneObject.objects.create(scene=self.scene, kind='zones', data=clean({'name': 'Public zone', 'geometry': {'shape': 'rect', 'x': 0, 'y': 0, 'width': 20, 'height': 20}}, self.who()))
        private_zone = SceneObject.objects.create(scene=self.scene, kind='zones', data=clean({'name': 'PRIVATE_ZONE', 'geometry': {'shape': 'rect', 'x': 20, 'y': 20, 'width': 20, 'height': 20}, 'audience': {'kind': 'gm'}}, self.who()))
        track = Track.objects.create(campaign=self.campaign, name='Audible source', file='sound.ogg', content_type='audio/ogg')
        sound = SceneObject.objects.create(scene=self.scene, kind='spatialSounds', data={'trackId': str(track.pk), 'name': 'Sound source', 'x': 10, 'y': 10, 'radius': 10, 'gain': 1, 'enabled': True})
        for row in (visible_pin, public_zone, sound):
            self.assertIsNotNone(self.resolve('scene-object', row, self.player))
        for row in (private_pin, private_zone):
            self.assertIsNone(self.resolve('scene-object', row, self.player))
        foreign = SceneObject.objects.create(scene=self.foreign_scene, kind='images', data={'name': 'FOREIGN_IMAGE'})
        self.assertIsNone(self.resolve('scene-object', foreign, self.player))

    def test_mindmap_editor_read_rights_and_link_resolution_do_not_recurse(self):
        from gravewright.table.models import MindMap
        from gravewright.table import mindmaps
        private = MindMap.objects.create(campaign=self.campaign, name='Private shared with editor', editor_ids=[str(self.player.pk)])
        public = MindMap.objects.create(campaign=self.campaign, name='Public mind map', visibility='players')
        hidden = MindMap.objects.create(campaign=self.campaign, name='PRIVATE_MINDMAP')
        with patch.object(mindmaps, 'project', side_effect=AssertionError('Graph projection must not recurse')):
            self.assertEqual(self.resolve('mindmap', private, self.player)['label'], private.name)
            self.assertIsNone(self.resolve('mindmap', hidden, self.player))
            self.assertIsNotNone(self.resolve('mindmap', public, self.streamer))
            self.assertIsNone(self.resolve('mindmap', private, self.streamer))

    def test_chat_links_survive_the_history_window_without_exposing_hidden_scenes(self):
        from gravewright.chat.models import Message
        first = Message.objects.create(campaign=self.campaign, author=self.gm, author_name='GM', text='Old public message', request_id=uuid4())
        Message.objects.bulk_create([Message(campaign=self.campaign, author=self.gm, author_name='GM', text='New message', request_id=uuid4()) for _ in range(101)])
        self.assertEqual(self.resolve('chat-message', first, self.player)['label'], first.text)
        secret = Message.objects.create(campaign=self.campaign, scene=self.hidden_scene, author=self.gm, author_name='GM', text='PRIVATE_SCENE_MESSAGE', request_id=uuid4())
        self.assertIsNone(self.resolve('chat-message', secret, self.player))

    def test_gm_preparation_templates_and_live_membership(self):
        from gravewright.campaigns.models import SessionPlan, CampaignEvent
        from gravewright.pdf_system.models import MappingTemplate
        from gravewright.maps.models import MapBuilderProject, BlueprintTemplate
        session = SessionPlan.objects.create(campaign=self.campaign, title='PRIVATE_SESSION')
        event = CampaignEvent.objects.create(campaign=self.campaign, title='PRIVATE_EVENT')
        mapping = MappingTemplate.objects.create(campaign=self.campaign, name='PRIVATE_MAPPING')
        project = MapBuilderProject.objects.create(campaign=self.campaign, name='PRIVATE_PROJECT')
        template = BlueprintTemplate.objects.create(campaign=self.campaign, name='PRIVATE_BLUEPRINT', definition={'blueprint': {'kind': 'lever'}})
        for kind, row in [('session-plan', session), ('campaign-event', event), ('pdf-mapping', mapping), ('map-builder-project', project), ('blueprint-template', template)]:
            self.assertIsNotNone(self.resolve(kind, row))
            self.assertIsNone(self.resolve(kind, row, self.player))
        stale = self.who()
        Membership.objects.filter(pk=stale.pk).update(role='player')
        self.assertIsNone(links.resolve(stale, {'kind': 'session-plan', 'id': str(session.pk)}))

    def test_chat_recipients_not_gm_status_control_private_messages(self):
        from gravewright.chat.models import Message, Recipient
        public = Message.objects.create(campaign=self.campaign, author=self.gm, author_name='GM', text='Visible chat', request_id=uuid4())
        private = Message.objects.create(campaign=self.campaign, author=self.player, author_name='Player', text='PRIVATE_WHISPER', visibility='whisper', request_id=uuid4())
        Recipient.objects.create(message=private, user=self.player)
        self.assertIsNotNone(self.resolve('chat-message', public, self.player))
        self.assertIsNotNone(self.resolve('chat-message', private, self.player))
        self.assertIsNone(self.resolve('chat-message', private))
        public.deleted = True
        public.save()
        self.assertIsNone(self.resolve('chat-message', public, self.player))

    def test_caches_are_request_scoped_memoized_and_do_not_expose_mutable_state(self):
        from gravewright.actors.models import Actor
        actor = Actor.objects.create(campaign=self.campaign, name='Current name', permissions={'default': 'read'})
        reference = {'kind': 'actor', 'id': str(actor.pk)}
        from gravewright.actors import services
        with patch.object(services, 'state', wraps=services.state) as native:
            resolver = links.Resolver(self.who(self.player))
            result = resolver.resolve_many([reference] * 200)
            self.assertEqual(native.call_count, 1)
            result[0]['label'] = 'Forged label'
            self.assertEqual(resolver.resolve(reference)['label'], 'Current name')
        actor.name = 'Updated name'
        actor.permissions = {'default': 'none'}
        actor.save()
        self.assertIsNone(links.resolve(self.who(self.player), reference))
        for query, kinds, limit in [(None, None, 80), ('x' * 121, None, 80), ('', ['unknown'], 80), ('', ['actor', 'actor'], 80), ('', None, True), ('', None, 201)]:
            with self.subTest(query=query, kinds=kinds, limit=limit), self.assertRaises(MapError):
                links.catalog(self.who(), query=query, kinds=kinds, limit=limit)
        Actor.objects.create(campaign=self.campaign, name='Another actor')
        result = links.catalog(self.who(), kinds=['actor'], query='', limit=1)
        self.assertEqual(len(result['resources']), 1)
        self.assertTrue(result['truncated'])
