"""Empty projects keep manual layers explicit and never accept orphaned objects."""

from copy import deepcopy
import uuid

from django.test import TestCase, override_settings
from PIL import Image

from gravewright.maps import builder_render, builder_services, objects
from gravewright.maps.models import MapBuilderProject, Scene, SceneObject

from . import test_builder_projects as fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow")
class BuilderLayerTests(TestCase):
    setUp = fixtures.BuilderProjectTests.setUp
    asset = fixtures.BuilderProjectTests.asset
    post = fixtures.BuilderProjectTests.post
    save = fixtures.BuilderProjectTests.save
    generate = fixtures.BuilderProjectTests.generate
    files = fixtures.BuilderProjectTests.files

    def empty(self):
        document = deepcopy(self.doc)
        document.update(schemaVersion=3, layers=[])
        for kind in ("floors", "walls", "doors", "decorations", "lights", "particles", "shaders"):
            document[kind] = []
        return document

    def test_layerless_document_and_asset_library_save_reopen_without_inserted_defaults(self):
        document = self.empty()
        self.assertTrue(document["assets"])
        before = deepcopy(document)
        self.assertEqual(builder_services.clean_document(document, self.membership), before)
        saved = self.save(document=document)
        self.assertEqual(saved.status_code, 200, saved.content)
        self.assertEqual(saved.json()["project"]["document"], before)
        self.assertEqual(self.client.get(self.url).json()["project"]["document"], before)
        self.assertEqual(MapBuilderProject.objects.get(pk=self.project_id).document, before)
        self.assertEqual(document, before)

    def test_layerless_sources_preserve_omitted_optional_effect_lists(self):
        document = self.empty()
        del document["particles"], document["shaders"]
        self.assertEqual(builder_services.clean_document(document, self.membership), document)
        self.assertEqual(builder_services.clean_document(document, self.membership)["layers"], [])

    def test_each_object_kind_requires_an_existing_layer_even_in_an_empty_project(self):
        for kind in ("floors", "walls", "doors", "decorations", "lights", "particles", "shaders"):
            document = self.empty()
            document[kind].append({"id": str(uuid.uuid4()), "layerId": str(uuid.uuid4())})
            with self.subTest(kind=kind):
                response = self.save(document=document)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json()["error"], "Choose an existing map layer.")
                self.assertFalse(MapBuilderProject.objects.exists())
        document = self.empty(); del document["layers"]
        self.assertEqual(self.save(document=document).status_code, 400)

    def test_invalid_layer_containers_and_excess_layers_still_fail(self):
        for layers in (None, False, {}, "", [
                {"id": str(uuid.uuid4()), "name": f"Layer {index}", "visible": True, "locked": False}
                for index in range(33)]):
            document = self.empty(); document["layers"] = layers
            with self.subTest(layers=layers):
                response = self.save(document=document)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json()["error"], "Use up to 32 map layers.")

    def test_empty_raster_and_generated_scene_contain_only_the_authored_background(self):
        document = self.empty()
        before = deepcopy(document)
        content = builder_render.render(document, self.campaign.pk)
        self.addCleanup(content.close)
        with Image.open(content) as image:
            self.assertEqual(image.size, (512, 512))
            self.assertEqual(set(image.getdata()), {(17, 34, 51)})
        self.assertEqual(document, before)
        self.assertEqual(self.save(document=document).status_code, 200)
        result = self.generate()
        self.assertEqual(result.status_code, 200, result.content)
        scene = Scene.objects.get()
        self.assertEqual((scene.width, scene.height), (512, 512))
        self.assertFalse(scene.elements.exists())
        source = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual(source.document, before)
        self.assertEqual(source.generation["objects"], [])
        self.assertTrue(result.json()["project"]["canUpdate"])
        tile = scene.tiles.get(lod=0, x=0, y=0)
        with tile.file.open("rb") as stream, Image.open(stream) as image:
            with image.convert("RGB") as rgb:
                for actual, expected in zip(rgb.getpixel((256, 256)), (17, 34, 51)):
                    self.assertLessEqual(abs(actual - expected), 2)

    def test_updating_to_no_layers_removes_owned_content_and_preserves_manual_scene_objects(self):
        self.assertEqual(self.save().status_code, 200)
        generated = self.generate()
        self.assertEqual(generated.status_code, 200, generated.content)
        scene = Scene.objects.get()
        self.assertTrue(scene.elements.exists())
        manual = SceneObject.objects.create(scene=scene, kind="walls", data=objects.wall(
            {"x1": 20, "y1": 20, "x2": 60, "y2": 20, "kind": "wall"}))
        document = self.empty()
        self.assertEqual(self.save(document=document, expected_version=1).status_code, 200)
        updated = self.post(self.url + "/update", {"request_id": str(uuid.uuid4()),
            "expected_version": 2, "expected_scene_version": scene.version})
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(list(scene.elements.values_list("pk", flat=True)), [manual.pk])
        source = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual(source.document, document)
        self.assertEqual(source.generation["objects"], [])

    def test_legacy_documents_and_existing_schema_three_layers_retain_their_shape(self):
        original = deepcopy(self.doc)
        self.assertEqual(builder_services.clean_document(original, self.membership), original)
        self.assertNotIn("layers", builder_services.clean_document(original, self.membership))
        original.update(schemaVersion=3, layers=[{"id": str(uuid.uuid4()), "name": "Authored layer", "visible": False, "locked": True}],
                        decorations=[], lights=[])
        for kind in ("floors", "walls", "doors"):
            for row in original[kind]:
                row["layerId"] = original["layers"][0]["id"]
        original["floors"][0]["rotation"] = 0
        before = deepcopy(original)
        self.assertEqual(builder_services.clean_document(original, self.membership), before)
        self.assertEqual(original, before)
