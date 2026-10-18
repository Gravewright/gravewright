"""Door appearance follows native state without widening asset permissions."""

from io import BytesIO
import tempfile
import uuid

from django.core.files.base import ContentFile
from django.test import TransactionTestCase, override_settings
from PIL import Image

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps import objects, services
from gravewright.maps.models import Broadcast, MapAsset, MapBuilderProject, Scene, SceneObject, SceneState


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class BuilderDoorArtTests(TransactionTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        media = override_settings(MEDIA_ROOT=temporary.name)
        media.enable()
        self.addCleanup(media.disable)
        self.gm = User.objects.create_user("door-gm@example.test", "password-12345", name="GM")
        self.player = User.objects.create_user("door-player@example.test", "password-12345", name="Player")
        self.campaign = Campaign.objects.create(owner=self.gm, name="Door workshop")
        self.who = Membership.objects.create(campaign=self.campaign, user=self.gm, role="gm")
        self.viewer = Membership.objects.create(campaign=self.campaign, user=self.player)
        self.scene = Scene.objects.create(campaign=self.campaign, name="Room", width=560, height=420)
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        SceneState.objects.create(scene=self.scene)
        image = BytesIO()
        Image.new("RGB", (8, 8), "#bd713e").save(image, "PNG")
        self.asset = MapAsset.objects.create(campaign=self.campaign, name="Door texture",
            width=8, height=8, file=ContentFile(image.getvalue(), name="door.png"))
        self.payload = {"kind": "door", "x1": 70, "y1": 140, "x2": 140, "y2": 140,
            "asset_id": str(self.asset.pk), "thickness": 14}

    def create_door(self, **patch):
        return SceneObject.objects.create(scene=self.scene, kind="walls",
            data=objects.wall({**self.payload, **patch}, campaign_id=self.campaign.pk))

    def asset_response(self):
        response = self.client.get(f"/game/map-assets/{self.asset.pk}")
        response.close()
        return response.status_code

    def test_door_image_is_scoped_on_create_update_and_paste(self):
        other = Campaign.objects.create(owner=self.gm, name="Private room")
        foreign = MapAsset.objects.create(campaign=other, name="Private texture", width=1, height=1)
        for action in ("create", "paste"):
            with self.subTest(action=action), self.assertRaises(services.MapError):
                payload = {**self.payload, "asset_id": str(foreign.pk)}
                objects.apply(self.scene, self.who,
                    "walls" if action == "create" else "wall-selection", action,
                    payload if action == "create" else {"walls": [payload]})
        door = self.create_door()
        with self.assertRaises(services.MapError):
            objects.apply(self.scene, self.who, "walls", "update",
                {"wall_id": str(door.pk), "asset_id": str(foreign.pk)})
        with self.assertRaises(services.MapError):
            objects.wall({**self.payload, "asset_id": str(uuid.uuid4())}, campaign_id=self.campaign.pk)

    def test_player_reads_only_art_of_visible_broadcast_doors(self):
        door = self.create_door()
        self.client.force_login(self.player)
        self.assertEqual(self.asset_response(), 200)
        self.assertIn(str(self.asset.pk), [row["id"] for row in self.client.get(
            f"/api/containers/{self.campaign.pk}/library/asset-state").json()["assets"]])
        door.data.update(presentation="secret", discovered=False)
        door.save()
        self.assertEqual(self.asset_response(), 404)
        self.assertNotIn("asset_id", objects.layer_state(self.scene, self.viewer)["walls"][0])
        door.data["discovered"] = True
        door.save()
        self.assertEqual(self.asset_response(), 200)
        self.scene.visibility = "gm"
        self.scene.save()
        self.assertEqual(self.asset_response(), 404)

    def test_opening_and_moving_preserve_art_but_deleting_art_keeps_collision(self):
        door = self.create_door()
        objects.apply(self.scene, self.who, "walls", "door",
            {"wall_id": str(door.pk), "door_state": "open"})
        objects.apply(self.scene, self.who, "wall-selection", "move",
            {"wall_ids": [str(door.pk)], "dx": 0, "dy": 70})
        door.refresh_from_db()
        self.assertEqual(door.data["asset_id"], str(self.asset.pk))
        self.assertEqual(door.data["y1"], 210)
        objects.apply(self.scene, self.who, "walls", "door",
            {"wall_id": str(door.pk), "door_state": "closed"})
        self.client.force_login(self.gm)
        response = self.client.post(f"/api/containers/{self.campaign.pk}/library/assets/delete",
            {"asset_id": str(self.asset.pk)}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        door.refresh_from_db()
        self.assertNotIn("asset_id", door.data)
        self.assertEqual(door.data["door_state"], "closed")
        self.assertEqual(door.data["movement_behavior"], "block")

    def test_deleting_material_preserves_editable_geometry_and_invalidates_old_revision(self):
        self.client.force_login(self.gm)
        project_id = uuid.uuid4()
        base = f"/api/containers/{self.campaign.pk}/map-builder/projects/{project_id}"
        document = {"schemaVersion": 1, "name": "Textured room", "columns": 8, "rows": 6,
            "cellSize": 32, "background": "#253038", "assets": [{"assetId": str(self.asset.pk), "role": "floor"}],
            "floors": [{"id": str(uuid.uuid4()), "assetId": str(self.asset.pk), "x": 1, "y": 1, "width": 6, "height": 4}],
            "walls": [], "doors": []}
        saved = self.client.post(base, {"request_id": str(uuid.uuid4()), "expected_version": 0,
            "folder_id": None, "document": document}, content_type="application/json")
        self.assertEqual(saved.status_code, 200, saved.content)
        deleted = self.client.post(f"/api/containers/{self.campaign.pk}/library/assets/delete",
            {"asset_id": str(self.asset.pk)}, content_type="application/json")
        self.assertEqual(deleted.status_code, 200, deleted.content)
        row = MapBuilderProject.objects.get(pk=project_id)
        self.assertEqual(row.version, 2)
        self.assertEqual(row.document["assets"], [])
        self.assertIsNone(row.document["floors"][0]["assetId"])
        self.assertEqual(row.document["floors"][0]["width"], 6)
        conflict = self.client.post(base, {"request_id": str(uuid.uuid4()), "expected_version": 1,
            "folder_id": None, "document": document}, content_type="application/json")
        self.assertEqual(conflict.status_code, 409)
        current = self.client.post(base, {"request_id": str(uuid.uuid4()), "expected_version": 2,
            "folder_id": None, "document": row.document}, content_type="application/json")
        self.assertEqual(current.status_code, 200, current.content)
        generated = self.client.post(base + "/generate", {"request_id": str(uuid.uuid4()),
            "expected_version": 3}, content_type="application/json")
        self.assertEqual(generated.status_code, 200, generated.content)
