"""Shared drawings keep authorship, GM-layer privacy and independent revisions."""
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership, StreamerLink
from gravewright.journals.services import JournalError
from gravewright.maps import objects, services
from gravewright.maps.extra_objects import drawing as cleaned
from gravewright.maps.models import Broadcast, Scene, SceneState


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class DrawingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gm = User.objects.create_user('draw-gm@example.test', 'password-123')
        cls.player = User.objects.create_user('draw-player@example.test', 'password-123')
        cls.other = User.objects.create_user('draw-other@example.test', 'password-123')
        cls.streamer = User.objects.create_user('draw-stream@example.test', 'password-123')
        cls.campaign = Campaign.objects.create(owner=cls.gm, name='Drawings')
        for user, role in [(cls.gm, 'gm'), (cls.player, 'player'), (cls.other, 'player'), (cls.streamer, 'streamer')]:
            Membership.objects.create(campaign=cls.campaign, user=user, role=role)
        StreamerLink.objects.create(campaign=cls.campaign, guest=cls.streamer, digest='d' * 64,
                                    expires_at=timezone.now() + timedelta(hours=1))
        cls.scene = Scene.objects.create(campaign=cls.campaign, name='Map', width=1000, height=1000)
        Broadcast.objects.create(campaign=cls.campaign, scene=cls.scene)

    def drawing(self, **extra):
        return {'id': str(uuid.uuid4()), 'kind': 'pen', 'audience': 'campaign', 'color': '#abcdef',
                'fill': 'none', 'width': 3, 'opacity': 1, 'fontSize': 21, 'text': '<b>Authored</b>',
                'points': [{'x': 1, 'y': 2}, {'x': 20, 'y': 30}], **extra}

    def command(self, user, upserts=None, removed=None, request_id=None):
        return services.command(self.campaign.pk, user.pk, 'objects', {
            'mapId': str(self.scene.pk), 'area': 'drawings', 'action': 'patch',
            'data': {'upserts': upserts or [], 'removed': removed or []}}, request_id or str(uuid.uuid4()))

    def replace(self, user, rows, version):
        return services.command(self.campaign.pk, user.pk, 'objects', {
            'mapId': str(self.scene.pk), 'area': 'drawings', 'action': 'replace',
            'data': {'rows': rows, 'expected_version': version}}, str(uuid.uuid4()))

    def state(self, user):
        return objects.layer_state(self.scene, services.member(self.campaign.pk, user.pk))['drawings']

    def stored(self):
        return SceneState.objects.get(scene=self.scene).drawings['rows']

    def test_players_draw_for_everyone_and_edit_only_their_own(self):
        forged = self.drawing(owner=str(self.gm.pk), version=40)
        self.command(self.player, [forged])
        stored = self.stored()[0]
        self.assertEqual((stored['owner'], stored['version']), (str(self.player.pk), 1))
        for user, can_edit in [(self.player, True), (self.other, False), (self.streamer, False), (self.gm, True)]:
            row, = self.state(user)['rows']
            self.assertEqual(row['text'], '<b>Authored</b>')
            self.assertIs(row['canEdit'], can_edit)
        for upserts, removed in [([{**forged, 'expected_version': 1, 'text': 'forged'}], None),
                                 (None, [{'id': forged['id'], 'expected_version': 1}])]:
            with self.subTest(upserts=upserts), self.assertRaises(services.MapError) as caught:
                self.command(self.other, upserts, removed)
            self.assertEqual(caught.exception.code, 'forbidden')
        self.command(self.player, [{**forged, 'expected_version': 1, 'text': 'mine'}])
        self.command(self.gm, [{**forged, 'expected_version': 2, 'text': 'mine', 'color': '#123456'}])
        stored = self.stored()[0]
        self.assertEqual((stored['owner'], stored['version'], stored['text'], stored['color']),
                         (str(self.player.pk), 3, 'mine', '#123456'))
        self.command(self.gm, removed=[{'id': forged['id'], 'expected_version': 3}])
        self.assertEqual(self.stored(), [])

    def test_gm_layer_drawings_stay_private_and_players_cannot_create_them(self):
        private, public = self.drawing(audience='gm'), self.drawing()
        self.command(self.gm, [private, public])
        for user in (self.player, self.streamer):
            self.assertEqual([row['id'] for row in self.state(user)['rows']], [public['id']])
        self.assertEqual(len(self.state(self.gm)['rows']), 2)
        own = self.drawing()
        self.command(self.player, [own])
        for upserts in ([self.drawing(audience='gm')], [{**own, 'audience': 'gm', 'expected_version': 1}],
                        [{**private, 'expected_version': 1, 'text': 'probe'}]):
            with self.subTest(upserts=upserts), self.assertRaises(services.MapError) as caught:
                self.command(self.player, upserts)
            self.assertEqual(caught.exception.code, 'forbidden')
        with self.assertRaises((services.MapError, JournalError)):
            self.command(self.streamer, [self.drawing()])
        self.assertEqual(len(self.stored()), 3)

    def test_concurrent_participants_keep_each_others_work_and_conflicts_roll_back(self):
        first, second = self.drawing(), self.drawing()
        self.command(self.player, [first])
        self.command(self.other, [second])
        self.command(self.player, [{**first, 'expected_version': 1, 'text': 'moved'}])
        self.assertEqual([(row['id'], row['version']) for row in self.state(self.gm)['rows']],
                         [(first['id'], 2), (second['id'], 1)])
        third = self.drawing()
        with self.assertRaises(services.MapError) as caught:
            self.command(self.player, [third, {**first, 'expected_version': 1, 'text': 'stale'}])
        self.assertEqual(caught.exception.code, 'conflict')
        self.assertEqual([row['id'] for row in self.stored()], [first['id'], second['id']])
        for upserts, removed in [([{**third, 'expected_version': 1}], None),
                                 (None, [{'id': third['id'], 'expected_version': 1}]),
                                 ([first], None), ([first, first], None)]:
            with self.subTest(upserts=upserts, removed=removed), self.assertRaises(services.MapError):
                self.command(self.player, upserts, removed)

    def test_retry_returns_current_projection_without_duplicating(self):
        row, rid = self.drawing(audience='gm'), str(uuid.uuid4())
        with patch('gravewright.realtime.dispatch.changed') as changed:
            first = self.command(self.gm, [row], request_id=rid)
            again = self.command(self.gm, [row], request_id=rid)
            self.assertEqual(changed.call_count, 1)
        self.assertEqual(first['rows'], again['rows'])
        self.assertEqual(len(self.stored()), 1)
        Membership.objects.filter(campaign=self.campaign, user=self.gm).update(role='player')
        self.assertEqual(self.command(self.gm, [row], request_id=rid)['rows'], [])
        with self.assertRaises(services.MapError) as caught:
            self.command(self.gm, [self.drawing()], request_id=rid)
        self.assertEqual(caught.exception.code, 'conflict')

    def test_invalid_payloads_and_limits_are_rejected(self):
        for extra in ({'audience': 'everyone'}, {'points': []}, {'kind': 'rect', 'points': [{'x': 0, 'y': 0}]},
                      {'text': 'x' * 1001}, {'points': [{'x': float('nan'), 'y': 0}]}, {'width': 200}):
            with self.subTest(extra=extra), self.assertRaises(services.MapError):
                self.command(self.player, [self.drawing(**extra)])
        with self.assertRaises(services.MapError):
            self.command(self.player)
        with self.assertRaises(services.MapError):
            self.command(self.player, [self.drawing(points=[{'x': i, 'y': i} for i in range(4096)])
                                       for _ in range(13)])
        env = SceneState.objects.filter(scene=self.scene).first()
        self.assertFalse(env and env.drawings)

    def test_gm_replace_preserves_authors_revisions_and_player_replace_is_forbidden(self):
        # Rows saved before authorship was recorded have no owner or revision.
        mine, legacy = self.drawing(), cleaned(self.drawing())
        self.command(self.player, [mine])
        env = SceneState.objects.get(scene=self.scene)
        env.drawings = {'version': env.drawings['version'], 'rows': [*env.drawings['rows'], legacy]}
        env.save()
        state = self.state(self.gm)
        self.assertIs(next(r for r in self.state(self.player)['rows'] if r['id'] == legacy['id'])['canEdit'], False)
        rows = [{**r, 'text': 'moved'} if r['id'] == mine['id'] else r for r in state['rows']]
        added = self.drawing()
        self.replace(self.gm, [*rows, added], state['version'])
        by_id = {r['id']: r for r in self.stored()}
        self.assertEqual((by_id[mine['id']]['owner'], by_id[mine['id']]['version']), (str(self.player.pk), 2))
        self.assertNotIn('owner', by_id[legacy['id']])
        self.assertEqual(by_id[legacy['id']]['version'], 1)
        self.assertEqual(by_id[added['id']]['owner'], str(self.gm.pk))
        with self.assertRaises(services.MapError) as caught:
            self.replace(self.player, [], self.state(self.player)['version'])
        self.assertEqual(caught.exception.code, 'forbidden')
