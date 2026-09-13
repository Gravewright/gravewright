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


class ArchiveTests(SimpleTestCase):
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
            backup = supervisor.state / 'backups/test'
            supervisor.backup(backup)
            with closing(sqlite3.connect(db)) as c, c:
                c.execute("update fixture set value='changed'")
            (media / 'file').write_bytes(b'changed');(media / 'new-file').touch()
            write(supervisor.state / 'transaction.json', {'previous': str(supervisor.origin), 'backup': 'test', 'restore': True})
            supervisor.recover()
            with closing(sqlite3.connect(db)) as c, c:
                self.assertEqual(c.execute('select value from fixture').fetchone(), ('original',))
            self.assertEqual((media / 'file').read_bytes(), b'original')
            self.assertFalse((media / 'new-file').exists())
            self.assertEqual(read(supervisor.state / 'progress.json')['stage'], 'rolled_back')
            self.assertFalse((supervisor.state / 'transaction.json').exists())


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
            self.assertTrue(request_update('0.1.0-alpha.1')['busy'])
            self.assertEqual(read(Path(directory) / 'job.json')['version'], '0.1.0-alpha.1')
            with self.assertRaises(AuthError):
                request_update('0.1.0-alpha.1')

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
