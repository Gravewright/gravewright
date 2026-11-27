"""Batch initiative remains atomic, private and replayable under native contracts."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch
import uuid

from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from gravewright.actors.models import Actor
from gravewright.accounts.models import User
from gravewright.campaigns.models import Membership
from gravewright.chat.models import Message, Recipient, SendWindow
from gravewright.chat.services import history, public_message
from gravewright.dice.engine import evaluate_batch
from gravewright.dice.grammar.errors import RollError
from gravewright.maps.models import Receipt, Scene
from gravewright.maps.services import MapError
from gravewright.modules.frontend import invoke
from gravewright.modules.packages import ModuleFailure
from gravewright.table import domain
from gravewright.table.tests import test_modules as fixtures
from gravewright.tokens.models import Token
from .models import Encounter, InitiativeBatchReceipt


class InitiativeBatchTests(TestCase):
    def setUp(self):
        fixtures.TableModuleTests.setUp(self)
        self.actor.permissions['default'] = 'read';self.actor.save(update_fields=['permissions'])
        self.other = Actor.objects.create(campaign=self.campaign, name='Other', data={})
        self.hidden = Token.objects.create(scene=self.scene, actor=self.other, linked=False,
            snapshot={'token': {'name': 'Secret <name>'}}, hidden=True)
        self.encounter = Encounter.objects.create(scene=self.scene, active=True, round=3, turn=0,
            combatants=[{'tokenId': str(self.token.pk), 'initiative': None},
                        {'tokenId': str(self.hidden.pk), 'initiative': None},
                        {'actorId': str(self.actor.pk), 'initiative': None}],
            history=[{'round': 2, 'turn': 1, 'tokenId': str(self.hidden.pk)}],
            config={'formula': '1d20', '_encounter_id': str(uuid.uuid4())})

    def payload(self):
        self.encounter.refresh_from_db()
        return {'sceneId': str(self.scene.pk), 'version': self.encounter.version, 'label': 'Initiative',
            'entries': [
                {'tokenId': str(self.token.pk), 'expression': '1d1+3',
                 'source': {'actorVersion': self.actor.version, 'sheetVersion': self.actor.sheet_version,
                            'tokenVersion': self.token.version}},
                {'tokenId': str(self.hidden.pk), 'expression': '2d1+10', 'visibility': 'public',
                 'source': {'actorVersion': self.other.version, 'sheetVersion': self.hidden.sheet_version,
                            'tokenVersion': self.hidden.version}},
                {'actorId': str(self.actor.pk), 'expression': '4',
                 'source': {'actorVersion': self.actor.version, 'sheetVersion': self.actor.sheet_version}}]}

    def roll(self, payload=None, request_id=None, user=None):
        return domain.command(self.campaign.pk, (user or self.gm).pk, 'combat',
            'roll-initiative-batch', payload or self.payload(), request_id or uuid.uuid4())

    def unchanged(self, version=1):
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.version, version)
        self.assertEqual([entry['initiative'] for entry in self.encounter.combatants], [None, None, None])
        self.assertFalse(Message.objects.exists())
        self.assertFalse(InitiativeBatchReceipt.objects.exists())
        self.assertFalse(SendWindow.objects.exists())

    def test_batch_sorts_once_preserves_turn_and_groups_private_chat(self):
        before = deepcopy(self.encounter)
        with patch('gravewright.realtime.dispatch.send') as send, self.captureOnCommitCallbacks(execute=True):
            result = self.roll()
        self.assertEqual(result['version'], 2)
        self.assertEqual([entry['initiative'] for entry in result['combatants']], [12, 4, 4])
        self.assertEqual([entry['id'] for entry in result['combatants']],
                         [str(self.hidden.pk), str(self.token.pk), str(self.actor.pk)])
        self.assertEqual(result['combatants'][result['turn']]['id'], str(self.token.pk))
        self.encounter.refresh_from_db()
        self.assertEqual(self.encounter.history, before.history)
        self.assertEqual((self.encounter.round, self.encounter.config), (before.round, before.config))
        self.assertFalse(result['batch']['replayed'])
        self.assertEqual(len(result['batch']['messageIds']), 2)
        self.assertEqual(SendWindow.objects.get().count, 2)
        events = [call.args[1] for call in send.call_args_list]
        self.assertEqual([event['type'] for event in events].count('room.changes'), 1)
        self.assertEqual([event['type'] for event in events].count('room.message'), 2)
        public, secret = Message.objects.get(visibility='public'), Message.objects.get(visibility='gm')
        self.assertEqual([row['expression'] for row in public.roll['batch']], ['1d1+3', '4'])
        self.assertEqual(secret.roll['batch'][0]['label'], 'Secret <name>')
        self.assertEqual(set(Recipient.objects.filter(message=secret).values_list('user_id', flat=True)), {self.gm.pk})
        visible = history(self.campaign.pk, self.player.pk, str(self.scene.pk))
        self.assertEqual([message['id'] for message in visible], [str(public.pk)])
        self.assertNotIn('Secret', str(visible))
        html = public_message(public)['html']
        self.assertIn('1d1+3', html)
        self.assertIn('>4</code>', html)
        self.assertIn('&lt;name&gt;', public_message(secret)['html'])

    def test_select_first_preserves_round_identity_history_and_does_not_start_inactive_combat(self):
        payload = self.payload();payload['selectFirst'] = True
        result = self.roll(payload)
        self.assertEqual((result['turn'], result['round']), (0, 3))
        self.assertEqual(result['encounterId'], self.encounter.config['_encounter_id'])
        self.encounter.refresh_from_db();self.assertEqual(len(self.encounter.history), 1)
        self.encounter.active = False;self.encounter.round = 0;self.encounter.save()
        result = self.roll({**self.payload(), 'selectFirst': True})
        self.assertEqual((result['active'], result['round'], result['turn']), (False, 0, 0))

    def test_replay_after_lost_response_returns_current_projection_without_new_draws_or_events(self):
        payload, request_id = self.payload(), uuid.uuid4()
        with patch('gravewright.dice.grammar.runtime.secure_sample', return_value=0.25) as random:
            first = self.roll(payload, request_id)
            self.assertEqual(random.call_count, 3)
            self.encounter.refresh_from_db();self.encounter.turn = 0;self.encounter.version += 1;self.encounter.save()
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                replay = self.roll(payload, request_id)
            self.assertEqual(random.call_count, 3)
        self.assertEqual(callbacks, [])
        self.assertTrue(replay['batch']['replayed'])
        self.assertEqual(replay['batch']['results'], first['batch']['results'])
        self.assertEqual((replay['version'], replay['batch']['version']), (3, 2))
        self.assertEqual(replay['turn'], 0)
        self.assertEqual(Message.objects.count(), 2)
        self.assertEqual(InitiativeBatchReceipt.objects.count(), 1)
        self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())

    def test_uuid_cannot_change_payload_and_private_receipt_is_not_replayed_by_another_domain(self):
        payload, request_id = self.payload(), uuid.uuid4()
        self.roll(payload, request_id)
        changed = deepcopy(payload);changed['entries'][0]['expression'] = '999'
        with self.assertRaises(MapError):self.roll(changed, request_id)
        Membership.objects.filter(campaign=self.campaign, user=self.gm).update(role='player')
        with self.assertRaises(MapError) as denied:self.roll(payload, request_id)
        self.assertEqual(denied.exception.code, 'forbidden')
        with self.assertRaises(MapError):
            domain.command(self.campaign.pk, self.gm.pk, 'combat', 'start',
                {'sceneId': str(self.scene.pk), 'version': 2}, request_id)
        self.assertEqual(Message.objects.count(), 2)

    def test_replay_rechecks_membership_account_and_scene_access(self):
        from gravewright.journals.services import JournalError
        payload, request_id = self.payload(), uuid.uuid4()
        self.roll(payload, request_id)
        self.gm.is_active = False;self.gm.save(update_fields=['is_active'])
        with self.assertRaises(JournalError):self.roll(payload, request_id)
        self.gm.is_active = True;self.gm.save(update_fields=['is_active'])
        membership = Membership.objects.get(campaign=self.campaign, user=self.gm)
        membership.delete()
        with self.assertRaises(JournalError):self.roll(payload, request_id)
        Membership.objects.create(campaign=self.campaign, user=self.gm, role='gm')
        self.scene.delete()
        with self.assertRaises(MapError):self.roll(payload, request_id)
        self.assertEqual(InitiativeBatchReceipt.objects.count(), 1)

    def test_explicit_and_encounter_hidden_audiences_include_only_active_gms(self):
        co_gm = User.objects.create_user('batch-co-gm@example.test', 'password-12345', name='Co-GM')
        inactive = User.objects.create_user('batch-inactive@example.test', 'password-12345', name='Inactive', is_active=False)
        Membership.objects.create(campaign=self.campaign, user=co_gm, role='gm')
        Membership.objects.create(campaign=self.campaign, user=inactive, role='gm')
        self.encounter.combatants[0]['hidden'] = True;self.encounter.save()
        payload = self.payload();payload['entries'][2]['visibility'] = 'gm'
        self.roll(payload)
        secret = Message.objects.get()
        self.assertEqual(secret.visibility, 'gm')
        self.assertEqual(len(secret.roll['batch']), 3)
        self.assertEqual(set(secret.recipients.values_list('user_id', flat=True)), {self.gm.pk, co_gm.pk})
        self.assertEqual(history(self.campaign.pk, self.player.pk, str(self.scene.pk)), [])
        self.assertEqual(len(history(self.campaign.pk, co_gm.pk, str(self.scene.pk))), 1)

    def test_direct_actor_with_restricted_ownership_is_not_published_to_public_chat(self):
        self.actor.name = 'Private direct actor'
        self.actor.permissions = {str(self.player.pk): 'owner'}
        self.actor.save(update_fields=['name', 'permissions'])
        payload = self.payload();payload['entries'] = payload['entries'][2:]
        self.roll(payload)
        secret = Message.objects.get()
        self.assertEqual(secret.visibility, 'gm')
        self.assertEqual(secret.roll['batch'][0]['label'], 'Private direct actor')
        self.assertEqual(history(self.campaign.pk, self.player.pk, str(self.scene.pk)), [])
        self.actor.permissions = {'default': 'read', str(self.player.pk): 'none'}
        self.actor.save(update_fields=['permissions'])
        payload = self.payload();payload['entries'] = payload['entries'][2:]
        self.roll(payload)
        self.assertFalse(Message.objects.filter(visibility='public').exists())

    def test_all_sources_and_encounter_version_reject_before_randomness(self):
        for target, field in [(None, 'version'), (0, 'actorVersion'), (0, 'sheetVersion'),
                              (0, 'tokenVersion'), (1, 'actorVersion'), (1, 'sheetVersion'),
                              (1, 'tokenVersion'), (2, 'sheetVersion')]:
            with self.subTest(target=target, field=field):
                payload = self.payload()
                if target is None:payload[field] += 1
                else:payload['entries'][target]['source'][field] += 1
                with patch('gravewright.dice.grammar.runtime.secure_sample') as random:
                    with self.assertRaises(MapError) as rejected:self.roll(payload)
                self.assertEqual(rejected.exception.code, 'conflict');random.assert_not_called()
                self.unchanged()

    def test_missing_or_foreign_participants_reject_the_whole_plan(self):
        foreign = Scene.objects.create(campaign=self.campaign, name='Elsewhere', width=100, height=100)
        token = Token.objects.create(scene=foreign, actor=self.actor)
        for token_id in [str(uuid.uuid4()), str(token.pk)]:
            payload = self.payload();payload['entries'][0]['tokenId'] = token_id
            with patch('gravewright.dice.grammar.runtime.secure_sample') as random:
                with self.assertRaises(MapError) as rejected:self.roll(payload)
            self.assertEqual(rejected.exception.code, 'conflict');random.assert_not_called();self.unchanged()

    def test_compile_failure_in_last_expression_does_not_draw_any_dice(self):
        payload = self.payload();payload['entries'][-1]['expression'] = '1d20 +'
        with patch('gravewright.dice.grammar.runtime.secure_sample') as random:
            with self.assertRaises(MapError):self.roll(payload)
        random.assert_not_called();self.unchanged()

    def test_runtime_or_message_failure_rolls_back_encounter_quota_and_receipt(self):
        payload = self.payload();payload['entries'][-1]['expression'] = '1/(1d1-1)'
        with self.assertRaises(MapError):self.roll(payload)
        self.unchanged()
        with patch('gravewright.chat.models.Message.objects.create', side_effect=RuntimeError('disk failed')):
            with self.assertRaisesRegex(RuntimeError, 'disk failed'):self.roll()
        self.unchanged()
        with patch('gravewright.combat.models.InitiativeBatchReceipt.objects.create', side_effect=RuntimeError('receipt failed')):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                with self.assertRaisesRegex(RuntimeError, 'receipt failed'):self.roll()
        self.assertEqual(callbacks, [])
        self.unchanged();self.assertFalse(Recipient.objects.exists())

    def test_boolean_and_out_of_range_results_are_not_initiative_values(self):
        for expression in ['1==1', '1000001', '-1000001']:
            payload = self.payload();payload['entries'][-1]['expression'] = expression
            with self.assertRaises(MapError):self.roll(payload)
            self.unchanged()

    def test_remaining_quota_is_checked_for_both_audiences_before_randomness(self):
        member = Membership.objects.get(campaign=self.campaign, user=self.gm)
        window = SendWindow.objects.create(membership=member, count=19, expires_at=timezone.now()+timedelta(seconds=10))
        with patch('gravewright.dice.grammar.runtime.secure_sample') as random:
            from gravewright.accounts.services import AuthError
            with self.assertRaises(AuthError):self.roll()
        random.assert_not_called();window.refresh_from_db();self.assertEqual(window.count, 19)
        self.assertFalse(Message.objects.exists());self.assertFalse(InitiativeBatchReceipt.objects.exists())

    def test_structural_limits_and_invalid_source_types_do_not_write(self):
        changes = [lambda p:p.update(entries=[]), lambda p:p.update(entries=p['entries']*22),
            lambda p:p.update(selectFirst=1), lambda p:p.update(label='x'*49),
            lambda p:p.update(extra=True), lambda p:p['entries'][0].update(actorId=str(self.actor.pk)),
            lambda p:p['entries'][0].update(expression='x'*513),
            lambda p:p['entries'][0].update(visibility='whisper'),
            lambda p:p['entries'][0].pop('source'),
            lambda p:p['entries'][0]['source'].update(actorVersion=True),
            lambda p:p['entries'][0]['source'].pop('tokenVersion')]
        for change in changes:
            with self.subTest(change=change):
                payload = self.payload();change(payload)
                with self.assertRaises(MapError):self.roll(payload)
                self.unchanged()

    def test_native_sdk_dispatch_enforces_context_and_player_denial(self):
        payload = self.payload()
        with self.assertRaises(ModuleFailure) as mismatch:
            invoke(self.campaign.pk, self.gm.pk, 'combat', 'rollInitiativeBatch', payload,
                   uuid.uuid4(), scene_id=str(uuid.uuid4()))
        self.assertEqual(mismatch.exception.code, 'stale_context')
        with self.assertRaises(ModuleFailure) as denied:
            invoke(self.campaign.pk, self.player.pk, 'combat', 'rollInitiativeBatch', payload, uuid.uuid4())
        self.assertEqual(denied.exception.code, 'permission_denied')
        result = invoke(str(self.campaign.pk), str(self.gm.pk), 'combat', 'rollInitiativeBatch', payload,
                        uuid.uuid4(), scene_id=str(self.scene.pk))
        self.assertEqual(result['version'], 2)

    def test_sixty_four_participants_use_one_revision_and_one_public_chat_message(self):
        tokens = [Token.objects.create(scene=self.scene, actor=self.actor) for _ in range(64)]
        self.encounter.combatants = [{'tokenId': str(token.pk), 'initiative': None} for token in tokens]
        self.encounter.save()
        payload = self.payload()
        payload['entries'] = [{'tokenId': str(token.pk), 'expression': '1d1', 'source': {
            'actorVersion': self.actor.version, 'sheetVersion': self.actor.sheet_version, 'tokenVersion': token.version}}
            for token in tokens]
        result = self.roll(payload)
        self.assertEqual(result['version'], 2);self.assertEqual(len(result['batch']['results']), 64)
        self.assertEqual(Message.objects.count(), 1);self.assertEqual(SendWindow.objects.get().count, 1)
        self.assertEqual(len(Message.objects.get().roll['batch']), 64)


class InitiativeBatchEngineTests(TestCase):
    def test_aggregate_initial_dice_limit_rejects_before_randomness(self):
        with patch('gravewright.dice.grammar.runtime.secure_sample') as random:
            with self.assertRaisesRegex(RollError, '1024'):evaluate_batch(['99d6']*11)
        random.assert_not_called()

    def test_aggregate_node_limit_rejects_before_randomness(self):
        with patch('gravewright.dice.grammar.runtime.secure_sample') as random:
            with self.assertRaisesRegex(RollError, '4096'):evaluate_batch(['+'.join(['1']*100)]*21)
        random.assert_not_called()

    def test_aggregate_runtime_facts_are_bounded_and_the_slot_is_released(self):
        draws = []
        def sample():draws.append(1);return .99
        with self.assertRaisesRegex(RollError, '2048'):
            evaluate_batch(['50d6!o!o']*12, random_source=sample)
        self.assertEqual(len(draws), 2048)
        self.assertEqual(evaluate_batch(['2'])[0]['value']['value'], 2)


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class InitiativeBatchConcurrencyTests(TransactionTestCase):
    setUp = InitiativeBatchTests.setUp
    payload = InitiativeBatchTests.payload
    roll = InitiativeBatchTests.roll

    def concurrent(self, requests):
        ready = Barrier(len(requests))
        def run(arguments):
            try:
                ready.wait(timeout=5)
                return self.roll(**arguments)
            except MapError as error:
                return error.code
            finally:
                connection.close()
        with patch('gravewright.realtime.dispatch.send'), ThreadPoolExecutor(max_workers=len(requests)) as pool:
            return list(pool.map(run, requests))

    def test_duplicate_concurrent_requests_roll_and_publish_once(self):
        payload, request_id = self.payload(), uuid.uuid4()
        with patch('gravewright.dice.grammar.runtime.secure_sample', return_value=.5) as random:
            results = self.concurrent([{'payload': payload, 'request_id': request_id}]*2)
        self.assertEqual(random.call_count, 3)
        self.assertEqual(sorted(result['batch']['replayed'] for result in results), [False, True])
        self.assertEqual(results[0]['batch']['results'], results[1]['batch']['results'])
        self.assertEqual(Message.objects.count(), 2)
        self.assertEqual(InitiativeBatchReceipt.objects.count(), 1)
        self.encounter.refresh_from_db();self.assertEqual(self.encounter.version, 2)

    def test_competing_gms_reject_stale_plan_before_any_second_draw(self):
        co_gm = User.objects.create_user('batch-racing-gm@example.test', 'password-12345', name='Co-GM')
        Membership.objects.create(campaign=self.campaign, user=co_gm, role='gm')
        payload = self.payload()
        with patch('gravewright.dice.grammar.runtime.secure_sample', return_value=.5) as random:
            results = self.concurrent([{'payload': payload, 'user': self.gm}, {'payload': payload, 'user': co_gm}])
        self.assertEqual(random.call_count, 3)
        self.assertEqual(len([result for result in results if result == 'conflict']), 1)
        self.assertEqual(Message.objects.count(), 2)
        self.assertEqual(InitiativeBatchReceipt.objects.count(), 1)
        self.encounter.refresh_from_db();self.assertEqual(self.encounter.version, 2)
