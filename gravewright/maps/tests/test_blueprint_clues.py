"""Clue nodes delegate one GM-authored discovery effect without leaking notes."""

from copy import deepcopy
import uuid
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from api import clues as clue_api
from gravewright.campaigns.models import Membership
from gravewright.journals.services import JournalError
from gravewright.maps import blueprint_testing, services
from gravewright.maps.blueprint_clocks import clock_scope, effective_scene_id
from gravewright.maps.blueprint_clues import catalog, control_clue
from gravewright.maps.blueprint_delays import invalid_reason
from gravewright.maps.blueprint_runtime import clean_native_blueprint
from gravewright.maps.blueprints import clean_blueprint, data_inputs, evaluate_graph, execution_outputs
from gravewright.maps.models import AutomationDelay, AutomationRun, Scene
from gravewright.table.models import ClueReceipt, ProgressClue

from . import test_builder_blueprints as fixtures
from . import test_blueprint_delays as delay_fixtures
from .test_blueprint_references import data, execution, node
from .test_blueprint_world import audience, chain


def clue_node(clue_id=None, **values):
    return node('clue', 'clueControl', **{'clueId': str(clue_id or uuid.uuid4()),
                                        'action': 'advance', 'amount': 1, **values})


def connected_amount(action='advance', default=3):
    raw = chain(clue_node(action=action))
    graph = raw['graphs']['interact']
    graph['nodes'].append(node('amount', 'getVariable', scope='scene', name='Count', valueType='number', default=default))
    graph['edges'].append(data('amount', 'value', 'clue', 'amount'))
    return raw


class ClueBlueprintContractTests(SimpleTestCase):
    def test_six_actions_have_only_numeric_amount_and_pure_v2_evaluation(self):
        for action in ('advance', 'reduce', 'set', 'reset', 'reveal', 'hide'):
            authored = clue_node(action=action)
            raw = chain(authored)
            before = deepcopy(raw)
            self.assertEqual(evaluate_graph(raw, 'interact', 'closed')['actions'], [authored])
            self.assertEqual(raw, before)
            self.assertEqual(data_inputs(authored), {'amount': 'number'})
            self.assertEqual(execution_outputs(authored), ('next',))
            raw['version'] = 1
            with self.assertRaises(services.MapError):
                clean_blueprint(raw)
        invalid = [clue_node(amount=value) for value in (True, 1.0, -1, 25, '1', None)]
        invalid += [clue_node(action=value) for value in ('add', '', None, False, [])]
        invalid += [clue_node(clueId=value) for value in ('bad', True, None)]
        invalid += [{**clue_node(), 'unexpected': True}]
        missing = clue_node()
        missing.pop('amount')
        invalid.append(missing)
        for authored in invalid:
            with self.subTest(node=authored), self.assertRaises(services.MapError):
                clean_blueprint(chain(authored))

    def test_connected_amount_is_bounded_whole_number_and_ignored_for_reset_reveal_hide(self):
        raw = connected_amount(default=3.0)
        before = deepcopy(raw)
        result = evaluate_graph(raw, 'interact', 'closed')
        self.assertEqual(result['actions'][0]['amount'], 3)
        self.assertIs(type(result['actions'][0]['amount']), int)
        self.assertIn('amount', result['trace'])
        self.assertEqual(raw, before)
        for value in (-1, 25, 1.5):
            with self.subTest(value=value), self.assertRaises(services.MapError):
                evaluate_graph(connected_amount(default=value), 'interact', 'closed')
        for action in ('reset', 'reveal', 'hide'):
            result = evaluate_graph(connected_amount(action=action), 'interact', 'closed', variables={
                'scene': {'Count': {'type': 'text', 'value': 'Never evaluate this variable'}}})
            self.assertEqual(result['actions'][0]['amount'], 1)
            self.assertNotIn('amount', result['trace'])
        wrong_type = connected_amount()
        wrong_type['graphs']['interact']['nodes'][-1].update(valueType='text', default='2')
        with self.assertRaises(services.MapError):
            clean_blueprint(wrong_type)

    def test_delayed_amount_uses_the_original_variable_snapshot(self):
        raw = connected_amount()
        graph = raw['graphs']['interact']
        graph['nodes'].append(node('wait', 'delay', seconds=.1))
        graph['edges'] = [edge for edge in graph['edges'] if edge.get('kind') == 'data'] + [
            execution('event', 'wait'), execution('wait', 'clue')]
        first = evaluate_graph(raw, 'interact', 'closed', variables={'scene': {'Count': {'type': 'number', 'value': 4}}})
        resumed = evaluate_graph(raw, 'interact', 'closed', variables={'scene': {'Count': {'type': 'number', 'value': 20}}},
                                 continuation=first['delay']['continuation'])
        self.assertEqual(resumed['actions'][0]['amount'], 4)


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   ALLOWED_HOSTS=['testserver'], GRAVEWRIGHT_MAP_TILER='pillow', DYNAMIC_LIGHTING_ENABLED=True)
class ClueBlueprintRuntimeTests(TestCase):
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
        self.clue = ProgressClue.objects.create(campaign=self.campaign, name='PRIVATE_CLUE_NAME',
            content='PRIVATE_CLUE_CONTENT', gm_notes='PRIVATE_CLUE_NOTES', segments=6, value=1, visibility='gm')

    def install(self, *actions):
        self.doc['doors'][0]['blueprint'] = chain(*actions)
        self.generated()

    def native_graph(self, *actions):
        self.door_object.data['blueprint'] = clean_native_blueprint(chain(*actions), self.campaign.pk, self.scene.pk)
        self.door_object.save(update_fields=['data'])

    def test_player_triggers_private_progress_without_general_edit_authority_or_private_acknowledgement(self):
        self.install(clue_node(self.clue.pk, amount=2))
        request_id = uuid.uuid4()
        with patch('gravewright.realtime.dispatch.send') as send, self.captureOnCommitCallbacks(execute=True):
            response = self.command('closed', user=self.player, request_id=request_id)
        self.clue.refresh_from_db()
        self.assertEqual((self.clue.value, self.clue.version), (3, 2))
        self.assertEqual(clue_api.state(self.campaign.pk, self.player.pk)['clues'], [])
        for secret in (self.clue.name, self.clue.content, self.clue.gm_notes, str(self.clue.pk)):
            self.assertNotIn(secret, str(response))
        clue_events = [call.args[1] for call in send.call_args_list if call.args[1].get('module') == 'clues']
        self.assertEqual(clue_events, [{'type': 'room.resources', 'module': 'clues'}])
        self.assertEqual(ClueReceipt.objects.get().user_id, self.gm.pk)
        with self.assertRaises(services.MapError):
            clue_api.command(self.campaign.pk, self.player.pk, 'advance', {
                'id': str(self.clue.pk), 'version': 2, 'delta': 1}, uuid.uuid4())
        self.command('closed', user=self.player, request_id=request_id)
        self.clue.refresh_from_db()
        self.assertEqual((self.clue.value, self.clue.version, ClueReceipt.objects.count()), (3, 2, 1))
        step = AutomationRun.objects.filter(scene=self.scene).latest('created_at').data['events'][0]['steps'][-1]
        self.assertEqual((step['clueId'], step['before'], step['value'], step['changed']), (str(self.clue.pk), 1, 3, True))
        self.assertNotIn(self.clue.content, str(step))
        self.assertNotIn(self.clue.gm_notes, str(step))

    def test_progress_actions_clamp_and_skip_noops_while_reveal_hide_change_visibility(self):
        self.install(clue_node(self.clue.pk, amount=24))
        self.command('closed', user=self.player)
        self.clue.refresh_from_db()
        self.assertEqual((self.clue.value, self.clue.visibility), (6, 'gm'))
        self.command('closed', user=self.player)
        self.assertEqual(ClueReceipt.objects.count(), 1)
        expected_receipts = 1
        for action, amount, value, visibility, changed in (
            ('reduce', 2, 4, 'gm', True), ('set', 24, 6, 'gm', True),
            ('reveal', 0, 6, 'players', True), ('reveal', 24, 6, 'players', False),
            ('hide', 0, 6, 'gm', True), ('hide', 24, 6, 'gm', False),
            ('reset', 24, 0, 'gm', True), ('reduce', 24, 0, 'gm', False),
            ('reveal', 0, 6, 'players', True), ('reset', 0, 0, 'players', True),
        ):
            self.native_graph(clue_node(self.clue.pk, action=action, amount=amount))
            self.command('closed', user=self.player)
            self.clue.refresh_from_db()
            expected_receipts += int(changed)
            self.assertEqual((self.clue.value, self.clue.visibility), (value, visibility))
            self.assertEqual(ClueReceipt.objects.count(), expected_receipts)
            public = clue_api.state(self.campaign.pk, self.player.pk)['clues']
            self.assertEqual(bool(public), value == 6 and visibility == 'players')
            self.assertNotIn('gmNotes', str(public))
            self.assertNotIn(self.clue.gm_notes, str(public))

    def test_foreign_scene_and_campaign_bindings_are_rejected_but_missing_portable_targets_are_inert(self):
        self.install()
        other_scene = Scene.objects.create(campaign=self.campaign, name='Other scope', width=100, height=100)
        foreign = ProgressClue.objects.create(campaign=self.other, name='Foreign clue')
        other = ProgressClue.objects.create(campaign=self.campaign, scene=other_scene, name='Other-scene clue')
        for clue in (foreign, other):
            authored = clue_node(clue.pk)
            with self.subTest(clue=clue.pk), self.assertRaisesMessage(services.MapError, 'campaign and scene'):
                clean_native_blueprint(chain(authored), self.campaign.pk, self.scene.pk)
            with self.assertRaisesMessage(services.MapError, 'campaign and scene'):
                control_clue(self.scene, self.membership, authored)
        missing = clue_node()
        clean_native_blueprint(chain(missing), self.campaign.pk, self.scene.pk)
        with self.assertRaisesMessage(services.MapError, 'campaign and scene'):
            control_clue(self.scene, self.membership, missing)

    def test_scene_scope_and_gm_catalog_filter_other_scenes_campaigns_content_and_notes(self):
        self.install()
        local = ProgressClue.objects.create(campaign=self.campaign, scene=self.scene, name='Scene clue')
        other_scene = Scene.objects.create(campaign=self.campaign, name='Other scene', width=100, height=100)
        other = ProgressClue.objects.create(campaign=self.campaign, scene=other_scene, name='Other-scene clue')
        foreign = ProgressClue.objects.create(campaign=self.other, name='Foreign clue')
        self.native_graph(clue_node(local.pk))
        self.command('closed', user=self.player)
        local.refresh_from_db()
        self.assertEqual(local.value, 1)
        choices = catalog(self.membership, self.scene.pk)
        self.assertEqual({row['id'] for row in choices}, {str(self.clue.pk), str(local.pk)})
        self.assertNotIn(self.clue.content, str(choices))
        self.assertNotIn(self.clue.gm_notes, str(choices))
        self.assertEqual({row['id'] for row in catalog(self.membership, all_scenes=True)},
                         {str(self.clue.pk), str(local.pk), str(other.pk)})
        self.assertNotIn(str(foreign.pk), str(catalog(self.membership, all_scenes=True)))
        with self.assertRaises(services.MapError):
            catalog(Membership.objects.get(campaign=self.campaign, user=self.player), self.scene.pk)

    def test_streamers_and_missing_or_revoked_gm_authority_cannot_apply_delegated_effects(self):
        self.install(clue_node(self.clue.pk))
        with self.assertRaises(JournalError):
            self.command('closed', user=self.streamer)
        with self.assertRaises(services.MapError):
            control_clue(self.scene, Membership.objects.get(campaign=self.campaign, user=self.streamer), clue_node(self.clue.pk))
        with patch('gravewright.maps.blueprint_clues.clues.public_command',
                   side_effect=JournalError('You no longer have access to this table.', 'not_a_member')):
            with self.assertRaises(services.MapError) as rejected:
                self.command('closed', user=self.player)
        self.assertEqual(rejected.exception.code, 'not_a_member')
        Membership.objects.filter(pk=self.membership.pk).update(role='player')
        with self.assertRaisesMessage(services.MapError, 'active campaign GM'):
            self.command('closed', user=self.player)
        self.clue.refresh_from_db()
        self.assertEqual((self.clue.value, self.clue.version), (1, 1))
        self.assertFalse(ClueReceipt.objects.exists())

    def test_failure_after_reveal_rolls_back_discovery_private_receipt_and_notifications(self):
        self.install(clue_node(self.clue.pk, action='reveal'),
                     node('outside', 'cameraFocus', focusX=1000, focusY=1000, audience=audience()))
        with patch('gravewright.realtime.dispatch.send') as send, self.captureOnCommitCallbacks(execute=True):
            with self.assertRaisesMessage(services.MapError, 'outside the map'):
                self.command('closed', user=self.player)
        self.clue.refresh_from_db()
        self.assertEqual((self.clue.value, self.clue.visibility, self.clue.version), (1, 'gm', 1))
        self.assertFalse(ClueReceipt.objects.exists())
        self.assertFalse(any(call.args[1].get('module') == 'clues' for call in send.call_args_list))

    def test_rehearsal_predicts_discovery_without_committing_or_exposing_notes_in_diff(self):
        self.install(clue_node(self.clue.pk, action='reveal'))
        with patch('gravewright.realtime.dispatch.send') as send, self.captureOnCommitCallbacks(execute=True):
            result = blueprint_testing.run(self.campaign.pk, self.gm.pk, self.scene.pk, self.door_object.pk, {
                'request_id': str(uuid.uuid4()), 'event': 'interact', 'expected_version': self.door_object.version})
        self.assertTrue(result['ok'], result)
        change = result['changes']['clues'][0]
        self.assertEqual((change['id'], change['before']['value'], change['after']['value'],
                          change['after']['visibility'], change['after']['discovered']), (str(self.clue.pk), 1, 6, 'players', True))
        self.assertNotIn(self.clue.content, str(change))
        self.assertNotIn(self.clue.gm_notes, str(change))
        self.clue.refresh_from_db()
        self.assertEqual((self.clue.value, self.clue.visibility, self.clue.version), (1, 'gm', 1))
        self.assertFalse(ClueReceipt.objects.exists())
        send.assert_not_called()

    def test_delay_completes_once_and_native_retry_does_not_schedule_or_reveal_twice(self):
        self.install(node('wait', 'delay', seconds=.1), clue_node(self.clue.pk, action='reveal'))
        request_id = uuid.uuid4()
        self.command('closed', user=self.player, request_id=request_id)
        self.command('closed', user=self.player, request_id=request_id)
        job = AutomationDelay.objects.get(status='pending')
        self.assertIsNone(invalid_reason(job))
        self.assertFalse(ClueReceipt.objects.exists())
        self.assertEqual(self.due(job)['completed'], 1)
        self.clue.refresh_from_db()
        self.assertEqual((self.clue.value, self.clue.visibility, self.clue.version), (6, 'players', 2))
        self.assertEqual(self.due(job)['completed'], 0)
        self.assertEqual(ClueReceipt.objects.count(), 1)

    def test_deleted_or_moved_delayed_clue_cancels_without_discovery(self):
        self.install(node('wait', 'delay', seconds=.1), clue_node(self.clue.pk, action='reveal'))
        self.command('closed', user=self.player)
        job = AutomationDelay.objects.get(status='pending')
        other_scene = Scene.objects.create(campaign=self.campaign, name='Moved scope', width=100, height=100)
        ProgressClue.objects.filter(pk=self.clue.pk).update(scene=other_scene)
        self.assertEqual(invalid_reason(job), 'A delayed blueprint target is missing.')
        self.assertEqual(self.due(job)['cancelled'], 1)
        self.assertFalse(ClueReceipt.objects.exists())
        ProgressClue.objects.filter(pk=self.clue.pk).update(scene=None)
        self.command('closed', user=self.player)
        job = AutomationDelay.objects.get(status='pending')
        self.clue.delete()
        self.assertEqual(invalid_reason(job), 'A delayed blueprint target is missing.')
        self.assertEqual(self.due(job)['cancelled'], 1)

    def test_draft_uses_authorized_original_project_scope_and_always_rolls_back(self):
        self.install()
        local = ProgressClue.objects.create(campaign=self.campaign, scene=self.scene, name='Original scene clue')
        self.doc['doors'][0]['blueprint'] = chain(clue_node(local.pk, action='reveal'))
        payload = {'request_id': str(uuid.uuid4()), 'document': self.doc,
                   'elementId': self.doc['doors'][0]['id'], 'event': 'interact', 'projectId': str(self.project_id)}
        result = blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, payload)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['changes']['clues'][0]['id'], str(local.pk))
        self.assertTrue(result['changes']['clues'][0]['after']['discovered'])
        local.refresh_from_db()
        self.assertEqual((local.value, local.version), (0, 1))
        self.assertFalse(ClueReceipt.objects.exists())
        with self.assertRaisesMessage(services.MapError, 'campaign and scene'):
            blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, {key: value for key, value in payload.items() if key != 'projectId'})
        self.assertEqual(effective_scene_id(self.scene.pk), str(self.scene.pk))

    def test_explicit_campaign_only_scope_never_turns_foreign_or_other_scene_targets_into_global_clues(self):
        self.install()
        local = ProgressClue.objects.create(campaign=self.campaign, scene=self.scene, name='Local clue')
        foreign_scene = Scene.objects.create(campaign=self.other, name='Foreign scene', width=100, height=100)
        foreign = ProgressClue.objects.create(campaign=self.other, scene=foreign_scene, name='Foreign clue')
        with clock_scope(None):
            with self.assertRaises(services.MapError):
                clean_native_blueprint(chain(clue_node(local.pk)), self.campaign.pk, self.scene.pk)
            with clock_scope(self.scene.pk):
                clean_native_blueprint(chain(clue_node(local.pk)), self.campaign.pk, self.scene.pk)
            self.assertIsNone(effective_scene_id(self.scene.pk))
        with clock_scope(foreign_scene.pk), self.assertRaises(services.MapError):
            control_clue(self.scene, self.membership, clue_node(foreign.pk))
        self.assertEqual(effective_scene_id(self.scene.pk), str(self.scene.pk))
