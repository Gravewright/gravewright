import json
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import zipfile
from unittest import skipUnless
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase
from gravewright.accounts.models import User
from scripts.update_supervisor import Supervisor, extract, read, write
from scripts.project_files import source_files, copy_files, replace_files


class ActiveReleaseStateTests(SimpleTestCase):
    def supervisor(self, root):
        with patch.dict(os.environ, {}, clear=True):
            return Supervisor(root / 'app', root / 'state', root / 'database.sqlite3',
                              root / 'media', '127.0.0.1', 3000)

    def test_missing_state_uses_current_installation_without_writing_a_pointer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            supervisor = self.supervisor(root)
            self.assertEqual(supervisor.active, root / 'app')
            self.assertEqual(supervisor.runtime_python, sys.executable)
            self.assertFalse((root / 'state/active.json').exists())

    def test_current_origin_and_managed_release_preserve_the_saved_interpreter_and_bytes(self):
        for relative in ('app', 'state/releases/release/source'):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                path = root / 'state/active.json'
                content = (json.dumps({'path': str(root / relative), 'python': 'saved-python'}, indent=2) + '\n').encode()
                path.parent.mkdir(parents=True)
                path.write_bytes(content)
                with patch('scripts.update_supervisor.instance_lock') as lock:
                    supervisor = self.supervisor(root)
                self.assertEqual(supervisor.active, root / relative)
                self.assertEqual(supervisor.runtime_python, 'saved-python')
                self.assertEqual(path.read_bytes(), content)
                self.assertEqual(list(path.parent.glob('active.json.backup-*')), [])
                lock.assert_not_called()

    def test_idle_pointer_from_another_or_moved_installation_is_backed_up_and_rebound(self):
        for exists in (False, True):
            with self.subTest(previous_exists=exists), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                previous = root / 'previous-installation'
                if exists:
                    previous.mkdir()
                path = root / 'state/active.json'
                content = (json.dumps({'path': str(previous), 'python': 'foreign-python'}, indent=2) + '\n').encode()
                path.parent.mkdir(parents=True)
                path.write_bytes(content)
                supervisor = self.supervisor(root)
                self.assertEqual(supervisor.active, root / 'app')
                self.assertEqual(supervisor.runtime_python, sys.executable)
                self.assertEqual(read(path), {'path': str(root / 'app'), 'python': sys.executable})
                backups = list(path.parent.glob('active.json.backup-*'))
                self.assertEqual(len(backups), 1)
                self.assertEqual(backups[0].read_bytes(), content)
                self.assertEqual(previous.exists(), exists)

    def test_foreign_pointer_with_any_pending_state_is_rejected_without_rewriting(self):
        for name in ('transaction.json', 'job.json', 'job.lock', 'maintenance'):
            with self.subTest(marker=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                path = root / 'state/active.json'
                write(path, {'path': str(root / 'other-app'), 'python': 'foreign-python'})
                before = path.read_bytes()
                marker = path.parent / name
                if name == 'job.lock':
                    marker.mkdir()
                else:
                    marker.write_bytes(b'pending state must survive')
                with self.assertRaisesRegex(ValueError, 'Invalid active release path with pending updater state'):
                    self.supervisor(root)
                self.assertEqual(path.read_bytes(), before)
                self.assertTrue(marker.exists())
                if marker.is_file():
                    self.assertEqual(marker.read_bytes(), b'pending state must survive')
                self.assertEqual(list(path.parent.glob('active.json.backup-*')), [])

    def test_pointer_is_reloaded_under_lock_before_rebinding(self):
        from contextlib import contextmanager
        for change in ('valid-pointer', 'pending-job'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                path = root / 'state/active.json'
                write(path, {'path': str(root / 'other-app'), 'python': 'foreign-python'})

                @contextmanager
                def locked(lock_path):
                    self.assertEqual(lock_path, root / 'state/supervisor.lock')
                    if change == 'valid-pointer':
                        write(path, {'path': str(root / 'app'), 'python': 'concurrent-python'})
                    else:
                        write(path.parent / 'job.json', {'pending': True})
                    yield

                with patch('scripts.update_supervisor.instance_lock', side_effect=locked):
                    if change == 'valid-pointer':
                        supervisor = self.supervisor(root)
                        self.assertEqual(supervisor.runtime_python, 'concurrent-python')
                        self.assertEqual(read(path)['python'], 'concurrent-python')
                    else:
                        before = path.read_bytes()
                        with self.assertRaisesRegex(ValueError, 'pending updater state'):
                            self.supervisor(root)
                        self.assertEqual(path.read_bytes(), before)
                self.assertEqual(list(path.parent.glob('active.json.backup-*')), [])

    def test_foreign_pointer_is_unchanged_when_another_supervisor_holds_the_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            path = root / 'state/active.json'
            write(path, {'path': str(root / 'other-app'), 'python': 'foreign-python'})
            before = path.read_bytes()
            with patch('scripts.update_supervisor.instance_lock', side_effect=OSError('already locked')):
                with self.assertRaisesRegex(OSError, 'already locked'):
                    self.supervisor(root)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(path.parent.glob('active.json.backup-*')), [])

    def test_resolver_still_rejects_paths_outside_the_origin_and_managed_releases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            supervisor = self.supervisor(root)
            with self.assertRaisesRegex(ValueError, '^Invalid active release path$'):
                supervisor.resolve_active(root / 'state/releases/../outside')


class ArchiveTests(SimpleTestCase):
    def test_relative_module_storage_stays_at_original_location_during_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for configured in ('data/media/modules', ''):
                with patch.dict(os.environ, {'GRAVEWRIGHT_MODULES_ROOT': configured}):
                    supervisor = Supervisor(root / 'app', root / 'state', root / 'db.sqlite3', root / 'media', '127.0.0.1', 3000)
                expected = root / 'app/data/media/modules' if configured else root / 'media/modules'
                self.assertEqual(supervisor.environment(root / 'candidate')['GRAVEWRIGHT_MODULES_ROOT'], str(expected.resolve()))

    def test_django_crash_restores_registry_and_previous_interpreter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / 'database.sqlite3'
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute('create table fixture(value text)')
            with patch.dict(os.environ, {'GRAVEWRIGHT_MODULES_ROOT': str(root / 'media/modules')}):
                supervisor = Supervisor(root / 'app', root / 'state', database, root / 'media', '127.0.0.1', 3000)
            registry = supervisor.modules / 'server-apps.json'
            write(registry, {'original': {}})
            supervisor.backup(supervisor.state / 'backups/test')
            write(registry, {'broken': {}})
            write(supervisor.state / 'transaction.json', {'previous': str(supervisor.origin),
                  'previous_python': 'original-python', 'backup': 'test', 'restore': True})
            supervisor.runtime_python = 'broken-python'
            supervisor.recover()
            self.assertEqual(read(registry), {'original': {}})
            self.assertEqual(supervisor.runtime_python, 'original-python')
            self.assertEqual(read(supervisor.state / 'active.json')['python'], 'original-python')

    def test_staged_runner_uses_final_project_even_before_the_swap_completes(self):
        import shutil
        import sys
        from scripts.windows.create_runner import create_runner

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage, origin, data = root / 'stage', root / 'original', root / 'data'
            (stage / 'scripts/windows').mkdir(parents=True)
            source = Path(__file__).resolve().parents[2] / 'scripts/windows'
            for name in ('runner.bat', 'launch_runner.py'):
                shutil.copy2(source / name, stage / 'scripts/windows' / name)
            create_runner(stage, sys.executable, data, runtime_project=origin)
            content = next((data / '.runner-launchers').glob('*.bat')).read_text(encoding='utf-8')
            self.assertIn(f'pushd "{origin.resolve()}"', content)
            self.assertIn(f'--project "{origin.resolve()}"', content)
            self.assertNotIn(str(stage), content)

    def test_external_startup_recovery_repairs_project_before_importing_it(self):
        from scripts.windows.launch_runner import recover_source
        from scripts.gravewright_runner import instance_lock

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project, data = root / 'app', root / 'data'
            project.mkdir(); data.mkdir()
            backup = data / 'updates/backups/test/project'
            (backup / 'scripts').mkdir(parents=True)
            (backup / 'scripts/gravewright_runner.py').write_text('old runnable code')
            (project / 'new-file').write_text('partially installed')
            (project / '.env').write_text('private')
            transaction = data / 'updates/transaction.json'
            write(transaction, {'backup': 'test', 'previous_python': 'previous-python',
                                'project_files': ['scripts/gravewright_runner.py'],
                                'incoming_files': ['scripts/gravewright_runner.py', 'new-file']})
            with instance_lock(data), self.assertRaises(OSError):
                recover_source(project, data)
            self.assertEqual(recover_source(project, data), 'previous-python')
            self.assertEqual((project / 'scripts/gravewright_runner.py').read_text(), 'old runnable code')
            self.assertFalse((project / 'new-file').exists())
            self.assertEqual((project / '.env').read_text(), 'private')
            self.assertTrue(transaction.exists())  # Data recovery still has to commit.

    def test_external_startup_recovery_accepts_aliases_without_touching_private_data(self):
        from scripts.windows.launch_runner import recover_source

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            project, data = root / 'app', root / 'data'
            project.mkdir(); data.mkdir()
            backup = data / 'updates/backups/test/project'
            backup.mkdir(parents=True)
            (backup / 'module.py').write_text('previous source')
            (project / 'module.py').write_text('interrupted source')
            (project / 'incoming.py').write_text('partial addition')
            (project / '.env').write_text('private configuration')
            (project / 'data').mkdir()
            (project / 'data/campaign').write_text('private campaign')
            transaction = data / 'updates/transaction.json'
            write(transaction, {'backup': 'test', 'previous_python': 'previous-python',
                                'project_files': ['module.py'],
                                'incoming_files': ['module.py', 'incoming.py']})
            # Deterministic aliases exercise the same canonical comparison as
            # Windows short paths and macOS /var -> /private/var, without
            # requiring privileges to create directory symlinks on Windows.
            self.assertEqual(recover_source(project / '..' / 'app', data / '..' / 'data'), 'previous-python')
            self.assertEqual((project / 'module.py').read_text(), 'previous source')
            self.assertFalse((project / 'incoming.py').exists())
            self.assertEqual((project / '.env').read_text(), 'private configuration')
            self.assertEqual((project / 'data/campaign').read_text(), 'private campaign')
            self.assertTrue(transaction.exists())

    def test_external_startup_recovery_rejects_escapes_through_aliases(self):
        from scripts.windows.launch_runner import recover_source

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            project, data = root / 'app', root / 'data'
            project.mkdir(); data.mkdir()
            backup = data / 'updates/backups/test/project'
            backup.mkdir(parents=True)
            (backup / 'module.py').write_text('previous source')
            (project / 'module.py').write_text('interrupted source')
            outside = root / 'outside.py'
            outside.write_text('outside must survive')
            for field, value in [('incoming_files', ['module.py', '../outside.py']),
                                 ('project_files', ['../outside.py']),
                                 ('backup', '../../../../outside')]:
                with self.subTest(field=field):
                    journal = {'backup': 'test', 'previous_python': 'previous-python',
                               'project_files': ['module.py'], 'incoming_files': ['module.py']}
                    journal[field] = value
                    write(data / 'updates/transaction.json', journal)
                    with self.assertRaisesRegex(ValueError, 'Invalid recovery'):
                        recover_source(project / '..' / 'app', data / '..' / 'data')
                    self.assertEqual(outside.read_text(), 'outside must survive')
                    self.assertEqual((project / 'module.py').read_text(), 'interrupted source')

    def test_project_replacement_and_recovery_preserve_private_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            origin, release = root / 'app', root / 'release'
            origin.mkdir(); release.mkdir()
            for folder in (origin, release):
                (folder / 'Install Windows.bat').write_text('old' if folder == origin else 'new')
            (origin / 'removed.py').write_text('old module')
            (origin / '__pycache__').mkdir()
            (origin / '__pycache__/removed.pyc').write_bytes(b'stale')
            (origin / '.env').write_text('private secret')
            (origin / 'data').mkdir(); (origin / 'data/private').write_text('campaign')
            (release / 'added.py').write_text('new module')
            names, previous = source_files(release), source_files(origin)
            self.assertNotIn('.env', previous)
            self.assertNotIn('data/private', previous)
            copy_files(origin, root / 'backup', previous)
            replace_files(release, origin, names, previous)
            self.assertEqual((origin / 'Install Windows.bat').read_text(), 'new')
            self.assertFalse((origin / 'removed.py').exists())
            self.assertFalse((origin / '__pycache__').exists())
            replace_files(root / 'backup', origin, previous, names)
            self.assertEqual((origin / 'Install Windows.bat').read_text(), 'old')
            self.assertTrue((origin / 'removed.py').exists())
            self.assertFalse((origin / 'added.py').exists())
            self.assertEqual((origin / '.env').read_text(), 'private secret')
            self.assertEqual((origin / 'data/private').read_text(), 'campaign')

    def test_traversal_and_private_paths_rejected(self):
        for member in ['../escape', '/escape', 'root/.env', 'root/.git/config', 'root/data/db', 'C:/escape']:
            with self.subTest(member=member), tempfile.TemporaryDirectory() as directory:
                archive = Path(directory) / 'test.zip'
                with zipfile.ZipFile(archive, 'w') as z:
                    z.writestr(member, 'bad')
                with self.assertRaises(ValueError):
                    extract(archive, Path(directory) / 'out')

    def test_backup_restore_and_crash_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / 'db.sqlite3'
            with closing(sqlite3.connect(db)) as c, c:
                c.execute('create table fixture(value text)')
                c.execute("insert into fixture values('original')")
            media = root / 'media';media.mkdir();(media / 'file').write_bytes(b'original')
            supervisor = Supervisor(root / 'app', root / 'state', db, media, '127.0.0.1', 3000)
            supervisor.origin.mkdir()
            (supervisor.origin / 'Install Windows.bat').write_text('original installer')
            previous_files = source_files(supervisor.origin)
            backup = supervisor.state / 'backups/test'
            supervisor.backup(backup)
            copy_files(supervisor.origin, backup / 'project', previous_files)
            (supervisor.origin / 'Install Windows.bat').write_text('partially updated installer')
            (supervisor.origin / 'new-file.txt').write_text('partial update')
            with closing(sqlite3.connect(db)) as c, c:
                c.execute("update fixture set value='changed'")
            (media / 'file').write_bytes(b'changed');(media / 'new-file').touch()
            write(supervisor.state / 'transaction.json', {
                'previous': str(supervisor.origin), 'backup': 'test', 'restore': True,
                'previous_python': supervisor.runtime_python, 'project_files': previous_files,
                'incoming_files': ['Install Windows.bat', 'new-file.txt'],
            })
            supervisor.recover()
            with closing(sqlite3.connect(db)) as c, c:
                self.assertEqual(c.execute('select value from fixture').fetchone(), ('original',))
            self.assertEqual((media / 'file').read_bytes(), b'original')
            self.assertFalse((media / 'new-file').exists())
            self.assertEqual(read(supervisor.state / 'progress.json')['stage'], 'rolled_back')
            self.assertFalse((supervisor.state / 'transaction.json').exists())
            self.assertEqual((supervisor.origin / 'Install Windows.bat').read_text(), 'original installer')
            self.assertFalse((supervisor.origin / 'new-file.txt').exists())


class StateWriteTests(SimpleTestCase):
    @skipUnless(os.name == 'nt', 'Requires native Windows file-sharing semantics')
    def test_reader_releases_state_without_losing_atomic_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'progress.json'
            previous = {'stage': 'dependencies'}
            incoming = {'stage': 'backup', 'detail': 'Atualização pronta'}
            write(target, previous)
            locked, collision = threading.Event(), threading.Event()
            failures, blocked = [], []
            original_replace = Path.replace

            def reader():
                try:
                    with target.open('rb') as handle:
                        locked.set()
                        self.assertTrue(collision.wait(2), 'No replacement was attempted with the reader open')
                        self.assertEqual(json.load(handle), previous)
                        self.assertEqual(read(target), previous)
                        time.sleep(.075)
                except BaseException as error:
                    failures.append(error)

            def replace(source, destination):
                try:
                    return original_replace(source, destination)
                except PermissionError as error:
                    blocked.append(error.winerror)
                    collision.set()
                    raise

            thread = threading.Thread(target=reader)
            thread.start()
            try:
                self.assertTrue(locked.wait(2))
                with patch.object(Path, 'replace', replace):
                    write(target, incoming)
            finally:
                thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(failures, [])
            self.assertTrue(blocked, 'The test did not exercise a real Windows sharing conflict')
            self.assertTrue(set(blocked) <= {5, 32})
            self.assertEqual(read(target), incoming)
            self.assertEqual(list(target.parent.glob('progress.json.tmp-*')), [])

    def test_permanent_windows_denial_stops_at_deadline_and_cleans_owned_temporary(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'progress.json'
            write(target, {'stage': 'dependencies'})
            original = target.read_bytes()
            error = PermissionError('Permanent access denial')
            error.winerror = 5
            with (patch('scripts.update_supervisor.os', SimpleNamespace(name='nt')),
                  patch('scripts.update_supervisor.time.monotonic', side_effect=[100, 100.5, 101, 101.5, 102]),
                  patch('scripts.update_supervisor.time.sleep') as sleep,
                  patch.object(Path, 'replace', side_effect=error) as replace):
                with self.assertRaisesRegex(PermissionError, 'Permanent access denial'):
                    write(target, {'stage': 'backup'})
            self.assertEqual(replace.call_count, 4)
            self.assertEqual(sleep.call_count, 3)
            self.assertTrue(all(call.args[0] <= .025 for call in sleep.call_args_list))
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(list(target.parent.glob('progress.json.tmp-*')), [])

    def test_non_sharing_errors_fail_immediately_and_preserve_previous_state(self):
        # Windows disk-full errors and non-Windows permission errors retain
        # their immediate failure behavior.
        for platform, code in (('nt', 112), ('posix', 5)):
            with self.subTest(platform=platform, code=code), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / 'progress.json'
                write(target, {'stage': 'dependencies'})
                original = target.read_bytes()
                error = OSError('Not a file-sharing conflict')
                error.winerror = code
                with (patch('scripts.update_supervisor.os', SimpleNamespace(name=platform)),
                      patch('scripts.update_supervisor.time.sleep') as sleep,
                      patch.object(Path, 'replace', side_effect=error) as replace):
                    with self.assertRaisesRegex(OSError, 'Not a file-sharing conflict'):
                        write(target, {'stage': 'backup'})
                replace.assert_called_once()
                sleep.assert_not_called()
                self.assertEqual(target.read_bytes(), original)
                self.assertEqual(list(target.parent.glob('progress.json.tmp-*')), [])


class FailureDiagnosticsTests(SimpleTestCase):
    def supervisor(self, root):
        origin = root / 'application'
        origin.mkdir()
        (origin / 'pyproject.toml').write_text('[project]\nversion = "0.2.1"\n', encoding='utf-8')
        database = root / 'database.sqlite3'
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute('create table fixture(value text)')
        # Every path and process environment belongs to this isolated fixture.
        with patch.dict(os.environ, {}, clear=True):
            return Supervisor(origin, root / 'state', database, root / 'media', '127.0.0.1', 3000)

    def fail_migration(self, *args, **kwargs):
        if 'prepare_django_packages' in args:
            write(args[-1], {})
        if 'migrate' in args:
            raise ValueError('Falha original: migração inválida')

    def assert_original_failure(self, supervisor, prefix):
        log = (supervisor.state / 'update.log').read_text(encoding='utf-8')
        self.assertIn(f'{prefix}: ValueError: Falha original: migração inválida', log)
        self.assertIn('Traceback (most recent call last):', log)
        self.assertIn('fail_migration', log)

    def test_source_failure_is_logged_even_when_backup_recovery_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            supervisor = self.supervisor(root)
            candidate = root / 'candidate'
            candidate.mkdir()
            (candidate / 'pyproject.toml').write_text('[project]\nversion = "0.2.2"\n', encoding='utf-8')
            with (patch('scripts.update_supervisor.download'),
                  patch('scripts.update_supervisor.extract', return_value=candidate),
                  patch('scripts.update_supervisor.shutil.which', return_value='uv'),
                  patch.object(supervisor, 'command', side_effect=self.fail_migration),
                  patch.object(supervisor, 'stop'),
                  patch.object(supervisor, 'recover', side_effect=OSError('Backup recovery unavailable'))):
                with self.assertRaisesRegex(OSError, 'Backup recovery unavailable'):
                    supervisor.apply({'version': '0.2.2', 'artifact': {'size': 0}})
            self.assert_original_failure(supervisor, 'Update failed')
            # Leave the journal for a later recovery attempt, as before.
            self.assertTrue((supervisor.state / 'transaction.json').exists())
            self.assertTrue((supervisor.state / 'maintenance').exists())

    def test_django_failure_is_logged_even_when_previous_server_cannot_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            supervisor = self.supervisor(Path(directory))
            supervisor.env['GW_UV'] = 'uv'
            with (patch.object(supervisor, 'command', side_effect=self.fail_migration),
                  patch.object(supervisor, 'stop'),
                  patch.object(supervisor, 'start'),
                  patch.object(supervisor, 'ready', side_effect=RuntimeError('Previous server unavailable'))):
                with self.assertRaisesRegex(RuntimeError, 'Previous server unavailable'):
                    supervisor.apply_django({'id': 'test.fixture', 'version': '1.0.0', 'enabled': True})
            self.assert_original_failure(supervisor, 'Django activation failed')
            self.assertEqual(read(supervisor.state / 'progress.json')['stage'], 'rolled_back')

    def test_unavailable_diagnostic_storage_does_not_prevent_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            supervisor = self.supervisor(Path(directory))
            supervisor.env['GW_UV'] = 'uv'
            # A directory at the log path causes a real OSError on all platforms.
            (supervisor.state / 'update.log').mkdir()
            with (patch.object(supervisor, 'command', side_effect=self.fail_migration),
                  patch.object(supervisor, 'stop'),
                  patch.object(supervisor, 'start'),
                  patch.object(supervisor, 'ready')):
                supervisor.apply_django({'id': 'test.fixture', 'version': '1.0.0', 'enabled': True})
            self.assertEqual(read(supervisor.state / 'progress.json')['stage'], 'rolled_back')
            self.assertFalse((supervisor.state / 'transaction.json').exists())
            self.assertFalse((supervisor.state / 'maintenance').exists())


class RequestTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@update.test', name='Owner', password='long-test-password', role='owner')
        self.player = User.objects.create_user(email='player@update.test', name='Player', password='long-test-password')

    def test_owner_only_and_managed_mode_required(self):
        self.client.force_login(self.player)
        self.assertEqual(self.client.post('/api/admin/updates/apply', {'version':'0.1.0-alpha.1'}, content_type='application/json').status_code, 403)
        self.client.force_login(self.owner)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.client.post('/api/admin/updates/apply', {'version':'0.1.0-alpha.1'}, content_type='application/json').status_code, 409)

    def test_queue_pins_checked_release_and_rejects_parallel_requests(self):
        from gravewright.administration.automatic_updates import request_update
        from gravewright.accounts.services import AuthError
        with tempfile.TemporaryDirectory() as directory, self.settings(BASE_DIR=Path(directory)), patch.dict(os.environ, {'GRAVEWRIGHT_MANAGED_STATE':directory}), patch('gravewright.administration.automatic_updates.CoreUpdateService') as service:
            service.return_value.check.return_value = {'status':'available','availableVersion':'0.1.0-alpha.1','artifact':{'sha256':'a'*64}}
            with self.assertRaises(AuthError):
                request_update('0.1.0-alpha.2')
            self.assertFalse((Path(directory) / 'job.lock').exists())
            self.assertTrue(request_update('0.1.0-alpha.1', keep_old=False)['busy'])
            self.assertEqual(read(Path(directory) / 'job.json')['version'], '0.1.0-alpha.1')
            self.assertIs(read(Path(directory) / 'job.json')['keep_old'], False)
            with self.assertRaises(AuthError):
                request_update('0.1.0-alpha.1')

    def test_backup_choice_is_a_boolean_and_is_forwarded(self):
        self.client.force_login(self.owner)
        with patch('gravewright.administration.automatic_updates.request_update', return_value={'busy': True}) as apply:
            for value in ('false', 0, None, []):
                result = self.client.post('/api/admin/updates/apply', {'version': '0.2.0', 'keep_old': value}, content_type='application/json')
                self.assertEqual(result.status_code, 400)
            apply.assert_not_called()
            for value in (False, True):
                result = self.client.post('/api/admin/updates/apply', {'version': '0.2.0', 'keep_old': value}, content_type='application/json')
                self.assertEqual(result.status_code, 202)
                apply.assert_called_with('0.2.0', keep_old=value)

class MaintenanceTests(SimpleTestCase):
    async def test_blocks_requests_during_swap_and_keeps_health_probe_private(self):
        from asgiref.testing import ApplicationCommunicator
        from config.managed_asgi import ManagedApplication
        from unittest.mock import AsyncMock
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'GRAVEWRIGHT_MANAGED_STATE':directory,'GRAVEWRIGHT_MANAGED_TOKEN':'private-test-token'}):
            (Path(directory) / 'maintenance').touch()
            app = ManagedApplication()
            for scope, expected in [({'type':'http','path':'/api/auth/account','headers':[]},503),
                                    ({'type':'http','path':'/__gravewright_update_health','headers':[]},403),
                                    ({'type':'websocket','path':'/ws/table','headers':[]},1012)]:
                c=ApplicationCommunicator(app,scope)
                output=await c.receive_output()
                self.assertEqual(output.get('status',output.get('code')),expected)
                await c.wait()
            with patch('config.managed_asgi.database_ready',new=AsyncMock(return_value=True)):
                c=ApplicationCommunicator(app,{'type':'http','path':'/__gravewright_update_health','headers':[(b'x-gravewright-update',b'private-test-token')]})
                self.assertEqual((await c.receive_output())['status'],200)
                await c.wait()
