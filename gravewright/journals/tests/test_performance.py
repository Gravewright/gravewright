"""Directory query cost stays bounded as quest boards grow."""
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.journals import services
from gravewright.journals.data import normalize_quest_data
from gravewright.journals.models import Journal, BoardEntry
from gravewright.table.models import DocumentAccess


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class DirectoryPerformanceTests(TestCase):
    def test_board_projection_batches_links_and_keeps_private_quests_hidden(self):
        gm=User.objects.create_user('performance-gm@example.test','password-12345',role='owner')
        player=User.objects.create_user('performance-player@example.test','password-12345')
        campaign=Campaign.objects.create(owner=gm,name='Performance')
        Membership.objects.create(campaign=campaign,user=player,role='player')
        quests=[Journal.objects.create(campaign=campaign,title=f'Quest {i}',type='quest',
            data=normalize_quest_data({'status':'active'})) for i in range(12)]
        boards=[Journal.objects.create(campaign=campaign,title=f'Board {i}',type='quest_board',visibility='shared') for i in range(8)]
        BoardEntry.objects.bulk_create([BoardEntry(board=b,quest=q,sort_order=i*10,pinned=i==3)
            for b in boards for i,q in enumerate(quests)])
        DocumentAccess.objects.create(campaign=campaign,kind='journals',resource_id=str(quests[0].pk),grants={'default':'none'})
        with CaptureQueriesContext(connection) as queries:
            result=services.state(campaign.pk,player.pk)
        self.assertLessEqual(len(queries),8)
        self.assertNotIn(str(quests[0].pk),{j['id'] for j in result['journals']})
        self.assertIn(str(quests[1].pk),{j['id'] for j in result['journals']})
        for board in (j for j in result['journals'] if j['type']=='quest_board'):
            self.assertEqual(len(board['board_entries']),11)
            self.assertEqual(board['board_entries'][0]['quest_id'],str(quests[3].pk))
