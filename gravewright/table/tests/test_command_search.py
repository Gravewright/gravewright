import uuid

from django.test import TestCase

from gravewright.campaigns.models import Campaign
from gravewright.actors.models import Actor
from gravewright.items.models import Item
from gravewright.journals.models import Journal
from gravewright.journals import services as journals
from gravewright.table.models import DocumentAccess
from gravewright.table.tests.test_modules import TableModuleTests
from gravewright.table import services


class CommandSearchTests(TestCase):
    setUp=TableModuleTests.setUp

    def search(self,query='',**kwargs):
        return services.search(self.campaign.pk,self.player.pk,query,**kwargs)

    def doc(self,value):
        return {'format':'gw-journal-doc-v1','version':1,'doc':{'type':'doc','content':[{'type':'paragraph','content':[{'type':'text','text':value}]}]}}

    def diary(self):
        row=Journal.objects.create(campaign=self.campaign,creator=self.gm,title='Search diary',visibility='shared')
        who=self.campaign.memberships.get(user=self.gm)
        row.data=journals.clean_data({'sections':[
            {'id':str(uuid.uuid4()),'title':'Public','kind':'text','audience':'public','content':self.doc('Visible search passage')},
            {'id':str(uuid.uuid4()),'title':'Private','kind':'text','audience':'gm','content':self.doc('Secret search passage')},
        ]},row,who);row.save()
        return row

    def test_read_permission_required_for_results_and_recent_references(self):
        self.actor.name='Search hero';self.actor.permissions={'default':'limited'};self.actor.save()
        diary=self.diary()
        DocumentAccess.objects.create(campaign=self.campaign,kind='journals',resource_id=str(diary.pk),grants={'default':'limited'})
        item=Item.objects.create(campaign=self.campaign,name='Search item',type='gear',system_id=self.campaign.system,permissions={'default':'limited'})
        refs=[{'type':'actor','id':str(self.actor.pk)},{'type':'journal','id':str(diary.pk)},{'type':'item','id':str(item.pk)}]
        self.assertEqual(self.search('Search'),[])
        self.assertEqual(self.search(recent=refs),[])
        self.actor.permissions={'default':'read'};self.actor.save()
        self.assertEqual([row['id'] for row in self.search(recent=refs)],[str(self.actor.pk)])
        self.actor.permissions={'default':'none'};self.actor.save()
        self.assertEqual(self.search(recent=refs),[])

    def test_snippets_use_only_authorized_pages(self):
        diary=self.diary()
        rows=self.search('passage',kind='journal')
        self.assertEqual(len(rows),1)
        self.assertIn('Visible search passage',rows[0]['snippet'])
        self.assertNotIn('Secret',rows[0]['snippet'])
        self.assertEqual(self.search('Secret'),[])
        recent=self.search(recent=[{'type':'journal','id':str(diary.pk)}])
        self.assertNotIn('Secret',recent[0]['snippet'])
        page=diary.data['sections'][0]['id']
        DocumentAccess.objects.create(campaign=self.campaign,kind='pages',resource_id=f'{diary.pk}:{page}',grants={'default':'limited'})
        self.assertEqual(self.search('Visible search passage'),[])

    def test_quests_are_filtered_and_secrets_are_not_searched(self):
        quest=Journal.objects.create(campaign=self.campaign,creator=self.gm,title='Search quest',type='quest',visibility='shared')
        who=self.campaign.memberships.get(user=self.gm)
        quest.data=journals.clean_data({'status':'active','public':{'summary':'Rescue the caravan'},'gm':{'notes':'Invisible enemy'}},quest,who);quest.save()
        self.assertEqual(self.search('caravan',kind='quest')[0]['kind'],'quest')
        self.assertEqual(self.search('caravan',kind='journal'),[])
        self.assertEqual(self.search('Invisible'),[])
        self.assertEqual(self.search('Search',kind='actor'),[])

    def test_recent_order_cross_campaign_isolation_and_scene_actions(self):
        diary=self.diary()
        other=Campaign.objects.create(owner=self.gm,name='Other')
        foreign=Actor.objects.create(campaign=other,name='Search foreign',permissions={'default':'read'})
        refs=[{'type':'journal','id':str(diary.pk)},{'type':'actor','id':str(foreign.pk)},{'type':'actor','id':str(self.actor.pk)}]
        self.assertEqual([row['id'] for row in self.search(recent=refs)],[str(diary.pk),str(self.actor.pk)])
        self.assertEqual(self.search('Scene',kind='scene')[0]['actions'],['open'])
        gm=services.search(self.campaign.pk,self.gm.pk,'Scene',kind='scene')
        self.assertEqual(gm[0]['actions'],['open','activate'])

    def test_invalid_filters_and_recent_payloads_are_rejected(self):
        for kwargs in [{'kind':'secret'},{'recent':{}},{'recent':[{'type':'actor','id':'invalid'}]},
                       {'recent':[{'type':'actor','id':str(self.actor.pk)}]*13}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(journals.JournalError):self.search(**kwargs)

    def test_frontend_api_forwards_filter_and_recent_references(self):
        from gravewright.modules.frontend import invoke
        diary=self.diary()
        rows=invoke(self.campaign.pk,self.player.pk,'table','search',{'query':'','kind':'journal','recent':[
            {'type':'actor','id':str(self.actor.pk)},{'type':'journal','id':str(diary.pk)}]})
        self.assertEqual([row['id'] for row in rows],[str(diary.pk)])
