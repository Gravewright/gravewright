import uuid
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from gravewright.accounts.models import User, UserPreference
from gravewright.campaigns.models import Campaign, Membership, StreamerLink
from gravewright.chat.context import scene_for
from gravewright.journals.services import JournalError
from gravewright.maps import services
from gravewright.maps.audience import destination
from gravewright.maps.library_services import active_scene
from gravewright.maps.models import Broadcast, Receipt, Scene, SceneAssignment, SceneNavigation
from gravewright.tokens import services as tokens


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class SceneAudienceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gm = User.objects.create_user('audience-gm@example.test', 'password-123', name='GM')
        cls.campaign = Campaign.objects.create(owner=cls.gm, name='Split party')
        cls.gm_member = Membership.objects.create(campaign=cls.campaign, user=cls.gm, role='gm')
        cls.users, cls.members = [], []
        for name, role in (('One', 'player'), ('Two', 'player'), ('Observer', 'streamer')):
            user = User.objects.create_user(f'{name.lower()}@example.test', 'password-123', name=name)
            cls.users.append(user)
            cls.members.append(Membership.objects.create(campaign=cls.campaign, user=user, role=role))
        StreamerLink.objects.create(campaign=cls.campaign, guest=cls.users[2], digest='a' * 64,
                                    expires_at=timezone.now() + timedelta(hours=1))
        cls.first = Scene.objects.create(campaign=cls.campaign, name='First', width=100, height=100)
        cls.second = Scene.objects.create(campaign=cls.campaign, name='Second', width=100, height=100, visibility='gm')
        Broadcast.objects.create(campaign=cls.campaign, scene=cls.first)

    def activate(self, ids=None, *, user=None, rid=None):
        payload = {'mapId': str(self.second.pk)}
        if ids is not None:
            payload['playerIds'] = ids
        return services.command(self.campaign.pk, (user or self.gm).pk, 'activate', payload, rid or str(uuid.uuid4()))

    def test_selected_player_changes_scene_without_moving_other_players_or_gm(self):
        SceneNavigation.objects.create(membership=self.gm_member, scene=self.first)
        self.activate([str(self.users[0].pk)])
        self.assertEqual(Broadcast.objects.get().scene_id, self.first.pk)
        self.assertEqual(SceneNavigation.objects.get(membership=self.gm_member).scene_id, self.first.pk)
        self.second.refresh_from_db()
        self.assertEqual(self.second.visibility, 'players')
        for member, expected in zip(self.members, (self.second, self.first, self.first)):
            self.assertEqual(destination(member), expected)
            state = services.state(self.campaign.pk, member.user_id)
            self.assertEqual(state['activeMapId'], str(expected.pk))
            self.assertEqual([row['id'] for row in state['maps']], [str(expected.pk)])
            self.assertNotIn('players', state)
            self.assertEqual(services.scene(expected.pk, member), expected)
            other = self.first if expected == self.second else self.second
            with self.assertRaises(services.MapError):
                services.scene(other.pk, member)

    def test_multiple_recipients_replay_and_full_activation_reunites_table(self):
        rid = str(uuid.uuid4())
        ids = [str(user.pk) for user in self.users[:2]]
        result = self.activate(ids, rid=rid)
        self.assertEqual(self.activate(ids, rid=rid), result)
        self.assertEqual(SceneAssignment.objects.count(), 2)
        self.assertEqual(Receipt.objects.count(), 1)
        self.activate()
        self.assertFalse(SceneAssignment.objects.exists())
        self.assertEqual(Broadcast.objects.get().scene_id, self.second.pk)
        self.assertTrue(all(destination(member) == self.second for member in self.members))

    def test_invalid_and_foreign_recipients_are_atomic_and_private_scene_stays_private(self):
        outsider = User.objects.create_user('outside@example.test', 'password-123')
        other = Campaign.objects.create(owner=self.gm, name='Other')
        Membership.objects.create(campaign=other, user=outsider)
        for ids in ([], 'all', [str(self.users[0].pk)] * 2, [str(outsider.pk)],
                    [str(self.gm.pk)], [str(self.users[2].pk)], ['bad-id'], [str(self.users[0].pk), str(outsider.pk)]):
            with self.subTest(ids=ids), self.assertRaises((services.MapError, JournalError)):
                self.activate(ids)
        self.second.refresh_from_db()
        self.assertEqual(self.second.visibility, 'gm')
        self.assertFalse(SceneAssignment.objects.exists())
        self.assertFalse(Receipt.objects.exists())
        for user in self.users:
            with self.assertRaises((services.MapError, JournalError)):
                self.activate([str(self.users[0].pk)], user=user)

    def test_chat_library_tokens_and_http_follow_the_assigned_scene(self):
        self.activate([str(self.users[0].pk)])
        who = self.members[0]
        self.assertEqual(scene_for(who), self.second)
        self.assertEqual(active_scene(who), self.second.pk)
        tokens.state(self.campaign.pk, who.user_id, self.second.pk)
        with self.assertRaises(services.MapError):
            tokens.state(self.campaign.pk, who.user_id, self.first.pk)
        self.client.force_login(self.users[0])
        self.assertEqual(self.client.get(f'/api/maps/{self.second.pk}/manifest').status_code, 200)
        self.assertEqual(self.client.get(f'/api/maps/{self.first.pk}/manifest').status_code, 404)
        self.client.force_login(self.users[1])
        self.assertEqual(self.client.get(f'/api/maps/{self.second.pk}/state').status_code, 404)

    def test_gm_only_roster_uses_saved_colors_and_effective_destinations(self):
        UserPreference.objects.create(user=self.users[0], ping_color='#123456')
        self.activate([str(self.users[0].pk)])
        roster = {row['id']: row for row in services.state(self.campaign.pk, self.gm.pk)['players']}
        self.assertEqual(len(roster), 2)
        self.assertEqual(roster[str(self.users[0].pk)]['color'], '#123456')
        self.assertEqual(roster[str(self.users[1].pk)]['color'], '#f2c679')
        self.assertEqual(roster[str(self.users[0].pk)]['sceneId'], str(self.second.pk))
        self.assertEqual(roster[str(self.users[1].pk)]['sceneId'], str(self.first.pk))

    def test_deleting_assigned_scene_returns_player_to_broadcast(self):
        self.activate([str(self.users[0].pk)])
        self.second.delete()
        self.assertFalse(SceneAssignment.objects.exists())
        self.assertEqual(destination(self.members[0]), self.first)

    def test_previous_gm_preview_does_not_become_a_player_assignment(self):
        SceneNavigation.objects.create(membership=self.gm_member, scene=self.second)
        self.gm_member.role = 'player'
        self.gm_member.save(update_fields=['role'])
        self.assertEqual(destination(self.gm_member), self.first)
