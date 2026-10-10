"""Local Runner configuration and network boundaries without persistent app data."""

import os
from io import StringIO
from pathlib import Path
import sys
import tempfile
import shutil
import json
import subprocess
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from config.runner_asgi import LocalOnlyMiddleware
from scripts import gravewright_runner as runner
from scripts.gravewright_runner import (
    DEFAULT_MARKETPLACE_URL,
    RunnerError,
    configure_environment,
    data_directory,
    offer_default_marketplace,
    prepare_environment,
)


class RunnerEnvironmentTests(SimpleTestCase):
    def setUp(self):
        project = self.enterContext(tempfile.TemporaryDirectory())
        root = Path(project)
        shutil.copy2(runner.ROOT / '.env.example', root / '.env.example')
        self.enterContext(patch.object(runner, 'ROOT', root))
        self.enterContext(patch.object(runner, 'LANGUAGE', runner.RunnerLanguage()))

    def test_runner_locale_comes_from_project_not_inherited_or_user_configuration(self):
        config = runner.ROOT / '.env'
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, DEFAULT_LOCALE='pt-BR'):
            (Path(temporary) / '.env').write_text('DEFAULT_LOCALE=pt-BR\n', encoding='utf-8')
            config.write_text('DEFAULT_LOCALE=en\n', encoding='utf-8')
            runner.LANGUAGE.from_project()
            self.assertEqual(runner.tr('Configuration saved.'), 'Configuration saved.')
            config.write_text('DEFAULT_LOCALE=pt-BR\n', encoding='utf-8')
            runner.LANGUAGE.from_project()
            self.assertEqual(runner.tr('Configuration saved.'), 'Configuração salva.')
            self.assertEqual(str(RunnerError('GRAVEWRIGHT_PORT must be a number from 1 to 65535.')),
                             'GRAVEWRIGHT_PORT deve ser um número de 1 a 65535.')

    def test_installer_changes_language_immediately_in_both_directions(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            directory = Path(temporary)
            prepare_environment(directory)
            for locale, expected_port, expected_bool, expected_saved in (
                    ('pt-BR', 'Porta local', '(s/n)', 'Configuração salva.'),
                    ('en', 'Local port', '(y/n)', 'Configuration saved.')):
                answers = iter(['', locale, '', '', '', '', '', ''])
                prompts = []
                def answer(message):
                    prompts.append(message)
                    return next(answers)
                with patch('sys.stdout', new_callable=StringIO) as output:
                    configure_environment(directory, prompt=answer)
                self.assertIn(expected_port, prompts[2])
                self.assertIn(expected_bool, prompts[-1])
                self.assertIn(expected_saved, output.getvalue())

    def test_runner_uses_active_translator_and_preserves_formatted_values(self):
        runner.LANGUAGE.configure('pt-BR')
        with patch('gravewright.modules.localization.catalogs', return_value={
                'pt-BR': {'name': 'Português', 'messages': {'Runner test: {path}': 'Teste do Runner: {path}'}}}):
            runner.LANGUAGE.load_translator()
        path = r'C:\Mesa {name}\São Paulo'
        self.assertEqual(runner.tr('Runner test: {path}', path=path), 'Teste do Runner: ' + path)
        self.assertEqual(runner.tr('Unknown message: {path}', path=path), 'Unknown message: ' + path)
        self.assertEqual(runner.tr('Configuration saved.'), 'Configuração salva.')

    def test_portuguese_startup_errors_work_before_database_setup(self):
        (runner.ROOT / '.env').write_text('DEFAULT_LOCALE=pt-BR\n', encoding='utf-8')
        with patch.object(runner, 'data_directory', side_effect=lambda _: (_ for _ in ()).throw(
                RunnerError('The data directory must be separate from the project root.'))):
            with patch('sys.stderr', new_callable=StringIO) as output:
                self.assertEqual(runner.main(['--no-browser']), 1)
            self.assertIn('A pasta de dados deve ser diferente da raiz do projeto.', output.getvalue())

    def test_legacy_byte_limits_are_migrated_without_changing_sizes(self):
        from dotenv import dotenv_values
        from config.size_limits import SIZE_DEFAULTS, size_bytes

        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            config = runner.ROOT / '.env'
            config.write_text('DJANGO_SECRET_KEY=' + 'x' * 64 + '\n'
                              + ''.join(f'{name}=12345\n' for name in SIZE_DEFAULTS), encoding='utf-8')
            prepare_environment(Path(temporary))
            saved = config.read_bytes()
            values = dotenv_values(config, interpolate=False)
            for name, default in SIZE_DEFAULTS.items():
                key = name.removesuffix('_BYTES') + '_MB'
                self.assertNotIn(name, values)
                self.assertNotIn(name, os.environ)
                self.assertEqual(size_bytes(values, name, default), 12345)
                self.assertEqual(os.environ[key], values[key])
            prepare_environment(Path(temporary))
            self.assertEqual(config.read_bytes(), saved)

    def test_django_child_and_supervisor_use_database_and_media_from_project_configuration(self):
        from scripts.update_supervisor import Supervisor

        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            state = Path(temporary)
            config = runner.ROOT / '.env'
            config.write_text('DJANGO_SECRET_KEY=' + 'x' * 64
                              + '\nGRAVEWRIGHT_DATABASE=custom/db.sqlite3\n'
                              'GRAVEWRIGHT_MEDIA_ROOT=custom/uploads\n'
                              'GRAVEWRIGHT_MODULES_ROOT=custom/modules\n', encoding='utf-8')
            prepare_environment(state)
            expected = [str(runner.ROOT / name) for name in
                        ('custom/db.sqlite3', 'custom/uploads', 'custom/modules')]
            supervisor = Supervisor(runner.ROOT, state / 'updates',
                                    os.environ['GRAVEWRIGHT_DATABASE'], os.environ['GRAVEWRIGHT_MEDIA_ROOT'],
                                    '127.0.0.1', 3000)
            result = subprocess.run([sys.executable, '-X', 'utf8', '-c',
                'import django, json; django.setup(); from django.conf import settings; '
                'print(json.dumps([str(settings.DATABASES["default"]["NAME"]), '
                'str(settings.MEDIA_ROOT), str(settings.GRAVEWRIGHT_MODULES_ROOT)]))'],
                env=supervisor.env, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout), expected)
            self.assertEqual(str(supervisor.database), expected[0])
            self.assertEqual(str(supervisor.media), expected[1])
            self.assertFalse((state / 'gravewright.sqlite3').exists())

    def test_user_data_configuration_is_ignored_even_when_project_env_is_missing(self):
        from dotenv import dotenv_values

        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            directory = Path(temp)
            legacy = directory / '.env'
            content = 'DJANGO_SECRET_KEY=' + 'a' * 64 + '\nGRAVEWRIGHT_PORT=3001\nDEFAULT_LOCALE=pt-BR\n'
            legacy.write_text(content, encoding='utf-8')
            self.assertEqual(prepare_environment(directory), 3000)
            saved = (runner.ROOT / '.env').read_bytes()
            values = dotenv_values(runner.ROOT / '.env', interpolate=False)
            self.assertNotEqual(values['DJANGO_SECRET_KEY'], 'a' * 64)
            self.assertEqual(values['DEFAULT_LOCALE'], 'en')
            self.assertEqual(legacy.read_text(encoding='utf-8'), content)
            legacy.write_text('invalid legacy configuration', encoding='utf-8')
            self.assertEqual(prepare_environment(directory), 3000)
            self.assertEqual((runner.ROOT / '.env').read_bytes(), saved)
            (runner.ROOT / '.env').unlink()
            self.assertEqual(prepare_environment(directory), 3000)
            self.assertNotEqual((runner.ROOT / '.env').read_bytes(), saved)

    def test_configuration_questions_validate_and_preserve_secret_and_custom_values(self):
        from dotenv import dotenv_values

        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            directory = Path(temp)
            prepare_environment(directory)
            config = runner.ROOT / '.env'
            with config.open('a', encoding='utf-8') as stream:
                stream.write('# Keep this comment\nCUSTOM_OPTION=literal\n')
            secret = os.environ['DJANGO_SECRET_KEY']
            answers = iter(['Mesa "São Paulo" ${literal}', 'invalid', 'pt-br', '0', '65536',
                            'abc', '3001', 'C:\\My modules', 'maybe', 's', 'n', 'yes', 'n'])
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
                self.assertEqual(prompt.call_count, 8)
            self.assertEqual(dotenv_values(config, interpolate=False), values)

    def test_cancelled_configuration_can_be_retried_without_partial_answers(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            directory = Path(temp)
            prepare_environment(directory)
            original = (runner.ROOT / '.env').read_bytes()
            for interrupt in (EOFError, KeyboardInterrupt):
                with patch('builtins.input', side_effect=['Unsaved name', interrupt]) as prompt:
                    with self.assertRaises(RunnerError):
                        configure_environment(directory, prompt=prompt)
                self.assertEqual((runner.ROOT / '.env').read_bytes(), original)
            configure_environment(directory, prompt=lambda _: '')
            self.assertEqual(prepare_environment(directory), 3000)
            self.assertEqual(os.environ['GRAVEWRIGHT_MODULES_ROOT'], str(runner.ROOT / 'data/media/modules'))

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
        from dotenv import dotenv_values

        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            directory = Path(temp)
            self.assertEqual(prepare_environment(directory), 3000)
            original = (runner.ROOT / '.env').read_bytes()
            sample = dotenv_values(runner.ROOT / '.env.example', interpolate=False)
            generated = dotenv_values(runner.ROOT / '.env', interpolate=False)
            self.assertTrue(set(sample).issubset(generated))
            for line in (runner.ROOT / '.env.example').read_text(encoding='utf-8').splitlines():
                if line.startswith('#') and not line.startswith('# DJANGO_SECRET_KEY='):
                    self.assertIn(line, original.decode('utf-8'))
            secret = os.environ['DJANGO_SECRET_KEY']
            self.assertGreaterEqual(len(secret), 50)
            self.assertEqual(os.environ['GRAVEWRIGHT_MODULES_ROOT'], str(runner.ROOT / 'data/media/modules'))
            self.assertEqual(prepare_environment(directory, 3333), 3333)
            self.assertEqual(os.environ['DJANGO_SECRET_KEY'], secret)
            self.assertEqual((runner.ROOT / '.env').read_bytes(), original)

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
            (runner.ROOT / '.env').write_text(content, encoding='utf-8')
            prepare_environment(directory)
            self.assertEqual(os.environ['APP_NAME'], 'Mesa São Paulo')
            self.assertEqual(os.environ['DJANGO_DEBUG'], 'false')
            self.assertEqual(os.environ['DJANGO_SETTINGS_MODULE'], 'config.runner')
            self.assertEqual(os.environ['DJANGO_ALLOWED_HOSTS'], '127.0.0.1')
            self.assertEqual(os.environ['GRAVEWRIGHT_PUBLIC_ORIGIN'], 'http://127.0.0.1:3000')
            self.assertEqual(os.environ['GRAVEWRIGHT_DATABASE'], str(runner.ROOT / 'data/gravewright.sqlite3'))
            self.assertEqual(os.environ['GRAVEWRIGHT_MODULES_ROOT'], str(runner.ROOT / 'meus-modulos'))
            self.assertEqual(os.environ['GRAVEWRIGHT_REDIS_URL'], '')
            self.assertEqual(os.environ['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE'], '')
            self.assertEqual(os.environ['TRUSTED_PROXIES'], '')
            self.assertNotEqual(os.environ['GRAVEWRIGHT_RUNNER_TOKEN'], 'inherited')
            from dotenv import dotenv_values
            saved = dotenv_values(runner.ROOT / '.env', interpolate=False)
            for key, value in dotenv_values(stream=StringIO(content), interpolate=False).items():
                self.assertEqual(saved[key], value)

    def test_incomplete_configuration_gets_example_sections_without_losing_custom_settings(self):
        from dotenv import dotenv_values

        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            config = runner.ROOT / '.env'
            config.write_text('# Owner note\nDJANGO_SECRET_KEY=' + 'b' * 64
                              + '\nAPP_NAME="Mesa ${literal}"\nCUSTOM_OPTION=keep\n', encoding='utf-8')
            prepare_environment(Path(temp))
            values = dotenv_values(config, interpolate=False)
            self.assertEqual(values['DJANGO_SECRET_KEY'], 'b' * 64)
            self.assertEqual(values['APP_NAME'], 'Mesa ${literal}')
            self.assertEqual(values['CUSTOM_OPTION'], 'keep')
            self.assertIn('# Owner note', config.read_text(encoding='utf-8'))
            self.assertTrue(set(dotenv_values(runner.ROOT / '.env.example')).issubset(values))
            original = config.read_bytes()
            prepare_environment(Path(temp))
            self.assertEqual(config.read_bytes(), original)

    def test_installer_enables_all_tunnels_without_asking_for_a_url(self):
        from dotenv import dotenv_values

        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            directory = Path(temporary)
            prepare_environment(directory)
            answers = iter([''] * 7 + ['y'])
            configure_environment(directory, prompt=lambda _: next(answers))
            values = dotenv_values(runner.ROOT / '.env', interpolate=False)
            self.assertEqual(values['GRAVEWRIGHT_ALLOW_TUNNELS'], 'true')
            self.assertEqual(values['GRAVEWRIGHT_PUBLIC_ORIGIN'], '')
            prepare_environment(directory)
            self.assertEqual(os.environ['GRAVEWRIGHT_HOST'], '127.0.0.1')
            self.assertEqual(os.environ['DJANGO_SECURE_COOKIES'], 'false')
            self.assertEqual(os.environ['TRUSTED_PROXIES'], '127.0.0.1/32,::1/128')
            result = subprocess.run([sys.executable, '-X', 'utf8', '-c',
                'import django, json; django.setup(); from django.conf import settings; '
                'print(json.dumps([settings.GRAVEWRIGHT_ALLOW_TUNNELS, settings.SESSION_COOKIE_SECURE, '
                'settings.CSRF_TRUSTED_ORIGINS, settings.ALLOWED_HOSTS]))'],
                capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout), [True, False, [], ['*']])

    def test_tunnels_do_not_require_or_pin_a_public_origin(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            config = runner.ROOT / '.env'
            config.write_text('DJANGO_SECRET_KEY=' + 'x' * 64 + '\nGRAVEWRIGHT_ALLOW_TUNNELS=true\n', encoding='utf-8')
            prepare_environment(Path(temporary))
            self.assertEqual(os.environ['GRAVEWRIGHT_PUBLIC_ORIGIN'], '')
            self.assertEqual(os.environ['DJANGO_ALLOWED_HOSTS'], '*')

    def test_invalid_port_and_missing_secret_fail_without_replacing_user_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for contents in ('GRAVEWRIGHT_PORT=3000\n',
                             'DJANGO_SECRET_KEY=' + 'a' * 64 + '\nGRAVEWRIGHT_PORT=65536\n'):
                (runner.ROOT / '.env').write_text(contents, encoding='utf-8')
                with self.assertRaises(RunnerError):
                    prepare_environment(directory)
                self.assertEqual((runner.ROOT / '.env').read_text(encoding='utf-8'), contents)

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
            values = dotenv_values(runner.ROOT / '.env', interpolate=False)
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

    @override_settings(GRAVEWRIGHT_ALLOW_TUNNELS=True, GRAVEWRIGHT_PUBLIC_ORIGIN='')
    async def test_tunnels_accept_any_public_host_from_local_agents(self):
        for kind in ('http', 'websocket'):
            for host in (b'table.example', b'any.ngrok-free.app', b'changing.trycloudflare.com', b'custom.example:8080'):
                self.assertEqual(await self.request(kind=kind, hosts=(host,)), [{'type': 'accepted'}])
            rejected = await self.request(kind=kind, hosts=(b'table.example',), peer='192.0.2.1')
            self.assertEqual(rejected[0].get('status', rejected[0].get('code')), 403 if kind == 'http' else 4403)
            for hosts in ((), (b'table.example', b'other.example')):
                rejected = await self.request(kind=kind, hosts=hosts)
                self.assertEqual(rejected[0].get('status', rejected[0].get('code')), 400 if kind == 'http' else 4403)

    @override_settings(GRAVEWRIGHT_ALLOW_TUNNELS=True, GRAVEWRIGHT_PUBLIC_ORIGIN='', ALLOWED_HOSTS=['*'])
    async def test_tunnel_websocket_origins_follow_each_host_without_pinning_a_url(self):
        from gravewright.realtime.security import SameOriginWebSocketMiddleware

        for host in ('first.example', 'second.example', 'third.example:8080'):
            for scheme in ('http', 'https'):
                messages = []
                async def accepted(scope, receive, send):
                    messages.append('accepted')
                async def send(message):
                    messages.append(message)
                scope = {'type': 'websocket', 'scheme': 'ws', 'client': ('127.0.0.1', 1234),
                         'headers': [(b'host', host.encode()), (b'origin', f'{scheme}://{host}'.encode())]}
                application = LocalOnlyMiddleware(SameOriginWebSocketMiddleware(accepted))
                await application(scope, None, send)
                self.assertEqual(messages, ['accepted'])
                messages.clear()
                scope['headers'][1] = (b'origin', b'https://other.example')
                await application(scope, None, send)
                self.assertEqual(messages, [{'type': 'websocket.close', 'code': 4403}])
