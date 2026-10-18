"""Typed fan-out survives native execution, reference cleanup and archives."""

from copy import deepcopy
from unittest.mock import patch
import uuid

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.accounts.services import AuthError
from gravewright.administration.archives import export_campaign, import_campaign, read_archive
from gravewright.audio import services as audio_services
from gravewright.audio.models import Playback, Track
from gravewright.campaigns.models import Campaign, Membership
from gravewright.maps import builder_services, services
from gravewright.maps.blueprint_runtime import clean_native_blueprint, detach_blueprint_light
from gravewright.maps.blueprints import clean_blueprint, convert_blueprint, default_blueprint, evaluate_graph
from gravewright.maps.models import MapBuilderProject, Receipt, SceneObject

from . import test_builder_blueprints as fixtures


def execution(origin, target, output="next"):
    return {"from": origin, "to": target, "output": output, "kind": "execution"}


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class BlueprintV2IntegrationTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    command = fixtures.BuilderBlueprintTests.command
    update_scene = fixtures.BuilderBlueprintTests.update_scene

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        blueprint = convert_blueprint(self.doc["doors"][0]["blueprint"])
        graph = {"nodes": [
            {"id": "event", "type": "event", "event": "interact", "x": 0, "y": 0},
            {"id": "node0", "type": "light", "targetId": self.light_id,
             "enabled": True, "x": 200, "y": 0},
            {"id": "node1", "type": "sound", "trackId": str(self.sound.pk),
             "volume": .35, "x": 400, "y": 0},
            {"id": "after", "type": "light", "targetId": self.light_id,
             "enabled": False, "x": 800, "y": 0},
            {"id": "tail", "type": "sound", "trackId": str(self.sound.pk),
             "volume": .65, "x": 300, "y": 240},
        ], "edges": []}
        graph["edges"] = [execution("event", "node0"), execution("node0", "node1"),
                          execution("node1", "after"), execution("event", "tail")]
        blueprint["graphs"] = {"interact": graph}
        self.doc["doors"][0]["blueprint"] = clean_blueprint(blueprint)

    def source_and_snapshot(self):
        source = MapBuilderProject.objects.get(pk=self.project_id)
        snapshot = next(row["data"]["blueprint"] for row in source.generation["objects"]
                        if row["data"].get("kind") == "door")
        return source, snapshot

    def test_save_generation_and_receipt_retry_preserve_typed_ordered_effects(self):
        authored = deepcopy(self.doc)
        self.generated()
        source, snapshot = self.source_and_snapshot()
        self.assertEqual(source.document, authored)
        native = clean_native_blueprint(self.door_object.data["blueprint"],
                                        self.campaign.pk, self.scene.pk)
        self.assertEqual(native, snapshot)
        self.assertEqual(native["version"], 2)
        light_ids = {node["targetId"] for node in native["graphs"]["interact"]["nodes"]
                     if node["type"] == "light"}
        self.assertEqual(light_ids, {str(self.light_object.pk)})
        self.assertNotIn(self.light_id, light_ids)
        self.assertFalse(Playback.objects.filter(scene=self.scene).exists())

        request_id = uuid.uuid4()
        receipts = Receipt.objects.count()
        with patch("gravewright.audio.services.play_effects", wraps=audio_services.play_effects) as play:
            first = self.command(request_id=request_id)
            playback = Playback.objects.get(scene=self.scene)
            played, revision = deepcopy(playback.data), playback.version
            self.assertEqual(self.command(request_id=request_id), first)
            self.assertEqual(Receipt.objects.count(), receipts + 1)
            self.assertEqual(play.call_count, 1)
            self.assertEqual([effect["volume"] for effect in play.call_args.args[1]], [.35, .65])
        self.assertEqual(first["blueprint"]["trace"][-1],
                         {"event": "interact", "nodes": ["event", "node0", "node1", "after", "tail"]})
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])
        self.assertEqual(self.light_object.version, 3)
        playback.refresh_from_db()
        self.assertEqual(playback.data, played)
        self.assertEqual(playback.version, revision)
        self.assertEqual(played["ambient"][0]["volume"], .65)
        # Every fresh interaction starts its graph, regardless of the current state.
        with patch("gravewright.audio.services.play_effects", wraps=audio_services.play_effects) as play:
            self.command("open")
            self.assertEqual(play.call_count, 1)
            self.assertEqual([effect["volume"] for effect in play.call_args.args[1]], [.35, .65])

    def test_deleting_light_preserves_typed_branch_position_and_remaining_sound_order(self):
        self.generated()
        services.command(self.campaign.pk, self.gm.pk, "objects",
            {"mapId": str(self.scene.pk), "area": "lights", "action": "delete",
             "data": {"light_id": str(self.light_object.pk)}}, uuid.uuid4())
        self.door_object.refresh_from_db()
        source, snapshot = self.source_and_snapshot()
        expected = [execution("event", "node1"), execution("event", "tail")]
        for blueprint in (self.door_object.data["blueprint"], snapshot):
            self.assertEqual(blueprint["graphs"]["interact"]["edges"], expected)
            self.assertEqual(evaluate_graph(blueprint, "interact", "open")["trace"],
                             ["event", "node1", "tail"])
            clean_blueprint(blueprint, light_ids=set())
        clean_native_blueprint(self.door_object.data["blueprint"], self.campaign.pk, self.scene.pk)
        self.assertIn(self.light_id, str(source.document))
        result = self.command()
        self.assertEqual(result["blueprint"]["trace"][-1]["nodes"], ["event", "node1", "tail"])
        self.assertEqual(Playback.objects.get(scene=self.scene).data["ambient"][0]["volume"], .65)
        with self.assertRaisesMessage(services.MapError, "changed in the VTT"):
            self.update_scene()

    def test_deleting_sound_cleans_typed_source_native_and_snapshot_continuations(self):
        self.generated()
        audio_services.public_command(self.campaign.pk, self.gm.pk, "track-delete",
            {"id": str(self.sound.pk), "version": self.sound.version}, uuid.uuid4())
        self.door_object.refresh_from_db()
        source, snapshot = self.source_and_snapshot()
        expected = [execution("event", "node0"), execution("node0", "after")]
        for blueprint in (source.document["doors"][0]["blueprint"],
                          self.door_object.data["blueprint"], snapshot):
            self.assertEqual(blueprint["graphs"]["interact"]["edges"], expected)
            self.assertEqual(evaluate_graph(blueprint, "interact", "open")["trace"],
                             ["event", "node0", "after"])
            clean_blueprint(blueprint, track_ids=set())
        builder_services.clean_document(source.document, self.membership)
        clean_native_blueprint(self.door_object.data["blueprint"], self.campaign.pk, self.scene.pk)
        self.command()
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])
        self.assertFalse(Playback.objects.filter(scene=self.scene).exists())
        self.update_scene()

    def test_scene_export_without_audio_preserves_typed_branches_on_export_copies(self):
        self.generated()
        source, _ = self.source_and_snapshot()
        original = deepcopy((source.document, source.generation, self.door_object.data))
        raw = export_campaign(self.campaign, {"audio": False})
        payload, _ = read_archive(raw)
        self.assertFalse(any(row["model"].startswith("gravewright_audio.") for row in payload["records"]))
        restored = import_campaign(raw, self.gm, "Typed silent room")
        project = MapBuilderProject.objects.get(campaign=restored)
        door = SceneObject.objects.get(scene=project.scene, kind="walls", data__kind="door")
        who = Membership.objects.get(campaign=restored, user=self.gm)
        source_blueprint = builder_services.clean_document(project.document, who)["doors"][0]["blueprint"]
        native_blueprint = clean_native_blueprint(door.data["blueprint"], restored.pk, project.scene_id)
        snapshot = next(row["data"]["blueprint"] for row in project.generation["objects"]
                        if row["data"].get("kind") == "door")
        for blueprint in (source_blueprint, native_blueprint, snapshot):
            clean_blueprint(blueprint, track_ids=set())
            self.assertEqual(blueprint["version"], 2)
            self.assertEqual(blueprint["graphs"]["interact"]["edges"],
                             [execution("event", "node0"), execution("node0", "after")])
        source.refresh_from_db()
        self.door_object.refresh_from_db()
        self.assertEqual((source.document, source.generation, self.door_object.data), original)
        self.assertTrue(Track.objects.filter(pk=self.sound.pk).exists())

    @override_settings(CAMPAIGN_CLONE_ENABLED=True)
    def test_selective_clone_reports_cleanup_limit_without_modifying_campaign_data(self):
        nodes = [{"id": "event", "type": "event", "event": "interact", "x": 0, "y": 0},
                 {"id": "removed", "type": "sound", "trackId": str(self.sound.pk),
                  "volume": .5, "x": 480, "y": 0}]
        nodes.extend({"id": f"before{index}", "type": "state", "targetState": "open",
                      "x": 240, "y": index * 100} for index in range(8))
        nodes.extend({"id": f"after{index}", "type": "light", "targetId": self.light_id,
                      "enabled": True, "x": 720, "y": index * 100} for index in range(10))
        edges = [execution("event", f"before{index}") for index in range(8)]
        edges.extend(execution(f"before{index}", "removed") for index in range(8))
        edges.extend(execution("removed", f"after{index}") for index in range(10))
        self.doc["doors"][0]["blueprint"]["graphs"]["interact"] = {"nodes": nodes, "edges": edges}
        self.generated()
        source, _ = self.source_and_snapshot()
        original = deepcopy((source.document, source.generation, self.door_object.data))
        campaign_count = Campaign.objects.count()
        receipts = Receipt.objects.count()
        for action in ("preview", "create"):
            response = self.post(f"/api/admin/campaigns/{self.campaign.pk}/clone/{action}",
                                 {"title": "Silent copy", "options": {"audio": False}})
            with self.subTest(action=action):
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json(), {"error": "blueprint_audio_cleanup_limit"})
        with self.assertRaisesMessage(AuthError, "blueprint_audio_cleanup_limit"):
            export_campaign(self.campaign, {"audio": False})
        source.refresh_from_db()
        self.door_object.refresh_from_db()
        self.assertEqual((source.document, source.generation, self.door_object.data), original)
        self.assertEqual(Campaign.objects.count(), campaign_count)
        self.assertEqual(Receipt.objects.count(), receipts)
        self.assertTrue(Track.objects.filter(pk=self.sound.pk).exists())
        clean_blueprint(self.door_object.data["blueprint"])


class BlueprintV2CleanupLimitsTests(SimpleTestCase):
    def test_cleanup_limit_applies_after_all_actions_for_the_deleted_target_are_removed(self):
        light_id = str(uuid.uuid4())
        blueprint = convert_blueprint(default_blueprint())
        nodes = [{"id": "event", "type": "event", "event": "interact", "x": 0, "y": 0},
                 {"id": "removed", "type": "light", "targetId": light_id,
                  "enabled": True, "x": 480, "y": 0}]
        nodes.extend({"id": f"before{index}", "type": "state", "targetState": "open",
                      "x": 240, "y": index * 100} for index in range(8))
        nodes.extend({"id": f"after{index}", "type": "light", "targetId": light_id,
                      "enabled": False, "x": 720, "y": index * 100} for index in range(10))
        edges = [execution("event", f"before{index}") for index in range(8)]
        edges.extend(execution(f"before{index}", "removed") for index in range(8))
        edges.extend(execution("removed", f"after{index}") for index in range(10))
        blueprint["graphs"]["interact"] = {"nodes": nodes, "edges": edges}
        blueprint = clean_blueprint(blueprint)
        self.assertTrue(detach_blueprint_light(blueprint, light_id))
        clean_blueprint(blueprint, light_ids=set())
        self.assertEqual(blueprint["graphs"]["interact"]["edges"],
                         [execution("event", f"before{index}") for index in range(8)])

    def test_expanding_cleanup_rejects_over_limit_and_preserves_every_original_graph(self):
        light_id = str(uuid.uuid4())
        track_id = str(uuid.uuid4())
        blueprint = convert_blueprint(default_blueprint())
        blueprint["graphs"]["signal:Close"] = {
            "nodes": [
                {"id": "event", "type": "event", "event": "signal:Close", "x": 0, "y": 0},
                {"id": "removed", "type": "light", "targetId": light_id,
                 "enabled": False, "x": 240, "y": 0},
            ],
            "edges": [execution("event", "removed")],
        }
        nodes = [{"id": "event", "type": "event", "event": "interact", "x": 0, "y": 0},
                 {"id": "removed", "type": "light", "targetId": light_id,
                  "enabled": True, "x": 480, "y": 0}]
        nodes.extend({"id": f"before{index}", "type": "state", "targetState": "open",
                      "x": 240, "y": index * 100} for index in range(8))
        nodes.extend({"id": f"after{index}", "type": "sound", "trackId": track_id,
                      "volume": .5, "x": 720, "y": index * 100} for index in range(10))
        edges = [execution("event", f"before{index}") for index in range(8)]
        edges.extend(execution(f"before{index}", "removed") for index in range(8))
        edges.extend(execution("removed", f"after{index}") for index in range(10))
        blueprint["graphs"]["interact"] = {"nodes": nodes, "edges": edges}
        blueprint = clean_blueprint(blueprint)
        before = deepcopy(blueprint)
        with self.assertRaisesMessage(services.MapError, "too many nodes or connections"):
            detach_blueprint_light(blueprint, light_id)
        self.assertEqual(blueprint, before)
