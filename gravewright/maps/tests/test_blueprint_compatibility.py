"""Blueprint art and portable archives use the host's existing boundaries."""

from copy import deepcopy
from io import BytesIO
import uuid
import wave

from django.core.files.base import ContentFile
from django.test import TransactionTestCase, override_settings

from gravewright.administration.archives import export_campaign, import_campaign, read_archive
from gravewright.audio import services as audio_services
from gravewright.audio.models import Track
from gravewright.campaigns.models import Membership
from gravewright.maps import builder_services, objects, services
from gravewright.maps.blueprints import clean_blueprint, default_blueprint
from gravewright.maps.blueprint_runtime import clean_native_blueprint
from gravewright.maps.models import Broadcast, MapBuilderProject, Scene, SceneObject, SceneState
from gravewright.table.models import DocumentAccess

from . import test_builder_projects as fixtures
from . import test_builder_expansion as expansion_fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], DYNAMIC_LIGHTING_ENABLED=True)
class BlueprintCompatibilityTests(TransactionTestCase):
    asset = fixtures.BuilderProjectTests.asset

    def setUp(self):
        fixtures.BuilderProjectTests.setUp(self)
        self.who = self.membership
        self.viewer = Membership.objects.get(campaign=self.campaign, user=self.player)
        self.alternate = self.asset("open-door.png", "#00bbcc")
        self.doc = expansion_fixtures.BuilderExpansionTests.expanded(self)
        self.doc["assets"].append({"assetId": str(self.alternate.pk), "role": "door"})
        recording = BytesIO()
        with wave.open(recording, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(1)
            wav.setframerate(8000)
            wav.writeframes(b"\x80" * 80)
        self.track = Track.objects.create(campaign=self.campaign, name="Door latch",
            file=ContentFile(recording.getvalue(), name="latch.wav"), content_type="audio/wav",
            duration=0.01, kind="effect", loop=False)
        blueprint = default_blueprint()
        blueprint["states"]["open"] = {"appearance": "asset", "assetId": str(self.alternate.pk)}
        blueprint["graphs"]["interact"] = {
            "nodes": [
                {"id": "event", "type": "event", "event": "interact", "x": 0, "y": 0},
                {"id": "condition", "type": "condition", "state": "closed", "x": 240, "y": 0},
                {"id": "sound1", "type": "sound", "trackId": str(self.track.pk), "volume": 1, "x": 480, "y": 0},
                {"id": "sound2", "type": "sound", "trackId": str(self.track.pk), "volume": 0.5, "x": 720, "y": 0},
                {"id": "light", "type": "light", "targetId": self.doc["lights"][0]["id"], "enabled": False, "x": 960, "y": 0},
                {"id": "state", "type": "state", "targetState": "closed", "x": 480, "y": 240},
                {"id": "open", "type": "state", "targetState": "open", "x": 1200, "y": 0},
            ],
            "edges": [
                {"from": "event", "to": "condition", "output": "next"},
                {"from": "condition", "to": "sound1", "output": "true"},
                {"from": "condition", "to": "state", "output": "false"},
                {"from": "sound1", "to": "sound2", "output": "next"},
                {"from": "sound2", "to": "light", "output": "next"},
                {"from": "light", "to": "open", "output": "next"},
            ],
        }
        for edge in blueprint["graphs"]["interact"]["edges"]:
            edge["kind"] = "execution"
        self.doc["doors"][0]["blueprint"] = blueprint
        self.doc = builder_services.clean_document(self.doc, self.who)
        self.scene = Scene.objects.create(campaign=self.campaign, name="Blueprint room", width=512,
            height=512, settings=services.settings({"gridSize": 64}))
        native = builder_services.native_objects(self.doc, self.scene)
        SceneObject.objects.bulk_create(native)
        self.native_door = self.scene.elements.get(kind="walls", data__kind="door")
        self.native_light = self.scene.elements.get(kind="lights")
        SceneState.objects.create(scene=self.scene)
        Broadcast.objects.create(campaign=self.campaign, scene=self.scene)
        self.project = MapBuilderProject.objects.create(campaign=self.campaign, scene=self.scene,
            name=self.doc["name"], document=deepcopy(self.doc), version=1,
            generation=builder_services.generation_manifest(self.scene, self.doc, native))

    def image_status(self, asset):
        response = self.client.get(f"/game/map-assets/{asset.pk}")
        response.close()
        return response.status_code

    def audience_assets(self):
        response = self.client.get(f"/api/containers/{self.campaign.pk}/library/asset-state")
        self.assertEqual(response.status_code, 200, response.content)
        return {row["id"] for row in response.json()["assets"]}

    def operate(self, state, *, who=None, scene=None, door=None):
        return services.command(self.campaign.pk if scene is None else scene.campaign_id,
            (who or self.who).user_id, "objects", {"mapId": str((scene or self.scene).pk),
                "area": "walls", "action": "door", "data": {
                    "wall_id": str((door or self.native_door).pk), "door_state": state,
                }}, str(uuid.uuid4()))

    def delete_asset(self, asset):
        self.client.force_login(self.gm)
        response = self.client.post(f"/api/containers/{self.campaign.pk}/library/assets/delete",
            {"asset_id": str(asset.pk)}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)

    def test_audience_catalog_and_file_follow_only_the_current_state_appearance(self):
        self.client.force_login(self.player)
        self.assertEqual(self.image_status(self.door), 200)
        self.assertEqual(self.image_status(self.alternate), 404)
        self.assertIn(str(self.door.pk), self.audience_assets())
        self.assertNotIn(str(self.alternate.pk), self.audience_assets())
        self.operate("open")
        self.assertEqual(self.image_status(self.door), 404)
        self.assertEqual(self.image_status(self.alternate), 200)
        ids = self.audience_assets()
        self.assertIn(str(self.alternate.pk), ids)
        self.assertNotIn(str(self.door.pk), ids)
        row = next(row for row in objects.layer_state(self.scene, self.viewer)["walls"] if row["id"] == str(self.native_door.pk))
        self.assertNotIn("blueprint", row)
        self.assertEqual(row["asset_id"], str(self.alternate.pk))
        result = self.operate("closed", who=self.viewer)
        self.assertNotIn("blueprint", result)
        self.assertNotIn("blueprint", result["wall"])

    def test_hidden_and_undiscovered_state_art_is_not_delivered(self):
        self.client.force_login(self.player)
        self.native_door.data["blueprint"]["states"]["closed"] = {"appearance": "hidden"}
        self.native_door.save()
        self.assertEqual(self.image_status(self.door), 404)
        self.assertEqual(self.image_status(self.alternate), 404)
        self.assertNotIn(str(self.door.pk), self.audience_assets())
        self.native_door.data["blueprint"]["states"]["closed"] = {
            "appearance": "asset", "assetId": str(self.alternate.pk)}
        for presentation in ("secret", "invisible"):
            self.native_door.data.update(presentation=presentation, discovered=False)
            self.native_door.save()
            self.assertEqual(self.image_status(self.alternate), 404)
            self.assertNotIn(str(self.alternate.pk), self.audience_assets())
            self.native_door.data["discovered"] = True
            self.native_door.save()
            self.assertEqual(self.image_status(self.alternate), 200)

    def test_file_delivery_obeys_the_broadcast_scene_document_permission(self):
        self.client.force_login(self.player)
        self.assertEqual(self.image_status(self.door), 200)
        DocumentAccess.objects.create(campaign=self.campaign, kind="scenes", resource_id=str(self.scene.pk),
            grants={"default": "none"})
        self.assertEqual(self.image_status(self.door), 404)
        self.assertEqual(self.client.get(f"/api/containers/{self.campaign.pk}/library/asset-state").status_code, 404)

    def test_deleting_alternate_image_cleans_source_native_and_snapshot_without_blocking_door(self):
        before_environment = self.scene.environment.version
        self.delete_asset(self.alternate)
        self.project.refresh_from_db()
        self.native_door.refresh_from_db()
        for blueprint in (self.project.document["doors"][0]["blueprint"], self.native_door.data["blueprint"],
                          next(row["data"]["blueprint"] for row in self.project.generation["objects"]
                               if row["data"].get("kind") == "door")):
            self.assertEqual(blueprint["states"]["open"], {"appearance": "inherit"})
        self.assertEqual(self.native_door.data["thickness"], 32)
        self.assertEqual(self.native_door.data["movement_behavior"], "block")
        self.scene.environment.refresh_from_db()
        self.assertGreater(self.scene.environment.version, before_environment)
        clean_native_blueprint(self.native_door.data["blueprint"], self.campaign.pk, self.scene.pk)
        self.operate("open")
        self.native_door.refresh_from_db()
        self.assertEqual(self.native_door.data["door_state"], "open")
        self.project.refresh_from_db()
        builder_services.update_target(self.project, self.who, {"expected_scene_version": self.scene.version},
            builder_services.clean_document(self.project.document, self.who))

    def test_deleting_base_art_retains_alternate_sizing_and_generation_ownership(self):
        self.delete_asset(self.door)
        self.project.refresh_from_db()
        self.native_door.refresh_from_db()
        self.assertNotIn("asset_id", self.native_door.data)
        self.assertEqual(self.native_door.data["thickness"], 32)
        self.assertEqual(self.native_door.data["blueprint"]["states"]["open"]["assetId"], str(self.alternate.pk))
        builder_services.update_target(self.project, self.who, {"expected_scene_version": self.scene.version},
            builder_services.clean_document(self.project.document, self.who))
        self.operate("open")
        self.client.force_login(self.player)
        self.assertEqual(self.image_status(self.alternate), 200)

    def test_art_cleanup_does_not_adopt_unrelated_manual_geometry(self):
        self.native_door.data["x1"] += 1
        self.native_door.save()
        self.delete_asset(self.door)
        self.project.refresh_from_db()
        with self.assertRaisesMessage(services.MapError, "changed in the VTT"):
            builder_services.update_target(self.project, self.who,
                {"expected_scene_version": self.scene.version}, self.project.document)

    def test_deleted_sound_actions_are_detached_and_remaining_light_action_executes(self):
        audio_services.command(self.who, "track-delete", {"id": str(self.track.pk), "version": 1})
        self.project.refresh_from_db()
        self.native_door.refresh_from_db()
        for blueprint in (self.project.document["doors"][0]["blueprint"], self.native_door.data["blueprint"]):
            graph = blueprint["graphs"]["interact"]
            self.assertFalse(any(node["type"] == "sound" for node in graph["nodes"]))
            self.assertIn({"from": "condition", "to": "light", "output": "true", "kind": "execution"}, graph["edges"])
        self.operate("open")
        self.native_light.refresh_from_db()
        self.assertFalse(self.native_light.data["enabled"])
        self.project.refresh_from_db()
        builder_services.update_target(self.project, self.who, {"expected_scene_version": self.scene.version},
            builder_services.clean_document(self.project.document, self.who))

    def test_scene_export_without_audio_removes_only_sound_actions_from_export_copies(self):
        before_document = deepcopy(self.project.document)
        before_generation = deepcopy(self.project.generation)
        before_native = deepcopy(self.native_door.data)
        raw = export_campaign(self.campaign, {"audio": False})
        payload, _ = read_archive(raw)
        self.assertFalse(any(row["model"].startswith("gravewright_audio.") for row in payload["records"]))
        restored = import_campaign(raw, self.gm, "Silent blueprint room")
        project = MapBuilderProject.objects.get(campaign=restored)
        door = SceneObject.objects.get(scene=project.scene, kind="walls", data__kind="door")
        who = Membership.objects.get(campaign=restored, user=self.gm)
        source_blueprint = builder_services.clean_document(project.document, who)["doors"][0]["blueprint"]
        native_blueprint = clean_native_blueprint(door.data["blueprint"], restored.pk, project.scene_id)
        snapshot_blueprint = next(row["data"]["blueprint"] for row in project.generation["objects"] if row["data"].get("kind") == "door")
        for blueprint in (source_blueprint, native_blueprint, snapshot_blueprint):
            clean_blueprint(blueprint)
            graph = blueprint["graphs"]["interact"]
            self.assertEqual({node["type"] for node in graph["nodes"]}, {"event", "condition", "light", "state"})
            self.assertIn({"from": "condition", "to": "light", "output": "true", "kind": "execution"}, graph["edges"])
            self.assertIn({"from": "condition", "to": "state", "output": "false", "kind": "execution"}, graph["edges"])
        self.operate("open", who=who, scene=project.scene, door=door)
        door.refresh_from_db()
        self.assertEqual(door.data["door_state"], "open")
        restored_light = SceneObject.objects.get(scene=project.scene, kind="lights")
        self.assertFalse(restored_light.data["enabled"])
        project.refresh_from_db()
        builder_services.update_target(project, who, {"expected_scene_version": project.scene.version}, project.document)
        self.project.refresh_from_db()
        self.native_door.refresh_from_db()
        self.assertEqual(self.project.document, before_document)
        self.assertEqual(self.project.generation, before_generation)
        self.assertEqual(self.native_door.data, before_native)
        self.assertTrue(Track.objects.filter(pk=self.track.pk).exists())

    def test_full_clone_remaps_native_targets_but_preserves_authored_source_targets(self):
        restored = import_campaign(export_campaign(self.campaign), self.gm, "Cloned blueprint room")
        project = MapBuilderProject.objects.get(campaign=restored)
        door = SceneObject.objects.get(scene=project.scene, kind="walls", data__kind="door")
        light = SceneObject.objects.get(scene=project.scene, kind="lights")
        sound = Track.objects.get(campaign=restored)
        self.assertNotEqual(light.pk, self.native_light.pk)
        self.assertNotEqual(sound.pk, self.track.pk)
        source_nodes = project.document["doors"][0]["blueprint"]["graphs"]["interact"]["nodes"]
        native_nodes = door.data["blueprint"]["graphs"]["interact"]["nodes"]
        self.assertEqual(next(node["targetId"] for node in source_nodes if node["type"] == "light"), self.doc["lights"][0]["id"])
        self.assertEqual(next(node["targetId"] for node in native_nodes if node["type"] == "light"), str(light.pk))
        self.assertEqual({node["trackId"] for node in native_nodes if node["type"] == "sound"}, {str(sound.pk)})
        who = Membership.objects.get(campaign=restored, user=self.gm)
        self.operate("open", who=who, scene=project.scene, door=door)
        light.refresh_from_db()
        self.assertFalse(light.data["enabled"])
