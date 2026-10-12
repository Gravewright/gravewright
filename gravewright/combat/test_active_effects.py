"""Generic effect arithmetic never selects a game's rules or sheet schema."""
from copy import deepcopy
from unittest import TestCase

from .active_effects import (
    active_effects, all_effects, apply_resource_delta, apply_roll_modifiers,
    apply_stat_modifiers, effect_modifiers, effect_restrictions, granted_effects,
    periodic_modifiers, resolve_resource_target,
)


def effect(*modifiers, **payload):
    return {'id': 'example', 'data': {'modifiers': list(modifiers), **payload}}


class GenericEffectTests(TestCase):
    def test_collections_and_activation_predicates_are_explicit(self):
        source = effect({'target': 'reactor.output', 'operation': 'add', 'value': 2})
        source['equipped'] = False
        data = {'inventory': [source], 'systems': {'modules': [source]}, 'effects': []}
        self.assertEqual(all_effects(data), [])
        self.assertEqual(granted_effects(data, collections=['systems.modules']), [source])
        self.assertEqual(granted_effects(data, collections=['systems.modules'], eligible=lambda value: value.get('online')), [])
        data['status'] = {'rules': [source]}
        self.assertEqual(active_effects(data, path='status.rules'), [source])

    def test_target_matching_and_restrictions_keep_identifiers_opaque(self):
        source = effect({'target': 'sensor.scan', 'operation': 'add', 'value': 2},
                        restrictions=[{'target': 'pilot.jump', 'reason': 'offline'}])
        data = {'effects': [source]}
        modifiers, applied = effect_modifiers(data, {'sensor.scan.remote'})
        self.assertEqual(len(modifiers), 1)
        self.assertEqual(applied[0]['target'], 'sensor.scan')
        self.assertEqual(effect_modifiers(data, {'sensor.scanner'})[0], [])
        self.assertEqual(effect_restrictions(data, 'pilot.jump.remote')[0]['reason'], 'offline')

    def test_conditions_and_disabled_sources_are_respected_without_rule_inference(self):
        data = {'reactor': 2, 'effects': [
            effect({'target': 'sensor.scan', 'operation': 'add', 'value': 2}, condition='@sheet.reactor > 3'),
            {**effect({'target': 'sensor.scan', 'operation': 'add', 'value': 3}), 'enabled': False},
            effect({'target': 'sensor.scan', 'operation': 'add', 'value': 4}, condition='invalid syntax'),
        ]}
        self.assertEqual(effect_modifiers(data, {'sensor.scan'})[0], [])
        data['reactor'] = 4
        self.assertEqual(effect_modifiers(data, {'sensor.scan'})[0][0]['value'], 2)

    def test_roll_arithmetic_does_not_interpret_advantage_or_dice_faces(self):
        formula = apply_roll_modifiers('1d20', [
            {'operation': 'advantage'}, {'operation': 'disadvantage'},
            {'operation': 'add', 'value': 3}, {'operation': 'subtract', 'value': 2},
            {'operation': 'add_dice', 'value': '1d8'},
        ])
        self.assertEqual(formula, '1d20 + 3 - 2 + 1d8')
        self.assertEqual(apply_roll_modifiers('3d6', [{'operation': 'advantage'}]), '3d6')

    def test_stats_require_explicit_paths_and_keep_base_data_unchanged(self):
        data = {'ac': 8, 'prof': 2, 'spell': {'dc': 7}, 'reactor': {'output': 5}, 'effects': [effect(
            {'target': 'stat.ac', 'operation': 'add', 'value': 99},
            {'target': 'stat.prof', 'operation': 'set', 'value': 99},
            {'target': 'stat.spell.dc', 'operation': 'add', 'value': 99},
            {'target': 'sheet.reactor.output', 'operation': 'subtract', 'value': 2},
        )]}
        before = deepcopy(data)
        derived = apply_stat_modifiers(data)
        self.assertEqual(derived['reactor']['output'], 3)
        self.assertEqual((derived['ac'], derived['prof'], derived['spell']['dc']), (8, 2, 7))
        self.assertEqual(data, before)

    def test_periodic_values_are_signed_explicit_deltas_without_damage_rules(self):
        data = {'effects': [effect(
            {'target': 'resource.charge', 'operation': 'resource_delta', 'value': '-1d6 - 2'},
            {'target': 'resource.charge', 'operation': 'resource_delta', 'value': 4},
            {'target': 'damage.self', 'operation': 'damage_over_time', 'value': 99},
            {'target': 'damage.received', 'operation': 'resistance'},
        )]}
        self.assertEqual([entry['delta'] for entry in periodic_modifiers(data, roller=lambda count, sides: [1] * count)], [-3, 4])

    def test_resources_have_no_primary_hp_or_field_name_fallback(self):
        resources = {'charge': {'path': 'sheet.reactor.charge', 'maxPath': 'sheet.reactor.capacity', 'min': -2}}
        self.assertEqual(resolve_resource_target('resource.charge', resources), ('reactor.charge', 'reactor.capacity', -2))
        self.assertEqual(resolve_resource_target('sheet.reserve.value', resources), ('reserve.value', '', 0))
        for target in ('', 'self', 'damage.self', 'heal.self', 'resource.missing'):
            self.assertIsNone(resolve_resource_target(target, resources))
        self.assertIsNone(resolve_resource_target('resource.charge', {'charge': {}}))
        data = {'reserve': {'value': 3, 'max': 4}}
        self.assertEqual(apply_resource_delta(data, 'reserve.value', '', 0, 5), 8)
        self.assertEqual(apply_resource_delta(data, 'reserve.value', 'reserve.max', 0, 5), 4)

    def test_arithmetic_bounds_use_only_configured_paths(self):
        data = {'reactor': {'charge': 2, 'capacity': 10}, 'hp': {'value': 50}, 'bars': {'bar_1': {'value': 8}}}
        self.assertEqual(apply_resource_delta(data, 'reactor.charge', 'reactor.capacity', -2, -7), -2)
        self.assertEqual(apply_resource_delta(data, 'reactor.charge', 'reactor.capacity', -2, 99), 10)
        self.assertEqual(data['hp']['value'], 50)
        self.assertEqual(data['bars']['bar_1']['value'], 8)
        before = deepcopy(data)
        for path, delta in [('', 1), ('__proto__.x', 1), ('reactor.charge', float('inf')), ('reactor.charge', True)]:
            self.assertIsNone(apply_resource_delta(data, path, '', 0, delta))
        self.assertEqual(data, before)
