"""Clock nodes retain delegated authority, scoped targets and atomic effects."""

from copy import deepcopy
import uuid
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from api import clocks as clock_api
from gravewright.campaigns.models import Membership
from gravewright.journals.services import JournalError
from gravewright.maps import blueprint_testing, services
from gravewright.maps.blueprint_clocks import (
    catalog, clock_scope, control_clock, effective_scene_id,
)
from gravewright.maps.blueprint_delays import invalid_reason
from gravewright.maps.blueprint_runtime import clean_native_blueprint
from gravewright.maps.blueprints import clean_blueprint, data_inputs, evaluate_graph, execution_outputs
from gravewright.maps.models import AutomationDelay, AutomationRun, Scene
from gravewright.table.models import ClockReceipt, ProgressClock

from . import test_builder_blueprints as fixtures
from . import test_blueprint_delays as delay_fixtures
from .test_blueprint_references import data, execution, node
from .test_blueprint_world import audience, chain


def clock_node(clock_id=None, **values):
    return node('clock', 'clockControl', **{'clockId': str(clock_id or uuid.uuid4()),
                                          'action': 'advance', 'amount': 1, **values})


def connected_amount(action='advance', amount=1, default=3):
    raw = chain(clock_node(action=action, amount=amount))
    graph = raw['graphs']['interact']
    graph['nodes'].append(node('amount', 'getVariable', scope='scene', name='Count', valueType='number', default=default))
    graph['edges'].append(data('amount', 'value', 'clock', 'amount'))
    return raw


class ClockBlueprintContractTests(SimpleTestCase):
    def test_actions_are_strict_v2_nodes_with_numeric_input_and_pure_evaluation(self):
        for action in ('advance', 'reduce', 'set', 'reset'):
            authored = clock_node(action=action)
            raw = chain(authored)
            before = deepcopy(raw)
            self.assertEqual(evaluate_graph(raw, 'interact', 'closed')['actions'], [authored])
            self.assertEqual(raw, before)
            self.assertEqual(data_inputs(authored), {'amount': 'number'})
            self.assertEqual(execution_outputs(authored), ('next',))
            raw['version'] = 1
            with self.assertRaises(services.MapError):
                clean_blueprint(raw)
        invalid = [clock_node(amount=value) for value in (True, 1.0, -1, 25, '1', None)]
        invalid += [clock_node(action=value) for value in ('add', '', None, False, [])]
        invalid += [clock_node(clockId=value) for value in ('bad', True, None)]
        invalid += [{**clock_node(), 'unexpected': True}]
        missing = clock_node()
        missing.pop('amount')
        invalid.append(missing)
        for authored in invalid:
            with self.subTest(node=authored), self.assertRaises(services.MapError):
                clean_blueprint(chain(authored))

    def test_connected_numeric_amount_replaces_default_without_rounding_fractional_values(self):
        raw = connected_amount(default=3.0)
        before = deepcopy(raw)
        evaluated = evaluate_graph(raw, 'interact', 'closed')
        self.assertEqual(evaluated['actions'][0]['amount'], 3)
        self.assertIs(type(evaluated['actions'][0]['amount']), int)
        self.assertIn('amount', evaluated['trace'])
        self.assertEqual(raw, before)
        for value in (-1, 25, 1.5):
            with self.subTest(value=value), self.assertRaises(services.MapError):
                evaluate_graph(connected_amount(default=value), 'interact', 'closed')
        text_source = connected_amount()
        text_source['graphs']['interact']['nodes'][-1].update(valueType='text', default='2')
        with self.assertRaises(services.MapError):
            clean_blueprint(text_source)

    def test_reset_does_not_read_a_connected_variable_with_a_different_live_type(self):
        raw = connected_amount(action='reset')
        result = evaluate_graph(raw, 'interact', 'closed', variables={
            'scene': {'Count': {'type': 'text', 'value': 'Do not read this'}}})
        self.assertEqual(result['actions'][0]['amount'], 1)
        self.assertNotIn('amount', result['trace'])

    def test_delayed_amount_uses_original_variable_snapshot_after_resume(self):
        raw = connected_amount()
        graph = raw['graphs']['interact']
        graph['nodes'].append(node('wait', 'delay', seconds=.1))
        graph['edges'] = [edge for edge in graph['edges'] if edge.get('kind') == 'data'] + [
            execution('event', 'wait'), execution('wait', 'clock')]
        first = evaluate_graph(raw, 'interact', 'closed', variables={'scene': {'Count': {'type': 'number', 'value': 4}}})
        resumed = evaluate_graph(raw, 'interact', 'closed', variables={'scene': {'Count': {'type': 'number', 'value': 20}}},
                                 continuation=first['delay']['continuation'])
        self.assertEqual(resumed['actions'][0]['amount'], 4)


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   ALLOWED_HOSTS=['testserver'], GRAVEWRIGHT_MAP_TILER='pillow', DYNAMIC_LIGHTING_ENABLED=True)
class ClockBlueprintRuntimeTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    command = fixtures.BuilderBlueprintTests.command
    due = delay_fixtures.DelayRuntimeTests.due

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.clock = ProgressClock.objects.create(campaign=self.campaign, name='PRIVATE_CLOCK_NAME',
                                                  segments=6, value=1, visibility='gm')

    def install(self, *actions):
        self.doc['doors'][0]['blueprint'] = chain(*actions)
        self.generated()

    def native_graph(self, *actions):
        self.door_object.data['blueprint'] = clean_native_blueprint(chain(*actions), self.campaign.pk, self.scene.pk)
        self.door_object.save(update_fields=['data'])

    def test_player_triggers_specific_private_clock_effect_without_receiving_clock_edit_access_or_values(self):
        self.install(clock_node(self.clock.pk, amount=2))
        request_id = uuid.uuid4()
        with patch('gravewright.realtime.dispatch.send') as send, self.captureOnCommitCallbacks(execute=True):
            response = self.command('closed', user=self.player, request_id=request_id)
        self.clock.refresh_from_db()
        self.assertEqual((self.clock.value, self.clock.version), (3, 2))
        self.assertFalse(self.clock.players_can_edit)
        self.assertEqual(clock_api.state(self.campaign.pk, self.player.pk)['clocks'], [])
        self.assertNotIn(self.clock.name, str(response))
        self.assertNotIn(str(self.clock.pk), str(response))
        clock_events = [call.args[1] for call in send.call_args_list if call.args[1].get('module') == 'clocks']
        self.assertEqual(clock_events, [{'type': 'room.resources', 'module': 'clocks'}])
        receipt = ClockReceipt.objects.get()
        self.assertEqual(receipt.user_id, self.gm.pk)
        with self.assertRaises(services.MapError):
            clock_api.command(self.campaign.pk, self.player.pk, 'advance', {
                'id': str(self.clock.pk), 'version': 2, 'delta': 1}, uuid.uuid4())
        self.command('closed', user=self.player, request_id=request_id)
        self.clock.refresh_from_db()
        self.assertEqual((self.clock.value, self.clock.version, ClockReceipt.objects.count()), (3, 2, 1))
        step = AutomationRun.objects.filter(scene=self.scene).latest('created_at').data['events'][0]['steps'][-1]
        self.assertEqual((step['clockId'], step['action'], step['amount'], step['before'], step['value'], step['changed']),
                         (str(self.clock.pk), 'advance', 2, 1, 3, True))
        self.assertNotIn(self.clock.name, str(step))

    def test_advance_reduce_set_reset_and_clamping_use_clock_service_and_skip_noops(self):
        self.install(clock_node(self.clock.pk, amount=24))
        self.command('closed', user=self.player)
        self.clock.refresh_from_db()
        self.assertEqual((self.clock.value, self.clock.version), (6, 2))
        self.command('closed', user=self.player)
        self.clock.refresh_from_db()
        self.assertEqual((self.clock.value, self.clock.version, ClockReceipt.objects.count()), (6, 2, 1))
        for action, amount, expected in (('reduce', 2, 4), ('set', 24, 6), ('reset', 24, 0), ('reduce', 24, 0)):
            self.native_graph(clock_node(self.clock.pk, action=action, amount=amount))
            self.command('closed', user=self.player)
            self.clock.refresh_from_db()
            self.assertEqual(self.clock.value, expected)
        self.assertEqual(ClockReceipt.objects.count(), 4)

    def test_foreign_campaign_and_other_scene_bindings_are_rejected_at_save_and_execution(self):
        self.install()
        other_scene = Scene.objects.create(campaign=self.campaign, name='Other scope', width=100, height=100)
        foreign = ProgressClock.objects.create(campaign=self.other, name='Foreign clock')
        other = ProgressClock.objects.create(campaign=self.campaign, scene=other_scene, name='Other-scene clock')
        for clock in (foreign, other):
            authored = clock_node(clock.pk)
            with self.subTest(clock=clock.pk), self.assertRaisesMessage(services.MapError, 'campaign and scene'):
                clean_native_blueprint(chain(authored), self.campaign.pk, self.scene.pk)
            with self.assertRaisesMessage(services.MapError, 'campaign and scene'):
                control_clock(self.scene, self.membership, authored)
        missing = clock_node()
        clean_native_blueprint(chain(missing), self.campaign.pk, self.scene.pk)
        with self.assertRaisesMessage(services.MapError, 'campaign and scene'):
            control_clock(self.scene, self.membership, missing)
        self.assertFalse(ClockReceipt.objects.exists())

    def test_current_scene_scoped_clock_is_available_and_catalog_remains_gm_only(self):
        self.install()
        scoped = ProgressClock.objects.create(campaign=self.campaign, scene=self.scene, name='Scene clock')
        other_scene = Scene.objects.create(campaign=self.campaign, name='Other scope', width=100, height=100)
        other = ProgressClock.objects.create(campaign=self.campaign, scene=other_scene, name='Other-scene clock')
        foreign = ProgressClock.objects.create(campaign=self.other, name='Foreign clock')
        self.native_graph(clock_node(scoped.pk))
        self.command('closed', user=self.player)
        scoped.refresh_from_db()
        self.assertEqual(scoped.value, 1)
        self.assertEqual({row['id'] for row in catalog(self.membership, self.scene.pk)}, {str(self.clock.pk), str(scoped.pk)})
        self.assertEqual({row['id'] for row in catalog(self.membership, all_scenes=True)},
                         {str(self.clock.pk), str(scoped.pk), str(other.pk)})
        self.assertNotIn(str(foreign.pk), str(catalog(self.membership, all_scenes=True)))
        player = Membership.objects.get(campaign=self.campaign, user=self.player)
        with self.assertRaises(services.MapError):
            catalog(player, self.scene.pk)

    def test_streamers_and_events_without_an_active_gm_cannot_use_delegated_effects(self):
        self.install(clock_node(self.clock.pk))
        with self.assertRaises(JournalError):
            self.command('closed', user=self.streamer)
        streamer = Membership.objects.get(campaign=self.campaign, user=self.streamer)
        with self.assertRaises(services.MapError):
            control_clock(self.scene, streamer, clock_node(self.clock.pk))
        Membership.objects.filter(pk=self.membership.pk).update(role='player')
        with self.assertRaisesMessage(services.MapError, 'active campaign GM'):
            self.command('closed', user=self.player)
        self.clock.refresh_from_db()
        self.assertEqual((self.clock.value, self.clock.version), (1, 1))
        self.assertFalse(ClockReceipt.objects.exists())

    def test_authority_revoked_during_the_effect_surfaces_as_a_native_permission_error(self):
        self.install(clock_node(self.clock.pk))
        with patch('gravewright.maps.blueprint_clocks.clocks.public_command',
                   side_effect=JournalError('You no longer have access to this table.', 'not_a_member')):
            with self.assertRaises(services.MapError) as rejected:
                self.command('closed', user=self.player)
        self.assertEqual(rejected.exception.code, 'not_a_member')
        self.clock.refresh_from_db()
        self.assertEqual((self.clock.value, self.clock.version), (1, 1))
        self.assertFalse(ClockReceipt.objects.exists())

    def test_later_failure_rolls_back_clock_receipt_progress_and_notifications(self):
        self.install(clock_node(self.clock.pk),
                     node('outside', 'cameraFocus', focusX=1000, focusY=1000, audience=audience()))
        with patch('gravewright.realtime.dispatch.send') as send, self.captureOnCommitCallbacks(execute=True):
            with self.assertRaisesMessage(services.MapError, 'outside the map'):
                self.command('closed', user=self.player)
        self.clock.refresh_from_db()
        self.assertEqual((self.clock.value, self.clock.version), (1, 1))
        self.assertFalse(ClockReceipt.objects.exists())
        self.assertFalse(any(call.args[1].get('module') == 'clocks' for call in send.call_args_list))

    def test_rehearsal_reports_prediction_and_rolls_back_progress_receipt_and_notifications(self):
        self.install(clock_node(self.clock.pk, action='set', amount=5))
        with patch('gravewright.realtime.dispatch.send') as send, self.captureOnCommitCallbacks(execute=True):
            result = blueprint_testing.run(self.campaign.pk, self.gm.pk, self.scene.pk, self.door_object.pk, {
                'request_id': str(uuid.uuid4()), 'event': 'interact', 'expected_version': self.door_object.version})
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['changes']['clocks'], [{'id': str(self.clock.pk),
            'before': {'name': self.clock.name, 'value': 1, 'segments': 6, 'version': 1},
            'after': {'name': self.clock.name, 'value': 5, 'segments': 6, 'version': 2}}])
        self.clock.refresh_from_db()
        self.assertEqual((self.clock.value, self.clock.version), (1, 1))
        self.assertFalse(ClockReceipt.objects.exists())
        send.assert_not_called()

    def test_delayed_clock_effect_completes_once_and_retry_does_not_schedule_again(self):
        self.install(node('wait', 'delay', seconds=.1), clock_node(self.clock.pk, amount=2))
        request_id = uuid.uuid4()
        self.command('closed', user=self.player, request_id=request_id)
        self.command('closed', user=self.player, request_id=request_id)
        job = AutomationDelay.objects.get(status='pending')
        self.assertIsNone(invalid_reason(job))
        self.assertFalse(ClockReceipt.objects.exists())
        self.assertEqual(self.due(job)['completed'], 1)
        self.clock.refresh_from_db()
        self.assertEqual((self.clock.value, self.clock.version, ClockReceipt.objects.count()), (3, 2, 1))
        self.assertEqual(self.due(job)['completed'], 0)
        self.assertEqual(ClockReceipt.objects.count(), 1)

    def test_delayed_clock_target_deletion_or_scope_change_cancels_without_effect(self):
        self.install(node('wait', 'delay', seconds=.1), clock_node(self.clock.pk))
        self.command('closed', user=self.player)
        job = AutomationDelay.objects.get(status='pending')
        other_scene = Scene.objects.create(campaign=self.campaign, name='Moved scope', width=100, height=100)
        ProgressClock.objects.filter(pk=self.clock.pk).update(scene=other_scene)
        self.assertEqual(invalid_reason(job), 'A delayed blueprint target is missing.')
        self.assertEqual(self.due(job)['cancelled'], 1)
        self.assertFalse(ClockReceipt.objects.exists())
        ProgressClock.objects.filter(pk=self.clock.pk).update(scene=None)
        self.command('closed', user=self.player)
        job = AutomationDelay.objects.get(status='pending')
        self.clock.delete()
        self.assertEqual(invalid_reason(job), 'A delayed blueprint target is missing.')
        self.assertEqual(self.due(job)['cancelled'], 1)

    def test_draft_rehearsal_uses_only_the_authorized_project_scene_scope(self):
        self.install()
        scoped = ProgressClock.objects.create(campaign=self.campaign, scene=self.scene, name='Original scene clock')
        self.doc['doors'][0]['blueprint'] = chain(clock_node(scoped.pk, amount=2))
        payload = {'request_id': str(uuid.uuid4()), 'document': self.doc,
                   'elementId': self.doc['doors'][0]['id'], 'event': 'interact', 'projectId': str(self.project_id)}
        result = blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, payload)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['changes']['clocks'][0]['id'], str(scoped.pk))
        self.assertEqual(result['changes']['clocks'][0]['after']['value'], 2)
        scoped.refresh_from_db()
        self.assertEqual((scoped.value, scoped.version), (0, 1))
        self.assertFalse(ClockReceipt.objects.exists())
        without_project = {key: value for key, value in payload.items() if key != 'projectId'}
        with self.assertRaisesMessage(services.MapError, 'campaign and scene'):
            blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, without_project)
        self.assertEqual(effective_scene_id(self.scene.pk), str(self.scene.pk))

    def test_explicit_campaign_scope_context_is_nested_and_never_bypasses_campaign_isolation(self):
        self.install()
        scoped = ProgressClock.objects.create(campaign=self.campaign, scene=self.scene, name='Scene clock')
        foreign_scene = Scene.objects.create(campaign=self.other, name='Foreign scene', width=100, height=100)
        foreign = ProgressClock.objects.create(campaign=self.other, scene=foreign_scene, name='Foreign clock')
        with clock_scope(None):
            self.assertIsNone(effective_scene_id(self.scene.pk))
            with self.assertRaises(services.MapError):
                clean_native_blueprint(chain(clock_node(scoped.pk)), self.campaign.pk, self.scene.pk)
            with clock_scope(self.scene.pk):
                clean_native_blueprint(chain(clock_node(scoped.pk)), self.campaign.pk, self.scene.pk)
            self.assertIsNone(effective_scene_id(self.scene.pk))
        with clock_scope(foreign_scene.pk), self.assertRaises(services.MapError):
            control_clock(self.scene, self.membership, clock_node(foreign.pk))
        self.assertEqual(effective_scene_id(self.scene.pk), str(self.scene.pk))
