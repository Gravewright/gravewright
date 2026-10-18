"""Regeneration owns only its generated geometry and preserves manual VTT data."""

from copy import deepcopy
import uuid
from unittest.mock import patch

from django.test import TestCase, override_settings

from gravewright.actors.models import Actor
from gravewright.maps import builder_services, services
from gravewright.maps.models import Broadcast, MapBuilderProject, Scene, SceneObject, SceneState
from gravewright.tokens.models import Token
from . import test_builder_projects as fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow")
class BuilderUpdateTests(TestCase):
    setUp = fixtures.BuilderProjectTests.setUp
    asset = fixtures.BuilderProjectTests.asset
    post = fixtures.BuilderProjectTests.post
    save = fixtures.BuilderProjectTests.save
    generate = fixtures.BuilderProjectTests.generate
    files = fixtures.BuilderProjectTests.files

    def generated(self):
        self.assertEqual(self.save().status_code, 200)
        result = self.generate()
        self.assertEqual(result.status_code, 200, result.content)
        return Scene.objects.get(pk=result.json()["scene"]["id"])

    def update(self, **overrides):
        return self.post(self.url + "/update", {"request_id": str(uuid.uuid4()),
                                              "expected_version": 2, "expected_scene_version": 1, **overrides})

    def edited(self):
        self.doc["walls"][0]["y1"] = self.doc["walls"][0]["y2"] = 4
        self.assertEqual(self.save(expected_version=1).status_code, 200)

    def test_update_preserves_tokens_manual_objects_settings_environment_and_live_door(self):
        scene = self.generated()
        scene.name, scene.visibility = "Live name", "players"
        scene.settings["gridVisible"] = False
        scene.save()
        Broadcast.objects.create(campaign=self.campaign, scene=scene)
        actor = Actor.objects.create(campaign=self.campaign, name="Hero")
        token = Token.objects.create(scene=scene, actor=actor, grid_x=6, grid_y=6)
        manual = SceneObject.objects.create(scene=scene, kind="lights", data={"x": 11, "y": 22})
        env = SceneState.objects.create(scene=scene, lighting={"mode": "dynamic", "darkness": .6})
        door = scene.elements.get(data__kind="door")
        door.data["door_state"] = "open"
        door.version += 1
        door.save()
        old_ids = set(scene.elements.values_list("pk", flat=True))
        old_manifest = services.manifest(scene)
        self.edited()
        result = self.update()
        self.assertEqual(result.status_code, 200, result.content)
        self.assertEqual(Scene.objects.count(), 1)
        scene.refresh_from_db()
        token.refresh_from_db()
        manual.refresh_from_db()
        env.refresh_from_db()
        door.refresh_from_db()
        self.assertEqual((scene.name, scene.visibility, scene.settings["gridVisible"]), ("Live name", "players", False))
        self.assertEqual((token.grid_x, token.grid_y, token.version), (6, 6, 1))
        self.assertEqual(manual.data, {"x": 11, "y": 22})
        self.assertEqual(env.lighting, {"mode": "dynamic", "darkness": .6})
        self.assertEqual(door.data["door_state"], "open")
        self.assertEqual(Broadcast.objects.get().scene_id, scene.pk)
        self.assertEqual(scene.elements.filter(kind="walls").count(), 2)
        self.assertEqual(scene.version, 2)
        self.assertNotEqual(services.manifest(scene)["tileUrlTemplate"], old_manifest["tileUrlTemplate"])
        # A second update replaces its own rows without duplicates.
        again = self.update(expected_scene_version=2)
        self.assertEqual(again.status_code, 200, again.content)
        self.assertEqual(scene.elements.count(), 3)
        self.assertIn(manual.pk, old_ids)

    def test_stale_project_and_scene_or_native_modification_conflict_without_writes(self):
        scene = self.generated()
        self.edited()
        original = self.files()
        self.assertEqual(self.update(expected_version=1).status_code, 409)
        self.assertEqual(self.update(expected_scene_version=0).status_code, 409)
        wall = scene.elements.filter(data__kind="wall").first()
        wall.data["x1"] += 1
        wall.save()
        result = self.update()
        self.assertEqual(result.status_code, 409, result.content)
        self.assertEqual(self.files(), original)
        scene.refresh_from_db()
        self.assertEqual(scene.version, 1)

    def test_idempotent_retry_does_not_duplicate_objects_or_publish_a_new_scene(self):
        scene = self.generated()
        self.edited()
        request_id = str(uuid.uuid4())
        result = self.update(request_id=request_id)
        self.assertEqual(result.status_code, 200, result.content)
        self.assertEqual(self.update(request_id=request_id).json(), result.json())
        self.assertEqual(self.update(request_id=request_id, expected_scene_version=2).status_code, 409)
        self.assertEqual(Scene.objects.count(), 1)
        self.assertEqual(scene.elements.count(), 2)

    def test_old_or_remapped_history_cannot_delete_unknown_scene_content(self):
        self.generated()
        self.edited()
        for history in ({}, {"formatVersion": 1, "sceneId": str(uuid.uuid4()), "objects": []}):
            MapBuilderProject.objects.filter(pk=self.project_id).update(generation=history)
            self.assertEqual(self.update().status_code, 409)

    def legacy_scene(self):
        scene = self.generated()
        # Delivery one numbered each wall's split spans in global output order.
        for index, x1 in enumerate((64, 256)):
            wall = scene.elements.get(data__kind="wall", data__x1=x1)
            legacy_id = uuid.uuid5(scene.pk, f'{self.doc["walls"][0]["id"]}:{index}')
            data = deepcopy(wall.data)
            wall.delete()
            SceneObject.objects.create(id=legacy_id, scene=scene, kind="walls", data=data)
        MapBuilderProject.objects.filter(pk=self.project_id).update(generation={})
        return scene

    def test_legacy_scene_is_adopted_before_save_without_losing_manual_content(self):
        scene = self.legacy_scene()
        door = scene.elements.get(data__kind="door")
        door.data["door_state"] = "open"
        door.save()
        manual_wall = SceneObject.objects.create(scene=scene, kind="walls", data={"x1": 9, "y1": 10, "x2": 20, "y2": 10})
        manual_light = SceneObject.objects.create(scene=scene, kind="lights", data={"x": 9, "y": 10})
        actor = Actor.objects.create(campaign=self.campaign, name="Legacy hero")
        token = Token.objects.create(scene=scene, actor=actor, grid_x=6, grid_y=6)
        previous_ids = set(scene.elements.values_list("pk", flat=True))
        project = MapBuilderProject.objects.get(pk=self.project_id)
        before_updated = project.updated_at
        for url in (self.url, self.base):
            response = self.client.get(url)
            data = response.json()
            result = data["project"] if "project" in data else data["projects"][0]
            self.assertTrue(result["canUpdate"])
        project.refresh_from_db()
        self.assertEqual(project.generation, {})
        self.assertEqual(project.updated_at, before_updated)
        self.assertEqual(project.version, 1)
        # A browser upgrades the edited document before saving it.
        doc = deepcopy(self.doc)
        doc["schemaVersion"] = 3
        layer_id = str(uuid.uuid4())
        doc["layers"] = [{"id": layer_id, "name": "Base", "visible": True, "locked": False}]
        doc["decorations"], doc["lights"] = [], []
        for kind in ("floors", "walls", "doors"):
            for row in doc[kind]:
                row["layerId"] = layer_id
        doc["floors"][0]["rotation"] = 0
        doc["walls"][0]["y1"] = doc["walls"][0]["y2"] = 4
        saved = self.save(document=doc, expected_version=1)
        self.assertEqual(saved.status_code, 200, saved.content)
        self.assertTrue(saved.json()["project"]["canUpdate"])
        project.refresh_from_db()
        self.assertEqual({uuid.UUID(row["id"]) for row in project.generation["objects"]}, previous_ids - {manual_wall.pk, manual_light.pk})
        response = self.update()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["scene"]["id"], str(scene.pk))
        self.assertEqual(Scene.objects.count(), 1)
        door.refresh_from_db()
        self.assertEqual(door.data["door_state"], "open")
        manual_wall.refresh_from_db()
        manual_light.refresh_from_db()
        token.refresh_from_db()
        self.assertEqual(manual_wall.data, {"x1": 9, "y1": 10, "x2": 20, "y2": 10})
        self.assertEqual(manual_light.data, {"x": 9, "y": 10})
        self.assertEqual((token.grid_x, token.grid_y), (6, 6))
        self.assertEqual(scene.elements.filter(kind="walls").count(), 3)
        self.assertEqual(self.update(expected_scene_version=2).status_code, 200)
        self.assertEqual(scene.elements.filter(kind="walls").count(), 3)

    def test_unchanged_legacy_scene_can_be_updated_directly(self):
        scene = self.legacy_scene()
        result = self.update(expected_version=1)
        self.assertEqual(result.status_code, 200, result.content)
        self.assertEqual(result.json()["scene"]["id"], str(scene.pk))
        self.assertEqual(Scene.objects.count(), 1)
        self.assertEqual(scene.elements.count(), 3)
        project = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual(len(project.generation["objects"]), 3)

    def test_changed_or_missing_legacy_geometry_is_never_adopted(self):
        scene = self.legacy_scene()
        wall = scene.elements.get(data__kind="wall", data__x1=64)
        wall.data["x1"] += 1
        wall.save()
        files = self.files()
        self.assertFalse(self.client.get(self.url).json()["project"]["canUpdate"])
        self.assertEqual(self.update(expected_version=1).status_code, 409)
        self.assertEqual(self.files(), files)
        project = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual(project.generation, {})
        wall.delete()
        self.assertFalse(self.client.get(self.url).json()["project"]["canUpdate"])
        self.assertEqual(self.update(expected_version=1).status_code, 409)

    def test_legacy_dimensions_must_match_and_malformed_history_cannot_be_replaced(self):
        scene = self.legacy_scene()
        scene.settings["gridSize"] = 32
        scene.save()
        self.assertFalse(self.client.get(self.url).json()["project"]["canUpdate"])
        self.assertEqual(self.update(expected_version=1).status_code, 409)
        scene.settings["gridSize"] = 64
        scene.save()
        history = {"unrecognized": "keep this record"}
        MapBuilderProject.objects.filter(pk=self.project_id).update(generation=history)
        self.assertFalse(self.client.get(self.url).json()["project"]["canUpdate"])
        self.assertEqual(self.update(expected_version=1).status_code, 409)
        self.edited()
        self.assertEqual(MapBuilderProject.objects.get(pk=self.project_id).generation, history)

    def test_cloned_campaign_updates_remapped_objects_without_resetting_its_open_door(self):
        from gravewright.administration.archives import export_campaign, import_campaign

        original = self.generated()
        door = original.elements.get(data__kind="door")
        door.data["door_state"] = "open"
        door.save()
        clone = import_campaign(export_campaign(self.campaign), self.gm, "Cloned workshop")
        project = MapBuilderProject.objects.get(campaign=clone)
        scene = project.scene
        door = scene.elements.get(data__kind="door")
        door_id = door.pk
        manual = SceneObject.objects.create(scene=scene, kind="lights", data={"x": 9, "y": 10})
        actor = Actor.objects.create(campaign=clone, name="Clone hero")
        token = Token.objects.create(scene=scene, actor=actor, grid_x=6, grid_y=6)
        doc = deepcopy(project.document)
        doc["walls"][0]["y1"] = doc["walls"][0]["y2"] = 4
        base = f"/api/containers/{clone.pk}/map-builder/projects/{project.pk}"
        saved = self.post(base, {"request_id": str(uuid.uuid4()), "expected_version": 1,
                                 "folder_id": str(project.folder_id), "document": doc})
        self.assertEqual(saved.status_code, 200, saved.content)
        for version in (1, 2):
            response = self.post(base + "/update", {"request_id": str(uuid.uuid4()),
                "expected_version": 2, "expected_scene_version": version})
            self.assertEqual(response.status_code, 200, response.content)
            door.refresh_from_db()
            self.assertEqual(door.pk, door_id)
            self.assertEqual(door.data["door_state"], "open")
            self.assertEqual(scene.elements.filter(kind="walls").count(), 2)
            self.assertTrue(SceneObject.objects.filter(pk=manual.pk).exists())
            token.refresh_from_db()
            self.assertEqual((token.grid_x, token.grid_y), (6, 6))
        self.assertEqual(Scene.objects.filter(campaign=clone).count(), 1)

    def test_deleting_used_door_and_decoration_assets_keeps_scene_updatable(self):
        from .test_builder_expansion import BuilderExpansionTests

        self.doc = BuilderExpansionTests.expanded(self)
        self.doc["lights"] = []
        scene = self.generated()
        door = scene.elements.get(data__kind="door")
        door.data["door_state"] = "open"
        door.save()
        actor = Actor.objects.create(campaign=self.campaign, name="Hero")
        token = Token.objects.create(scene=scene, actor=actor, grid_x=6, grid_y=6)
        manual = SceneObject.objects.create(scene=scene, kind="lights", data={"x": 12, "y": 34})
        for asset_id in (self.doc["doors"][0]["assetId"], self.doc["decorations"][0]["assetId"]):
            deleted = self.post(f"/api/containers/{self.campaign.pk}/library/assets/delete", {"asset_id": asset_id})
            self.assertEqual(deleted.status_code, 200, deleted.content)
        saved = self.client.get(self.url).json()["project"]
        self.assertIsNone(saved["document"]["doors"][0]["assetId"])
        self.assertIsNone(saved["document"]["decorations"][0]["assetId"])
        self.assertEqual(saved["version"], 3)
        response = self.update(expected_version=3)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Scene.objects.count(), 1)
        door.refresh_from_db()
        self.assertEqual(door.data["door_state"], "open")
        self.assertNotIn("asset_id", door.data)
        self.assertNotIn("thickness", door.data)
        self.assertEqual(scene.elements.filter(kind="images").count(), 0)
        token.refresh_from_db()
        manual.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y), (6, 6))
        self.assertEqual(manual.data, {"x": 12, "y": 34})

    def test_asset_cleanup_does_not_accept_unrelated_manual_door_changes(self):
        scene = self.generated()
        door = scene.elements.get(data__kind="door")
        door.data["x1"] += 1
        door.save()
        deleted = self.post(f"/api/containers/{self.campaign.pk}/library/assets/delete", {"asset_id": str(self.door.pk)})
        self.assertEqual(deleted.status_code, 200, deleted.content)
        self.assertEqual(self.update(expected_version=2).status_code, 409)

    def test_asset_cleanup_also_tracks_art_already_removed_from_edited_source(self):
        scene = self.generated()
        self.doc["doors"][0]["assetId"] = None
        self.doc["assets"] = [entry for entry in self.doc["assets"] if entry["assetId"] != str(self.door.pk)]
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        deleted = self.post(f"/api/containers/{self.campaign.pk}/library/assets/delete", {"asset_id": str(self.door.pk)})
        self.assertEqual(deleted.status_code, 200, deleted.content)
        project = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual(project.version, 3)
        response = self.update(expected_version=3)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["scene"]["id"], str(scene.pk))
        self.assertNotIn("asset_id", scene.elements.get(data__kind="door").data)

    def test_asset_cleanup_does_not_repair_malformed_ownership_history(self):
        self.generated()
        project = MapBuilderProject.objects.get(pk=self.project_id)
        history = deepcopy(project.generation)
        entry = next(row for row in history["objects"] if row["data"].get("kind") == "door")
        entry.pop("sourceId")
        MapBuilderProject.objects.filter(pk=project.pk).update(generation=history)
        deleted = self.post(f"/api/containers/{self.campaign.pk}/library/assets/delete", {"asset_id": str(self.door.pk)})
        self.assertEqual(deleted.status_code, 200, deleted.content)
        project.refresh_from_db()
        self.assertEqual(project.generation, history)
        self.assertEqual(self.update(expected_version=2).status_code, 409)

    def test_resize_with_manual_tokens_is_rejected_without_clamping_them(self):
        scene = self.generated()
        actor = Actor.objects.create(campaign=self.campaign, name="Hero")
        token = Token.objects.create(scene=scene, actor=actor, grid_x=7, grid_y=7)
        self.doc["columns"] = 7
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        self.assertEqual(self.update().status_code, 409)
        token.refresh_from_db()
        self.assertEqual(token.grid_x, 7)

    def test_concurrent_native_edit_during_raster_is_rechecked_and_new_files_removed(self):
        scene = self.generated()
        self.edited()
        before = self.files()
        prepare = builder_services.prepare

        def race(*args):
            result = prepare(*args)
            door = scene.elements.get(data__kind="door")
            door.data["x1"] += 1
            door.save()
            return result

        with patch.object(builder_services, "prepare", side_effect=race):
            self.assertEqual(self.update().status_code, 409)
        self.assertEqual(self.files(), before)

    def test_update_requires_gm_membership(self):
        self.generated()
        self.edited()
        for user in (self.player, self.streamer):
            self.client.force_login(user)
            self.assertIn(self.update().status_code, (403, 404))
