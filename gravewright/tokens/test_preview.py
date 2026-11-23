"""Transient movement validates live scope without materializing unrelated tokens."""

import uuid
from unittest.mock import patch
from django.test import TestCase, override_settings

from gravewright.journals.services import JournalError
from gravewright.maps.models import Scene, SceneObject
from gravewright.maps.services import MapError
from gravewright.table.tests import test_modules as fixtures
from . import services
from .models import Token


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PreviewTests(TestCase):
    setUp = fixtures.TableModuleTests.setUp

    def preview(self, positions=None):
        return services.preview(self.campaign.pk, self.player.pk, str(self.scene.pk),
            positions if positions is not None else [self.position()], {})

    def position(self, **changes):
        return {'id': str(self.token.pk), 'gridX': 1, 'gridY': 1,
                'version': self.token.version, **changes}

    def test_one_token_drag_does_not_load_the_rest_of_the_scene(self):
        Token.objects.bulk_create([Token(scene=self.scene, actor=self.actor) for _ in range(100)])
        loaded, original = [], Token.from_db
        def from_db(cls, *args, **kwargs):
            row = original(*args, **kwargs)
            loaded.append(row.pk)
            return row
        with patch.object(Token, 'from_db', classmethod(from_db)):
            result = self.preview()
        self.assertEqual(loaded, [self.token.pk])
        self.assertEqual(result, [{'id': str(self.token.pk), 'gridX': 1, 'gridY': 1, 'version': 1}])
        self.token.refresh_from_db()
        self.assertEqual((self.token.grid_x, self.token.grid_y, self.token.version), (0, 0, 1))

    def test_live_control_visibility_version_and_scene_checks_remain(self):
        for field, value in [('hidden', True), ('locked', True), ('version', 2)]:
            with self.subTest(field=field):
                Token.objects.filter(pk=self.token.pk).update(**{field: value})
                with self.assertRaises(MapError):
                    self.preview()
                Token.objects.filter(pk=self.token.pk).update(**{field: getattr(self.token, field)})
        self.actor.permissions = {}
        self.actor.save(update_fields=['permissions'])
        with self.assertRaises(MapError):
            self.preview()
        other = Scene.objects.create(campaign=self.campaign, name='Elsewhere', width=1000, height=1000)
        foreign = Token.objects.create(scene=other, actor=self.actor)
        with self.assertRaises(MapError):
            self.preview([self.position(id=str(foreign.pk))])

    def test_invalid_batches_and_duplicate_ids_are_rejected(self):
        for positions in ([], [None], [self.position(id='bad')], [self.position(id=str(uuid.uuid4()))],
                          [self.position(), self.position()], [self.position()] * 101):
            with self.subTest(positions=positions), self.assertRaises((MapError, JournalError)):
                self.preview(positions)

    def test_wall_blocks_preview_and_open_door_allows_it(self):
        wall = SceneObject.objects.create(scene=self.scene, kind='walls', data={
            'x1': 210, 'y1': 0, 'x2': 210, 'y2': 1000, 'kind': 'door', 'door_state': 'closed',
            'movement_behavior': 'block'})
        with self.assertRaises(MapError):
            self.preview([self.position(gridX=5)])
        wall.data['door_state'] = 'open'
        wall.save(update_fields=['data'])
        self.assertEqual(self.preview([self.position(gridX=5)])[0]['gridX'], 5)
