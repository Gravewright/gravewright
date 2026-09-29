"""Local Runner configuration and network boundaries without persistent app data."""

import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from config.runner_asgi import LocalOnlyMiddleware
from scripts.gravewright_runner import (
    DEFAULT_MARKETPLACE_URL,
    RunnerError,
    configure_environment,
    data_directory,
    offer_default_marketplace,
    prepare_environment,
)


class RunnerEnvironmentTests(SimpleTestCase):
    def test_configuration_questions_validate_and_preserve_secret_and_custom_values(self):
        from dotenv import dotenv_values

        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            directory = Path(temp)
            prepare_environment(directory)
            config = directory / '.env'
            with config.open('a', encoding='utf-8') as stream:
                stream.write('# Keep this comment\nCUSTOM_OPTION=literal\n')
            secret = os.environ['DJANGO_SECRET_KEY']
            answers = iter(['Mesa "São Paulo" ${literal}', 'invalid', 'pt-br', '0', '65536',
                            'abc', '3001', 'C:\\My modules', 'maybe', 's', 'n', 'yes'])
            self.assertTrue(configure_environment(directory, prompt=lambda _: next(answers)))
            values = dotenv_values(config, interpolate=False)
            self.assertEqual(values['APP_NAME'], 'Mesa "São Paulo" ${literal}')
            self.assertEqual(values['DEFAULT_LOCALE'], 'pt-BR')
            self.assertEqual(values['GRAVEWRIGHT_PORT'], '3001')
            self.assertEqual(values['GRAVEWRIGHT_MODULES_ROOT'], 'C:\\My modules')
            self.assertEqual(values['CAMPAIGN_JOIN_CODE_ENABLED'], 'true')
            self.assertEqual(values['CAMPAIGN_SNAPSHOTS_ENABLED'], 'false')
            self.assertEqual(values['CAMPAIGN_EXPORT_ENABLED'], 'true')
            self.assertEqual(values['DJANGO_SECRET_KEY'], secret)
            self.assertEqual(values['CUSTOM_OPTION'], 'literal')
            self.assertIn('# Keep this comment', config.read_text(encoding='utf-8'))
            with patch('builtins.input', return_value='') as prompt:
                self.assertTrue(configure_environment(directory, prompt=prompt))
                self.assertEqual(prompt.call_count, 7)
            self.assertEqual(dotenv_values(config, interpolate=False), values)

    def test_cancelled_configuration_can_be_retried_without_partial_answers(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            directory = Path(temp)
            prepare_environment(directory)
            original = (directory / '.env').read_bytes()
            for interrupt in (EOFError, KeyboardInterrupt):
                with patch('builtins.input', side_effect=['Unsaved name', interrupt]) as prompt:
                    with self.assertRaises(RunnerError):
                        configure_environment(directory, prompt=prompt)
                self.assertEqual((directory / '.env').read_bytes(), original)
            configure_environment(directory, prompt=lambda _: '')
            self.assertEqual(prepare_environment(directory), 3000)
            self.assertEqual(os.environ['GRAVEWRIGHT_MODULES_ROOT'], str(directory / 'media/modules'))

    def test_configuration_replaces_export_and_duplicate_assignments(self):
        from dotenv import dotenv_values
        from scripts.gravewright_runner import _update_dotenv

        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / '.env'
            config.write_text('export APP_NAME=Old\nAPP_NAME=Duplicate\n', encoding='utf-8')
            _update_dotenv(config, {'APP_NAME': 'New'})
            self.assertEqual(dotenv_values(config)['APP_NAME'], 'New')
            self.assertEqual(config.read_text(encoding='utf-8').count('APP_NAME='), 1)

    def test_first_run_creates_secret_and_restart_preserves_configuration(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            directory = Path(temp)
            self.assertEqual(prepare_environment(directory), 3000)
            original = (directory / '.env').read_bytes()
            secret = os.environ['DJANGO_SECRET_KEY']
            self.assertGreaterEqual(len(secret), 50)
            self.assertEqual(os.environ['GRAVEWRIGHT_MODULES_ROOT'], str(directory / 'media/modules'))
            self.assertEqual(prepare_environment(directory, 3333), 3333)
            self.assertEqual(os.environ['DJANGO_SECRET_KEY'], secret)
            self.assertEqual((directory / '.env').read_bytes(), original)

    def test_user_features_survive_while_external_settings_cannot_replace_local_bounds(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {
            'DJANGO_SETTINGS_MODULE': 'unsafe.settings', 'GRAVEWRIGHT_RUNNER_TOKEN': 'inherited',
            'GRAVEWRIGHT_DATABASE': '/do-not-use.sqlite3', 'TRUSTED_PROXIES': '0.0.0.0/0',
            'GRAVEWRIGHT_MARKETPLACE_KEYS_FILE': '/do-not-read.json',
        }), patch.object(sys, 'path', sys.path.copy()):
            directory = Path(temp)
            content = ('DJANGO_SECRET_KEY=' + 'a' * 64 + '\nAPP_NAME=Mesa São Paulo\n'
                       'GRAVEWRIGHT_MODULES_ROOT=meus-modulos\n'
                       'GRAVEWRIGHT_HOST=0.0.0.0\nDJANGO_DEBUG=true\n'
                       'GRAVEWRIGHT_PUBLIC_ORIGIN=https://foreign.example\n'
                       'GRAVEWRIGHT_REDIS_URL=redis://foreign.example/0\n')
            (directory / '.env').write_text(content, encoding='utf-8')
            prepare_environment(directory)
            self.assertEqual(os.environ['APP_NAME'], 'Mesa São Paulo')
            self.assertEqual(os.environ['DJANGO_DEBUG'], 'false')
            self.assertEqual(os.environ['DJANGO_SETTINGS_MODULE'], 'config.runner')
            self.assertEqual(os.environ['DJANGO_ALLOWED_HOSTS'], '127.0.0.1')
            self.assertEqual(os.environ['GRAVEWRIGHT_PUBLIC_ORIGIN'], 'http://127.0.0.1:3000')
            self.assertEqual(os.environ['GRAVEWRIGHT_DATABASE'], str(directory / 'gravewright.sqlite3'))
            self.assertEqual(os.environ['GRAVEWRIGHT_MODULES_ROOT'], str(directory / 'meus-modulos'))
            self.assertEqual(os.environ['GRAVEWRIGHT_REDIS_URL'], '')
            self.assertEqual(os.environ['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE'], '')
            self.assertEqual(os.environ['TRUSTED_PROXIES'], '')
            self.assertNotEqual(os.environ['GRAVEWRIGHT_RUNNER_TOKEN'], 'inherited')
            self.assertEqual((directory / '.env').read_text(encoding='utf-8'), content)

    def test_invalid_port_and_missing_secret_fail_without_replacing_user_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for contents in ('GRAVEWRIGHT_PORT=3000\n',
                             'DJANGO_SECRET_KEY=' + 'a' * 64 + '\nGRAVEWRIGHT_PORT=65536\n'):
                (directory / '.env').write_text(contents, encoding='utf-8')
                with self.assertRaises(RunnerError):
                    prepare_environment(directory)
                self.assertEqual((directory / '.env').read_text(encoding='utf-8'), contents)

    def test_default_data_uses_user_profile(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'LOCALAPPDATA': temp}):
            self.assertEqual(data_directory(), Path(temp).resolve() / 'Gravewright' / 'data')

    def test_runner_can_install_default_marketplace_and_remembers_choice(self):
        from dotenv import dotenv_values

        raw = b'{\n  "gravewright-2026": "PXbpURq9J1jLkPnnwBVN/5B+zrb0p5MaWQAe/ltJ8LY="\n}\n'
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, clear=True), patch.object(
            sys, 'path', sys.path.copy()
        ):
            directory = Path(temp)
            prepare_environment(directory)
            self.assertTrue(offer_default_marketplace(
                directory, prompt=lambda _: 'sim', download=lambda: raw,
            ))
            values = dotenv_values(directory / '.env', interpolate=False)
            key_path = directory / 'marketplace' / 'trusted-keys.json'
            self.assertEqual(values['GRAVEWRIGHT_MARKETPLACE_URL'], DEFAULT_MARKETPLACE_URL)
            self.assertEqual(values['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE'], key_path.as_posix())
            self.assertEqual(key_path.read_bytes(), raw)
            self.assertFalse(offer_default_marketplace(
                directory,
                prompt=lambda _: self.fail('The saved choice must prevent another question.'),
            ))

    def test_runner_remembers_declined_default_marketplace(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, clear=True), patch.object(
            sys, 'path', sys.path.copy()
        ):
            directory = Path(temp)
            prepare_environment(directory)
            self.assertFalse(offer_default_marketplace(directory, prompt=lambda _: 'n'))
            self.assertTrue((directory / '.default-marketplace-choice').is_file())
            self.assertFalse(offer_default_marketplace(
                directory,
                prompt=lambda _: self.fail('The saved choice must prevent another question.'),
            ))


@override_settings(GRAVEWRIGHT_PORT=3000)
class RunnerTransportTests(SimpleTestCase):
    async def request(self, *, peer='127.0.0.1', kind='http', hosts=(b'127.0.0.1:3000',), extra=()):
        messages = []

        async def accepted(scope, receive, send):
            messages.append({'type': 'accepted'})

        async def send(message):
            messages.append(message)

        scope = {'type': kind, 'client': (peer, 1234) if peer else None,
                 'headers': [(b'host', host) for host in hosts] + list(extra)}
        await LocalOnlyMiddleware(accepted)(scope, None, send)
        return messages

    async def test_loopback_with_exact_host_and_port_reaches_the_application(self):
        for kind in ('http', 'websocket'):
            self.assertEqual(await self.request(kind=kind), [{'type': 'accepted'}])

    async def test_forwarded_headers_cannot_make_remote_peer_local(self):
        for peer in ('192.0.2.1', None):
            for kind in ('http', 'websocket'):
                response = await self.request(peer=peer, kind=kind, extra=[
                    (b'x-forwarded-for', b'127.0.0.1'), (b'x-forwarded-proto', b'http'),
                ])
                self.assertEqual(response[0].get('status', response[0].get('code')),
                                 403 if kind == 'http' else 4403)

    async def test_missing_duplicate_foreign_or_wrong_port_host_is_rejected(self):
        for hosts in ((), (b'127.0.0.1:3000',) * 2, (b'evil.example:3000',),
                      (b'127.0.0.1:3001',), (b'127.0.0.1',)):
            with self.subTest(hosts=hosts):
                self.assertEqual((await self.request(hosts=hosts))[0]['status'], 400)
