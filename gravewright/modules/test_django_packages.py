import base64
import hashlib
import io
import json
import os
import sys
import zipfile
from unittest.mock import patch

from django.test import TestCase

from config.marketplace_apps import load_apps
from scripts.update_supervisor import read, write
from .models import Package
from .packages import ModuleFailure, canonical, host
from .server_apps import plan
from . import test_marketplace


class DjangoPackageTests(TestCase):
    def setUp(self):
        test_marketplace.MarketplaceTests.setUp(self)
        environment = patch.dict(os.environ, {'GRAVEWRIGHT_MANAGED_PROTOCOL': '2'})
        environment.start()
        self.addCleanup(environment.stop)

    def release(self, django=None, record_type='django', files=None):
        manifest = {'id': 'publisher.server', 'name': 'Server app', 'version': '1.0.0',
                    'description': 'Test server app', 'author': 'Publisher', 'license': 'MIT',
                    'sdk': {'requires': '>=1.0.0 <2.0.0', 'tested': '1.0.0'},
                    'django': django or {'apps': ['marketplace_fixture.apps.FixtureConfig']}}
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr('manifest.json', json.dumps(manifest))
            for name, content in (files or {'marketplace_fixture/__init__.py': '',
                    'marketplace_fixture/apps.py': 'from django.apps import AppConfig\nclass FixtureConfig(AppConfig):\n name="marketplace_fixture"\n'}).items():
                archive.writestr(name, content)
        raw = output.getvalue()
        record = {'id': manifest['id'], 'version': manifest['version'], 'sdk': manifest['sdk']['requires'],
                  'download': 'https://publisher.example/server.zip', 'sha256': hashlib.sha256(raw).hexdigest(),
                  'keyId': 'publisher'}
        if record_type:
            record['type'] = record_type
        record['signature'] = base64.b64encode(self.key.sign(canonical(record))).decode()
        return record, raw

    def test_signed_and_local_django_archives_are_installed_without_importing(self):
        record, raw = self.release()
        engine = host()
        manifest = engine.install(record, raw)
        self.assertIn('django', manifest)
        self.assertNotIn('entry', manifest)
        self.assertNotIn('marketplace_fixture', sys.modules)
        self.assertEqual(engine.install_local(raw, expected_type='module'), manifest)
        engine.verify_installed(Package.objects.get())
        self.assertFalse(self.client.get('/api/module-packages').json()[0]['globalEnabled'])

    def test_browser_type_cannot_smuggle_python(self):
        for kind in ('module', None):
            with self.subTest(kind=kind), self.assertRaises(ModuleFailure):
                host().install(*self.release(record_type=kind))

    def test_rejects_missing_apps_and_dependency_command_arguments(self):
        for options in ({'files': {'other/__init__.py': ''}},
                        {'django': {'apps': ['marketplace_fixture'], 'requirements': ['--index-url=https://example.test']}},
                        {'django': {'apps': ['marketplace_fixture'], 'requirements': ['Django @ https://example.test/pkg.whl']}}):
            with self.subTest(options=options), self.assertRaises(ModuleFailure):
                host().install(*self.release(**options))

    def test_python_and_manifest_are_not_served_as_browser_assets(self):
        host().install(*self.release())
        row = Package.objects.get()
        for asset in ('manifest.json', 'marketplace_fixture/apps.py'):
            response = self.client.get(f'/api/module-packages/{row.module_id}/{row.version}/{row.digest}/{asset}')
            self.assertEqual(response.status_code, 404)

    def test_owner_activation_is_queued_and_serialized_with_core_updates(self):
        host().install(*self.release())
        body = {'id': 'publisher.server', 'version': '1.0.0', 'enabled': True}
        with patch.dict(os.environ, {'GRAVEWRIGHT_MANAGED_STATE': str(self.directory)}):
            response = self.client.post('/api/module-packages/activation', body, content_type='application/json')
            self.assertEqual(response.status_code, 202, response.content)
            self.assertEqual(read(self.directory / 'job.json'), {'kind': 'django', **body})
            self.assertEqual(self.client.post('/api/module-packages/activation', body, content_type='application/json').status_code, 409)
        self.assertFalse((host().directory / 'server-apps.json').exists())

    def test_unmanaged_activation_is_rejected(self):
        host().install(*self.release())
        with patch.dict(os.environ, {'GRAVEWRIGHT_MANAGED_STATE': ''}):
            response = self.client.post('/api/module-packages/activation',
                {'id': 'publisher.server', 'version': '1.0.0', 'enabled': True}, content_type='application/json')
        self.assertEqual(response.status_code, 409)

    def test_legacy_supervisor_cannot_receive_django_jobs(self):
        host().install(*self.release())
        with patch.dict(os.environ, {'GRAVEWRIGHT_MANAGED_STATE': str(self.directory), 'GRAVEWRIGHT_MANAGED_PROTOCOL': ''}):
            response = self.client.post('/api/module-packages/activation',
                {'id': 'publisher.server', 'version': '1.0.0', 'enabled': True}, content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['error'], 'managed_start_required')
        self.assertFalse((self.directory / 'job.json').exists())

    def test_non_owner_cannot_activate_and_revoked_versions_cannot_enable(self):
        host().install(*self.release())
        body = {'id': 'publisher.server', 'version': '1.0.0', 'enabled': True}
        self.client.logout()
        response = self.client.post('/api/module-packages/activation', body, content_type='application/json')
        self.assertIn(response.status_code, (401, 403))
        self.client.force_login(self.user)
        Package.objects.update(revoked=True)
        with patch.dict(os.environ, {'GRAVEWRIGHT_MANAGED_STATE': str(self.directory)}):
            response = self.client.post('/api/module-packages/activation', body, content_type='application/json')
            self.assertEqual(response.status_code, 403)
            self.assertFalse((self.directory / 'job.json').exists())

    def test_registry_load_checks_bytes_and_deactivation_preserves_other_apps(self):
        host().install(*self.release())
        engine = host()
        registry = plan('publisher.server', '1.0.0', True)
        write(engine.directory / 'server-apps.json', registry)
        with patch.object(sys, 'path', list(sys.path)), patch.object(sys, 'dont_write_bytecode', False):
            self.assertEqual(load_apps(engine.directory), ['marketplace_fixture.apps.FixtureConfig'])
            self.assertTrue(sys.dont_write_bytecode)
        self.assertEqual(plan('publisher.server', '1.0.0', False), {})
        row = Package.objects.get()
        path = engine.directory / 'packages' / row.module_id / row.version / row.digest / 'marketplace_fixture/apps.py'
        path.write_text('raise RuntimeError("tampered")', encoding='utf-8')
        with self.assertRaises(ValueError):
            load_apps(engine.directory)
        with self.assertRaises(ModuleFailure):
            plan('publisher.server', '1.0.0', True)
