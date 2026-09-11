import base64
from datetime import timedelta
from io import BytesIO
import json
from pathlib import Path
import tempfile

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from PIL import Image

from gravewright.accounts.models import User, UserPreference
from gravewright.campaigns.models import AccessCode, Campaign, JoinAttempt, Membership


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CampaignTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        override = override_settings(MEDIA_ROOT=self.media.name)
        override.enable()
        self.addCleanup(override.disable)
        self.owner = User.objects.create_user('owner@example.test', 'owner-password-123', name='Game Master', role='owner')
        self.player = User.objects.create_user('player@example.test', 'player-password-123', name='Player')
        self.stranger = User.objects.create_user('stranger@example.test', 'stranger-password-123', name='Stranger')
        self.clients = {}
        for user in (self.owner, self.player, self.stranger):
            client = Client(enforce_csrf_checks=True)
            client.force_login(user)
            client.get('/api/security/csrf')
            self.clients[user.pk] = client
        self.client = self.clients[self.owner.pk]
        self.data = {'name': 'The Lost Keep', 'description': 'An old ruin.', 'system': 'gravewright-pdf-system', 'image': ''}

    def post(self, path, data=None, *, user=None):
        client = self.clients[(user or self.owner).pk]
        return client.post(path, json.dumps(data or {}), content_type='application/json',
                           HTTP_X_CSRF_TOKEN=client.cookies[settings.CSRF_COOKIE_NAME].value)

    def create(self, **changes):
        response = self.post('/api/containers', {**self.data, **changes})
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def code(self, row, kind='invitation'):
        response = self.post(f"/api/containers/{row['id']}/{kind}")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()['code']

    def test_membership_controls_listing_management_and_join(self):
        row = self.create()
        path = '/api/containers/' + row['id']
        self.assertEqual(row['participantNames'], ['Game Master'])
        self.assertEqual(Membership.objects.get().role, 'gm')
        player = self.clients[self.player.pk]
        self.assertEqual(player.get('/api/containers').json(), [])
        self.assertEqual(self.post('/api/containers', self.data, user=self.player).status_code, 403)
        self.assertEqual(self.post(path, self.data, user=self.player).status_code, 404)
        code = self.code(row)
        joined = self.post('/api/containers/join', {'code': code.lower().replace('-', ' ')}, user=self.player)
        self.assertEqual(joined.status_code, 200)
        self.assertEqual(joined.json()['participantNames'], ['Game Master', 'Player'])
        self.post('/api/containers/join', {'code': code}, user=self.player)
        self.assertEqual(Membership.objects.count(), 2)
        for suffix in ['', '/invitation', '/removal-code', '/remove']:
            self.assertEqual(self.post(path + suffix, self.data, user=self.player).status_code, 403)
        self.assertEqual(len(player.get('/api/containers').json()), 1)
        self.assertEqual(self.clients[self.stranger.pk].get('/api/containers').json(), [])

    def test_invites_rotate_expire_and_are_never_stored_plaintext(self):
        row = self.create()
        first = self.code(row)
        second = self.code(row)
        self.assertRegex(second, r'^[A-Z2-9]{4}(-[A-Z2-9]{4}){2}$')
        self.assertNotEqual(AccessCode.objects.get().digest, second)
        self.assertEqual(self.post('/api/containers/join', {'code': first}, user=self.player).status_code, 400)
        AccessCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.post('/api/containers/join', {'code': second}, user=self.player).status_code, 400)
        self.assertEqual(Membership.objects.count(), 1)

    def test_failed_join_limit_persists_and_blocks_valid_code_until_expiry(self):
        code = self.code(self.create())
        for _ in range(10):
            self.assertEqual(self.post('/api/containers/join', {'code': 'invalid'}, user=self.player).status_code, 400)
        response = self.post('/api/containers/join', {'code': code}, user=self.player)
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)
        self.assertTrue(all(attempt.count == 10 for attempt in JoinAttempt.objects.all()))
        JoinAttempt.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.post('/api/containers/join', {'code': code}, user=self.player).status_code, 200)
        self.assertFalse(JoinAttempt.objects.exists())

    def test_removal_needs_separate_live_confirmation_and_cascades(self):
        row = self.create()
        invitation = self.code(row)
        remove = '/api/containers/' + row['id'] + '/remove'
        self.assertEqual(self.post(remove, {'code': invitation}).status_code, 400)
        first = self.code(row, 'removal-code')
        second = self.code(row, 'removal-code')
        self.assertEqual(self.post(remove, {'code': first}).status_code, 400)
        self.assertEqual(self.post(remove, {'code': second}).status_code, 204)
        self.assertFalse(Campaign.objects.exists())
        self.assertFalse(Membership.objects.exists())
        self.assertFalse(AccessCode.objects.exists())

    def test_cover_validation_private_access_preservation_and_cleanup(self):
        image = BytesIO()
        Image.new('RGB', (30, 20), '#123456').save(image, 'PNG')
        encoded = 'data:image/png;base64,' + base64.b64encode(image.getvalue()).decode()
        row = self.create(image=encoded)
        campaign = Campaign.objects.get()
        cover_path = Path(campaign.cover.path)
        self.assertTrue(cover_path.is_file())
        self.assertEqual(self.clients[self.stranger.pk].get(row['image']).status_code, 404)
        self.assertEqual(Client().get(row['image']).status_code, 401)
        response = self.client.get(row['image'])
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(b''.join(response.streaming_content), image.getvalue())
        response = self.post('/api/containers/' + row['id'], {**self.data, 'image': row['image'], 'name': 'Edited keep'})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['image'], row['image'])
        self.assertTrue(cover_path.exists())
        with self.captureOnCommitCallbacks(execute=True):
            response = self.post('/api/containers/' + row['id'], {**self.data, 'image': 'https://example.test/cover.png'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(cover_path.exists())
        self.assertEqual(response.json()['image'], 'https://example.test/cover.png')
        for invalid in ['data:image/png;base64,eHl6', 'javascript:alert(1)', 'file:///etc/passwd', '/campaigns/other/cover']:
            self.assertEqual(self.post('/api/containers', {**self.data, 'image': invalid}).status_code, 400)

    def test_validation_csrf_and_html_escaping(self):
        for fields in [{'name': 'x'}, {'name': ' ' * 8}, {'description': 'x' * 501}, {'system': 'unknown'}, {'name': ['bad']}]:
            self.assertEqual(self.post('/api/containers', {**self.data, **fields}).status_code, 400)
        self.assertEqual(self.client.post('/api/containers', self.data).status_code, 403)
        row = self.create(name='<img src=x onerror=alert(1)>')
        page = self.client.get('/inside')
        self.assertContains(page, '&lt;img src=x')
        self.assertNotContains(page, '<img src=x')
        self.assertContains(page, 'datastar-1.0.3.js')
        for mode in ['preview', 'edit', 'invite', 'remove']:
            self.assertEqual(self.client.get('/inside/dialog/' + mode + '/' + row['id']).status_code, 200)
        self.assertRedirects(Client().get('/inside'), '/login')

    def test_ui_mutations_and_preferences(self):
        token = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        response = self.client.post('/inside/campaigns/create', {**self.data, 'csrfmiddlewaretoken': token}, HTTP_DATASTAR_REQUEST='true')
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        self.assertIn('The Lost Keep', b''.join(response.streaming_content).decode())
        self.assertEqual(Campaign.objects.count(), 1)
        self.assertEqual(self.post('/api/player-preferences', {'pingColor': '#AB1234'}).json(), {'pingColor': '#ab1234'})
        self.assertEqual(UserPreference.objects.get(user=self.owner).ping_color, '#ab1234')
        self.assertEqual(self.clients[self.player.pk].get('/api/player-preferences').json(), {'pingColor': '#f2c679'})
        self.assertEqual(self.post('/api/player-preferences', {'pingColor': 'red'}).status_code, 400)
        response = self.client.post('/inside/account', {'name': 'Renamed GM', 'csrfmiddlewaretoken': token})
        self.assertContains(response, 'Profile saved.')
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.name, 'Renamed GM')

    def test_stale_edit_cannot_recreate_a_removed_campaign(self):
        from gravewright.accounts.services import AuthError
        from gravewright.campaigns.services import save_campaign
        from gravewright.campaigns.views import validate_campaign_form
        row = self.create()
        campaign = Campaign.objects.get(pk=row['id'])
        form = validate_campaign_form({**self.data, 'name': 'Stale edit'}, instance=campaign)
        Campaign.objects.filter(pk=campaign.pk).delete()
        with self.assertRaises(AuthError) as raised:
            save_campaign(self.owner, form, existing=campaign)
        self.assertEqual(raised.exception.status, 404)
        self.assertFalse(Campaign.objects.exists())
