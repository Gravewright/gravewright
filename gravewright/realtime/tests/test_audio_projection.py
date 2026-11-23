"""Audio transport deltas retain clocks, playback and recipient-specific catalogs."""

import uuid
from unittest.mock import AsyncMock, patch
from asgiref.sync import async_to_sync
from django.test import TestCase, override_settings
from gravewright.audio.models import Track, Playlist, Playback
from gravewright.campaigns.models import Membership
from gravewright.maps.models import SceneObject
from gravewright.realtime.consumers import TableConsumer
from gravewright.realtime import projections
from gravewright.table import domain
from gravewright.table.tests import test_modules as fixtures


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AudioResourceDeltaTests(TestCase):
    setUp = fixtures.TableModuleTests.setUp

    def consumer(self):
        consumer = TableConsumer()
        consumer.emit = AsyncMock()
        return consumer

    def deliver(self, consumer, user=None, at=100, scene_id=None):
        scene_id = scene_id or str(self.scene.pk)
        with patch('gravewright.audio.services.time.time', return_value=at):
            state = domain.state(self.campaign.pk, (user or self.gm).pk, 'audio', scene_id)
        payload = {'module': 'audio', 'sceneId': scene_id, 'state': state}
        async_to_sync(consumer.emit_projection)('resources.state', ('audio', scene_id), payload)
        return consumer.emit.await_args.args[1], state

    def test_clock_and_ended_playback_arrive_without_resending_catalogs(self):
        sound = Track.objects.create(campaign=self.campaign, name='Effect', duration=2, loop=False)
        Playlist.objects.create(campaign=self.campaign, name='Set', tracks=[{'soundId': str(sound.pk)}])
        Playback.objects.create(scene=self.scene, data={'ambient': [{
            'trackId': str(sound.pk), 'status': 'playing', 'position': 0, 'startedAt': 100,
            'loop': False, 'volume': .7, 'playId': 'one'}]})
        consumer = self.consumer()
        first, before = self.deliver(consumer, at=100)
        self.assertNotIn('delta', first['state'])
        second, after = self.deliver(consumer, at=103)
        self.assertTrue(second['state']['delta'])
        self.assertEqual(second['state']['serverTime'], 103)
        self.assertEqual(second['state']['score']['serverTime'], 103)
        self.assertEqual(second['state']['playback']['ambient'][0]['status'], 'stopped')
        self.assertNotIn('tracks', second['state'])
        self.assertNotIn('playlists', second['state'])
        self.assertNotIn('upserts', second['state'])
        self.assertEqual(projections.apply(before, second['state']), after)

    def test_source_change_removes_player_tracks_without_exposing_gm_library(self):
        self.scene.visibility = 'players'
        self.scene.save(update_fields=['visibility'])
        first, second, private = [Track.objects.create(campaign=self.campaign, name=name)
                                  for name in ('First', 'Second', 'Private')]
        Playlist.objects.create(campaign=self.campaign, name='Private playlist')
        source = SceneObject.objects.create(scene=self.scene, kind='spatialSounds', data={
            'trackId': str(first.pk), 'x': 0, 'y': 0, 'radius': 5, 'gain': .7,
            'enabled': False, 'occlusion': True, 'falloff': 'smooth', 'loop': True})
        gm, player = self.consumer(), self.consumer()
        _, gm_before = self.deliver(gm)
        _, player_before = self.deliver(player, self.player)
        source.data['trackId'] = str(second.pk)
        source.save(update_fields=['data'])
        gm_frame, gm_after = self.deliver(gm, at=101)
        player_frame, player_after = self.deliver(player, self.player, at=101)
        self.assertNotIn('tracks', gm_frame['state'].get('upserts', {}))
        self.assertEqual(player_frame['state']['removes']['tracks'], [str(first.pk)])
        self.assertEqual([row['id'] for row in player_frame['state']['upserts']['tracks']], [str(second.pk)])
        self.assertNotIn(str(private.pk), projections.canonical(player_frame))
        self.assertEqual(player_after['playlists'], [])
        self.assertEqual(projections.apply(gm_before, gm_frame['state']), gm_after)
        self.assertEqual(projections.apply(player_before, player_frame['state']), player_after)

    def test_score_overlap_fades_and_natural_end_survive_delta_reconstruction(self):
        sounds = [Track.objects.create(campaign=self.campaign, name=f'Track {i}', duration=10)
                  for i in range(2)]
        playlist = Playlist.objects.create(campaign=self.campaign, name='Score', fade=2, tracks=[
            {'soundId': str(sound.pk), 'duration': 10, 'gain': .7} for sound in sounds])
        with patch('gravewright.audio.soundtrack.time.time', return_value=100):
            domain.command(self.campaign.pk, self.gm.pk, 'audio', 'score-start', {
                'sceneId': str(self.scene.pk), 'id': str(playlist.pk), 'kind': 'playlist',
                'expectedVersion': 0, 'repeat': False}, uuid.uuid4())
        consumer = self.consumer()
        _, previous = self.deliver(consumer, at=100)
        for at, count, status in ((109, 2, 'playing'), (119, 0, 'stopped')):
            frame, current = self.deliver(consumer, at=at)
            self.assertEqual(projections.apply(previous, frame['state']), current)
            self.assertEqual(len(current['score']['playbacks']), count)
            self.assertEqual(current['score']['state'], status)
            if count:
                self.assertTrue(all(row['fadeIn'] == row['fadeOut'] == 2
                                    for row in current['score']['playbacks']))
            previous = current

    def test_downgraded_role_discards_the_private_catalog(self):
        self.scene.visibility = 'players'
        self.scene.save(update_fields=['visibility'])
        sound = Track.objects.create(campaign=self.campaign, name='Private track')
        playlist = Playlist.objects.create(campaign=self.campaign, name='Private playlist')
        consumer = self.consumer()
        _, before = self.deliver(consumer)
        Membership.objects.filter(campaign=self.campaign, user=self.gm).update(role='player')
        frame, after = self.deliver(consumer, at=101)
        self.assertEqual(frame['state']['removes'], {'tracks': [str(sound.pk)], 'playlists': [str(playlist.pk)]})
        self.assertFalse(frame['state']['isGM'])
        self.assertEqual(projections.apply(before, frame['state']), after)

    def test_resubscribe_is_complete_and_other_resources_remain_independent(self):
        consumer = self.consumer()
        self.deliver(consumer)
        other = {'module': 'items', 'sceneId': str(self.scene.pk), 'state': {'items': []}}
        async_to_sync(consumer.emit_projection)('resources.state', ('items', str(self.scene.pk)), other)
        frame, _ = self.deliver(consumer, at=101)
        self.assertTrue(frame['state']['delta'])
        consumer.forget_projections('resources.state', match=lambda key: key[0] == 'audio')
        frame, _ = self.deliver(consumer, at=102)
        self.assertNotIn('delta', frame['state'])
        consumer.emit.reset_mock()
        async_to_sync(consumer.emit_projection)('resources.state', ('items', str(self.scene.pk)), other)
        consumer.emit.assert_not_awaited()
