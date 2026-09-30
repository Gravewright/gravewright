import json
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import zipfile
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase
from gravewright.accounts.models import User
from scripts.update_supervisor import Supervisor, extract, read, write
from scripts.project_files import source_files, copy_files, replace_files


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
            self.assertIn(f'pushd "{origin}"', content)
            self.assertIn(f'--project "{origin}"', content)
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
