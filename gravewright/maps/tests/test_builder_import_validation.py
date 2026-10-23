"""Imported ownership requires a faithful snapshot and bounded validation work."""

from copy import deepcopy
import math
import uuid
from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from gravewright.maps import builder_import, objects
from gravewright.maps.models import SceneObject
from . import test_builder_import as fixtures


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
    DYNAMIC_LIGHTING_ENABLED=True,
)
class BuilderImportValidationTests(TestCase):
    setUp = fixtures.BuilderImportTests.setUp
    asset = fixtures.BuilderImportTests.asset
    post = fixtures.BuilderImportTests.post
    files = fixtures.BuilderImportTests.files
    existing_scene = fixtures.BuilderImportTests.existing_scene
    adopt = fixtures.BuilderImportTests.adopt
    update_project = fixtures.BuilderImportTests.update_project
    save_project = fixtures.BuilderImportTests.save_project

    def test_custom_door_channels_discovery_anchor_and_interaction_survive_update(self):
        scene, _, door, _ = self.existing_scene()
        door.data = objects.wall({**door.data, "door_state": "locked", "discovered": True,
                                  "rotationAnchor": "end", "interactionEnabled": False,
                                  "behavior": {"movement": "pass", "vision": "pass", "light": "block", "sound": "attenuate"}})
        door.save(update_fields=["data"])
        before = deepcopy(door.data)
        response = self.adopt(scene)
        self.assertEqual(response.status_code, 200, response.content)
        project = response.json()["project"]
        source = project["document"]["doors"][0]
        self.assertEqual(source["id"], str(door.pk))
        self.assertEqual(source["behavior"], {"movement": "pass", "vision": "pass", "light": "block", "sound": "attenuate"})
        self.assertTrue(source["discovered"])
        self.assertFalse(source["interactionEnabled"])
        self.update_project(project, scene)
        door.refresh_from_db()
        self.assertTrue(builder_import._equivalent(door.data, before))

    def test_fractional_native_coordinates_are_adopted_after_numeric_round_trip(self):
        scene, wall, _, light = self.existing_scene()
        cell = builder_import._source_document(scene)["cellSize"]
        coordinate = next(value / 1000 for value in range(1001, 10000)
                          if (value / 1000) / cell * cell != value / 1000)
        wall.data.update(x1=coordinate, x2=coordinate + 50)
        wall.save(update_fields=["data"])
        light.data["x"] = coordinate
        light.save(update_fields=["data"])
        response = self.adopt(scene)
        self.assertEqual(response.status_code, 200, response.content)
        project = response.json()["project"]
        self.assertEqual(project["document"]["walls"][0]["id"], str(wall.pk))
        self.assertEqual(project["document"]["lights"][0]["id"], str(light.pk))
        self.update_project(project, scene)
        wall.refresh_from_db()
        light.refresh_from_db()
        self.assertAlmostEqual(wall.data["x1"], coordinate)
        self.assertAlmostEqual(light.data["x"], coordinate)

    def test_partial_workspace_cell_does_not_adopt_content_outside_physical_scene(self):
        scene, *_ = self.existing_scene()
        outside_wall = SceneObject.objects.create(scene=scene, kind="walls", data=objects.wall({
            "x1": 190, "y1": 30, "x2": 199, "y2": 30,
        }))
        outside_light = SceneObject.objects.create(scene=scene, kind="lights", data=objects.light({"x": 198, "y": 80}))
        before = {row.pk: deepcopy(row.data) for row in (outside_wall, outside_light)}
        response = self.adopt(scene)
        self.assertEqual(response.status_code, 200, response.content)
        project = response.json()["project"]
        owned = {item["id"] for kind in ("walls", "doors", "lights") for item in project["document"][kind]}
        self.assertFalse(owned & {str(key) for key in before})
        self.assertIn(builder_import.UNSUPPORTED_OBJECTS, response.json()["warnings"])
        self.update_project(project, scene)
        for row in (outside_wall, outside_light):
            row.refresh_from_db()
            self.assertEqual(row.data, before[row.pk])
            self.assertEqual(row.version, 1)

    def test_unknown_native_fields_remain_external_without_blocking_supported_objects(self):
        scene, wall, door, _ = self.existing_scene()
        wall.data["privateExtension"] = {"value": "Keep this data"}
        wall.save(update_fields=["data"])
        door.data["unknownFlag"] = True
        door.save(update_fields=["data"])
        response = self.adopt(scene)
        self.assertEqual(response.status_code, 200, response.content)
        project = response.json()["project"]
        self.assertEqual(project["document"]["walls"], [])
        self.assertEqual(project["document"]["doors"], [])
        self.assertEqual(len(project["document"]["lights"]), 1)
        self.update_project(project, scene)
        wall.refresh_from_db()
        door.refresh_from_db()
        self.assertEqual(wall.data["privateExtension"], {"value": "Keep this data"})
        self.assertTrue(door.data["unknownFlag"])

    def test_large_simple_import_validates_campaign_resources_only_once_per_document(self):
        scene, *_ = self.existing_scene()
        scene.elements.all().delete()
        SceneObject.objects.bulk_create([SceneObject(scene=scene, kind="walls", data=objects.wall({
            "x1": 10, "y1": 20, "x2": 100, "y2": 20,
        })) for _ in range(300)])
        with CaptureQueriesContext(connection) as queries:
            project, notes = builder_import.create_project(scene, self.membership, [])
        self.assertEqual(len(project.document["walls"]), 300)
        self.assertEqual(notes, [])
        track_queries = [item for item in queries if '"audio_track"' in item["sql"]]
        # Campaign audio is collected by the two whole-document validations,
        # never once for each source candidate.
        self.assertLessEqual(len(track_queries), 2)
        self.assertLess(len(queries), 20)

    def test_renamed_storage_cleanup_tracks_only_new_files_when_candidate_exists(self):
        scene, *_ = self.existing_scene()
        stored = []
        storage = builder_import.default_storage
        original_save = storage.save

        def renamed(name, content):
            return original_save(name + "-new.png", content)

        with patch.object(storage, "exists", side_effect=lambda name: not str(name).endswith("-new.png")), \
                patch.object(storage, "save", side_effect=renamed):
            project, _ = builder_import.create_project(scene, self.membership, stored)
        background = project.document["backgroundImage"]["assetId"]
        from gravewright.maps.models import MapAsset
        path = MapAsset.objects.get(pk=background).file.name
        self.assertEqual(stored, [path])

    def test_snapshot_comparison_distinguishes_boolean_values_from_numbers(self):
        self.assertFalse(builder_import._equivalent({"enabled": True}, {"enabled": 1}))
        self.assertTrue(builder_import._equivalent({"position": [1, 2.0]}, {"position": [1.0, math.nextafter(2.0, 3.0)]}))

    def test_enabling_imported_wall_artwork_retains_original_native_identity(self):
        scene, wall, *_ = self.existing_scene()
        response = self.adopt(scene)
        self.assertEqual(response.status_code, 200, response.content)
        project = response.json()["project"]
        document = deepcopy(project["document"])
        document["walls"][0]["artwork"] = True
        project = self.save_project(project, document)
        project = self.update_project(project, scene)
        wall.refresh_from_db()
        self.assertEqual(scene.elements.filter(kind="walls", data__kind="wall").count(), 1)
        self.assertEqual(wall.data["name"], "Existing wall")
        document = deepcopy(project["document"])
        document["walls"][0]["artwork"] = False
        document["walls"][0]["x1"] += .1
        project = self.save_project(project, document)
        self.update_project(project, scene)
        wall.refresh_from_db()
        self.assertAlmostEqual(wall.data["x1"], 15)

    def test_imported_image_scale_survives_update_and_generation_of_new_scene(self):
        from gravewright.maps.models import Scene
        scene, _, _, light = self.existing_scene()
        scene.settings["imageScale"] = 2
        scene.save(update_fields=["settings"])
        response = self.adopt(scene)
        self.assertEqual(response.status_code, 200, response.content)
        project = response.json()["project"]
        self.assertEqual(project["document"]["sceneGeometry"]["imageScale"], 2)
        project = self.update_project(project, scene)
        scene.refresh_from_db()
        self.assertEqual(scene.settings["imageScale"], 2)
        result = self.post(f"{self.base}/projects/{project['id']}/generate", {
            "request_id": str(uuid.uuid4()), "expected_version": project["version"],
        })
        self.assertEqual(result.status_code, 200, result.content)
        copy = Scene.objects.get(pk=result.json()["scene"]["id"])
        self.assertNotEqual(scene.pk, copy.pk)
        self.assertEqual(copy.settings["gridSize"], scene.settings["gridSize"])
        self.assertEqual(copy.settings["imageScale"], 2)
        self.assertEqual((copy.width, copy.height), (scene.width, scene.height))
        self.assertEqual(copy.elements.get(kind="lights").data["dim_radius"], light.data["dim_radius"])

    def test_new_objects_cannot_be_saved_in_padding_beyond_imported_canvas(self):
        scene, *_ = self.existing_scene()
        result = self.adopt(scene)
        self.assertEqual(result.status_code, 200, result.content)
        project = result.json()["project"]
        source = project["document"]
        self.assertGreater(source["columns"] * source["cellSize"], scene.width)
        for kind in ("walls", "doors", "lights", "particles", "shaders", "floors", "decorations", "regions"):
            with self.subTest(kind=kind):
                document = deepcopy(source)
                if kind in ("walls", "doors"):
                    document[kind][0]["x2"] = document["columns"]
                elif kind == "lights":
                    document[kind][0]["x"] = document["columns"]
                else:
                    item = {"id": str(uuid.uuid4()), "layerId": document["layers"][0]["id"],
                            "x": document["columns"], "y": 1}
                    if kind in ("floors", "decorations", "regions"):
                        item.update(width=.1, height=.1)
                    if kind in ("floors", "decorations"):
                        item["assetId"] = None
                    if kind == "regions":
                        item["name"] = "Outside"
                    document[kind] = [item]
                response = self.post(f"{self.base}/projects/{project['id']}", {
                    "request_id": str(uuid.uuid4()), "expected_version": project["version"],
                    "folder_id": project["folderId"], "document": document,
                })
                self.assertEqual(response.status_code, 400, response.content)
