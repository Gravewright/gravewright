"""The encounter host dispatches opaque documents to their system provider."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import uuid

from django.test import SimpleTestCase, TestCase
from jsonschema import Draft202012Validator

from gravewright.accounts.models import User
from gravewright.actors.models import Actor
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps.models import Scene
from gravewright.maps.services import MapError
from gravewright.table import domain
from gravewright.tokens.models import Token
from . import providers, services, effects
from .models import Encounter


SYSTEM = 'example.starship'


class ProviderContractTests(SimpleTestCase):
    def setUp(self):
        clean = patch.dict(providers._providers, {}, clear=True)
        clean.start()
        self.addCleanup(clean.stop)
        self.who = SimpleNamespace(campaign=SimpleNamespace(system=SYSTEM))

    def test_identity_is_explicit_and_registration_never_replaces_another_provider(self):
        callback = lambda formula, data, **kwargs: (formula, data)
        provider = providers.register(SYSTEM, prepare_initiative=callback)
        self.assertIs(providers.get(SYSTEM), provider)
        self.assertIsNone(providers.get('example.other'))
        self.assertEqual(providers.register(SYSTEM, prepare_initiative=callback), provider)
        with self.assertRaises(ValueError):
            providers.register(SYSTEM, prepare_initiative=lambda *args: None)
        for identity, implementation in [('', callback), (None, callback), (SYSTEM, 'import code')]:
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                providers.register(identity, prepare_initiative=implementation)

    def test_only_the_selected_system_prepares_initiative_and_receives_a_copy(self):
        seen = []
        def prepare(formula, data, *, conditions):
            seen.append((formula, deepcopy(data), conditions))
            data['reactor']['power'] += 2
            conditions.append({'code': 'handled'})
            return '1d1 + @reactor.power', data
        providers.register(SYSTEM, prepare_initiative=prepare)
        providers.register('example.other', prepare_initiative=lambda *args, **kwargs: self.fail('Wrong system'))
        data = {'reactor': {'power': 7}, 'opaque': ['arbitrary']}
        conditions = [{'code': 'sensor-lock'}]
        before = deepcopy(data)
        with patch.object(services, 'system_combat', return_value={}):
            self.assertEqual(services.roll_initiative(self.who, '1d20', data, conditions=conditions), 10)
        self.assertEqual(data, before)
        self.assertEqual(conditions, [{'code': 'sensor-lock'}])
        self.assertEqual(seen[0][0], '1d20')

    def test_unregistered_system_uses_only_its_formula_without_interpreting_fields(self):
        data = {'engine': 4, 'conditions': ['any-label'], 'exhaustion': 99}
        with patch.object(services, 'system_combat', return_value={}):
            self.assertEqual(services.roll_initiative(self.who, '1d1 + @engine', data), 5)

    def test_required_server_provider_is_not_silently_ignored(self):
        with patch.object(services, 'system_combat', return_value={'requires_provider': True}):
            with self.assertRaisesMessage(MapError, 'requires its server extension'):
                services.roll_initiative(self.who, '1d1', {})

    def test_legacy_blank_identity_resolves_the_registered_default_provider(self):
        provider = providers.register(SYSTEM)
        self.who.campaign.system = ''
        with patch('gravewright.campaigns.systems._default_system', SYSTEM):
            with patch.object(services, 'system_combat', return_value={}):
                self.assertIs(services.system_provider(self.who), provider)

    def test_invalid_provider_results_do_not_bypass_the_native_dice_parser(self):
        for result in [None, ('1d1',), ('1d1; import os', {}), ('1d1', []), ('x' * 501, {}), ('1d1 + @score', {'score': float('inf')})]:
            with self.subTest(result=result):
                with patch.dict(providers._providers, {SYSTEM: providers.Provider(prepare_initiative=lambda *args, **kwargs: result)}):
                    with patch.object(services, 'system_combat', return_value={}), self.assertRaises(MapError):
                        services.roll_initiative(self.who, '1d1', {})

    def test_manifests_can_require_their_provider_but_cannot_select_host_game_rules(self):
        schema = json.loads((Path(__file__).parents[1] / 'modules/contracts/schemas/manifest.json').read_text(encoding='utf-8'))
        validator = Draft202012Validator(schema)
        manifest = {
            'id': SYSTEM, 'name': 'Starship', 'version': '1.0.0',
            'sdk': {'requires': '>=1.0.0 <2.0.0', 'tested': '1.0.0'},
            'description': 'Fixture', 'author': 'Fixture', 'license': 'MIT', 'entry': 'main.js',
            'system': {'actorTypes': [{'id': 'vessel', 'label': 'Vessel'}],
                       'combat': {'formula': '1d6 + @engine', 'requiresProvider': True, 'showRoll': False}},
        }
        self.assertTrue(validator.is_valid(manifest))
        manifest['system']['combat']['rollProfile'] = 'example.old-profile'
        self.assertFalse(validator.is_valid(manifest))


class EncounterProviderTests(TestCase):
    def setUp(self):
        clean = patch.dict(providers._providers, {}, clear=True)
        clean.start()
        self.addCleanup(clean.stop)
        self.gm = User.objects.create_user(email='provider-gm@example.test', password='long-test-password', role='owner')
        self.player = User.objects.create_user(email='provider-player@example.test', password='long-test-password')
        self.campaign = Campaign.objects.create(owner=self.gm, name='Starship', system=SYSTEM)
        Membership.objects.create(campaign=self.campaign, user=self.gm, role='gm')
        Membership.objects.create(campaign=self.campaign, user=self.player, role='player')
        self.scene = Scene.objects.create(campaign=self.campaign, name='Bridge', width=100, height=100)
        self.actor = Actor.objects.create(campaign=self.campaign, name='Ship', type='vessel', data={'charge': 9})
        self.linked = Token.objects.create(scene=self.scene, actor=self.actor, linked=True)
        self.independent = Token.objects.create(scene=self.scene, actor=self.actor, linked=False, snapshot={'charge': 20})
        self.outsider = Actor.objects.create(campaign=self.campaign, name='Unrelated', type='vessel', data={'charge': 90})
        self.row = Encounter.objects.create(scene=self.scene, active=True, round=1, combatants=[
            {'tokenId': str(self.linked.pk)}, {'tokenId': str(self.independent.pk)}, {'actorId': str(self.actor.pk)},
        ], config={'formula': '1d1'})

    def execute(self, action='next', request_id=None, user=None, **payload):
        self.row.refresh_from_db()
        return domain.command(self.campaign.pk, (user or self.gm).pk, 'combat', action,
                              {'sceneId': str(self.scene.pk), 'version': self.row.version, **payload}, request_id or uuid.uuid4())

    def test_absent_provider_does_not_interpret_or_mutate_sheet_data(self):
        self.actor.data = {'charge': 9, 'effects': [{'duration': {'type': 'rounds', 'value': 1}}]}
        self.actor.save()
        before = deepcopy(self.actor.data)
        self.execute()
        self.actor.refresh_from_db()
        self.assertEqual(self.actor.data, before)
        self.assertEqual(self.actor.sheet_version, 1)

    def test_provider_owns_each_isolated_document_and_core_preserves_permissions(self):
        seen = []
        def advance(data, event):
            seen.append(deepcopy(event))
            if event['phase'] == 'start' and event['isCurrent'] and event['periodic']:
                data['charge'] -= 3
                return True
            return False
        providers.register(SYSTEM, advance_effects=advance)
        self.execute()
        self.actor.refresh_from_db()
        self.independent.refresh_from_db()
        self.outsider.refresh_from_db()
        self.assertEqual(self.actor.data, {'charge': 9})
        self.assertEqual(self.independent.snapshot, {'charge': 17})
        self.assertEqual(self.outsider.data, {'charge': 90})
        self.assertEqual(self.independent.sheet_version, 2)
        self.assertEqual(len([e for e in seen if e['phase'] == 'start']), 2)
        self.assertTrue(all(e['actorType'] == 'vessel' for e in seen))
        before = len(seen)
        with self.assertRaises(MapError):
            self.execute(user=self.player)
        self.assertEqual(len(seen), before)

    def test_retry_applies_the_provider_once_and_retains_encounter_identity(self):
        calls = []
        def advance(data, event):
            if event['phase'] == 'start' and event['isCurrent'] and event['periodic']:
                calls.append(event['ownerTokenId'])
                data['charge'] += 1
                return True
            return False
        providers.register(SYSTEM, advance_effects=advance)
        request_id = uuid.uuid4()
        payload = {'sceneId': str(self.scene.pk), 'version': self.row.version}
        first = domain.command(self.campaign.pk, self.gm.pk, 'combat', 'next', payload, request_id)
        retry = domain.command(self.campaign.pk, self.gm.pk, 'combat', 'next', payload, request_id)
        self.assertEqual(retry['encounterId'], first['encounterId'])
        self.assertEqual(calls, [str(self.independent.pk)])
        self.independent.refresh_from_db()
        self.assertEqual(self.independent.snapshot, {'charge': 21})

    def test_failed_provider_rolls_back_documents_encounter_and_receipt(self):
        def fail(data, event):
            if event['ownerTokenId']:
                raise MapError('Provider rejected this operation.')
            data['charge'] = 0
            return True
        providers.register(SYSTEM, advance_effects=fail)
        before = (deepcopy(self.actor.data), self.actor.sheet_version, self.row.version, self.row.turn)
        with self.assertRaisesMessage(MapError, 'Provider rejected'):
            self.execute()
        self.actor.refresh_from_db()
        self.row.refresh_from_db()
        self.assertEqual((self.actor.data, self.actor.sheet_version, self.row.version, self.row.turn), before)

    def test_backward_navigation_never_dispatches_rules(self):
        providers.register(SYSTEM, advance_effects=lambda *args: self.fail('Backward dispatch'))
        self.row.history = [{'round': 1, 'turn': 0, 'tokenId': str(self.linked.pk)}]
        self.row.turn = 1
        self.row.save()
        self.execute('previous')

    def test_callback_cannot_persist_invalid_document_json(self):
        def invalid(data, event):
            data['charge'] = float('nan')
            return True
        providers.register(SYSTEM, advance_effects=invalid)
        with self.assertRaisesMessage(MapError, 'Invalid character sheet'):
            self.execute()
        self.actor.refresh_from_db()
        self.assertEqual(self.actor.data, {'charge': 9})
