"""Campaign entry controls follow campaign GM membership, including co-GMs."""
import re
from unittest.mock import patch

from django.test import TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ManagementEntryTests(TestCase):
    def setUp(self):
        self.host = User.objects.create_user('entry-host@example.test', 'password-12345', name='Host', role='owner')
        self.co_gm = User.objects.create_user('entry-gm@example.test', 'password-12345', name='Co-GM')
        self.player = User.objects.create_user('entry-player@example.test', 'password-12345', name='Player')
        self.streamer = User.objects.create_user('entry-streamer@example.test', 'password-12345', name='Streamer')
        self.campaign = Campaign.objects.create(owner=self.host, name='Synthetic managed campaign')
        for user, role in ((self.host, 'gm'), (self.co_gm, 'gm'), (self.player, 'player'), (self.streamer, 'streamer')):
            Membership.objects.create(campaign=self.campaign, user=user, role=role)
        self.other = Campaign.objects.create(owner=self.host, name='Synthetic player campaign')
        for user in (self.host, self.co_gm):
            Membership.objects.create(campaign=self.other, user=user, role='player')
        self.hidden = Campaign.objects.create(owner=self.host, name='Synthetic campaign without membership')

    def preview(self, campaign=None):
        response = self.client.get(f'/inside/dialog/preview/{(campaign or self.campaign).pk}')
        self.assertEqual(response.status_code, 200, response.content)
        return response.content.decode().split('id="campaign-dialog"', 1)[1]

    def test_campaign_gms_have_management_links_in_both_home_variants_and_preview(self):
        for user in (self.host, self.co_gm):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                response = self.client.get('/inside')
                self.assertContains(response, f'href="/campaigns/{self.campaign.pk}/manage"')
                self.assertNotContains(response, f'href="/campaigns/{self.other.pk}/manage"')
                self.assertNotContains(response, str(self.hidden.pk))
                preview = self.preview()
                self.assertIn(f'href="/campaigns/{self.campaign.pk}/manage"', preview)
                self.assertIn(f'/inside/dialog/invite/{self.campaign.pk}', preview)
                self.assertLess(preview.index('/manage'), preview.index(f'/game/{self.campaign.pk}'))

    def test_players_and_streamers_never_receive_management_links(self):
        for user in (self.player, self.streamer):
            with self.subTest(role=user.name):
                self.client.force_login(user)
                self.assertNotContains(self.client.get('/inside'), f'/campaigns/{self.campaign.pk}/manage')
                preview = self.preview()
                self.assertNotIn(f'/campaigns/{self.campaign.pk}/manage', preview)
                self.assertNotIn(f'/inside/dialog/invite/{self.campaign.pk}', preview)

    def test_host_account_role_does_not_grant_campaign_management(self):
        self.client.force_login(self.host)
        preview = self.preview(self.other)
        self.assertNotIn(f'/campaigns/{self.other.pk}/manage', preview)
        self.assertNotIn(f'/inside/dialog/invite/{self.other.pk}', preview)
        html = self.client.get('/inside').content.decode()
        card = re.search(rf'<article id="campaign-{self.other.pk}".*?</article>', html, re.S).group()
        self.assertNotIn(f'data-backup="{self.other.pk}"', card)
        Membership.objects.filter(campaign=self.campaign, user=self.host).update(role='player')
        self.assertNotContains(self.client.get('/inside'), f'/campaigns/{self.campaign.pk}/manage')
        self.assertNotIn(f'/campaigns/{self.campaign.pk}/manage', self.preview())

    def test_management_label_uses_translator_without_translating_authored_names(self):
        self.client.force_login(self.co_gm)
        language = {'id': 'pt-BR', 'messages': {'Manage campaign': 'Gerenciar campanha'},
                    'options': [{'id': 'en', 'name': 'English'}, {'id': 'pt-BR', 'name': 'Portuguese'}]}
        with patch('gravewright.modules.localization.for_request', return_value=language):
            response = self.client.get('/inside')
            self.assertContains(response, 'Gerenciar campanha')
            self.assertContains(response, self.campaign.name)
            preview = self.preview()
            self.assertIn('Gerenciar campanha', preview)
            self.assertNotIn('>Manage campaign<', preview)
