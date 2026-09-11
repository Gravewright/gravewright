"""Regressions for contracts found missing in the original-game comparison."""
import uuid
from django.test import TestCase
from gravewright.table.tests import test_modules
from gravewright.table import services
from gravewright.maps import objects
from gravewright.maps.services import MapError
from gravewright.journals.models import Journal


class AuditGapTests(TestCase):
    setUp = test_modules.TableModuleTests.setUp
    command = test_modules.TableModuleTests.command
    state = test_modules.TableModuleTests.state

    def test_card_placement_scale_and_order(self):
        deck=self.command('cards','create',{'name':'Deck','cards':['Ace']})['id']
        card=self.command('cards','draw',{'deck_instance_id':deck})['cards'][0]
        placed=self.command('cards','place',{'id':card['id'],'version':card['version'],
            'sceneId':str(self.scene.pk),'x':20,'y':30,'scale':2,'z_index':7})['card']
        self.assertEqual((placed['scale'],placed['z_index']),(2,7))
        who=self.campaign.memberships.get(user=self.gm)
        self.assertEqual(objects.layer_state(self.scene,who)['cards'][0]['scale'],2)
        with self.assertRaises(MapError):
            self.command('cards','move',{'id':card['id'],'version':placed['version'],'scale':0})
        with self.assertRaises(MapError):
            self.command('cards','move',{'id':card['id'],'version':placed['version'],'z_index':1.5})
        self.assertEqual(self.state('cards')['cards'][0]['z_index'],7)

    def test_actor_without_token_and_previous_round(self):
        base={'sceneId':str(self.scene.pk)}
        state=self.command('combat','add',{**base,'actorId':str(self.actor.pk)})
        self.assertIsNone(state['combatants'][0]['token_id'])
        self.assertEqual(state['combatants'][0]['actor_id'],str(self.actor.pk))
        state=self.command('combat','start',{**base,'version':state['version']})
        state=self.command('combat','next',{**base,'version':state['version']},self.player)
        self.assertEqual(state['round'],2)
        with self.assertRaises(MapError):
            self.command('combat','previous-round',{**base,'version':state['version']},self.player)
        state=self.command('combat','previous-round',{**base,'version':state['version']})
        self.assertEqual(state['round'],1)
        state=self.command('combat','initiative',{**base,'actorId':str(self.actor.pk),'value':18,'version':state['version']})
        state=self.command('combat','remove',{**base,'actorId':str(self.actor.pk),'version':state['version']})
        self.assertFalse(state['active'])
        self.assertEqual(state['combatants'],[])

    def test_scene_soundscape_versions_and_access(self):
        from gravewright.audio.models import Playlist
        preset=Playlist.objects.create(campaign=self.campaign,name='Rain',kind='preset')
        who=self.campaign.memberships.get(user=self.gm)
        value=objects.apply(self.scene,who,'soundscape','set',{'soundscape_id':str(preset.pk),'expected_version':1})
        self.assertEqual(value['soundscape_id'],str(preset.pk))
        self.scene.refresh_from_db()
        with self.assertRaises(MapError):
            objects.apply(self.scene,who,'soundscape','set',{'soundscape_id':None,'expected_version':1})
        with self.assertRaises(MapError):
            objects.apply(self.scene,self.campaign.memberships.get(user=self.player),'soundscape','set',{'soundscape_id':None,'expected_version':2})
        self.assertEqual(self.state('audio',self.player)['soundscape']['soundscape_id'],str(preset.pk))
        objects.apply(self.scene,who,'soundscape','set',{'soundscape_id':None,'expected_version':2})
        self.assertIsNone(self.state('audio')['soundscape']['soundscape_id'])

    def test_search_diary_body_respects_section_audience(self):
        from gravewright.journals import services as journals
        who=self.campaign.memberships.get(user=self.gm)
        journal=Journal.objects.create(campaign=self.campaign,creator=self.gm,title='Notes',visibility='shared')
        def doc(text):
            return {'format':'gw-journal-doc-v1','version':1,'doc':{'type':'doc','content':[{'type':'paragraph','content':[{'type':'text','text':text}]}]}}
        journal.data=journals.clean_data({'sections':[
            {'id':str(uuid.uuid4()),'title':'Public','kind':'text','audience':'public','content':doc('uniquesandstorm')},
            {'id':str(uuid.uuid4()),'title':'Secret','kind':'text','audience':'gm','content':doc('hiddentreasure')}]},journal,who)
        journal.save()
        self.assertEqual(len(services.search(self.campaign.pk,self.player.pk,'uniquesandstorm')),1)
        self.assertEqual(services.search(self.campaign.pk,self.player.pk,'hiddentreasure'),[])
        self.assertEqual(len(services.search(self.campaign.pk,self.gm.pk,'hiddentreasure')),1)

    def test_zones_geometry_audience_and_stale_edits(self):
        who=self.campaign.memberships.get(user=self.gm)
        zone=objects.apply(self.scene,who,'zones','create',{'geometry':{'shape':'circle','x':50,'y':50,'radius':10},'audience':{'kind':'gm'}})
        self.assertEqual(len(objects.layer_state(self.scene,who)['zones']),1)
        player=self.campaign.memberships.get(user=self.player)
        self.assertEqual(objects.layer_state(self.scene,player)['zones'],[])
        with self.assertRaises(MapError):objects.apply(self.scene,player,'zones','delete',{'zone_id':zone['id'],'expected_version':1})
        with self.assertRaises(MapError):objects.apply(self.scene,who,'zones','update',{'zone_id':zone['id'],'expected_version':0,'patch':{}})
        updated=objects.apply(self.scene,who,'zones','update',{'zone_id':zone['id'],'expected_version':1,'patch':{'audience':{'kind':'campaign'}}})
        self.assertEqual(updated['version'],2)
        self.assertEqual(len(objects.layer_state(self.scene,player)['zones']),1)
        with self.assertRaises(MapError):objects.apply(self.scene,who,'zones','create',{'geometry':{'shape':'polygon','points':[{'x':0,'y':0},{'x':10,'y':10},{'x':0,'y':10},{'x':10,'y':0}]}})

    def test_ban_and_onboarding(self):
        from gravewright.campaigns import onboarding,services as campaigns
        from gravewright.accounts.services import AuthError
        self.assertTrue(onboarding.claim(self.player,self.campaign.pk)['show'])
        self.assertFalse(onboarding.claim(self.player,self.campaign.pk)['show'])
        progress=onboarding.state(self.gm,self.campaign.pk)
        self.assertEqual(progress['completed'],4)
        self.assertTrue(onboarding.preference(self.gm,self.campaign.pk,True)['dismissed'])
        self.assertFalse(onboarding.preference(self.gm,self.campaign.pk,False)['dismissed'])
        with self.assertRaises(AuthError):campaigns.ban_member(self.player,self.campaign.pk,self.gm.pk)
        with self.assertRaises(AuthError):campaigns.ban_member(self.gm,self.campaign.pk,self.gm.pk)
        campaigns.ban_member(self.gm,self.campaign.pk,self.player.pk)
        self.assertFalse(self.campaign.memberships.filter(user=self.player).exists())
        with self.assertRaises(AuthError):onboarding.claim(self.player,self.campaign.pk)

    def test_streamer_readonly_expiration_and_revocation(self):
        from gravewright.campaigns import streamer
        from gravewright.campaigns.models import StreamerLink
        from gravewright.realtime.services import authorize
        from django.test import Client
        from django.utils import timezone
        from datetime import timedelta
        link=streamer.issue(self.gm,self.campaign.pk)
        client=Client()
        response=client.get(link['url'])
        self.assertEqual(response.status_code,302)
        member=authorize(client.session.session_key,self.campaign.pk)
        self.assertEqual(member.role,'streamer')
        self.assertFalse(member.user.has_usable_password())
        self.assertEqual(client.get(f'/game/{self.campaign.pk}').status_code,200)
        self.assertEqual(client.post(f'/api/containers/{self.campaign.pk}/modules-native/cards',{},content_type='application/json').status_code,403)
        self.assertEqual(client.post('/api/containers',{'name':'Forbidden'},content_type='application/json').status_code,403)
        streamer.revoke(self.gm,self.campaign.pk)
        self.assertIsNone(authorize(client.session.session_key,self.campaign.pk))
        self.assertEqual(client.get(f'/game/{self.campaign.pk}').status_code,403)
        self.assertEqual(Client().get(link['url']).url,'/login')
        second=streamer.issue(self.gm,self.campaign.pk)
        StreamerLink.objects.filter(revoked_at=None).update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(Client().get(second['url']).url,'/login')

    def test_native_compendium_search_requires_access(self):
        import json
        from pathlib import Path
        from django.test import override_settings
        from gravewright.compendiums.models import ContentAccess
        root=Path(self.media.name)/'compendiums';pack=root/'adventure';pack.mkdir(parents=True)
        (pack/'index.json').write_text(json.dumps({'name':'Tempest archive','campaigns':[str(self.campaign.pk)],'packs':[{'id':'lore','type':'journal_pack','label':'Weather lore','entries':[]}]}))
        with override_settings(GRAVEWRIGHT_CONTENT_ROOT=root):
            self.assertEqual(len(services.search(self.campaign.pk,self.gm.pk,'Tempest')),1)
            self.assertEqual(services.search(self.campaign.pk,self.player.pk,'Tempest'),[])
            ContentAccess.objects.create(campaign=self.campaign,collection='adventure',pack='lore',role='player',level='read')
            self.assertTrue(services.search(self.campaign.pk,self.player.pk,'Tempest')[0]['id'].startswith('native:'))

    def test_zone_move_events_commit_once(self):
        from unittest.mock import AsyncMock,patch
        from gravewright.tokens import services as tokens
        from gravewright.maps.zones import movement_events
        who=self.campaign.memberships.get(user=self.gm)
        objects.apply(self.scene,who,'zones','create',{'geometry':{'shape':'rect','x':100,'y':0,'width':100,'height':100}})
        # Initial token center is (35,35), destination center is (175,35).
        send=AsyncMock()
        with patch('channels.layers.get_channel_layer') as layer:
            layer.return_value.group_send=send
            request=uuid.uuid4()
            with self.captureOnCommitCallbacks(execute=True):
                tokens.command(self.campaign.pk,self.gm.pk,'move',{'mapId':str(self.scene.pk),'id':str(self.token.pk),'gridX':2,'gridY':0,'expectedVersion':1},request)
            self.assertEqual(send.await_args.args[1]['event'],'zone.entered')
            with self.captureOnCommitCallbacks(execute=True):
                tokens.command(self.campaign.pk,self.gm.pk,'move',{'mapId':str(self.scene.pk),'id':str(self.token.pk),'gridX':2,'gridY':0,'expectedVersion':1},request)
            self.assertEqual(send.await_count,1)
