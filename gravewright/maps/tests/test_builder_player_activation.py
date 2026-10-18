"""Explicit broadcasts deliver prepared Builder scenes without exposing private art."""

from datetime import timedelta
import uuid
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone

from gravewright.accounts.models import User
from gravewright.campaigns.models import StreamerLink
from gravewright.journals.services import JournalError
from gravewright.maps import services
from gravewright.maps.models import Broadcast, Receipt, Scene, SceneNavigation, SceneObject
from gravewright.table.models import DocumentAccess

from . import test_builder_projects as fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow")
class BuilderPlayerActivationTests(TestCase):
    asset = fixtures.BuilderProjectTests.asset
    post = fixtures.BuilderProjectTests.post
    save = fixtures.BuilderProjectTests.save
    generate = fixtures.BuilderProjectTests.generate

    def setUp(self):
        fixtures.BuilderProjectTests.setUp(self)
        StreamerLink.objects.create(campaign=self.campaign, guest=self.streamer, digest="a" * 64,
            expires_at=timezone.now() + timedelta(hours=1))

    def generated(self):
        self.assertEqual(self.save().status_code, 200)
        response = self.generate()
        self.assertEqual(response.status_code, 200, response.content)
        return Scene.objects.get(pk=response.json()["scene"]["id"])

    def activate(self, scene, *, user=None, campaign=None, rid=None):
        return services.command((campaign or self.campaign).pk, (user or self.gm).pk, "activate",
                                {"mapId": str(scene.pk)}, rid or uuid.uuid4())

    def test_generate_and_navigate_stay_private_until_explicit_activation(self):
        old = Scene.objects.create(campaign=self.campaign, name="Current game", width=128, height=128)
        Broadcast.objects.create(campaign=self.campaign, scene=old)
        generated = self.generated()
        self.assertEqual(generated.visibility, "gm")
        self.assertEqual(Broadcast.objects.get(campaign=self.campaign).scene_id, old.pk)
        services.command(self.campaign.pk, self.gm.pk, "navigate", {"mapId": str(generated.pk)}, uuid.uuid4())
        self.assertEqual(SceneNavigation.objects.get(membership=self.membership).scene_id, generated.pk)
        for user in (self.player, self.streamer):
            self.client.force_login(user)
            before = services.state(self.campaign.pk, user.pk)
            self.assertEqual(before["activeMapId"], str(old.pk))
            self.assertEqual([row["id"] for row in before["maps"]], [str(old.pk)])
            for endpoint in ("manifest", "state", "tiles/0/0/0.webp"):
                self.assertEqual(self.client.get(f"/api/maps/{generated.pk}/{endpoint}").status_code, 404)
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            result = self.activate(generated)
            self.assertFalse(send.called)
        generated.refresh_from_db()
        self.assertEqual((generated.visibility, generated.version), ("players", 2))
        self.assertEqual(result["map"]["visibility"], "players")
        self.assertEqual(Broadcast.objects.get(campaign=self.campaign).scene_id, generated.pk)
        self.assertIsNone(SceneNavigation.objects.get(membership=self.membership).scene_id)
        self.assertTrue(any(call.args[1]["type"] == "room.maps" for call in send.call_args_list))
        for user in (self.player, self.streamer):
            self.client.force_login(user)
            after = services.state(self.campaign.pk, user.pk)
            self.assertEqual(after["activeMapId"], str(generated.pk))
            self.assertEqual([row["id"] for row in after["maps"]], [str(generated.pk)])
            self.assertNotIn("builderProjectId", after["maps"][0])
            for endpoint in ("manifest", "state", "tiles/0/0/0.webp"):
                response = self.client.get(f"/api/maps/{generated.pk}/{endpoint}")
                self.assertEqual(response.status_code, 200, response.content if not response.streaming else "tile")
                if response.streaming:
                    self.assertTrue(b"".join(response.streaming_content))

    def test_retries_and_repeated_activation_do_not_increment_an_already_public_revision(self):
        generated = self.generated()
        rid = uuid.uuid4()
        first = self.activate(generated, rid=rid)
        self.assertEqual(first["map"]["version"], 2)
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.activate(generated, rid=rid), first)
        self.assertFalse(send.called)
        self.assertEqual(Receipt.objects.filter(campaign=self.campaign, user=self.gm, request_id=rid).count(), 1)
        self.assertEqual(self.activate(generated)["map"]["version"], 2)
        generated.refresh_from_db()
        self.assertEqual((generated.visibility, generated.version), ("players", 2))
        services.command(self.campaign.pk, self.gm.pk, "update", {"mapId": str(generated.pk),
            "version": generated.version, "settings": {"visibility": "gm"}}, uuid.uuid4())
        self.assertEqual(self.activate(generated, rid=rid), first)
        generated.refresh_from_db()
        self.assertEqual((generated.visibility, generated.version), ("gm", 3), "A replay cannot reverse a later edit.")

    def test_activation_shares_a_private_scene_already_selected_for_broadcast(self):
        generated = self.generated()
        Broadcast.objects.create(campaign=self.campaign, scene=generated)
        self.assertEqual(services.state(self.campaign.pk, self.player.pk)["maps"], [])
        self.activate(generated)
        generated.refresh_from_db()
        self.assertEqual((generated.visibility, generated.version), ("players", 2))
        self.assertEqual(services.state(self.campaign.pk, self.player.pk)["activeMapId"], str(generated.pk))

    def test_failed_broadcast_rolls_back_visibility_revision_and_receipt(self):
        generated = self.generated()
        version, rid = generated.version, uuid.uuid4()
        with patch("gravewright.maps.services.Broadcast.objects.update_or_create", side_effect=DatabaseError("Synthetic failure")), \
                patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            with self.assertRaisesMessage(DatabaseError, "Synthetic failure"):
                self.activate(generated, rid=rid)
        generated.refresh_from_db()
        self.assertEqual((generated.visibility, generated.version), ("gm", version))
        self.assertFalse(Receipt.objects.filter(campaign=self.campaign, request_id=rid).exists())
        self.assertFalse(send.called)

    def test_players_streamers_outsiders_and_foreign_campaigns_cannot_activate(self):
        generated = self.generated()
        outsider = User.objects.create_user("builder-outsider@example.test", "password-12345", name="Outsider")
        for user in (self.player, self.streamer, outsider):
            with self.subTest(user=user.name), self.assertRaises((services.MapError, JournalError)):
                self.activate(generated, user=user)
        with self.assertRaisesMessage(services.MapError, "Scene not found"):
            self.activate(generated, campaign=self.other)
        self.activate(generated)
        self.client.force_login(outsider)
        for endpoint in ("manifest", "state", "tiles/0/0/0.webp"):
            self.assertEqual(self.client.get(f"/api/maps/{generated.pk}/{endpoint}").status_code, 404)
        self.client.force_login(self.player)
        foreign = Scene.objects.create(campaign=self.other, name="Foreign private", width=128, height=128)
        for endpoint in ("manifest", "state", "tiles/0/0/0.webp"):
            self.assertEqual(self.client.get(f"/api/maps/{foreign.pk}/{endpoint}").status_code, 404)

    def test_activation_keeps_gm_art_and_unreferenced_assets_private(self):
        generated = self.generated()
        secret = self.asset("Secret GM art.png", "#112244")
        private = SceneObject.objects.create(scene=generated, kind="images", data={
            "asset_id": str(secret.pk), "src": f"/game/map-assets/{secret.pk}", "scene_id": str(generated.pk),
            "x": 64, "y": 64, "scale": 1, "rotation": 0, "natural_width": 16, "natural_height": 16,
            "layer": "gm-image-layer", "z_index": 1})
        before = private.data.copy()
        self.activate(generated)
        private.refresh_from_db()
        self.assertEqual(private.data, before)
        for user in (self.player, self.streamer):
            self.client.force_login(user)
            response = self.client.get(f"/api/maps/{generated.pk}/state")
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(str(private.pk), str(response.json()))
            self.assertNotIn(str(secret.pk), str(response.json()))
            self.assertEqual(self.client.get(f"/game/map-assets/{secret.pk}").status_code, 404)
        self.client.force_login(self.gm)
        response = self.client.get(f"/api/maps/{generated.pk}/state")
        self.assertIn(str(private.pk), {row["id"] for row in response.json()["images"]})

    def test_activation_preserves_explicit_document_permission_denials(self):
        generated = self.generated()
        DocumentAccess.objects.create(campaign=self.campaign, kind="scenes", resource_id=str(generated.pk),
                                       grants={"default": "read", str(self.player.pk): "none"})
        self.activate(generated)
        state = services.state(self.campaign.pk, self.player.pk)
        self.assertEqual(state["maps"], [])
        self.assertIsNone(state["activeMapId"])
        self.client.force_login(self.player)
        for endpoint in ("manifest", "state", "tiles/0/0/0.webp"):
            self.assertEqual(self.client.get(f"/api/maps/{generated.pk}/{endpoint}").status_code, 404)
