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

    def test_provider_type_presentation_passes_through_without_known_game_types(self):
        definition = {
            'actorTypes': [{'id': 'vehicle', 'label': 'Vehicle', 'labelKey': 'types.vehicle', 'icon': 'User'}],
            'itemTypes': [{'id': 'component', 'label': 'Component', 'labelKey': 'types.component', 'icon': 'Backpack'}],
        }
        self.install(system=definition)
        result = self.create_campaign()
        self.assertEqual(result.status_code, 201, result.content)
        from gravewright.items.services import types
        campaign = Campaign.objects.get()
        self.assertEqual(types(campaign.system, campaign_id=campaign.pk), definition['itemTypes'])
        self.assertEqual(get_ruleset(campaign.system)['actorTypes'], definition['actorTypes'])

    def test_provider_type_icons_are_names_without_paths_or_markup(self):
        for index, icon in enumerate(['../image.svg', '<svg>', 'https://example.test/icon.svg', 'x' * 81]):
            with self.subTest(icon=icon), self.assertRaises(ModuleFailure):
                self.install(module_id=f'example.badicon{index}', system={
                    'actorTypes': [{'id': 'entity', 'label': 'Entity'}],
                    'itemTypes': [{'id': 'component', 'label': 'Component', 'icon': icon}],
                })

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

    def test_installed_system_initiative_uses_the_pinned_release_and_numeric_sheet_data(self):
        from gravewright.combat.services import configuration, roll_initiative
        from gravewright.campaigns.models import Membership
        from gravewright.maps.services import MapError
        declaration = {'actorTypes': [{'id': 'hero', 'label': 'Hero'}],
                       'combat': {'formula': '1d20 + @combat.initiative', 'manualInput': 'number'}}
        self.install('example.initiative', system=declaration)
        created = self.create_campaign('example.initiative')
        self.assertEqual(created.status_code, 201, created.content)
        who = Membership.objects.select_related('campaign').get(campaign_id=created.json()['id'])
        self.install('example.initiative', version='2.0.0', system={
            **declaration, 'combat': {'formula': '1d6'}})
        self.assertEqual(configuration(who)['formula'], '1d20 + @combat.initiative')
        self.assertEqual(configuration(who)['input'], 'roll')
        for _ in range(8):
            result = roll_initiative(who, '1d20 + @combat.initiative', {'combat': {'initiative': 5}})
            self.assertGreaterEqual(result, 6)
            self.assertLessEqual(result, 25)
        self.assertEqual(roll_initiative(who, '@missing + 2', {}), 2)
        for bad in ['1d20', True, {}, float('inf'), 1e9, 10**1000]:
            with self.subTest(bad=bad), self.assertRaises(MapError):
                roll_initiative(who, '@init + 1', {'init': bad})

    def test_system_combat_manifest_rejects_unbounded_or_executable_configuration(self):
        for combat in [{'formula': ''}, {'formula': 'x' * 121}, {'formula': 3},
                       {'formula': '1d20', 'manualInput': 'javascript'}, {'formula': '1d20', 'roll': 'code'}]:
            with self.subTest(combat=combat), self.assertRaises(ModuleFailure):
                self.install(system={'actorTypes': [{'id': 'hero', 'label': 'Hero'}], 'combat': combat})
