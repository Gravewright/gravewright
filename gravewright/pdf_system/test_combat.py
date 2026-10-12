"""The PDF provider retains its own legacy clocks and mapped-bar conventions."""
from copy import deepcopy
from unittest import TestCase

from .combat import advance_effects, periodic_modifiers


def event(**changes):
    return {'phase': 'start', 'roundBoundary': False, 'isCurrent': True,
            'periodic': True, 'tokenId': 'current-token', 'actorId': 'current-actor',
            'ownerTokenId': '', 'ownerActorId': 'current-actor',
            'documentKey': ('actor', 'current-actor'), 'clockKeys': set(), **changes}


def effect(operation, value=None, target='', **fields):
    return {'data': {'modifiers': [{'operation': operation, 'value': value, 'target': target}]}, **fields}


def sheet(*effects):
    return {'bars': {'bar_1': {'value': 20, 'max': 30}, 'bar_2': {'value': 5, 'max': 10}},
            'effects': list(effects)}


class PdfCombatTests(TestCase):
    def test_periodic_damage_and_healing_use_only_the_pdf_mapped_bar(self):
        data = sheet(effect('damage_over_time', 5), effect('heal_over_time', 2))
        self.assertTrue(advance_effects(data, event()))
        self.assertEqual(data['bars']['bar_1']['value'], 17)
        self.assertEqual(data['bars']['bar_2']['value'], 5)
        self.assertNotIn('death', data)
        self.assertNotIn('concentration', data)
        dice = sheet(effect('damage_over_time', '1d6 + 4'))
        self.assertEqual(periodic_modifiers(dice, roller=lambda count, sides: [1] * count)[0]['delta'], -5)

    def test_legacy_resistance_reduction_vulnerability_and_immunity_remain_local(self):
        data = sheet(effect('damage_over_time', 15),
                     effect('reduce', 2, 'damage.received'),
                     effect('resistance', target='damage.received'),
                     effect('vulnerability', target='damage.received'))
        self.assertEqual(periodic_modifiers(data)[0]['delta'], -12)
        data['effects'].append(effect('immunity', target='damage.received'))
        self.assertEqual(periodic_modifiers(data), [])

    def test_bounds_disabled_sources_and_other_turns_preserve_old_behavior(self):
        data = sheet(effect('heal_over_time', 90), effect('damage_over_time', 99, enabled=False))
        original = deepcopy(data)
        self.assertFalse(advance_effects(data, event(isCurrent=False)))
        self.assertEqual(data, original)
        self.assertTrue(advance_effects(data, event()))
        self.assertEqual(data['bars']['bar_1']['value'], 30)
        self.assertFalse(advance_effects(data, event(periodic=False)))

    def test_legacy_round_duration_ticks_only_at_round_boundary_and_once(self):
        data = sheet({'id': 'timed', 'duration': {'type': 'rounds', 'value': 2}})
        self.assertFalse(advance_effects(data, event(phase='end', isCurrent=False)))
        end = event(phase='end', isCurrent=False, roundBoundary=True)
        self.assertTrue(advance_effects(data, end))
        self.assertEqual(data['effects'][0]['duration']['remaining'], 1)
        self.assertFalse(advance_effects(data, end))
        self.assertTrue(advance_effects(data, event(phase='end', roundBoundary=True)))
        self.assertFalse(data['effects'][0]['enabled'])

    def test_canonical_duration_source_token_and_owner_identity_are_preserved(self):
        data = sheet({'duration': {'type': 'rounds', 'value': 99}, 'data': {
            'duration': {'type': 'rounds', 'value': 2, 'expires': 'start',
                         'sourceTokenId': 'source-token', 'sourceActorId': 'current-actor'}}})
        self.assertFalse(advance_effects(data, event()))
        self.assertTrue(advance_effects(data, event(tokenId='source-token', isCurrent=False)))
        duration = data['effects'][0]['data']['duration']
        self.assertEqual(duration['remaining'], 1)
        self.assertEqual(data['effects'][0]['duration'], duration)
        duration.pop('sourceTokenId')
        duration.pop('sourceActorId')
        self.assertFalse(advance_effects(data, event(isCurrent=False)))
        self.assertTrue(advance_effects(data, event()))
        self.assertFalse(data['effects'][0]['enabled'])

    def test_manual_invalid_and_conditional_effects_do_not_apply(self):
        data = sheet({'data': {'duration': {'type': 'rounds', 'value': 2, 'expires': 'manual'}}},
                     {'duration': {'type': 'rounds', 'value': 1.5}},
                     {'data': {'condition': '@sheet.bars.bar_1.value < 5',
                               'modifiers': [{'operation': 'damage_over_time', 'value': 50}]}},
                     {'data': {'condition': 'invalid syntax',
                               'modifiers': [{'operation': 'damage_over_time', 'value': 50}]}})
        before = deepcopy(data)
        self.assertFalse(advance_effects(data, event(phase='end', roundBoundary=True)))
        self.assertFalse(advance_effects(data, event()))
        self.assertEqual(data, before)
