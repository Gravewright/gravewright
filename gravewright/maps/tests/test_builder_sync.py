"""Reconcile generated native edits without replacing live or external content."""

from copy import deepcopy
import uuid

from django.test import TestCase, override_settings

from gravewright.maps import services
from gravewright.maps.blueprints import default_blueprint
from gravewright.maps.models import MapBuilderProject, Scene, SceneObject

from . import test_builder_expansion as expansion
from . import test_builder_projects as fixtures
from .test_levers import execution, node


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class BuilderSyncTests(TestCase):
    asset = fixtures.BuilderProjectTests.asset
    post = fixtures.BuilderProjectTests.post
    save = fixtures.BuilderProjectTests.save
    generate = fixtures.BuilderProjectTests.generate
    files = fixtures.BuilderProjectTests.files

    def setUp(self):
        fixtures.BuilderProjectTests.setUp(self)
        self.doc = expansion.BuilderExpansionTests.expanded(self)
        self.doc["layers"][0].update(visible=True, locked=False)

    def generated(self):
        saved = self.save()
        self.assertEqual(saved.status_code, 200, saved.content)
        generated = self.generate()
        self.assertEqual(generated.status_code, 200, generated.content)
        return Scene.objects.get(pk=generated.json()["scene"]["id"])

    def sync(self, **overrides):
        project = MapBuilderProject.objects.get(pk=self.project_id)
        return self.post(self.url + "/sync", {
            "request_id": str(uuid.uuid4()), "expected_version": project.version,
            "expected_scene_version": project.scene.version if project.scene_id else None,
            **overrides,
        })

    def command(self, scene, area, action, data):
        return services.command(self.campaign.pk, self.gm.pk, "objects", {
            "mapId": str(scene.pk), "area": area, "action": action, "data": data,
        }, uuid.uuid4())

    def update_scene(self, project, scene):
        scene.refresh_from_db()
        response = self.post(self.url + "/update", {
            "request_id": str(uuid.uuid4()), "expected_version": project["version"],
            "expected_scene_version": scene.version,
        })
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["scene"]["id"], str(scene.pk))
        return response.json()["project"]

    def test_noop_and_live_door_light_state_do_not_change_authored_defaults(self):
        scene = self.generated()
        before = MapBuilderProject.objects.get(pk=self.project_id)
        door = scene.elements.get(data__kind="door")
        self.command(scene, "walls", "door", {"wall_id": str(door.pk), "door_state": "open"})
        light = scene.elements.get(kind="lights")
        self.command(scene, "lights", "update", {"light_id": str(light.pk), "enabled": False})
        files = self.files()
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        result = response.json()
        self.assertFalse(result["synchronized"])
        self.assertEqual(result["project"]["version"], before.version)
        self.assertEqual(result["project"]["document"], before.document)
        self.assertEqual(self.files(), files)
        door.refresh_from_db()
        light.refresh_from_db()
        self.assertEqual(door.data["door_state"], "open")
        self.assertFalse(light.data["enabled"])

    def test_door_geometry_anchor_name_and_native_blueprint_references_roundtrip(self):
        self.doc["regions"] = [{"id": str(uuid.uuid4()), "layerId": self.doc["layers"][0]["id"],
            "x": 5, "y": 5, "width": 2, "height": 2, "name": "Destination", "enabled": True}]
        scene = self.generated()
        door = scene.elements.get(data__kind="door")
        image = scene.elements.get(kind="images")
        light = scene.elements.get(kind="lights")
        destination = scene.elements.get(kind="zones")
        blueprint = default_blueprint("door")
        blueprint["graphs"]["interact"] = {"nodes": [
            node("event", "event", event="interact"),
            node("image", "reference", targetId=str(image.pk)),
            node("lamp", "lightReference", targetId=str(light.pk)),
            node("group", "elementGroup", name="Targets", memberType="element", targetIds=[str(image.pk)]),
            node("travel", "teleport", destinationId=str(destination.pk)),
        ], "edges": []}
        self.command(scene, "walls", "update", {
            "wall_id": str(door.pk), "version": door.version,
            "x1": 3.25 * 64, "x2": 4.25 * 64, "y1": 3.5 * 64, "y2": 3.5 * 64,
            "thickness": .75 * 64, "rotationAnchor": "end", "name": "Native renamed door",
            "blueprint": blueprint,
        })
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["synchronized"])
        project = response.json()["project"]
        authored = project["document"]["doors"][0]
        self.assertEqual([authored[key] for key in ("x1", "x2", "y1", "y2", "thickness")],
                         [3.25, 4.25, 3.5, 3.5, .75])
        self.assertEqual(authored["rotationAnchor"], "end")
        self.assertEqual(authored["name"], "Native renamed door")
        nodes = {row["id"]: row for row in authored["blueprint"]["graphs"]["interact"]["nodes"]}
        image_source = self.doc["decorations"][0]["id"]
        self.assertEqual(nodes["image"]["targetId"], image_source)
        self.assertEqual(nodes["lamp"]["targetId"], self.doc["lights"][0]["id"])
        self.assertEqual(nodes["group"]["targetIds"], [image_source])
        self.assertEqual(nodes["travel"]["destinationId"], self.doc["regions"][0]["id"])
        self.update_scene(project, scene)
        door.refresh_from_db()
        self.assertEqual(door.data["rotationAnchor"], "end")
        self.assertEqual(door.data["x1"], 3.25 * 64)
        rebound = {row["id"]: row for row in door.data["blueprint"]["graphs"]["interact"]["nodes"]}
        self.assertEqual(rebound["image"]["targetId"], str(image.pk))
        self.assertEqual(rebound["lamp"]["targetId"], str(light.pk))

    def test_image_resize_move_and_light_parameters_sync_without_changing_native_ids(self):
        scene = self.generated()
        image = scene.elements.get(kind="images")
        light = scene.elements.get(kind="lights")
        self.command(scene, "images", "update", {
            "placement_id": str(image.pk), "x": 4 * 64, "y": 3 * 64,
            "scale": image.data["scale"] * 1.5, "rotation": 90, "name": "Moved image",
        })
        self.command(scene, "lights", "update", {
            "light_id": str(light.pk), "x": 5.5 * 64, "y": 6 * 64,
            "bright_radius": 3, "dim_radius": 7, "color": "#123456", "intensity": .4,
        })
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        project = response.json()["project"]
        authored_image = project["document"]["decorations"][0]
        self.assertEqual(authored_image["rotation"], 90)
        self.assertEqual(authored_image["name"], "Moved image")
        self.assertEqual(authored_image["x"] + authored_image["width"] / 2, 4)
        self.assertEqual(authored_image["y"] + authored_image["height"] / 2, 3)
        authored_light = project["document"]["lights"][0]
        self.assertEqual((authored_light["x"], authored_light["y"], authored_light["brightRadius"],
                          authored_light["dimRadius"], authored_light["color"], authored_light["intensity"]),
                         (5.5, 6, 3, 7, "#123456", .4))
        self.update_scene(project, scene)
        image.refresh_from_db()
        light.refresh_from_db()
        self.assertEqual(image.data["x"], 4 * 64)
        self.assertEqual(light.data["dim_radius"], 7)

    def test_native_drag_after_runtime_move_imports_the_final_absolute_image_position(self):
        from gravewright.maps.blueprint_actions import transform

        scene = self.generated()
        image = scene.elements.get(kind="images")
        original = MapBuilderProject.objects.get(pk=self.project_id).document["decorations"][0]
        self.assertTrue(transform(scene, self.membership, image, {"type": "move", "dx": 1, "dy": 0}))
        # Runtime actions advance the native ownership snapshot while the
        # original editable source intentionally retains its authored position.
        stored = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual(stored.document["decorations"][0], original)
        self.command(scene, "images", "update", {"placement_id": str(image.pk), "x": 5 * 64})
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        authored = response.json()["project"]["document"]["decorations"][0]
        self.assertEqual(authored["x"] + authored["width"] / 2, 5)
        self.update_scene(response.json()["project"], scene)
        image.refresh_from_db()
        self.assertEqual(image.data["x"], 5 * 64)

    def test_native_image_layer_and_order_are_kept_after_scene_update(self):
        scene = self.generated()
        image = scene.elements.get(kind="images")
        self.command(scene, "images", "update", {"placement_id": str(image.pk),
            "layer": "gm-image-layer", "z_index": 17})
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        self.update_scene(response.json()["project"], scene)
        image.refresh_from_db()
        self.assertEqual((image.data["layer"], image.data["z_index"]), ("gm-image-layer", 17))

    def test_unsafe_native_presentation_history_cannot_be_applied_during_update(self):
        scene = self.generated()
        project = MapBuilderProject.objects.get(pk=self.project_id)
        history = deepcopy(project.generation)
        original = list(scene.elements.order_by("pk").values("pk", "data", "version"))
        files = self.files()
        for overrides in ({"blueprint": default_blueprint("lever")}, {"layer": "unsafe-layer"}):
            modified = deepcopy(history)
            next(row for row in modified["objects"] if row["kind"] == "images")["nativeOverrides"] = overrides
            MapBuilderProject.objects.filter(pk=self.project_id).update(generation=modified)
            with self.subTest(overrides=overrides):
                response = self.post(self.url + "/update", {
                    "request_id": str(uuid.uuid4()), "expected_version": 1, "expected_scene_version": 1,
                })
                self.assertIn(response.status_code, (400, 409), response.content)
                self.assertEqual(list(scene.elements.order_by("pk").values("pk", "data", "version")), original)
                self.assertEqual(self.files(), files)

    def test_deleted_generated_decoration_is_removed_without_adopting_manual_objects(self):
        scene = self.generated()
        image = scene.elements.get(kind="images")
        self.command(scene, "images", "delete", {"placement_id": str(image.pk), "version": image.version})
        manual = self.command(scene, "walls", "create", {
            "x1": 32, "y1": 32, "x2": 96, "y2": 32,
        })["wall"]
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        project = response.json()["project"]
        self.assertEqual(project["document"]["decorations"], [])
        self.assertEqual(len(project["document"]["walls"]), len(self.doc["walls"]))
        self.update_scene(project, scene)
        self.assertFalse(SceneObject.objects.filter(pk=image.pk).exists())
        self.assertEqual(scene.elements.get(pk=manual["id"]).data["x1"], 32)

    def test_changed_split_wall_segment_does_not_move_its_other_generated_segment(self):
        scene = self.generated()
        wall = scene.elements.get(kind="walls", data__kind="wall", data__x1=64)
        other = scene.elements.get(kind="walls", data__kind="wall", data__x1=256)
        untouched = deepcopy(other.data)
        self.command(scene, "walls", "update", {
            "wall_id": str(wall.pk), "y1": 4 * 64, "y2": 4 * 64,
        })
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        self.update_scene(response.json()["project"], scene)
        self.assertTrue(scene.elements.filter(kind="walls", data__kind="wall", data__x1=64,
                                              data__x2=192, data__y1=256, data__y2=256).exists())
        self.assertTrue(scene.elements.filter(kind="walls", data__kind="wall", data=untouched).exists())

    def test_split_wall_native_move_merges_a_pending_builder_name(self):
        scene = self.generated()
        document = deepcopy(self.doc)
        document["walls"][0]["name"] = "Builder wall name"
        self.assertEqual(self.save(document=document, expected_version=1).status_code, 200)
        wall = scene.elements.get(kind="walls", data__kind="wall", data__x1=64)
        self.command(scene, "walls", "update", {"wall_id": str(wall.pk), "y1": 256, "y2": 256})
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        walls = response.json()["project"]["document"]["walls"]
        self.assertEqual(len(walls), 2)
        self.assertTrue(all(row["name"] == "Builder wall name" for row in walls))
        self.update_scene(response.json()["project"], scene)
        self.assertTrue(scene.elements.filter(kind="walls", data__kind="wall", data__x1=64, data__y1=256).exists())

    def test_native_door_deletion_keeps_the_original_wall_opening(self):
        scene = self.generated()
        spans = list(scene.elements.filter(data__kind="wall").order_by("pk").values("pk", "data"))
        door = scene.elements.get(data__kind="door")
        self.command(scene, "walls", "delete", {"wall_id": str(door.pk), "version": door.version})
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["project"]["document"]["doors"], [])
        self.update_scene(response.json()["project"], scene)
        self.assertEqual(list(scene.elements.filter(data__kind="wall").order_by("pk").values("pk", "data")), spans)

    def test_native_door_move_keeps_the_previous_wall_spans_in_place(self):
        scene = self.generated()
        spans = list(scene.elements.filter(data__kind="wall").order_by("pk").values("pk", "data"))
        door = scene.elements.get(data__kind="door")
        self.command(scene, "walls", "update", {"wall_id": str(door.pk), "y1": 256, "y2": 256})
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        self.update_scene(response.json()["project"], scene)
        self.assertEqual(list(scene.elements.filter(data__kind="wall").order_by("pk").values("pk", "data")), spans)
        door.refresh_from_db()
        self.assertEqual((door.data["y1"], door.data["y2"]), (256, 256))

    def test_lever_projection_uses_authored_box_and_base_art_while_state_is_on(self):
        source = self.doc["decorations"][0]
        source.update(x=3, y=4, width=1, height=2, rotation=0, lever={"state": "off"})
        alternative = self.asset("alternate-lever.png", "#3355aa")
        self.doc["assets"].append({"assetId": str(alternative.pk), "role": "decoration"})
        source["blueprint"] = default_blueprint("lever")
        source["blueprint"]["states"]["on"] = {"appearance": "asset", "assetId": str(alternative.pk)}
        source["blueprint"]["graphs"]["interact"] = {"nodes": [
            node("event", "event", event="interact"), node("on", "state", targetState="on")],
            "edges": [execution("event", "on")]}
        scene = self.generated()
        image = scene.elements.get(kind="images")
        self.command(scene, "images", "interact", {"image_id": str(image.pk)})
        image.refresh_from_db()
        self.assertEqual(image.data["lever"]["state"], "on")
        self.command(scene, "images", "update", {"placement_id": str(image.pk), "x": 4 * 64})
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        authored = response.json()["project"]["document"]["decorations"][0]
        self.assertEqual((authored["assetId"], authored["width"], authored["height"], authored["lever"]),
                         (source["assetId"], 1, 2, {"state": "off"}))
        self.assertEqual(authored["x"], 3.5)
        self.update_scene(response.json()["project"], scene)
        image.refresh_from_db()
        self.assertEqual(image.data["lever"]["state"], "on")
        self.assertEqual(image.data["asset_id"], str(alternative.pk))

    def test_particle_settings_and_region_geometry_name_and_filters_are_imported(self):
        layer = self.doc["layers"][0]["id"]
        self.doc["particles"] = [{"id": str(uuid.uuid4()), "layerId": layer, "x": 5, "y": 5,
            "kind": "smoke", "scale": 1, "density": .5, "color": "#556677", "enabled": True,
            "rotation": 0, "light_response": 0, "light_emission": 0}]
        self.doc["regions"] = [{"id": str(uuid.uuid4()), "layerId": layer, "x": 1, "y": 1,
            "width": 2, "height": 2, "name": "Authored region", "enabled": True}]
        scene = self.generated()
        particle = scene.elements.get(kind="particles")
        region = scene.elements.get(kind="zones")
        self.command(scene, "particles", "update", {
            "emitter_id": str(particle.pk), "x": 6 * 64, "density": .9, "kind": "rain",
        })
        self.command(scene, "zones", "update", {"id": str(region.pk), "expected_version": region.version,
            "patch": {"geometry": {"shape": "rect", "x": 2 * 64, "y": 3 * 64, "width": 3 * 64, "height": 2 * 64},
                      "region": {"name": "Native region", "filters": {"visibility": "visible"}}}})
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        document = response.json()["project"]["document"]
        self.assertEqual((document["particles"][0]["x"], document["particles"][0]["density"],
                          document["particles"][0]["kind"]), (6, .9, "rain"))
        region_source = document["regions"][0]
        self.assertEqual([region_source[key] for key in ("x", "y", "width", "height", "name")],
                         [2, 3, 3, 2, "Native region"])
        self.assertEqual(region_source["filters"]["visibility"], "visible")
        self.update_scene(response.json()["project"], scene)

    def torch_source(self):
        source = self.doc["decorations"][0]
        source.update(x=3, y=4, width=1, height=2, rotation=0,
                      torch={"state": "off", "lit": True, "lightId": self.doc["lights"][0]["id"]})
        self.doc["lights"][0].update(x=4, y=5)
        source["blueprint"] = default_blueprint("torch")
        source["blueprint"]["graphs"]["interact"] = {"nodes": [
            node("event", "event", event="interact"), node("on", "state", targetState="on")],
            "edges": [execution("event", "on")]}
        return source

    def test_turning_a_torch_does_not_import_runtime_child_positions(self):
        self.torch_source()
        scene = self.generated()
        before = deepcopy(MapBuilderProject.objects.get(pk=self.project_id).document)
        image = scene.elements.get(kind="images")
        self.command(scene, "images", "interact", {"image_id": str(image.pk)})
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(response.json()["synchronized"])
        self.assertEqual(response.json()["project"]["document"], before)

    def test_native_move_resize_and_rotation_of_turned_torch_do_not_double_rotate_child(self):
        self.torch_source()
        scene = self.generated()
        image = scene.elements.get(kind="images")
        self.command(scene, "images", "interact", {"image_id": str(image.pk)})
        image.refresh_from_db()
        self.command(scene, "images", "update", {"placement_id": str(image.pk),
            "x": 5 * 64, "y": 5 * 64, "rotation": 180, "scale": image.data["scale"] * 2})
        child = scene.elements.get(kind="lights")
        original_child = deepcopy(child.data)
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        document = response.json()["project"]["document"]
        authored = document["decorations"][0]
        self.assertEqual(authored["rotation"], 90)
        self.assertEqual(authored["torch"]["state"], "off")
        self.assertEqual((authored["width"], authored["height"]), (2, 4))
        self.update_scene(response.json()["project"], scene)
        image.refresh_from_db()
        child.refresh_from_db()
        self.assertEqual(image.data["rotation"], 180)
        self.assertEqual(image.data["torch"]["state"], "on")
        for field in ("x", "y", "rotation"):
            self.assertAlmostEqual(child.data[field], original_child[field], msg=field)

    def test_disjoint_project_edits_and_native_changes_merge_by_field(self):
        scene = self.generated()
        document = deepcopy(self.doc)
        document["doors"][0]["name"] = "Pending builder name"
        document["floors"][0]["rotation"] = 180
        saved = self.save(document=document, expected_version=1)
        self.assertEqual(saved.status_code, 200, saved.content)
        door = scene.elements.get(data__kind="door")
        self.command(scene, "walls", "update", {
            "wall_id": str(door.pk), "rotationAnchor": "start", "x1": 3.5 * 64, "x2": 4.5 * 64,
        })
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        document = response.json()["project"]["document"]
        self.assertEqual(document["doors"][0]["name"], "Pending builder name")
        self.assertEqual(document["doors"][0]["rotationAnchor"], "start")
        self.assertEqual(document["doors"][0]["x1"], 3.5)
        self.assertEqual(document["floors"][0]["rotation"], 180)

    def test_same_field_project_and_native_edits_conflict_without_partial_writes(self):
        scene = self.generated()
        document = deepcopy(self.doc)
        document["doors"][0]["rotationAnchor"] = "start"
        self.assertEqual(self.save(document=document, expected_version=1).status_code, 200)
        door = scene.elements.get(data__kind="door")
        self.command(scene, "walls", "update", {"wall_id": str(door.pk), "rotationAnchor": "end"})
        before = MapBuilderProject.objects.get(pk=self.project_id)
        files = self.files()
        response = self.sync()
        self.assertEqual(response.status_code, 409, response.content)
        after = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual((after.document, after.generation, after.version),
                         (before.document, before.generation, before.version))
        self.assertEqual(self.files(), files)
        door.refresh_from_db()
        self.assertEqual(door.data["rotationAnchor"], "end")

    def test_legacy_manifest_without_source_snapshot_still_imports_direct_native_edits(self):
        scene = self.generated()
        project = MapBuilderProject.objects.get(pk=self.project_id)
        project.generation.pop("sourceDocument", None)
        project.save(update_fields=["generation"])
        door = scene.elements.get(data__kind="door")
        self.command(scene, "walls", "update", {"wall_id": str(door.pk), "rotationAnchor": "end"})
        response = self.sync()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["project"]["document"]["doors"][0]["rotationAnchor"], "end")
        self.update_scene(response.json()["project"], scene)

    def test_sync_retry_is_idempotent_and_cannot_reuse_request_identity(self):
        scene = self.generated()
        door = scene.elements.get(data__kind="door")
        self.command(scene, "walls", "update", {"wall_id": str(door.pk), "rotationAnchor": "end"})
        request = {"request_id": str(uuid.uuid4()), "expected_version": 1, "expected_scene_version": 1}
        first = self.sync(**request)
        self.assertEqual(first.status_code, 200, first.content)
        repeated = self.sync(**request)
        self.assertEqual(repeated.status_code, 200, repeated.content)
        self.assertEqual(repeated.json(), first.json())
        self.assertEqual(MapBuilderProject.objects.get(pk=self.project_id).version, 2)
        mismatch = self.sync(**{**request, "expected_version": 2})
        self.assertEqual(mismatch.status_code, 409, mismatch.content)

    def test_stale_revisions_and_missing_scene_are_rejected_without_writes(self):
        self.assertEqual(self.save().status_code, 200)
        self.assertEqual(self.sync().status_code, 409)
        generated = self.generate()
        self.assertEqual(generated.status_code, 200, generated.content)
        before = MapBuilderProject.objects.get(pk=self.project_id)
        for changes in ({"expected_version": 0}, {"expected_scene_version": 0}):
            response = self.sync(**changes)
            self.assertEqual(response.status_code, 409, response.content)
        after = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual((after.document, after.generation, after.version),
                         (before.document, before.generation, before.version))

    def test_sync_requires_current_gm_membership_and_campaign_ownership(self):
        self.generated()
        for user in (self.player, self.streamer, None):
            if user:
                self.client.force_login(user)
            else:
                self.client.logout()
            with self.subTest(user=user):
                self.assertIn(self.sync().status_code, (403, 404))
        self.client.force_login(self.gm)
        foreign = MapBuilderProject.objects.create(campaign=self.other, name="Foreign source", document=self.doc)
        response = self.post(f"{self.base}/projects/{foreign.pk}/sync", {
            "request_id": str(uuid.uuid4()), "expected_version": 1, "expected_scene_version": 1,
        })
        self.assertEqual(response.status_code, 404)
        self.membership.delete()
        self.assertEqual(self.sync().status_code, 404)
