"""Editable map sources, authenticated assets, native doors and atomic generation."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import tempfile
import threading
from unittest.mock import Mock, patch
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image

from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps import builder_render, builder_services, services, tiling
from gravewright.maps.models import (
    Broadcast, Folder, MapAsset, MapBuilderProject, Receipt, Scene, SceneNavigation,
    SceneObject, Tile,
)


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
)
class BuilderProjectTests(TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="builder-project-tests-")
        self.addCleanup(self.scratch.cleanup)
        self.media = Path(self.scratch.name) / "media"
        self.options = override_settings(MEDIA_ROOT=str(self.media), FILE_UPLOAD_TEMP_DIR=self.scratch.name)
        self.options.enable()
        self.addCleanup(self.options.disable)
        self.gm = User.objects.create_user("builder@example.test", "password-12345", name="GM", role="owner")
        self.player = User.objects.create_user("builder-player@example.test", "password-12345", name="Player")
        self.streamer = User.objects.create_user("builder-streamer@example.test", None, name="Streamer")
        self.campaign = Campaign.objects.create(owner=self.gm, name="Builder campaign")
        self.other = Campaign.objects.create(owner=self.gm, name="Another campaign")
        self.membership = Membership.objects.create(campaign=self.campaign, user=self.gm, role="gm")
        Membership.objects.create(campaign=self.other, user=self.gm, role="gm")
        Membership.objects.create(campaign=self.campaign, user=self.player, role="player")
        Membership.objects.create(campaign=self.campaign, user=self.streamer, role="streamer")
        self.folder = Folder.objects.create(campaign=self.campaign, label="Builder maps")
        self.foreign_folder = Folder.objects.create(campaign=self.other, label="Foreign maps")
        self.floor = self.asset("floor.png", "#b02020")
        self.wall = self.asset("wall.png", "#888888")
        self.door = self.asset("door.png", "#20b020")
        self.foreign_asset = self.asset("foreign.png", "#2020b0", campaign=self.other)
        self.client.force_login(self.gm)
        self.project_id = uuid.uuid4()
        self.base = f"/api/containers/{self.campaign.pk}/map-builder"
        self.url = f"{self.base}/projects/{self.project_id}"
        self.doc = {
            "schemaVersion": 2, "name": "A room", "columns": 8, "rows": 8,
            "cellSize": 64, "background": "#112233",
            "assets": [{"assetId": str(asset.pk), "role": role}
                       for asset, role in ((self.floor, "floor"), (self.wall, "wall"), (self.door, "door"))],
            "floors": [{"id": str(uuid.uuid4()), "assetId": str(self.floor.pk),
                        "x": 1, "y": 1, "width": 6, "height": 6}],
            "walls": [{"id": str(uuid.uuid4()), "assetId": str(self.wall.pk),
                       "x1": 1, "y1": 3, "x2": 7, "y2": 3, "thickness": 0.5}],
            "doors": [],
        }
        self.doc["doors"].append({"id": str(uuid.uuid4()), "assetId": str(self.door.pk),
                                   "x1": 3, "y1": 3, "x2": 4, "y2": 3,
                                   "thickness": 0.5, "state": "closed"})

    def asset(self, name, color, campaign=None):
        image = Image.new("RGB", (16, 16), color)
        data = BytesIO()
        image.save(data, "PNG")
        image.close()
        row = MapAsset(campaign=campaign or self.campaign, name=name, width=16, height=16)
        row.file.save(name, ContentFile(data.getvalue()), save=False)
        row.save()
        return row

    def post(self, url, payload):
        return self.client.post(url, payload, content_type="application/json")

    def save(self, **overrides):
        return self.post(self.url, {"request_id": str(uuid.uuid4()), "expected_version": 0,
                                   "folder_id": str(self.folder.pk), "document": self.doc, **overrides})

    def generate(self, **overrides):
        return self.post(self.url + "/generate", {"request_id": str(uuid.uuid4()), "expected_version": 1, **overrides})

    def files(self):
        return sorted(str(path.relative_to(self.media)) for path in self.media.rglob("*") if path.is_file())

    def test_save_reopen_list_and_update_preserve_editable_source(self):
        response = self.save()
        self.assertEqual(response.status_code, 200, response.content)
        saved = response.json()["project"]
        self.assertEqual(saved["document"], self.doc)
        self.assertEqual(saved["folderId"], str(self.folder.pk))
        self.assertEqual(saved["version"], 1)
        self.assertIsNone(saved["sceneId"])
        self.assertEqual(self.client.get(self.url).json(), response.json())
        catalog = self.client.get(self.base).json()
        self.assertEqual(catalog["projects"][0]["id"], str(self.project_id))
        self.assertEqual({row["id"] for row in catalog["assets"]}, {str(a.pk) for a in (self.floor, self.wall, self.door)})
        self.assertEqual(catalog["limits"]["maxPixels"], 16_777_216)
        changed = deepcopy(self.doc)
        changed["name"] = "The renamed room"
        updated = self.save(expected_version=1, document=changed)
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(updated.json()["project"]["version"], 2)
        self.assertFalse(Scene.objects.exists())

    def test_save_retries_are_idempotent_and_request_identity_cannot_be_reused(self):
        request_id = str(uuid.uuid4())
        first = self.save(request_id=request_id)
        self.assertEqual(self.save(request_id=request_id).json(), first.json())
        self.assertEqual(MapBuilderProject.objects.count(), 1)
        changed = deepcopy(self.doc)
        changed["name"] = "Another operation"
        self.assertEqual(self.save(request_id=request_id, document=changed).status_code, 409)
        self.assertEqual(self.generate(request_id=request_id).status_code, 409)
        self.assertEqual(Receipt.objects.count(), 1)

    def test_stale_save_is_conflict_without_overwriting(self):
        self.assertEqual(self.save().status_code, 200)
        stale = self.save()
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["code"], "conflict")
        self.assertEqual(MapBuilderProject.objects.get().version, 1)
        self.assertEqual(Receipt.objects.count(), 1)

    def test_apis_reject_anonymous_player_streamer_and_removed_members(self):
        self.assertEqual(self.save().status_code, 200)
        for user in (self.player, self.streamer, None):
            if user:
                self.client.force_login(user)
            else:
                self.client.logout()
            with self.subTest(user=user):
                for response in (self.client.get(self.base), self.client.get(self.url), self.save(), self.generate()):
                    self.assertIn(response.status_code, (403, 404))
        self.client.force_login(self.gm)
        self.membership.delete()
        self.assertEqual(self.client.get(self.base).status_code, 404)
        self.assertEqual(self.generate().status_code, 404)
        self.assertFalse(Scene.objects.exists())

    def test_cross_campaign_project_and_folder_are_rejected(self):
        foreign = MapBuilderProject.objects.create(campaign=self.other, name="Secret", document=self.doc)
        foreign_url = f"{self.base}/projects/{foreign.pk}"
        self.assertEqual(self.client.get(foreign_url).status_code, 404)
        payload = {"request_id": str(uuid.uuid4()), "expected_version": 1, "document": self.doc}
        self.assertEqual(self.post(foreign_url, payload).status_code, 404)
        self.assertEqual(self.save(folder_id=str(self.foreign_folder.pk)).status_code, 400)
        self.assertEqual(MapBuilderProject.objects.count(), 1)

    def test_asset_ownership_classification_and_references_are_enforced(self):
        for mutate in (
            lambda doc: doc["assets"].append({"assetId": str(self.foreign_asset.pk), "role": "floor"}),
            lambda doc: doc["floors"][0].update(assetId=str(self.door.pk)),
            lambda doc: doc["assets"].append(doc["assets"][0]),
            lambda doc: doc["walls"][0].update(assetId=str(uuid.uuid4())),
        ):
            doc = deepcopy(self.doc)
            mutate(doc)
            with self.subTest(doc=doc):
                self.assertEqual(self.save(document=doc).status_code, 400)
        self.assertFalse(MapBuilderProject.objects.exists())

    def test_schema_rejects_unknown_fields_nonfinite_numbers_boolean_dimensions_and_duplicate_ids(self):
        changes = (
            lambda d: d.update(untrusted="value"),
            lambda d: d.update(columns=True),
            lambda d: d.update(columns=10 ** 1000),
            lambda d: d.update(schemaVersion=3),
            lambda d: d["walls"][0].update(thickness=float("inf")),
            lambda d: d["floors"][0].update(width=-1),
            lambda d: d["walls"][0].update(id=d["floors"][0]["id"]),
            lambda d: d["walls"][0].update(x2=20),
            lambda d: d["floors"][0].update(x=7),
        )
        for change in changes:
            doc = deepcopy(self.doc)
            change(doc)
            # Infinity is accepted by Python's encoder to exercise server rejection.
            response = self.post(self.url, {"request_id": str(uuid.uuid4()), "expected_version": 0, "document": doc})
            self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(Receipt.objects.exists())

    def test_doors_require_finite_bounded_endpoints_thickness_and_state(self):
        changes = (
            lambda d: d["doors"][0].update(x1=True),
            lambda d: d["doors"][0].update(x2="4"),
            lambda d: d["doors"][0].update(x2=float("nan")),
            lambda d: d["doors"][0].update(y2=float("inf")),
            lambda d: d["doors"][0].update(x2=3),
            lambda d: d["doors"][0].update(x2=3.1),
            lambda d: d["doors"][0].update(x1=-1),
            lambda d: d["doors"][0].update(y2=9),
            lambda d: d["doors"][0].update(thickness=0),
            lambda d: d["doors"][0].update(thickness=3),
            lambda d: d["doors"][0].update(thickness=True),
            lambda d: d["doors"][0].update(wallId=self.doc["walls"][0]["id"]),
            lambda d: d["doors"][0].update(assetId=str(self.floor.pk)),
            lambda d: d["doors"][0].update(state="broken"),
        )
        for change in changes:
            doc = deepcopy(self.doc)
            change(doc)
            with self.subTest(doc=doc):
                self.assertEqual(self.save(document=doc).status_code, 400)
        too_wide = deepcopy(self.doc)
        too_wide.update(columns=32)
        too_wide["doors"][0].update(x1=1, x2=22)
        self.assertEqual(self.save(document=too_wide).status_code, 400)

    def test_independent_doors_generate_without_walls_in_each_orientation(self):
        self.doc["walls"] = []
        self.doc["doors"] = [
            {**self.doc["doors"][0], "id": str(uuid.uuid4()), "x1": x1, "y1": y1, "x2": x2, "y2": y2}
            for x1, y1, x2, y2 in ((1, 1, 3, 1), (5, 1, 5, 3), (1, 5, 3, 7))
        ]
        self.assertEqual(self.save().status_code, 200)
        response = self.generate()
        self.assertEqual(response.status_code, 200, response.content)
        scene = Scene.objects.get(pk=response.json()["scene"]["id"])
        native = list(scene.elements.all())
        self.assertEqual(len(native), 3)
        for source in self.doc["doors"]:
            row = scene.elements.get(pk=uuid.uuid5(scene.pk, source["id"]))
            self.assertEqual(row.data["kind"], "door")
            self.assertEqual(row.data["door_state"], "closed")
            self.assertEqual(row.data["asset_id"], str(self.door.pk))
            self.assertEqual(row.data["thickness"], source["thickness"] * 64)
            for key in ("x1", "y1", "x2", "y2"):
                self.assertEqual(row.data[key], source[key] * 64)

    def test_touching_doors_and_noncollinear_crossings_are_allowed(self):
        self.doc["walls"] = []
        first = self.doc["doors"][0]
        self.doc["doors"].extend([
            {**first, "id": str(uuid.uuid4()), "x1": 4, "x2": 5},
            {**first, "id": str(uuid.uuid4()), "x1": 3.5, "x2": 3.5, "y1": 2, "y2": 4},
        ])
        self.assertEqual(self.save().status_code, 200)

    def test_collinear_door_overlap_is_rejected_in_both_directions(self):
        for x1, x2 in ((3.5, 4.5), (4.5, 3.5), (4, 3), (2, 5)):
            doc = deepcopy(self.doc)
            doc["doors"].append({**doc["doors"][0], "id": str(uuid.uuid4()), "x1": x1, "x2": x2})
            with self.subTest(x1=x1, x2=x2):
                self.assertEqual(self.save(document=doc).status_code, 400)

    def test_legacy_linked_doors_upgrade_to_independent_geometry_without_losing_art(self):
        legacy = deepcopy(self.doc)
        legacy["schemaVersion"] = 1
        legacy["doors"] = [{"id": self.doc["doors"][0]["id"], "assetId": str(self.door.pk),
                            "wallId": legacy["walls"][0]["id"], "offset": 2, "width": 1, "state": "closed"}]
        response = self.save(document=legacy)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["project"]["document"], self.doc)
        self.assertEqual(MapBuilderProject.objects.get().document, self.doc)
        self.assertEqual(self.client.get(self.url).json()["project"]["document"], self.doc)

    def test_legacy_reversed_diagonal_geometry_uses_original_wall_direction(self):
        legacy = deepcopy(self.doc)
        legacy.update(schemaVersion=1)
        wall = legacy["walls"][0]
        wall.update(x1=6, y1=6, x2=2, y2=2, thickness=0.3)
        legacy["doors"] = [{"id": self.doc["doors"][0]["id"], "assetId": str(self.door.pk),
                            "wallId": wall["id"], "offset": 2 ** 0.5, "width": 2 ** 0.5, "state": "locked"}]
        response = self.save(document=legacy)
        self.assertEqual(response.status_code, 200, response.content)
        door = response.json()["project"]["document"]["doors"][0]
        self.assertEqual(door["id"], legacy["doors"][0]["id"])
        self.assertEqual(door["state"], "locked")
        self.assertEqual(door["assetId"], str(self.door.pk))
        self.assertEqual(door["thickness"], 0.3)
        for key, value in (("x1", 5), ("y1", 5), ("x2", 4), ("y2", 4)):
            self.assertAlmostEqual(door[key], value)
        self.assertNotIn("wallId", door)

    def test_invalid_legacy_doors_still_require_valid_original_wall_intervals(self):
        legacy = deepcopy(self.doc)
        legacy["schemaVersion"] = 1
        legacy["doors"] = [{"id": self.doc["doors"][0]["id"], "assetId": str(self.door.pk),
                            "wallId": legacy["walls"][0]["id"], "offset": 2, "width": 1, "state": "closed"}]
        for update in ({"wallId": str(uuid.uuid4())}, {"offset": 5.5}, {"width": 0}):
            doc = deepcopy(legacy)
            doc["doors"][0].update(update)
            self.assertEqual(self.save(document=doc).status_code, 400)

    def test_minimum_width_legacy_diagonal_can_be_saved_again_after_conversion(self):
        legacy = deepcopy(self.doc)
        legacy["schemaVersion"] = 1
        wall = legacy["walls"][0]
        wall.update(x1=6, y1=6, x2=0, y2=0)
        legacy["doors"] = [{"id": self.doc["doors"][0]["id"], "assetId": str(self.door.pk),
                            "wallId": wall["id"], "offset": 2 ** 0.5, "width": 0.25, "state": "closed"}]
        converted = self.save(document=legacy)
        self.assertEqual(converted.status_code, 200, converted.content)
        canonical = converted.json()["project"]["document"]
        saved = self.save(document=canonical, expected_version=1)
        self.assertEqual(saved.status_code, 200, saved.content)
        self.assertEqual(saved.json()["project"]["document"], canonical)

    def test_existing_legacy_project_generates_without_an_intermediate_save(self):
        legacy = deepcopy(self.doc)
        legacy["schemaVersion"] = 1
        legacy["doors"] = [{"id": self.doc["doors"][0]["id"], "assetId": str(self.door.pk),
                            "wallId": legacy["walls"][0]["id"], "offset": 2, "width": 1, "state": "closed"}]
        row = MapBuilderProject.objects.create(
            id=self.project_id, campaign=self.campaign, folder=self.folder,
            name=legacy["name"], document=legacy, version=1,
        )
        response = self.generate()
        self.assertEqual(response.status_code, 200, response.content)
        scene = Scene.objects.get(pk=response.json()["scene"]["id"])
        door = scene.elements.get(pk=uuid.uuid5(scene.pk, legacy["doors"][0]["id"]))
        self.assertEqual((door.data["x1"], door.data["y1"], door.data["x2"], door.data["y2"]),
                         (192, 192, 256, 192))
        row.refresh_from_db()
        self.assertEqual(row.document, legacy)
        self.assertEqual(row.version, 1)

    def test_moving_and_deleting_wall_preserves_independent_door(self):
        self.assertEqual(self.save().status_code, 200)
        self.doc["walls"][0].update(y1=4, y2=4)
        moved = self.save(expected_version=1)
        self.assertEqual(moved.status_code, 200, moved.content)
        self.assertEqual(moved.json()["project"]["document"]["doors"], self.doc["doors"])
        self.doc["walls"] = []
        removed = self.save(expected_version=2)
        self.assertEqual(removed.status_code, 200, removed.content)
        self.assertEqual(removed.json()["project"]["document"]["doors"], self.doc["doors"])
        response = self.generate(expected_version=3)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(SceneObject.objects.count(), 1)
        self.assertEqual(SceneObject.objects.get().data["kind"], "door")

    def test_fragmented_native_geometry_is_bounded_before_rendering(self):
        self.doc.update(columns=200, rows=2, cellSize=16, floors=[])
        self.doc["walls"] = [{**self.doc["walls"][0], "id": str(uuid.uuid4()),
                              "x1": 0, "y1": 1, "x2": 200, "y2": 1, "thickness": 0.05}
                             for _ in range(72)]
        self.doc["doors"] = [{**self.doc["doors"][0], "id": str(uuid.uuid4()),
                              "x1": 2 * i + 1, "y1": 1, "x2": 2 * i + 2, "y2": 1}
                             for i in range(70)]
        with patch("gravewright.maps.builder_render.render", side_effect=AssertionError("Unexpected render")):
            response = self.save()
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("segments", response.json()["error"])
        self.assertFalse(MapBuilderProject.objects.exists())

    def test_raster_and_object_complexity_are_bounded(self):
        too_large = deepcopy(self.doc)
        too_large.update(columns=200, rows=200, cellSize=256)
        self.assertEqual(self.save(document=too_large).status_code, 400)
        too_many = deepcopy(self.doc)
        too_many["floors"] = [{**self.doc["floors"][0], "id": str(uuid.uuid4())} for _ in range(2001)]
        self.assertEqual(self.save(document=too_many).status_code, 400)
        overlapping = deepcopy(self.doc)
        overlapping["floors"] *= 1000
        self.assertEqual(self.save(document=overlapping).status_code, 400)

    def test_generate_private_scene_and_tiles_preserves_broadcast_with_private_navigation(self):
        active = Scene.objects.create(campaign=self.campaign, name="Running game", width=100, height=100)
        Broadcast.objects.create(campaign=self.campaign, scene=active)
        SceneNavigation.objects.create(membership=self.membership, scene=active)
        self.assertEqual(self.save().status_code, 200)
        response = self.generate()
        self.assertEqual(response.status_code, 200, response.content)
        scene = Scene.objects.get(pk=response.json()["scene"]["id"])
        self.assertEqual((scene.width, scene.height, scene.visibility), (512, 512, "gm"))
        self.assertEqual(scene.folder, self.folder)
        self.assertEqual(scene.settings["gridSize"], 64)
        self.assertEqual(Tile.objects.filter(scene=scene).count(), 1)
        self.assertEqual(Broadcast.objects.get().scene, active)
        self.assertEqual(SceneNavigation.objects.get().scene, scene)
        project = MapBuilderProject.objects.get()
        self.assertEqual(project.scene, scene)
        self.assertEqual(project.version, 1)
        self.assertEqual(project.document, self.doc)
        self.client.force_login(self.player)
        self.assertEqual(self.client.get(f"/api/maps/{scene.pk}/manifest").status_code, 404)
        self.assertEqual(self.client.get(f"/api/maps/{scene.pk}/tiles/0/0/0.webp").status_code, 404)

    def test_door_replaces_wall_span_and_preserves_native_opening_behavior(self):
        self.assertEqual(self.save().status_code, 200)
        response = self.generate()
        self.assertEqual(response.status_code, 200, response.content)
        scene = Scene.objects.get(pk=response.json()["scene"]["id"])
        walls = list(scene.elements.order_by("data__x1"))
        self.assertEqual(len(walls), 3)
        self.assertEqual([(row.data["x1"], row.data["x2"]) for row in walls], [(64, 192), (192, 256), (256, 448)])
        self.assertEqual([row.data["kind"] for row in walls], ["wall", "door", "wall"])
        door = walls[1]
        self.assertEqual(door.data["asset_id"], str(self.door.pk))
        self.assertEqual(door.data["thickness"], 32)
        services.command(self.campaign.pk, self.gm.pk, "objects", {
            "mapId": str(scene.pk), "area": "walls", "action": "door",
            "data": {"wall_id": str(door.pk), "door_state": "open"},
        }, uuid.uuid4())
        door.refresh_from_db()
        self.assertEqual(door.data["door_state"], "open")
        self.assertEqual(door.data["asset_id"], str(self.door.pk))
        with scene.tiles.get().file.open("rb") as stream, Image.open(stream) as image:
            self.assertEqual(image.getpixel((224, 192))[:3], (176, 32, 32))
            self.assertEqual(image.getpixel((128, 192))[:3], (136, 136, 136))

    def test_generation_retry_returns_same_scene_without_creating_tiles_twice(self):
        self.save()
        request_id = str(uuid.uuid4())
        first = self.generate(request_id=request_id)
        files = self.files()
        with patch("gravewright.maps.builder_render.render", side_effect=AssertionError("Replay must not render")):
            second = self.generate(request_id=request_id)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(Scene.objects.count(), 1)
        self.assertEqual(Tile.objects.count(), 1)
        self.assertEqual(files, self.files())

    def test_generation_failure_rolls_back_and_cleans_written_tiles(self):
        self.save()
        files = self.files()
        with patch("gravewright.maps.builder_services.native_objects", side_effect=OSError("synthetic failure")):
            with self.assertRaisesRegex(OSError, "synthetic failure"):
                self.generate()
        self.assertFalse(Scene.objects.exists())
        self.assertFalse(Tile.objects.exists())
        self.assertEqual(Receipt.objects.count(), 1)
        self.assertEqual(self.files(), files)

    def test_storage_failure_after_partial_write_removes_the_attempted_tile(self):
        self.save()
        files = self.files()
        original = default_storage.save

        def partial_write(name, content):
            original(name, ContentFile(b"synthetic partial tile"))
            raise OSError("synthetic disk failure")

        with patch.object(default_storage, "save", side_effect=partial_write):
            with self.assertRaisesRegex(OSError, "synthetic disk failure"):
                self.generate()
        self.assertFalse(Scene.objects.exists())
        self.assertFalse(Tile.objects.exists())
        self.assertEqual(Receipt.objects.count(), 1)
        self.assertEqual(self.files(), files)

    def test_storage_rename_cleanup_preserves_a_preexisting_candidate(self):
        self.save()
        collision = uuid.uuid4()
        candidate = "maps/tiles/" + collision.hex + ".webp"
        default_storage.save(candidate, ContentFile(b"older private tile"))
        files = self.files()
        with patch("gravewright.maps.builder_services.uuid.uuid4", return_value=collision), patch(
            "gravewright.maps.builder_services.native_objects", side_effect=OSError("synthetic rollback")
        ):
            with self.assertRaisesRegex(OSError, "synthetic rollback"):
                self.generate()
        with default_storage.open(candidate, "rb") as stream:
            self.assertEqual(stream.read(), b"older private tile")
        self.assertEqual(self.files(), files)
        self.assertFalse(Scene.objects.exists())

    def test_generation_rechecks_revision_after_expensive_rendering(self):
        self.save()
        files = self.files()
        original = tiling.generate_pyramid

        def changed(*args, **kwargs):
            result = original(*args, **kwargs)
            MapBuilderProject.objects.filter(pk=self.project_id).update(version=2)
            return result

        with patch("gravewright.maps.builder_services.tiling.generate_pyramid", side_effect=changed):
            result = self.generate()
        self.assertEqual(result.status_code, 409)
        self.assertFalse(Scene.objects.exists())
        self.assertEqual(self.files(), files)

    def test_generation_rechecks_role_after_expensive_rendering(self):
        self.save()
        files = self.files()
        original = tiling.generate_pyramid

        def changed(*args, **kwargs):
            result = original(*args, **kwargs)
            Membership.objects.filter(pk=self.membership.pk).update(role="player")
            return result

        with patch("gravewright.maps.builder_services.tiling.generate_pyramid", side_effect=changed):
            result = self.generate()
        self.assertEqual(result.status_code, 403)
        self.assertFalse(Scene.objects.exists())
        self.assertEqual(self.files(), files)

    def test_missing_asset_is_reported_before_rendering(self):
        self.save()
        self.floor.delete()
        with patch("gravewright.maps.builder_render.render", side_effect=AssertionError("Missing asset")):
            result = self.generate()
        self.assertEqual(result.status_code, 400)
        self.assertIn("asset", result.json()["error"])
        self.assertFalse(Scene.objects.exists())

    def test_notifications_are_registered_after_commit_only(self):
        self.save()
        with patch("gravewright.realtime.dispatch.send") as send:
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                self.assertEqual(self.generate().status_code, 200)
            self.assertFalse(send.called)
            self.assertGreaterEqual(len(callbacks), 1)


class BuilderSegmentTests(SimpleTestCase):
    def wall(self, x1, y1, x2, y2):
        return {"id": str(uuid.uuid4()), "assetId": None, "thickness": 0.5,
                "x1": x1, "y1": y1, "x2": x2, "y2": y2}

    def document(self, walls, doors):
        return {"cellSize": 64, "walls": walls, "doors": doors}

    def geometry(self, span):
        return tuple(span[key] for key in ("x1", "y1", "x2", "y2"))

    def test_reversed_door_cuts_multiple_collinear_wall_strokes_once(self):
        walls = [self.wall(1, 3, 4, 3), self.wall(7, 3, 4, 3)]
        door = {**self.wall(5, 3, 3, 3), "state": "closed"}
        spans = list(builder_services.segments(self.document(walls, [door])))
        self.assertEqual([self.geometry(row) for row in spans],
                         [(1, 3, 3, 3), (7, 3, 5, 3), (5, 3, 3, 3)])
        self.assertEqual(sum(row["door"] is not None for row in spans), 1)
        self.assertEqual(spans[-1]["door"]["id"], door["id"])

    def test_vertical_and_diagonal_wall_openings_preserve_exact_door_geometry(self):
        cases = [
            ((2, 1, 2, 7), (2, 3, 2, 5), [(2, 1, 2, 3), (2, 5, 2, 7)]),
            ((1, 1, 7, 7), (5, 5, 3, 3), [(1, 1, 3, 3), (5, 5, 7, 7)]),
        ]
        for wall_coordinates, door_coordinates, expected in cases:
            door = {**self.wall(*door_coordinates), "state": "open"}
            spans = list(builder_services.segments(self.document([self.wall(*wall_coordinates)], [door])))
            with self.subTest(wall=wall_coordinates):
                self.assertEqual(len(spans), 3)
                for span, coordinates in zip(spans[:-1], expected):
                    for value, target in zip(self.geometry(span), coordinates):
                        self.assertAlmostEqual(value, target)
                self.assertEqual(self.geometry(spans[-1]), door_coordinates)

    def test_noncollinear_crossing_does_not_cut_wall(self):
        wall = self.wall(1, 3, 7, 3)
        door = {**self.wall(4, 2, 4, 4), "state": "closed"}
        spans = list(builder_services.segments(self.document([wall], [door])))
        self.assertEqual([self.geometry(row) for row in spans], [(1, 3, 7, 3), (4, 2, 4, 4)])

    def test_parallel_offset_door_does_not_cut_wall(self):
        wall = self.wall(1, 3, 7, 3)
        door = {**self.wall(3, 3.01, 4, 3.01), "state": "closed"}
        spans = list(builder_services.segments(self.document([wall], [door])))
        self.assertEqual([self.geometry(row) for row in spans], [(1, 3, 7, 3), (3, 3.01, 4, 3.01)])

    def test_door_covering_wall_omits_wall_completely(self):
        wall = self.wall(3, 3, 4, 3)
        door = {**self.wall(2, 3, 5, 3), "state": "closed"}
        spans = list(builder_services.segments(self.document([wall], [door])))
        self.assertEqual(len(spans), 1)
        self.assertEqual(self.geometry(spans[0]), (2, 3, 5, 3))
        self.assertIs(spans[0]["door"], door)

    def test_touching_doors_leave_no_wall_between_their_endpoints(self):
        wall = self.wall(1, 3, 7, 3)
        doors = [{**self.wall(3, 3, 4, 3), "state": "open"},
                 {**self.wall(4, 3, 5, 3), "state": "closed"}]
        spans = list(builder_services.segments(self.document([wall], doors)))
        self.assertEqual([self.geometry(row) for row in spans],
                         [(1, 3, 3, 3), (5, 3, 7, 3), (3, 3, 4, 3), (4, 3, 5, 3)])


class BuilderPreparationTests(SimpleTestCase):
    def test_second_render_waits_until_first_raster_is_tiled_and_closed(self):
        tiling_started = threading.Event()
        release_tiler = threading.Event()
        second_started = threading.Event()
        second_rendered = threading.Event()
        first_raster, second_raster = Mock(), Mock()
        calls = []

        def render(doc, campaign_id):
            calls.append(doc["id"])
            if doc["id"] == 1:
                return first_raster
            self.assertTrue(first_raster.close.called)
            second_rendered.set()
            return second_raster

        def tile(raster, callback):
            if raster is first_raster:
                tiling_started.set()
                self.assertTrue(release_tiler.wait(5))
            return 16, 16, 0

        def second():
            second_started.set()
            return builder_services.prepare({"id": 2, "floors": [], "walls": []}, uuid.uuid4(), [], [])

        with patch("gravewright.maps.builder_render.render", side_effect=render), patch(
            "gravewright.maps.builder_services.tiling.generate_pyramid", side_effect=tile
        ), ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(builder_services.prepare, {"id": 1, "floors": [], "walls": []}, uuid.uuid4(), [], [])
            try:
                self.assertTrue(tiling_started.wait(5))
                waiting = pool.submit(second)
                self.assertTrue(second_started.wait(5))
                self.assertFalse(second_rendered.wait(0.1))
            finally:
                release_tiler.set()
            self.assertEqual(first.result(timeout=5), (16, 16, 0))
            self.assertEqual(waiting.result(timeout=5), (16, 16, 0))
        self.assertEqual(calls, [1, 2])
        first_raster.close.assert_called_once()
        second_raster.close.assert_called_once()
