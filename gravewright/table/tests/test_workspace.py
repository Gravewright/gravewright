from django.test import TestCase, override_settings
from unittest.mock import patch
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class WorkspaceTests(TestCase):
    def test_game_preferences_live_in_the_table_instead_of_account_settings(self):
        self.client.force_login(self.owner)
        page = self.client.get(self.path)
        for marker in ('data-table-language', 'data-table-ping', 'data-table-conditions', 'data-table-marketplace'):
            self.assertContains(page, marker)
        account = self.client.get('/inside?section=settings')
        self.assertContains(account, 'account-settings__identity')
        for marker in ('data-language-settings', 'class="ping-preferences', 'class="condition-preferences', 'data-default-marketplace'):
            self.assertNotContains(account, marker)
        self.client.force_login(self.player)
        Membership.objects.create(campaign=self.campaign, user=self.player)
        self.assertNotContains(self.client.get(self.path), 'data-table-marketplace')

    def test_language_change_returns_to_table_and_rejects_external_redirects(self):
        from gravewright.accounts.models import UserPreference
        self.client.force_login(self.owner)
        available = {'en': {'name': 'English', 'messages': {}},
                     'pt-BR': {'name': 'Português (Brasil)', 'messages': {}}}
        with patch('gravewright.modules.localization.catalogs', return_value=available):
            page = self.client.get(self.path)
            self.assertContains(page, 'id="table-language"')
            self.assertContains(page, 'value="pt-BR"')
            response = self.client.post('/inside/language', {'locale': 'pt-BR', 'next': self.path})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response['Location'], self.path)
            self.assertEqual(UserPreference.objects.get(user=self.owner).locale, 'pt-BR')
            response = self.client.post('/inside/language', {'locale': 'en', 'next': 'https://other.test'})
            self.assertEqual(response['Location'], '/inside?section=settings')
            response = self.client.post('/inside/language', {'locale': 'pt-BR'}, HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {'locale': 'pt-BR'})
            self.assertNotIn('Location', response)
            self.assertEqual(UserPreference.objects.get(user=self.owner).locale, 'pt-BR')

    def setUp(self):
        self.owner = User.objects.create_user('gm@example.test', 'password-12345', name='GM', role='owner')
        self.player = User.objects.create_user('player@example.test', 'password-12345', name='Player')
        self.campaign = Campaign.objects.create(owner=self.owner, name='The old keep')
        Membership.objects.create(campaign=self.campaign, user=self.owner, role='gm')
        self.path = f'/game/{self.campaign.pk}'

    def test_membership_is_required_even_for_a_direct_url(self):
        self.assertRedirects(self.client.get(self.path), '/login')
        self.client.force_login(self.player)
        self.assertEqual(self.client.get(self.path).status_code, 404)
        Membership.objects.create(campaign=self.campaign, user=self.player)
        response = self.client.get(self.path)
        self.assertContains(response, 'The old keep')
        self.assertNotContains(response, 'class="game-menubar__layers"')
        self.assertNotContains(response, 'data-panel="scenes"')
        self.assertContains(response, 'data-panel="content"')
        self.assertContains(response, 'data-panel="actors"')

    def test_owner_chrome_and_enter_action(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.path)
        self.assertContains(response, 'class="game-menubar__layers"')
        self.assertContains(response, 'The world is still unwritten')
        self.assertContains(response, 'data-panel="scenes"')
        self.assertContains(response, 'Return to tables')
        # Canvas previews may occur inside inert templates; the scene starts empty.
        self.assertContains(response, 'class="game-table__empty-scene"')
        self.assertEqual(response['Cache-Control'], 'no-store')
        preview = self.client.get(f'/inside/dialog/preview/{self.campaign.pk}')
        self.assertContains(preview, f'/game/{self.campaign.pk}')

    def test_campaign_text_is_escaped_and_deleted_tables_are_unreachable(self):
        self.client.force_login(self.owner)
        self.campaign.name = '<script>alert(1)</script>'
        self.campaign.save()
        self.assertContains(self.client.get(self.path), '&lt;script&gt;')
        self.assertNotContains(self.client.get(self.path), '<script>alert(1)</script>')
        self.campaign.delete()
        self.assertEqual(self.client.get(self.path).status_code, 404)

    def test_setup_guide_stops_with_either_a_character_or_an_inactive_scene(self):
        from gravewright.actors.models import Actor
        from gravewright.maps.models import Scene

        self.client.force_login(self.owner)
        empty = self.client.get(self.path)
        self.assertContains(empty, 'game-dock__item game-dock__guide', count=2)
        self.assertContains(empty, 'data-empty-scenes')
        self.assertContains(empty, 'data-empty-actors')
        actor = Actor.objects.create(campaign=self.campaign, name='First character')
        self.assertNotContains(self.client.get(self.path), 'game-dock__item game-dock__guide')
        actor.delete()
        Scene.objects.create(campaign=self.campaign, name='Prepared scene', width=800, height=600)
        self.assertNotContains(self.client.get(self.path), 'game-dock__item game-dock__guide')

    @override_settings(COMMAND_PALETTE_ENABLED=False,LOBBY_READY_CHECK_ENABLED=False,APP_DEBUG=True)
    def test_table_flags_control_the_available_tools(self):
        self.client.force_login(self.owner)
        response=self.client.get(self.path)
        self.assertNotContains(response,'data-command-palette-dialog')
        self.assertNotContains(response,'data-lobby-panel-window')
        self.assertContains(response,'data-renderer-debug="true"')
