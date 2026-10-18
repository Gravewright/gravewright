"""Expanded sources preserve layer organization and generate live native objects."""

from copy import deepcopy
import uuid

from django.test import TestCase, override_settings

from gravewright.maps import builder_services
from gravewright.maps.models import Scene
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

    def test_deleted_decoration_material_preserves_source_geometry(self):
        doc = self.expanded()
        self.assertEqual(self.save(document=doc).status_code, 200)
        builder_services.detach_project_art(self.campaign.pk, doc["decorations"][0]["assetId"])
        saved = self.client.get(self.url).json()["project"]
        self.assertIsNone(saved["document"]["decorations"][0]["assetId"])
        self.assertEqual(saved["document"]["decorations"][0]["width"], 2)
        self.assertEqual(saved["version"], 2)
