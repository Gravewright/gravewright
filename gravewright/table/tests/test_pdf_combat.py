"""PDF combat reads the same sheet source as its token and PDF mappings."""
from copy import deepcopy

from django.test import TestCase

from gravewright.maps.services import MapError
from gravewright.table.tests.test_modules import TableModuleTests
from gravewright.tokens.models import Token
from gravewright.actors.models import Asset


class PdfCombatTests(TestCase):
    setUp = TableModuleTests.setUp
    command = TableModuleTests.command
    state = TableModuleTests.state

    def execute(self, action, **data):
        return self.command('combat', action, {
            'sceneId': str(self.scene.pk), 'version': self.state('combat')['version'], **data,
        })

    def test_default_pdf_formula_and_linked_or_snapshot_initiative(self):
        self.assertEqual(self.state('combat')['config']['formula'], '1d20 + @initiative')
        self.actor.data['init'] = 3
        self.actor.save()
        self.token.linked = True
        self.token.save()
        snapshot = deepcopy(self.actor.data)
        snapshot['init'] = 9
        other = Token.objects.create(scene=self.scene, actor=self.actor, linked=False, snapshot=snapshot)
        self.execute('add', tokenId=str(self.token.pk))
        self.execute('add', tokenId=str(other.pk))
        self.execute('add', actorId=str(self.actor.pk))
        self.execute('configure', formula='1d1 + @initiative')
        rolled = self.execute('roll', scope='all')
        scores = {row['id']: row['initiative'] for row in rolled['combatants']}
        self.assertEqual(scores, {str(self.token.pk): 4, str(other.pk): 10, str(self.actor.pk): 4})
        self.assertFalse(rolled['active'])

    def test_actor_only_combatant_uses_existing_resource_bar(self):
        self.actor.data['bars']['bar_1'] = {'value': 7, 'max': 20}
        self.actor.save()
        state = self.execute('add', actorId=str(self.actor.pk))
        self.assertEqual(state['combatants'][0]['bar'], {'value': 7, 'max': 20, 'percent': 35})
        self.actor.data['bars']['bar_1']['max'] = 0
        self.actor.save()
        self.assertIsNone(self.state('combat')['combatants'][0]['bar'])

    def test_combatant_image_prefers_token_and_falls_back_to_portrait(self):
        self.execute('add', tokenId=str(self.token.pk))
        self.execute('add', actorId=str(self.actor.pk))
        self.assertTrue(all(row['portrait_url'] is None for row in self.state('combat')['combatants']))
        portrait = Asset.objects.create(campaign=self.campaign, actor=self.actor, kind='portrait', name='Portrait', file='portrait.png')
        self.assertTrue(all(row['portrait_url'] == f'/game/actors/asset/{portrait.pk}' for row in self.state('combat')['combatants']))
        image = Asset.objects.create(campaign=self.campaign, actor=self.actor, kind='token', name='Token', file='token.png')
        self.assertTrue(all(row['portrait_url'] == f'/game/actors/asset/{image.pk}' for row in self.state('combat')['combatants']))
        self.execute('toggle', tokenId=str(self.token.pk), hidden=True)
        self.assertNotIn(str(self.token.pk), [row['id'] for row in self.state('combat', self.player)['combatants']])

    def test_manual_initiative_and_changes_preserve_current_turn(self):
        self.execute('add', tokenId=str(self.token.pk))
        self.execute('add', actorId=str(self.actor.pk))
        self.execute('configure', formula='')
        self.assertEqual(self.state('combat')['config']['input'], 'number')
        self.execute('initiative', tokenId=str(self.token.pk), value=10)
        self.execute('initiative', actorId=str(self.actor.pk), value=4)
        self.execute('start')
        state = self.execute('initiative', actorId=str(self.actor.pk), value=20)
        self.assertEqual(next(row['id'] for row in state['combatants'] if row['current']), str(self.token.pk))
        self.execute('configure', formula='1d1 + @initiative')
        state = self.execute('roll', scope='all')
        self.assertEqual(next(row['id'] for row in state['combatants'] if row['current']), str(self.token.pk))

    def test_invalid_formula_and_player_configuration_are_rejected(self):
        self.execute('add', actorId=str(self.actor.pk))
        before = self.state('combat')
        with self.assertRaises(MapError):
            self.execute('configure', formula='1d20 + @unknown')
        self.assertEqual(self.state('combat'), before)
        with self.assertRaises(MapError):
            self.command('combat', 'configure', {
                'sceneId': str(self.scene.pk), 'version': before['version'], 'formula': '1d1',
            }, self.player)
        with self.assertRaises(MapError):
            self.command('combat', 'roll', {
                'sceneId': str(self.scene.pk), 'version': before['version'], 'scope': 'all',
            }, self.player)

    def test_other_systems_do_not_inherit_pdf_rules(self):
        self.campaign.system = 'third-party-system'
        self.campaign.save()
        self.assertEqual(self.state('combat')['config']['formula'], '')

    def test_next_turn_skips_defeated_and_does_not_repeat_lone_combatant(self):
        self.execute('add', tokenId=str(self.token.pk))
        self.execute('start')
        self.assertFalse(self.state('combat')['combatants'][0]['is_next'])
        other = Token.objects.create(scene=self.scene, actor=self.actor)
        self.execute('add', tokenId=str(other.pk))
        self.execute('add', actorId=str(self.actor.pk))
        self.execute('toggle', tokenId=str(other.pk), defeated=True)
        state = self.state('combat')
        self.assertEqual(next(row['id'] for row in state['combatants'] if row['is_next']), str(self.actor.pk))
        self.execute('stop')
        self.assertFalse(any(row['is_next'] or row['is_current'] for row in self.state('combat')['combatants']))
