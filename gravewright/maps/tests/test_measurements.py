"""Shared dock measurements retain ownership, privacy and independent revisions."""
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings

from gravewright.accounts.models import User
from django.utils import timezone
from gravewright.campaigns.models import Campaign, Membership, StreamerLink
from gravewright.journals.services import JournalError
from gravewright.maps import services, objects
from gravewright.maps.models import Scene, SceneObject, Broadcast


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class MeasurementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gm = User.objects.create_user('measure-gm@example.test', 'password-123')
        cls.player = User.objects.create_user('measure-player@example.test', 'password-123')
        cls.other = User.objects.create_user('measure-other@example.test', 'password-123')
        cls.streamer = User.objects.create_user('measure-stream@example.test', 'password-123')
        cls.campaign = Campaign.objects.create(owner=cls.gm, name='Measurements')
        for user, role in [(cls.gm, 'gm'), (cls.player, 'player'), (cls.other, 'player'), (cls.streamer, 'streamer')]:
            Membership.objects.create(campaign=cls.campaign, user=user, role=role)
        StreamerLink.objects.create(campaign=cls.campaign, guest=cls.streamer, digest='b' * 64,
                                    expires_at=timezone.now() + timedelta(hours=1))
        cls.scene = Scene.objects.create(campaign=cls.campaign, name='Map', width=1000, height=1000)
        Broadcast.objects.create(campaign=cls.campaign, scene=cls.scene)

    def marker(self, **extra):
        return {'id': str(uuid.uuid4()), 'kind': 'line', 'origin': {'x': 10, 'y': 10},
                'length': 20, 'width': 0, 'angle': 90, 'color': '#abcdef',
                'audience': 'campaign', 'title': '<script>Authored text</script>', 'titleEnabled': True,
                'points': [{'x': 0, 'y': 0}, {'x': 20, 'y': 0}], **extra}

    def command(self, user, upserts=None, removed=None, scene=None, request_id=None):
        return services.command(self.campaign.pk, user.pk, 'objects', {
            'mapId': str((scene or self.scene).pk), 'area': 'markers', 'action': 'patch',
            'data': {'upserts': upserts or [], 'removed': removed or []}}, request_id or str(uuid.uuid4()))

    def state(self, user):
        return objects.layer_state(self.scene, services.member(self.campaign.pk, user.pk))['markers']

    def test_owner_and_private_audience_are_server_enforced(self):
        own, private = self.marker(owner=str(self.gm.pk)), self.marker(audience='gm')
        self.command(self.player, [own]); self.command(self.gm, [private])
        player = self.state(self.player)
        self.assertEqual(len(player), 1)
        self.assertEqual(player[0]['owner'], str(self.player.pk))
        self.assertTrue(player[0]['canEdit'])
        self.assertFalse(self.state(self.other)[0]['canEdit'])
        self.assertFalse(self.state(self.streamer)[0]['canEdit'])
        self.assertEqual(len(self.state(self.gm)), 2)
        for user, marker in [(self.other, own), (self.player, private)]:
            with self.assertRaises((services.MapError, JournalError)):
                self.command(user, [{**marker, 'expected_version': 1, 'title': 'forged'}])
        for user in (self.player, self.streamer):
            with self.assertRaises((services.MapError, JournalError)):
                self.command(user, [self.marker(audience='gm')])

    def test_paths_titles_and_delete_are_shared_without_overwriting_peer_work(self):
        first, second = self.marker(), self.marker()
        self.command(self.player, [first]); self.command(self.other, [second])
        self.command(self.player, [{**first, 'expected_version': 1, 'title': 'new'}])
        self.assertEqual(len(self.state(self.player)), 2)
        self.assertEqual(SceneObject.objects.get(pk=first['id']).data['title'], 'new')
        self.command(self.player, removed=[{'id': first['id'], 'expected_version': 2}])
        self.assertEqual([row['id'] for row in self.state(self.player)], [second['id']])

    def test_conflict_rolls_back_entire_operation_and_replay_does_not_duplicate(self):
        first = self.marker(); rid = str(uuid.uuid4())
        with patch('gravewright.realtime.dispatch.changed') as changed:
            self.command(self.player, [first], request_id=rid)
            self.command(self.player, [first], request_id=rid)
            self.assertEqual(changed.call_count, 1)
        second = self.marker()
        with self.assertRaises(services.MapError):
            self.command(self.player, [second, {**first, 'expected_version': 99}])
        self.assertFalse(SceneObject.objects.filter(pk=second['id']).exists())

    def test_invalid_geometry_and_cross_scene_identifier_are_rejected(self):
        for extra in ({'title': 'x' * 121}, {'titleEnabled': 1}, {'points': [{}]},
                      {'origin': {'x': float('nan'), 'y': 0}}, {'points': [{'x': 0, 'y': 0}] * 257}):
            with self.subTest(extra=extra), self.assertRaises(services.MapError):
                self.command(self.player, [self.marker(**extra)])
        marker = self.marker(); self.command(self.gm, [marker])
        other = Scene.objects.create(campaign=self.campaign, name='Other', width=1000, height=1000)
        with self.assertRaises(services.MapError):
            self.command(self.gm, [marker], scene=other)

    def test_legacy_replace_preserves_private_measurements_and_optional_data(self):
        self.command(self.player, [self.marker()]); self.command(self.gm, [self.marker(audience='gm')])
        state = objects.layer_state(self.scene, services.member(self.campaign.pk, self.player.pk))
        services.command(self.campaign.pk, self.player.pk, 'objects', {
            'mapId': str(self.scene.pk), 'area': 'markers', 'action': 'replace',
            'data': {'rows': state['markers'], 'expected_version': state['version']}}, str(uuid.uuid4()))
        self.assertEqual(len(self.state(self.gm)), 2)

    def test_replay_rechecks_scene_and_filters_after_gm_demotion(self):
        marker = self.marker(audience='gm'); rid = str(uuid.uuid4())
        self.command(self.gm, [marker], request_id=rid)
        Membership.objects.filter(campaign=self.campaign, user=self.gm).update(role='player')
        self.assertEqual(self.command(self.gm, [marker], request_id=rid)['markers'], [])
        with self.assertRaises(services.MapError):
            self.command(self.gm, [self.marker()], request_id=rid)

    @override_settings(BOARD_MARKERS_MAX_PER_SCENE=2)
    def test_legacy_scene_limit_counts_invisible_private_markers(self):
        self.command(self.gm, [self.marker(audience='gm')])
        state = objects.layer_state(self.scene, services.member(self.campaign.pk, self.player.pk))
        with self.assertRaises(services.MapError):
            services.command(self.campaign.pk, self.player.pk, 'objects', {
                'mapId': str(self.scene.pk), 'area': 'markers', 'action': 'replace',
                'data': {'rows': [self.marker(), self.marker()], 'expected_version': state['version']}}, str(uuid.uuid4()))
        self.assertEqual(SceneObject.objects.filter(scene=self.scene, kind='markers').count(), 1)
