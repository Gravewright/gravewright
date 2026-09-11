import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import IntegrityError, close_old_connections, transaction
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from gravewright.accounts.models import AuthAttempt

User = get_user_model()
PASSWORD = 'integration-password-123'
OWNER = {'name': 'Mestre', 'email': 'gm@example.test', 'password': PASSWORD}
PLAYER = {'name': 'Jogador', 'email': 'player@example.test', 'password': PASSWORD}
FAST_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


class AuthClientMixin:
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.client.get('/api/security/csrf')

    def post(self, path, data=None, client=None, **kwargs):
        client = client or self.client
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        return client.post(path, data=data or {}, content_type='application/json',
                           HTTP_X_CSRF_TOKEN=token, **kwargs)

    def setup_owner(self):
        response = self.post('/api/auth/setup', OWNER)
        self.assertEqual(response.status_code, 201, response.content)
        return response


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class AuthenticationTests(AuthClientMixin, TestCase):
    def test_setup_login_logout_rotation_and_cookie_flags(self):
        self.assertEqual(self.client.get('/api/auth/status').json(), {'configured': False})
        response = self.setup_owner()
        self.assertEqual(response.json()['account'], {'name': 'Mestre', 'email': OWNER['email'], 'role': 'owner'})
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Strict')
        self.assertLessEqual(cookie['max-age'], 43200)
        self.assertGreater(cookie['max-age'], 43190)
        old = cookie.value
        self.assertEqual(self.client.get('/api/home/gm').status_code, 200)
        response = self.post('/api/auth/login', {**OWNER, 'email': ' GM@EXAMPLE.TEST '})
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(old, self.client.cookies[settings.SESSION_COOKIE_NAME].value)
        self.assertFalse(Session.objects.filter(session_key=old).exists())
        stale = Client()
        stale.cookies[settings.SESSION_COOKIE_NAME] = old
        self.assertFalse(stale.get('/api/auth/session').json()['authenticated'])
        self.assertEqual(self.post('/api/auth/logout').status_code, 204)
        self.assertEqual(self.post('/api/auth/logout').status_code, 204)
        self.assertEqual(self.client.get('/api/home/gm').status_code, 401)

    def test_public_registration_cannot_elevate_roles(self):
        self.assertEqual(self.post('/api/auth/register', PLAYER).status_code, 409)
        self.setup_owner()
        response = self.post('/api/auth/register', {**PLAYER, 'role': 'owner', 'is_staff': True, 'is_superuser': True})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['account']['role'], 'participant')
        user = User.objects.get(email=PLAYER['email'])
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertEqual(self.client.get('/api/home/player').status_code, 200)
        self.assertEqual(self.client.get('/api/home/gm').status_code, 403)
        self.assertEqual(self.post('/api/auth/setup', PLAYER).status_code, 409)
        self.assertEqual(self.client.get('/api/home/unknown').status_code, 404)

    def test_absolute_session_expiration_and_persistence(self):
        self.setup_owner()
        key = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        before = Session.objects.get(pk=key).expire_date
        restarted = Client()
        restarted.cookies[settings.SESSION_COOKIE_NAME] = key
        self.assertTrue(restarted.get('/api/auth/session').json()['authenticated'])
        self.assertEqual(Session.objects.get(pk=key).expire_date, before)
        Session.objects.filter(pk=key).update(expire_date=timezone.now() - timedelta(seconds=1))
        self.assertFalse(restarted.get('/api/auth/session').json()['authenticated'])

    def test_csrf_origin_and_method_restrictions(self):
        self.assertEqual(self.client.post('/api/auth/setup', OWNER).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/setup', OWNER, HTTP_X_CSRF_TOKEN='forged').status_code, 403)
        self.assertEqual(self.post('/api/auth/setup', OWNER, HTTP_ORIGIN='https://evil.example').status_code, 403)
        self.assertEqual(self.client.get('/api/auth/logout').status_code, 405)
        self.assertEqual(self.client.get('/logout').status_code, 405)
        self.assertFalse(User.objects.exists())

    def test_validation_duplicate_email_and_uniform_credentials_error(self):
        for field, value in [('name', 'x'), ('email', 'invalid'), ('password', 'short'),
                             ('name', 'x' * 81), ('password', 'x' * 257), ('name', 123),
                             ('password', ['twelve-characters'])]:
            with self.subTest(field=field, value=value):
                self.assertEqual(self.post('/api/auth/setup', {**OWNER, field: value}).status_code, 400)
        self.setup_owner()
        self.assertEqual(self.post('/api/auth/register', {**PLAYER, 'email': OWNER['email'].upper()}).status_code, 409)
        for email in [OWNER['email'], 'unknown@example.test']:
            response = self.post('/api/auth/login', {'email': email, 'password': 'wrong'})
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), {'error': 'invalid_credentials'})
        User.objects.filter(email=OWNER['email']).update(is_active=False)
        self.assertEqual(self.post('/api/auth/login', OWNER).status_code, 401)

    @override_settings(GRAVEWRIGHT_AUTH_MAX_ATTEMPTS=2)
    def test_rate_limit_shared_across_endpoints_and_reset(self):
        self.setup_owner()
        self.assertEqual(self.post('/api/auth/register', PLAYER).status_code, 201)
        limited = self.post('/api/auth/login', OWNER)
        self.assertEqual(limited.status_code, 429)
        self.assertGreater(int(limited['Retry-After']), 0)
        self.assertNotIn('127.0.0.1', AuthAttempt.objects.get().key)
        AuthAttempt.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.post('/api/auth/login', OWNER).status_code, 200)

    def test_content_type_shape_and_body_limits(self):
        token = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        response = self.client.post('/api/auth/login', 'x', content_type='text/plain', HTTP_X_CSRF_TOKEN=token)
        self.assertEqual(response.status_code, 415)
        for body, expected in [('{', 400), ('[]', 400), ('null', 400), ('x' * 17000, 413)]:
            response = self.client.post('/api/auth/login', body, content_type='application/json', HTTP_X_CSRF_TOKEN=token)
            self.assertEqual(response.status_code, expected)

    def test_password_change_preserves_current_session_and_invalidates_others(self):
        self.setup_owner()
        other = Client(enforce_csrf_checks=True)
        other.get('/api/security/csrf')
        self.assertEqual(self.post('/api/auth/login', OWNER, client=other).status_code, 200)
        expiry = self.client.session.get_expiry_date()
        bad = self.post('/api/auth/account', {'newPassword': 'another-long-password', 'currentPassword': 'wrong'})
        self.assertEqual(bad.status_code, 401)
        result = self.post('/api/auth/account', {'name': 'New name', 'currentPassword': PASSWORD,
                                                'newPassword': 'another-long-password'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['account']['name'], 'New name')
        self.assertTrue(self.client.get('/api/auth/session').json()['authenticated'])
        self.assertFalse(other.get('/api/auth/session').json()['authenticated'])
        self.assertEqual(self.client.session.get_expiry_date(), expiry)
        self.assertEqual(self.post('/api/auth/account', {'role': 'owner'}).status_code, 400)
        self.assertEqual(self.post('/api/auth/account', {'newPassword': ''}).status_code, 400)

    def test_database_constraints_and_django_admin(self):
        self.setup_owner()
        for kwargs in [dict(email='second@example.test', role='owner'),
                       dict(email='GM@EXAMPLE.TEST', role='participant'),
                       dict(email='invalid@example.test', role='admin')]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                User.objects.create(name='Other', **kwargs)
        staff = User.objects.create_superuser('staff@example.test', PASSWORD, name='Staff')
        self.client.force_login(staff)
        self.assertEqual(self.client.get('/admin/gravewright_accounts/user/').status_code, 200)
        self.assertEqual(self.client.get('/admin/gravewright_accounts/user/add/').status_code, 200)

    def test_jinja_pages_form_posts_and_datastar_errors(self):
        page = self.client.get('/')
        self.assertContains(page, 'Create the administrator account for this installation.')
        self.assertContains(page, 'data-on:submit')
        self.assertContains(page, 'datastar-1.0.3.js')
        self.assertNotContains(page, 'vue')
        token = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        data = {**OWNER, 'csrfmiddlewaretoken': token}
        response = self.client.post('/setup', data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(self.client.get('/'), '/inside')
        self.assertContains(self.client.get('/inside'), 'Every universe begins in the void.')
        self.post('/api/auth/logout')
        self.assertContains(self.client.get('/register'), 'Create your account to join campaigns shared with you.')
        data = {**OWNER, 'password': 'wrong-password', 'csrfmiddlewaretoken': self.client.cookies[settings.CSRF_COOKIE_NAME].value}
        response = self.client.post('/login', data, HTTP_DATASTAR_REQUEST='true')
        body = b''.join(response.streaming_content).decode()
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        self.assertIn('event: datastar-patch-elements', body)
        self.assertIn('The email or password is incorrect.', body)
        self.assertNotIn('wrong-password', body)

    def test_user_input_escaped_in_html_and_no_cache(self):
        self.setup_owner()
        self.post('/api/auth/account', {'name': '<img src=x onerror=alert(1)>'})
        page = self.client.get('/inside')
        self.assertContains(page, '&lt;img')
        self.assertNotContains(page, '<img src=x')
        self.assertEqual(page['Cache-Control'], 'no-store')
        self.assertIn("script-src 'self'", page['Content-Security-Policy'])
        self.assertIn("media-src 'self' blob:", page['Content-Security-Policy'])
        self.assertEqual(page['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(self.client.get('/', HTTP_HOST='evil.example').status_code, 400)

    @override_settings(SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True,
                       SESSION_COOKIE_NAME='__Host-gravewright-session',
                       CSRF_COOKIE_NAME='__Host-gravewright-csrf')
    def test_secure_cookie_configuration(self):
        self.client.get('/api/security/csrf', secure=True)
        response = self.post('/api/auth/setup', OWNER, secure=True, HTTP_ORIGIN='https://testserver')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.cookies[settings.SESSION_COOKIE_NAME]['secure'])


class PasswordHashTests(AuthClientMixin, TestCase):
    def test_real_scrypt_hash_and_session_contain_no_password(self):
        self.setup_owner()
        user = User.objects.get()
        self.assertTrue(user.password.startswith('scrypt$'))
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotIn(PASSWORD, user.password)
        self.assertNotIn(PASSWORD, json.dumps(dict(self.client.session.items())))


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class ConcurrentSetupTests(AuthClientMixin, TransactionTestCase):
    def test_only_one_owner_wins_concurrent_setup(self):
        def attempt(index):
            close_old_connections()
            try:
                client = Client(enforce_csrf_checks=True)
                client.get('/api/security/csrf')
                return self.post('/api/auth/setup', {**OWNER, 'email': f'gm{index}@example.test'}, client=client).status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertEqual(sorted(results), [201, 409])
        self.assertEqual(User.objects.filter(role='owner').count(), 1)
