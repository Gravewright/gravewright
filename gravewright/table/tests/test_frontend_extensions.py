"""Extended browser capabilities share native authority and transaction scopes."""
import uuid
from unittest.mock import patch

from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings

from api import systems
from gravewright.campaigns import system_api
from gravewright.maps.models import AssetFolder, SceneNavigation
from gravewright.modules.frontend import invoke
from gravewright.modules.packages import ModuleFailure
from gravewright.table.tests import test_modules as fixtures


class BrowserCalls:
    setUp = fixtures.TableModuleTests.setUp

    def call(self, domain, method, payload=None, **extra):
        return self.client.post(f'/api/tables/{self.campaign.pk}/api', {
            'domain': domain, 'method': method, 'payload': payload or {},
            'requestId': str(uuid.uuid4()), **extra,
        }, content_type='application/json')


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ExtendedFrontendApiTests(BrowserCalls, TestCase):
    def test_map_domains_dispatch_only_explicit_methods_with_authoritative_context(self):
        request_id = uuid.uuid4()
        payload = {'projectId': str(uuid.uuid4()), 'expectedVersion': 4, 'expectedSceneVersion': 8}
        original = dict(payload)
        with patch('gravewright.maps.public.invoke', return_value={'ok': True}) as dispatch:
            result = invoke(self.campaign.pk, self.gm.pk, 'mapBuilder', 'sync', payload,
                            request_id, scene_id=self.scene.pk)
            self.assertEqual(result, {'ok': True})
            dispatch.assert_called_once_with(self.campaign.pk, self.gm.pk, 'mapBuilder', 'sync', {
                **payload, 'sceneId': str(self.scene.pk), 'mapId': str(self.scene.pk),
            }, request_id, scene_id=self.scene.pk)
            self.assertEqual(payload, original)
            for domain, method, attempted in (
                ('mapBuilder', '__dict__', {}), ('blueprints', 'execute', {}),
                ('mapBuilder', 'adopt', {'mapId': str(uuid.uuid4())}),
                ('maps', 'exportUniversalVtt', {'sceneId': str(uuid.uuid4())}),
            ):
                with self.subTest(domain=domain, method=method), self.assertRaises(ModuleFailure) as error:
                    invoke(self.campaign.pk, self.gm.pk, domain, method, attempted,
                           request_id, scene_id=self.scene.pk)
                self.assertIn(error.exception.code, ('unavailable', 'stale_context'))
            self.assertEqual(dispatch.call_count, 1)

    def test_map_catalogs_and_export_enforce_live_gm_authority(self):
        self.client.force_login(self.gm)
        for domain, method in (('mapBuilder', 'state'), ('blueprints', 'templates')):
            result = self.call(domain, method)
            self.assertEqual(result.status_code, 200, result.content)
        self.client.force_login(self.player)
        for domain, method, payload in (
            ('mapBuilder', 'state', {}), ('blueprints', 'templates', {}),
            ('maps', 'exportUniversalVtt', {'mapId': str(self.scene.pk)}),
        ):
            with self.subTest(domain=domain, method=method):
                result = self.call(domain, method, payload)
                self.assertEqual(result.status_code, 403, result.content)
        self.campaign.memberships.filter(user=self.player).delete()
        self.assertEqual(self.call('mapBuilder', 'state').status_code, 403)

    def test_map_navigation_accepts_explicit_return_to_broadcast(self):
        self.client.force_login(self.gm)
        response = self.call('maps', 'navigate', {'mapId': str(self.scene.pk)})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['value']['navigatingMapId'], str(self.scene.pk))
        response = self.call('maps', 'navigate', {'mapId': None})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(response.json()['value']['navigatingMapId'])
        self.assertIsNone(SceneNavigation.objects.get(membership__user=self.gm).scene_id)

    def test_system_discovery_and_invocation_use_session_identity_and_request_uuid(self):
        previous = dict(system_api._providers)
        self.addCleanup(lambda: (system_api._providers.clear(), system_api._providers.update(previous)))
        self.campaign.system = 'example.integration'
        self.campaign.save(update_fields=['system'])
        calls = []

        def handler(campaign_id, user_id, data, request_id, scene_id):
            calls.append((campaign_id, user_id, data, request_id, scene_id))
            return {'ok': True}

        systems.register_api('example.integration', {
            'example.read': {'effect': 'read', 'handler': handler},
        })
        self.client.force_login(self.player)
        discovery = self.call('system', 'state')
        self.assertEqual(discovery.status_code, 200, discovery.content)
        self.assertEqual(discovery.json()['value']['operations'], [
            {'name': 'example.read', 'effect': 'read', 'description': ''},
        ])
        request_id = uuid.uuid4()
        result = self.call('system', 'call', {'operation': 'example.read', 'data': {'field': 'value'}},
                           requestId=str(request_id))
        self.assertEqual(result.status_code, 200, result.content)
        self.assertEqual(calls, [(self.campaign.pk, self.player.pk, {'field': 'value'}, request_id, None)])
        self.assertEqual(self.call('system', 'call', {'operation': 'unknown', 'data': {}}).status_code, 404)
        self.assertEqual(self.call('system', '__dict__').status_code, 503)
        self.assertEqual(self.call('system', 'call', {'operation': 'example.read', 'data': []}).status_code, 400)
        self.assertEqual(len(calls), 1)
        with self.assertRaises(ModuleFailure) as error:
            invoke(self.campaign.pk, self.player.pk, 'system', 'call', {
                'operation': 'example.read', 'data': {'mapId': str(uuid.uuid4())},
            }, uuid.uuid4(), scene_id=self.scene.pk)
        self.assertEqual(error.exception.code, 'conflict')
        self.assertEqual(len(calls), 1)

    def test_library_folder_calls_retain_receipts_aliases_and_gm_permissions(self):
        self.client.force_login(self.gm)
        request_id = str(uuid.uuid4())
        created = self.call('library', 'createFolder', {'name': 'Synthetic library'}, requestId=request_id)
        self.assertEqual(created.status_code, 200, created.content)
        replay = self.call('library', 'createFolder', {'name': 'Synthetic library'}, requestId=request_id)
        self.assertEqual(replay.json(), created.json())
        self.assertEqual(AssetFolder.objects.filter(campaign=self.campaign).count(), 1)
        folder_id = created.json()['value']['id']
        renamed = self.call('library', 'updateFolder', {'folderId': folder_id, 'name': 'Renamed library'})
        self.assertEqual(renamed.status_code, 200, renamed.content)
        state = self.call('library', 'state')
        self.assertEqual(state.json()['value']['folders'], [{'id': folder_id, 'name': 'Renamed library'}])
        self.client.force_login(self.player)
        result = self.call('library', 'deleteFolder', {'folderId': folder_id})
        self.assertEqual(result.status_code, 403, result.content)
        self.assertTrue(AssetFolder.objects.filter(pk=folder_id).exists())
        self.assertEqual(self.call('library', 'state').json()['value']['folders'], [])
        self.client.force_login(self.gm)
        deleted = self.call('library', 'deleteFolder', {'folderId': folder_id})
        self.assertEqual(deleted.status_code, 200, deleted.content)
        self.assertFalse(AssetFolder.objects.filter(pk=folder_id).exists())

    def test_ownership_update_preserves_native_revision_payload_and_request_identity(self):
        payload = {'kind': 'actors', 'id': str(self.actor.pk), 'version': 8,
                   'permissions': {'default': 'read'}, 'reset': [str(self.player.pk)]}
        request_id = uuid.uuid4()
        with patch('api.ownership.command', return_value={'version': 9}) as command:
            result = invoke(self.campaign.pk, self.gm.pk, 'ownership', 'update', payload, request_id)
            self.assertEqual(result, {'version': 9})
            command.assert_called_once_with(self.campaign.pk, self.gm.pk, 'actors', str(self.actor.pk),
                                            payload, request_id)
        self.assertEqual(payload['version'], 8)
        with patch('api.ownership.command') as command:
            with self.assertRaises(ModuleFailure) as failure:
                invoke(self.campaign.pk, self.gm.pk, 'ownership', 'execute', payload, request_id)
            self.assertEqual(failure.exception.code, 'unavailable')
            command.assert_not_called()

    def test_ownership_reads_share_native_projection_and_live_gm_checks(self):
        self.client.force_login(self.gm)
        payload = {'kind': 'actors', 'id': str(self.actor.pk)}
        result = self.call('ownership', 'state', payload)
        self.assertEqual(result.status_code, 200, result.content)
        self.assertEqual(result.json()['value']['permissions'], {'default': 'none', **self.actor.permissions})
        self.assertEqual(result.json()['value']['id'], str(self.actor.pk))
        read = self.call('ownership', 'read', payload)
        self.assertEqual(read.json(), result.json())
        self.client.force_login(self.player)
        result = self.call('ownership', 'read', payload)
        self.assertEqual(result.status_code, 403, result.content)

    def test_bound_navigation_cannot_clear_its_authoritative_scene(self):
        for key in ('mapId', 'sceneId'):
            with self.subTest(key=key), patch('api.maps.command') as command:
                with self.assertRaises(ModuleFailure) as failure:
                    invoke(self.campaign.pk, self.gm.pk, 'maps', 'navigate', {key: None},
                           uuid.uuid4(), scene_id=self.scene.pk)
                self.assertEqual(failure.exception.code, 'stale_context')
                command.assert_not_called()


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class MapPreparationTransactionTests(BrowserCalls, TransactionTestCase):
    def test_http_dispatch_leaves_render_preparation_outside_write_transaction(self):
        self.client.force_login(self.gm)
        seen = []

        def prepare(*args, **kwargs):
            seen.append(connection.in_atomic_block)
            return {'prepared': True}

        with patch('gravewright.maps.public.invoke', side_effect=prepare):
            response = self.call('mapBuilder', 'generate', {
                'projectId': str(uuid.uuid4()), 'expectedVersion': 1,
            })
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(seen, [False])
