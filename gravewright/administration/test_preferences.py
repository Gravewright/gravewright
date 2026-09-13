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

    @override_settings(PRIVACY_ENABLED=False)
    def test_login_policy_follows_toggle_and_escapes_operator_text(self):
        self.assertNotContains(self.client.get('/login'), 'owner-privacy-panel')
        update(self.owner, 'privacy', {'enabled': True, 'title': 'Host policy',
                                      'content': '<script>alert(1)</script>',
                                      'data_categories': 'Account and table records'})
        response = self.client.get('/login')
        self.assertContains(response, 'owner-privacy-panel')
        self.assertContains(response, 'Host policy')
        self.assertContains(response, 'Account and table records')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;')
        update(self.owner, 'privacy', {'enabled': False})
        with override_settings(PRIVACY_ENABLED=True):
            self.assertNotContains(self.client.get('/login'), 'owner-privacy-panel')
            self.assertEqual(public_privacy(), {'enabled': False})
        self.assertEqual(read()['privacy']['content'], '<script>alert(1)</script>')

    def test_owner_has_privacy_editor(self):
        self.client.force_login(self.owner)
        response = self.client.get('/inside?section=privacy')
        self.assertContains(response, 'data-privacy-form')
        self.assertContains(response, 'name="enabled"')
        self.assertContains(response, 'name="data_subject_rights"')
        self.client.force_login(self.player)
        self.assertNotContains(self.client.get('/inside?section=privacy'), 'data-privacy-form')
