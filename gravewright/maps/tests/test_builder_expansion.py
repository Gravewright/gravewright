"""Expanded sources preserve layer organization and generate live native objects."""

from copy import deepcopy
from io import BytesIO
import uuid

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from PIL import Image

from gravewright.maps import builder_services, extra_objects
from gravewright.maps.models import MapAsset, Scene
from . import test_builder_projects as fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class BuilderExpansionTests(TestCase):
    setUp = fixtures.BuilderProjectTests.setUp
    asset = fixtures.BuilderProjectTests.asset
    post = fixtures.BuilderProjectTests.post
    save = fixtures.BuilderProjectTests.save
    generate = fixtures.BuilderProjectTests.generate
    files = fixtures.BuilderProjectTests.files

    def expanded(self):
        doc = deepcopy(self.doc)
        doc["schemaVersion"] = 3
        layer_id = str(uuid.uuid4())
        doc["layers"] = [{"id": layer_id, "name": "Furniture", "visible": False, "locked": True}]
        for kind in ("floors", "walls", "doors"):
            for row in doc[kind]:
                row["layerId"] = layer_id
        doc["floors"][0]["rotation"] = 90
        doc["assets"][0].update(name="Red floor", collection="Stone")
        art = self.asset("table.png", "#aa3300")
        doc["assets"].append({"assetId": str(art.pk), "role": "decoration", "collection": "Tavern"})
        doc["decorations"] = [{"id": str(uuid.uuid4()), "assetId": str(art.pk), "layerId": layer_id,
                               "x": 2, "y": 2, "width": 2, "height": 1, "rotation": 45}]
        doc["lights"] = [{"id": str(uuid.uuid4()), "layerId": layer_id, "x": 4, "y": 5,
                          "brightRadius": 2, "dimRadius": 4, "color": "#ffd8a8", "intensity": .8,
                          "enabled": True, "rotation": 90, "angle": 360, "animation": "torch"}]
        return doc

    def test_layers_metadata_and_native_decoration_and_lights_roundtrip(self):
        doc = self.expanded()
        response = self.save(document=doc)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["project"]["document"], doc)
        response = self.generate()
        self.assertEqual(response.status_code, 200, response.content)
        scene = Scene.objects.get()
        image = scene.elements.get(kind="images")
        self.assertEqual(image.pk, uuid.uuid5(scene.pk, doc["decorations"][0]["id"]))
        self.assertEqual((image.data["x"], image.data["y"], image.data["scale"]), (192, 160, 4))
        self.assertEqual(image.data["rotation"], 45)
        light = scene.elements.get(kind="lights")
        self.assertEqual((light.data["x"], light.data["y"]), (256, 320))
        self.assertEqual(light.data["bright_radius"], 2)
        self.assertEqual(light.data["animation"], "torch")
        self.assertEqual(scene.environment.lighting, {"mode": "dynamic", "darkness": 1, "lights_out": False})
        self.assertTrue(response.json()["project"]["canUpdate"])

    def test_layer_and_object_validation_is_bounded_and_campaign_scoped(self):
        original = self.expanded()
        mutations = [
            lambda d: d.update(layers=[]),
            lambda d: d["layers"].append(deepcopy(d["layers"][0])),
            lambda d: d["layers"][0].update(visible="true"),
            lambda d: d["floors"][0].update(layerId=str(uuid.uuid4())),
            lambda d: d["floors"][0].update(rotation=45),
            lambda d: d["decorations"][0].update(x=0, y=0, rotation=45),
            lambda d: d["decorations"][0].update(assetId=str(self.foreign_asset.pk)),
            lambda d: d["lights"][0].update(brightRadius=float("nan")),
            lambda d: d["lights"][0].update(enabled=1),
            lambda d: d["assets"][0].update(collection="x" * 81),
            lambda d: d["lights"][0].update(id=d["doors"][0]["id"]),
        ]
        for change in mutations:
            doc = deepcopy(original)
            change(doc)
            with self.subTest(doc=doc):
                response = self.save(document=doc)
                self.assertEqual(response.status_code, 400, response.content)

    def test_extreme_fitted_decorations_generate_update_and_clone_with_editable_boxes(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        from gravewright.maps.blueprint_actions import validate_campaign_sprites

        for pixels, box in (((1024, 1024), (.05, .05)), ((1, 1), (8, 8)), ((2048, 1), (.05, .05))):
            with self.subTest(pixels=pixels, box=box):
                self.project_id = uuid.uuid4()
                self.url = f"{self.base}/projects/{self.project_id}"
                doc = self.expanded()
                doc["cellSize"] = 16
                source = doc["decorations"][0]
                source.update(x=0, y=0, width=box[0], height=box[1], rotation=0)
                asset = MapAsset.objects.get(pk=source["assetId"])
                output = BytesIO()
                with Image.new("RGB", pixels, "#aa3300") as image:
                    image.save(output, "PNG")
                asset.width, asset.height = pixels
                asset.file.save("fitted-decoration.png", ContentFile(output.getvalue()))
                saved = self.save(document=doc)
                self.assertEqual(saved.status_code, 200, saved.content)
                generated = self.generate()
                self.assertEqual(generated.status_code, 200, generated.content)
                scene = Scene.objects.get(pk=generated.json()["scene"]["id"])
                row = scene.elements.get(kind="images")
                scale = min(box[0] * 16 / pixels[0], box[1] * 16 / pixels[1])
                self.assertFalse(.001 <= scale <= 100)
                self.assertEqual(row.data["scale"], scale)
                self.assertEqual(row.data["spriteBase"], {
                    "assetId": str(asset.pk), "layer": "map", "width": box[0] * 16, "height": box[1] * 16})
                moved = extra_objects.image(scene, {"x": row.data["x"] + 1}, row.data)
                self.assertEqual(moved["scale"], scale)
                self.assertEqual(moved["spriteBase"], row.data["spriteBase"])
                validate_campaign_sprites(self.campaign)
                doc["name"] = "Updated fitted decoration"
                self.assertEqual(self.save(document=doc, expected_version=1).status_code, 200)
                updated = builder_services.update(self.campaign.pk, self.gm.pk, self.project_id, {
                    "request_id": str(uuid.uuid4()), "expected_version": 2, "expected_scene_version": scene.version})
                self.assertEqual(updated["scene"]["id"], str(scene.pk))
                row.refresh_from_db()
                self.assertEqual(row.data["scale"], scale)
                clone = import_campaign(export_campaign(self.campaign), self.gm, "Fitted decoration clone")
                validate_campaign_sprites(clone)

    def test_deleted_decoration_material_preserves_source_geometry(self):
        doc = self.expanded()
        self.assertEqual(self.save(document=doc).status_code, 200)
        builder_services.detach_project_art(self.campaign.pk, doc["decorations"][0]["assetId"])
        saved = self.client.get(self.url).json()["project"]
        self.assertIsNone(saved["document"]["decorations"][0]["assetId"])
        self.assertEqual(saved["document"]["decorations"][0]["width"], 2)
        self.assertEqual(saved["version"], 2)
