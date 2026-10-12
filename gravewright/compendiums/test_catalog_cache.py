"""Immutable content reuse never caches campaign selection or authorization."""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import uuid
import zipfile

from django.test import TestCase, override_settings

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.modules.models import ModuleSet, Package
from gravewright.modules.packages import Contracts, ModuleFailure, ModulePackages, host
from gravewright.table import domain
from gravewright.table.models import DocumentAccess
from . import catalog, content


SYSTEM = 'example.catalog-cache'


@override_settings(
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
)
class CatalogCacheTests(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix='gravewright-catalog-cache-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.enterContext(override_settings(
            MEDIA_ROOT=self.root / 'media', GRAVEWRIGHT_MODULES_ROOT=self.root / 'modules',
            GRAVEWRIGHT_CONTENT_ROOT=self.root / 'content', GRAVEWRIGHT_MARKETPLACE_KEYS_FILE='',
        ))
        catalog._collection_cache.clear()
        self.addCleanup(catalog._collection_cache.clear)
        self.gm = User.objects.create_user(email='cache-gm@example.test', name='GM', password='password', role='owner')
        self.player = User.objects.create_user(email='cache-player@example.test', name='Player', password='password')
        self.campaign = Campaign.objects.create(owner=self.gm, name='Catalog fixture', system=SYSTEM)
        for user, role in ((self.gm, 'gm'), (self.player, 'player')):
            Membership.objects.create(campaign=self.campaign, user=user, role=role)
        self.manifest = {
            'id': SYSTEM, 'version': '0.1.0', 'name': 'Catalog fixture', 'description': 'Opaque test documents',
            'author': 'Tests', 'license': 'MIT', 'entry': 'main.js',
            'sdk': {'requires': '>=1.0.0 <2.0.0', 'tested': '1.0.0'},
            'system': {'actorTypes': [{'id': 'entity', 'label': 'Entity'}],
                       'itemTypes': [{'id': 'origin', 'label': 'Origin'}, {'id': 'gear', 'label': 'Gear'}]},
            'content': {'compendiums': ['content/alpha.json', 'content/beta.json']},
        }
        self.package = self.install()
        host().configure(self.campaign.pk, {SYSTEM: '0.1.0'}, {}, '0')

    def install(self, version='0.1.0', marker='Original', collections=None):
        manifest = deepcopy(self.manifest)
        manifest['version'] = version
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json', json.dumps(manifest))
            archive.writestr('main.js', 'export default {start(){}}')
            for label in ('alpha', 'beta'):
                collection = {'name': label, 'packs': [{
                    'id': label, 'label': label, 'type': 'item_pack', 'entries': [
                        {'id': label + '-' + kind, 'name': kind, 'type': kind, 'systemId': SYSTEM,
                         'data': {'marker': marker, 'nested': {'number': number}}}
                        for number, kind in enumerate(('origin', 'gear'))
                    ],
                }]}
                archive.writestr(f'content/{label}.json', json.dumps((collections or {}).get(label, collection)))
        host().install_local(output.getvalue(), expected_type='system')
        return Package.objects.get(module_id=SYSTEM, version=version)

    def state(self, user=None):
        return domain.state(self.campaign.pk, (user or self.gm).pk, 'compendiums')

    def read(self, user=None, request_id=None, **payload):
        return domain.command(self.campaign.pk, (user or self.gm).pk, 'compendiums', 'read', {
            'packId': self.pack_id(), **({'id': 'beta-origin'} if 'ids' not in payload else {}), **payload,
        }, request_id or uuid.uuid4())

    def pack_id(self, label='beta'):
        return 'native:' + str(uuid.uuid5(uuid.NAMESPACE_URL, f'module/{SYSTEM}/content/{label}.json/{label}'))

    def asset(self, label='beta'):
        return self.root / 'modules/packages' / SYSTEM / self.package.version / self.package.digest / f'content/{label}.json'

    def test_warm_reads_verify_only_the_requested_asset_without_reparsing_other_collections(self):
        summaries = self.state()['packs']
        self.assertEqual({entry['type'] for pack in summaries for entry in pack['entries']}, {'origin', 'gear'})
        verified = ModulePackages.verify_installed
        with patch.object(ModulePackages, 'verify_installed', autospec=True, side_effect=verified) as verify, \
             patch.object(content, 'validate_collection', wraps=content.validate_collection) as validate, \
             patch('gravewright.modules.packages.Contracts', wraps=Contracts) as contracts:
            for _ in range(3):
                self.assertEqual(self.read()['data']['marker'], 'Original')
            self.assertEqual(verify.call_count, 3)
            self.assertTrue(all(call.args[2] == 'content/beta.json' for call in verify.call_args_list))
            validate.assert_not_called()
            contracts.assert_not_called()

    def test_batch_and_single_reads_return_independent_copies(self):
        self.state()
        first = self.read()
        first['data']['nested']['number'] = 999
        result = self.read(ids=['beta-gear', 'beta-origin'])
        self.assertEqual([entry['type'] for entry in result['entries']], ['gear', 'origin'])
        self.assertEqual(result['entries'][1]['data']['nested']['number'], 0)
        result['entries'][0]['data']['nested']['number'] = 999
        self.assertEqual(self.read(id='beta-gear')['data']['nested']['number'], 1)

    def test_live_grants_are_not_reused_from_the_content_cache_or_old_request_id(self):
        self.state()
        access = DocumentAccess.objects.create(campaign=self.campaign, kind='compendiums', resource_id=self.pack_id(), grants={'player': 'read'})
        request_id = uuid.uuid4()
        self.assertEqual(self.read(self.player, request_id)['type'], 'origin')
        access.grants = {'player': 'none'}
        access.save(update_fields=['grants'])
        with self.assertRaises(domain.MapError) as denied:
            self.read(self.player, request_id)
        self.assertEqual(denied.exception.code, 'not_found')

    def test_extracted_bytes_are_reverified_even_with_same_size_and_timestamp(self):
        self.state()
        path = self.asset()
        original = path.read_bytes()
        stat = path.stat()
        path.write_bytes(original.replace(b'Original', b'Tampered'))
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        with self.assertRaises(domain.MapError):
            self.read()
        path.write_bytes(original)
        self.assertEqual(self.read()['data']['marker'], 'Original')

    def test_archive_and_approval_record_are_rechecked_after_warming(self):
        self.state()
        path = self.root / 'modules/archives' / (self.package.digest + '.zip')
        original = path.read_bytes()
        path.write_bytes(original + b'changed')
        with self.assertRaises(domain.MapError):
            self.read()
        path.write_bytes(original)
        record = deepcopy(self.package.record)
        Package.objects.filter(pk=self.package.pk).update(record={**record, 'sdk': '>=999.0.0'})
        with self.assertRaises(domain.MapError):
            self.read()
        Package.objects.filter(pk=self.package.pk).update(record=record)
        self.assertEqual(self.read()['data']['marker'], 'Original')

    def test_revocation_and_table_selection_are_live(self):
        self.state()
        Package.objects.filter(pk=self.package.pk).update(revoked=True)
        with self.assertRaises(domain.MapError):
            self.read()
        Package.objects.filter(pk=self.package.pk).update(revoked=False)
        ModuleSet.objects.filter(campaign=self.campaign).update(modules={})
        with self.assertRaises(domain.MapError):
            self.read()
        ModuleSet.objects.filter(campaign=self.campaign).update(modules={SYSTEM: '0.1.0'})
        self.assertEqual(self.read()['data']['marker'], 'Original')

    def test_release_change_invalidates_content_while_preserving_pack_identity(self):
        self.state()
        original_id = self.pack_id()
        self.install('0.2.0', 'Updated')
        selected = ModuleSet.objects.get(campaign=self.campaign)
        host().configure(self.campaign.pk, {SYSTEM: '0.2.0'}, {}, selected.revision)
        self.assertEqual(self.read()['data']['marker'], 'Updated')
        self.assertIn(original_id, [pack['id'] for pack in self.state()['packs']])

    def test_cache_is_bounded_by_collection_count_and_source_bytes(self):
        with patch.object(catalog, '_COLLECTION_CACHE_LIMIT', 1):
            self.assertEqual(len(self.state()['packs']), 2)
            self.assertLessEqual(len(catalog._collection_cache), 1)
            self.assertEqual(self.read(packId=self.pack_id('alpha'), id='alpha-origin')['type'], 'origin')
            self.assertLessEqual(len(catalog._collection_cache), 1)
        catalog._collection_cache.clear()
        with patch.object(catalog, '_COLLECTION_CACHE_BYTES', 1):
            self.assertEqual(len(self.state()['packs']), 2)
            self.assertFalse(catalog._collection_cache)
            self.assertEqual(self.read()['type'], 'origin')

    def test_schema_compilation_is_lazy_but_validation_and_asset_integrity_remain_enforced(self):
        with patch('gravewright.modules.packages.Contracts', wraps=Contracts) as contracts:
            manager = host()
            self.assertEqual(manager.verify_installed(self.package, 'main.js'), b'export default {start(){}}')
            contracts.assert_not_called()
            self.assertIs(manager.contracts, manager.contracts)
            contracts.assert_called_once()
            with self.assertRaises(ModuleFailure):
                manager.contracts.validate('schemas/manifest.json', {'invalid': True})
        self.assertIsNone(host().verify_installed(self.package))
        with self.assertRaises(ModuleFailure):
            host().verify_installed(self.package, 'missing.js')

    def test_metadata_projection_does_not_load_or_expose_database_document_bodies(self):
        from .models import Entry, Pack
        pack = Pack.objects.create(campaign=self.campaign, name='Database index', system_id=SYSTEM)
        entry = Entry.objects.create(pack=pack, name='Custom document', kind='item', bundle='private/archive.zip',
            data={'type': 'telemetry', 'data': {'private': 'opaque body', 'unfamiliarRule': {'operation': 'nothing'}}})
        seen = []
        from_db = Entry.from_db

        def capture(cls, db, fields, values):
            seen.append(set(fields))
            return from_db(db, fields, values)

        with patch.object(Entry, 'from_db', classmethod(capture)):
            packs = self.state()['packs']
        indexed = next(value for value in packs if value['id'] == str(pack.pk))
        self.assertEqual(indexed['entries'], [{
            'id': str(entry.pk), 'name': 'Custom document', 'kind': 'item', 'type': 'telemetry', 'version': 1,
        }])
        self.assertTrue(seen)
        self.assertTrue(all(not fields & {'data', 'bundle'} for fields in seen))
        self.assertNotIn('opaque body', json.dumps(packs))
        for item in packs:
            self.assertEqual(set(item), {'id', 'name', 'shared', 'locked', 'version', 'systemId', 'entries'})
            for summary in item['entries']:
                self.assertEqual(set(summary), {'id', 'name', 'kind', 'type', 'version'})

    def test_all_installed_pack_kinds_preserve_arbitrary_registered_types_and_opaque_data(self):
        opaque = {'revision': 'custom-revision', 'powerGrid': {'state': ['a', 0, False]},
                  'ruleOptions': {'edition': 'unrecognized-and-opaque', 'concentration': 123}}
        packs = [dict(id=pack_type, label=pack_type, type=pack_type, entries=[{
            'id': pack_type + '-document', 'name': 'Opaque document', 'type': document_type,
            'systemId': SYSTEM, 'data': deepcopy(opaque),
        }]) for pack_type, document_type in (('actor_pack', 'entity'), ('item_pack', 'origin'), ('spell_pack', 'gear'))]
        self.install('0.2.0', collections={'alpha': {'name': 'Generic packs', 'packs': packs}})
        selected = ModuleSet.objects.get(campaign=self.campaign)
        host().configure(self.campaign.pk, {SYSTEM: '0.2.0'}, {}, selected.revision)
        summaries = [pack for pack in self.state()['packs'] if pack['name'].startswith('Generic packs / ')]
        self.assertEqual(len(summaries), 3)
        verified = ModulePackages.verify_installed
        with patch.object(ModulePackages, 'verify_installed', autospec=True, side_effect=verified) as verify, \
             patch.object(content, 'validate_collection', wraps=content.validate_collection) as validate:
            for pack in summaries:
                entry = pack['entries'][0]
                request_id = uuid.uuid4()
                payload = {'packId': pack['id'], 'ids': [entry['id']]}
                result = domain.command(self.campaign.pk, self.gm.pk, 'compendiums', 'read', payload, request_id)['entries'][0]
                self.assertEqual(result['data'], opaque)
                self.assertEqual(result['type'], entry['type'])
                self.assertEqual(entry['kind'], 'actor' if entry['type'] == 'entity' else 'item')
                access = DocumentAccess.objects.create(campaign=self.campaign, kind='compendiums',
                    resource_id=pack['id'], grants={'player': 'read'})
                self.assertEqual(domain.command(self.campaign.pk, self.player.pk, 'compendiums', 'read', payload, request_id)['entries'][0], result)
                access.grants = {'player': 'none'}
                access.save(update_fields=['grants'])
                self.assertNotIn(pack['id'], [row['id'] for row in self.state(self.player)['packs']])
                with self.assertRaises(domain.MapError) as denied:
                    domain.command(self.campaign.pk, self.player.pk, 'compendiums', 'read', payload, request_id)
                self.assertEqual(denied.exception.code, 'not_found')
            validate.assert_not_called()
        self.assertTrue(all(call.args[2] in {'content/alpha.json', 'content/beta.json'} for call in verify.call_args_list))

    def test_legacy_native_actor_without_type_uses_the_provider_default(self):
        from gravewright.actors.models import Actor
        directory = self.root / 'content' / 'legacy'
        directory.mkdir(parents=True)
        collection = {'name': 'Legacy', 'campaigns': [str(self.campaign.pk)], 'packs': [{
            'id': 'actors', 'label': 'Actors', 'type': 'actor_pack', 'entries': [{
                'id': 'legacy-entity', 'name': 'Legacy entity', 'systemId': SYSTEM,
                'data': {'customField': ['retained', 7]},
            }],
        }]}
        (directory / 'index.json').write_text(json.dumps(collection), encoding='utf-8')
        pack = next(pack for pack in self.state()['packs'] if pack['name'] == 'Legacy / Actors')
        result = domain.command(self.campaign.pk, self.gm.pk, 'compendiums', 'import',
            {'packId': pack['id'], 'id': 'legacy-entity'}, uuid.uuid4())
        actor = Actor.objects.get(pk=result['id'])
        self.assertEqual(actor.type, 'entity')
        self.assertEqual(actor.data, {'customField': ['retained', 7]})

    def test_database_actor_uses_provider_default_without_changing_explicit_legacy_types(self):
        from gravewright.actors.models import Actor
        from .models import Entry, Pack
        pack = Pack.objects.create(campaign=self.campaign, name='Generic actors', system_id=SYSTEM)
        entry = Entry.objects.create(pack=pack, name='Legacy entity', kind='actor',
            data={'name': 'Legacy entity', 'data': {'customField': ['retained', 7]}})
        result = domain.command(self.campaign.pk, self.gm.pk, 'compendiums', 'import',
            {'packId': str(pack.pk), 'id': str(entry.pk)}, uuid.uuid4())
        actor = Actor.objects.get(pk=result['id'])
        self.assertEqual(actor.type, 'entity')
        self.assertEqual(actor.data, {'customField': ['retained', 7]})
        entry.data['type'] = 'historical-entity'
        entry.save(update_fields=['data'])
        Package.objects.filter(pk=self.package.pk).update(revoked=True)
        copied=domain.command(self.campaign.pk, self.gm.pk, 'compendiums', 'import',
            {'packId': str(pack.pk), 'id': str(entry.pk)}, uuid.uuid4())
        self.assertEqual(Actor.objects.get(pk=copied['id']).type,'historical-entity')
        self.assertEqual(Actor.objects.count(), 2)

    def test_legacy_document_pack_kinds_share_metadata_and_read_permission_boundaries(self):
        directory = self.root / 'content' / 'legacy'
        directory.mkdir(parents=True)
        collection = {'name':'Legacy kinds','campaigns':[str(self.campaign.pk)],'packs':[
            {'id':pack_type,'label':pack_type,'type':pack_type,'entries':[{
                'id':'document','name':'Opaque document','type':'custom-document',
                'data':{'privateBody':{'onlyOnRead':True}},
            }]} for pack_type in catalog.KINDS
        ]}
        (directory / 'index.json').write_text(json.dumps(collection), encoding='utf-8')
        packs = [pack for pack in self.state()['packs'] if pack['name'].startswith('Legacy kinds / ')]
        expected = {pack['label']:pack['entries'][0] for pack in collection['packs']}
        self.assertEqual(len(packs),len(catalog.KINDS))
        for pack in packs:
            summary = pack['entries'][0]
            self.assertEqual(set(summary),{'id','name','kind','type','version'})
            self.assertNotIn('privateBody',json.dumps(pack))
            payload = {'packId':pack['id'],'ids':['document']}
            with self.assertRaises(domain.MapError):
                domain.command(self.campaign.pk,self.player.pk,'compendiums','read',payload,uuid.uuid4())
            grant = DocumentAccess.objects.create(campaign=self.campaign,kind='compendiums',
                resource_id=pack['id'],grants={'player':'read'})
            result = domain.command(self.campaign.pk,self.player.pk,'compendiums','read',payload,uuid.uuid4())
            self.assertEqual(result['entries'][0],expected[pack['name'].split(' / ')[-1]])
            grant.grants = {'player':'none'}
            grant.save(update_fields=['grants'])
            with self.assertRaises(domain.MapError):
                domain.command(self.campaign.pk,self.player.pk,'compendiums','read',payload,uuid.uuid4())
