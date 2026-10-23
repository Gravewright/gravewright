"""Mind-map nodes preserve permissions, transactional effects and scoped bindings."""

from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.journals.services import member
from gravewright.maps import blueprint_network, blueprint_templates, blueprint_testing, builder_services, services
from gravewright.maps.blueprint_clocks import clock_scope
from gravewright.maps.blueprint_delays import invalid_reason
from gravewright.maps.blueprint_mindmaps import catalog, control_node
from gravewright.maps.blueprint_runtime import clean_native_blueprint
from gravewright.maps.blueprint_world import presentation_for
from gravewright.maps.blueprints import clean_blueprint, data_inputs, evaluate_graph, execution_outputs
from gravewright.maps.models import AutomationDelay, AutomationRun, MapBuilderProject, Scene
from gravewright.table import mindmaps
from gravewright.table.models import MindMap, MindMapReceipt

from . import test_blueprint_testing as fixtures
from . import test_blueprint_delays as delay_fixtures
from .test_blueprint_references import node
from .test_blueprint_world import audience, chain


def control(map_id=None, node_id=None, **patches):
    return node('topic', 'mindMapNode', **{'mindMapId': str(map_id or uuid4()),
                'nodeId': str(node_id or uuid4()), 'action': 'complete', **patches})


def opening(map_id=None, node_id=None, **patches):
    return node('open', 'openMindMap', **{'mindMapId': str(map_id or uuid4()),
                'nodeId': str(node_id) if node_id else None, 'audience': audience(), **patches})


class MindMapBlueprintContractTests(SimpleTestCase):
    def test_version_two_exact_nodes_have_no_untrusted_data_ports_and_pure_evaluation(self):
        for authored in (control(), opening(), opening(node_id=uuid4())):
            raw = chain(authored)
            before = deepcopy(raw)
            self.assertEqual(evaluate_graph(raw, 'interact', 'closed')['actions'], [authored])
            self.assertEqual(data_inputs(authored), {})
            self.assertEqual(execution_outputs(authored), ('next',))
            self.assertEqual(raw, before)
            raw['version'] = 1
            with self.assertRaises(services.MapError):
                clean_blueprint(raw)
        for authored in (control(action='delete'), control(nodeId=None), control(mindMapId=False),
                         opening(nodeId='bad'), opening(audience=audience('gm')), control(userId=str(uuid4()))):
            with self.subTest(node=authored), self.assertRaises(services.MapError):
                clean_blueprint(chain(authored))

    def test_templates_contain_typed_map_and_topic_slots_while_authored_text_is_untouched(self):
        map_id, topic_id = str(uuid4()), str(uuid4())
        raw = chain(opening(map_id), control(map_id, topic_id))
        for authored in raw['graphs']['interact']['nodes'][1:]:
            authored['mindMapId'] = {'binding': 'map'}
        raw['graphs']['interact']['nodes'][2]['nodeId'] = {'binding': 'topic'}
        template = {'version': 1, 'blueprint': raw, 'bindings': [
            {'id': 'map', 'type': 'mindmap', 'label': 'Map'},
            {'id': 'topic', 'type': 'mindmapTopic', 'label': 'Topic'}], 'parameters': []}
        clean = blueprint_templates.clean_definition(template)
        resolved = blueprint_templates.resolve_definition(clean, {'map': map_id, 'topic': topic_id}, owner_id=str(uuid4()))
        self.assertEqual(resolved['graphs']['interact']['nodes'][1]['nodeId'], None)
        self.assertEqual(resolved['graphs']['interact']['nodes'][2]['nodeId'], topic_id)


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   ALLOWED_HOSTS=['testserver'], GRAVEWRIGHT_MAP_TILER='pillow', DYNAMIC_LIGHTING_ENABLED=True)
class MindMapBlueprintRuntimeTests(TestCase):
    asset = fixtures.BlueprintTestingTests.asset
    post = fixtures.BlueprintTestingTests.post
    save = fixtures.BlueprintTestingTests.save
    generate = fixtures.BlueprintTestingTests.generate
    files = fixtures.BlueprintTestingTests.files
    generated = fixtures.BlueprintTestingTests.generated
    command = fixtures.BlueprintTestingTests.command
    draft = fixtures.BlueprintTestingTests.draft
    due = delay_fixtures.DelayRuntimeTests.due

    def setUp(self):
        fixtures.BlueprintTestingTests.setUp(self)
        self.topic_id = str(uuid4())
        self.graph = mindmaps.validate_document({'nodes': [{'id': self.topic_id, 'label': 'PRIVATE TOPIC',
            'notes': 'PRIVATE NOTES'}], 'edges': []})
        self.map = MindMap.objects.create(campaign=self.campaign, name='PRIVATE MAP', document=self.graph)

    def install(self, *actions):
        self.doc['doors'][0]['blueprint'] = chain(*actions)
        self.generated()

    def native_graph(self, *actions):
        self.door_object.data['blueprint'] = clean_native_blueprint(chain(*actions), self.campaign.pk, self.scene.pk)
        self.door_object.save(update_fields=['data'])

    def topic(self, **changes):
        return control(self.map.pk, self.topic_id, **changes)

    def test_player_trigger_delegates_only_authored_completion_and_receipt_retries_do_not_repeat_it(self):
        self.install(self.topic(action='toggle'))
        request_id = uuid4()
        response = self.command('closed', user=self.player, request_id=request_id)
        self.map.refresh_from_db()
        self.assertTrue(self.map.document['nodes'][0]['completed'])
        self.assertEqual((self.map.version, MindMapReceipt.objects.count()), (2, 1))
        self.assertEqual(MindMapReceipt.objects.get().user_id, self.gm.pk)
        self.assertNotIn('PRIVATE', str(response))
        self.assertNotIn(str(self.map.pk), str(response))
        self.assertEqual(mindmaps.public_state(self.campaign.pk, self.player.pk)['mindmaps'], [])
        self.command('closed', user=self.player, request_id=request_id)
        self.map.refresh_from_db()
        self.assertTrue(self.map.document['nodes'][0]['completed'])
        self.assertEqual(MindMapReceipt.objects.count(), 1)
        step = AutomationRun.objects.filter(scene=self.scene).latest('created_at').data['events'][0]['steps'][-1]
        self.assertEqual((step['before'], step['completed'], step['action']), (False, True, 'toggle'))
        self.assertNotIn('PRIVATE', str(step))

    def test_complete_reset_toggle_and_noop_use_native_service_without_authorizing_player_edits(self):
        self.install(self.topic())
        for action, expected, receipts in [('complete', True, 1), ('complete', True, 1),
                                            ('reset', False, 2), ('toggle', True, 3), ('toggle', False, 4)]:
            self.native_graph(self.topic(action=action))
            self.command('closed', user=self.player)
            self.map.refresh_from_db()
            self.assertEqual(self.map.document['nodes'][0]['completed'], expected)
            self.assertEqual(MindMapReceipt.objects.count(), receipts)
        with self.assertRaises(services.MapError):
            mindmaps.public_command(self.campaign.pk, self.player.pk, 'node', {'id': str(self.map.pk),
                'version': self.map.version, 'nodeId': self.topic_id, 'patch': {'completed': True}}, uuid4())

    def test_missing_topic_rolls_back_prior_effect_and_receipts(self):
        self.install(self.topic(), control(self.map.pk, uuid4(), id='missing'))
        with self.assertRaises(services.MapError):
            self.command('closed', user=self.player)
        self.map.refresh_from_db()
        self.assertFalse(self.map.document['nodes'][0]['completed'])
        self.assertEqual((self.map.version, MindMapReceipt.objects.count()), (1, 0))

    def test_foreign_and_different_scene_references_reject_but_deleted_bindings_remain_repairable(self):
        self.install()
        other_scene = Scene.objects.create(campaign=self.campaign, name='Another scope', width=100, height=100)
        for row in (MindMap.objects.create(campaign=self.other, name='Foreign', document=self.graph),
                    MindMap.objects.create(campaign=self.campaign, scene=other_scene, name='Other scene', document=self.graph)):
            with self.subTest(row=row.pk), self.assertRaises(services.MapError):
                clean_native_blueprint(chain(control(row.pk, self.topic_id)), self.campaign.pk, self.scene.pk)
        clean_native_blueprint(chain(control(uuid4(), uuid4())), self.campaign.pk, self.scene.pk)
        with self.assertRaises(services.MapError):
            control_node(self.scene, member(self.campaign.pk, self.streamer.pk), self.topic())

    def test_open_rechecks_live_permissions_and_topics_without_grants_or_private_payloads(self):
        self.install(opening(self.map.pk, self.topic_id, audience=audience('players')))
        with patch('gravewright.realtime.dispatch.send') as send, self.captureOnCommitCallbacks(execute=True):
            self.command('closed', user=self.player)
        presentations = [call.args[1] for call in send.call_args_list if call.args[1]['type'] == 'room.automation_presentation']
        self.assertEqual(presentations, [])
        self.map.visibility = 'players'
        self.map.save(update_fields=['visibility'])
        with patch('gravewright.realtime.dispatch.send') as send, self.captureOnCommitCallbacks(execute=True):
            self.command('closed', user=self.player)
        presentations = [call.args[1] for call in send.call_args_list if call.args[1]['type'] == 'room.automation_presentation']
        self.assertEqual(len(presentations), 1)
        payload = presentations[0]['payload']
        self.assertEqual((payload['type'], payload['mindMapId'], payload['nodeId']), ('mindmap', str(self.map.pk), self.topic_id))
        self.assertNotIn('PRIVATE', str(payload))
        self.assertIsNotNone(presentation_for(self.campaign.pk, self.player.pk, payload))
        self.map.visibility = 'gm'
        self.map.save(update_fields=['visibility'])
        self.assertIsNone(presentation_for(self.campaign.pk, self.player.pk, payload))
        self.assertIsNone(presentation_for(self.campaign.pk, self.gm.pk, {**payload, 'nodeId': str(uuid4())}))

    def test_catalogs_are_gm_only_scoped_and_do_not_include_notes_or_links(self):
        self.install()
        local = MindMap.objects.create(campaign=self.campaign, scene=self.scene, name='Local', document=self.graph)
        other_scene = Scene.objects.create(campaign=self.campaign, name='Other', width=100, height=100)
        other = MindMap.objects.create(campaign=self.campaign, scene=other_scene, name='Other', document=self.graph)
        self.assertEqual({row['id'] for row in blueprint_network.state(self.campaign.pk, self.gm.pk, self.scene.pk)['mindmaps']},
                         {str(self.map.pk), str(local.pk)})
        self.assertEqual({row['id'] for row in builder_services.catalog(self.campaign.pk, self.gm.pk)['mindmaps']},
                         {str(self.map.pk), str(local.pk), str(other.pk)})
        self.assertNotIn('PRIVATE NOTES', str(catalog(member(self.campaign.pk, self.gm.pk), self.scene.pk)))
        with self.assertRaises(services.MapError):
            catalog(member(self.campaign.pk, self.player.pk), self.scene.pk)

    def test_native_and_scoped_draft_rehearsals_report_completion_and_rollback_every_effect(self):
        self.install(self.topic(), opening(self.map.pk))
        self.map.scene = self.scene
        self.map.save(update_fields=['scene'])
        result = blueprint_testing.run(self.campaign.pk, self.gm.pk, self.scene.pk, self.door_object.pk, {
            'request_id': str(uuid4()), 'event': 'interact', 'expected_version': self.door_object.version})
        self.assertTrue(result['ok'])
        self.assertEqual(len(result['changes']['mindmaps']), 1)
        self.assertIn('presentation-not-delivered', result['warnings'])
        self.map.refresh_from_db()
        self.assertFalse(self.map.document['nodes'][0]['completed'])
        self.assertEqual(MindMapReceipt.objects.count(), 0)
        with clock_scope(self.scene.pk):
            result = blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, self.draft(projectId=str(self.project_id)))
        self.assertTrue(result['ok'])
        self.assertEqual(len(result['changes']['mindmaps']), 1)
        self.map.refresh_from_db()
        self.assertEqual(self.map.version, 1)
        self.assertFalse(self.map.document['nodes'][0]['completed'])

    def test_delayed_topic_effect_runs_once_and_deleted_topics_cancel_the_continuation(self):
        self.install(node('wait', 'delay', seconds=.1), self.topic(action='toggle'))
        request_id = uuid4()
        self.command('closed', user=self.player, request_id=request_id)
        self.command('closed', user=self.player, request_id=request_id)
        job = AutomationDelay.objects.get(status='pending')
        self.assertIsNone(invalid_reason(job))
        self.assertEqual(self.due(job)['completed'], 1)
        self.assertEqual(self.due(job)['completed'], 0)
        self.map.refresh_from_db()
        self.assertTrue(self.map.document['nodes'][0]['completed'])
        self.assertEqual(MindMapReceipt.objects.count(), 1)
        self.command('closed', user=self.player)
        job = AutomationDelay.objects.get(status='pending')
        self.map.document['nodes'] = []
        self.map.save(update_fields=['document'])
        self.assertEqual(invalid_reason(job), 'A delayed blueprint target is missing.')
        self.assertEqual(self.due(job)['cancelled'], 1)
        self.assertEqual(MindMapReceipt.objects.count(), 1)

    def test_native_network_edits_preserve_scene_scoped_bindings_in_the_linked_project(self):
        self.install(self.topic())
        self.map.scene = self.scene
        self.map.save(update_fields=['scene'])
        project = MapBuilderProject.objects.get(pk=self.project_id)
        result = blueprint_network.save(self.campaign.pk, self.gm.pk, self.scene.pk, self.door_object.pk, {
            'request_id': str(uuid4()), 'expected_version': self.door_object.version,
            'expected_project_version': project.version, 'blueprint': chain(self.topic(action='toggle'))})
        project.refresh_from_db()
        self.assertEqual(project.document['doors'][0]['blueprint']['graphs']['interact']['nodes'][1]['action'], 'toggle')
        self.assertEqual(result['projectVersion'], project.version)
