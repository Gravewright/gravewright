"""Local Runner configuration and network boundaries without persistent app data."""

import os
from io import StringIO
from pathlib import Path
import sys
import tempfile
import shutil
import json
import hashlib
import subprocess
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from config.runner_asgi import LocalOnlyMiddleware
from scripts import gravewright_runner as runner
from scripts.gravewright_runner import (
    DEFAULT_MARKETPLACE_URL,
    RunnerError,
    configure_environment,
    data_directory,
    ensure_default_marketplace,
    prepare_environment,
)


class RunnerEnvironmentTests(SimpleTestCase):
    def setUp(self):
        project = self.enterContext(tempfile.TemporaryDirectory())
        # Match the production ROOT, including Windows 8.3 and macOS /var aliases.
        root = Path(project).resolve()
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
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp).resolve() / 'home'
            windows = home / 'Windows state'
            xdg = home / 'XDG state'
            cases = (
                ('win32', {'LOCALAPPDATA': str(windows), 'XDG_DATA_HOME': str(xdg)}, windows / 'Gravewright/data'),
                ('darwin', {'LOCALAPPDATA': str(windows), 'XDG_DATA_HOME': str(xdg)}, home / 'Library/Application Support/Gravewright/data'),
                ('linux', {'LOCALAPPDATA': str(windows), 'XDG_DATA_HOME': str(xdg)}, xdg / 'Gravewright/data'),
                ('linux', {'LOCALAPPDATA': str(windows)}, home / '.local/share/Gravewright/data'),
            )
            for platform, environment, expected in cases:
                with self.subTest(platform=platform, environment=environment), \
                        patch.object(sys, 'platform', platform), \
                        patch.object(Path, 'home', return_value=home), \
                        patch.dict(os.environ, environment, clear=True):
                    self.assertEqual(data_directory(), expected)

    def test_runner_configures_default_marketplace_without_a_question_and_is_offline_on_repeat(self):
        from dotenv import dotenv_values

        raw = RunnerDefaultKeysTests.keys
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, clear=True), patch.object(
            sys, 'path', sys.path.copy()
        ):
            directory = Path(temp)
            prepare_environment(directory)
            self.assertTrue(ensure_default_marketplace(
                directory, download=lambda: raw,
            ))
            values = dotenv_values(runner.ROOT / '.env', interpolate=False)
            key_path = runner.marketplace_directory(directory) / 'trusted-keys.json'
            self.assertEqual(values['GRAVEWRIGHT_MARKETPLACE_URL'], DEFAULT_MARKETPLACE_URL)
            self.assertEqual(values['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE'], key_path.as_posix())
            self.assertEqual(key_path.read_bytes(), raw)
            original = (runner.ROOT / '.env').read_bytes()
            with patch.object(runner, '_write_private') as write:
                self.assertFalse(ensure_default_marketplace(
                    directory, download=lambda: self.fail('Configured official keys must work offline.'),
                ))
                write.assert_not_called()
            self.assertEqual((runner.ROOT / '.env').read_bytes(), original)

    def test_old_declined_marker_does_not_prevent_automatic_default_marketplace(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, clear=True), patch.object(
            sys, 'path', sys.path.copy()
        ):
            directory = Path(temp)
            prepare_environment(directory)
            marker = runner.marketplace_directory(directory) / runner.DEFAULT_MARKETPLACE_CHOICE
            marker.parent.mkdir(parents=True)
            marker.write_text('declined\n', encoding='utf-8')
            self.assertTrue(ensure_default_marketplace(directory, download=lambda: RunnerDefaultKeysTests.keys))
            self.assertEqual(marker.read_text(encoding='utf-8'), 'installed\n')
            self.assertEqual(os.environ['GRAVEWRIGHT_MARKETPLACE_URL'], DEFAULT_MARKETPLACE_URL)

    def test_automatic_catalog_keys_are_per_installation_and_ignore_legacy_global_marker(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, clear=True):
            directory = Path(temporary)
            (directory / '.default-marketplace-choice').write_text('declined\n', encoding='utf-8')
            first = runner.ROOT / 'first'
            second = runner.ROOT / 'second'
            with patch.object(runner, 'ROOT', first):
                self.assertTrue(ensure_default_marketplace(directory, download=lambda: RunnerDefaultKeysTests.keys))
                first_keys = Path(os.environ['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE'])
                self.assertEqual(first_keys, runner.marketplace_directory(directory) / 'trusted-keys.json')
            os.environ['GRAVEWRIGHT_MARKETPLACE_URL'] = ''
            os.environ['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE'] = ''
            with patch.object(runner, 'ROOT', second):
                self.assertTrue(ensure_default_marketplace(directory, download=lambda: RunnerDefaultKeysTests.keys))
                second_keys = Path(os.environ['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE'])
                self.assertEqual(second_keys, runner.marketplace_directory(directory) / 'trusted-keys.json')
                self.assertNotEqual(first_keys, second_keys)

    def test_existing_custom_catalog_configuration_is_preserved_without_network_or_writes(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {
                'GRAVEWRIGHT_MARKETPLACE_URL': 'https://catalog.example/catalog.json',
                'GRAVEWRIGHT_MARKETPLACE_KEYS_FILE': 'custom-trust.json'}):
            with patch.object(runner, '_write_private') as write:
                self.assertFalse(ensure_default_marketplace(
                    Path(temporary), download=lambda: self.fail('A custom catalog must not need official keys.'),
                ))
                write.assert_not_called()
            self.assertEqual(os.environ['GRAVEWRIGHT_MARKETPLACE_URL'], 'https://catalog.example/catalog.json')
            self.assertEqual(os.environ['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE'], 'custom-trust.json')

    def test_keys_installed_for_translation_allow_automatic_catalog_configuration_offline(self):
        raw = RunnerDefaultKeysTests.keys
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, clear=True):
            directory = Path(temporary)
            custom = directory / 'custom-trust.json'
            custom.write_bytes(raw)
            os.environ['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE'] = str(custom)
            self.assertTrue(ensure_default_marketplace(
                directory, download=lambda: self.fail('Validated local keys do not need a download.'),
            ))
            self.assertEqual(os.environ['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE'], custom.as_posix())
            self.assertEqual(custom.read_bytes(), raw)
            self.assertEqual(os.environ['GRAVEWRIGHT_MARKETPLACE_URL'], DEFAULT_MARKETPLACE_URL)

    def test_automatic_official_catalog_merges_keys_without_overwriting_the_custom_file(self):
        raw = RunnerDefaultKeysTests.keys
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, clear=True):
            directory = Path(temporary)
            custom = directory / 'custom-trust.json'
            original = b'{"custom-publisher":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="}'
            custom.write_bytes(original)
            os.environ['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE'] = str(custom)
            self.assertTrue(ensure_default_marketplace(directory, download=lambda: raw))
            self.assertEqual(custom.read_bytes(), original)
            saved = Path(os.environ['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE'])
            self.assertEqual(saved, runner.marketplace_directory(directory) / 'trusted-keys.json')
            self.assertEqual(json.loads(saved.read_bytes()), {**json.loads(original), **json.loads(raw)})
            self.assertFalse(ensure_default_marketplace(
                directory, download=lambda: self.fail('Merged official/custom keys must work offline.'),
            ))

    def test_existing_official_catalog_with_missing_keys_is_repaired(self):
        from dotenv import dotenv_values

        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {
                'GRAVEWRIGHT_MARKETPLACE_URL': DEFAULT_MARKETPLACE_URL,
                'GRAVEWRIGHT_MARKETPLACE_KEYS_FILE': ''}, clear=True):
            directory = Path(temporary)
            self.assertTrue(ensure_default_marketplace(directory, download=lambda: RunnerDefaultKeysTests.keys))
            values = dotenv_values(runner.ROOT / '.env', interpolate=False)
            self.assertEqual(values['GRAVEWRIGHT_MARKETPLACE_URL'], DEFAULT_MARKETPLACE_URL)
            self.assertEqual(json.loads(Path(values['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE']).read_bytes()),
                             runner.DEFAULT_MARKETPLACE_PUBLIC_KEYS)

    def test_existing_official_catalog_with_previous_signing_key_adds_the_reviewed_key(self):
        raw = RunnerDefaultKeysTests.keys
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, clear=True):
            directory = Path(temporary)
            custom = directory / 'previous-keys.json'
            original = json.dumps({'gravewright-2026': runner.DEFAULT_MARKETPLACE_PUBLIC_KEYS['gravewright-2026']}).encode()
            custom.write_bytes(original)
            os.environ.update({'GRAVEWRIGHT_MARKETPLACE_URL': DEFAULT_MARKETPLACE_URL,
                               'GRAVEWRIGHT_MARKETPLACE_KEYS_FILE': str(custom)})
            self.assertTrue(ensure_default_marketplace(directory, download=lambda: raw))
            self.assertEqual(custom.read_bytes(), original)
            self.assertEqual(json.loads(Path(os.environ['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE']).read_bytes()),
                             runner.DEFAULT_MARKETPLACE_PUBLIC_KEYS)

    def test_automatic_catalog_download_failure_does_not_change_configuration(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, clear=True):
            config = runner.ROOT / '.env'
            config.write_text('GRAVEWRIGHT_MARKETPLACE_URL=\nCUSTOM_OPTION=keep\n', encoding='utf-8')
            original = config.read_bytes()
            download = Mock(side_effect=RunnerError('Could not download the default marketplace public keys.'))
            with self.assertRaisesRegex(RunnerError, 'Could not download'):
                ensure_default_marketplace(Path(temporary), download=download)
            self.assertEqual(config.read_bytes(), original)
            self.assertNotIn('GRAVEWRIGHT_MARKETPLACE_URL', os.environ)

    def test_official_key_conflicts_or_invalid_custom_files_leave_configuration_unchanged(self):
        raw = RunnerDefaultKeysTests.keys
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, clear=True):
            directory = Path(temporary)
            custom = directory / 'custom-trust.json'
            config = runner.ROOT / '.env'
            config.write_text('GRAVEWRIGHT_MARKETPLACE_URL=\nCUSTOM_OPTION=keep\n', encoding='utf-8')
            original = config.read_bytes()
            os.environ['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE'] = str(custom)
            cases = (
                b'{"gravewright-2026":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="}',
                b'not a json file',
                b'{"invalid-publisher":"short"}',
            )
            for content in cases:
                with self.subTest(content=content):
                    custom.write_bytes(content)
                    with self.assertRaises(RunnerError):
                        ensure_default_marketplace(directory, download=lambda: raw)
                    self.assertEqual(custom.read_bytes(), content)
                    self.assertEqual(config.read_bytes(), original)
                    self.assertFalse((runner.marketplace_directory(directory) / runner.DEFAULT_MARKETPLACE_CHOICE).exists())

    def test_interactive_installer_configures_catalog_before_preparing_translation(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {'DEFAULT_LOCALE': 'pt-BR'}):
            events = []
            with patch.object(runner, 'data_directory', return_value=Path(temporary)), \
                    patch.object(runner, 'instance_lock'), \
                    patch.object(runner, 'prepare_environment', return_value=3000), \
                    patch.object(runner, 'configure_environment', side_effect=lambda _: events.append('configure')), \
                    patch.object(runner, 'ensure_default_marketplace', side_effect=lambda _: events.append('marketplace')), \
                    patch.object(runner, 'prepare_application', side_effect=lambda _: events.append('application')), \
                    patch('gravewright.administration.models.HostSettings.objects.update_or_create'):
                self.assertEqual(runner.main(['--configure-default-marketplace']), 0)
            self.assertEqual(events, ['configure', 'marketplace', 'application'])

    def test_noninteractive_runner_check_never_prompts_for_catalog_configuration(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            with patch.object(runner, 'prepare_application'), \
                    patch.object(runner, 'configure_logging', return_value=Path(temporary) / 'runner.log'), \
                    patch.object(runner, 'configure_environment') as configure, \
                    patch.object(runner, 'ensure_default_marketplace') as ensure, \
                    patch('scripts.update_supervisor.Supervisor') as supervisor:
                self.assertEqual(runner.main(['--check', '--data-dir', temporary]), 0)
                configure.assert_not_called()
                ensure.assert_not_called()
                supervisor.return_value.recover.assert_called_once()
                configure.reset_mock()
                ensure.reset_mock()
                self.assertEqual(runner.main(['--check', '--configure-default-marketplace', '--data-dir', temporary]), 0)
                configure.assert_not_called()
                ensure.assert_not_called()


class RunnerPortugueseMarketplaceTests(SimpleTestCase):
    # Exercise the first-install Translator branch without downloading packages
    # or touching any real database, catalog, configuration or trust store.
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        shutil.copy2(runner.ROOT / '.env.example', root / '.env.example')
        self.enterContext(patch.object(runner, 'ROOT', root))
        self.enterContext(patch.object(runner, 'LANGUAGE', runner.RunnerLanguage()))

    def test_translation_preparation_does_not_configure_a_catalog_during_unattended_checks(self):
        from dotenv import dotenv_values

        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ), patch.object(sys, 'path', sys.path.copy()):
            directory = Path(temporary)
            prepare_environment(directory)
            row = Mock(pk=1, version='0.2.2', locale_catalogs={'pt-BR': 'pt-BR.json'})
            record = {'id': 'gravewright.translator', 'version': '0.2.2', 'sdk': '>=1.0.0',
                      'download': 'https://example.org/translator.zip'}
            with override_settings(DEFAULT_LOCALE='pt-BR', GRAVEWRIGHT_MARKETPLACE_URL='',
                                   GRAVEWRIGHT_MARKETPLACE_KEYS_FILE=''), \
                    patch('gravewright.modules.models.Package') as package, \
                    patch('gravewright.modules.packages.host') as host, \
                    patch('gravewright.modules.packages.ModulePackages') as engine, \
                    patch('gravewright.modules.views.download', side_effect=[json.dumps([record]).encode(), b'archive']), \
                    patch.object(runner, '_download_default_keys', return_value=RunnerDefaultKeysTests.keys), \
                    patch.object(runner.LANGUAGE, 'load_translator'), \
                    patch('django.db.transaction.atomic'):
                package.objects.filter.return_value.order_by.return_value.first.return_value = None
                package.objects.get.return_value = row
                engine.return_value.install.return_value = {'id': record['id'], 'version': record['version']}
                runner.ensure_portuguese_translation(directory)
                host.assert_called_once()
                engine.return_value.install.assert_called_once()
                row.save.assert_called_once_with(update_fields=['global_enabled'])
            values = dotenv_values(runner.ROOT / '.env', interpolate=False)
            self.assertEqual(values['GRAVEWRIGHT_MARKETPLACE_URL'], '')
            self.assertEqual(os.environ['GRAVEWRIGHT_MARKETPLACE_URL'], '')
            self.assertEqual(json.loads(Path(values['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE']).read_bytes()),
                             json.loads(RunnerDefaultKeysTests.keys))
            self.assertTrue(ensure_default_marketplace(
                directory, download=lambda: self.fail('Translation already installed the pinned keys.'),
            ))
            self.assertEqual(os.environ['GRAVEWRIGHT_MARKETPLACE_URL'], DEFAULT_MARKETPLACE_URL)


class RunnerDefaultKeysTests(SimpleTestCase):
    # Exact bytes from the reviewed official marketplace revision. This is a
    # public trust-store fixture, not a signing key or an online test dependency.
    keys = (b'{\n  "gravewright-2026": "PXbpURq9J1jLkPnnwBVN/5B+zrb0p5MaWQAe/ltJ8LY=",\n'
            b'  "gravewright-2026-10": "GEEbh7w29FAsH+XqMhGV+nlCZhroohrJEOwoNy5g48E="\n}\n')

    def setUp(self):
        self.enterContext(patch.object(runner, 'LANGUAGE', runner.RunnerLanguage()))
        self.opener = self.enterContext(patch.object(runner, 'build_opener')).return_value
        self.response = self.opener.open.return_value.__enter__.return_value

    def test_reviewed_immutable_trust_store_matches_pin_and_keeps_both_signing_keys(self):
        self.response.read.return_value = self.keys
        self.assertEqual(runner._download_default_keys(), self.keys)
        self.assertEqual(hashlib.sha256(self.keys).hexdigest(), runner.DEFAULT_MARKETPLACE_KEYS_SHA256)
        self.assertEqual(json.loads(self.keys), runner.DEFAULT_MARKETPLACE_PUBLIC_KEYS)
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://raw.githubusercontent.com/Gravewright/marketplace/'
                         '56aefb9db91666f7573bfdcdc2f6e9a6f2100527/trusted-keys.json')
        self.assertEqual(self.opener.open.call_args.kwargs['timeout'], 30)
        self.response.read.assert_called_once_with(1024 * 1024 + 1)
        self.assertEqual(set(json.loads(self.keys)), {'gravewright-2026', 'gravewright-2026-10'})

    def test_valid_json_with_a_replaced_public_key_still_fails_integrity(self):
        self.response.read.return_value = self.keys.replace(b'GEEbh7w', b'HEEbh7w')
        with self.assertRaisesRegex(RunnerError, 'failed its integrity check'):
            runner._download_default_keys()

    def test_oversized_download_is_rejected_before_json_validation(self):
        self.response.read.return_value = b' ' * (1024 * 1024 + 1)
        with self.assertRaisesRegex(RunnerError, 'failed its integrity check'):
            runner._download_default_keys()


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
