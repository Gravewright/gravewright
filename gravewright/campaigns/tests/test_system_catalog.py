"""Signed package installation must update campaign system choices immediately."""
import base64
import hashlib
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.test import TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.campaigns.catalog import get_ruleset, list_rulesets
from gravewright.campaigns.models import Campaign
from gravewright.modules.models import ModuleSet, Package
from gravewright.modules.packages import ModuleFailure, ModulePackages, canonical


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class SystemCatalogTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.key = Ed25519PrivateKey.generate()
        keys = {'test': base64.b64encode(self.key.public_key().public_bytes_raw()).decode()}
        self.host = ModulePackages(Path(directory.name) / 'modules', keys)
        host_patch = patch('gravewright.modules.packages.host', return_value=self.host)
        host_patch.start()
        self.addCleanup(host_patch.stop)
        self.owner = User.objects.create_user(
            'systems@example.test', 'owner-password-123', name='Owner', role='owner')
        self.client.force_login(self.owner)

    def install(self, module_id='example.system', version='1.0.0', *, system=True,
                title='Example System', sdk='>=1.0.0 <3.0.0'):
        manifest = {
            'id': module_id, 'version': version, 'name': title,
            'description': 'Campaign system test', 'author': 'Test', 'license': 'MIT',
            'sdk': {'requires': sdk, 'tested': '1.0.0'}, 'entry': 'main.js',
        }
        if system is not False:
            manifest['system'] = {
                'actorTypes': [{'id': 'hero', 'label': 'Hero'}],
                'itemTypes': [{'id': 'equipment', 'label': 'Equipment'}],
            } if system is True else system
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr('manifest.json', json.dumps(manifest))
            archive.writestr('main.js', 'export default {start(){},stop(){}}')
        raw = output.getvalue()
        record = {
            'id': module_id, 'version': version, 'sdk': sdk,
            'download': 'https://example.test/module.zip',
            'sha256': hashlib.sha256(raw).hexdigest(), 'keyId': 'test',
        }
        record['signature'] = base64.b64encode(self.key.sign(canonical(record))).decode()
        self.host.install(record, raw)
        return record

    def revoke(self, record):
        record = {**record, 'status': 'revoked'}
        record['signature'] = base64.b64encode(self.key.sign(canonical(record))).decode()
        self.host.revoke(record)

    def create_campaign(self, system='example.system'):
        return self.client.post('/api/containers', {
            'name': 'Installed system table', 'description': '', 'system': system,
        }, content_type='application/json')

    def test_signed_install_updates_api_inside_and_campaign_creation_without_restart(self):
        self.assertEqual(len(self.client.get('/api/rulesets').json()['rulesets']), 1)
        self.assertNotContains(self.client.get('/inside?section=systems'), 'Example System')
        self.install()
        row = self.client.get('/api/rulesets').json()['rulesets'][1]
        self.assertEqual(row, {
            'systemId': 'example.system', 'title': 'Example System', 'version': '1.0.0',
            'actorTypes': [{'id': 'hero', 'label': 'Hero'}],
            'itemTypes': [{'id': 'equipment', 'label': 'Equipment'}],
        })
        self.assertContains(self.client.get('/inside?section=systems'), 'data-package-kind="system"')
        self.assertIn('Example System', [r['title'] for r in self.client.get('/api/rulesets').json()['rulesets']])
        self.assertContains(self.client.get('/inside/dialog/create'), 'value="example.system"')
        created = self.create_campaign()
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.json()['system'], 'example.system')
        self.assertEqual(Campaign.objects.get().system, 'example.system')
        self.assertEqual(ModuleSet.objects.get().modules, {'example.system': '1.0.0'})
        self.assertEqual(get_ruleset('example.system'), row)

    def test_filters_releases_and_uses_numeric_semver_for_each_system(self):
        self.install(version='1.9.0', title='Old Example')
        self.install(version='1.10.0')
        self.install('example.addon', system=False)
        self.revoke(self.install('example.revoked'))
        self.install('example.incompatible', sdk='>=1.0.0 <2.0.0')
        # A host SDK upgrade can make a previously installed release incompatible.
        with patch('gravewright.modules.packages.SDK_VERSION', (2, 0, 0)):
            rows = list_rulesets()
            self.assertEqual([row['systemId'] for row in rows],
                             ['gravewright-pdf-system', 'example.system'])
            self.assertEqual(rows[1]['version'], '1.10.0')
            self.assertEqual(rows[1]['title'], 'Example System')
            self.assertIsNone(get_ruleset('example.incompatible'))
            for system in ['example.addon', 'example.revoked', 'example.incompatible']:
                response = self.create_campaign(system)
                self.assertEqual(response.status_code, 400, response.content)
        newest = Package.objects.get(module_id='example.system', version='1.10.0')
        self.revoke(newest.record)
        self.assertEqual(get_ruleset('example.system')['version'], '1.9.0')

    def test_existing_campaign_keeps_removed_or_revoked_system_when_edited(self):
        for unavailable in ['removed', 'revoked']:
            with self.subTest(unavailable=unavailable):
                system_id = 'example.' + unavailable
                record = self.install(system_id)
                created = self.create_campaign(system_id)
                self.assertEqual(created.status_code, 201, created.content)
                campaign_id = created.json()['id']
                if unavailable == 'removed':
                    Package.objects.filter(module_id=system_id).delete()
                else:
                    self.revoke(record)
                self.assertIsNone(get_ruleset(system_id))
                self.assertEqual(self.create_campaign(system_id).status_code, 400)
                self.assertNotContains(self.client.get('/inside/dialog/create'), f'value="{system_id}"')
                self.assertContains(self.client.get('/inside/dialog/edit/' + campaign_id),
                                    f'<option value="{system_id}" selected>{system_id} (unavailable)</option>')
                response = self.client.post('/api/containers/' + campaign_id, {
                    'name': 'Renamed table', 'description': '', 'system': system_id,
                }, content_type='application/json')
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(Campaign.objects.get(pk=campaign_id).system, system_id)

    def test_campaign_descriptor_keeps_explicitly_activated_version_after_install(self):
        self.install(version='1.0.0')
        created = self.create_campaign()
        self.assertEqual(created.status_code, 201, created.content)
        campaign_id = created.json()['id']
        selected = self.host.configure(campaign_id, {'example.system': '1.0.0'}, {}, self.host.state(campaign_id)['moduleSetRevision'])
        self.install(version='2.0.0', system={
            'actorTypes': [{'id': 'npc', 'label': 'NPC'}],
            'itemTypes': [{'id': 'treasure', 'label': 'Treasure'}],
        })
        self.assertEqual(get_ruleset('example.system')['version'], '2.0.0')
        pinned = get_ruleset('example.system', campaign_id=campaign_id)
        self.assertEqual(pinned['version'], '1.0.0')
        self.assertEqual(pinned['actorTypes'], [{'id': 'hero', 'label': 'Hero'}])
        self.assertEqual(pinned['itemTypes'], [{'id': 'equipment', 'label': 'Equipment'}])
        selected = self.host.configure(campaign_id, {'example.system': '2.0.0'}, {},
                                       selected['moduleSetRevision'])
        self.assertEqual(get_ruleset('example.system', campaign_id=campaign_id)['version'], '2.0.0')
        self.host.configure(campaign_id, {}, {}, selected['moduleSetRevision'])
        self.assertEqual(get_ruleset('example.system', campaign_id=campaign_id)['version'], '2.0.0')

    def test_unavailable_selected_release_does_not_fall_back_to_another_version(self):
        self.install(version='1.0.0', sdk='>=1.0.0 <2.0.0')
        self.install(version='2.0.0')
        created = self.create_campaign()
        self.assertEqual(created.status_code, 201, created.content)
        campaign_id = created.json()['id']
        self.host.configure(campaign_id, {'example.system': '1.0.0'}, {}, self.host.state(campaign_id)['moduleSetRevision'])
        with patch('gravewright.modules.packages.SDK_VERSION', (2, 0, 0)):
            self.assertIsNone(get_ruleset('example.system', campaign_id=campaign_id))
            self.assertEqual(get_ruleset('example.system')['version'], '2.0.0')
        Package.objects.filter(module_id='example.system', version='1.0.0').update(revoked=True)
        self.assertIsNone(get_ruleset('example.system', campaign_id=campaign_id))
        Package.objects.filter(module_id='example.system', version='1.0.0').delete()
        self.assertIsNone(get_ruleset('example.system', campaign_id=campaign_id))

    def test_default_native_identity_remains_available_without_package_queries(self):
        with self.assertNumQueries(0):
            self.assertEqual(get_ruleset(''), get_ruleset('gravewright-pdf-system'))
        self.assertEqual(self.create_campaign('gravewright-pdf-system').status_code, 201)
        self.assertEqual(self.create_campaign('').status_code, 201)
        self.assertIsNone(get_ruleset('example.missing'))

    def test_signed_install_rejects_invalid_system_declarations(self):
        actor_types = [{'id': 'hero', 'label': 'Hero'}]
        for declaration in [
            {}, {'actorTypes': []}, {'actorTypes': [{'id': 'hero'}]},
            {'actorTypes': actor_types + [{'id': 'hero', 'label': 'Duplicate'}]},
            {'actorTypes': actor_types, 'itemTypes': [
                {'id': 'equipment', 'label': 'Equipment'},
                {'id': 'equipment', 'label': 'Duplicate'},
            ]},
        ]:
            with self.subTest(declaration=declaration), self.assertRaises(ModuleFailure) as error:
                self.install(system=declaration)
            self.assertEqual(error.exception.code, 'invalid_data')
        with self.assertRaises(ModuleFailure) as error:
            self.install('gravewright-pdf-system')
        self.assertEqual(error.exception.code, 'invalid_data')
        self.assertFalse(Package.objects.exists())

    def test_switching_systems_preserves_addons_and_their_replacements(self):
        self.install('future.first')
        self.install('future.second', system={
            'actorTypes': [{'id': 'pilot', 'label': 'Pilot'}],
            'itemTypes': [{'id': 'ship', 'label': 'Ship'}],
        })
        self.install('future.addon', system=False)
        created = self.create_campaign('future.first')
        self.assertEqual(created.status_code, 201, created.content)
        campaign_id = created.json()['id']
        current = self.host.state(campaign_id)
        self.host.configure(campaign_id,
            {'future.first': '1.0.0', 'future.addon': '1.0.0'},
            {'actor.sheet': 'future.first', 'chat.log': 'future.addon'},
            current['moduleSetRevision'])
        response = self.client.post('/api/containers/' + campaign_id, {
            'name': 'Changed system', 'description': '', 'system': 'future.second',
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        selected = ModuleSet.objects.get(campaign_id=campaign_id)
        self.assertEqual(selected.modules, {'future.second': '1.0.0', 'future.addon': '1.0.0'})
        self.assertEqual(selected.replacements, {'chat.log': 'future.addon'})
        directory = self.client.get('/api/containers/' + campaign_id + '/actors')
        self.assertEqual(directory.status_code, 200, directory.content)
        self.assertEqual(directory.json()['systemId'], 'future.second')
        self.assertEqual(directory.json()['actorTypes'], [{'id': 'pilot', 'label': 'Pilot'}])
        response = self.client.post('/api/containers/' + campaign_id, {
            'name': 'Native again', 'description': '', 'system': 'gravewright-pdf-system',
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        selected.refresh_from_db()
        self.assertEqual(selected.modules, {'future.addon': '1.0.0'})
        self.assertEqual(selected.replacements, {'chat.log': 'future.addon'})

    def test_saving_system_does_not_silently_upgrade_the_active_release(self):
        self.install('future.pinned', version='1.0.0')
        created = self.create_campaign('future.pinned')
        self.assertEqual(created.status_code, 201, created.content)
        campaign_id = created.json()['id']
        revision = self.host.state(campaign_id)['moduleSetRevision']
        self.install('future.pinned', version='2.0.0')
        response = self.client.post('/api/containers/' + campaign_id, {
            'name': 'Renamed', 'description': '', 'system': 'future.pinned',
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        selected = ModuleSet.objects.get(campaign_id=campaign_id)
        self.assertEqual(selected.modules, {'future.pinned': '1.0.0'})
        self.assertEqual(selected.revision, revision)
