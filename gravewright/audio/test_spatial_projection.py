"""Spatial audio projections preserve listener permissions and acoustic gains."""

from unittest.mock import patch
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from gravewright.table.tests import test_modules as fixtures
from gravewright.table import domain
from gravewright.audio import services
from gravewright.audio.models import Track
from gravewright.maps.models import SceneObject
from gravewright.tokens.models import Token


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class SpatialProjectionTests(TestCase):
    setUp = fixtures.TableModuleTests.setUp

    def prepare(self):
        self.scene.visibility = 'players'
        self.scene.settings = {'gridSize': 100, 'measureValue': 1}
        self.scene.save(update_fields=['visibility', 'settings'])
        self.sound = Track.objects.create(campaign=self.campaign, name='Synthetic sound', duration=120)

    def source(self, **values):
        return SceneObject.objects.create(scene=self.scene, kind='spatialSounds', data={
            'trackId': str(self.sound.pk), 'x': 0, 'y': 50, 'radius': 1,
            'gain': .8, 'enabled': True, 'occlusion': True, 'falloff': 'linear',
            'loop': True, **values})

    def state(self, user=None, preview=None):
        return domain.state(self.campaign.pk, (user or self.player).pk, 'audio', str(self.scene.pk), preview)

    def test_inactive_and_out_of_range_sources_do_not_trace_walls(self):
        self.prepare()
        self.source(enabled=False)
        self.source(gain=0)
        self.source(x=10000)
        with patch('gravewright.audio.services.sound_attenuation', wraps=services.sound_attenuation) as attenuation, \
                CaptureQueriesContext(connection) as queries:
            projected = self.state()
        self.assertEqual([row['effectiveGain'] for row in projected['spatialSounds']], [0, 0, 0])
        attenuation.assert_not_called()
        self.assertFalse(any("'walls'" in query['sql'] for query in queries))
        # Sources and their permitted media remain available even when inaudible.
        self.assertEqual([row['id'] for row in projected['tracks']], [str(self.sound.pk)])

    def test_no_sources_skip_listeners_and_walls(self):
        self.prepare()
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.state()['spatialSounds'], [])
        self.assertFalse(any('gravewright_tokens_token' in query['sql'] for query in queries))
        self.assertFalse(any("'walls'" in query['sql'] for query in queries))

    def test_strongest_listener_preserves_attenuation_and_elevation(self):
        self.prepare()
        self.source()
        wall = SceneObject.objects.create(scene=self.scene, kind='walls', data={
            'x1': 25, 'y1': 0, 'x2': 25, 'y2': 100, 'sound_behavior': 'attenuate'})
        self.assertAlmostEqual(self.state()['spatialSounds'][0]['effectiveGain'], .8 * .5 * .45)
        # Another owned token farther away can be louder because its ray is clear.
        Token.objects.create(scene=self.scene, actor=self.actor, grid_x=.25, grid_y=0, elevation=20)
        wall.data.update(vertical_bottom=0, vertical_top=1)
        wall.save(update_fields=['data'])
        self.assertAlmostEqual(self.state()['spatialSounds'][0]['effectiveGain'], .8 * .25)
        wall.data.update(kind='door', door_state='open')
        wall.save(update_fields=['data'])
        self.assertAlmostEqual(self.state()['spatialSounds'][0]['effectiveGain'], .8 * .5)

    def test_gm_requires_explicit_preview_and_player_requires_control(self):
        self.prepare()
        self.source(occlusion=False, falloff='constant')
        self.assertEqual(self.state(self.gm)['spatialSounds'][0]['effectiveGain'], 0)
        self.assertEqual(self.state(self.gm, str(self.token.pk))['spatialSounds'][0]['effectiveGain'], .8)
        self.actor.permissions = {}
        self.actor.save(update_fields=['permissions'])
        self.assertEqual(self.state()['spatialSounds'][0]['effectiveGain'], 0)

    def test_falloff_boundary_remains_audible_only_for_constant_sources(self):
        self.prepare()
        self.source(x=-50, falloff='constant', occlusion=False)
        self.source(x=-50, falloff='linear', occlusion=False)
        self.source(x=-50, falloff='smooth', occlusion=False)
        values = {row['falloff']: row['effectiveGain'] for row in self.state()['spatialSounds']}
        self.assertEqual(values, {'constant': .8, 'linear': 0, 'smooth': 0})
