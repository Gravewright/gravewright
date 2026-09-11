from copy import deepcopy
from unittest.mock import patch
import uuid
from channels.db import database_sync_to_async as db
from django.test import TransactionTestCase, override_settings
from gravewright.campaigns.models import Campaign, Membership
from gravewright.chat import services as chat
from gravewright.chat.models import Message
from gravewright.journals import services
from gravewright.journals.models import Journal, BoardEntry
from . import test_journals as fixtures


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
 CHANNEL_LAYERS={'default':{'BACKEND':'channels.layers.InMemoryChannelLayer'}},
 GRAVEWRIGHT_HEARTBEAT_SECONDS=.1,GRAVEWRIGHT_PRESENCE_TTL=3,ALLOWED_HOSTS=['testserver'])
class JournalTypeTests(TransactionTestCase):
    setUp = fixtures.JournalTests.setUp
    socket = fixtures.JournalTests.socket
    event = fixtures.JournalTests.event
    finish = fixtures.JournalTests.finish
    command = fixtures.JournalTests.command
    payload = fixtures.JournalTests.payload

    def create_type(self, kind):
        return self.command('create', {'title':kind, 'journal_type':kind})['journal_id']

    def save(self, jid, data, visibility='shared'):
        payload = self.payload(jid);payload.update(data=data,visibility=visibility)
        return self.command('update',payload)

    def test_quest_secret_objectives_and_rewards_survive_player_edit(self):
        jid=self.create_type('quest')
        data={'status':'available','public':{'description':fixtures.doc('Public')},
              'gm':{'notes':fixtures.doc('Secret note')},
              'objectives':[{'id':'shown','text':'Find key','visibleToPlayers':True}, {'id':'secret','text':'Hidden task','visibleToPlayers':False}],
              'rewards':[{'id':'reward','text':'Secret treasure','visibleToPlayers':False}]}
        data['public']['description']['doc']['content'].extend(fixtures.doc('Secret block',True)['doc']['content'])
        self.save(jid,data)
        self.command('access',{'journal_id':jid,'target_user_id':str(self.player.pk),'access_level':'owner'})
        view=services.state(self.campaign.pk,self.player.pk)['journals'][0]
        self.assertNotIn('Secret',str(view));self.assertNotIn('Hidden task',str(view))
        payload=self.payload(jid);payload['data']=view['quest'];payload['data']['objectives'][0]['completed']=True
        self.command('update',payload,self.player)
        stored=Journal.objects.get(pk=jid).data
        self.assertTrue(stored['objectives'][0]['completed']);self.assertIn('Hidden task',str(stored));self.assertIn('Secret block',str(stored));self.assertIn('Secret treasure',str(stored))
        payload=self.payload(jid);payload['data']=view['quest'];payload['data']['objectives'].append({'id':'secret','text':'guess'})
        with self.assertRaises(services.JournalError):self.command('update',payload,self.player)

    def test_board_links_visibility_order_status_and_revocation(self):
        board=self.create_type('quest_board');q1=self.create_type('quest');q2=self.create_type('quest')
        self.command('status',{'journal_id':q1,'status':'draft'});self.command('status',{'journal_id':q2,'status':'draft'})
        self.command('board-add',{'journal_id':board,'quest_id':q1});self.command('board-add',{'journal_id':board,'quest_id':q2})
        self.command('board-add',{'journal_id':board,'quest_id':q1})
        self.assertEqual(BoardEntry.objects.count(),2)
        self.save(board,{})
        view=services.state(self.campaign.pk,self.player.pk)['journals']
        self.assertEqual(len(view),1);self.assertEqual(view[0]['board_entries'],[])
        self.command('status',{'journal_id':q1,'status':'available'})
        view=services.state(self.campaign.pk,self.player.pk)['journals']
        quest=next(j for j in view if j['id']==q1)
        self.assertFalse(quest['listed']);self.assertFalse(quest['can_edit'])
        self.assertEqual(str(services.get(q1,services.member(self.campaign.pk,self.player.pk)).pk),q1)
        with self.assertRaises(services.JournalError):self.command('status',{'journal_id':q1,'status':'failed'},self.player)
        self.command('board-pin',{'journal_id':board,'quest_id':q1,'pinned':True})
        self.command('board-reorder',{'journal_id':board,'ordered_quest_ids':[q2,q1]})
        self.assertEqual([str(l.quest_id) for l in BoardEntry.objects.all()],[q2,q1])
        projected=services.projection(Journal.objects.get(pk=board),services.member(self.campaign.pk,self.gm.pk))
        self.assertEqual(projected['board_entries'][0]['quest_id'],q1)
        with self.assertRaises(services.JournalError):self.command('board-reorder',{'journal_id':board,'ordered_quest_ids':[q1,q1]})
        self.command('status',{'journal_id':q1,'status':'archived'})
        self.assertEqual(len(services.state(self.campaign.pk,self.player.pk)['journals']),1)
        self.command('status',{'journal_id':q1,'status':'active'})
        self.command('board-remove',{'journal_id':board,'quest_id':q1})
        with self.assertRaises(services.JournalError):services.get(q1,services.member(self.campaign.pk,self.player.pk))
        self.command('delete',{'journal_id':q2});self.assertEqual(BoardEntry.objects.count(),0)

    def test_types_reject_wrong_type_cross_campaign_and_invalid_entries(self):
        board=self.create_type('quest_board');table=self.create_type('roll_table')
        with self.assertRaises(services.JournalError):self.command('board-add',{'journal_id':board,'quest_id':table})
        other=Campaign.objects.create(name='Other',owner=self.gm)
        alien=Journal.objects.create(campaign=other,creator=self.gm,title='Alien',type='quest')
        with self.assertRaises(services.JournalError):self.command('board-add',{'journal_id':board,'quest_id':str(alien.pk)})
        own = self.command('create',{'title':'Board','journal_type':'quest_board'},self.player)
        with self.assertRaises(services.JournalError):self.command('board-add',{'journal_id':own['journal_id'],'quest_id':str(alien.pk)},self.player)
        for key,bad in [('entries',[{'id':'a'},{'id':'a'}]),('entries',list({} for _ in range(257)))]:
            with self.assertRaises(services.JournalError):self.save(table,{key:bad})

    def test_weighted_draw_idempotence_exhaustion_reset_and_private_history(self):
        jid=self.create_type('roll_table')
        self.save(jid,{'withReplacement':False,'resultVisibility':'gm','entries':[
            {'id':'a','name':'One','result':'Secret result','weight':2}, {'id':'b','name':'Two','weight':3},
            {'id':'c','name':'Disabled','active':False,'weight':100}]})
        request=str(uuid.uuid4())
        with patch('gravewright.journals.types.secrets.randbelow',return_value=1):
            result=self.command('roll',{'journal_id':jid},request_id=request)
        self.assertEqual(result['entry']['id'],'a');self.assertEqual(Message.objects.count(),1)
        self.assertEqual(result,self.command('roll',{'journal_id':jid},request_id=request));self.assertEqual(Message.objects.count(),1)
        self.assertEqual(chat.history(self.campaign.pk,self.player.pk),[])
        self.assertIn('Secret result',str(chat.history(self.campaign.pk,self.gm.pk)))
        self.assertNotIn('Secret result',str(services.state(self.campaign.pk,self.player.pk)))
        with patch('gravewright.journals.types.secrets.randbelow',return_value=2):
            self.assertEqual(self.command('roll',{'journal_id':jid})['entry']['id'],'b')
        with self.assertRaises(services.JournalError):self.command('roll',{'journal_id':jid})
        self.command('reset',{'journal_id':jid});self.assertFalse(any(e['drawn'] for e in Journal.objects.get(pk=jid).data['entries']))
        with self.assertRaises(services.JournalError):self.command('roll',{'journal_id':jid},self.player)
        payload=self.payload(jid);payload['data']['withReplacement']=True;payload['data']['resultVisibility']='public';self.command('update',payload)
        self.command('roll',{'journal_id':jid});self.assertEqual(len(chat.history(self.campaign.pk,self.player.pk)),1)

    async def test_websocket_private_draw_and_live_board_revoke(self):
        board=await db(self.create_type)('quest_board');quest=await db(self.create_type)('quest');table=await db(self.create_type)('roll_table')
        await db(self.save)(board,{})
        await db(self.command)('status',{'journal_id':quest,'status':'available'})
        await db(self.command)('board-add',{'journal_id':board,'quest_id':quest})
        await db(self.save)(table,{'resultVisibility':'gm','entries':[{'id':'one','name':'Hidden result','weight':1}]})
        gm,player=self.socket(self.gm),self.socket(self.player)
        for socket in [gm,player]:
            self.assertTrue((await socket.connect())[0]);await self.event(socket,'chat.history')
        try:
            await player.send_json_to({'type':'journals.sync'})
            initial=await self.event(player,'journals.state');self.assertIn(quest,str(initial))
            request=str(uuid.uuid4())
            await gm.send_json_to({'type':'journals.command','payload':{'requestId':request,'action':'roll','data':{'journal_id':table}}})
            await self.event(gm,'journals.ack');message=await self.event(gm,'chat.message');self.assertIn('Hidden result',str(message))
            # A following sync consumes preceding events and must never carry a private chat result.
            await player.send_json_to({'type':'journals.sync'})
            for _ in range(30):
                packet=await player.receive_json_from(timeout=2)
                if packet.get('type')=='session.ping':await player.send_json_to({'type':'session.pong'})
                self.assertNotEqual(packet.get('type'),'chat.message')
                if packet.get('type')=='journals.state':break
            await gm.send_json_to({'type':'journals.command','payload':{'requestId':str(uuid.uuid4()),'action':'board-remove','data':{'journal_id':board,'quest_id':quest}}})
            await self.event(gm,'journals.ack')
            for _ in range(5):
                changed=await self.event(player,'journals.state')
                if quest not in str(changed):break
            self.assertNotIn(quest,str(changed))
        finally:await self.finish()
