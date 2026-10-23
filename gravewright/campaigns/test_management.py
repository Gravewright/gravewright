"""Campaign preparation reads stay GM-only and do not enter the live table."""

from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from gravewright.accounts.models import User
from gravewright.accounts.services import AuthError
from gravewright.actors.models import Actor
from gravewright.items.models import Item
from gravewright.journals.data import QUEST_STATUSES
from gravewright.journals.models import Journal
from gravewright.journals.services import JournalError
from gravewright.maps.models import Broadcast, Scene, SceneNavigation
from gravewright.realtime.models import PresenceConnection

from . import management, management_views
from .models import Campaign, Membership


class CampaignManagementTests(TestCase):
    def setUp(self):
        self.host = User.objects.create_user('management-host@example.test', name='Host', role='owner')
        self.gm = User.objects.create_user('management-gm@example.test', name='Campaign GM')
        self.player = User.objects.create_user('management-player@example.test', name='Player')
        self.streamer = User.objects.create_user('management-stream@example.test', name='Streamer')
        self.outsider = User.objects.create_user('management-outside@example.test', name='Outsider')
        self.campaign = Campaign.objects.create(owner=self.host, name='Authored synthetic campaign')
        self.gm_membership = Membership.objects.create(campaign=self.campaign, user=self.gm, role='gm')
        self.player_membership = Membership.objects.create(campaign=self.campaign, user=self.player, role='player')
        Membership.objects.create(campaign=self.campaign, user=self.streamer, role='streamer')
        self.scene = Scene.objects.create(campaign=self.campaign, name='Public scene', width=800, height=600)
        self.private_scene = Scene.objects.create(campaign=self.campaign, name='GM scene', visibility='gm', width=800, height=600)
        self.actor = Actor.objects.create(campaign=self.campaign, name='Private actor', data={'secret': 'sheet body'}, permissions={})
        self.diary = Journal.objects.create(campaign=self.campaign, title='Private notebook', data={'secret': 'private prose'})
        Journal.objects.create(campaign=self.campaign, title='Active quest', type='quest', data={
            'status': 'active', 'gm': {'notes_markdown': 'Never return this secret ' * 1000},
            'objectives': [{'completed': True}, {'completed': False}, {'completed': 'true'}],
        })
        Journal.objects.create(campaign=self.campaign, title='Completed quest', type='quest', data={
            'status': 'completed', 'objectives': [{'completed': True}],
        })
        Journal.objects.create(campaign=self.campaign, title='Legacy quest', type='quest', data={
            'status': 'unknown legacy status', 'objectives': {'bad': 'old data'},
        })
        Item.objects.create(campaign=self.campaign, name='Retained item', type='example', system_id='example.system',
                            data={'secret': 'item body'})
        self.foreign = Campaign.objects.create(owner=self.host, name='Foreign private campaign')
        Membership.objects.create(campaign=self.foreign, user=self.host, role='gm')
        Membership.objects.create(campaign=self.foreign, user=self.gm, role='player')
        Scene.objects.create(campaign=self.foreign, name='Foreign scene', width=100, height=100)
        Journal.objects.create(campaign=self.foreign, type='quest', title='Foreign secret quest', data={'status': 'failed'})
        self.page_url = reverse('campaigns:manage', args=[self.campaign.pk])
        self.api_url = reverse('campaigns:management', args=[self.campaign.pk])

    def assert_no_store(self, response):
        self.assertIn('no-store', response['Cache-Control'])

    def test_views_mark_management_responses_private_before_global_no_store_policy(self):
        request = RequestFactory().get(self.api_url)
        request.user = self.gm
        response = management_views.overview(request, self.campaign.pk)
        self.assertIn('private', response['Cache-Control'])
        self.assertIn('no-store', response['Cache-Control'])
        request = RequestFactory().get(self.page_url)
        request.user = self.gm
        with patch('gravewright.campaigns.management_views.render', return_value=HttpResponse('shell')):
            response = management_views.page(request, self.campaign.pk)
        self.assertIn('private', response['Cache-Control'])
        self.assertIn('no-store', response['Cache-Control'])

    def test_campaign_gm_can_load_native_shell_without_being_host_owner(self):
        self.assertEqual(self.gm.role, 'participant')
        self.client.force_login(self.gm)
        response = self.client.get(self.page_url)
        self.assertContains(response, 'id="campaign-management-overview"')
        self.assertContains(response, 'id="table-initial-content"')
        self.assertContains(response, 'data-management="true"')
        self.assertContains(response, self.campaign.name)
        self.assertContains(response, self.actor.name)
        self.assertContains(response, self.private_scene.name)
        self.assertNotContains(response, 'Foreign secret quest')
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)
        self.assert_no_store(response)

    def test_context_supplies_existing_native_includes_and_translator(self):
        self.client.force_login(self.gm)
        language = {'id': 'pt-BR', 'messages': {'Synthetic tool': 'Ferramenta de teste'},
                    'options': [{'id': 'en', 'name': 'English'}, {'id': 'pt-BR', 'name': 'Portuguese'}]}
        with patch('gravewright.campaigns.management_views.render', return_value=HttpResponse('shell')) as rendered, \
                patch('gravewright.modules.localization.for_request', return_value=language):
            response = self.client.get(self.page_url)
        self.assertEqual(response.status_code, 200)
        _, template, context = rendered.call_args.args
        self.assertEqual(template, 'gravewright_web/campaign_manager/page.html')
        self.assertTrue(context['owner'])
        self.assertEqual(context['member_role'], 'gm')
        self.assertEqual(context['management_api_url'], self.api_url)
        self.assertEqual(context['management_overview']['memberRole'], 'gm')
        self.assertEqual(context['default_locale'], 'pt-BR')
        self.assertEqual(context['campaign'].name, self.campaign.name)
        self.assertTrue(callable(context['t']))
        self.assertTrue(context['csrfCookie'])
        for key in ('actor_sheet_provider', 'system_id', 'ruleset', 'layers', 'tools', 'directories'):
            self.assertIn(key, context)
        self.assertEqual(set(context['initial_content']), {'maps', 'actors', 'journals', 'items'})
        self.assertTrue(context['has_scenes'])
        self.assertTrue(context['has_actors'])

    def test_overview_reports_campaign_counts_and_normalized_progress_without_document_bodies(self):
        self.client.force_login(self.gm)
        with patch('gravewright.actors.services.state', side_effect=AssertionError('No sheets in summary')), \
                patch('gravewright.journals.services.state', side_effect=AssertionError('No documents in summary')), \
                patch('gravewright.maps.services.state', side_effect=AssertionError('No maps in summary')):
            response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['counts'], {'scenes': 2, 'actors': 1, 'journals': 4, 'items': 1, 'quests': 3, 'members': 3})
        self.assertEqual(result['quests']['total'], 3)
        self.assertEqual(result['quests']['byStatus'], {key: int(key in ('draft', 'active', 'completed')) for key in QUEST_STATUSES})
        self.assertEqual(result['quests']['objectives'], {'total': 4, 'completed': 3})
        self.assertEqual(result['members'], [
            {'id': str(self.gm.pk), 'name': self.gm.name, 'role': 'gm'},
            {'id': str(self.player.pk), 'name': self.player.name, 'role': 'player'},
            {'id': str(self.streamer.pk), 'name': self.streamer.name, 'role': 'streamer'},
        ])
        for secret in ('Never return this secret', 'Private notebook', 'sheet body', 'Foreign', 'item body'):
            self.assertNotIn(secret, response.content.decode())
        self.assertLess(len(response.content), 4000)
        self.assert_no_store(response)

    def test_domain_capabilities_follow_selected_system_without_hiding_retained_counts(self):
        without_items = management.overview(self.gm, self.campaign.pk)
        self.assertFalse(without_items['domains']['items'])
        self.assertEqual(without_items['counts']['items'], 1)
        self.assertTrue(all(enabled for domain, enabled in without_items['domains'].items() if domain != 'items'))
        with patch('gravewright.campaigns.management.get_ruleset', return_value={'itemTypes': [{'id': 'generic'}]}):
            with_items = management.overview(self.gm, self.campaign.pk)
        self.assertTrue(with_items['domains']['items'])

    def test_public_python_facade_matches_http_projection_and_rechecks_membership(self):
        from api import capabilities, campaigns
        self.assertIn('management', capabilities()['browser']['global']['campaigns'])
        self.assertEqual(campaigns.management(self.campaign.pk, self.gm.pk),
                         management.overview(self.gm, self.campaign.pk))
        with self.assertRaises(AuthError):
            campaigns.management(self.campaign.pk, self.player.pk)
        with self.assertRaises(AuthError):
            campaigns.management(self.foreign.pk, self.gm.pk)
        self.gm_membership.delete()
        with self.assertRaises(JournalError):
            campaigns.management(self.campaign.pk, self.gm.pk)

    def test_player_streamer_nonmember_and_host_account_cannot_manage(self):
        for user, expected_api in ((self.player, 403), (self.streamer, 403), (self.outsider, 404), (self.host, 404)):
            with self.subTest(user=user.name):
                self.client.force_login(user)
                response = self.client.get(self.page_url)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn(self.campaign.name, response.content.decode())
                self.assert_no_store(response)
                response = self.client.get(self.api_url)
                self.assertEqual(response.status_code, expected_api)
                self.assertNotIn(self.campaign.name, response.content.decode())
                self.assert_no_store(response)
        Membership.objects.create(campaign=self.campaign, user=self.host, role='player')
        self.client.force_login(self.host)
        self.assertEqual(self.client.get(self.page_url).status_code, 404)
        self.assertEqual(self.client.get(self.api_url).status_code, 403)

    def test_management_authorization_is_current_and_campaign_local(self):
        self.client.force_login(self.gm)
        self.assertEqual(self.client.get(reverse('campaigns:management', args=[self.foreign.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('campaigns:manage', args=[self.foreign.pk])).status_code, 404)
        self.gm_membership.role = 'player'
        self.gm_membership.save(update_fields=['role'])
        self.assertEqual(self.client.get(self.api_url).status_code, 403)
        self.gm_membership.delete()
        self.assertEqual(self.client.get(self.api_url).status_code, 404)
        self.assertEqual(self.client.get(self.page_url).status_code, 404)

    def test_inactive_members_do_not_appear_and_inactive_gms_cannot_read_service(self):
        User.objects.filter(pk=self.player.pk).update(is_active=False)
        result = management.overview(self.gm, self.campaign.pk)
        self.assertEqual(result['counts']['members'], 2)
        self.assertNotIn(str(self.player.pk), [member['id'] for member in result['members']])
        User.objects.filter(pk=self.gm.pk).update(is_active=False)
        with self.assertRaises(AuthError) as caught:
            management.overview(self.gm, self.campaign.pk)
        self.assertEqual(caught.exception.status, 404)

    def test_anonymous_requests_and_non_get_methods_cannot_open_manager(self):
        page = self.client.get(self.page_url)
        self.assertRedirects(page, '/login', fetch_redirect_response=False)
        self.assert_no_store(page)
        api = self.client.get(self.api_url)
        self.assertEqual(api.status_code, 401)
        self.assert_no_store(api)
        self.client.force_login(self.gm)
        for url in (self.page_url, self.api_url):
            response = self.client.post(url, data={})
            self.assertEqual(response.status_code, 405)
            self.assert_no_store(response)

    def test_page_and_overview_preserve_presence_broadcast_and_private_navigation(self):
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        SceneNavigation.objects.create(membership=self.gm_membership, scene=self.private_scene)
        PresenceConnection.objects.create(membership=self.player_membership, expires_at=timezone.now() + timedelta(minutes=1))
        self.client.force_login(self.gm)
        before = {model: list(model.objects.values()) for model in (PresenceConnection, Broadcast, SceneNavigation)}
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.client.get(self.page_url).status_code, 200)
            self.assertEqual(self.client.get(self.api_url).status_code, 200)
        after = {model: list(model.objects.values()) for model in before}
        self.assertEqual(before, after)
        writes = [query['sql'] for query in queries if query['sql'].lstrip().upper().startswith(('INSERT ', 'UPDATE ', 'DELETE '))]
        self.assertEqual(writes, [])

    def test_empty_campaign_reads_do_not_initialize_table_navigation_or_presence(self):
        empty = Campaign.objects.create(owner=self.host, name='Empty preparation campaign')
        Membership.objects.create(campaign=empty, user=self.host, role='gm')
        self.client.force_login(self.host)
        before = {model: model.objects.count() for model in (PresenceConnection, Broadcast, SceneNavigation)}
        self.assertEqual(self.client.get(reverse('campaigns:manage', args=[empty.pk])).status_code, 200)
        response = self.client.get(reverse('campaigns:management', args=[empty.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['quests'], {
            'total': 0, 'byStatus': dict.fromkeys(QUEST_STATUSES, 0), 'objectives': {'total': 0, 'completed': 0}})
        self.assertEqual(before, {model: model.objects.count() for model in before})
