"""Door blueprints use native authority, transport, ownership and retry rules."""

from copy import deepcopy
from datetime import timedelta
from io import BytesIO
import uuid
import wave

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import timezone

from gravewright.audio.models import Playback, Track
from gravewright.audio import services as audio_services
from gravewright.campaigns.models import StreamerLink
from gravewright.journals.services import JournalError
from gravewright.maps import builder_services, objects, services
from gravewright.maps.blueprints import default_blueprint
from gravewright.maps.models import Broadcast, MapBuilderProject, Receipt, Scene
from . import test_builder_projects as fixtures


def graph(event, *actions):
    nodes = [{"id": "event", "type": "event", "event": event, "x": 0, "y": 0}]
    for index, action in enumerate(actions):
        nodes.append({"id": "node" + str(index), "x": (index + 1) * 200, "y": 0, **action})
    return {"nodes": nodes, "edges": [{"from": before["id"], "to": after["id"], "output": "next", "kind": "execution"}
                                      for before, after in zip(nodes, nodes[1:])]}


def interaction_graph(light_id, track_id):
    """Author state comparisons and both interaction branches explicitly."""
    nodes = [
        {"id": "event", "type": "event", "event": "interact"},
        {"id": "locked", "type": "condition", "state": "locked"},
        {"id": "open", "type": "condition", "state": "open"},
        {"id": "open-state", "type": "state", "targetState": "open"},
        {"id": "open-light", "type": "light", "targetId": light_id, "enabled": True},
        {"id": "open-sound", "type": "sound", "trackId": track_id, "volume": .35},
        {"id": "close-state", "type": "state", "targetState": "closed"},
        {"id": "close-light", "type": "light", "targetId": light_id, "enabled": False},
        {"id": "locked-sound", "type": "sound", "trackId": track_id, "volume": .5},
    ]
    links = [("event", "locked", "next"), ("locked", "locked-sound", "true"), ("locked", "open", "false"),
             ("open", "close-state", "true"), ("close-state", "close-light", "next"),
             ("open", "open-state", "false"), ("open-state", "open-light", "next"), ("open-light", "open-sound", "next")]
    return {"nodes": [{**row, "x": index * 200, "y": 0} for index, row in enumerate(nodes)],
            "edges": [{"from": origin, "to": target, "output": output, "kind": "execution"}
                      for origin, target, output in links]}


def authored_node(blueprint, identifier):
    return next(row for row in blueprint["graphs"]["interact"]["nodes"] if row["id"] == identifier)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class BuilderBlueprintTests(TestCase):
    asset = fixtures.BuilderProjectTests.asset
    post = fixtures.BuilderProjectTests.post
    save = fixtures.BuilderProjectTests.save
    generate = fixtures.BuilderProjectTests.generate
    files = fixtures.BuilderProjectTests.files

    def setUp(self):
        fixtures.BuilderProjectTests.setUp(self)
        StreamerLink.objects.create(campaign=self.campaign, guest=self.streamer, digest="b" * 64,
                                    expires_at=timezone.now() + timedelta(hours=1))
        self.doc["schemaVersion"] = 3
        layer_id = str(uuid.uuid4())
        self.doc["layers"] = [{"id": layer_id, "name": "Room", "visible": True, "locked": False}]
        for kind in ("floors", "walls", "doors"):
            for row in self.doc[kind]:
                row["layerId"] = layer_id
        self.doc["floors"][0]["rotation"] = 0
        self.doc["decorations"] = []
        self.light_id = str(uuid.uuid4())
        self.doc["lights"] = [{"id": self.light_id, "layerId": layer_id, "x": 5, "y": 5,
            "brightRadius": 2, "dimRadius": 4, "color": "#ffd8a8", "intensity": .8,
            "enabled": False, "rotation": 0, "angle": 360, "animation": "none"}]
        sound = BytesIO()
        with wave.open(sound, "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(8000)
            stream.writeframes(b"\x00\x00" * 8000)
        self.sound = Track.objects.create(campaign=self.campaign, name="Door click", duration=1,
            content_type="audio/wav", kind="effect", loop=False,
            file=ContentFile(sound.getvalue(), name="click.wav"))
        self.alternate = self.asset("open.png", "#2244ee")
        self.doc["assets"].append({"assetId": str(self.alternate.pk), "role": "door"})
        blueprint = default_blueprint()
        blueprint["states"]["open"] = {"appearance": "asset", "assetId": str(self.alternate.pk)}
        blueprint["states"]["locked"] = {"appearance": "hidden"}
        blueprint["graphs"] = {"interact": interaction_graph(self.light_id, str(self.sound.pk))}
        self.doc["doors"][0]["blueprint"] = blueprint

    def generated(self):
        saved = self.save()
        self.assertEqual(saved.status_code, 200, saved.content)
        generated = self.generate()
        self.assertEqual(generated.status_code, 200, generated.content)
        self.scene = Scene.objects.get(pk=generated.json()["scene"]["id"])
        self.scene.visibility = "players"
        self.scene.save(update_fields=["visibility"])
        Broadcast.objects.update_or_create(campaign=self.campaign, defaults={"scene": self.scene})
        self.door_object = self.scene.elements.get(kind="walls", data__kind="door")
        self.light_object = self.scene.elements.get(kind="lights")
        return self.scene

    def command(self, target="open", user=None, request_id=None, action="door", **extra):
        return services.command(self.campaign.pk, (user or self.gm).pk, "objects",
            {"mapId": str(self.scene.pk), "area": "walls", "action": action,
             "data": {"wall_id": str(self.door_object.pk), "door_state": target, **extra}},
            request_id or uuid.uuid4())

    def update_scene(self):
        source = MapBuilderProject.objects.get(pk=self.project_id)
        self.scene.refresh_from_db()
        return builder_services.update(self.campaign.pk, self.gm.pk, self.project_id,
            {"request_id": str(uuid.uuid4()), "expected_version": source.version,
             "expected_scene_version": self.scene.version})

    def test_definition_roundtrip_native_ids_and_campaign_sound_catalog(self):
        self.generated()
        source = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual(source.document, self.doc)
        node = authored_node(self.door_object.data["blueprint"], "open-light")
        self.assertEqual(node["targetId"], str(self.light_object.pk))
        self.assertNotEqual(node["targetId"], self.light_id)
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertNotIn("state", self.door_object.data["blueprint"])
        self.assertFalse(Playback.objects.filter(scene=self.scene).exists())
        catalog = builder_services.catalog(self.campaign.pk, self.gm.pk)
        self.assertEqual(catalog["sounds"], [{"id": str(self.sound.pk), "name": "Door click",
            "url": f"/game/audio/{self.sound.pk}", "duration": 1}])

    def test_unknown_foreign_and_misclassified_references_fail_before_save(self):
        foreign_sound = Track.objects.create(campaign=self.other, name="Private", duration=1)
        original = deepcopy(self.doc)
        mutations = [
            lambda b: b["states"]["open"].update(assetId=str(self.foreign_asset.pk)),
            lambda b: b["states"]["open"].update(assetId=str(self.floor.pk)),
            lambda b: authored_node(b, "open-light").update(targetId=str(uuid.uuid4())),
            lambda b: authored_node(b, "open-sound").update(trackId=str(foreign_sound.pk)),
        ]
        for mutate in mutations:
            self.doc = deepcopy(original)
            mutate(self.doc["doors"][0]["blueprint"])
            with self.subTest(blueprint=self.doc["doors"][0]["blueprint"]):
                response = self.save()
                self.assertEqual(response.status_code, 400, response.content)
                self.assertFalse(MapBuilderProject.objects.exists())

    def test_only_gm_may_assign_graphs_to_native_doors(self):
        self.generated()
        previous = deepcopy(self.door_object.data)
        with self.assertRaisesMessage(services.MapError, "Only the GM"):
            self.command("closed", user=self.player, action="update", blueprint=default_blueprint())
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data, previous)

    def test_alternate_art_without_base_asset_keeps_thickness_when_native_door_is_copied(self):
        self.doc["doors"][0]["assetId"] = None
        self.generated()
        payload = {**deepcopy(self.door_object.data), "x1": 64, "x2": 128}
        result = objects.apply(self.scene, self.membership, "wall-selection", "paste", {"walls": [payload]})
        copy = self.scene.elements.get(pk=result["walls"][0])
        self.assertEqual(copy.data["thickness"], 32)
        self.assertEqual(copy.data["blueprint"], self.door_object.data["blueprint"])

    def test_state_effects_run_once_with_retry_and_reads_never_replay(self):
        self.generated()
        request_id = uuid.uuid4()
        first = self.command(request_id=request_id)
        playback = Playback.objects.get(scene=self.scene)
        played = deepcopy(playback.data)
        self.door_object.refresh_from_db()
        self.light_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")
        self.assertTrue(self.light_object.data["enabled"])
        self.assertEqual(played["ambient"][0]["volume"], .35)
        self.assertFalse(played["ambient"][0]["loop"])
        self.assertEqual(self.command(request_id=request_id), first)
        for _ in range(2):
            objects.layer_state(self.scene, self.membership)
            audio_services.state(self.membership, str(self.scene.pk))
            builder_services.detail(self.campaign.pk, self.gm.pk, self.project_id)
        playback.refresh_from_db()
        self.assertEqual(playback.data, played)
        self.assertEqual(playback.version, 2)
        self.command("closed")
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])
        self.command("open")
        playback.refresh_from_db()
        self.assertEqual(playback.version, 3, "A new interaction executes its authored opening branch again.")

    def test_players_cannot_lock_unlock_or_operate_secret_doors(self):
        self.generated()
        self.command(user=self.player)
        with self.assertRaises(services.MapError):
            self.command("locked", user=self.player, action="update", version=self.door_object.version)
        self.door_object.refresh_from_db()
        self.command("locked", action="update", version=self.door_object.version)
        result = self.command("open", user=self.player)
        self.assertEqual(result["wall"]["door_state"], "locked")
        self.assertNotIn("blueprint", result)
        self.assertNotIn("blueprint", result["wall"])
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "locked")
        self.assertEqual(Playback.objects.get(scene=self.scene).data["ambient"][0]["volume"], .5)
        self.door_object.data.update(presentation="secret", discovered=False)
        self.door_object.save()
        with self.assertRaises(services.MapError):
            self.command("open", user=self.player)
        with self.assertRaisesMessage(JournalError, "read-only"):
            self.command(user=self.streamer)

    def test_player_graph_cannot_unlock_a_locked_door_and_effects_roll_back(self):
        self.doc["doors"][0]["state"] = "locked"
        self.doc["doors"][0]["blueprint"]["graphs"]["interact"] = graph("interact",
            {"type": "light", "targetId": self.light_id, "enabled": True},
            {"type": "state", "targetState": "closed"})
        self.generated()
        receipts = Receipt.objects.count()
        with self.assertRaises(services.MapError):
            self.command(user=self.player)
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])
        self.assertEqual(Receipt.objects.count(), receipts)

    def test_repeating_signals_roll_back_every_effect_and_receipt(self):
        bp = self.doc["doors"][0]["blueprint"]
        bp["graphs"] = {
            "interact": graph("interact", {"type": "light", "targetId": self.light_id, "enabled": True},
                              {"type": "state", "targetState": "open"}, {"type": "emitEvent", "scope": "element", "name": "Repeat"}),
            "signal:Repeat": graph("signal:Repeat", {"type": "state", "targetState": "closed"},
                                   {"type": "emitEvent", "scope": "element", "name": "Repeat"}),
        }
        self.generated()
        before = deepcopy(MapBuilderProject.objects.get(pk=self.project_id).generation)
        receipts = Receipt.objects.count()
        with self.assertRaisesMessage(services.MapError, "repeating chain"):
            self.command()
        self.light_object.refresh_from_db()
        self.door_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertFalse(Playback.objects.filter(scene=self.scene).exists())
        self.assertEqual(MapBuilderProject.objects.get(pk=self.project_id).generation, before)
        self.assertEqual(Receipt.objects.count(), receipts)

    def test_native_configuration_state_change_never_starts_an_event(self):
        self.generated()
        result = self.command("open", action="update", version=self.door_object.version)
        self.assertEqual(result.get("blueprint", {}).get("trace", []), [])
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.version, 2)
        self.assertEqual(self.door_object.data["door_state"], "open")
        self.assertFalse(Playback.objects.filter(scene=self.scene).exists())

    def test_public_projection_contains_only_active_image_and_hides_secret_blueprint(self):
        self.generated()
        viewer = self.campaign.memberships.get(user=self.player)
        self.command()
        row = next(w for w in objects.layer_state(self.scene, viewer)["walls"] if w["id"] == str(self.door_object.pk))
        self.assertNotIn("blueprint", row)
        self.assertEqual(row["blueprintAppearance"], {"visible": True, "assetId": str(self.alternate.pk)})
        self.assertEqual(row["asset_id"], str(self.alternate.pk))
        self.assertNotIn(str(self.sound.pk), str(row))
        self.door_object.refresh_from_db()
        self.door_object.data.update(presentation="secret", discovered=False)
        self.door_object.save()
        row = next(w for w in objects.layer_state(self.scene, viewer)["walls"] if w["id"] == str(self.door_object.pk))
        self.assertEqual(row["kind"], "wall")
        for key in ("blueprint", "blueprintAppearance", "asset_id", "thickness"):
            self.assertNotIn(key, row)

    def test_update_preserves_runtime_light_and_accepts_intentional_authored_change(self):
        self.generated()
        self.command()
        self.update_scene()
        self.light_object.refresh_from_db()
        self.assertTrue(self.light_object.data["enabled"])
        self.command("closed")
        self.doc["lights"][0]["enabled"] = True
        self.assertEqual(self.save(expected_version=1).status_code, 200)
        self.update_scene()
        self.light_object.refresh_from_db()
        self.door_object.refresh_from_db()
        self.assertTrue(self.light_object.data["enabled"])
        self.assertEqual(self.door_object.data["door_state"], "closed")

    def test_blueprint_effect_never_adopts_unrelated_manual_light_edits(self):
        self.generated()
        self.light_object.data["color"] = "#113355"
        self.light_object.save()
        self.command()
        with self.assertRaisesMessage(services.MapError, "changed in the VTT"):
            self.update_scene()

    def test_deleted_native_light_removes_action_but_preserves_manual_deletion_conflict(self):
        self.generated()
        services.command(self.campaign.pk, self.gm.pk, "objects",
            {"mapId": str(self.scene.pk), "area": "lights", "action": "delete",
             "data": {"light_id": str(self.light_object.pk)}}, uuid.uuid4())
        self.command()
        self.door_object.refresh_from_db()
        graph_data = self.door_object.data["blueprint"]["graphs"]["interact"]
        self.assertFalse(any(n["type"] == "light" for n in graph_data["nodes"]))
        self.assertEqual({n["id"] for n in graph_data["nodes"] if n["type"] == "sound"}, {"open-sound", "locked-sound"})
        self.assertTrue(Playback.objects.filter(scene=self.scene).exists())
        with self.assertRaisesMessage(services.MapError, "changed in the VTT"):
            self.update_scene()

    def test_deleted_sound_cleans_source_native_and_snapshot_and_keeps_other_actions(self):
        self.generated()
        audio_services.public_command(self.campaign.pk, self.gm.pk, "track-delete",
            {"id": str(self.sound.pk), "version": self.sound.version}, uuid.uuid4())
        self.command()
        self.light_object.refresh_from_db()
        self.assertTrue(self.light_object.data["enabled"])
        self.assertFalse(Playback.objects.filter(scene=self.scene).exists())
        source = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertNotIn(str(self.sound.pk), str(source.document))
        self.assertNotIn(str(self.sound.pk), str(source.generation))
        self.update_scene()

    def test_deleted_sound_cleans_dynamic_baseline_without_adopting_pending_source_edits(self):
        from gravewright.administration.archives import export_campaign, import_campaign

        self.doc["floors"][0]["dynamic"] = True
        self.doc["doors"][0]["blueprint"]["graphs"]["interact"] = graph("interact",
            {"type": "sound", "trackId": str(self.sound.pk), "volume": .35},
            {"type": "soundControl", "trackId": str(self.sound.pk), "action": "stop", "volume": .35},
            {"type": "state", "targetState": "open"})
        self.generated()
        self.doc["floors"][0].update(x=2, width=5)
        response = self.save(expected_version=1)
        self.assertEqual(response.status_code, 200, response.content)

        audio_services.public_command(self.campaign.pk, self.gm.pk, "track-delete",
            {"id": str(self.sound.pk), "version": self.sound.version}, uuid.uuid4())
        source = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual(source.version, 3)
        self.assertEqual(source.document["floors"][0]["x"], 2)
        self.assertEqual(source.generation["dynamicDocument"]["floors"][0]["x"], 1)
        self.assertNotIn(str(self.sound.pk), str(source.document))
        self.assertNotIn(str(self.sound.pk), str(source.generation))
        self.door_object.refresh_from_db()
        live_graph = self.door_object.data["blueprint"]["graphs"]["interact"]
        self.assertEqual([node["type"] for node in live_graph["nodes"]], ["event", "state"])
        self.assertEqual(live_graph["edges"], [
            {"from": "event", "to": "node2", "output": "next", "kind": "execution"}])
        snapshot = next(row for row in source.generation["objects"] if row["id"] == str(self.door_object.pk))
        self.assertEqual(snapshot["data"]["blueprint"], self.door_object.data["blueprint"])

        clone = import_campaign(export_campaign(self.campaign), self.gm, "Dynamic map without deleted sound")
        copied = MapBuilderProject.objects.get(campaign=clone)
        self.assertEqual(copied.document["floors"][0]["x"], 2)
        self.assertEqual(copied.generation["dynamicDocument"]["floors"][0]["x"], 1)
        self.assertFalse(Track.objects.filter(campaign=clone).exists())
        self.command()
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")
        self.assertFalse(Playback.objects.filter(scene=self.scene).exists())
        self.update_scene()
        builder_services.update(clone.pk, self.gm.pk, copied.pk,
            {"request_id": str(uuid.uuid4()), "expected_version": copied.version,
             "expected_scene_version": copied.scene.version})
