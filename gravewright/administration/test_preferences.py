from django.test import TestCase, override_settings
from gravewright.accounts.models import User
from gravewright.accounts.services import AuthError
from gravewright.administration.preferences import read, update, public_privacy
from gravewright.administration.updates import CoreUpdateService


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class HostPreferenceTests(TestCase):
    @override_settings(DEFAULT_LOCALE='unavailable')
    def test_unavailable_environment_locale_falls_back_to_installed_catalog(self):
        self.assertEqual(read()['app']['default_locale'], 'en')

    def setUp(self):
        self.owner=User.objects.create_user(email='owner@settings.test',password='password-long',name='Owner',role='owner')
        self.player=User.objects.create_user(email='player@settings.test',password='password-long',name='Player')

    @override_settings(APP_NAME='Environment name',PRIVACY_ENABLED=False)
    def test_defaults_partial_updates_and_channel_linking(self):
        self.assertEqual(read()['app']['app_name'],'Environment name')
        update(self.owner,'app',{'app_name':'Installation','core_channel':'testing'})
        self.assertEqual(read()['updates']['packages_channel'],'testing')
        self.assertEqual(CoreUpdateService().channel,'testing')
        update(self.owner,'app',{'channels_linked':False,'packages_channel':'dev'})
        self.assertEqual(read()['updates']['core_channel'],'testing')
        self.assertEqual(read()['updates']['packages_channel'],'dev')
        update(self.owner,'privacy',{'title':'Policy','content':'Host policy','enabled':True})
        self.assertEqual(read()['app']['app_name'],'Installation')
        self.assertEqual(public_privacy()['content'],'Host policy')
        update(self.owner,'app',{'app_name':'Renamed'})
        self.assertEqual(public_privacy()['content'],'Host policy')

    @override_settings(PRIVACY_ENABLED=False)
    def test_policy_visibility_validation_and_owner_only(self):
        self.assertEqual(public_privacy(),{'enabled':False})
        with self.assertRaises(AuthError):update(self.player,'privacy',{'enabled':True})
        with self.assertRaises(AuthError):update(self.owner,'privacy',{'enabled':'false'})
        with self.assertRaises(AuthError):update(self.owner,'privacy',{'contact_email':'invalid'})
        with self.assertRaises(AuthError):update(self.owner,'app',{'channels_linked':'false'})
        self.assertEqual(public_privacy(),{'enabled':False})
        with override_settings(PRIVACY_ENABLED=True):self.assertTrue(public_privacy()['enabled'])
        self.client.force_login(self.player)
        self.assertEqual(self.client.get('/api/admin/settings').status_code,403)
        self.client.logout()
        self.assertEqual(self.client.get('/api/privacy').json(),{'enabled':False})
