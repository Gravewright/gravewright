from django.test import TransactionTestCase, override_settings
from gravewright.actors.models import Actor
from gravewright.campaigns.models import Campaign
from gravewright.journals import services
from gravewright.journals.models import Journal, BoardEntry
from gravewright.maps.models import Scene, SceneObject, Broadcast
from . import test_types as fixtures


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
 CHANNEL_LAYERS={'default':{'BACKEND':'channels.layers.InMemoryChannelLayer'}})
class BoardWorkflowTests(TransactionTestCase):
    setUp=fixtures.JournalTypeTests.setUp
    command=fixtures.JournalTypeTests.command
    payload=fixtures.JournalTypeTests.payload
    create_type=fixtures.JournalTypeTests.create_type
    save=fixtures.JournalTypeTests.save
    def test_create_linked_quest_is_atomic_authorized_and_idempotent(self):
        import uuid
        board=self.create_type('quest_board');self.save(board,{})
        before=Journal.objects.count();request=str(uuid.uuid4())
        payload={'journal_id':board,'title':'Rescue the courier'}
        with self.assertRaises(services.JournalError):self.command('board-create',payload,self.player)
        self.assertEqual(Journal.objects.count(),before)
        result=self.command('board-create',payload,request_id=request)
        self.assertEqual(result,self.command('board-create',payload,request_id=request))
        quest=Journal.objects.get(pk=result['created_quest_id'])
        self.assertEqual(quest.data['status'],'available')
        self.assertTrue(BoardEntry.objects.filter(board_id=board,quest=quest).exists())
        view=services.state(self.campaign.pk,self.player.pk)['journals']
        self.assertIn(str(quest.pk),[row['id'] for row in view])

    def test_objectives_require_edit_access_version_and_visibility(self):
        quest=self.create_type('quest')
        self.save(quest,{'status':'active','objectives':[{'id':'visible','text':'Find the key','visibleToPlayers':True},{'id':'secret','text':'Secret','visibleToPlayers':False}]})
        def toggle(oid,version,user=None):return self.command('objective',{'journal_id':quest,'objective_id':oid,'completed':True,'version':version},user)
        row=Journal.objects.get(pk=quest)
        with self.assertRaises(services.JournalError):toggle('visible',row.version,self.player)
        self.command('access',{'journal_id':quest,'target_user_id':str(self.player.pk),'access_level':'owner'})
        row.refresh_from_db()
        with self.assertRaises(services.JournalError):toggle('secret',row.version,self.player)
        toggle('visible',row.version,self.player)
        with self.assertRaises(services.JournalError):toggle('visible',row.version,self.player)
        row.refresh_from_db();self.assertTrue(row.data['objectives'][0]['completed']);self.assertFalse(row.data['objectives'][1]['completed'])

    def test_assignees_are_campaign_scoped_and_filtered_by_read_access(self):
        quest=self.create_type('quest');self.save(quest,{'status':'active','objectives':[{'id':'secret','text':'Hidden','visibleToPlayers':False}]})
        readable=Actor.objects.create(campaign=self.campaign,name='Hero',permissions={'default':'read'})
        private=Actor.objects.create(campaign=self.campaign,name='Secret hero',permissions={'default':'none'})
        foreign=Actor.objects.create(campaign=Campaign.objects.create(owner=self.gm,name='Other'),name='Foreign')
        def assign(ids,user=None):return self.command('assign',{'journal_id':quest,'version':Journal.objects.get(pk=quest).version,'assignees':ids},user)
        assign([str(readable.pk),str(private.pk)])
        self.command('access',{'journal_id':quest,'target_user_id':str(self.player.pk),'access_level':'owner'})
        view=services.state(self.campaign.pk,self.player.pk)['journals'][0]
        self.assertEqual(view['quest']['assignees'],[str(readable.pk)])
        assign([],self.player)
        self.assertEqual(Journal.objects.get(pk=quest).data['assignees'],[str(private.pk)])
        self.assertIn('Hidden',str(Journal.objects.get(pk=quest).data))
        for ids in [[str(foreign.pk)],[str(private.pk)],[str(readable.pk)]*33,'invalid']:
            with self.subTest(ids=ids),self.assertRaises(services.JournalError):assign(ids,self.player)

    def test_board_locations_require_scene_marker_and_quest_read_access(self):
        board=self.create_type('quest_board');self.save(board,{})
        quest=self.command('board-create',{'journal_id':board,'title':'Find the gate'})['created_quest_id']
        scene=Scene.objects.create(campaign=self.campaign,name='Public scene',width=800,height=600)
        other=Scene.objects.create(campaign=self.campaign,name='Other scene',width=800,height=600)
        Broadcast.objects.create(campaign=self.campaign,scene=scene)
        for target,public in [(scene,True),(scene,False),(other,True)]:
            SceneObject.objects.create(scene=target,kind='journalPins',data={'journalId':quest,'pageId':'','public':public,'x':100,'y':100})
        def card(user):return next(row for row in services.state(self.campaign.pk,user.pk)['journals'] if row['id']==board)['board_entries'][0]['card']
        self.assertEqual(len(card(self.gm)['locations']),3)
        self.assertEqual(len(card(self.player)['locations']),1)
        self.command('access',{'journal_id':quest,'target_user_id':str(self.player.pk),'access_level':'none'})
        board_view=next(row for row in services.state(self.campaign.pk,self.player.pk)['journals'] if row['id']==board)
        self.assertEqual(board_view['board_entries'],[])
