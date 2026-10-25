"""Installed initiative providers retain HTTP errors and native combat rules."""
from copy import deepcopy
from unittest.mock import patch
import uuid

from django.test import TestCase

from gravewright.actors.models import Actor
from gravewright.maps.models import Receipt
from gravewright.modules.models import Package
from gravewright.table.tests import test_modules as fixtures
from gravewright.tokens.models import Token
from . import providers
from .models import Encounter


SYSTEM = 'example.initiative'


class InitiativeFrontendTests(TestCase):
    def setUp(self):
        fixtures.TableModuleTests.setUp(self)
        registry = patch.dict(providers._providers, {}, clear=True)
        registry.start()
        self.addCleanup(registry.stop)
        Package.objects.create(
            module_id=SYSTEM, version='1.0.0', digest='0' * 64, record={},
            manifest={
                'id': SYSTEM, 'version': '1.0.0', 'name': 'Initiative fixture',
                'sdk': {'requires': '>=1.0.0 <3.0.0'},
                'system': {
                    'actorTypes': [{'id': 'character', 'label': 'Character'}],
                    'combat': {'formula': '1d1 + @init', 'requiresProvider': True},
                },
            },
        )
        self.campaign.system = SYSTEM
        self.campaign.save(update_fields=['system'])
        self.actor.data = {'init': 3}
        self.actor.save(update_fields=['data'])
        self.independent = Token.objects.create(
            scene=self.scene, actor=self.actor, linked=False, snapshot={'init': 7},
        )
        self.npc = Actor.objects.create(
            campaign=self.campaign, name='NPC', data={'init': 11}, permissions={},
        )
        self.row = Encounter.objects.create(scene=self.scene, combatants=[
            {'tokenId': str(self.token.pk), 'initiative': None},
            {'tokenId': str(self.independent.pk), 'initiative': None},
            {'actorId': str(self.npc.pk), 'initiative': None},
        ])
        self.client.force_login(self.gm)

    def roll(self, scope='all', **payload):
        self.row.refresh_from_db()
        return self.client.post(f'/api/tables/{self.campaign.pk}/api', {
            'domain': 'combat', 'method': 'rollInitiative',
            'payload': {
                'sceneId': str(self.scene.pk), 'version': self.row.version,
                'scope': scope, **payload,
            },
            'requestId': str(uuid.uuid4()),
        }, content_type='application/json')

    def scores(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        return {row['id']: row['initiative'] for row in response.json()['value']['combatants']}

    def test_required_provider_failure_keeps_unavailable_status_and_encounter(self):
        before = (deepcopy(self.row.combatants), self.row.version)
        receipts = Receipt.objects.filter(campaign=self.campaign).count()
        response = self.roll()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {
            'error': 'unavailable',
            'message': 'The selected system requires its server extension to be enabled.',
        })
        self.row.refresh_from_db()
        self.assertEqual((self.row.combatants, self.row.version), before)
        self.assertEqual(Receipt.objects.filter(campaign=self.campaign).count(), receipts)

    def test_provider_rolls_sheet_sources_and_preserves_scope_rules(self):
        seen = []

        def prepare(formula, data, *, conditions):
            seen.append(data['init'])
            data['init'] += 2
            return formula, data

        providers.register(SYSTEM, prepare_initiative=prepare)
        linked, independent, npc = map(str, (self.token.pk, self.independent.pk, self.npc.pk))
        self.assertEqual(self.scores(self.roll('one', tokenId=linked)), {
            linked: 6, independent: None, npc: None,
        })
        self.actor.data = {'init': 4}
        self.actor.save(update_fields=['data'])
        self.assertEqual(self.scores(self.roll('missing')), {
            linked: 6, independent: 10, npc: 14,
        })
        self.assertEqual(self.scores(self.roll('all')), {
            linked: 7, independent: 10, npc: 14,
        })
        self.npc.data = {'init': 12}
        self.npc.save(update_fields=['data'])
        self.assertEqual(self.scores(self.roll('npcs')), {
            linked: 7, independent: 10, npc: 15,
        })
        self.assertEqual(seen, [3, 7, 11, 11, 7, 4, 12])
        self.actor.refresh_from_db()
        self.independent.refresh_from_db()
        self.npc.refresh_from_db()
        self.assertEqual(self.actor.data, {'init': 4})
        self.assertEqual(self.independent.snapshot, {'init': 7})
        self.assertEqual(self.npc.data, {'init': 12})

    def test_player_cannot_roll_owned_combatant(self):
        seen = []

        def prepare(formula, data, *, conditions):
            seen.append(data)
            return formula, data

        providers.register(SYSTEM, prepare_initiative=prepare)
        self.client.force_login(self.player)
        before = (deepcopy(self.row.combatants), self.row.version)
        response = self.roll('one', tokenId=str(self.token.pk))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'permission_denied')
        self.assertEqual(seen, [])
        self.row.refresh_from_db()
        self.assertEqual((self.row.combatants, self.row.version), before)
        self.assertFalse(Receipt.objects.filter(campaign=self.campaign).exists())
