"""Map pings use the sender's saved identification color."""

from django.test import TestCase

from gravewright.accounts.models import User, UserPreference
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps import services
from gravewright.maps.models import Broadcast, Scene


class PingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gm = User.objects.create_user('ping-gm@example.test', 'password-123')
        cls.player = User.objects.create_user('ping-player@example.test', 'password-123')
        cls.campaign = Campaign.objects.create(owner=cls.gm, name='Ping colors')
        Membership.objects.create(campaign=cls.campaign, user=cls.gm, role='gm')
        Membership.objects.create(campaign=cls.campaign, user=cls.player)
        cls.scene = Scene.objects.create(campaign=cls.campaign, name='Map', width=1000, height=1000)
        Broadcast.objects.create(campaign=cls.campaign, scene=cls.scene)

    def ping(self, user, **extra):
        return services.ping(self.campaign.pk, user.pk, {
            'mapId': str(self.scene.pk), 'x': 100, 'y': 200, **extra,
        })

    def test_missing_preference_uses_default_without_creating_preferences(self):
        self.assertEqual(self.ping(self.player)['color'], '#f2c679')
        self.assertFalse(UserPreference.objects.filter(user=self.player).exists())

    def test_sender_colors_are_independent_and_changes_apply_to_the_next_ping(self):
        UserPreference.objects.create(user=self.gm, ping_color='#123456')
        UserPreference.objects.create(user=self.player, ping_color='#abcdef')
        self.assertEqual(self.ping(self.gm, focus=True)['color'], '#123456')
        self.assertEqual(self.ping(self.player)['color'], '#abcdef')
        UserPreference.objects.filter(user=self.player).update(ping_color='#654321')
        self.assertEqual(self.ping(self.player)['color'], '#654321')
        self.assertEqual(self.ping(self.gm)['color'], '#123456')

    def test_payload_cannot_override_saved_color_or_grant_player_camera_focus(self):
        UserPreference.objects.create(user=self.player, ping_color='#123456')
        result = self.ping(self.player, color='#ffffff', focus=True)
        self.assertEqual(result['color'], '#123456')
        self.assertFalse(result['focus'])
        self.assertTrue(self.ping(self.gm, focus=True)['focus'])
