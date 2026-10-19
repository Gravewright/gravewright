"""Typed native target sets, trusted event values and live object actions."""

from copy import deepcopy
from datetime import timedelta
import json
from unittest import mock
import uuid

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.audio.models import Playback, Track
from gravewright.campaigns.models import Membership
from gravewright.maps import blueprint_runtime, builder_services, objects
from gravewright.maps.blueprints import clean_blueprint, data_outputs, evaluate_graph
from gravewright.maps.models import AutomationDelay, AutomationRun, Scene, SceneObject
from gravewright.maps.services import MapError

from . import test_builder_blueprints as fixtures
from . import test_blueprint_delays as delays
from . import test_torches as torch_fixtures
from .test_blueprint_references import blueprint, data, execution, node


EVENT = "interact"


def grouped(kind="element", targets=None):
    return node("group", "elementGroup", name="Puzzle group", memberType=kind,
                targetIds=targets or [str(uuid.uuid4()), str(uuid.uuid4())])


def graph_with(*nodes, edges=(), event=EVENT):
    return blueprint({event: (list(nodes), list(edges))})


class CapabilityContractTests(SimpleTestCase):
    def test_groups_are_typed_ordered_bounded_canonical_and_independent(self):
        targets = [str(uuid.uuid4()), str(uuid.uuid4())]
        for kind in ("element", "light", "sound"):
            group = grouped(kind, targets)
            self.assertEqual(data_outputs(group), {"targets": kind + "set"})
            action = node("act", "move", dx=1, dy=0) if kind == "element" else (
                node("act", "light", targetId=targets[0], enabled=True) if kind == "light" else
                node("act", "sound", trackId=targets[0], volume=.5))
            raw = graph_with(group, action, edges=[execution("event", "act"), data("group", "targets", "act", "target")])
            before = deepcopy(raw)
            result = evaluate_graph(raw, EVENT, "closed")
            self.assertEqual(result["actions"][0]["target"], targets)
            result["actions"][0]["target"].reverse()
            self.assertEqual(raw, before)
        group = grouped(targets=[targets[0].upper(), targets[0]])
        with self.assertRaisesMessage(MapError, "element group"):
            clean_blueprint(graph_with(group))
        for changes in ({"targetIds": []}, {"targetIds": targets * 17}, {"targetIds": ["bad"]},
                        {"memberType": "token"}, {"name": " "}, {"name": "a" * 81}, {"name": "A\x00"}):
            with self.subTest(changes=changes), self.assertRaises(MapError):
                clean_blueprint(graph_with({**grouped(), **changes}))

    def test_target_ports_reject_wrong_resource_kind_and_property_rejects_sets(self):
        for source, action in ((grouped("sound"), node("act", "light", targetId=str(uuid.uuid4()), enabled=True)),
                               (grouped("light"), node("act", "state", targetState="open")),
                               (grouped(), node("act", "property", property="state"))):
            raw = graph_with(source, action, edges=[data("group", "targets", "act", "target")])
            with self.assertRaisesMessage(MapError, "connection input"):
                clean_blueprint(raw)

    def test_new_resource_references_allow_missing_ids_but_legacy_fallbacks_remain_strict(self):
        identifier = str(uuid.uuid4())
        for item in (node("ref", "lightReference", targetId=identifier), node("ref", "soundReference", trackId=identifier)):
            clean_blueprint(graph_with(item), light_ids=set(), track_ids=set())
        with self.assertRaises(MapError):
            clean_blueprint(graph_with(node("light", "light", targetId=identifier, enabled=True)), light_ids=set())
        for item in (node("ref", "lightReference", targetId="bad"), node("ref", "soundReference", trackId="bad")):
            with self.assertRaises(MapError):
                clean_blueprint(graph_with(item))

    def test_context_values_have_typed_ports_and_evaluator_owned_event_state(self):
        context = {"userId": "original", "userName": "Owner", "tokenId": "token", "count": 2,
                   "event": "spoof", "state": "locked", "previous": "locked"}
        nodes = [node(prop, "eventContext", property=prop) for prop in ("event", "state", "previous", "userName", "count", "hasToken")]
        self.assertEqual([data_outputs(item)["value"] for item in nodes], ["text", "state", "state", "text", "number", "boolean"])
        raw = graph_with(*nodes, node("eventValue", "setVariable", scope="element", name="Event", valueType="text", value=""),
            edges=[execution("event", "eventValue"), data("event", "value", "eventValue", "value")])
        # Avoid colliding the authored getter with the mandatory event node.
        raw["graphs"][EVENT]["nodes"][1]["id"] = "readEvent"
        raw["graphs"][EVENT]["edges"][1]["from"] = "readEvent"
        before = deepcopy(context)
        result = evaluate_graph(raw, EVENT, "open", "closed", event_context=context)
        self.assertEqual(result["actions"][0]["value"], EVENT)
        self.assertEqual(context, before)

    def test_context_defaults_invalid_metadata_and_unknown_properties(self):
        for property_, value_type, expected in (("userId", "text", ""), ("count", "number", 0), ("hasToken", "boolean", False)):
            raw = graph_with(node("read", "eventContext", property=property_),
                node("store", "setVariable", scope="element", name="Value", valueType=value_type, value=expected),
                edges=[execution("event", "store"), data("read", "value", "store", "value")])
            self.assertEqual(evaluate_graph(raw, EVENT, "closed")["actions"][0]["value"], expected)
            for context in ({"count": True}, {"count": -1}, {"count": 1.5}, {"count": 1_000_001},
                            {"userName": "x" * 257}, {"hasToken": 1}, {"custom": "payload"}):
                with self.subTest(context=context), self.assertRaisesMessage(MapError, "event context"):
                    evaluate_graph(raw, EVENT, "closed", event_context=context)
        with self.assertRaisesMessage(MapError, "event context"):
            clean_blueprint(graph_with(node("read", "eventContext", property="secret")))

    def test_delay_preserves_context_and_validates_cached_target_sets(self):
        raw = graph_with(grouped(), node("wait", "delay", seconds=1), node("move", "move", dx=1, dy=0),
            node("read", "eventContext", property="userName"),
            node("store", "setVariable", scope="element", name="Name", valueType="text", value=""),
            edges=[execution("event", "wait"), execution("wait", "move"), execution("move", "store"),
                   data("group", "targets", "move", "target"), data("read", "value", "store", "value")])
        first = evaluate_graph(raw, EVENT, "closed", event_context={"userName": "Original"})
        final = evaluate_graph(raw, EVENT, "open", event_context={"userName": "Changed"}, continuation=first["delay"]["continuation"])
        self.assertEqual(final["actions"][-1]["value"], "Original")
        checkpoint = deepcopy(first["delay"]["continuation"])
        checkpoint["values"]["group"] = ["bad"]
        with self.assertRaises(MapError):
            evaluate_graph(raw, EVENT, "closed", continuation=checkpoint)

    def test_movement_rotation_and_enable_actions_have_strict_parameters_and_v2_only(self):
        valid = [node("action", "move", dx=-1000, dy=1000), node("action", "rotate", degrees=36000),
                 node("action", "setInteraction", enabled=False), node("action", "setRegion", enabled=True)]
        for item in valid:
            raw = graph_with(item, edges=[execution("event", "action")])
            self.assertEqual(evaluate_graph(raw, EVENT, "closed")["actions"][0], item)
            raw["version"] = 1
            for graph in raw["graphs"].values():
                for edge in graph["edges"]:
                    edge.pop("kind", None)
            with self.assertRaisesMessage(MapError, "node type"):
                clean_blueprint(raw)
        for item in (node("action", "move", dx=1000.1, dy=0), node("action", "rotate", degrees=True),
                     node("action", "setInteraction", enabled=1), node("action", "setRegion", enabled="true")):
            with self.assertRaises(MapError):
                clean_blueprint(graph_with(item))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class CapabilityRuntimeTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    command = fixtures.BuilderBlueprintTests.command
    update_scene = fixtures.BuilderBlueprintTests.update_scene
    due = delays.DelayRuntimeTests.due

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.doc["doors"][0]["blueprint"] = graph_with()

    def configure(self, raw):
        self.door_object.refresh_from_db()
        return self.command("closed", action="update", blueprint=raw, version=self.door_object.version)

    def test_group_state_targets_each_door_once_without_replaying_receipts(self):
        self.generated()
        other = SceneObject.objects.create(scene=self.scene, kind="walls", data=objects.wall({
            "x1": 100, "y1": 100, "x2": 200, "y2": 100, "kind": "door"}))
        raw = graph_with(grouped(targets=[str(self.door_object.pk), str(other.pk)]), node("open", "state", targetState="open"),
            edges=[execution("event", "open"), data("group", "targets", "open", "target")])
        self.configure(raw)
        request_id = uuid.uuid4()
        self.command("closed", request_id=request_id)
        for row in (self.door_object, other):
            row.refresh_from_db()
            self.assertEqual(row.data["door_state"], "open")
        versions = [row.version for row in (self.door_object, other)]
        self.command("closed", request_id=request_id)
        self.assertEqual([SceneObject.objects.get(pk=row.pk).version for row in (self.door_object, other)], versions)

    def test_group_signal_queue_keeps_chain_caps_and_rolls_back_excess_members(self):
        self.generated()
        listener = graph_with(node("open", "state", targetState="open"), event="signal:Open",
                              edges=[execution("event", "open")])
        others = [SceneObject.objects.create(scene=self.scene, kind="walls", data=objects.wall({
            "x1": 100, "y1": 100 + index, "x2": 200, "y2": 100 + index, "kind": "door",
            "blueprint": listener}, campaign_id=self.campaign.pk, scene_id=self.scene.pk)) for index in range(32)]
        def configure(targets):
            raw = graph_with(grouped(targets=targets), node("emit", "emitEvent", scope="element", name="Open"),
                edges=[execution("event", "emit"), data("group", "targets", "emit", "target")])
            raw["graphs"].update(listener["graphs"])
            self.configure(raw)
        configure([str(row.pk) for row in others])
        # Distinct targets make a long chain, not a loop.
        with self.assertRaisesMessage(MapError, "exceeded 32 element operations"):
            self.command("closed")
        self.assertTrue(all(SceneObject.objects.get(pk=row.pk).data["door_state"] == "closed" for row in others))
        configure([str(row.pk) for row in others[:31]])
        self.command("closed", user=self.player)
        self.assertTrue(all(SceneObject.objects.get(pk=row.pk).data["door_state"] == "open" for row in others[:31]))
        self.assertEqual(SceneObject.objects.get(pk=others[-1].pk).data["door_state"], "closed")

    def test_scene_signal_receivers_use_broadcast_budget_but_repetition_still_fails(self):
        self.generated()
        listener = graph_with(node("open", "state", targetState="open"), event="signal:Open",
                              edges=[execution("event", "open")])
        others = [SceneObject.objects.create(scene=self.scene, kind="walls", data=objects.wall({
            "x1": 100, "y1": 100 + index, "x2": 200, "y2": 100 + index, "kind": "door",
            "blueprint": listener}, campaign_id=self.campaign.pk, scene_id=self.scene.pk)) for index in range(48)]
        self.configure(graph_with(node("emit", "emitEvent", scope="scene", name="Open"),
                                  edges=[execution("event", "emit")]))
        with mock.patch.object(blueprint_runtime, "MAX_BROADCAST_DELIVERIES", len(others) - 1):
            with self.assertRaisesMessage(MapError, "more than 256 receiving elements"):
                self.command("closed", user=self.player)
        self.assertTrue(all(SceneObject.objects.get(pk=row.pk).data["door_state"] == "closed" for row in others))
        self.command("closed", user=self.player)
        self.assertTrue(all(SceneObject.objects.get(pk=row.pk).data["door_state"] == "open" for row in others))
        repeating = graph_with(node("close", "state", targetState="closed"),
                               node("emit", "emitEvent", scope="scene", name="Open"), event="signal:Open",
                               edges=[execution("event", "close"), execution("close", "emit")])
        for row in others:
            row.refresh_from_db()
            row.data["blueprint"] = objects.wall({**row.data, "blueprint": repeating}, campaign_id=self.campaign.pk,
                                                 scene_id=self.scene.pk)["blueprint"]
            row.save(update_fields=["data"])
        with self.assertRaisesMessage(MapError, "repeating chain"):
            self.command("closed")
        self.assertTrue(all(SceneObject.objects.get(pk=row.pk).data["door_state"] == "open" for row in others))

    def test_group_transform_failure_rolls_back_earlier_native_writes(self):
        self.generated()
        other = SceneObject.objects.create(scene=self.scene, kind="walls", data=objects.wall({
            "x1": 999999, "y1": 10, "x2": 1000000, "y2": 10, "kind": "door"}))
        self.configure(graph_with(grouped(targets=[str(self.door_object.pk), str(other.pk)]), node("move", "move", dx=1, dy=0),
            edges=[execution("event", "move"), data("group", "targets", "move", "target")]))
        self.door_object.refresh_from_db()
        before = deepcopy(self.door_object.data)
        with self.assertRaisesMessage(MapError, "coordinate"):
            self.command("closed")
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data, before)

    def test_legacy_scene_signal_target_group_still_broadcasts_only_once(self):
        self.generated()
        other = SceneObject.objects.create(scene=self.scene, kind="walls", data=objects.wall({
            "x1": 100, "y1": 100, "x2": 200, "y2": 100, "kind": "door"}))
        raw = graph_with(grouped(targets=[str(self.door_object.pk), str(other.pk)]),
            node("emit", "emitEvent", name="Pulse", scope="scene"),
            edges=[execution("event", "emit"), data("group", "targets", "emit", "target")])
        raw["graphs"].update(graph_with(node("move", "move", dx=1, dy=0), event="signal:Pulse",
            edges=[execution("event", "move")])["graphs"])
        self.configure(raw)
        self.door_object.refresh_from_db()
        before = self.door_object.data["x1"]
        self.command("closed")
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["x1"], before + 64)
        events = AutomationRun.objects.latest("created_at").data["events"]
        self.assertEqual(sum(event["event"] == "signal:Pulse" for event in events), 1)

    def test_missing_connected_targets_do_not_fall_back_to_self_or_light_fallback(self):
        self.generated()
        missing = str(uuid.uuid4())
        raw = graph_with(grouped(targets=[missing]), node("open", "state", targetState="open"),
            node("ref", "lightReference", targetId=missing), node("light", "light", targetId=str(self.light_object.pk), enabled=True),
            edges=[execution("event", "open"), execution("open", "light"), data("group", "targets", "open", "target"),
                   data("ref", "light", "light", "target")])
        self.configure(raw)
        self.command("closed")
        self.door_object.refresh_from_db()
        self.light_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertFalse(self.light_object.data["enabled"])
        steps = AutomationRun.objects.latest("created_at").data["events"][0]["steps"]
        self.assertTrue(next(step for step in steps if step["id"] == "open")["missing"])
        self.assertTrue(next(step for step in steps if step["id"] == "light")["missing"])

    def test_existing_foreign_resource_and_group_members_are_rejected(self):
        self.generated()
        foreign_scene = Scene.objects.create(campaign=self.other, name="Private", width=500, height=500)
        foreign = SceneObject.objects.create(scene=foreign_scene, kind="lights", data=objects.light({"x": 20, "y": 20}))
        for item in (node("ref", "lightReference", targetId=str(foreign.pk)), grouped("light", [str(foreign.pk)])):
            with self.assertRaisesMessage(MapError, "this scene"):
                self.configure(graph_with(item))
        foreign_track = Track.objects.create(campaign=self.other, name="Private sound", duration=1)
        with self.assertRaisesMessage(MapError, "this campaign"):
            self.configure(graph_with(node("ref", "soundReference", trackId=str(foreign_track.pk))))

    def test_live_geometry_is_acknowledged_and_explicit_update_restores_authored_position(self):
        self.doc["doors"][0]["blueprint"] = graph_with(node("move", "move", dx=1, dy=.5),
            node("rotate", "rotate", degrees=90), edges=[execution("event", "move"), execution("move", "rotate")])
        self.generated()
        initial = deepcopy(self.door_object.data)
        self.command("closed")
        self.door_object.refresh_from_db()
        self.assertAlmostEqual((self.door_object.data["x1"] + self.door_object.data["x2"]) / 2,
                               (initial["x1"] + initial["x2"]) / 2 + 64)
        self.assertAlmostEqual(self.door_object.data["x1"], self.door_object.data["x2"])
        identifier = self.door_object.pk
        self.update_scene()
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.pk, identifier)
        self.assertEqual({key: self.door_object.data[key] for key in ("x1", "y1", "x2", "y2")},
                         {key: initial[key] for key in ("x1", "y1", "x2", "y2")})

    def test_rotation_pivots_on_the_door_anchor(self):
        self.doc["doors"][0]["rotationAnchor"] = "start"
        self.doc["doors"][0]["blueprint"] = graph_with(node("rotate", "rotate", degrees=90),
                                                       edges=[execution("event", "rotate")])
        self.generated()
        initial = deepcopy(self.door_object.data)
        self.command("closed")
        self.door_object.refresh_from_db()
        data = self.door_object.data
        self.assertEqual((data["x1"], data["y1"]), (initial["x1"], initial["y1"]))
        self.assertAlmostEqual(data["x2"], initial["x1"] - (initial["y2"] - initial["y1"]))
        self.assertAlmostEqual(data["y2"], initial["y1"] + (initial["x2"] - initial["x1"]))

    def test_prior_manual_geometry_conflict_is_not_adopted_by_automation(self):
        self.doc["doors"][0]["blueprint"] = graph_with(node("move", "move", dx=1, dy=0), edges=[execution("event", "move")])
        self.generated()
        self.door_object.data["x1"] += 5
        self.door_object.save(update_fields=["data"])
        self.command("closed")
        with self.assertRaisesMessage(MapError, "changed"):
            self.update_scene()

    def test_generic_live_image_moves_and_cannot_receive_a_door_state(self):
        self.generated()
        from gravewright.maps.extra_objects import image
        picture = SceneObject.objects.create(scene=self.scene, kind="images", data=image(self.scene, {
            "asset_id": str(self.alternate.pk), "x": 120, "y": 140}))
        self.configure(graph_with(node("ref", "reference", targetId=str(picture.pk)),
            node("move", "move", dx=1, dy=0), node("rotate", "rotate", degrees=30), node("open", "state", targetState="open"),
            edges=[execution("event", "move"), execution("move", "rotate"), execution("rotate", "open"),
                   *[data("ref", "door", target, "target") for target in ("move", "rotate", "open")]]))
        self.command("closed")
        picture.refresh_from_db()
        self.assertEqual((picture.data["x"], picture.data["y"], picture.data["rotation"]), (184, 140, 30))
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")

    def test_typed_light_and_sound_groups_apply_each_resource_in_order(self):
        self.generated()
        light = SceneObject.objects.create(scene=self.scene, kind="lights", data=objects.light({"x": 10, "y": 20, "enabled": False}))
        sound = Track.objects.create(campaign=self.campaign, name="Second", duration=1)
        self.configure(graph_with(grouped("light", [str(self.light_object.pk), str(light.pk)]),
            node("sounds", "elementGroup", name="Sounds", memberType="sound", targetIds=[str(self.sound.pk), str(sound.pk)]),
            node("light", "light", targetId=str(self.light_object.pk), enabled=True),
            node("play", "sound", trackId=str(self.sound.pk), volume=.7),
            node("volume", "soundControl", trackId=str(self.sound.pk), action="volume", volume=.2),
            edges=[execution("event", "light"), execution("light", "play"), execution("play", "volume"),
                   data("group", "targets", "light", "target"), data("sounds", "targets", "play", "target"),
                   data("sounds", "targets", "volume", "target")]))
        self.command("closed")
        self.assertTrue(all(SceneObject.objects.get(pk=row.pk).data["enabled"] for row in (light, self.light_object)))
        voices = Playback.objects.get(scene=self.scene).data["ambient"]
        self.assertEqual([voice["trackId"] for voice in voices], [str(self.sound.pk), str(sound.pk)])
        self.assertTrue(all(voice["volume"] == .2 for voice in voices))

    def test_player_interaction_gate_allows_gm_and_saved_automation(self):
        self.doc["doors"][0]["blueprint"] = graph_with(node("disable", "setInteraction", enabled=False),
            node("wait", "delay", seconds=.1), node("open", "state", targetState="open"),
            edges=[execution("event", "disable"), execution("disable", "wait"), execution("wait", "open")])
        self.generated()
        self.command("closed", user=self.player)
        job = AutomationDelay.objects.get(status="pending")
        with self.assertRaisesMessage(MapError, "interaction is disabled"):
            self.command("closed", user=self.player)
        self.assertEqual(self.due(job)["completed"], 1)
        self.command("open")
        self.update_scene()
        self.door_object.refresh_from_db()
        self.assertFalse(self.door_object.data["interactionEnabled"])
        self.command("open", action="update", version=self.door_object.version, interactionEnabled=True)
        self.door_object.refresh_from_db()
        self.assertTrue(self.door_object.data["interactionEnabled"])

    def test_deleted_pure_light_binding_remains_inert_without_retargeting_fallback(self):
        self.generated()
        target = SceneObject.objects.create(scene=self.scene, kind="lights", data=objects.light({"x": 30, "y": 30}))
        self.configure(graph_with(node("ref", "lightReference", targetId=str(target.pk)),
            node("enable", "light", targetId=str(self.light_object.pk), enabled=True),
            edges=[execution("event", "enable"), data("ref", "light", "enable", "target")]))
        from gravewright.maps import services
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk), "area": "lights",
            "action": "delete", "data": {"light_id": str(target.pk)}}, uuid.uuid4())
        self.door_object.refresh_from_db()
        graph = self.door_object.data["blueprint"]["graphs"][EVENT]
        self.assertTrue(any(item["type"] == "lightReference" for item in graph["nodes"]))
        self.assertIn(data("ref", "light", "enable", "target"), graph["edges"])
        self.command("closed")
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])

    def test_event_identity_is_server_owned_and_frozen_across_delay(self):
        raw = graph_with(node("wait", "delay", seconds=.1), node("user", "eventContext", property="userId"),
            node("name", "eventContext", property="userName"),
            node("store", "setVariable", scope="element", name="User", valueType="text", value=""),
            node("storeName", "setVariable", scope="element", name="Name", valueType="text", value=""),
            edges=[execution("event", "wait"), execution("wait", "store"), execution("store", "storeName"),
                   data("user", "value", "store", "value"), data("name", "value", "storeName", "value")])
        self.doc["doors"][0]["blueprint"] = raw
        self.generated()
        original_name = self.player.name
        self.command("closed", user=self.player, context={"userId": str(self.gm.pk), "userName": "Spoof"})
        job = AutomationDelay.objects.get(status="pending")
        self.player.name = "Renamed"
        self.player.save(update_fields=["name"])
        self.assertEqual(self.due(job)["completed"], 1)
        self.door_object.refresh_from_db()
        values = self.door_object.data["automationVariables"]
        self.assertEqual(values["User"]["value"], str(self.player.pk))
        self.assertEqual(values["Name"]["value"], original_name)

    def test_timer_context_keeps_trigger_identity_but_uses_current_graph_and_state(self):
        raw = graph_with(node("timer", "timer", name="Inspect", action="start", seconds=.1),
                         edges=[execution("event", "timer")])
        raw["graphs"].update(graph_with(node("eventValue", "eventContext", property="event"),
            node("stateValue", "eventContext", property="state"), node("isOpen", "compare", state="open"),
            node("name", "eventContext", property="userName"),
            node("storeEvent", "setVariable", scope="element", name="Event", valueType="text", value=""),
            node("storeState", "setVariable", scope="element", name="WasOpen", valueType="boolean", value=False),
            node("storeName", "setVariable", scope="element", name="Name", valueType="text", value=""),
            event="signal:Inspect", edges=[execution("event", "storeEvent"), execution("storeEvent", "storeState"),
                execution("storeState", "storeName"), data("eventValue", "value", "storeEvent", "value"),
                data("stateValue", "value", "isOpen", "value"), data("isOpen", "result", "storeState", "value"),
                data("name", "value", "storeName", "value")])["graphs"])
        self.doc["doors"][0]["blueprint"] = raw
        self.generated()
        original_name = self.player.name
        self.command("closed", user=self.player)
        job = AutomationDelay.objects.get(status="pending")
        self.player.name = "Changed"
        self.player.save(update_fields=["name"])
        self.door_object.refresh_from_db()
        self.door_object.data["door_state"] = "open"
        self.door_object.save(update_fields=["data"])
        self.assertEqual(self.due(job)["completed"], 1)
        self.door_object.refresh_from_db()
        values = self.door_object.data["automationVariables"]
        self.assertEqual(values["Event"]["value"], "signal:Inspect")
        self.assertTrue(values["WasOpen"]["value"])
        self.assertEqual(values["Name"]["value"], original_name)

    def test_source_groups_bind_native_ids_and_archive_preserves_authored_names(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        from gravewright.maps.models import MapBuilderProject
        name = "Group " + str(self.alternate.pk)
        raw = graph_with({**grouped(targets=[self.doc["doors"][0]["id"]]), "name": name},
            node("lights", "elementGroup", name="Lights", memberType="light", targetIds=[self.light_id]),
            node("lightRef", "lightReference", targetId=self.light_id))
        self.doc["doors"][0]["blueprint"] = raw
        self.generated()
        nodes = self.door_object.data["blueprint"]["graphs"][EVENT]["nodes"]
        self.assertEqual(nodes[1]["targetIds"], [str(self.door_object.pk)])
        self.assertEqual(nodes[2]["targetIds"], [str(self.light_object.pk)])
        self.assertEqual(nodes[3]["targetId"], str(self.light_object.pk))
        restored = import_campaign(export_campaign(self.campaign), self.gm, "Imported capabilities")
        source = MapBuilderProject.objects.get(campaign=restored)
        imported_door = source.scene.elements.get(kind="walls", data__kind="door")
        imported_light = source.scene.elements.get(kind="lights")
        nodes = imported_door.data["blueprint"]["graphs"][EVENT]["nodes"]
        self.assertEqual(nodes[1]["name"], name)
        self.assertEqual(nodes[1]["targetIds"], [str(imported_door.pk)])
        self.assertEqual(nodes[2]["targetIds"], [str(imported_light.pk)])
        self.update_scene()
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["blueprint"]["graphs"][EVENT]["nodes"][1]["targetIds"], [str(self.door_object.pk)])

    def test_missing_required_group_member_cancels_a_wait(self):
        self.generated()
        target = SceneObject.objects.create(scene=self.scene, kind="walls", data=objects.wall({
            "x1": 10, "y1": 10, "x2": 50, "y2": 10, "kind": "door"}))
        self.configure(graph_with(grouped(targets=[str(target.pk)]), node("wait", "delay", seconds=.1),
            node("open", "state", targetState="open"), edges=[execution("event", "wait"), execution("wait", "open"),
            data("group", "targets", "open", "target")]))
        self.command("closed")
        job = AutomationDelay.objects.get(status="pending")
        target.delete()
        self.assertEqual(self.due(job)["cancelled"], 1)

    def test_public_layers_do_not_include_context_or_group_definitions(self):
        self.doc["doors"][0]["blueprint"] = graph_with(node("read", "eventContext", property="userName"), grouped())
        self.generated()
        for user in (self.player, self.streamer):
            projected = json.dumps(objects.layer_state(self.scene, Membership.objects.get(campaign=self.campaign, user=user)))
            self.assertNotIn("Puzzle group", projected)
            self.assertNotIn("eventContext", projected)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class TorchTransformTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    torch = torch_fixtures.TorchTests.torch
    children = torch_fixtures.TorchTests.children
    command = torch_fixtures.TorchTests.command

    def setUp(self):
        torch_fixtures.TorchTests.setUp(self)

    def test_move_rotate_uses_native_torch_components_once(self):
        raw = graph_with(node("move", "move", dx=1, dy=0), node("rotate", "rotate", degrees=30),
            node("stay", "state", targetState="off"), event="interact",
            edges=[execution("event", "move"), execution("move", "rotate"), execution("rotate", "stay")])
        raw["kind"], raw["states"] = "torch", {"off": {"appearance": "inherit"}, "on": {"appearance": "inherit"}}
        self.doc["decorations"][0]["blueprint"] = raw
        self.generated()
        before, children = self.torch(), self.children()
        self.command()
        after, moved = self.torch(), self.children()
        self.assertEqual(after.data["x"], before.data["x"] + 64)
        self.assertEqual(after.data["rotation"], 30)
        import math
        for kind, original in children.items():
            dx, dy = original.data["x"] - before.data["x"], original.data["y"] - before.data["y"]
            self.assertAlmostEqual(moved[kind].data["x"], after.data["x"] + dx * math.cos(math.pi / 6) - dy * math.sin(math.pi / 6))
            self.assertAlmostEqual(moved[kind].data["y"], after.data["y"] + dx * math.sin(math.pi / 6) + dy * math.cos(math.pi / 6))
