"""Offline launcher, update and interrupted-recovery checks on every OS.

Run ``python -m unittest discover -s tests/posix -p test_runner.py -v``.
Native shell execution tests additionally run on Linux and macOS.
"""

import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch
import venv
import zipfile


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts import gravewright_runner as runner
from scripts.posix.create_runner import create_runner, desktop_argument, shell_value
from scripts.project_files import copy_files, source_files
from scripts.update_supervisor import Supervisor, extract, read, runner_layout, write
from scripts.windows.launch_runner import recover_source


def fixture(project):
    for name in ('scripts/posix/runner.sh', 'scripts/posix/create_runner.py',
                 'scripts/windows/launch_runner.py'):
        destination = project / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    for name in ('Install Linux.sh', 'Install macOS.command', 'scripts/posix/install.sh',
                 'manage.py', 'uv.lock', 'config/managed_asgi.py', 'scripts/managed_server.py'):
        destination = project / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text('# test fixture\n', encoding='utf-8')
    (project / 'pyproject.toml').write_text('[project]\nversion = "2.0.0"\n', encoding='utf-8')


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.project = self.work / "Gravewright ç ' $ % ` (test)"
        fixture(self.project)
        self.data = self.work / "User data ã $ ' %"

    def test_shell_values_round_trip_without_interpolation(self):
        for value in ['plain', 'space ã', 'quote\'"$`\\%; (test)', '@@PROJECT@@']:
            with self.subTest(value=value):
                self.assertEqual(shlex.split(shell_value(value)), [value])
        for value in ['bad\npath', 'bad\rpath', 'bad\0path']:
            with self.assertRaises(ValueError):
                shell_value(value)

    def test_native_names_and_hashes_are_stable_without_private_paths_in_templates(self):
        for platform, name in [('linux', 'Gravewright Runner.sh'),
                               ('darwin', 'Gravewright Runner.command')]:
            with self.subTest(platform=platform):
                data = self.data / platform
                destination = create_runner(self.project, sys.executable, data, platform=platform)
                before = destination.read_bytes()
                self.assertEqual(destination.name, name)
                self.assertNotIn(b'\r', before)
                create_runner(self.project, sys.executable, data, platform=platform)
                self.assertEqual(destination.read_bytes(), before)
                for item in (data / '.runner-launchers').iterdir():
                    self.assertEqual(item.stem, hashlib.sha256(item.read_bytes()).hexdigest())
                if os.name != 'nt':
                    self.assertTrue(os.access(destination, os.X_OK))

    def test_staged_launchers_use_final_project_and_keep_environment_python(self):
        final = self.work / 'Installed @@DATA@@ project ç'
        python = self.work / 'private venv/bin/python'
        destination = create_runner(self.project, python, self.data, runtime_project=final,
                                    uv=self.work / 'uv $ tool', port=4321, no_browser=True,
                                    platform='linux')
        content = next((self.data / '.runner-launchers').glob('*.sh')).read_text(encoding='utf-8')
        self.assertIn('cd ' + shell_value(final.resolve()), content)
        self.assertIn('--project ' + shell_value(final.resolve()), content)
        self.assertIn('GW_PYTHON=' + shell_value(python), content)
        self.assertIn('--port 4321 --no-browser "$@"', content)
        self.assertNotIn(str(self.project), content)
        desktop = (self.project / 'Gravewright Runner.desktop').read_text(encoding='utf-8')
        self.assertIn('Exec=/bin/sh ' + desktop_argument(final / destination.name), desktop)
        self.assertIn('Terminal=true\n', desktop)
        self.assertNotIn('sh -c', desktop)

    def test_modified_saved_launcher_is_rejected(self):
        create_runner(self.project, sys.executable, self.data, platform='linux')
        immutable = next((self.data / '.runner-launchers').glob('*.sh'))
        immutable.write_text('tampered', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'has changed'):
            create_runner(self.project, sys.executable, self.data, platform='linux')

    def test_mac_launcher_captures_private_build_environment_for_staged_updates(self):
        values = {'GRAVEWRIGHT_BUILD_TOOLS_PATH': str(self.work / "Rust bins ç '$"),
                  'OPENSSL_DIR': str(self.work / "OpenSSL static ã '$"),
                  'OPENSSL_STATIC': '1', 'CARGO_HOME': str(self.work / 'Private cargo cache')}
        with patch.dict(os.environ, {**values, 'AUTOBAHN_USE_NVX': '1'}):
            create_runner(self.project, sys.executable, self.data, platform='darwin',
                          runtime_project=self.work / 'final app')
        content = next((self.data / '.runner-launchers').glob('*.command')).read_text(encoding='utf-8')
        for name, value in values.items():
            self.assertIn(name + '=' + shell_value(value) + '\nexport ' + name, content)
        self.assertIn('AUTOBAHN_USE_NVX=0\nexport AUTOBAHN_USE_NVX', content)
        self.assertIn('PATH="$GRAVEWRIGHT_BUILD_TOOLS_PATH:', content)

    def test_recovery_restores_generated_launcher_and_keeps_local_configuration(self):
        launcher = create_runner(self.project, sys.executable, self.data, platform='linux')
        original = launcher.read_bytes()
        backup = self.data / 'updates/backups/interrupted/project'
        copy_files(self.project, backup, source_files(self.project))
        previous = source_files(self.project)
        launcher.write_text('# partially updated entrypoint', encoding='utf-8')
        (self.project / '.env').write_text('private configuration')
        (self.project / 'new-file').write_text('incomplete update')
        write(self.data / 'updates/transaction.json', {
            'backup': 'interrupted', 'previous_python': sys.executable,
            'project_files': previous, 'incoming_files': previous + ['new-file'],
        })
        self.assertEqual(recover_source(self.project, self.data), sys.executable)
        self.assertEqual(launcher.read_bytes(), original)
        self.assertFalse((self.project / 'new-file').exists())
        self.assertEqual((self.project / '.env').read_text(), 'private configuration')
        self.assertTrue((self.data / 'updates/transaction.json').exists())
        if os.name != 'nt':
            self.assertTrue(os.access(launcher, os.X_OK))


class PlatformTests(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'Private build tools are a POSIX installer contract')
    def test_private_build_path_survives_project_environment_loading_without_becoming_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            values = {'DEFAULT_LOCALE': 'en', 'GRAVEWRIGHT_PORT': '3000', 'DJANGO_SECRET_KEY': 'x' * 64}
            (work / '.env.example').write_text('DEFAULT_LOCALE=en\nGRAVEWRIGHT_PORT=3000\n')
            (work / '.env').write_text('DJANGO_SECRET_KEY=' + 'x' * 64 + '\n')
            dotenv = ModuleType('dotenv')
            dotenv.dotenv_values = lambda *args, **kwargs: values.copy()
            build = str(work / 'Private Rust bins ç')
            with patch.object(runner, 'ROOT', work), patch.dict(os.environ), \
                    patch.object(sys, 'path', sys.path.copy()), patch.dict(sys.modules, {'dotenv': dotenv}):
                os.environ['GRAVEWRIGHT_BUILD_TOOLS_PATH'] = build
                runner.prepare_environment(work / 'runner state')
                self.assertEqual(os.environ['GRAVEWRIGHT_BUILD_TOOLS_PATH'], build)
                self.assertNotIn('GRAVEWRIGHT_BUILD_TOOLS_PATH', (work / '.env').read_text())

    def test_terminal_close_uses_the_same_graceful_stop_as_termination(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            handlers = {}
            def remember(number, callback):
                handlers[number] = callback
            def terminal_closed():
                number = getattr(signal, 'SIGHUP', signal.SIGTERM)
                self.assertIs(handlers[number], handlers[signal.SIGTERM])
                handlers[number](number, None)
            env = {'GRAVEWRIGHT_DATABASE': str(work / 'db.sqlite3'),
                   'GRAVEWRIGHT_MEDIA_ROOT': str(work / 'media')}
            with patch.dict(os.environ, env), \
                    patch.object(runner, 'LANGUAGE', runner.RunnerLanguage()), \
                    patch.object(runner.RunnerLanguage, 'from_project'), \
                    patch.object(runner, 'prepare_environment', return_value=3000), \
                    patch.object(runner, 'prepare_application'), patch.object(runner, 'check_port'), \
                    patch.object(runner, 'configure_logging', return_value=work / 'runner.log'), \
                    patch('scripts.update_supervisor.Supervisor') as supervisor, \
                    patch('signal.signal', side_effect=remember), patch('builtins.print'):
                supervisor.return_value.run.side_effect = terminal_closed
                self.assertEqual(runner.main(['--data-dir', str(work), '--no-browser']), 0)
                self.assertTrue(supervisor.return_value.run.called)

    def test_data_defaults_use_native_home_and_ignore_other_platform_variables(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(Path, 'home', return_value=Path(temp)), \
                patch.dict(os.environ, {'LOCALAPPDATA': str(Path(temp) / 'windows'),
                                        'XDG_DATA_HOME': str(Path(temp) / 'xdg')}, clear=True):
            for platform, expected in [('darwin', Path(temp) / 'Library/Application Support/Gravewright/data'),
                                       ('linux', Path(temp) / 'xdg/Gravewright/data'),
                                       ('win32', Path(temp) / 'windows/Gravewright/data')]:
                with self.subTest(platform=platform), patch.object(sys, 'platform', platform):
                    self.assertEqual(runner.data_directory(), expected.resolve())

    def test_update_layout_is_native(self):
        for platform, installer, outputs in [
                ('linux', 'Install Linux.sh', ('Gravewright Runner.sh', 'Gravewright Runner.desktop')),
                ('darwin', 'Install macOS.command', ('Gravewright Runner.command',)),
                ('win32', 'Install Windows.bat', ('Gravewright Runner.bat',))]:
            with self.subTest(platform=platform), patch.object(sys, 'platform', platform):
                generator, required, generated = runner_layout()
                self.assertIn(installer, required)
                self.assertIn(generator, required)
                self.assertEqual(generated, outputs)

    @unittest.skipIf(os.name == 'nt', 'POSIX executable permission bits')
    def test_archive_extraction_restores_only_safe_launcher_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / 'release.zip'
            names = ['pyproject.toml', 'manage.py', 'uv.lock', 'config/managed_asgi.py',
                     'scripts/managed_server.py', 'Install Linux.sh', 'Install macOS.command']
            with zipfile.ZipFile(archive, 'w') as stream:
                for name in names:
                    item = zipfile.ZipInfo('release/' + name)
                    item.external_attr = (stat.S_IFREG | 0o6755) << 16
                    stream.writestr(item, '# harmless fixture\n')
            project = extract(archive, root / 'out')
            for name in names:
                mode = stat.S_IMODE((project / name).stat().st_mode)
                self.assertEqual(mode & 0o6000, 0)
                self.assertEqual(mode & 0o111, 0o111 if name.endswith(('.sh', '.command')) else 0)


class UpdateTests(unittest.TestCase):
    def test_update_refreshes_native_outputs_and_failed_restart_restores_them(self):
        for platform, fail in [('linux', False), ('darwin', False), ('linux', True), ('darwin', True)]:
            with self.subTest(platform=platform, fail=fail), tempfile.TemporaryDirectory() as temp:
                work = Path(temp).resolve()
                project, stage, data = work / 'app ç', work / 'new source', work / 'user data'
                fixture(project); fixture(stage)
                launcher = create_runner(project, sys.executable, data, platform=platform)
                original = launcher.read_bytes()
                (project / '.env').write_text('private', encoding='utf-8')
                with (stage / 'scripts/posix/runner.sh').open('a', encoding='utf-8') as handle:
                    handle.write('\n# updated release marker\n')
                database = work / 'db.sqlite3'
                with closing(sqlite3.connect(database)) as db, db:
                    db.execute('CREATE TABLE fixture(value TEXT)')
                env = {'DJANGO_SETTINGS_MODULE': 'config.runner', 'GW_UV': 'test-uv',
                       'GRAVEWRIGHT_RUNNER_DATA': str(data),
                       'GRAVEWRIGHT_BUILD_TOOLS_PATH': str(work / 'private Rust/bin'),
                       'OPENSSL_DIR': str(work / 'private OpenSSL'), 'OPENSSL_STATIC': '1',
                       'CARGO_HOME': str(work / 'cargo cache')}
                with patch.dict(os.environ, env, clear=True), patch.object(sys, 'platform', platform):
                    supervisor = Supervisor(project, data / 'updates', database, work / 'media', '127.0.0.1', 3000)
                    calls = []
                    def command(candidate, *args, **kwargs):
                        calls.append(args)
                        if len(args) > 1 and args[1] == 'scripts/posix/create_runner.py':
                            create_runner(candidate, args[0], data, uv='test-uv',
                                          runtime_project=project, platform=platform)
                    restarts = []
                    def ready(*_):
                        restarts.append(True)
                        if fail and len(restarts) == 1:
                            raise RuntimeError('intentional restart failure')
                    with patch('scripts.update_supervisor.download'), \
                            patch('scripts.update_supervisor.extract', return_value=stage), \
                            patch.object(supervisor, 'command', side_effect=command), \
                            patch.object(supervisor, 'start'), patch.object(supervisor, 'stop'), \
                            patch.object(supervisor, 'ready', side_effect=ready):
                        supervisor.apply({'version': '2.0.0', 'artifact': {'size': 1}, 'keep_old': False})
                self.assertTrue(any(len(call) > 1 and call[1] == 'scripts/posix/create_runner.py' for call in calls))
                self.assertEqual((project / '.env').read_text(), 'private')
                self.assertEqual(read(data / 'updates/progress.json')['stage'], 'rolled_back' if fail else 'complete')
                if fail:
                    self.assertEqual(launcher.read_bytes(), original)
                    self.assertEqual(supervisor.runtime_python, sys.executable)
                else:
                    self.assertNotEqual(launcher.read_bytes(), original)
                    saved = [p for p in (data / '.runner-launchers').glob('*')
                             if p.suffix in {'.sh', '.command'} and b'updated release marker' in p.read_bytes()]
                    self.assertEqual(len(saved), 1)
                    self.assertIn('--project ' + shell_value(project), saved[0].read_text(encoding='utf-8'))
                    for name in ('GRAVEWRIGHT_BUILD_TOOLS_PATH', 'OPENSSL_DIR', 'OPENSSL_STATIC', 'CARGO_HOME'):
                        self.assertIn(name + '=' + shell_value(env[name]), saved[0].read_text(encoding='utf-8'))
                    if platform == 'linux':
                        self.assertTrue((project / 'Gravewright Runner.desktop').is_file())
                    if os.name != 'nt':
                        self.assertTrue(os.access(launcher, os.X_OK))


@unittest.skipIf(os.name == 'nt', 'Native /bin/sh execution requires Linux or macOS')
class NativeShellTests(unittest.TestCase):
    def test_special_paths_arguments_venv_identity_and_immutable_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp).resolve()
            project = work / 'World "ç" \' $ ` %; (test)'
            fixture(project)
            data = work / 'State $ % \' " ã'
            report = work / 'observed.json'
            sentinel = work / 'INJECTION-MUST-NOT-EXIST'
            # A bare symlink is not a venv: macOS framework Python legitimately
            # resolves it to the base executable. Exercise the actual prepared
            # environment contract, including its pyvenv.cfg and sys.prefix.
            environment = work / 'venv $ "'
            venv.EnvBuilder(with_pip=False, symlinks=True).create(environment)
            python = environment / 'bin/python'
            fake = (
                'import json, os, sys\nfrom pathlib import Path\n'
                f'Path({str(report)!r}).write_text(json.dumps({{"argv": sys.argv[1:], "cwd": os.getcwd(), '
                '"python": sys.executable, "prefix": sys.prefix, "uv": os.environ.get("GW_UV"), '
                '"build_path": os.environ.get("GRAVEWRIGHT_BUILD_TOOLS_PATH"), '
                '"openssl": os.environ.get("OPENSSL_DIR"), "static": os.environ.get("OPENSSL_STATIC"), '
                '"cargo": os.environ.get("CARGO_HOME"), "path": os.environ.get("PATH"), '
                '"pythonpath": os.environ.get("PYTHONPATH"), "venv": os.environ.get("VIRTUAL_ENV")}))\n'
                'Path("replacement").write_text("#!/bin/sh\\necho REPLACEMENT_EXECUTED\\nexit 99\\n")\n'
                'Path("replacement").replace("Gravewright Runner.sh")\n'
                'raise SystemExit(7)\n'
            )
            (project / 'scripts/gravewright_runner.py').write_text(fake, encoding='utf-8')
            uv = work / 'uv $ ` " % \' binary'
            build_env = {'GRAVEWRIGHT_BUILD_TOOLS_PATH': str(work / 'Rust $ " binaries'),
                         'OPENSSL_DIR': str(work / 'OpenSSL $ " static'), 'OPENSSL_STATIC': '1',
                         'CARGO_HOME': str(work / 'Cargo $ " cache')}
            with patch.dict(os.environ, build_env):
                launcher = create_runner(project, python, data, uv=uv, platform='linux')
            argument = 'literal $(touch ' + str(sentinel) + ') $ ` % \' " ã'
            env = {**os.environ, **{name: 'inherited poison' for name in build_env},
                   'PYTHONPATH': str(work / 'poison'), 'VIRTUAL_ENV': 'poison'}
            result = subprocess.run(['/bin/sh', str(launcher), '--check', '--no-browser', '--port', '3210', argument],
                                    cwd=work, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
            observed = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(observed['argv'], ['--data-dir', str(data), '--check', '--no-browser', '--port', '3210', argument])
            self.assertEqual(observed['cwd'], str(project))
            self.assertEqual(observed['python'], str(python))
            self.assertEqual(observed['prefix'], str(environment))
            self.assertEqual(observed['uv'], str(uv))
            for field, name in [('build_path', 'GRAVEWRIGHT_BUILD_TOOLS_PATH'), ('openssl', 'OPENSSL_DIR'),
                                ('static', 'OPENSSL_STATIC'), ('cargo', 'CARGO_HOME')]:
                self.assertEqual(observed[field], build_env[name])
            self.assertEqual(observed['path'], build_env['GRAVEWRIGHT_BUILD_TOOLS_PATH'] + os.pathsep + env['PATH'])
            self.assertIsNone(observed['pythonpath'])
            self.assertIsNone(observed['venv'])
            self.assertNotIn('REPLACEMENT_EXECUTED', result.stdout)
            self.assertFalse(sentinel.exists())


if __name__ == '__main__':
    unittest.main()
