"""Card projections keep private faces and bounded library query costs."""

from django.test import TestCase, override_settings

from gravewright.journals.services import member
from gravewright.table.models import DocumentAccess
from gravewright.table.tests import test_modules as fixtures
from . import services
from .models import Card, Deck


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CardProjectionTests(TestCase):
    setUp = fixtures.TableModuleTests.setUp

    def test_scene_projection_preserves_faces_and_excludes_hands(self):
        deck = Deck.objects.create(campaign=self.campaign, name='Deck', back='synthetic-back.png')
        face_down = Card.objects.create(deck=deck, name='Secret face', front='synthetic-front.png',
                                       zone='scene', scene=self.scene, owner=self.player)
        face_up = Card.objects.create(deck=deck, name='Public face', front='public.png',
                                     zone='scene', scene=self.scene, revealed=True)
        Card.objects.create(deck=deck, name='Private hand', zone='hand', owner=self.player)
        for user in (self.gm, self.player):
            who = member(self.campaign.pk, user.pk)
            expected = services.state(who, str(self.scene.pk))['cards']
            with self.assertNumQueries(1):
                rows = services.scene_cards(self.scene, who)
            self.assertEqual(rows, expected)
            by_id = {row['id']: row for row in rows}
            self.assertEqual(set(by_id), {str(face_down.pk), str(face_up.pk)})
            self.assertEqual(by_id[str(face_down.pk)]['name'], 'Card')
            self.assertIsNone(by_id[str(face_down.pk)]['frontUrl'])
            self.assertEqual(by_id[str(face_up.pk)]['name'], 'Public face')

    def test_library_counts_are_batched_and_keep_denied_decks_private(self):
        decks = [Deck.objects.create(campaign=self.campaign, name=f'Deck {index:02}') for index in range(20)]
        Card.objects.bulk_create([Card(deck=deck, name=zone, zone=zone)
                                 for deck in decks for zone in ('draw', 'draw', 'discard', 'hand')])
        DocumentAccess.objects.create(campaign=self.campaign, kind='cards', resource_id=str(decks[0].pk),
                                      grants={str(self.player.pk): 'none'})
        for user, expected_count, queries in ((self.gm, 20, 2), (self.player, 19, 3)):
            who = member(self.campaign.pk, user.pk)
            with self.assertNumQueries(queries):
                value = services.state(who)
            self.assertEqual(len(value['decks']), expected_count)
            self.assertTrue(all((row['draw_count'], row['discard_count']) == (2, 1)
                                for row in value['decks']))

    def test_scene_query_cost_does_not_grow_with_unrelated_decks(self):
        who = member(self.campaign.pk, self.player.pk)
        for count in (0, 30):
            Deck.objects.bulk_create([Deck(campaign=self.campaign, name=f'Unused {i}') for i in range(count)])
            with self.assertNumQueries(1):
                self.assertEqual(services.scene_cards(self.scene, who), [])
