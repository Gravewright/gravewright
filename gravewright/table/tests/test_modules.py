import uuid
from django.test import TestCase,override_settings
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign,Membership
from gravewright.maps.models import Scene,SceneState,Broadcast
from gravewright.actors.models import Actor
from gravewright.tokens.models import Token
from gravewright.pdf_system.schema import normalize
from gravewright.maps.services import MapError
from gravewright.journals.services import JournalError
from gravewright.table import domain,services

class TableModuleTests(TestCase):
    def setUp(self):
        import tempfile
        self.media=tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        media_settings=override_settings(MEDIA_ROOT=self.media.name)
        media_settings.enable();self.addCleanup(media_settings.disable)
        self.gm=User.objects.create_user(email='gm-modules@example.test',password='a-long-password',name='GM',role='owner')
        self.player=User.objects.create_user(email='player-modules@example.test',password='a-long-password',name='Player')
        self.campaign=Campaign.objects.create(owner=self.gm,name='Table')
        Membership.objects.create(campaign=self.campaign,user=self.gm,role='gm')
        Membership.objects.create(campaign=self.campaign,user=self.player,role='player')
        self.scene=Scene.objects.create(campaign=self.campaign,name='Scene',width=1000,height=1000)
        Broadcast.objects.create(campaign=self.campaign,scene=self.scene)
        self.actor=Actor.objects.create(campaign=self.campaign,name='Hero',data=normalize({}),permissions={str(self.player.pk):'owner'})
        self.token=Token.objects.create(scene=self.scene,actor=self.actor)
    def command(self,module,action,data,user=None):
        return domain.command(self.campaign.pk,(user or self.gm).pk,module,action,data,uuid.uuid4())
    def state(self,module,user=None):
        return domain.state(self.campaign.pk,(user or self.gm).pk,module,str(self.scene.pk))
    def test_item_permissions_and_revision(self):
        from unittest.mock import patch
        with patch('gravewright.items.services.types', return_value=[{'id':'gear','label':'Gear'}]):
            item=self.command('items','create',{'name':'Private','type':'gear'})['item']
        self.assertEqual(self.state('items',self.player)['items'],[])
        with self.assertRaises(MapError):self.command('items','update',{'id':item['id'],'version':1,'name':'Stolen'},self.player)
        self.command('items','permissions',{'id':item['id'],'version':1,'permissions':{str(self.player.pk):'read'}})
        self.assertEqual(len(self.state('items',self.player)['items']),1)
        with self.assertRaises(MapError):self.command('items','update',{'id':item['id'],'version':1,'name':'Stale'})
    def test_cards_are_private_and_draw_is_idempotent(self):
        deck=self.command('cards','create',{'name':'Deck','cards':['Secret Ace','Two']})['id']
        request=uuid.uuid4();payload={'deck_instance_id':deck,'count':1}
        first=domain.command(self.campaign.pk,self.player.pk,'cards','draw',payload,request)
        self.assertEqual(first,domain.command(self.campaign.pk,self.player.pk,'cards','draw',payload,request))
        self.assertEqual(self.state('cards')['hand'],[])
        self.assertEqual(len(self.state('cards',self.player)['hand']),1)
        self.assertEqual(self.state('cards')['decks'][0]['draw_count'],1)
    def test_combat_turn_and_player_authorization(self):
        self.command('combat','add',{'sceneId':str(self.scene.pk),'tokenId':str(self.token.pk)})
        state=self.state('combat')
        self.command('combat','start',{'sceneId':str(self.scene.pk),'version':state['version']})
        state=self.state('combat')
        self.command('combat','next',{'sceneId':str(self.scene.pk),'version':state['version']},self.player)
        self.assertEqual(self.state('combat')['round'],2)
        with self.assertRaises(MapError):self.command('combat','stop',{'sceneId':str(self.scene.pk),'version':self.state('combat')['version']},self.player)
    def test_compendium_import_and_visibility(self):
        pack=self.command('compendiums','create',{'name':'Bestiary'})['id']
        entry=self.command('compendiums','add',{'packId':pack,'kind':'actor','resourceId':str(self.actor.pk)})['id']
        self.assertEqual(self.state('compendiums',self.player)['packs'],[])
        imported=self.command('compendiums','import',{'packId':pack,'id':entry})
        self.assertNotEqual(imported['id'],str(self.actor.pk))
        self.assertEqual(Actor.objects.get(pk=imported['id']).permissions,{})
    def test_lobby_validates_actor_and_search_permissions(self):
        result=services.update_lobby(self.campaign.pk,self.player.pk,{'is_ready':True,'selected_actor_id':str(self.actor.pk)})
        self.assertEqual(result['summary']['ready'],1)
        self.actor.permissions={};self.actor.save()
        with self.assertRaises(MapError):services.update_lobby(self.campaign.pk,self.player.pk,{'is_ready':True,'selected_actor_id':str(self.actor.pk)})
        self.assertEqual(services.search(self.campaign.pk,self.player.pk,'Hero'),[])
    def test_fog_stale_version_rejected(self):
        from gravewright.maps.services import command
        def fog(action,data):return command(self.campaign.pk,self.gm.pk,'objects',{'mapId':str(self.scene.pk),'area':'fog','action':action,'data':data},uuid.uuid4())
        fog('enable',{'initial':'reveal_all','expected_version':1})
        with self.assertRaises(MapError):fog('reset',{'to':'hide_all','expected_version':1})
        self.assertEqual(SceneState.objects.get(scene=self.scene).fog['baseline'],'reveal_all')
    def test_combat_initiative_uses_native_dice_result(self):
        base={'sceneId':str(self.scene.pk)}
        self.command('combat','add',{**base,'tokenId':str(self.token.pk)})
        self.command('combat','configure',{**base,'version':self.state('combat')['version'],'formula':'1d6'})
        rolled=self.command('combat','roll',{**base,'version':self.state('combat')['version'],'scope':'one','tokenId':str(self.token.pk)})
        value=rolled['combatants'][0]['initiative']
        self.assertTrue(1<=value<=6)
        self.command('combat','initiative',{**base,'version':rolled['version'],'tokenId':str(self.token.pk),'value':99})
        rolled=self.command('combat','roll',{**base,'version':self.state('combat')['version'],'scope':'missing'})
        self.assertEqual(rolled['combatants'][0]['initiative'],99)
    def test_documents_reject_nonfinite_numbers(self):
        with self.assertRaises(MapError):domain.document({'value':float('nan')})
    def test_audio_timeline_overlap_pause_and_permission(self):
        from gravewright.audio.models import Track
        first=Track.objects.create(campaign=self.campaign,name='First',file='test.ogg')
        second=Track.objects.create(campaign=self.campaign,name='Second',file='test2.ogg')
        playlist=self.command('audio','playlist-create',{'name':'Score','kind':'playlist','tracks':[{'soundId':str(t.pk),'duration':10,'gain':1} for t in (first,second)],'fade':2})
        from unittest.mock import patch
        with patch('gravewright.audio.soundtrack.time.time',return_value=100):
            score=self.command('audio','score-start',{'sceneId':str(self.scene.pk),'id':playlist['id'],'kind':'playlist','expectedVersion':0,'repeat':False})
        with patch('gravewright.audio.services.time.time',return_value=109):
            state=self.state('audio',self.player)
        self.assertEqual(len(state['score']['playbacks']),2)
        self.assertEqual(state['playlists'],[])
        with self.assertRaises(MapError):self.command('audio','score-stop',{'sceneId':str(self.scene.pk),'expectedVersion':score['version']},self.player)
        with patch('gravewright.audio.soundtrack.time.time',return_value=109):
            paused=self.command('audio','score-pause',{'sceneId':str(self.scene.pk),'expectedVersion':score['version']})
        self.assertEqual(paused['position'],9)
        self.assertEqual(paused['state'],'paused')

    def test_pdf_system_does_not_invent_item_types(self):
        self.assertEqual(self.state('items')['types'],[])
        with self.assertRaises(MapError):self.command('items','create',{'name':'Invented','type':'gear'})
    @override_settings(BOARD_MARKERS_MAX_PER_SCENE=1)
    def test_shared_marker_quota_ownership_and_revision(self):
        from gravewright.maps.services import command
        def update(rows,expected,user):
            return command(self.campaign.pk,user.pk,'objects',{'mapId':str(self.scene.pk),'area':'markers','action':'replace','data':{'rows':rows,'expected_version':expected}},uuid.uuid4())
        row={'id':str(uuid.uuid4()),'kind':'circle','origin':{'x':50,'y':60},'length':40,'width':0,'angle':90,'direction':0,'color':'#ff0000'}
        update([row],1,self.gm)
        with self.assertRaises(MapError):update([],2,self.player)
        with self.assertRaises(MapError):update([{**row,'id':str(uuid.uuid4())},row],2,self.gm)
        with self.assertRaises(MapError):update([],1,self.gm)
        update([],2,self.gm)
        update([row],3,self.player)
    def test_archive_preserves_native_modules_and_selective_scene_omission(self):
        from gravewright.administration.archives import export_campaign,import_campaign
        from gravewright.cards.models import Deck,Card
        from gravewright.combat.models import Encounter
        from gravewright.compendiums.models import Pack,Entry
        from gravewright.audio.models import Playlist,Playback
        deck=Deck.objects.create(campaign=self.campaign,name='Deck')
        Card.objects.create(deck=deck,name='Private',zone='hand',owner=self.player)
        pack=Pack.objects.create(campaign=self.campaign,name='Pack')
        Entry.objects.create(pack=pack,name='Note',kind='journal',data={'title':'Note','type':'text','data':{}})
        Playlist.objects.create(campaign=self.campaign,name='Mix')
        Playback.objects.create(scene=self.scene)
        Encounter.objects.create(scene=self.scene)
        clone=import_campaign(export_campaign(self.campaign,include_files=False),self.gm)
        self.assertEqual(Deck.objects.filter(campaign=clone).count(),1)
        card=Card.objects.get(deck__campaign=clone)
        self.assertEqual(card.zone,'draw');self.assertIsNone(card.owner_id)
        self.assertEqual(Encounter.objects.filter(scene__campaign=clone).count(),1)
        self.assertEqual(Entry.objects.filter(pack__campaign=clone).count(),1)
        partial=import_campaign(export_campaign(self.campaign,{'scenes':False},include_files=False),self.gm)
        self.assertFalse(Playback.objects.filter(scene__campaign=partial).exists())

    def test_spatial_audio_preserves_original_wall_acoustics(self):
        from gravewright.audio.geometry import sound_attenuation
        wall={'x1':50,'y1':-50,'x2':50,'y2':50,'sound_behavior':'block'}
        def gain():return sound_attenuation(walls=[wall],origin=(0,0,0),target=(100,0,0))
        self.assertEqual(gain(),0)
        wall['sound_behavior']='attenuate';self.assertEqual(gain(),.45)
        wall.update(kind='door',door_state='open');self.assertEqual(gain(),1)
        wall.update(door_state='closed',vertical_bottom=10,vertical_top=20);self.assertEqual(gain(),1)

    def test_audio_ranges_remain_authenticated(self):
        import tempfile
        from django.core.files.base import ContentFile
        from gravewright.audio.models import Track
        with tempfile.TemporaryDirectory() as temp,override_settings(MEDIA_ROOT=temp):
            track=Track.objects.create(campaign=self.campaign,name='Audio',content_type='audio/wav')
            track.file.save('test.wav',ContentFile(b'0123456789'))
            url=f'/game/audio/{track.pk}'
            self.assertEqual(self.client.get(url,HTTP_RANGE='bytes=2-4').status_code,404)
            self.client.force_login(self.player)
            response=self.client.get(url,HTTP_RANGE='bytes=2-4')
            self.assertEqual(response.status_code,206)
            self.assertEqual(b''.join(response.streaming_content),b'234')
            self.assertEqual(response['Content-Range'],'bytes 2-4/10')
            response=self.client.get(url,HTTP_RANGE='bytes=-3')
            self.assertEqual(b''.join(response.streaming_content),b'789')
            self.assertEqual(self.client.get(url,HTTP_RANGE='bytes=99-100').status_code,416)
    def test_compendium_asset_snapshot_survives_original_deletion(self):
        import tempfile
        from django.core.files.base import ContentFile
        from gravewright.actors.models import Asset
        with tempfile.TemporaryDirectory() as temp,override_settings(MEDIA_ROOT=temp):
            asset=Asset(campaign=self.campaign,actor=self.actor,kind='pdf',name='Sheet')
            asset.file.save('sheet.pdf',ContentFile(b'%PDF-test'))
            self.actor.data['pdf']['asset']=str(asset.pk);self.actor.save()
            pack=self.command('compendiums','create',{'name':'Independent'})['id']
            entry=self.command('compendiums','add',{'packId':pack,'kind':'actor','resourceId':str(self.actor.pk)})['id']
            asset.file.delete();self.actor.delete()
            result=self.command('compendiums','import',{'packId':pack,'id':entry})
            restored=Actor.objects.get(pk=result['id'])
            copied=Asset.objects.get(actor=restored)
            self.assertEqual(restored.data['pdf']['asset'],str(copied.pk))
            with copied.file.open('rb') as stream:self.assertEqual(stream.read(),b'%PDF-test')

    def test_scene_and_deck_compendiums_copy_graph_without_replacing_campaign(self):
        from gravewright.cards.models import Deck,Card
        pack=self.command('compendiums','create',{'name':'Complete documents'})['id']
        entry=self.command('compendiums','add',{'packId':pack,'kind':'scene','resourceId':str(self.scene.pk)})['id']
        result=self.command('compendiums','import',{'packId':pack,'id':entry})
        copied=Scene.objects.get(pk=result['id'])
        self.assertEqual(copied.campaign_id,self.campaign.pk)
        self.assertEqual(copied.tokens.count(),1)
        self.assertNotEqual(copied.tokens.get().actor_id,self.actor.pk)
        self.assertTrue(Scene.objects.filter(pk=self.scene.pk).exists())
        self.campaign.refresh_from_db();self.assertEqual(self.campaign.name,'Table')
        deck=Deck.objects.create(campaign=self.campaign,name='Cards')
        Card.objects.create(deck=deck,name='Ace',scene=self.scene,zone='scene',owner=self.player,revealed=True)
        entry=self.command('compendiums','add',{'packId':pack,'kind':'deck','resourceId':str(deck.pk)})['id']
        result=self.command('compendiums','import',{'packId':pack,'id':entry})
        copied_card=Card.objects.get(deck_id=result['id'])
        self.assertEqual(copied_card.zone,'draw');self.assertIsNone(copied_card.scene_id)
        self.assertEqual(Scene.objects.filter(campaign=self.campaign).count(),2)
    def test_quest_board_compendium_keeps_linked_quests(self):
        from gravewright.journals.models import Journal,BoardEntry
        board=Journal.objects.create(campaign=self.campaign,title='Board',type='quest_board',creator=self.gm)
        quest=Journal.objects.create(campaign=self.campaign,title='Quest',type='quest',creator=self.gm)
        BoardEntry.objects.create(board=board,quest=quest,pinned=True)
        pack=self.command('compendiums','create',{'name':'Adventures'})['id']
        entry=self.command('compendiums','add',{'packId':pack,'kind':'journal','resourceId':str(board.pk)})['id']
        result=self.command('compendiums','import',{'packId':pack,'id':entry})
        link=BoardEntry.objects.get(board_id=result['id'])
        self.assertTrue(link.pinned);self.assertNotEqual(link.quest_id,quest.pk)
    def test_compendium_bundle_survives_campaign_clone(self):
        from gravewright.administration.archives import export_campaign,import_campaign
        from gravewright.compendiums.models import Entry
        pack=self.command('compendiums','create',{'name':'Portable'})['id']
        self.command('compendiums','add',{'packId':pack,'kind':'actor','resourceId':str(self.actor.pk)})
        clone=import_campaign(export_campaign(self.campaign),self.gm)
        entry=Entry.objects.get(pack__campaign=clone)
        result=domain.command(clone.pk,self.gm.pk,'compendiums','import',{'packId':str(entry.pack_id),'id':str(entry.pk)},uuid.uuid4())
        self.assertEqual(Actor.objects.get(pk=result['id']).campaign_id,clone.pk)
