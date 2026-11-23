"""Encounter projections batch reads while preserving recipient-specific state."""

import uuid
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from gravewright.actors.models import Actor, Asset
from gravewright.journals.services import member
from gravewright.table.tests import test_modules as fixtures
from gravewright.tokens.models import Token
from . import services
from .models import Encounter


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CombatProjectionCostTests(TestCase):
    setUp = fixtures.TableModuleTests.setUp

    def test_query_count_is_bounded_for_distinct_combatants_and_shared_actors(self):
        tokens = [self.token, *Token.objects.bulk_create([
            Token(scene=self.scene, actor=self.actor) for _ in range(19)])]
        encounter = Encounter.objects.create(scene=self.scene, active=True)
        counts = []
        for count in (1, 20):
            encounter.combatants = [{'tokenId': str(token.pk)} for token in tokens[:count]]
            encounter.save(update_fields=['combatants'])
            who = member(self.campaign.pk, self.player.pk)
            with CaptureQueriesContext(connection) as queries:
                value = services.state(who, str(self.scene.pk))
            counts.append(len(queries))
            self.assertEqual(len(value['combatants']), count)
        self.assertEqual(counts[0], counts[1])

    def test_batch_preserves_private_tokens_bars_assets_order_and_missing_entries(self):
        self.actor.data = {'bars': {'bar_1': {'value': 7, 'max': 10}}}
        self.actor.save(update_fields=['data'])
        portrait = Asset.objects.create(campaign=self.campaign, actor=self.actor, kind='portrait',
                                        name='Synthetic portrait', file='synthetic.png')
        hidden = Token.objects.create(scene=self.scene, actor=self.actor, hidden=True)
        unowned = Actor.objects.create(campaign=self.campaign, name='Unowned', data={'bars': {'bar_1': {'value': 1, 'max': 4}}})
        public = Token.objects.create(scene=self.scene, actor=unowned)
        Encounter.objects.create(scene=self.scene, active=True, turn=2, combatants=[
            {'tokenId': str(hidden.pk)}, {'tokenId': str(uuid.uuid4())},
            {'tokenId': str(self.token.pk)}, {'actorId': str(self.actor.pk)},
            {'tokenId': str(public.pk)}, {'actorId': str(unowned.pk)}])
        player = services.state(member(self.campaign.pk, self.player.pk), str(self.scene.pk))
        rows = player['combatants']
        self.assertEqual([row['id'] for row in rows], [str(self.token.pk), str(self.actor.pk), str(public.pk)])
        self.assertTrue(rows[0]['is_current'])
        self.assertTrue(rows[1]['is_next'])
        self.assertEqual(rows[0]['portrait_url'], f'/game/actors/asset/{portrait.pk}')
        self.assertEqual(rows[0]['bar']['value'], 7)
        self.assertIsNone(rows[2]['bar'])
        self.assertEqual(rows[2]['bars'], [])
        gm = services.state(member(self.campaign.pk, self.gm.pk), str(self.scene.pk))
        self.assertEqual(len(gm['combatants']), 5)

    def test_foreign_participants_are_excluded_and_missing_token_keeps_actor_fallback(self):
        from gravewright.campaigns.models import Campaign
        from gravewright.maps.models import Scene
        foreign = Campaign.objects.create(owner=self.gm, name='Other campaign')
        scene = Scene.objects.create(campaign=foreign, name='Other scene', width=100, height=100)
        actor = Actor.objects.create(campaign=foreign, name='Foreign')
        token = Token.objects.create(scene=scene, actor=actor)
        Encounter.objects.create(scene=self.scene, combatants=[
            {'tokenId': str(token.pk)}, {'actorId': str(actor.pk)},
            {'tokenId': str(uuid.uuid4()), 'actorId': str(self.actor.pk)}])
        value = services.state(member(self.campaign.pk, self.gm.pk), str(self.scene.pk))
        self.assertEqual(len(value['combatants']), 1)
        self.assertEqual(value['combatants'][0]['actor_id'], str(self.actor.pk))
