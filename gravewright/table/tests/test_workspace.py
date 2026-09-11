from django.test import TestCase, override_settings
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class WorkspaceTests(TestCase):
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

    @override_settings(COMMAND_PALETTE_ENABLED=False,LOBBY_READY_CHECK_ENABLED=False,APP_DEBUG=True)
    def test_table_flags_control_the_available_tools(self):
        self.client.force_login(self.owner)
        response=self.client.get(self.path)
        self.assertNotContains(response,'data-command-palette-dialog')
        self.assertNotContains(response,'data-lobby-panel-window')
        self.assertContains(response,'data-renderer-debug="true"')
