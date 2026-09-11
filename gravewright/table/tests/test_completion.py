"""Regression cases found by the table inventory (no UI changes)."""
from gravewright.table.tests import test_modules as fixtures
from gravewright.combat.models import Encounter
from gravewright.tokens.models import Token
from gravewright.maps.models import SceneObject
from gravewright.compendiums.models import Pack
from gravewright.maps.services import MapError
from gravewright.table import domain


from django.test import TestCase, override_settings


class CompletionTests(TestCase):
    setUp = fixtures.TableModuleTests.setUp
    command = fixtures.TableModuleTests.command
    state = fixtures.TableModuleTests.state
    def test_roster_changes_preserve_current_identity(self):
        others=[Token.objects.create(scene=self.scene,actor=self.actor) for _ in range(2)]
        rows=[{'tokenId':str(t.pk),'defeated':False} for t in [self.token,*others]]
        encounter=Encounter.objects.create(scene=self.scene,active=True,round=2,turn=1,combatants=rows)
        self.command('combat','remove',{'sceneId':str(self.scene.pk),'tokenId':str(self.token.pk),'version':encounter.version})
        encounter.refresh_from_db()
        self.assertEqual(encounter.combatants[encounter.turn]['tokenId'],str(others[0].pk))
        self.command('combat','order-down',{'sceneId':str(self.scene.pk),'tokenId':str(others[0].pk),'version':encounter.version})
        encounter.refresh_from_db()
        self.assertEqual(encounter.combatants[encounter.turn]['tokenId'],str(others[0].pk))

    def test_locked_pack_can_import_but_cannot_edit(self):
        pack=self.command('compendiums','create',{'name':'Read only'})['id']
        entry=self.command('compendiums','add',{'packId':pack,'kind':'actor','resourceId':str(self.actor.pk)})['id']
        Pack.objects.filter(pk=pack).update(locked=True)
        self.assertIn('id',self.command('compendiums','import',{'packId':pack,'id':entry}))
        with self.assertRaises(MapError):
            self.command('compendiums','remove',{'packId':pack,'id':entry,'version':1})

    def test_effect_clock_expires_before_periodic_damage_and_is_bounded(self):
        self.actor.data['bars']['bar_1']={'value':10,'max':10}
        self.actor.data['effects']=[
            {'id':'expired','duration':{'type':'rounds','remaining':1},'data':{'modifiers':[{'operation':'damage_over_time','value':100,'target':'damage.self'}]}},
            {'id':'poison','duration':{'type':'rounds','remaining':3},'data':{'modifiers':[{'operation':'damage_over_time','value':3,'target':'damage.self'}]}},
        ];self.actor.save()
        encounter=Encounter.objects.create(scene=self.scene,active=True,round=1,combatants=[{'tokenId':str(self.token.pk)}])
        self.command('combat','next',{'sceneId':str(self.scene.pk),'version':encounter.version})
        self.actor.refresh_from_db()
        self.assertFalse(self.actor.data['effects'][0]['enabled'])
        self.assertEqual(self.actor.data['effects'][1]['duration']['remaining'],2)
        self.assertEqual(self.actor.data['bars']['bar_1']['value'],7)
        self.assertEqual(self.actor.sheet_version,3)
        encounter.refresh_from_db()
        self.command('combat','previous',{'sceneId':str(self.scene.pk),'version':encounter.version})
        self.actor.refresh_from_db();self.assertEqual(self.actor.data['bars']['bar_1']['value'],7)

    def test_gm_spatial_audio_requires_explicit_listener(self):
        from gravewright.audio.models import Track
        track=Track.objects.create(campaign=self.campaign,name='Source')
        SceneObject.objects.create(scene=self.scene,kind='spatialSounds',data={'trackId':str(track.pk),'gain':1,'radius':1000,'x':0,'y':0,'enabled':True,'occlusion':False})
        self.assertEqual(self.state('audio')['spatialSounds'][0]['effectiveGain'],0)
        projected=domain.state(self.campaign.pk,self.gm.pk,'audio',str(self.scene.pk),str(self.token.pk))
        self.assertGreater(projected['spatialSounds'][0]['effectiveGain'],0)

    def test_native_collection_activation_permissions_and_import(self):
        import json
        from pathlib import Path
        from gravewright.actors.models import Actor
        base=Path(self.media.name)/'catalog'
        directory=base/'adventure';directory.mkdir(parents=True)
        index={'id':'adventure','name':'Adventure','campaigns':[str(self.campaign.pk)],'packs':[{'id':'heroes','type':'actor_pack','entries':[{'id':'hero','name':'Imported hero','type':'character','data':{}}]}]}
        (directory/'index.json').write_text(json.dumps(index))
        with override_settings(GRAVEWRIGHT_CONTENT_ROOT=base):
            pack=self.state('compendiums')['packs'][0]
            self.assertEqual(self.state('compendiums',self.player)['packs'],[])
            result=self.command('compendiums','import',{'packId':pack['id'],'id':'hero'})
            self.assertEqual(Actor.objects.get(pk=result['id']).name,'Imported hero')
            self.command('compendiums','permissions',{'packId':pack['id'],'level':'read'})
            self.assertEqual(len(self.state('compendiums',self.player)['packs']),1)
            with self.assertRaises(MapError):self.command('compendiums','import',{'packId':pack['id'],'id':'hero'},self.player)
            index['campaigns']=[];(directory/'index.json').write_text(json.dumps(index))
            self.assertEqual(self.state('compendiums')['packs'],[])
            with self.assertRaises(MapError):self.command('compendiums','import',{'packId':pack['id'],'id':'hero'})

    def test_card_chat_metadata_hides_unrevealed_faces(self):
        from gravewright.chat.models import Message
        deck=self.command('cards','create',{'name':'Cards','cards':['Secret','Public']})['id']
        self.command('cards','draw',{'deck_instance_id':deck,'count':1,'destination':'chat','face_state':'face_down'})
        hidden=Message.objects.latest('id').metadata
        self.assertEqual(hidden['type'],'cards.revealed')
        self.assertEqual(hidden['cards'][0]['name'],'Card')
        self.assertIsNone(hidden['cards'][0]['frontUrl'])
        self.command('cards','draw',{'deck_instance_id':deck,'count':1,'destination':'chat','face_state':'face_up'})
        self.assertEqual(Message.objects.latest('id').metadata['cards'][0]['name'],'Public')

    def test_native_deck_and_journal_are_independent_copies(self):
        import io
        import json
        from pathlib import Path
        from PIL import Image
        from gravewright.cards.models import Deck
        from gravewright.journals.models import Journal
        base=Path(self.media.name)/'catalog';directory=base/'adventure';directory.mkdir(parents=True)
        picture=io.BytesIO();Image.new('RGB',(8,8),'red').save(picture,format='WEBP')
        (directory/'card.webp').write_bytes(picture.getvalue())
        index={'campaigns':[str(self.campaign.pk)],'packs':[
            {'id':'cards','type':'deck_pack','entries':[{'id':'deck','name':'Native cards','data':{'cards':[{'name':'Ace','artwork':'card.webp','quantity':2}]}}]},
            {'id':'notes','type':'journal_pack','entries':[{'id':'note','name':'Native note','type':'diary','content':'A quiet room.'}]},
        ]}
        (directory/'index.json').write_text(json.dumps(index))
        with override_settings(GRAVEWRIGHT_CONTENT_ROOT=base):
            packs=self.state('compendiums')['packs']
            deck=self.command('compendiums','import',{'packId':packs[0]['id'],'id':'deck'})
            journal=self.command('compendiums','import',{'packId':packs[1]['id'],'id':'note'})
        (directory/'card.webp').unlink()
        self.assertEqual(Deck.objects.get(pk=deck['id']).cards.count(),2)
        for card in Deck.objects.get(pk=deck['id']).cards.all():
            with card.front.open('rb') as stream:self.assertEqual(stream.read(),picture.getvalue())
        stored=Journal.objects.get(pk=journal['id'])
        self.assertIn('A quiet room.',json.dumps(stored.data))
        self.assertEqual(stored.folder.parent.name,'adventure')

    def test_periodic_damage_is_idempotent_and_previous_preserves_identity(self):
        import uuid
        other=Token.objects.create(scene=self.scene,actor=self.actor)
        self.actor.data['bars']['bar_1']={'value':10,'max':10}
        self.actor.data['effects']=[{'data':{'modifiers':[{'operation':'damage_over_time','value':2,'target':'damage.self'}]}}]
        self.actor.save()
        encounter=Encounter.objects.create(scene=self.scene,active=True,round=1,combatants=[{'tokenId':str(self.token.pk)},{'tokenId':str(other.pk)}])
        rid=uuid.uuid4();payload={'sceneId':str(self.scene.pk),'version':encounter.version}
        for _ in range(2):domain.command(self.campaign.pk,self.gm.pk,'combat','next',payload,rid)
        self.actor.refresh_from_db();self.assertEqual(self.actor.data['bars']['bar_1']['value'],8)
        encounter.refresh_from_db()
        self.command('combat','order-up',{'sceneId':str(self.scene.pk),'tokenId':str(other.pk),'version':encounter.version})
        encounter.refresh_from_db()
        self.command('combat','previous',{'sceneId':str(self.scene.pk),'version':encounter.version})
        encounter.refresh_from_db()
        self.assertEqual(encounter.combatants[encounter.turn]['tokenId'],str(self.token.pk))

    def test_audio_preview_cannot_select_another_scene_and_player_cannot_impersonate(self):
        from gravewright.audio.models import Track
        from gravewright.maps.models import Scene
        track=Track.objects.create(campaign=self.campaign,name='Sound')
        SceneObject.objects.create(scene=self.scene,kind='spatialSounds',data={'trackId':str(track.pk),'gain':1,'radius':100,'x':0,'y':0,'enabled':True,'occlusion':False})
        elsewhere=Scene.objects.create(campaign=self.campaign,name='Elsewhere',width=100,height=100)
        other=Token.objects.create(scene=elsewhere,actor=self.actor)
        value=domain.state(self.campaign.pk,self.gm.pk,'audio',str(self.scene.pk),str(other.pk))
        self.assertEqual(value['spatialSounds'][0]['effectiveGain'],0)
        ordinary=self.state('audio',self.player)
        spoofed=domain.state(self.campaign.pk,self.player.pk,'audio',str(self.scene.pk),str(other.pk))
        self.assertEqual(ordinary['spatialSounds'],spoofed['spatialSounds'])

    def test_revealed_chat_images_survive_deck_deletion_and_remain_private(self):
        from django.core.files.base import ContentFile
        from gravewright.cards.models import Deck, Card
        from gravewright.chat.models import Message
        deck=Deck.objects.create(campaign=self.campaign,name='Durable')
        card=Card.objects.create(deck=deck,name='Ace')
        card.front.save('front.webp',ContentFile(b'image-snapshot'))
        self.command('cards','draw',{'deck_instance_id':str(deck.pk),'count':1,'destination':'chat'})
        message=Message.objects.latest('id');url=message.metadata['cards'][0]['frontUrl']
        self.assertIsNotNone(url)
        deck.refresh_from_db()
        with self.captureOnCommitCallbacks(execute=True):
            self.command('cards','delete-deck',{'deck_instance_id':str(deck.pk),'version':deck.version})
        self.client.force_login(self.player)
        response=self.client.get(url)
        self.assertEqual(response.status_code,200)
        self.assertEqual(b''.join(response.streaming_content),b'image-snapshot')
        from gravewright.administration.archives import export_campaign,import_campaign
        backup=export_campaign(self.campaign,snapshot=True)
        with self.captureOnCommitCallbacks(execute=True):
            import_campaign(backup,self.gm,target=self.campaign)
        restored=self.client.get(url)
        self.assertEqual(restored.status_code,200)
        self.assertEqual(b''.join(restored.streaming_content),b'image-snapshot')
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code,404)
        self.scene.visibility='gm';self.scene.save()
        self.client.force_login(self.player)
        self.assertEqual(self.client.get(url).status_code,404)
