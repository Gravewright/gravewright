import base64
import hashlib
import io
import json
import zipfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign
from .models import ModuleSet, ModuleValue, Package
from .packages import canonical, host
from . import test_marketplace


class LifecycleTests(TestCase):
    setUp = test_marketplace.MarketplaceTests.setUp

    def release(self, version='1.0.0', locales=False, system=False):
        manifest = {'id': 'publisher.test', 'version': version, 'name': 'Test package',
                    'description': 'Test', 'author': 'Publisher', 'license': 'MIT',
                    'sdk': {'requires': '>=1.0.0 <2.0.0', 'tested': '1.0.0'}, 'entry': 'main.js'}
        if locales:
            manifest['locales'] = {'pt-BR': {'name': 'Português', 'path': 'pt-BR.json'}}
        if system:
            manifest['system'] = {'actorTypes': [{'id': 'character', 'label': 'Character'}]}
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr('manifest.json', json.dumps(manifest))
            archive.writestr('main.js', 'export default {}')
            if locales:
                archive.writestr('pt-BR.json', json.dumps({'Hello': 'Olá'}))
        raw = output.getvalue()
        record = {'id': manifest['id'], 'version': version, 'sdk': manifest['sdk']['requires'],
                  'download': f'https://publisher.example/{version}.zip',
                  'sha256': hashlib.sha256(raw).hexdigest(), 'keyId': 'publisher'}
        if system:
            record['type'] = 'system'
        record['signature'] = base64.b64encode(self.key.sign(canonical(record))).decode()
        return record, raw

    def install(self, **kwargs):
        record, raw = self.release(**kwargs)
        host().install(record, raw)
        return Package.objects.get(module_id=record['id'], version=record['version'])

    def post(self, action, version='1.0.0', **extra):
        if action == 'remove' and 'confirmedTables' not in extra:
            extra['confirmedTables'] = [str(pk) for pk in Campaign.objects.values_list('pk', flat=True)]
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post('/api/module-packages/' + action,
                                    {'id': 'publisher.test', 'version': version, **extra},
                                    content_type='application/json')

    def campaign(self):
        campaign = Campaign.objects.create(owner=self.user, name='Lifecycle')
        selected = ModuleSet.objects.create(campaign=campaign, modules={'publisher.test': '1.0.0'},
                                            replacements={'actor.sheet': 'publisher.test'})
        ModuleValue.objects.create(campaign=campaign, module_id='publisher.test', key='saved',
                                   value={'keep': True}, revision='1')
        return selected

    def test_remove_deactivates_tables_and_files_but_preserves_storage(self):
        row = self.install()
        selected = self.campaign()
        engine = host()
        path = engine.directory / 'packages' / row.module_id / row.version / row.digest
        archive = engine.directory / 'archives' / (row.digest + '.zip')
        with override_settings(GRAVEWRIGHT_MARKETPLACE_URL='', GRAVEWRIGHT_MARKETPLACE_KEYS_FILE=''):
            response = self.post('remove')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(Package.objects.exists())
        self.assertFalse(path.exists())
        self.assertFalse(archive.exists())
        selected.refresh_from_db()
        self.assertEqual(selected.modules, {})
        self.assertEqual(selected.replacements, {})
        self.assertNotEqual(selected.revision, '0')
        self.assertEqual(ModuleValue.objects.get().value, {'keep': True})

    def test_update_selects_newest_version_and_preserves_table_activation(self):
        self.install()
        selected = self.campaign()
        releases = [self.release('1.9.0'), self.release('1.10.0')]
        records = [record for record, _ in releases]
        downloads = {record['download']: raw for record, raw in releases}
        downloads['https://publisher.example/catalog.json'] = json.dumps(records).encode()
        with patch('gravewright.modules.views.download', side_effect=lambda url, limit: downloads[url]):
            response = self.post('update')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['version'], '1.10.0')
        self.assertEqual(list(Package.objects.values_list('version', flat=True)), ['1.10.0'])
        selected.refresh_from_db()
        self.assertEqual(selected.modules, {'publisher.test': '1.10.0'})
        self.assertEqual(selected.replacements, {'actor.sheet': 'publisher.test'})
        self.assertNotEqual(selected.revision, '0')
        self.assertTrue(ModuleValue.objects.exists())

    def test_update_keeps_globally_active_language(self):
        row = self.install(locales=True)
        row.global_enabled = True
        row.save()
        record, raw = self.release('1.1.0', locales=True)
        with patch('gravewright.modules.views.download', side_effect=[json.dumps([record]).encode(), raw]):
            response = self.post('update')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(Package.objects.get(version='1.1.0').global_enabled)

    def test_no_update_does_not_download_or_downgrade(self):
        self.install(version='2.0.0')
        record, _ = self.release()
        with patch('gravewright.modules.views.download', return_value=json.dumps([record]).encode()) as download:
            response = self.post('update', version='2.0.0')
        self.assertEqual(response.json(), {'updated': False, 'version': '2.0.0'})
        self.assertEqual(download.call_count, 1)
        self.assertTrue(Package.objects.filter(version='2.0.0').exists())

    def test_untrusted_update_preserves_current_release(self):
        self.install()
        record, raw = self.release('1.1.0')
        with patch('gravewright.modules.views.download', side_effect=[json.dumps([record]).encode(), raw + b'changed']):
            response = self.post('update')
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(Package.objects.get().version, '1.0.0')

    def test_only_owner_can_update_or_remove(self):
        self.install()
        user = User.objects.create_user(email='player@lifecycle.test', name='Player', role='participant')
        self.client.force_login(user)
        for action in ['update', 'remove']:
            self.assertEqual(self.post(action).status_code, 403)
        self.assertTrue(Package.objects.exists())

    def test_unknown_release_and_extra_input_are_rejected(self):
        self.assertEqual(self.post('remove').status_code, 404)
        self.install()
        self.assertEqual(self.post('remove', path='elsewhere').status_code, 400)
        self.assertTrue(Package.objects.exists())

    def test_active_server_module_is_deactivated_before_removal(self):
        row = Package.objects.create(module_id='publisher.test', version='1.0.0', digest='f' * 64,
                                     manifest={'django': {'apps': ['review_app']}}, record={})
        with patch('gravewright.modules.views.server_active', return_value=True), patch(
            'gravewright.modules.server_apps.queue_activation',
            return_value={'restartRequired': True, 'stage': 'queued'},
        ) as queue:
            response = self.post('remove')
        self.assertEqual(response.status_code, 202)
        queue.assert_called_once_with(row, False)
        self.assertTrue(Package.objects.exists())
        with patch('gravewright.modules.views.server_active', return_value=False):
            response = self.post('remove')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Package.objects.exists())

    def test_removal_rejects_paths_outside_module_directory(self):
        row = self.install()
        row.digest = '../../../../outside'
        row.save()
        self.assertEqual(self.post('remove').status_code, 403)
        self.assertTrue(Package.objects.exists())

    def test_preview_lists_affected_tables_and_removal_requires_confirmation(self):
        self.install()
        selected = self.campaign()
        second = Campaign.objects.create(owner=self.user, name='Second table')
        ModuleSet.objects.create(campaign=second, modules={'publisher.test': '1.0.0'})
        Campaign.objects.create(owner=self.user, name='Unaffected')
        response = self.post('removal-preview')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['tables'], [
            {'id': str(selected.campaign_id), 'name': 'Lifecycle'},
            {'id': str(second.pk), 'name': 'Second table'},
        ])
        self.assertEqual(self.post('remove', confirmedTables=[]).status_code, 409)
        self.assertEqual(self.post('remove', confirmedTables=[str(selected.campaign_id)]).status_code, 409)
        self.assertTrue(Package.objects.exists())
        self.assertEqual(self.post('remove').status_code, 200)
        self.assertFalse(ModuleSet.objects.get(campaign=second).modules)

    def test_last_system_removal_resets_table_system_and_preserves_data(self):
        self.install(system=True)
        selected = self.campaign()
        campaign = selected.campaign
        campaign.system = 'publisher.test'
        campaign.save()
        preview = self.post('removal-preview').json()
        self.assertTrue(preview['system'])
        self.assertTrue(preview['resetsSystem'])
        self.assertEqual(self.post('remove').status_code, 200)
        campaign.refresh_from_db()
        self.assertEqual(campaign.system, 'gravewright-pdf-system')
        selected.refresh_from_db()
        self.assertFalse(selected.modules)
        self.assertTrue(ModuleValue.objects.exists())

    def test_system_update_keeps_table_system(self):
        self.install(system=True)
        selected = self.campaign()
        campaign = selected.campaign
        campaign.system = 'publisher.test'
        campaign.save()
        record, raw = self.release('1.1.0', system=True)
        with patch('gravewright.modules.views.download', side_effect=[json.dumps([record]).encode(), raw]):
            response = self.post('update')
        self.assertEqual(response.status_code, 200, response.content)
        campaign.refresh_from_db()
        self.assertEqual(campaign.system, 'publisher.test')
        selected.refresh_from_db()
        self.assertEqual(selected.modules, {'publisher.test': '1.1.0'})


class SingleReleaseTests(TestCase):
    """Installing another version replaces the installed release, as an update does."""

    setUp = test_marketplace.MarketplaceTests.setUp
    release = LifecycleTests.release
    install = LifecycleTests.install
    campaign = LifecycleTests.campaign

    def upload(self, raw, kind='module'):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post('/api/module-packages/install-local', {
                'file': SimpleUploadedFile('package.zip', raw, content_type='application/zip'), 'kind': kind})

    def test_local_install_of_a_newer_version_replaces_the_installed_release(self):
        self.install()
        selected = self.campaign()
        _, raw = self.release('1.1.0')
        response = self.upload(raw)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['replaced'], ['1.0.0'])
        self.assertEqual(list(Package.objects.values_list('version', flat=True)), ['1.1.0'])
        selected.refresh_from_db()
        self.assertEqual(selected.modules, {'publisher.test': '1.1.0'})
        self.assertEqual(selected.replacements, {'actor.sheet': 'publisher.test'})
        self.assertEqual(ModuleValue.objects.get().value, {'keep': True})
        self.assertEqual([row['version'] for row in self.client.get('/api/module-packages').json()], ['1.1.0'])

    def test_an_older_version_is_refused_without_installing_it(self):
        self.install(version='2.0.0')
        _, raw = self.release('1.0.0')
        response = self.upload(raw)
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json(), {'error': 'newer_installed'})
        self.assertEqual(list(Package.objects.values_list('version', flat=True)), ['2.0.0'])
        digest = hashlib.sha256(raw).hexdigest()
        self.assertFalse((host().directory / 'archives' / (digest + '.zip')).exists())

    def test_a_package_id_keeps_its_kind(self):
        self.install()
        _, raw = self.release('1.1.0', system=True)
        response = self.upload(raw, kind='system')
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json(), {'error': 'package_type_changed'})
        self.assertEqual(list(Package.objects.values_list('version', flat=True)), ['1.0.0'])

    def assert_language_kind_change_rejected(self, locales):
        installed = self.install(locales=locales)
        installed.global_enabled = locales
        installed.save(update_fields=['global_enabled'])
        record, raw = self.release('1.1.0', locales=not locales)
        engine = host()
        original_archive = engine.directory / 'archives' / (installed.digest + '.zip')
        original_bytes = original_archive.read_bytes()
        for route in ('local', 'marketplace', 'update'):
            with self.subTest(route=route):
                if route == 'local':
                    response = self.upload(raw)
                else:
                    with patch('gravewright.modules.views.download', side_effect=[json.dumps([record]).encode(), raw]):
                        path = '/api/marketplace/install' if route == 'marketplace' else '/api/module-packages/update'
                        version = '1.1.0' if route == 'marketplace' else '1.0.0'
                        response = self.client.post(path, {'id': installed.module_id, 'version': version},
                                                    content_type='application/json')
                self.assertEqual(response.status_code, 409, response.content)
                self.assertEqual(response.json(), {'error': 'package_type_changed'})
                self.assertEqual(list(Package.objects.values_list('version', 'global_enabled')), [('1.0.0', locales)])
                self.assertEqual(original_archive.read_bytes(), original_bytes)
                engine.verify_installed(installed)
                self.assertFalse((engine.directory / 'archives' / (record['sha256'] + '.zip')).exists())
                self.assertFalse((engine.directory / 'packages' / installed.module_id / '1.1.0').exists())

    def test_a_language_package_cannot_be_replaced_by_a_browser_module(self):
        self.assert_language_kind_change_rejected(locales=True)

    def test_a_browser_module_cannot_be_replaced_by_a_language_package(self):
        self.assert_language_kind_change_rejected(locales=False)

    def test_marketplace_install_of_a_newer_release_replaces_the_active_language(self):
        row = self.install(locales=True)
        row.global_enabled = True
        row.save()
        record, raw = self.release('1.1.0', locales=True)
        with patch('gravewright.modules.views.download', side_effect=[json.dumps([record]).encode(), raw]), \
                self.captureOnCommitCallbacks(execute=True):
            response = self.client.post('/api/marketplace/install', {'id': 'publisher.test', 'version': '1.1.0'},
                                        content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['replaced'], ['1.0.0'])
        self.assertEqual(list(Package.objects.values_list('version', 'global_enabled')), [('1.1.0', True)])

    def test_first_and_repeated_installs_keep_their_response_shape(self):
        record, raw = self.release()
        with patch('gravewright.modules.views.download', side_effect=[json.dumps([record]).encode(), raw] * 2):
            for _ in range(2):
                response = self.client.post('/api/marketplace/install', {'id': 'publisher.test', 'version': '1.0.0'},
                                            content_type='application/json')
                self.assertEqual(response.status_code, 200, response.content)
                self.assertNotIn('replaced', response.json())
        self.assertEqual(Package.objects.count(), 1)

    def test_revoked_releases_stay_recorded_and_do_not_block_another_version(self):
        self.install(version='1.1.0')
        Package.objects.update(revoked=True)
        _, raw = self.release('1.0.0')
        response = self.upload(raw)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['replaced'], [])
        self.assertEqual(sorted(Package.objects.values_list('version', 'revoked')), [('1.0.0', False), ('1.1.0', True)])

    def test_an_active_server_app_switches_after_a_supervised_restart(self):
        Package.objects.create(module_id='publisher.test', version='1.0.0', digest='f' * 64,
                               manifest={'django': {'apps': ['review_app']}}, record={})
        replacement = Package.objects.create(module_id='publisher.test', version='1.1.0', digest='e' * 64,
                                             manifest={'django': {'apps': ['review_app']}}, record={})
        from .lifecycle import supersede
        with patch('gravewright.modules.server_apps.queue_activation',
                   return_value={'restartRequired': True, 'stage': 'queued'}) as queue:
            result = supersede(host(), replacement, lambda engine, row: row.version == '1.0.0')
        queue.assert_called_once_with(replacement, True)
        self.assertEqual(result['replaced'], ['1.0.0'])
        self.assertTrue(result['restartRequired'])
        self.assertEqual(Package.objects.count(), 2, 'The running release stays until the restart switches it.')
