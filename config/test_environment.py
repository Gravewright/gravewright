import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config.environment import BASE_DIR, env_bool, env_path, load_environment, public_origin


class EnvironmentTests(unittest.TestCase):
    def test_dotenv_priority_and_literal_secrets(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'PORT': '9000'}, clear=True):
            root = Path(directory)
            (root / '.env').write_text('PORT=3000\nSECRET="literal-${PORT}-#-value"\n')
            load_environment(root)
            self.assertEqual(os.environ['PORT'], '9000')
            self.assertEqual(os.environ['SECRET'], 'literal-${PORT}-#-value')

    def test_paths_are_project_relative(self):
        with patch.dict(os.environ, {'GRAVEWRIGHT_DATABASE': 'data/custom.sqlite3'}):
            self.assertEqual(env_path('GRAVEWRIGHT_DATABASE', ''), BASE_DIR / 'data/custom.sqlite3')

    def test_booleans(self):
        for value, expected in [('true', True), (' ON ', True), ('false', False), ('0', False)]:
            with self.subTest(value=value), patch.dict(os.environ, {'TEST_BOOL': value}):
                self.assertEqual(env_bool('TEST_BOOL'), expected)
        with patch.dict(os.environ, {'TEST_BOOL': 'typo'}):
            with self.assertRaises(ValueError):
                env_bool('TEST_BOOL')

    def test_public_origin_validation(self):
        for value in ['https://example.org/path', 'https://user@example.org',
                      'https://example.org:99999', 'https://example.org:0', 'ftp://example.org',
                      'https://example.org:', 'https://example.org?', 'https://example.org#',
                      '\x01https://example.org', 'https://exam\x7fple.org']:
            with self.subTest(value=value), patch.dict(os.environ, {'GRAVEWRIGHT_PUBLIC_ORIGIN': value}):
                with self.assertRaises(ValueError):
                    public_origin()

    def test_public_origin_normalizes_scheme_host_and_ipv6(self):
        for value, expected in [
            ('HTTPS://VTT.EXAMPLE:8443', ('https://vtt.example:8443', 'vtt.example')),
            ('HTTPS://[2001:DB8::1]:8443', ('https://[2001:db8::1]:8443', '[2001:db8::1]')),
        ]:
            with self.subTest(value=value), patch.dict(os.environ, {'GRAVEWRIGHT_PUBLIC_ORIGIN': value}):
                self.assertEqual(public_origin(), expected)

    def test_https_origin_configures_django(self):
        # Reload settings with a controlled environment; never change the local .env.
        import config.settings as settings
        try:
            for origin in ('https://vtt.example.org:8443', 'HTTPS://VTT.EXAMPLE.ORG:8443'):
                with self.subTest(origin=origin), patch.dict(os.environ, {
                    'GRAVEWRIGHT_PUBLIC_ORIGIN': origin,
                    'DJANGO_DEBUG': 'true', 'DJANGO_SECURE_COOKIES': 'false',
                    'DJANGO_ALLOWED_HOSTS': ' localhost , 127.0.0.1 ',
                }):
                    importlib.reload(settings)
                    self.assertIn('vtt.example.org', settings.ALLOWED_HOSTS)
                    self.assertIn('localhost', settings.ALLOWED_HOSTS)
                    self.assertEqual(settings.CSRF_TRUSTED_ORIGINS, ['https://vtt.example.org:8443'])
                    self.assertTrue(settings.SESSION_COOKIE_SECURE)
                    self.assertTrue(settings.CSRF_COOKIE_SECURE)
                    self.assertEqual(settings.SECURE_HSTS_SECONDS, 31536000)
        finally:
            importlib.reload(settings)

    def test_launcher_uses_configured_address(self):
        from main import main
        with patch.dict(os.environ, {'DJANGO_SETTINGS_MODULE': 'config.settings'}), patch(
            'django.core.management.execute_from_command_line'
        ) as execute, patch('sys.argv', ['main.py', '--noreload']), patch(
            'django.conf.settings.GRAVEWRIGHT_HOST', '::1'
        ), patch('django.conf.settings.GRAVEWRIGHT_PORT', 3123):
            main()
            execute.assert_called_once_with(['main.py', 'runserver', '[::1]:3123', '--noreload'])
