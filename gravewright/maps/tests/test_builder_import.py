"""Existing and Universal VTT scenes gain editable sources without losing live data."""

import base64
from copy import deepcopy
from io import BytesIO
import json
import uuid
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from PIL import Image

from gravewright.actors.models import Actor
from gravewright.maps import extra_objects, objects, services, universal_vtt
from gravewright.maps.models import (
    Broadcast, MapAsset, MapBuilderProject, Scene, SceneNavigation, SceneObject,
    SceneState, Tile,
)
from gravewright.tokens.models import Token
from . import test_builder_projects as fixtures


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
    DYNAMIC_LIGHTING_ENABLED=True,
)
class BuilderImportTests(TestCase):
    setUp = fixtures.BuilderProjectTests.setUp
    asset = fixtures.BuilderProjectTests.asset
    post = fixtures.BuilderProjectTests.post
    files = fixtures.BuilderProjectTests.files

    def existing_scene(self, *, width=197, height=145, grid=50.5):
        scene = Scene.objects.create(
            campaign=self.campaign, folder=self.folder, name="Existing room",
            visibility="players", width=width, height=height,
            settings=services.settings({"gridSize": grid, "gridOffsetX": 7.25,
                                        "gridOffsetY": -3.5, "gridVisible": False}),
        )
        with Image.new("RGBA", (width, height), (17, 34, 51, 255)) as image, BytesIO() as output:
            image.save(output, "PNG")
            tile = Tile(scene=scene, lod=0, x=0, y=0, byte_size=output.tell())
            tile.file.save("existing-map.png", ContentFile(output.getvalue()))
        wall = SceneObject.objects.create(scene=scene, kind="walls", data=objects.wall({
            "x1": 10, "y1": 20, "x2": 100, "y2": 20,
            "presentation": "window", "behavior": {"vision": "pass", "sound": "attenuate"},
            "vertical": {"bottom": -2, "top": 8}, "name": "Existing wall",
        }))
        door = SceneObject.objects.create(scene=scene, kind="walls", data=objects.wall({
            "kind": "door", "x1": 110, "y1": 20, "x2": 160, "y2": 20,
            "door_state": "open", "name": "Existing door",
            "behavior": {"movement": "pass", "vision": "pass", "light": "pass", "sound": "attenuate"},
        }))
        light = SceneObject.objects.create(scene=scene, kind="lights", data=objects.light({
            "x": 90, "y": 80, "bright_radius": 1.5, "dim_radius": 3.25,
            "color": "#abcdef", "intensity": .7, "animation": "torch", "name": "Existing light",
        }))
        return scene, wall, door, light

    def adopt(self, scene, **overrides):
        return self.post(f"{self.base}/scenes/{scene.pk}/adopt", {
            "request_id": str(uuid.uuid4()), "expected_scene_version": scene.version,
            **overrides,
        })

    def save_project(self, project, document):
        response = self.post(f"{self.base}/projects/{project['id']}", {
            "request_id": str(uuid.uuid4()), "expected_version": project["version"],
            "folder_id": project["folderId"], "document": document,
        })
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["project"]

    def update_project(self, project, scene):
        scene.refresh_from_db()
        response = self.post(f"{self.base}/projects/{project['id']}/update", {
            "request_id": str(uuid.uuid4()), "expected_version": project["version"],
            "expected_scene_version": scene.version,
        })
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["scene"]["id"], str(scene.pk))
        return response.json()["project"]

    def synchronize_project(self, project, scene):
        scene.refresh_from_db()
        return self.post(f"{self.base}/projects/{project['id']}/sync", {
            "request_id": str(uuid.uuid4()), "expected_version": project["version"],
            "expected_scene_version": scene.version,
        })

    def change_scene_settings(self, scene, **settings):
        scene.refresh_from_db()
        services.command(self.campaign.pk, self.gm.pk, "update", {
            "mapId": str(scene.pk), "version": scene.version, "settings": settings,
        }, uuid.uuid4())
        scene.refresh_from_db()

    def raster_pixel(self, scene, point):
        tile = scene.tiles.get(lod=0, x=0, y=0)
        with tile.file.open("rb") as stream, Image.open(stream) as image:
            with image.convert("RGBA") as pixels:
                return pixels.getpixel(point)

    def assert_native_values(self, actual, expected):
        for key, value in expected.items():
            with self.subTest(native_field=key):
                if type(value) in (int, float):
                    self.assertAlmostEqual(actual[key], value)
                else:
                    self.assertEqual(actual[key], value)

    def test_adopt_edit_update_preserves_exact_geometry_and_external_live_content(self):
        scene, wall, door, light = self.existing_scene()
        actor = Actor.objects.create(campaign=self.campaign, name="Existing hero")
        token = Token.objects.create(scene=scene, actor=actor, grid_x=2.25, grid_y=1.5)
        env = SceneState.objects.create(
            scene=scene, lighting={"mode": "dynamic", "darkness": .35},
            fog={"mode": "manual"}, drawings={"authored": ["retained"]},
        )
        artwork = SceneObject.objects.create(scene=scene, kind="images", data=extra_objects.image(scene, {
            "asset_id": str(self.floor.pk), "x": 50, "y": 80, "scale": 2, "layer": "map",
        }))
        hidden = SceneObject.objects.create(scene=scene, kind="images", data=extra_objects.image(scene, {
            "asset_id": str(self.wall.pk), "x": 60, "y": 100, "layer": "gm-image-layer",
        }))
        Broadcast.objects.create(campaign=self.campaign, scene=scene)
        previous = Scene.objects.create(campaign=self.campaign, name="GM preview", width=1, height=1)
        SceneNavigation.objects.create(membership=self.membership, scene=previous)
        before_scene = (scene.width, scene.height, deepcopy(scene.settings), scene.visibility,
                        scene.name, scene.block_id, scene.version)
        before_objects = {row.pk: deepcopy(row.data) for row in (wall, door, light, artwork, hidden)}
        response = self.adopt(scene)
        self.assertEqual(response.status_code, 200, response.content)
        project = response.json()["project"]
        self.assertTrue(project["canUpdate"])
        self.assertEqual((project["sceneId"], project["folderId"]), (str(scene.pk), str(self.folder.pk)))
        self.assertEqual(tuple(len(project["document"][kind]) for kind in ("walls", "doors", "lights")), (1, 1, 1))
        scene.refresh_from_db()
        self.assertEqual((scene.width, scene.height, scene.settings, scene.visibility,
                          scene.name, scene.block_id, scene.version), before_scene)
        self.assertEqual(SceneNavigation.objects.get(membership=self.membership).scene_id, previous.pk)
        self.assertEqual(Broadcast.objects.get(campaign=self.campaign).scene_id, scene.pk)
        # Copy only the scene's base tiles. Native artwork must remain independently placed.
        background = MapAsset.objects.get(pk=project["document"]["backgroundImage"]["assetId"])
        with background.file.open("rb") as stream, Image.open(stream) as image:
            self.assertEqual(image.size, (197, 145))
            with image.convert("RGBA") as pixels:
                self.assertEqual(pixels.getpixel((50, 80)), (17, 34, 51, 255))
        doc = deepcopy(project["document"])
        doc["walls"][0]["y1"] += .1
        doc["walls"][0]["y2"] += .1
        moved_y = doc["walls"][0]["y1"] * doc["cellSize"]
        project = self.save_project(project, doc)
        self.update_project(project, scene)
        scene.refresh_from_db()
        self.assertEqual((scene.width, scene.height, scene.settings, scene.visibility,
                          scene.name, scene.block_id), before_scene[:-1])
        self.assertEqual(set(scene.elements.values_list("pk", flat=True)), set(before_objects))
        wall.refresh_from_db()
        self.assertAlmostEqual(wall.data["y1"], moved_y)
        self.assertAlmostEqual(wall.data["y2"], moved_y)
        for field in ("presentation", "vertical_bottom", "vertical_top", "movement_behavior", "vision_behavior", "light_behavior", "sound_behavior"):
            self.assertEqual(wall.data[field], before_objects[wall.pk][field])
        for row in (door, light, artwork, hidden):
            row.refresh_from_db()
            if row.kind in ("walls", "lights"):
                self.assert_native_values(row.data, before_objects[row.pk])
            else:
                self.assertEqual(row.data, before_objects[row.pk])
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y, token.version), (2.25, 1.5, 1))
        env.refresh_from_db()
        self.assertEqual((env.lighting, env.fog, env.drawings, env.version),
                         ({"mode": "dynamic", "darkness": .35}, {"mode": "manual"}, {"authored": ["retained"]}, 1))
        self.assertEqual(Broadcast.objects.get(campaign=self.campaign).scene_id, scene.pk)
        # An imported collision wall must never paint an extra opaque wall into the raster.
        self.assertEqual(self.raster_pixel(scene, (50, round(moved_y))), (17, 34, 51, 255))
        self.assertEqual(self.raster_pixel(scene, (50, 80)), (17, 34, 51, 255))

    def test_adoption_retries_and_reopening_reuse_the_same_project_and_background(self):
        scene, *_ = self.existing_scene()
        request_id = str(uuid.uuid4())
        first = self.adopt(scene, request_id=request_id)
        self.assertEqual(first.status_code, 200, first.content)
        files = self.files()
        self.assertEqual(self.adopt(scene, request_id=request_id).json(), first.json())
        reopened = self.adopt(scene)
        self.assertEqual(reopened.status_code, 200, reopened.content)
        self.assertEqual(reopened.json()["project"]["id"], first.json()["project"]["id"])
        self.assertEqual(MapBuilderProject.objects.filter(scene=scene).count(), 1)
        self.assertEqual(self.files(), files)
        self.assertEqual(self.adopt(scene, request_id=request_id, expected_scene_version=2).status_code, 409)

    def test_permission_scene_ownership_and_expected_version_fail_without_creating_source(self):
        scene, *_ = self.existing_scene()
        files = self.files()
        for user in (self.player, self.streamer, None):
            if user:
                self.client.force_login(user)
            else:
                self.client.logout()
            with self.subTest(user=user):
                self.assertIn(self.adopt(scene).status_code, (403, 404))
        self.client.force_login(self.gm)
        self.assertEqual(self.adopt(scene, expected_scene_version=0).status_code, 409)
        self.assertEqual(self.adopt(scene, expected_scene_version=True).status_code, 409)
        foreign = Scene.objects.create(campaign=self.other, name="Foreign room", width=32, height=32)
        self.assertEqual(self.adopt(foreign).status_code, 404)
        self.assertFalse(MapBuilderProject.objects.exists())
        self.assertEqual(self.files(), files)

    def test_incompatible_objects_stay_external_with_warnings_through_update(self):
        scene, *_ = self.existing_scene()
        incompatible = SceneObject.objects.create(scene=scene, kind="walls", data=objects.wall({
            "x1": -10, "y1": 50, "x2": 20, "y2": 50,
        }))
        beyond_edge = SceneObject.objects.create(scene=scene, kind="walls", data=objects.wall({
            "x1": 190, "y1": 60, "x2": 199, "y2": 60,
        }))
        before = deepcopy(incompatible.data)
        edge_before = deepcopy(beyond_edge.data)
        result = self.adopt(scene)
        self.assertEqual(result.status_code, 200, result.content)
        self.assertTrue(result.json()["warnings"])
        project = result.json()["project"]
        self.assertEqual(len(project["document"]["walls"]), 1)
        self.update_project(project, scene)
        incompatible.refresh_from_db()
        self.assertEqual(incompatible.data, before)
        self.assertEqual(incompatible.version, 1)
        beyond_edge.refresh_from_db()
        self.assertEqual(beyond_edge.data, edge_before)
        self.assertEqual(beyond_edge.version, 1)

    def test_fractional_native_coordinates_remain_editable_after_roundtrip(self):
        scene, wall, _, light = self.existing_scene()
        wall.data.update(x1=53.4, y1=123.45, x2=123.45, y2=123.45)
        wall.save()
        light.data.update(x=53.4, y=123.45)
        light.save()
        result = self.adopt(scene)
        self.assertEqual(result.status_code, 200, result.content)
        project = result.json()["project"]
        self.assertEqual((len(project["document"]["walls"]), len(project["document"]["lights"])), (1, 1))
        wall_before, light_before = deepcopy(wall.data), deepcopy(light.data)
        self.update_project(project, scene)
        for row, before in ((wall, wall_before), (light, light_before)):
            row.refresh_from_db()
            self.assert_native_values(row.data, before)

    def test_native_wall_edit_sync_retains_ownership_and_merges_builder_name(self):
        scene, wall, *_ = self.existing_scene()
        response = self.adopt(scene)
        self.assertEqual(response.status_code, 200, response.content)
        project = response.json()["project"]
        doc = deepcopy(project["document"])
        source_id = doc["walls"][0]["id"]
        doc["walls"][0]["name"] = "Builder renamed wall"
        project = self.save_project(project, doc)
        services.command(self.campaign.pk, self.gm.pk, "objects", {
            "mapId": str(scene.pk), "area": "walls", "action": "update",
            "data": {"wall_id": str(wall.pk), "y1": 35, "y2": 35},
        }, uuid.uuid4())
        synchronized = self.synchronize_project(project, scene)
        self.assertEqual(synchronized.status_code, 200, synchronized.content)
        self.assertTrue(synchronized.json()["synchronized"])
        project = synchronized.json()["project"]
        self.assertEqual(len(project["document"]["walls"]), 1)
        source = project["document"]["walls"][0]
        self.assertEqual((source["id"], source["name"]), (source_id, "Builder renamed wall"))
        self.assertAlmostEqual(source["y1"] * project["document"]["cellSize"], 35)
        self.update_project(project, scene)
        wall.refresh_from_db()
        self.assertEqual((wall.data["name"], wall.data["y1"], wall.data["y2"]), ("Builder renamed wall", 35, 35))

    def test_native_grid_calibration_sync_merges_source_settings_and_preserves_objects(self):
        scene, *_ = self.existing_scene()
        project = self.adopt(scene).json()["project"]
        doc = deepcopy(project["document"])
        original_objects = {kind: deepcopy(doc[kind]) for kind in ("walls", "doors", "lights")}
        # A pending source offset and a different native offset can be merged.
        doc["sceneGeometry"]["gridOffsetX"] = 11.5
        project = self.save_project(project, doc)
        self.change_scene_settings(scene, gridSize=63.25, gridOffsetY=8.75, imageScale=1.25)
        original_settings = deepcopy(scene.settings)
        synchronized = self.synchronize_project(project, scene)
        self.assertEqual(synchronized.status_code, 200, synchronized.content)
        self.assertTrue(synchronized.json()["synchronized"])
        project = synchronized.json()["project"]
        geometry = project["document"]["sceneGeometry"]
        self.assertEqual({key: geometry[key] for key in ("width", "height", "gridSize", "gridOffsetX", "gridOffsetY", "imageScale")},
                         {"width": 197, "height": 145, "gridSize": 63.25, "gridOffsetX": 11.5, "gridOffsetY": 8.75, "imageScale": 1.25})
        self.assertEqual({kind: project["document"][kind] for kind in original_objects}, original_objects)
        scene.refresh_from_db()
        self.assertEqual(scene.settings, original_settings)
        self.update_project(project, scene)
        scene.refresh_from_db()
        self.assertEqual((scene.width, scene.height, scene.settings["gridSize"], scene.settings["gridOffsetX"],
                          scene.settings["gridOffsetY"], scene.settings["imageScale"]), (197, 145, 63.25, 11.5, 8.75, 1.25))

    def test_native_and_source_edits_to_same_grid_field_conflict_without_overwriting(self):
        scene, *_ = self.existing_scene()
        project = self.adopt(scene).json()["project"]
        doc = deepcopy(project["document"])
        doc["sceneGeometry"]["gridSize"] = 55.5
        project = self.save_project(project, doc)
        self.change_scene_settings(scene, gridSize=63.25)
        before = deepcopy(MapBuilderProject.objects.get(pk=project["id"]).document)
        synchronized = self.synchronize_project(project, scene)
        self.assertEqual(synchronized.status_code, 409, synchronized.content)
        self.assertEqual(MapBuilderProject.objects.get(pk=project["id"]).document, before)
        scene.refresh_from_db()
        self.assertEqual(scene.settings["gridSize"], 63.25)

    def test_native_raster_resize_conflicts_without_replacing_source_background(self):
        scene, *_ = self.existing_scene()
        project = self.adopt(scene).json()["project"]
        before = deepcopy(project["document"])
        scene.width += 1
        scene.version += 1
        scene.save(update_fields=["width", "version"])
        synchronized = self.synchronize_project(project, scene)
        self.assertEqual(synchronized.status_code, 409, synchronized.content)
        self.assertEqual(MapBuilderProject.objects.get(pk=project["id"]).document, before)

    def test_campaign_clone_preserves_imported_geometry_artwork_and_updatable_ownership(self):
        from gravewright.administration.archives import export_campaign, import_campaign

        scene, *_ = self.existing_scene()
        project = self.adopt(scene).json()["project"]
        copied = import_campaign(export_campaign(self.campaign), self.gm, "Copied existing map")
        source = MapBuilderProject.objects.get(campaign=copied)
        copied_scene = source.scene
        self.assertNotEqual(copied_scene.pk, scene.pk)
        self.assertEqual(source.document["sceneGeometry"], project["document"]["sceneGeometry"])
        self.assertTrue(all(row["artwork"] is False for kind in ("walls", "doors") for row in source.document[kind]))
        background = MapAsset.objects.get(pk=source.document["backgroundImage"]["assetId"])
        self.assertEqual(background.campaign_id, copied.pk)
        self.assertNotEqual(str(background.pk), project["document"]["backgroundImage"]["assetId"])
        native_ids = set(copied_scene.elements.values_list("pk", flat=True))
        response = self.post(f"/api/containers/{copied.pk}/map-builder/projects/{source.pk}/update", {
            "request_id": str(uuid.uuid4()), "expected_version": source.version,
            "expected_scene_version": copied_scene.version,
        })
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(set(copied_scene.elements.values_list("pk", flat=True)), native_ids)
        copied_scene.refresh_from_db()
        self.assertEqual((copied_scene.width, copied_scene.height, copied_scene.settings),
                         (scene.width, scene.height, scene.settings))

    def test_incomplete_scene_raster_fails_without_publishing_partial_project(self):
        scene, *_ = self.existing_scene(width=600)
        files = self.files()
        result = self.adopt(scene)
        self.assertEqual(result.status_code, 400, result.content)
        self.assertFalse(MapBuilderProject.objects.exists())
        self.assertEqual(self.files(), files)
        scene.refresh_from_db()
        self.assertEqual(scene.version, 1)

    def test_failed_project_write_removes_only_new_import_artwork(self):
        scene, *_ = self.existing_scene()
        files = self.files()
        assets = set(MapAsset.objects.values_list("pk", flat=True))
        with patch.object(MapBuilderProject, "save", side_effect=OSError("Synthetic project write failure")):
            with self.assertRaises(OSError):
                self.adopt(scene)
        self.assertFalse(MapBuilderProject.objects.exists())
        self.assertEqual(set(MapAsset.objects.values_list("pk", flat=True)), assets)
        self.assertEqual(self.files(), files)
        scene.refresh_from_db()
        self.assertEqual((scene.version, scene.elements.count()), (1, 3))

    def universal_document(self):
        with Image.new("RGBA", (128, 96), (17, 34, 51, 255)) as image, BytesIO() as output:
            image.save(output, "PNG")
            encoded = base64.b64encode(output.getvalue()).decode()
        return {"format": .2, "resolution": {"map_origin": {"x": .5, "y": -.25},
                "map_size": {"x": 4, "y": 3}, "pixels_per_grid": 32},
                "line_of_sight": [[{"x": .5, "y": -.25}, {"x": 4.5, "y": -.25}]],
                "portals": [{"bounds": [{"x": 1.5, "y": -.25}, {"x": 2.5, "y": -.25}],
                             "closed": False, "freestanding": False}],
                "lights": [{"position": {"x": 2, "y": 1}, "range": 2.5,
                            "color": "ffffffff", "intensity": .8, "shadows": True}],
                "image": encoded}

    def test_editable_universal_import_has_native_objects_and_reuses_scene_when_updated(self):
        raw = json.dumps(self.universal_document()).encode()
        request_id = str(uuid.uuid4())
        result = universal_vtt.import_map(
            self.campaign.pk, self.gm.pk, raw, name="Editable UVTT room",
            request_id=request_id, folder_id=str(self.folder.pk), builder_editable=True,
        )
        self.assertTrue(result["builderEditable"])
        project = result["project"]
        scene = Scene.objects.get(pk=result["scene"]["id"])
        self.assertEqual(project["sceneId"], str(scene.pk))
        self.assertEqual((scene.visibility, scene.width, scene.height), ("gm", 128, 96))
        self.assertEqual((scene.settings["gridOffsetX"], scene.settings["gridOffsetY"]), (16, 8))
        self.assertEqual(tuple(len(project["document"][kind]) for kind in ("walls", "doors", "lights")), (2, 1, 1))
        before = {row.pk: deepcopy(row.data) for row in scene.elements.all()}
        files = self.files()
        self.assertEqual(universal_vtt.import_map(
            self.campaign.pk, self.gm.pk, raw, name="Editable UVTT room",
            request_id=request_id, folder_id=str(self.folder.pk), builder_editable=True,
        ), result)
        self.assertEqual(self.files(), files)
        with self.assertRaises(services.MapError) as changed:
            universal_vtt.import_map(
                self.campaign.pk, self.gm.pk, raw, name="Editable UVTT room",
                request_id=request_id, folder_id=str(self.folder.pk), builder_editable=False,
            )
        self.assertEqual(changed.exception.code, "conflict")
        self.update_project(project, scene)
        scene.refresh_from_db()
        self.assertEqual(set(scene.elements.values_list("pk", flat=True)), set(before))
        for row in scene.elements.all():
            self.assert_native_values(row.data, before[row.pk])
        self.assertEqual((Scene.objects.count(), MapBuilderProject.objects.count()), (1, 1))
        self.assertEqual(self.raster_pixel(scene, (10, 0)), (17, 34, 51, 255))
        self.assertFalse(Broadcast.objects.exists())

    def test_editable_universal_import_failure_rolls_back_scene_selection_and_artwork(self):
        scene, *_ = self.existing_scene()
        Broadcast.objects.create(campaign=self.campaign, scene=scene)
        SceneNavigation.objects.create(membership=self.membership, scene=scene)
        files = self.files()
        assets = set(MapAsset.objects.values_list("pk", flat=True))
        with patch.object(MapBuilderProject, "save", side_effect=OSError("Synthetic project write failure")):
            with self.assertRaises(OSError):
                universal_vtt.import_map(
                    self.campaign.pk, self.gm.pk, json.dumps(self.universal_document()).encode(),
                    name="Failed editable UVTT", request_id=str(uuid.uuid4()),
                    builder_editable=True, activate=True,
                )
        self.assertEqual(list(Scene.objects.values_list("pk", flat=True)), [scene.pk])
        self.assertFalse(MapBuilderProject.objects.exists())
        self.assertEqual(set(MapAsset.objects.values_list("pk", flat=True)), assets)
        self.assertEqual(self.files(), files)
        self.assertEqual(Broadcast.objects.get(campaign=self.campaign).scene_id, scene.pk)
        self.assertEqual(SceneNavigation.objects.get(membership=self.membership).scene_id, scene.pk)
