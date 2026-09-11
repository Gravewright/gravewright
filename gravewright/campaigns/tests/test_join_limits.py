from concurrent.futures import ThreadPoolExecutor
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from gravewright.accounts.models import User
from gravewright.accounts.services import AuthError
from gravewright.campaigns.models import Campaign, Membership, AccessCode
from gravewright.campaigns.services import issue_code, join_campaign, code_status


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CodeLimitTests(TestCase):
    def setUp(self):
        self.gm=User.objects.create_user(email='gm@limits.test',password='test-password',name='GM',role='owner')
        self.player=User.objects.create_user(email='player@limits.test',password='test-password',name='Player')
        self.other=User.objects.create_user(email='other@limits.test',password='test-password',name='Other')
        self.campaign=Campaign.objects.create(owner=self.gm,name='Limits')
        Membership.objects.create(campaign=self.campaign,user=self.gm,role='gm')

    def test_exhaustion_does_not_consume_existing_members_and_rotation_resets(self):
        code=issue_code(self.gm,self.campaign.pk,'invite',max_uses=1)['code']
        for _ in range(2):join_campaign(self.player,code,'127.0.0.1')
        self.assertEqual(AccessCode.objects.get().use_count,1)
        with self.assertRaises(AuthError):join_campaign(self.other,code,'127.0.0.2')
        self.assertFalse(code_status(self.gm,self.campaign.pk)['active'])
        new=issue_code(self.gm,self.campaign.pk,'invite',max_uses=2)['code']
        self.assertEqual(AccessCode.objects.get().use_count,0)
        with self.assertRaises(AuthError):join_campaign(self.other,code,'127.0.0.2')
        join_campaign(self.other,new,'127.0.0.2')
        self.assertEqual(code_status(self.gm,self.campaign.pk)['useCount'],1)

    def test_validation_revocation_and_authorization(self):
        for values in ({'max_uses':True},{'max_uses':0},{'max_uses':1001},{'expires_in_hours':False},{'expires_in_hours':721}):
            with self.assertRaises(AuthError):issue_code(self.gm,self.campaign.pk,'invite',**values)
        code=issue_code(self.gm,self.campaign.pk,'invite',expires_in_hours=1)['code']
        with self.assertRaises(AuthError):code_status(self.player,self.campaign.pk,revoke=True)
        self.assertTrue(code_status(self.gm,self.campaign.pk)['active'])
        code_status(self.gm,self.campaign.pk,revoke=True)
        with self.assertRaises(AuthError):join_campaign(self.player,code,'127.0.0.1')


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ConcurrentCodeTests(TransactionTestCase):
    setUp=CodeLimitTests.setUp

    def test_last_use_is_consumed_once(self):
        code=issue_code(self.gm,self.campaign.pk,'invite',max_uses=1)['code']
        def redeem(user):
            close_old_connections()
            try:
                join_campaign(user,code,str(user.pk));return True
            except AuthError:return False
            finally:close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            accepted=list(pool.map(redeem,[self.player,self.other]))
        self.assertEqual(accepted.count(True),1)
        self.assertEqual(AccessCode.objects.get().use_count,1)
        self.assertEqual(Membership.objects.filter(campaign=self.campaign,role='player').count(),1)
