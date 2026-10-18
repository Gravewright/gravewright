"""Only base triggers start graphs; conditions and actions belong to their nodes."""

from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import uuid

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.maps import blueprint_network, blueprint_testing, objects
from gravewright.maps.blueprints import clean_blueprint, default_blueprint, evaluate_graph
from gravewright.maps.blueprint_memory import clean_memory
from gravewright.maps.blueprint_delays import cancel_invalid_delays, process_due_delays, semantic_hash
from gravewright.maps.models import AutomationDelay, AutomationRun, MapAsset, MapBuilderProject, Receipt
from gravewright.maps import services
from gravewright.maps.services import MapError

from . import test_levers as fixtures
from . import test_builder_blueprints as door_fixtures
from . import test_torches as torch_fixtures
from . import test_regions as region_fixtures
from .test_blueprint_events import EventFixture, definition, graph
from .test_levers import data, execution, node


class BaseEventValidationTests(SimpleTestCase):
    def test_known_retired_graphs_are_removed_without_mutating_unrelated_data(self):
        raw = default_blueprint()
        raw.update(version=1)
        raw["graphs"] = {"change": {"retired": True}, "enter:closed": {"retired": True},
                         "exit:open": {"retired": True}, "interact:locked": {"retired": True}}
        before = deepcopy(raw)
        normalized = clean_blueprint(raw)
        self.assertEqual(normalized["version"], 2)
        self.assertEqual(normalized["graphs"], {})
        self.assertEqual(normalized["states"], raw["states"])
        self.assertEqual(raw, before)
        for event in raw["graphs"]:
            with self.subTest(event=event), self.assertRaises(MapError):
                evaluate_graph(normalized, event, "closed")

    def test_unknown_events_and_malformed_base_graphs_remain_errors(self):
        for event in ("enter:unknown", "change:other", "onInteract", "onCreate"):
            with self.subTest(event=event), self.assertRaises(MapError):
                clean_blueprint(definition(**{event: graph(event)}))
        with self.assertRaises(MapError):
            clean_blueprint(definition(interact=[]))

    def test_memory_drops_retired_event_rows_but_keeps_base_progress(self):
        entry = {"gate": {"type": "once", "value": True}}
        self.assertEqual(clean_memory({"change": entry, "enter:on": entry, "interact": entry}), {"interact": entry})
        with self.assertRaises(MapError):
            clean_memory({"onChange": entry})

    def test_wait_fingerprint_ignores_removed_graph_bodies_without_ignoring_invalid_base_graphs(self):
        current = definition(interact=graph("interact", node("wait", "delay", seconds=1)))
        historical = deepcopy(current)
        historical["graphs"]["change"] = None
        self.assertEqual(semantic_hash(historical), semantic_hash(current))
        self.assertIsNone(historical["graphs"]["change"])
        current["graphs"]["interact"] = None
        with self.assertRaises(MapError):
            semantic_hash(current)

    def test_template_discards_bindings_and_parameters_owned_only_by_removed_graphs(self):
        from gravewright.maps import blueprint_templates
        from .test_blueprint_templates import fixture
        old = fixture()
        old["blueprint"]["graphs"]["interact:closed"] = old["blueprint"]["graphs"].pop("interact")
        old["blueprint"]["graphs"]["interact:closed"]["nodes"][0]["event"] = "interact:closed"
        for parameter in old["parameters"]:
            parameter["path"][1] = "interact:closed"
        clean = blueprint_templates.clean_definition(old)
        self.assertEqual(clean["blueprint"]["graphs"], {})
        self.assertEqual((clean["bindings"], clean["parameters"]), ([], []))

    def test_template_loader_discards_a_malformed_retired_body_but_still_validates_base_events(self):
        from gravewright.maps import blueprint_templates
        raw = {"version": 1, "blueprint": definition(interact=graph("interact"), change=None),
               "bindings": [], "parameters": []}
        result = blueprint_templates.clean_definition(raw)
        self.assertEqual(set(result["blueprint"]["graphs"]), {"interact"})
        self.assertIsNone(raw["blueprint"]["graphs"]["change"])
        raw["blueprint"]["graphs"]["interact"] = None
        with self.assertRaises(MapError):
            blueprint_templates.clean_definition(raw)

    def test_retired_variable_declarations_cannot_conflict_with_current_scene_types(self):
        from gravewright.maps.blueprint_variables import validate_definitions
        current = definition(interact=graph("interact", node("score", "setVariable", scope="scene",
                                                   name="Score", valueType="number", value=1)), change=None)
        validate_definitions([current])
        historical = definition(change=graph("change", node("score", "setVariable", scope="scene",
                                                   name="Score", valueType="text", value="retired")))
        validate_definitions([current, historical])
        historical["graphs"]["interact"] = historical["graphs"].pop("change")
        with self.assertRaisesMessage(MapError, "same type"):
            validate_definitions([current, historical])

    def test_template_prunes_retired_typed_bindings_around_malformed_nodes(self):
        from gravewright.maps import blueprint_templates
        historical = definition(interact=graph("interact"), change={"nodes": [None,
            node("old", "sprite", appearance="asset", assetId={"binding": "OldImage"}), None], "edges": []})
        raw = {"version": 1, "blueprint": historical,
               "bindings": [{"id": "OldImage", "type": "asset", "label": "Old image"}], "parameters": []}
        result = blueprint_templates.clean_definition(raw)
        self.assertEqual(set(result["blueprint"]["graphs"]), {"interact"})
        self.assertEqual(result["bindings"], [])
        raw["bindings"].append({"id": "Unrelated", "type": "asset", "label": "Unrelated unused binding"})
        with self.assertRaisesMessage(MapError, "Unused"):
            blueprint_templates.clean_definition(raw)

    def test_resource_cleanup_discards_retired_bodies_before_detaching_active_actions(self):
        from gravewright.maps.blueprint_runtime import detach_blueprint_art, detach_blueprint_light, detach_blueprint_sound
        asset_id, light_id, track_id = [str(uuid.uuid4()) for _ in range(3)]
        raw = definition(interact=graph("interact", node("art", "setAppearance", assetId=asset_id),
            node("lamp", "light", targetId=light_id, enabled=True), node("bell", "sound", trackId=track_id, volume=.5)), change=None)
        for cleanup, resource, removed_id in ((detach_blueprint_art, asset_id, "art"),
                (detach_blueprint_light, light_id, "lamp"), (detach_blueprint_sound, track_id, "bell")):
            with self.subTest(resource=removed_id):
                candidate = deepcopy(raw)
                self.assertTrue(cleanup(candidate, resource))
                self.assertEqual(set(candidate["graphs"]), {"interact"})
                self.assertNotIn(removed_id, [item["id"] for item in candidate["graphs"]["interact"]["nodes"]])
                clean_blueprint(candidate)
                candidate["graphs"]["interact"] = None
                with self.assertRaises(MapError):
                    cleanup(candidate, resource)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class BaseEventRuntimeTests(EventFixture, TestCase):
    lever = fixtures.LeverTests.lever
    interact = fixtures.LeverTests.interact

    def setUp(self):
        fixtures.LeverTests.setUp(self)
        self.doc["decorations"][0]["blueprint"] = definition("lever")

    def test_empty_blueprint_event_never_falls_back_to_native_toggle(self):
        self.generated()
        self.interact(user=self.player)
        self.assertEqual(self.lever().data["lever"]["state"], "off")
        owner = self.lever()
        owner.data["lever"]["state"] = "on"
        owner.save(update_fields=["data"])
        self.interact(user=self.player)
        self.assertEqual(self.lever().data["lever"]["state"], "on")

    def test_native_mechanism_without_a_blueprint_keeps_its_native_operation(self):
        self.generated()
        owner = self.lever()
        owner.data.pop("blueprint")
        owner.save(update_fields=["data"])
        self.interact(user=self.player)
        self.assertEqual(self.lever().data["lever"]["state"], "on")

    def test_paused_blueprint_ignores_event_without_toggling_or_running_effects(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever", interact=graph("interact", node("on", "state", targetState="on")))
        self.generated()
        self.scene.settings["automationPaused"] = True
        self.scene.save(update_fields=["settings"])
        self.interact(user=self.player)
        self.assertEqual(self.lever().data["lever"]["state"], "off")
        self.assertEqual(AutomationRun.objects.get(scene=self.scene).outcome, "paused")

    def test_state_sprite_state_sprite_actions_keep_their_authored_order(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever", interact=graph("interact",
            node("on", "state", targetState="on"), node("first", "sprite", appearance="hidden"),
            node("off", "state", targetState="off"), node("last", "sprite", appearance="asset", assetId=str(self.handle_on.pk))))
        self.generated()
        self.interact()
        owner = self.lever()
        self.assertEqual(owner.data["lever"]["state"], "off")
        self.assertEqual(owner.data["asset_id"], str(self.handle_on.pk))
        self.assertEqual(owner.data["layer"], "map")

    def test_state_sprite_state_preserves_the_explicit_sprite_without_an_implicit_reset(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever", interact=graph("interact",
            node("on", "state", targetState="on"), node("art", "sprite", appearance="asset", assetId=str(self.handle_on.pk)),
            node("off", "state", targetState="off")))
        self.generated()
        self.interact()
        owner = self.lever()
        self.assertEqual((owner.data["lever"]["state"], owner.data["asset_id"]), ("off", str(self.handle_on.pk)))

    def test_conditions_after_actions_still_observe_the_event_start_snapshot(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever", interact={
            "nodes": [node("event", "event", event="interact"), node("on", "state", targetState="on"),
                      node("check", "condition", state="off"), node("art", "sprite", appearance="asset", assetId=str(self.handle_on.pk)),
                      node("hide", "sprite", appearance="hidden")],
            "edges": [execution("event", "on"), execution("on", "check"),
                      execution("check", "art", "true"), execution("check", "hide", "false")]})
        self.generated()
        self.interact()
        owner = self.lever()
        self.assertEqual((owner.data["lever"]["state"], owner.data["asset_id"], owner.data["layer"]),
                         ("on", str(self.handle_on.pk), "map"))
        steps = AutomationRun.objects.get(scene=self.scene).data["events"][0]["steps"]
        self.assertTrue(next(step for step in steps if step["id"] == "check")["result"])

    def test_named_signal_starts_a_fresh_snapshot_after_ordered_actions(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever",
            interact=graph("interact", node("on", "state", targetState="on"), node("send", "emitEvent", scope="element", name="Ready")),
            **{"signal:Ready": {"nodes": [node("event", "event", event="signal:Ready"), node("check", "condition", state="on"),
                node("art", "sprite", appearance="asset", assetId=str(self.handle_on.pk))],
                "edges": [execution("event", "check"), execution("check", "art", "true")]}})
        self.generated()
        self.interact()
        self.assertEqual(self.lever().data["asset_id"], str(self.handle_on.pk))
        self.assertEqual([item["event"] for item in self.events()], ["interact", "signal:Ready"])

    def test_repeating_signals_roll_back_prior_state_visual_effects_and_receipt(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever",
            interact=graph("interact", node("on", "state", targetState="on"),
                node("art", "sprite", appearance="asset", assetId=str(self.handle_on.pk)),
                node("send", "emitEvent", scope="element", name="Loop")),
            **{"signal:Loop": graph("signal:Loop", node("send", "emitEvent", scope="element", name="Loop"))})
        self.generated()
        before = deepcopy(self.lever().data)
        request_id = uuid.uuid4()
        with self.assertRaisesMessage(MapError, "repeating chain"):
            self.interact(request_id=request_id)
        self.assertEqual(self.lever().data, before)
        self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())

    def test_explicit_visibility_and_appearance_actions_follow_state_without_reset(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever", interact=graph("interact",
            node("on", "state", targetState="on"), node("hide", "setVisibility", visible=False),
            node("show", "setVisibility", visible=True), node("art", "setAppearance", assetId=str(self.handle_on.pk))))
        self.generated()
        self.interact()
        owner = self.lever()
        self.assertEqual((owner.data["lever"]["state"], owner.data["asset_id"], owner.data["layer"]),
                         ("on", str(self.handle_on.pk), "map"))

    def test_explicit_visibility_survives_a_following_state_action(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever", interact=graph("interact",
            node("on", "state", targetState="on"), node("hide", "setVisibility", visible=False),
            node("off", "state", targetState="off")))
        self.generated()
        self.interact()
        self.assertEqual((self.lever().data["lever"]["state"], self.lever().data["layer"]), ("off", "gm-image-layer"))

    def test_retired_hooks_cannot_override_an_interaction_and_are_absent_from_projection(self):
        raw = definition("lever", interact=graph("interact", node("on", "state", targetState="on"),
                         node("art", "sprite", appearance="asset", assetId=str(self.handle_on.pk))),
                         change=graph("change", node("hide", "sprite", appearance="hidden")))
        self.doc["decorations"][0]["blueprint"] = raw
        self.generated()
        self.interact()
        owner = self.lever()
        self.assertEqual((owner.data["lever"]["state"], owner.data["layer"]), ("on", "map"))
        projected = next(item for item in blueprint_network.state(self.campaign.pk, self.gm.pk, self.scene.pk)["elements"] if item["id"] == str(owner.pk))
        self.assertEqual(set(projected["blueprint"]["graphs"]), {"interact"})

    def test_native_projection_drops_retired_memory_and_keeps_active_progress_without_writing(self):
        self.generated()
        owner = self.lever()
        owner.data["blueprint"] = definition("lever", interact=graph("interact", node("gate", "counter", target=3)),
                                               change=graph("change", node("old", "once")))
        owner.data["automationMemory"] = {"interact": {"gate": {"type": "counter", "value": 2}},
                                          "change": {"old": {"type": "once", "value": True}}}
        owner.save(update_fields=["data"])
        before, version = deepcopy(owner.data), owner.version
        projected = objects.entry(owner)
        self.assertEqual(projected["automationMemory"], {"interact": {"gate": {"type": "counter", "value": 2}}})
        self.assertEqual(set(projected["blueprint"]["graphs"]), {"interact"})
        owner.refresh_from_db()
        self.assertEqual((owner.data, owner.version), (before, version))

    def test_removed_delay_event_is_cancelled_without_executing_its_continuation(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever", interact=graph("interact",
            node("wait", "delay", seconds=1), node("on", "state", targetState="on")))
        self.generated()
        self.interact()
        job = AutomationDelay.objects.get(scene=self.scene)
        job.event = "change"
        job.save(update_fields=["event"])
        self.assertEqual(process_due_delays(now=job.due_at + timedelta(seconds=1))["cancelled"], 1)
        self.assertEqual(self.lever().data["lever"]["state"], "off")
        job.refresh_from_db()
        self.assertEqual(job.message, "The delayed blueprint event was removed.")

    def test_delay_on_historical_owner_ignores_malformed_retired_graph_without_rebasing_source(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever", interact=graph("interact",
            node("wait", "delay", seconds=1), node("on", "state", targetState="on")))
        self.generated()
        owner = self.lever()
        owner.data["blueprint"]["graphs"]["change"] = None
        owner.save(update_fields=["data"])
        self.interact()
        job = AutomationDelay.objects.get(scene=self.scene)
        digest = job.graph_hash
        cancel_invalid_delays(self.scene)
        job.refresh_from_db()
        self.assertEqual((job.status, job.graph_hash), ("pending", digest))
        self.assertEqual(process_due_delays(now=job.due_at + timedelta(seconds=1))["completed"], 1)
        owner = self.lever()
        self.assertEqual(owner.data["lever"]["state"], "on")
        self.assertIsNone(owner.data["blueprint"]["graphs"]["change"])

    def test_retired_resource_references_do_not_cancel_a_current_base_event_wait(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever", interact=graph("interact",
            node("wait", "delay", seconds=1), node("on", "state", targetState="on")))
        self.generated()
        owner = self.lever()
        owner.data["blueprint"]["graphs"]["enter:off"] = graph("enter:off",
            node("missing", "light", targetId=str(uuid.uuid4()), enabled=True))
        owner.save(update_fields=["data"])
        self.interact()
        job = AutomationDelay.objects.get(scene=self.scene)
        cancel_invalid_delays(self.scene)
        job.refresh_from_db()
        self.assertEqual(job.status, "pending")
        self.assertEqual(process_due_delays(now=job.due_at + timedelta(seconds=1))["completed"], 1)
        self.assertEqual(self.lever().data["lever"]["state"], "on")

    def test_timer_on_historical_owner_hashes_only_normalized_graphs(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever",
            interact=graph("interact", node("timer", "timer", name="Ready", action="start", seconds=1)),
            **{"signal:Ready": graph("signal:Ready", node("on", "state", targetState="on"))})
        self.generated()
        owner = self.lever()
        owner.data["blueprint"]["graphs"]["change"] = None
        owner.save(update_fields=["data"])
        self.interact()
        job = AutomationDelay.objects.get(scene=self.scene, kind="timer")
        self.assertEqual(process_due_delays(now=job.due_at + timedelta(seconds=1))["completed"], 1)
        self.assertEqual(self.lever().data["lever"]["state"], "on")

    def test_historical_raw_fingerprint_is_cancelled_instead_of_silently_rebased(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever", interact=graph("interact",
            node("wait", "delay", seconds=1), node("on", "state", targetState="on")))
        self.generated()
        self.interact()
        job, owner = AutomationDelay.objects.get(scene=self.scene), self.lever()
        raw = deepcopy(owner.data["blueprint"])
        raw["graphs"]["change"] = graph("change")
        owner.data["blueprint"] = deepcopy(raw)
        owner.save(update_fields=["data"])
        for value in raw["graphs"].values():
            for item in value["nodes"]:
                item.pop("x", None)
                item.pop("y", None)
        historical_digest = hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":"),
                                           ensure_ascii=True).encode("ascii")).hexdigest()
        job.graph_hash = historical_digest
        job.save(update_fields=["graph_hash"])
        self.assertEqual(process_due_delays(now=job.due_at + timedelta(seconds=1))["cancelled"], 1)
        job.refresh_from_db()
        self.assertEqual((job.graph_hash, job.message), (historical_digest, "The delayed blueprint changed."))
        self.assertEqual(self.lever().data["lever"]["state"], "off")

    def test_asset_deletion_normalizes_historical_native_source_and_owned_snapshots_without_events(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever", interact=graph("interact",
            node("art", "setAppearance", assetId=str(self.handle_on.pk))))
        self.generated()
        owner = self.lever()
        owner.data["blueprint"]["graphs"]["change"] = None
        owner.save(update_fields=["data"])
        project = MapBuilderProject.objects.get(pk=self.project_id)
        project.document["decorations"][0]["blueprint"]["graphs"]["change"] = None
        record = next(row for row in project.generation["objects"] if row["id"] == str(owner.pk))
        record["data"]["blueprint"]["graphs"]["change"] = None
        project.save(update_fields=["document", "generation"])
        response = self.post(f"/api/containers/{self.campaign.pk}/library/assets/delete", {"asset_id": str(self.handle_on.pk)})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(MapAsset.objects.filter(pk=self.handle_on.pk).exists())
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        owner = self.lever()
        project.refresh_from_db()
        record = next(row for row in project.generation["objects"] if row["id"] == str(owner.pk))
        for blueprint in (owner.data["blueprint"], project.document["decorations"][0]["blueprint"], record["data"]["blueprint"]):
            self.assertEqual(set(blueprint["graphs"]), {"interact"})
            self.assertEqual([item["type"] for item in blueprint["graphs"]["interact"]["nodes"]], ["event"])

    def test_rehearsal_predicts_ordered_state_and_sprite_without_saving(self):
        self.doc["decorations"][0]["blueprint"] = definition("lever", interact=graph("interact",
            node("on", "state", targetState="on"), node("art", "sprite", appearance="asset", assetId=str(self.handle_on.pk))))
        self.generated()
        owner = self.lever()
        before = deepcopy(owner.data)
        result = blueprint_testing.run(self.campaign.pk, self.gm.pk, self.scene.pk, owner.pk,
            {"request_id": str(uuid.uuid4()), "event": "interact", "expected_version": owner.version})
        self.assertTrue(result["ok"], result)
        predicted = next(row["after"]["data"] for row in result["changes"]["elements"] if row["id"] == str(owner.pk))
        self.assertEqual((predicted["lever"]["state"], predicted["asset_id"]), ("on", str(self.handle_on.pk)))
        self.assertEqual(self.lever().data, before)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class BaseEventDoorAuthorityTests(EventFixture, TestCase):
    def setUp(self):
        door_fixtures.BuilderBlueprintTests.setUp(self)

    def test_player_lock_change_requires_authored_permission_and_rolls_back_prior_effects(self):
        raw = definition(interact=graph("interact", node("lamp", "light", targetId=self.light_id, enabled=True),
                                      node("lock", "state", targetState="locked")))
        self.doc["doors"][0]["blueprint"] = raw
        self.generated()
        request_id = uuid.uuid4()
        with self.assertRaisesMessage(MapError, "cannot be operated"):
            self.command(user=self.player, request_id=request_id)
        self.door_object.refresh_from_db()
        self.light_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertFalse(self.light_object.data["enabled"])
        self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())
        owner = self.door_object
        owner.data["blueprint"]["graphs"]["interact"]["nodes"][-1]["players"] = True
        owner.save(update_fields=["data"])
        self.command(user=self.player)
        owner.refresh_from_db()
        self.assertEqual(owner.data["door_state"], "locked")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class BaseEventTorchTargetTests(EventFixture, TestCase):
    torch = torch_fixtures.TorchTests.torch
    children = torch_fixtures.TorchTests.children

    def setUp(self):
        torch_fixtures.TorchTests.setUp(self)
        self.doc["decorations"][0]["blueprint"] = definition("torch")

    def target_graph(self, *, appearance=False):
        nodes = [node("event", "event", event="interact"), node("torch", "reference", targetId=self.torch_id),
                 node("turn", "state", targetState="on")]
        edges = [execution("event", "turn"), data("torch", "door", "turn", "target")]
        if appearance:
            nodes.append(node("art", "setAppearance", assetId=str(self.alternate.pk)))
            edges.extend([execution("turn", "art"), data("torch", "door", "art", "target")])
        self.doc["doors"][0]["blueprint"] = definition(interact={"nodes": nodes, "edges": edges})

    def test_state_action_targeting_another_torch_updates_its_pose_and_native_components(self):
        self.target_graph()
        self.generated()
        self.command(user=self.player)
        owner, children = self.torch(), self.children()
        self.assertEqual((owner.data["torch"]["state"], owner.data["rotation"]), ("on", 90))
        self.assertAlmostEqual(children["lights"].data["x"], 384)
        self.assertAlmostEqual(children["lights"].data["y"], 352)
        self.assertTrue(children["lights"].data["enabled"])
        self.assertEqual(self.events()[0]["event"], "interact")

    def test_explicit_appearance_on_other_torch_survives_its_pose_commit(self):
        self.target_graph(appearance=True)
        self.generated()
        self.command()
        owner = self.torch()
        self.assertEqual((owner.data["torch"]["state"], owner.data["asset_id"], owner.data["rotation"]),
                         ("on", str(self.alternate.pk), 90))
        self.assertAlmostEqual(self.children()["lights"].data["y"], 352)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class BaseEventPresenceTests(EventFixture, TestCase):
    region = region_fixtures.RegionTests.region
    place = region_fixtures.RegionTests.place
    move = region_fixtures.RegionTests.move
    token_command = region_fixtures.RegionTests.token_command
    door_state = region_fixtures.RegionTests.door_state

    def setUp(self):
        region_fixtures.RegionTests.setUp(self)
        enter = region_fixtures.target_graph("presence:enter", self.doc["doors"][0]["id"], "open")
        leave = region_fixtures.target_graph("presence:exit", self.doc["doors"][0]["id"], "closed")
        leave["nodes"].extend([node("count", "eventContext", property="count"),
            node("last", "compareValue", valueType="number", operator="eq", expected=0), node("check", "condition", state="empty")])
        leave["edges"] = [execution("event", "check"), execution("check", "state", "true"),
            data("target", "door", "state", "target"), data("count", "value", "last", "value"),
            data("last", "result", "check", "test")]
        self.doc["regions"][0]["blueprint"] = definition("region", **{"presence:enter": enter, "presence:exit": leave})

    def test_base_presence_fires_per_token_and_last_exit_is_an_explicit_node_condition(self):
        self.generated()
        one, two = self.place(), self.place(0, 2)
        one.refresh_from_db()
        self.move(one, 2, user=self.player)
        self.move(two, 3)
        self.assertEqual(self.door_state(), "open")
        self.move(one, 0, user=self.player)
        self.assertEqual(self.door_state(), "open")
        self.assertEqual(self.region().data["region"]["state"], "occupied")
        self.move(two, 0)
        self.assertEqual(self.door_state(), "closed")
        runs = list(AutomationRun.objects.filter(scene=self.scene).order_by("created_at"))
        self.assertEqual([event["event"] for run in runs for event in run.data["events"]],
                         ["presence:enter", "presence:enter", "presence:exit", "presence:exit"])
        self.assertEqual([run.data["context"]["count"] for run in runs], [1, 2, 1, 0])
