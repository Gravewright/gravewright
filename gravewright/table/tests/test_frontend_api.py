"""The domain browser interface must share the native permission/commit boundary."""
import json
import uuid
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, Client
from api import events
from gravewright.actors.models import Actor
from gravewright.campaigns.models import Campaign
from gravewright.table.tests import test_modules as fixtures
from gravewright.modules import tests as module_fixtures


class FrontendApiTests(TestCase):
    setUp = fixtures.TableModuleTests.setUp

    def call(self, domain, method, payload=None, **extra):
        return self.client.post(f'/api/tables/{self.campaign.pk}/api', {
            'domain': domain, 'method': method, 'payload': payload or {},
            'requestId': str(uuid.uuid4()), **extra,
        }, content_type='application/json')

    def test_all_domain_states_and_generated_contract(self):
        self.client.force_login(self.gm)
        from gravewright.modules.frontend import CONTRACT
        for domain in CONTRACT['domains']:
            with self.subTest(domain=domain):
                result = self.call(domain, 'state', {'sceneId': str(self.scene.pk)})
                self.assertEqual(result.status_code, 200, result.content)
        root = Path(__file__).resolve().parents[2] / 'modules'
        generated = (root / 'static/gravewright_modules/frontend-contract.js').read_text()
        self.assertEqual(generated.split('export const FRONTEND_CONTRACT = ', 1)[1], json.dumps(CONTRACT, indent=2) + ';\n')

    def test_actor_writes_publish_hooks_after_commit_and_replay_once(self):
        self.client.force_login(self.gm)
        changes = []
        def receiver(sender, change, **kwargs):
            changes.append(change)
        events.resource_changed.connect(receiver, weak=False)
        self.addCleanup(events.resource_changed.disconnect, receiver)
        rid = str(uuid.uuid4())
        with self.captureOnCommitCallbacks(execute=True), patch('gravewright.realtime.dispatch.send'):
            created = self.call('actors', 'create', {'name': 'Browser actor'}, requestId=rid)
            self.assertEqual(created.status_code, 200, created.content)
            self.assertEqual(changes, [])
        self.assertEqual(len(changes), 1)
        with self.captureOnCommitCallbacks(execute=True):
            replay = self.call('actors', 'create', {'name': 'Browser actor'}, requestId=rid)
        self.assertEqual(replay.json(), created.json())
        self.assertEqual(len(changes), 1)
        actor_id = created.json()['value']['id']
        for method, payload in [('update', {'id':actor_id, 'name':'Renamed actor', 'version':1}), ('delete', {'id':actor_id})]:
            with self.captureOnCommitCallbacks(execute=True), patch('gravewright.realtime.dispatch.send'):
                response = self.call('actors', method, payload)
                self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([c.action for c in changes], ['actor.create', 'actor.update', 'actor.delete'])

    def test_membership_identity_csrf_and_private_projection(self):
        self.assertEqual(self.call('actors', 'state').status_code, 401)
        Actor.objects.create(campaign=self.campaign, name='Private')
        self.client.force_login(self.player)
        response = self.call('actors', 'state')
        self.assertEqual([row['name'] for row in response.json()['value']['actors']], ['Hero'])
        self.assertEqual(self.call('actors', 'create', {'name':'Forbidden'}).status_code, 403)
        self.assertEqual(self.call('actors', 'state', userId=str(self.gm.pk)).status_code, 400)
        self.campaign.memberships.filter(user=self.player).delete()
        self.assertEqual(self.call('actors', 'state').status_code, 403)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.gm)
        self.assertEqual(csrf_client.post(f'/api/tables/{self.campaign.pk}/api', {}, content_type='application/json').status_code, 403)

    def test_rejects_unknown_methods_bad_ids_and_stale_writes(self):
        self.client.force_login(self.gm)
        for domain, method, payload in [('actors','__dict__',{}), ('__import__','state',{}), ('actors','update',{'id':'bad','version':1})]:
            response = self.call(domain, method, payload)
            self.assertIn(response.status_code, (400, 503), response.content)
        response = self.call('actors', 'update', {'id':str(self.actor.pk), 'version':999, 'name':'Stale'})
        self.assertEqual(response.status_code, 409)
        self.actor.refresh_from_db()
        self.assertEqual(self.actor.name, 'Hero')

    def test_chat_dice_and_lobby_share_native_services(self):
        self.client.force_login(self.gm)
        with self.captureOnCommitCallbacks(execute=True), patch('gravewright.realtime.dispatch.send'):
            response = self.call('chat', 'send', {'text':'Public hello'})
            self.assertEqual(response.status_code, 200, response.content)
            response = self.call('dice', 'roll', {'expression':'1d6','visibility':'gm'})
            self.assertEqual(response.status_code, 200, response.content)
        self.client.force_login(self.player)
        history = self.call('chat', 'history').json()['value']
        self.assertEqual(len(history), 1)
        self.assertEqual(self.call('chat', 'clear').status_code, 403)
        self.assertEqual(self.call('table', 'lobby').status_code, 200)


class MountedFrontendApiTests(TestCase):
    setUp = module_fixtures.ModuleTests.setUp
    package = module_fixtures.ModuleTests.package
    activate = module_fixtures.ModuleTests.activate

    def test_module_lease_revision_scene_and_closed_context(self):
        from gravewright.maps.models import Scene
        state = self.activate()
        scene = Scene.objects.create(campaign=self.campaign, name='First', width=100, height=100)
        other = Scene.objects.create(campaign=self.campaign, name='Second', width=100, height=100)
        base = f'/api/tables/{self.campaign.pk}/modules/example.test'
        identity = {'mountId':'frontend-mount', 'moduleSetRevision':state['moduleSetRevision'], 'sceneId':str(scene.pk)}
        data = {**identity, 'domain':'tokens', 'method':'state', 'payload':{}}
        response = self.client.post(base+'/api', data, content_type='application/json')
        self.assertEqual(response.status_code, 409)
        response = self.client.post(base+'/context', {**identity,'action':'open'}, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        response = self.client.post(base+'/api', data, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['value']['mapId'], str(scene.pk))
        response = self.client.post(base+'/api', {**data,'payload':{'mapId':str(other.pk)}}, content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.client.post(base+'/context', {'mountId':identity['mountId'],'action':'close'}, content_type='application/json')
        self.assertEqual(self.client.post(base+'/api', data, content_type='application/json').status_code, 409)
