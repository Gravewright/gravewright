"""Persistent control nodes remain bounded, private and transaction-owned."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from unittest.mock import patch
import uuid

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.maps import builder_services, objects, services
from gravewright.maps.blueprint_memory import MAX_NOW, clean_memory, reconcile_memory
from gravewright.maps.blueprint_runtime import automation_memory
from gravewright.maps.blueprints import clean_blueprint, evaluate_graph
from gravewright.maps.models import AutomationRun, MapBuilderProject, Receipt, Scene, SceneObject
from gravewright.maps.services import MapError

from . import test_builder_blueprints as fixtures
from .test_blueprint_references import blueprint, execution, node


EVENT = "interact"


def controlled(kind="counter", *, event=EVENT, **parameters):
    defaults = {"counter": {"target": 3}, "once": {}, "cooldown": {"seconds": 2}}
    return blueprint({event: ([node("gate", kind, **{**defaults[kind], **parameters}),
        node("yes", "state", targetState="open"), node("no", "state", targetState="closed")],
        [execution("event", "gate"), execution("gate", "yes", "true"), execution("gate", "no", "false")])})


class ControlContractTests(SimpleTestCase):
    def test_counter_counts_once_per_event_and_keeps_saturating_progress(self):
        raw, memory = controlled(), {}
        for count in range(1, 5):
            previous = deepcopy(memory)
            result = evaluate_graph(raw, EVENT, "closed", memory=memory)
            self.assertEqual(memory, previous)
            memory = result["memory"]
            self.assertEqual(memory[EVENT]["gate"], {"type": "counter", "value": count})
            self.assertEqual(result["decisions"]["gate"], count >= 3)
            self.assertEqual(result["actions"][0]["targetState"], "open" if count >= 3 else "closed")
        memory[EVENT]["gate"]["value"] = 1_000_000
        self.assertEqual(evaluate_graph(raw, EVENT, "closed", memory=memory)["memory"], memory)

    def test_once_accepts_only_the_first_execution(self):
        raw = controlled("once")
        first = evaluate_graph(raw, EVENT, "closed")
        second = evaluate_graph(raw, EVENT, "closed", memory=first["memory"])
        self.assertTrue(first["decisions"]["gate"])
        self.assertFalse(second["decisions"]["gate"])
        self.assertEqual(second["memory"], {EVENT: {"gate": {"type": "once", "value": True}}})

    def test_cooldown_uses_deadline_without_extending_blocked_attempts(self):
        raw = controlled("cooldown", seconds=.1001)
        first = evaluate_graph(raw, EVENT, "closed", now=1000)
        self.assertEqual(first["memory"][EVENT]["gate"]["value"], 1101)
        blocked = evaluate_graph(raw, EVENT, "closed", memory=first["memory"], now=1100)
        self.assertFalse(blocked["decisions"]["gate"])
        self.assertEqual(blocked["memory"], first["memory"])
        ready = evaluate_graph(raw, EVENT, "closed", memory=blocked["memory"], now=1101)
        self.assertTrue(ready["decisions"]["gate"])
        self.assertEqual(ready["memory"][EVENT]["gate"]["value"], 1202)

    def test_time_and_parameters_are_authoritatively_bounded(self):
        for value in (0, -1, True, 1.5, 1_000_001, float("nan"), "3"):
            with self.subTest(target=value), self.assertRaises(MapError):
                clean_blueprint(controlled(target=value))
        for value in (.0999, 86400.1, True, float("inf"), float("nan"), 10 ** 1000, "2"):
            with self.subTest(seconds=value), self.assertRaises(MapError):
                clean_blueprint(controlled("cooldown", seconds=value))
        for value in (-1, 0.5, True, MAX_NOW + 1, float("inf")):
            with self.subTest(now=value), self.assertRaises(MapError):
                evaluate_graph(controlled("cooldown"), EVENT, "closed", now=value)
        evaluate_graph(controlled("cooldown", seconds=86400), EVENT, "closed", now=MAX_NOW)

    def test_version_one_extra_fields_and_nonbranch_ports_are_rejected(self):
        for kind in ("counter", "once", "cooldown"):
            raw = controlled(kind)
            raw["version"] = 1
            for graph in raw["graphs"].values():
                for edge in graph["edges"]:
                    edge.pop("kind", None)
            with self.subTest(kind=kind), self.assertRaisesMessage(MapError, "node type"):
                clean_blueprint(raw)
            raw = controlled(kind)
            raw["graphs"][EVENT]["edges"][1]["output"] = "next"
            with self.assertRaises(MapError):
                clean_blueprint(raw)
            raw = controlled(kind)
            raw["graphs"][EVENT]["nodes"][1]["value"] = 99
            with self.assertRaises(MapError):
                clean_blueprint(raw)

    def test_reconvergent_control_executes_once_and_disconnected_control_is_untouched(self):
        raw = controlled()
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("spare", "once"))
        graph["edges"].insert(1, execution("event", "gate"))
        with self.assertRaisesMessage(MapError, "Duplicate"):
            clean_blueprint(raw)
        graph["edges"].pop(1)
        graph["nodes"].append(node("seq", "sequence"))
        graph["edges"].append(execution("event", "seq"))
        graph["edges"].append(execution("seq", "gate", "then1"))
        result = evaluate_graph(raw, EVENT, "closed")
        self.assertEqual(result["trace"].count("gate"), 1)
        self.assertNotIn("spare", result["memory"][EVENT])

    def test_progress_is_per_event_and_same_id_can_exist_in_other_graph(self):
        raw = controlled("once")
        raw["graphs"].update(controlled("once", event="signal:Ready")["graphs"])
        first = evaluate_graph(raw, EVENT, "closed")
        signal = evaluate_graph(raw, "signal:Ready", "closed", memory=first["memory"])
        self.assertTrue(signal["decisions"]["gate"])
        self.assertEqual(set(signal["memory"]), {EVENT, "signal:Ready"})

    def test_reconcile_preserves_parameter_layout_and_edge_edits_but_prunes_removed_or_retyped(self):
        raw = controlled()
        stored = {EVENT: {"gate": {"type": "counter", "value": 7}}}
        changed = deepcopy(raw)
        changed["graphs"][EVENT]["nodes"][1].update(target=20, x=500, y=300)
        changed["graphs"][EVENT]["edges"] = []
        self.assertEqual(reconcile_memory(changed, stored), stored)
        self.assertEqual(reconcile_memory(controlled("once"), stored), {})
        self.assertEqual(reconcile_memory({"graphs": {}}, stored), {})
        once = {EVENT: {"gate": {"type": "once", "value": True}}}
        self.assertEqual(reconcile_memory(controlled("once"), once), once)

    def test_duration_edits_apply_after_existing_deadline_and_target_can_increase(self):
        stored = {EVENT: {"gate": {"type": "cooldown", "value": 2000}}}
        raw = controlled("cooldown", seconds=5)
        self.assertFalse(evaluate_graph(raw, EVENT, "closed", memory=stored, now=1999)["decisions"]["gate"])
        ready = evaluate_graph(raw, EVENT, "closed", memory=stored, now=2000)
        self.assertEqual(ready["memory"][EVENT]["gate"]["value"], 7000)
        stored = {EVENT: {"gate": {"type": "counter", "value": 4}}}
        self.assertFalse(evaluate_graph(controlled(target=10), EVENT, "closed", memory=stored)["decisions"]["gate"])

    def test_memory_rejects_malformed_or_unbounded_rows_before_pruning(self):
        invalid = ([], {"bad": {}}, {EVENT: []}, {EVENT: {"1bad": {"type": "once", "value": True}}},
            {EVENT: {"gate": {"type": "once", "value": False}}},
            {EVENT: {"gate": {"type": "counter", "value": True}}},
            {EVENT: {"gate": {"type": "cooldown", "value": 1.5}}},
            {EVENT: {"gate": {"type": "counter", "value": -1}}},
            {EVENT: {"gate": {"type": "once", "value": True, "other": 1}}},
            {EVENT: {f"N{i}": {"type": "once", "value": True} for i in range(129)}})
        for value in invalid:
            with self.subTest(memory=value), self.assertRaises(MapError):
                reconcile_memory({"graphs": {}}, value)
        self.assertEqual(clean_memory({EVENT: {}}), {})

    def test_existing_result_shape_and_implicit_simulation_time_stay_deterministic(self):
        raw = blueprint({})
        self.assertEqual(evaluate_graph(raw, EVENT, "closed"), {"trace": [], "actions": []})
        self.assertEqual(evaluate_graph(raw, EVENT, "closed", memory={})["memory"], {})
        self.assertEqual(evaluate_graph(controlled("cooldown"), EVENT, "closed")["memory"][EVENT]["gate"]["value"], 2000)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class ControlRuntimeTests(TestCase):
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
        self.doc["doors"][0]["blueprint"] = controlled()

    def reset(self, expected, *, user=None, request_id=None, element=None, event=EVENT, node_id="gate"):
        return services.command(self.campaign.pk, (user or self.gm).pk, "objects", {
            "mapId": str(self.scene.pk), "area": "automation", "action": "reset-memory", "data": {
                "elementId": str((element or self.door_object).pk), "event": event, "nodeId": node_id,
                "expected": expected}}, request_id or uuid.uuid4())

    def stored(self):
        self.door_object.refresh_from_db()
        return self.door_object.data.get("automationMemory", {})

    def edit_source(self, change):
        source = MapBuilderProject.objects.get(pk=self.project_id)
        changed = deepcopy(source.document)
        change(changed["doors"][0]["blueprint"])
        builder_services.save(self.campaign.pk, self.gm.pk, self.project_id, {
            "request_id": str(uuid.uuid4()), "expected_version": source.version,
            "folder_id": str(self.folder.pk), "document": changed})

    def test_counter_progress_survives_receipt_replay_and_reload(self):
        self.generated()
        request_id = uuid.uuid4()
        first = self.command("closed", user=self.player, request_id=request_id)
        self.assertEqual(self.command("closed", user=self.player, request_id=request_id), first)
        self.assertEqual(self.stored()[EVENT]["gate"]["value"], 1)
        self.command("closed", user=self.player)
        self.assertEqual(self.stored()[EVENT]["gate"]["value"], 2)
        self.command("closed", user=self.player)
        self.assertEqual(self.stored()[EVENT]["gate"]["value"], 3)
        self.assertEqual(self.door_object.data["door_state"], "open")
        self.assertEqual(Receipt.objects.filter(request_id=request_id).count(), 1)
        steps = AutomationRun.objects.filter(scene=self.scene).latest("created_at").data["events"][0]["steps"]
        self.assertEqual(next(row for row in steps if row["id"] == "gate"),
            {"id": "gate", "type": "counter", "result": True, "value": 3, "target": 3})

    def test_once_progress_is_saved_before_queued_signal_and_prevents_another_effect(self):
        raw = controlled("once")
        graph = raw["graphs"][EVENT]
        graph["nodes"][2] = node("yes", "emitEvent", scope="element", name="Again")
        raw["graphs"].update(blueprint({"signal:Again": (
            [node("set", "setVariable", scope="element", name="Done", valueType="boolean", value=True)],
            [execution("event", "set")])})["graphs"])
        self.doc["doors"][0]["blueprint"] = raw
        self.generated()
        self.command("closed")
        self.assertTrue(self.stored()[EVENT]["gate"]["value"])
        self.command("closed")
        self.assertEqual(sum(event["event"] == "signal:Again" for run in AutomationRun.objects.all()
                             for event in run.data["events"]), 1)

    def test_cooldown_uses_server_time_and_blocked_attempt_does_not_extend_it(self):
        self.doc["doors"][0]["blueprint"] = controlled("cooldown")
        # Avoid state transitions so each command runs the same interaction graph.
        self.doc["doors"][0]["blueprint"]["graphs"][EVENT]["nodes"][2]["targetState"] = "closed"
        self.generated()
        for seconds, expected_result, deadline in ((1000, True, 1002000), (1001, False, 1002000), (1002, True, 1004000)):
            with patch("django.utils.timezone.now", return_value=datetime.fromtimestamp(seconds, timezone.utc)):
                self.command("closed")
            self.assertEqual(self.stored()[EVENT]["gate"]["value"], deadline)
            run = AutomationRun.objects.filter(scene=self.scene).order_by("-created_at").first()
            self.assertEqual(next(row for row in run.data["events"][0]["steps"] if row["id"] == "gate")["result"], expected_result)

    def test_failed_chain_rolls_back_progress_and_no_receipt_is_kept(self):
        raw = controlled()
        graph = raw["graphs"][EVENT]
        graph["nodes"][3] = node("no", "emitEvent", scope="element", name="Loop")
        raw["graphs"].update(blueprint({"signal:Loop": (
            [node("again", "emitEvent", scope="element", name="Loop")], [execution("event", "again")])})["graphs"])
        self.doc["doors"][0]["blueprint"] = raw
        self.generated()
        request_id = uuid.uuid4()
        with self.assertRaisesMessage(MapError, "repeating chain"):
            self.command("closed", request_id=request_id)
        self.assertEqual(self.stored(), {})
        self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())
        self.assertEqual(AutomationRun.objects.get(scene=self.scene).outcome, "failed")

    def test_pause_does_not_advance_controls_and_progress_is_private(self):
        self.generated()
        self.scene.settings["automationPaused"] = True
        self.scene.save(update_fields=["settings"])
        self.command("closed")
        self.assertEqual(self.stored(), {})
        self.scene.settings.pop("automationPaused")
        self.scene.save(update_fields=["settings"])
        result = self.command("closed", user=self.player)
        from gravewright.journals.services import member
        for public in (result, services.state(self.campaign.pk, self.player.pk),
                services.state(self.campaign.pk, self.streamer.pk), services.view(self.scene),
                objects.layer_state(self.scene, member(self.campaign.pk, self.player.pk))):
            self.assertNotIn("automationMemory", json.dumps(public))
        self.client.force_login(self.gm)
        response = self.client.get(f"/api/maps/{self.scene.pk}/automation")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["memory"], {"elements": {str(self.door_object.pk): self.stored()}})
        for user in (self.player, self.streamer):
            self.client.force_login(user)
            self.assertEqual(self.client.get(f"/api/maps/{self.scene.pk}/automation").status_code, 404)

    def test_reset_is_gm_only_cas_idempotent_and_does_not_trigger_graphs(self):
        self.generated()
        self.command("closed")
        expected = self.stored()[EVENT]["gate"]
        for user in (self.player, self.streamer):
            with self.assertRaises(Exception):
                self.reset(expected, user=user)
        with self.assertRaisesMessage(MapError, "control changed") as error:
            self.reset({"type": "counter", "value": 0})
        self.assertEqual(error.exception.code, "conflict")
        request_id = uuid.uuid4()
        first = self.reset(expected, request_id=request_id)
        self.assertEqual(self.reset(expected, request_id=request_id), first)
        self.assertEqual(first["memory"], {"elements": {}})
        self.assertEqual(self.stored(), {})
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 1)
        self.command("closed")
        self.assertEqual(self.stored()[EVENT]["gate"]["value"], 1)

    def test_reset_rejects_an_element_from_another_scene(self):
        self.generated()
        foreign = Scene.objects.create(campaign=self.campaign, name="Other", width=100, height=100)
        other = SceneObject.objects.create(scene=foreign, kind="walls", data={**self.door_object.data,
            "automationMemory": {EVENT: {"gate": {"type": "counter", "value": 1}}}})
        with self.assertRaisesMessage(MapError, "element from this scene"):
            self.reset({"type": "counter", "value": 1}, element=other)

    def test_linked_update_preserves_progress_across_parameter_and_layout_edits(self):
        self.generated()
        self.command("closed")
        self.edit_source(lambda value: value["graphs"][EVENT]["nodes"][1].update(target=10, x=300))
        self.update_scene()
        self.assertEqual(self.stored()[EVENT]["gate"]["value"], 1)
        self.command("closed")
        self.assertEqual(self.stored()[EVENT]["gate"]["value"], 2)
        self.door_object.data["x1"] += 5
        self.door_object.save(update_fields=["data"])
        with self.assertRaisesMessage(MapError, "changed"):
            self.update_scene()

    def test_source_retyping_or_removing_control_prunes_progress(self):
        self.generated()
        self.command("closed")
        def retype(value):
            value["graphs"][EVENT]["nodes"][1] = node("gate", "once")
        self.edit_source(retype)
        self.update_scene()
        self.assertEqual(self.stored(), {})
        self.command("closed")
        self.assertEqual(self.stored()[EVENT]["gate"], {"type": "once", "value": True})
        self.edit_source(lambda value: value["graphs"].clear())
        self.update_scene()
        self.assertEqual(self.stored(), {})

    def test_native_edit_preserves_own_progress_and_pasted_copy_starts_empty(self):
        self.generated()
        self.command("closed")
        self.stored()
        self.command(action="update", x1=200, expected_version=self.door_object.version)
        self.assertEqual(self.stored()[EVENT]["gate"]["value"], 1)
        result = objects.apply(self.scene, self.membership, "wall-selection", "paste", {"walls": [{
            **self.door_object.data, "x1": 300, "x2": 400}]})
        clone = SceneObject.objects.get(pk=result["walls"][0])
        self.assertNotIn("automationMemory", clone.data)
        # Client-created private state is ignored rather than becoming authoritative.
        self.assertNotIn("automationMemory", objects.wall({**self.door_object.data,
            "automationMemory": {EVENT: {"gate": {"type": "counter", "value": 999}}}},
            campaign_id=self.campaign.pk, scene_id=self.scene.pk))

    def test_campaign_archive_preserves_control_progress_and_authored_node_identity(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        identity = "N" + str(self.door.pk)
        graph = self.doc["doors"][0]["blueprint"]["graphs"][EVENT]
        graph["nodes"][1]["id"] = identity
        for edge in graph["edges"]:
            for key in ("from", "to"):
                if edge[key] == "gate":
                    edge[key] = identity
        self.generated()
        self.command("closed")
        restored = import_campaign(export_campaign(self.campaign), self.gm, "Imported controls")
        scene = Scene.objects.get(campaign=restored)
        door = SceneObject.objects.get(scene=scene, kind="walls", data__kind="door")
        self.assertNotEqual(door.pk, self.door_object.pk)
        self.assertEqual(door.data["automationMemory"], self.stored())
        self.assertEqual(door.data["blueprint"]["graphs"][EVENT]["nodes"][1]["id"], identity)
        self.assertIn(identity, door.data["automationMemory"][EVENT])
        self.assertEqual(automation_memory(scene), {"elements": {str(door.pk): self.stored()}})
