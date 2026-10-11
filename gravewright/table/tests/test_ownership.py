import json
import tempfile
import uuid
from pathlib import Path

from django.test import TestCase, override_settings
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.actors.models import Actor, Folder
from gravewright.actors import services as actors
from gravewright.items.models import Item
from gravewright.items import services as items
from gravewright.journals.models import Journal, Access
from gravewright.journals import services as journals, data as shapes
from gravewright.maps.models import Scene, Broadcast
from gravewright.maps import services as maps
from gravewright.tokens.models import Token
from gravewright.tokens.services import control
from gravewright.cards.models import Deck, Card
from gravewright.table import domain
from gravewright.table.models import DocumentAccess


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'], ALLOWED_HOSTS=['testserver'])
class OwnershipTests(TestCase):
    def setUp(self):
        self.gm = User.objects.create_user('ownership-gm@example.test', 'password-12345', name='GM', role='owner')
        self.player = User.objects.create_user('ownership-player@example.test', 'password-12345', name='Alice')
        self.other = User.objects.create_user('ownership-other@example.test', 'password-12345', name='Bruno')
        self.campaign = Campaign.objects.create(owner=self.gm, name='Ownership')
        for user, role in [(self.gm, 'gm'), (self.player, 'player'), (self.other, 'player')]:
            Membership.objects.create(campaign=self.campaign, user=user, role=role)
        self.actor = Actor.objects.create(campaign=self.campaign, name='Hero', data={'secret': 'private sheet'})
        self.scene = Scene.objects.create(campaign=self.campaign, name='Map', width=800, height=600)
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        self.client.force_login(self.gm)

    def who(self, user=None):
        return journals.member(self.campaign.pk, (user or self.player).pk)

    def test_table_embeds_only_authorized_initial_content_and_escapes_json(self):
        import re
        journal = Journal.objects.create(campaign=self.campaign, title='Private diary', data={
            'sections': [{'id': 'public', 'title': 'Public page'},
                         {'id': 'secret', 'title': 'Hidden GM page', 'audience': 'gm'}]})
        hostile = '</script><script>alert(1)</script>'
        item = Item.objects.create(campaign=self.campaign, name=hostile, type='gear',
                                   system_id=self.campaign.system, permissions={'default': 'read'})
        def snapshot(user):
            self.client.force_login(user)
            response = self.client.get(f'/game/{self.campaign.pk}')
            self.assertEqual(response.status_code, 200)
            self.assertIn('no-store', response['Cache-Control'])
            encoded = re.search(r'<script id="table-initial-content" type="application/json">(.*?)</script>', response.content.decode(), re.S).group(1)
            self.assertNotIn('</script>', encoded)
            return json.loads(encoded)
        gm = snapshot(self.gm)
        self.assertEqual(gm['actors']['actors'][0]['id'], str(self.actor.pk))
        self.assertEqual(gm['journals']['journals'][0]['id'], str(journal.pk))
        self.assertEqual(gm['items']['items'][0]['name'], hostile)
        player = snapshot(self.player)
        self.assertEqual(player['actors']['actors'], [])
        self.assertEqual(player['journals']['journals'], [])
        self.assertEqual(player['items']['items'][0]['id'], str(item.pk))
        journal.visibility = 'shared'; journal.save()
        self.assertNotIn('Hidden GM page', str(snapshot(self.player)))

    def url(self, kind, key):
        return f'/api/containers/{self.campaign.pk}/ownership/{kind}/{key}'

    def save(self, kind, key, permissions, **extra):
        url = self.url(kind, key)
        current = self.client.get(url)
        self.assertEqual(current.status_code, 200, current.content)
        result = self.client.post(url, data=json.dumps({'version': current.json()['version'], 'permissions': permissions, **extra}), content_type='application/json')
        self.assertEqual(result.status_code, 200, result.content)
        return result.json()

    def test_default_explicit_denial_reset_and_token_control(self):
        token = Token.objects.create(scene=self.scene, actor=self.actor)
        self.save('tokens', token.pk, {'default': 'owner', str(self.player.pk): 'none'})
        self.actor.refresh_from_db()
        self.assertFalse(actors.access(self.actor, self.who()))
        self.assertTrue(control(Token.objects.select_related('actor').get(pk=token.pk), self.who(self.other)))
        self.save('actors', self.actor.pk, {'default': 'read'})
        self.actor.refresh_from_db()
        self.assertTrue(actors.access(self.actor, self.who()))
        self.assertFalse(actors.access(self.actor, self.who(), True))
        self.assertFalse(control(Token.objects.select_related('actor').get(pk=token.pk), self.who()))

    def test_limited_lists_metadata_but_blocks_sheet_and_item_data(self):
        self.save('actors', self.actor.pk, {'default': 'limited'})
        entry = actors.state(self.campaign.pk, self.player.pk)['actors'][0]
        self.assertFalse(entry['canOpen'])
        self.assertNotIn('private sheet', json.dumps(entry))
        with self.assertRaises(maps.MapError):
            actors.sheet(self.campaign.pk, self.player.pk, self.actor.pk)
        item = Item.objects.create(campaign=self.campaign, name='Gear', type='gear', system_id='test', data={'secret': 'hidden'}, permissions={'default': 'limited'})
        entry = items.state(self.who())['items'][0]
        self.assertEqual(entry['data'], {})
        self.assertFalse(entry['canOpen'])
        with self.assertRaises(maps.MapError):
            items.get(item.pk, self.who())

    def test_non_gm_and_foreign_campaign_cannot_inspect_or_write(self):
        self.client.force_login(self.player)
        self.assertEqual(self.client.get(self.url('actors', self.actor.pk)).status_code, 403)
        self.assertEqual(self.client.post(self.url('actors', self.actor.pk), '{}', content_type='application/json').status_code, 403)
        self.client.force_login(self.gm)
        foreign = Campaign.objects.create(owner=self.gm, name='Other table')
        actor = Actor.objects.create(campaign=foreign, name='Foreign')
        self.assertEqual(self.client.get(self.url('actors', actor.pk)).status_code, 404)
        self.assertEqual(self.client.get(self.url('actors', 'invalid-id')).status_code, 400)

    def test_revisions_and_untrusted_grants_are_rejected(self):
        url = self.url('actors', self.actor.pk)
        for grants in [{'default': ['owner']}, {'default': 'superuser'}, {str(uuid.uuid4()): 'owner'}]:
            response = self.client.post(url, json.dumps({'version': 1, 'permissions': grants}), content_type='application/json')
            self.assertEqual(response.status_code, 400)
        self.save('actors', self.actor.pk, {'default': 'read'})
        self.assertEqual(self.client.post(url, json.dumps({'version': 1, 'permissions': {'default': 'owner'}}), content_type='application/json').status_code, 409)

    def test_folder_bulk_does_not_change_descendants_and_detects_added_children(self):
        folder = Folder.objects.create(campaign=self.campaign, name='Party')
        child = Folder.objects.create(campaign=self.campaign, parent=folder, name='Secret')
        self.actor.folder = folder; self.actor.save()
        nested = Actor.objects.create(campaign=self.campaign, folder=child, name='Secret')
        self.save('actor-folders', folder.pk, {'default': 'read', str(self.player.pk): 'none'})
        self.actor.refresh_from_db(); nested.refresh_from_db()
        self.assertEqual(self.actor.permissions['default'], 'read')
        self.assertEqual(nested.permissions, {})
        self.save('actor-folders', folder.pk, {str(self.player.pk): 'unchanged'}, reset=[str(self.player.pk)])
        self.actor.refresh_from_db()
        self.assertTrue(actors.access(self.actor, self.who()))
        url = self.url('actor-folders', folder.pk)
        revision = self.client.get(url).json()['version']
        Actor.objects.create(campaign=self.campaign, folder=folder, name='Newcomer')
        self.assertEqual(self.client.post(url, json.dumps({'version': revision, 'permissions': {'default': 'none'}}), content_type='application/json').status_code, 409)

    def test_journal_default_denial_limited_and_page_inheritance(self):
        journal = Journal.objects.create(campaign=self.campaign, title='Book', data=shapes.normalize_diary_data({'sections': [{'id': 'public', 'title': 'Public'}, {'id': 'secret', 'title': 'Secret'}]}))
        self.save('journals', journal.pk, {'default': 'read', str(self.player.pk): 'none'})
        self.assertEqual(journals.state(self.campaign.pk, self.player.pk)['journals'], [])
        self.save('journals', journal.pk, {'default': 'owner'})
        self.save('pages', f'{journal.pk}:secret', {'default': 'none'})
        journal.refresh_from_db()
        projected = journals.projection(journal, self.who())
        self.assertEqual([s['id'] for s in projected['sections']], ['public'])
        self.assertTrue(projected['sections'][0]['can_edit'])
        raw = shapes.normalize_diary_data(journal.data)
        raw['sections'] = [s for s in raw['sections'] if s['id'] == 'public']
        clean = journals.clean_data(raw, journal, self.who())
        self.assertEqual({s['id'] for s in clean['sections']}, {'public', 'secret'})
        self.save('pages', f'{journal.pk}:secret', {'default': 'inherit'})
        self.assertEqual(len(journals.projection(journal, self.who())['sections']), 2)
        self.save('journals', journal.pk, {'default': 'limited'})
        state = journals.state(self.campaign.pk, self.player.pk)['journals'][0]
        self.assertFalse(state['can_open'])
        self.assertNotIn('sections', state)
        with self.assertRaises(journals.JournalError): journals.get(journal.pk, self.who())

    def test_page_observer_cannot_be_rewritten_by_journal_owner(self):
        journal = Journal.objects.create(campaign=self.campaign, title='Book', data=shapes.normalize_diary_data({'sections': [{'id': 'page', 'title': 'Original'}]}))
        self.save('journals', journal.pk, {'default': 'owner'})
        self.save('pages', f'{journal.pk}:page', {'default': 'read'})
        journal.refresh_from_db()
        raw = shapes.normalize_diary_data(journal.data)
        raw['sections'][0]['title'] = 'Tampered'
        self.assertEqual(journals.clean_data(raw, journal, self.who())['sections'][0]['title'], 'Original')

    def test_scene_denial_blocks_manifest_and_broadcast_projection(self):
        self.save('scenes', self.scene.pk, {'default': 'read', str(self.player.pk): 'none'})
        self.assertIsNone(maps.state(self.campaign.pk, self.player.pk)['activeMapId'])
        with self.assertRaises(maps.MapError): maps.scene(self.scene.pk, self.who())
        self.assertEqual(maps.state(self.campaign.pk, self.other.pk)['activeMapId'], str(self.scene.pk))

    def test_denied_deck_cannot_draw_even_with_known_id(self):
        deck = Deck.objects.create(campaign=self.campaign, name='Deck')
        Card.objects.create(deck=deck, name='Ace')
        self.save('cards', deck.pk, {'default': 'none'})
        self.assertEqual(domain.state(self.campaign.pk, self.player.pk, 'cards')['decks'], [])
        with self.assertRaises(maps.MapError): domain.command(self.campaign.pk, self.player.pk, 'cards', 'draw', {'deck_instance_id':str(deck.pk)}, uuid.uuid4())

    def test_compendium_role_policy_and_native_pack(self):
        from gravewright.compendiums.models import Pack
        pack = Pack.objects.create(campaign=self.campaign, name='Pack', shared=True)
        self.save('compendiums', pack.pk, {'default':'read', 'player':'none'})
        self.assertEqual(domain.state(self.campaign.pk, self.player.pk, 'compendiums')['packs'], [])
        with tempfile.TemporaryDirectory() as directory, override_settings(GRAVEWRIGHT_CONTENT_ROOT=directory):
            root = Path(directory)/'test'; root.mkdir()
            (root/'index.json').write_text(json.dumps({'campaigns':[str(self.campaign.pk)], 'packs':[{'id':'heroes','type':'actor_pack','entries':[]}]}))
            native = next(p for p in domain.state(self.campaign.pk, self.gm.pk, 'compendiums')['packs'] if p['id'].startswith('native:'))
            first = self.save('compendiums', native['id'], {'default':'none','player':'read'})
            self.assertEqual(len(domain.state(self.campaign.pk, self.player.pk, 'compendiums')['packs']),1)
            second = self.save('compendiums', native['id'], {'default':'none'})
            self.assertGreater(second['version'], first['version'])
            self.assertEqual(domain.state(self.campaign.pk, self.player.pk, 'compendiums')['packs'], [])

    def test_explicit_quest_denial_cannot_be_bypassed_by_shared_board(self):
        from gravewright.journals.models import BoardEntry
        quest = Journal.objects.create(campaign=self.campaign,title='Quest',type='quest',data={**shapes.empty_data_for('quest'),'status':'available'})
        board = Journal.objects.create(campaign=self.campaign,title='Board',type='quest_board',visibility='shared',data=shapes.empty_data_for('quest_board'))
        BoardEntry.objects.create(board=board,quest=quest)
        self.assertTrue(journals.types.via_board(quest,self.who()))
        self.save('journals',quest.pk,{'default':'none'})
        self.assertFalse(journals.types.via_board(quest,self.who()))
        with self.assertRaises(journals.JournalError): journals.get(quest.pk,self.who())
        self.assertEqual(journals.projection(board,self.who())['board_entries'],[])

    def test_limited_and_hidden_page_block_direct_attachment_urls(self):
        from django.core.files.base import ContentFile
        from gravewright.actors.models import Asset as ActorAsset
        from gravewright.journals.models import Asset
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            portrait = ActorAsset.objects.create(campaign=self.campaign,actor=self.actor,kind='portrait',name='portrait.png',file=ContentFile(b'private portrait',name='portrait.png'))
            journal = Journal.objects.create(campaign=self.campaign,title='Book',visibility='shared')
            asset = Asset.objects.create(journal=journal,uploader=self.gm,name='page.pdf',content_type='application/pdf',file=ContentFile(b'%PDF-private',name='page.pdf'))
            journal.data=shapes.normalize_diary_data({'sections':[{'id':'file','title':'Private attachment','kind':'pdf','assetId':str(asset.pk)}]});journal.save()
            self.save('actors',self.actor.pk,{'default':'limited'})
            self.save('pages',f'{journal.pk}:file',{'default':'none'})
            self.client.force_login(self.player)
            self.assertEqual(self.client.get(f'/game/actors/asset/{portrait.pk}').status_code,404)
            self.assertEqual(self.client.get(f'/game/journal/asset/{asset.pk}').status_code,404)
