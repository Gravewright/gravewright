"""Imported dynamic planes are bounded and cannot expose another scene's masks."""

from copy import deepcopy
from io import BytesIO
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import uuid
from zipfile import ZipFile, ZIP_DEFLATED

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from PIL import Image

from gravewright.accounts.models import User
from gravewright.accounts.services import AuthError
from gravewright.administration.archives import export_campaign, import_campaign
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps.models import Broadcast, MapAsset, MapBuilderProject, Scene, SceneObject
from gravewright.maps.services import MapError
from gravewright.maps.surface_validation import validate_campaign_surfaces


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"], ALLOWED_HOSTS=["testserver"])
class SurfaceArchiveTests(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="surface-archive-")
        self.addCleanup(self.temporary.cleanup)
        self.options = override_settings(MEDIA_ROOT=self.temporary.name)
        self.options.enable()
        self.addCleanup(self.options.disable)
        self.gm = User.objects.create_user("surface-gm@example.test", "password-12345", name="GM")
        self.player = User.objects.create_user("surface-player@example.test", "password-12345", name="Player")
        self.campaign = Campaign.objects.create(owner=self.gm, name="Surface imports")
        Membership.objects.create(campaign=self.campaign, user=self.gm, role="gm")
        Membership.objects.create(campaign=self.campaign, user=self.player, role="player")
        self.scene = Scene.objects.create(campaign=self.campaign, name="Public surface", width=1024, height=1024, visibility="players")
        self.private = Scene.objects.create(campaign=self.campaign, name="Private surface", width=1024, height=1024, visibility="gm")
        self.base = self.asset("Generated base", self.scene)
        self.mask = self.asset("Generated mask", self.scene)
        self.material = self.asset("Ordinary material")
        self.row = SceneObject.objects.create(scene=self.scene, kind="images", data={
            "asset_id": str(self.base.pk), "scene_id": str(self.scene.pk), "src": f"/game/map-assets/{self.base.pk}",
            "natural_width": 2, "natural_height": 2, "x": 1, "y": 1, "scale": 1, "rotation": 0,
            "layer": "map", "z_index": -9000,
            "surfacePlane": {"group": str(uuid.uuid4()), "order": 0, "operation": "paint"},
            "surface": {"kind": "floor", "cellSize": 64, "left": 0, "top": 0, "rotation": 0, "maskId": str(self.mask.pk)},
        })

    def asset(self, name, scene=None, *, campaign=None):
        output = BytesIO()
        with Image.new("RGBA", (2, 2), "#876b42") as image:
            image.save(output, "PNG")
        return MapAsset.objects.create(campaign=campaign or self.campaign, generated_for=scene, name=name,
            width=2, height=2, file=ContentFile(output.getvalue(), name="synthetic.png"))

    def validate(self):
        validate_campaign_surfaces(self.campaign)

    def update(self, data):
        self.row.data = deepcopy(data)
        self.row.save(update_fields=["data"])

    def corrupted_archive(self, edit):
        with ZipFile(BytesIO(export_campaign(self.campaign))) as archive:
            blobs = {name: archive.read(name) for name in archive.namelist()}
        payload = json.loads(blobs["campaign.json"])
        edit(payload)
        blobs["campaign.json"] = json.dumps(payload).encode()
        manifest = json.loads(blobs["manifest.json"])
        manifest["files"]["campaign.json"] = {"sha256": hashlib.sha256(blobs["campaign.json"]).hexdigest(), "bytes": len(blobs["campaign.json"])}
        blobs["manifest.json"] = json.dumps(manifest).encode()
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            for name, value in blobs.items():
                archive.writestr(name, value)
        return output.getvalue()

    def test_valid_roundtrip_remaps_scene_artwork_and_masks(self):
        self.validate()
        cloned = import_campaign(export_campaign(self.campaign), self.gm, "Cloned surfaces")
        copied = SceneObject.objects.get(scene__campaign=cloned, kind="images")
        self.assertNotEqual(copied.pk, self.row.pk)
        self.assertEqual(copied.data["scene_id"], str(copied.scene_id))
        self.assertEqual(MapAsset.objects.get(pk=copied.data["asset_id"]).generated_for_id, copied.scene_id)
        self.assertEqual(MapAsset.objects.get(pk=copied.data["surface"]["maskId"]).generated_for_id, copied.scene_id)
        validate_campaign_surfaces(cloned)

    def test_runtime_move_rotation_scale_visibility_and_floor_material_are_valid(self):
        data = deepcopy(self.row.data)
        data.update(x=70.5, y=80.25, scale=1.5, rotation=45, layer="gm-image-layer")
        data["surface"]["materialId"] = str(self.material.pk)
        for layer in ("map", "gm-image-layer", "gm"):
            data["layer"] = layer
            self.update(data)
            before = deepcopy(data)
            self.validate()
            self.row.refresh_from_db()
            self.assertEqual(self.row.data, before)

    def test_wall_planes_allow_null_group_and_valid_material_crop(self):
        data = deepcopy(self.row.data)
        data["surfacePlane"]["group"] = None
        data["surface"] = {"kind": "wall", "cellSize": 64, "left": 0, "top": 0, "origin": [0, 1],
            "direction": [1, 0], "phase": -.5, "thickness": 32, "maskId": str(self.mask.pk),
            "materialId": str(self.material.pk), "materialCrop": [0, 0, 2, 2]}
        self.update(data)
        self.validate()
        del data["surface"]
        self.update(data)
        self.validate()

    def test_floor_texture_rotation_keeps_valid_float_values_and_rejects_boolean_angles(self):
        original = deepcopy(self.row.data)
        for rotation in (0.0, 90.0, 180.0, 270.0):
            data = deepcopy(original)
            data["surface"]["rotation"] = rotation
            self.update(data)
            self.validate()
            self.row.refresh_from_db()
            self.assertIsInstance(self.row.data["surface"]["rotation"], float)
            self.assertEqual(self.row.data["surface"]["rotation"], rotation)
        for rotation in (False, True, 45.0, "90.0"):
            data = deepcopy(original)
            data["surface"]["rotation"] = rotation
            self.update(data)
            with self.assertRaises(MapError):
                self.validate()

    def test_plain_legacy_images_are_not_revalidated_or_rewritten(self):
        self.row.delete()
        old = SceneObject.objects.create(scene=self.scene, kind="images", data={"legacy": ["kept"], "x": "legacy coordinate"})
        self.validate()
        old.refresh_from_db()
        self.assertEqual(old.data, {"legacy": ["kept"], "x": "legacy coordinate"})
        cloned = import_campaign(export_campaign(self.campaign), self.gm, "Legacy archive")
        self.assertEqual(SceneObject.objects.get(scene__campaign=cloned).data, old.data)

    def test_markers_reject_unknown_keys_bad_types_and_invalid_plane_discriminants(self):
        original = deepcopy(self.row.data)
        mutations = [lambda data: data.update(surface=None), lambda data: data["surface"].update(recipe={}),
            lambda data: data["surface"].update(cellSize=True), lambda data: data["surface"].update(rotation=45),
            lambda data: data["surface"].update(left=-1), lambda data: data["surface"].update(top="0"),
            lambda data: data["surfacePlane"].update(extra=True), lambda data: data["surfacePlane"].update(group="not-a-uuid"),
            lambda data: data["surfacePlane"].update(group="AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"),
            lambda data: data["surfacePlane"].update(group="{aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa}"),
            lambda data: data["surfacePlane"].update(group=None), lambda data: data["surfacePlane"].update(order=True),
            lambda data: data["surfacePlane"].update(operation="erase"), lambda data: data.update(natural_width=3),
            lambda data: data.update(scene_id=str(self.private.pk)), lambda data: data.update(src="/arbitrary.png"),
            lambda data: data.update(scale=0), lambda data: data.update(rotation="0")]
        for mutate in mutations:
            data = deepcopy(original)
            mutate(data)
            with self.subTest(data=data):
                self.update(data)
                with self.assertRaises(MapError):
                    self.validate()
        self.update(original)

    def test_generated_base_and_mask_must_belong_to_the_placement_scene(self):
        private_mask = self.asset("Private mask", self.private)
        data = deepcopy(self.row.data)
        data["surface"]["maskId"] = str(private_mask.pk)
        self.update(data)
        with self.assertRaises(MapError): self.validate()
        data["surface"]["maskId"] = str(self.mask.pk)
        data["asset_id"] = str(private_mask.pk)
        self.update(data)
        with self.assertRaises(MapError): self.validate()
        data = {"asset_id": str(self.base.pk)}
        self.update(data)
        with self.assertRaises(MapError): self.validate()

    def test_generated_masks_cannot_be_replaced_with_normal_foreign_or_mismatched_images(self):
        original = deepcopy(self.row.data)
        for asset in (self.material, self.base):
            data = deepcopy(original); data["surface"]["maskId"] = str(asset.pk)
            self.update(data)
            with self.assertRaises(MapError): self.validate()
        data = deepcopy(original); data["surface"]["materialId"] = str(self.mask.pk)
        self.update(data)
        with self.assertRaises(MapError): self.validate()

    def test_actual_generated_png_headers_and_metadata_must_match_before_decode(self):
        self.base.width = 3
        self.base.save(update_fields=["width"])
        with self.assertRaises(MapError): self.validate()
        self.base.width = 2
        self.base.file.save("invalid.png", ContentFile(b"not a PNG"), save=True)
        with self.assertRaises(MapError): self.validate()

    def test_too_many_groups_or_dynamic_surfaces_are_rejected_without_canvas_allocation(self):
        original = deepcopy(self.row.data)
        rows = []
        self.row.delete()
        for index in range(1000):
            data = deepcopy(original)
            del data["surface"]
            data["surfacePlane"].update(order=index, group=str(uuid.uuid4()))
            rows.append(SceneObject(scene=self.scene, kind="images", data=data))
        SceneObject.objects.bulk_create(rows)
        with self.assertRaises(MapError): self.validate()
        SceneObject.objects.filter(scene=self.scene).delete()
        rows = []
        for index in range(65):
            data = deepcopy(original); data["surfacePlane"]["order"] = index
            rows.append(SceneObject(scene=self.scene, kind="images", data=data))
        SceneObject.objects.bulk_create(rows)
        with self.assertRaises(MapError): self.validate()

    def test_aggregate_base_mask_and_group_pixels_share_the_generation_budget(self):
        # Header I/O is replaced here so the budget test allocates no 64 MB PNG.
        self.scene.width = self.scene.height = 4096
        self.scene.save(update_fields=["width", "height"])
        for asset in (self.base, self.mask):
            asset.width = asset.height = 4096
            asset.save(update_fields=["width", "height"])
        data = deepcopy(self.row.data)
        data.update(natural_width=4096, natural_height=4096, x=2048, y=2048)
        self.update(data)
        with patch("gravewright.maps.surface_validation._inspect", side_effect=lambda asset, cache, **_: (asset.width, asset.height, 0)):
            self.validate()
            duplicate = deepcopy(data); duplicate["surfacePlane"].update(order=1, group=str(uuid.uuid4()))
            SceneObject.objects.create(scene=self.scene, kind="images", data=duplicate)
            with self.assertRaises(MapError): self.validate()

    def test_private_recipe_keeps_an_independent_baseline_but_must_validate(self):
        layer = str(uuid.uuid4())
        document = {"schemaVersion": 3, "name": "Authored source", "columns": 4, "rows": 4, "cellSize": 64,
            "background": "#253038", "layers": [{"id": layer, "name": "Layer", "visible": True, "locked": False}],
            "assets": [], "floors": [{"id": str(uuid.uuid4()), "layerId": layer, "assetId": None, "x": 0, "y": 0,
                "width": 1, "height": 1, "rotation": 0, "dynamic": True}], "walls": [], "doors": [], "decorations": [],
            "lights": [], "particles": [], "shaders": [], "regions": []}
        draft = deepcopy(document); draft["floors"][0]["x"] = 1
        project = MapBuilderProject.objects.create(campaign=self.campaign, name="Recipe", document=draft,
            generation={"dynamicDocument": document})
        self.validate()
        project.refresh_from_db()
        self.assertEqual(project.document, draft)
        self.assertEqual(project.generation["dynamicDocument"], document)
        project.generation["dynamicDocument"]["cellSize"] = 1
        project.save(update_fields=["generation"])
        with self.assertRaises(MapError): self.validate()

    def test_cross_scene_mask_in_checksummed_archive_rolls_back_files_and_records(self):
        private_mask = self.asset("Private mask", self.private)
        def corrupt(payload):
            row = next(row for row in payload["records"] if row["model"] == "gravewright_maps.sceneobject")
            row["fields"]["data"]["surface"]["maskId"] = str(private_mask.pk)
        raw = self.corrupted_archive(corrupt)
        files = sorted(str(path.relative_to(self.temporary.name)) for path in Path(self.temporary.name).rglob("*") if path.is_file())
        campaigns, rows = Campaign.objects.count(), SceneObject.objects.count()
        with self.assertRaises(AuthError): import_campaign(raw, self.gm, "Corrupted surface archive")
        self.assertEqual(Campaign.objects.count(), campaigns)
        self.assertEqual(SceneObject.objects.count(), rows)
        self.assertEqual(sorted(str(path.relative_to(self.temporary.name)) for path in Path(self.temporary.name).rglob("*") if path.is_file()), files)

    def test_orphan_generated_asset_cannot_become_an_ordinary_library_asset_on_import(self):
        self.asset("Unreferenced private generated mask", self.private)
        def corrupt(payload):
            payload["records"] = [record for record in payload["records"]
                if not (record["model"] == "gravewright_maps.scene" and record["pk"] == str(self.private.pk))]
        raw = self.corrupted_archive(corrupt)
        before = Campaign.objects.count()
        with self.assertRaises(AuthError):
            import_campaign(raw, self.gm, "Orphan generated artwork")
        self.assertEqual(Campaign.objects.count(), before)

    def test_player_cannot_fetch_private_scene_mask_even_from_a_corrupt_legacy_visible_row(self):
        private_mask = self.asset("Private mask", self.private)
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        data = deepcopy(self.row.data); data["surface"]["maskId"] = str(private_mask.pk)
        self.update(data)
        self.client.force_login(self.player)
        self.assertEqual(self.client.get(f"/game/map-assets/{private_mask.pk}").status_code, 404)
        response = self.client.get(f"/game/map-assets/{self.base.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"".join(response.streaming_content))
