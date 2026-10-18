"""The builder page is a private, read-only entry into the editing workspace."""

from datetime import timedelta
from unittest.mock import patch
import uuid

from django.apps import apps
from django.shortcuts import render
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership, StreamerLink
from gravewright.maps.models import (
    Broadcast, Folder, Scene, SceneNavigation, SceneObject, SceneState,
)


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    ALLOWED_HOSTS=["testserver"],
)
class BuilderEntryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gm = User.objects.create_user(
            "builder-gm@example.test", "password-12345", name="Builder GM", role="owner"
        )
        cls.player = User.objects.create_user(
            "builder-player@example.test", "password-12345", name="Builder Player"
        )
        cls.streamer = User.objects.create_user(
            "builder-streamer@example.test", None, name="Builder Streamer"
        )
        cls.campaign = Campaign.objects.create(owner=cls.gm, name="Map workshop")
        cls.other = Campaign.objects.create(owner=cls.gm, name="Other workshop")
        cls.gm_member = Membership.objects.create(
            campaign=cls.campaign, user=cls.gm, role="gm"
        )
        Membership.objects.create(campaign=cls.campaign, user=cls.player)
        Membership.objects.create(
            campaign=cls.campaign, user=cls.streamer, role="streamer"
        )
        StreamerLink.objects.create(
            campaign=cls.campaign, guest=cls.streamer, digest="a" * 64,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        cls.folder = Folder.objects.create(campaign=cls.campaign, label="New maps")
        cls.foreign_folder = Folder.objects.create(campaign=cls.other, label="Private maps")
        cls.scene = Scene.objects.create(
            campaign=cls.campaign, folder=cls.folder, name="Ongoing scene",
            width=1024, height=512, settings={"gridSize": 70},
        )
        Broadcast.objects.create(campaign=cls.campaign, scene=cls.scene)
        SceneNavigation.objects.create(membership=cls.gm_member, scene=cls.scene)
        SceneState.objects.create(scene=cls.scene, lighting={"darkness": 0.5})
        SceneObject.objects.create(
            scene=cls.scene, kind="walls", data={"a": {"x": 0, "y": 0}}
        )

    def entry_url(self, campaign=None):
        return reverse("map-builder", args=[(campaign or self.campaign).pk])

    def test_anonymous_entry_uses_existing_login_navigation(self):
        response = self.client.get(self.entry_url())
        self.assertRedirects(response, "/login", fetch_redirect_response=False)

    def test_gm_receives_independent_workspace_and_folder_context(self):
        self.client.force_login(self.gm)
        for folder in (None, self.folder):
            with self.subTest(folder=folder), patch(
                "gravewright.maps.builder.render", wraps=render
            ) as renderer:
                response = self.client.get(
                    self.entry_url(), {"folder": str(folder.pk)} if folder else {}
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Cache-Control"], "no-store")
                args = renderer.call_args.args
                self.assertEqual(args[1], "gravewright_maps/builder.html")
                context = args[2]
                self.assertEqual(context["campaign"], self.campaign)
                self.assertEqual(context["folder"], folder)
                self.assertEqual(
                    context["back_url"], reverse("table:workspace", args=[self.campaign.pk])
                )
                self.assertEqual(context["member_role"], "gm")
                self.assertIn("language", context)

    def test_players_and_active_streamers_cannot_open_builder(self):
        for user in (self.player, self.streamer):
            with self.subTest(role=user.name):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.entry_url()).status_code, 404)

    def test_host_owner_needs_campaign_membership(self):
        self.client.force_login(self.gm)
        self.assertEqual(self.client.get(self.entry_url(self.other)).status_code, 404)
        missing = reverse("map-builder", args=[uuid.uuid4()])
        self.assertEqual(self.client.get(missing).status_code, 404)

    def test_folder_must_exist_and_belong_to_campaign(self):
        self.client.force_login(self.gm)
        for folder_id in (str(self.foreign_folder.pk), str(uuid.uuid4()), "invalid"):
            with self.subTest(folder_id=folder_id):
                self.assertEqual(
                    self.client.get(self.entry_url(), {"folder": folder_id}).status_code, 404
                )

    def test_role_and_membership_are_rechecked_on_every_entry(self):
        self.client.force_login(self.gm)
        self.assertEqual(self.client.get(self.entry_url()).status_code, 200)
        Membership.objects.filter(pk=self.gm_member.pk).update(role="player")
        self.assertEqual(self.client.get(self.entry_url()).status_code, 404)
        Membership.objects.filter(pk=self.gm_member.pk).delete()
        self.assertEqual(self.client.get(self.entry_url()).status_code, 404)

    def test_entry_and_unsupported_writes_preserve_existing_scene_state(self):
        self.client.force_login(self.gm)
        models = list(apps.get_app_config("gravewright_maps").get_models())

        def snapshot():
            return {
                model._meta.label: list(model.objects.order_by("pk").values())
                for model in models
            }

        before = snapshot()
        for query in ({}, {"folder": str(self.folder.pk)}):
            self.assertEqual(self.client.get(self.entry_url(), query).status_code, 200)
        self.assertEqual(
            self.client.post(self.entry_url(), {"name": "Unpublished draft"}).status_code, 405
        )
        self.assertEqual(before, snapshot())
