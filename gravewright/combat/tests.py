"""Generic encounter identities and idempotent turn commands."""
from unittest.mock import patch
import uuid

from django.test import TestCase
from gravewright.table.tests import test_modules as fixtures
from . import services
from .models import Encounter


class EncounterIdentityTests(TestCase):
    setUp = fixtures.TableModuleTests.setUp
    command = fixtures.TableModuleTests.command
    state = fixtures.TableModuleTests.state

    def execute(self, action, **payload):
        return self.command('combat', action, {
            'sceneId': str(self.scene.pk), 'version': self.state('combat')['version'], **payload,
        })

    def test_new_start_changes_identity_but_configuration_order_and_turns_preserve_it(self):
        self.assertIsNone(self.state('combat')['encounterId'])
        self.assertIsNone(services.state(None)['encounterId'])
        self.execute('add', tokenId=str(self.token.pk))
        self.execute('add', actorId=str(self.actor.pk))
        self.assertIsNone(self.state('combat')['encounterId'])
        started = self.execute('start')
        encounter_id = started['encounterId']
        self.assertEqual(str(uuid.UUID(encounter_id)), encounter_id)
        for action, payload in [
            ('configure', {'formula': '1d1'}),
            ('initiative', {'tokenId': str(self.token.pk), 'value': 1}),
            ('initiative', {'actorId': str(self.actor.pk), 'value': 2}),
            ('order-up', {'tokenId': str(self.token.pk)}),
            ('next', {}),
            ('next-round', {}),
        ]:
            with self.subTest(action=action):
                current = self.execute(action, **payload)
                self.assertEqual(current['encounterId'], encounter_id)
                self.assertNotIn('_encounter_id', current['config'])
        self.assertEqual(self.state('combat', self.player)['encounterId'], encounter_id)
        self.execute('stop')
        self.execute('add', tokenId=str(self.token.pk))
        restarted = self.execute('start')
        self.assertNotEqual(restarted['encounterId'], encounter_id)
        self.assertEqual(restarted['config']['formula'], '1d1')
        self.assertNotIn('_encounter_id', restarted['config'])

    def test_retried_start_retains_the_original_identity(self):
        from gravewright.table import domain
        self.execute('add', tokenId=str(self.token.pk))
        request_id = uuid.uuid4()
        payload = {'sceneId': str(self.scene.pk), 'version': self.state('combat')['version']}
        first = domain.command(self.campaign.pk, self.gm.pk, 'combat', 'start', payload, request_id)
        retried = domain.command(self.campaign.pk, self.gm.pk, 'combat', 'start', payload, request_id)
        self.assertEqual(retried['encounterId'], first['encounterId'])
        self.assertEqual(self.state('combat')['encounterId'], first['encounterId'])

    def test_legacy_active_identity_is_stable_without_mutating_on_read(self):
        row = Encounter.objects.create(scene=self.scene, active=True, round=1,
            combatants=[{'tokenId': str(self.token.pk)}], config={'formula': '1d1'})
        before = self.state('combat')
        self.assertTrue(before['encounterId'])
        self.assertEqual(self.state('combat')['encounterId'], before['encounterId'])
        row.refresh_from_db()
        self.assertEqual(row.config, {'formula': '1d1'})
        self.assertEqual(row.version, before['version'])
        self.assertEqual(self.execute('next')['encounterId'], before['encounterId'])
        self.assertEqual(self.execute('configure', formula='1d1 + 1')['encounterId'], before['encounterId'])
        self.execute('stop')
        self.execute('add', tokenId=str(self.token.pk))
        self.assertNotEqual(self.execute('start')['encounterId'], before['encounterId'])

    def test_stop_clears_tracker_without_deleting_characters_or_tokens(self):
        self.execute('add', tokenId=str(self.token.pk))
        self.execute('add', actorId=str(self.actor.pk))
        self.execute('configure', formula='1d1')
        self.execute('start')
        self.execute('next')
        stopped = self.execute('stop')
        self.assertFalse(stopped['active'])
        self.assertEqual(stopped['combatants'], [])
        self.assertEqual((stopped['round'], stopped['turn']), (0, 0))
        self.assertIsNone(stopped['encounterId'])
        self.assertEqual(stopped['config']['formula'], '1d1')
        row = Encounter.objects.get(scene=self.scene)
        self.assertEqual(row.combatants, [])
        self.assertEqual(row.history, [])
        self.assertNotIn('_encounter_id', row.config)
        self.assertEqual(self.state('combat', self.player)['combatants'], [])
        self.actor.refresh_from_db()
        self.token.refresh_from_db()
        with self.assertRaises(services.MapError):
            self.execute('start')

    def test_stop_retry_does_not_clear_newly_added_participants(self):
        from gravewright.table import domain
        self.execute('add', tokenId=str(self.token.pk))
        self.execute('start')
        request_id = uuid.uuid4()
        payload = {'sceneId': str(self.scene.pk), 'version': self.state('combat')['version']}
        stopped = domain.command(self.campaign.pk, self.gm.pk, 'combat', 'stop', payload, request_id)
        self.execute('add', actorId=str(self.actor.pk))
        retried = domain.command(self.campaign.pk, self.gm.pk, 'combat', 'stop', payload, request_id)
        self.assertEqual(stopped, retried)
        self.assertEqual(len(self.state('combat')['combatants']), 1)
