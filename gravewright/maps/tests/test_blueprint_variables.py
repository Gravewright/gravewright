"""Typed private memory and named signals remain transactional scene automation."""

from copy import deepcopy
import json
import uuid

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.maps import builder_services, objects, services
from gravewright.maps.blueprints import clean_blueprint, default_blueprint, evaluate_graph
from gravewright.maps.blueprint_runtime import automation_variables
from gravewright.maps.blueprint_variables import clean_store, validate_definitions
from gravewright.maps.models import AutomationRun, MapBuilderProject, Receipt, Scene, SceneObject
from gravewright.maps.services import MapError

from . import test_builder_blueprints as fixtures
from .test_blueprint_references import blueprint, data, execution, node


def variable(identifier="set", scope="scene", name="Progress", value_type="number", value=3):
    return node(identifier, "setVariable", scope=scope, name=name, valueType=value_type, value=value)


def get_variable(identifier="get", scope="scene", name="Progress", value_type="number", default=0):
    return node(identifier, "getVariable", scope=scope, name=name, valueType=value_type, default=default)


def chain(event, *actions):
    nodes = [node("event", "event", event=event), *actions]
    return blueprint({event: (actions, [execution(a["id"], b["id"]) for a, b in zip(nodes, nodes[1:])])})


class VariableContractTests(SimpleTestCase):
    def test_typed_data_writes_and_comparisons_use_one_event_snapshot(self):
        raw = blueprint({"interact": (
            [variable(), get_variable(), node("compare", "compareValue", valueType="number", operator="gte", expected=2),
             node("condition", "condition", state="open"), node("act", "state", targetState="open")],
            [execution("event", "set"), execution("set", "condition"), data("get", "value", "compare", "value"),
             data("compare", "result", "condition", "test"), execution("condition", "act", "true")])})
        result = evaluate_graph(raw, "interact", "closed")
        self.assertEqual(result["values"], {"get": 0, "compare": False})
        self.assertEqual([a["type"] for a in result["actions"]], ["setVariable"])
        memory = {"scene": {"Progress": {"type": "number", "value": 2}}}
        before = deepcopy(memory)
        result = evaluate_graph(raw, "interact", "closed", variables=memory)
        self.assertEqual([a["type"] for a in result["actions"]], ["setVariable", "state"])
        self.assertEqual(memory, before)

    def test_boolean_number_text_ports_reject_cross_type_connections(self):
        for value_type, value in (("boolean", True), ("number", 2.5), ("text", "ready")):
            raw = blueprint({"signal:Ready": (
                [get_variable(value_type=value_type, default=value), variable(value_type=value_type, value=value)],
                [execution("event", "set"), data("get", "value", "set", "value")])})
            result = evaluate_graph(raw, "signal:Ready", "closed")
            self.assertEqual(result["actions"][0]["value"], value)
            raw["graphs"]["signal:Ready"]["nodes"][2].update(valueType="number" if value_type != "number" else "text",
                value=0 if value_type != "number" else "")
            with self.assertRaisesMessage(MapError, "connection input"):
                clean_blueprint(raw)

    def test_variable_names_types_values_and_operator_bounds_are_authoritative(self):
        valid = variable()
        bad = [{**valid, "name": value} for value in ("", "1start", "a b", "é", "a" * 65, "x\x00")]
        bad += [{**valid, "value": value} for value in (True, "2", float("nan"), float("inf"), 1_000_001, 10 ** 1000)]
        bad += [{**valid, "scope": "campaign"}, {**valid, "valueType": "object"},
                {**valid, "valueType": "text", "value": "x" * 257},
                {**valid, "valueType": "boolean", "value": 1},
                node("compare", "compareValue", valueType="text", operator="lt", expected="x")]
        for action in bad:
            with self.subTest(action=repr(action)[:100]), self.assertRaises(MapError):
                clean_blueprint(chain("interact", action))
        for key in ("constructor", "__proto__", "Quest.State-1", "A" * 64):
            # Names begin with a letter; JavaScript prototype labels are ordinary keys.
            if key.startswith("_"):
                continue
            clean_blueprint(chain("interact", {**valid, "name": key}))

    def test_type_consistency_is_per_element_and_shared_for_scene_scope(self):
        first = chain("interact", variable(scope="element"))
        second = chain("interact", variable(scope="element", value_type="text", value="ready"))
        validate_definitions([first, second])
        first["graphs"]["signal:Ready"] = chain("signal:Ready", variable(scope="element", value_type="text", value="x"))["graphs"]["signal:Ready"]
        with self.assertRaisesMessage(MapError, "same type"):
            clean_blueprint(first)
        with self.assertRaisesMessage(MapError, "same type"):
            validate_definitions([chain("interact", variable()),
                                  chain("interact", variable(value_type="text", value="ready"))])

    def test_stores_bound_count_and_preserve_exact_unicode_text(self):
        store = {f"V{i}": {"type": "text", "value": "😀" * 256} for i in range(64)}
        self.assertEqual(clean_store(store), store)
        for mutation in ({**store, "Extra": {"type": "boolean", "value": False}},
                         {"A": {"type": "number", "value": False}},
                         {"A": {"type": "text", "value": "😀" * 257}},
                         {"A": {"type": "boolean", "value": True, "private": 1}}):
            with self.assertRaises(MapError):
                clean_store(mutation)

    def test_named_signals_are_version_two_bounded_and_validated(self):
        raw = default_blueprint()
        raw["version"] = 2
        for i in range(16):
            event = f"signal:Event{i}"
            raw["graphs"][event] = chain(event)["graphs"][event]
        self.assertEqual(len(clean_blueprint(raw)["graphs"]), 16)
        raw["graphs"]["signal:Extra"] = chain("signal:Extra")["graphs"]["signal:Extra"]
        with self.assertRaisesMessage(MapError, "too many signal"):
            clean_blueprint(raw)
        for event in ("signal:", "signal:two words", "signal:é", "signal:" + "A" * 65):
            with self.subTest(event=event), self.assertRaises(MapError):
                clean_blueprint(chain(event))
        raw = chain("signal:Ready", node("emit", "emitEvent", scope="element", name="Ready"))
        raw["version"] = 1
        with self.assertRaises(MapError):
            clean_blueprint(raw)

    def test_get_type_mismatch_fails_instead_of_using_a_default(self):
        raw = blueprint({"interact": ([get_variable(), variable()],
            [execution("event", "set"), data("get", "value", "set", "value")])})
        with self.assertRaisesMessage(MapError, "same type"):
            evaluate_graph(raw, "interact", "closed", variables={"scene": {
                "Progress": {"type": "text", "value": "wrong"}}})

    def test_snapshot_rejects_invalid_values_even_when_the_graph_does_not_read_them(self):
        for memory in ([], {"campaign": {}}, {"scene": []},
                       {"scene": {"Flag": {"type": "boolean", "value": 1}}}):
            with self.subTest(memory=memory), self.assertRaises(MapError):
                evaluate_graph(default_blueprint(), "interact", "open", variables=memory)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class VariableSignalRuntimeTests(TestCase):
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
        self.doc["doors"][0]["blueprint"] = default_blueprint()
        self.doc["doors"][0]["blueprint"]["version"] = 2

    def configure(self, value):
        self.doc["doors"][0]["blueprint"] = value

    def other_door(self, definition, *, locked=False):
        return SceneObject.objects.create(scene=self.scene, kind="walls", data=objects.wall({
            **self.door_object.data, "x1": 64, "x2": 128, "door_state": "locked" if locked else "closed",
            "blueprint": definition}, campaign_id=self.campaign.pk, scene_id=self.scene.pk))

    def emit(self, scope="element", name="Ready", target=None, *actions):
        nodes = [*actions, node("emit", "emitEvent", scope=scope, name=name)]
        graph = chain("interact", *nodes)
        if target:
            graph["graphs"]["interact"]["nodes"].append(node("ref", "reference", targetId=str(target.pk)))
            graph["graphs"]["interact"]["edges"].append(data("ref", "door", "emit", "target"))
        self.door_object.data["blueprint"] = graph
        self.door_object.save(update_fields=["data"])

    def reset(self, scope, name, expected, *, element=None, user=None, request_id=None):
        return services.command(self.campaign.pk, (user or self.gm).pk, "objects", {
            "mapId": str(self.scene.pk), "area": "automation", "action": "reset-variable", "data": {
                "scope": scope, "name": name, "expected": expected,
                **({"elementId": str(element.pk)} if element else {})}}, request_id or uuid.uuid4())

    def test_all_types_persist_receipt_replay_and_reload(self):
        self.configure(chain("interact", variable(), variable("flag", "element", "Solved", "boolean", True),
                             variable("text", "scene", "Message", "text", "Porta pronta 😀")))
        self.generated()
        request_id = uuid.uuid4()
        first = self.command(request_id=request_id)
        self.assertEqual(self.command(request_id=request_id), first)
        self.scene.refresh_from_db()
        self.door_object.refresh_from_db()
        self.assertEqual(self.scene.settings["automationVariables"], {
            "Progress": {"type": "number", "value": 3}, "Message": {"type": "text", "value": "Porta pronta 😀"}})
        self.assertEqual(self.door_object.data["automationVariables"], {"Solved": {"type": "boolean", "value": True}})
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 1)
        self.assertEqual(Receipt.objects.filter(request_id=request_id).count(), 1)

    def test_signal_listener_reads_prior_writes_and_changes_state(self):
        self.generated()
        receiver = self.other_door(blueprint({"signal:Ready": (
            [get_variable(), node("compare", "compareValue", valueType="number", operator="eq", expected=3),
             node("check", "condition", state="open"), node("open", "state", targetState="open")],
            [execution("event", "check"), data("get", "value", "compare", "value"),
             data("compare", "result", "check", "test"), execution("check", "open", "true")])}))
        self.emit("element", "Ready", receiver, variable())
        self.command(user=self.player)
        receiver.refresh_from_db()
        self.assertEqual(receiver.data["door_state"], "open")
        run = AutomationRun.objects.get(scene=self.scene).data
        emission = next(step for event in run["events"] for step in event["steps"] if step["type"] == "emitEvent")
        self.assertEqual(emission["doorId"], str(receiver.pk))
        signal, = [event for event in run["events"] if event["event"] == "signal:Ready"]
        self.assertEqual(signal["doorId"], str(receiver.pk))
        self.assertEqual(next(s for s in signal["steps"] if s["id"] == "get")["value"], 3)

    def test_scene_signal_broadcast_has_stable_order_and_only_matching_listeners(self):
        self.generated()
        first = self.other_door(chain("signal:Ready", node("open", "state", targetState="open")))
        second = self.other_door(chain("signal:Ready", node("open", "state", targetState="open")))
        other = self.other_door(chain("signal:Other", node("open", "state", targetState="open")))
        self.emit("scene")
        self.command()
        for row in (first, second, other):
            row.refresh_from_db()
        self.assertEqual([row.data["door_state"] for row in (first, second, other)], ["open", "open", "closed"])
        run = AutomationRun.objects.get(scene=self.scene).data
        self.assertEqual([event["doorId"] for event in run["events"] if event["event"] == "signal:Ready"],
                         [str(first.pk), str(second.pk)])

    def test_element_signal_defaults_self_and_observes_next_event_memory(self):
        graphs = chain("interact", variable(scope="element"), node("emit", "emitEvent", scope="element", name="Ready"))
        receiver = blueprint({"signal:Ready": ([get_variable(scope="element"), variable("copy", "scene", "Copied")],
            [execution("event", "copy"), data("get", "value", "copy", "value")])})
        graphs["graphs"].update(receiver["graphs"])
        self.configure(graphs)
        self.generated()
        self.command()
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.settings["automationVariables"]["Copied"]["value"], 3)

    def test_repeating_signal_chain_rolls_back_memory_lights_and_state(self):
        graphs = chain("interact", variable(), variable("local", "element"),
            node("lamp", "light", targetId=self.light_id, enabled=True),
            node("open", "state", targetState="open"),
            node("emit", "emitEvent", scope="element", name="Loop"))
        graphs["graphs"].update(chain("signal:Loop", node("loop", "emitEvent", scope="element", name="Loop"))["graphs"])
        self.configure(graphs)
        self.generated()
        request_id = uuid.uuid4()
        before = deepcopy(self.door_object.data)
        with self.assertRaisesMessage(MapError, "repeating chain"):
            self.command(request_id=request_id)
        self.scene.refresh_from_db()
        self.door_object.refresh_from_db()
        self.light_object.refresh_from_db()
        self.assertNotIn("automationVariables", self.scene.settings)
        self.assertEqual(self.door_object.data, before)
        self.assertFalse(self.light_object.data["enabled"])
        self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())
        self.assertEqual(AutomationRun.objects.get(scene=self.scene).outcome, "failed")

    def test_player_signal_cannot_unlock_without_authored_authorization(self):
        self.generated()
        receiver = self.other_door(chain("signal:Ready", node("unlock", "state", targetState="open")), locked=True)
        self.emit("element", "Ready", receiver)
        self.command(user=self.player)
        receiver.refresh_from_db()
        self.assertEqual(receiver.data["door_state"], "locked")
        refusal = next(event for event in AutomationRun.objects.get(scene=self.scene).data["events"]
                       if event["event"] == "refused")
        self.assertEqual(refusal["doorId"], str(receiver.pk))
        self.assertIn("cannot be operated", refusal["message"])
        receiver.data["blueprint"]["graphs"]["signal:Ready"]["nodes"][1]["players"] = True
        receiver.save(update_fields=["data"])
        self.command("closed")
        self.command(user=self.player)
        receiver.refresh_from_db()
        self.assertEqual(receiver.data["door_state"], "open")

    def test_missing_target_is_logged_and_scene_signal_without_listeners_is_a_noop(self):
        self.generated()
        missing = type("Missing", (), {"pk": uuid.uuid4()})()
        self.emit("element", "Ready", missing)
        self.command()
        self.assertTrue(AutomationRun.objects.get(scene=self.scene).data["events"][0]["steps"][1]["missing"])
        self.command("closed")
        self.emit("scene", "NoListeners")
        self.command()
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 3)

    def test_paused_scene_does_not_write_variables_or_emit_signals(self):
        self.configure(chain("interact", variable(), node("emit", "emitEvent", scope="scene", name="Ready")))
        self.generated()
        receiver = self.other_door(chain("signal:Ready", node("open", "state", targetState="open")))
        self.scene.settings["automationPaused"] = True
        self.scene.save(update_fields=["settings"])
        self.command()
        self.scene.refresh_from_db()
        receiver.refresh_from_db()
        self.assertNotIn("automationVariables", self.scene.settings)
        self.assertEqual(receiver.data["door_state"], "closed")

    def test_private_memory_is_never_in_public_scenes_layers_or_player_results(self):
        self.configure(chain("interact", variable(), variable("local", "element", "Secret", "text", "private-plan")))
        self.generated()
        result = self.command(user=self.player)
        for public in (result, services.state(self.campaign.pk, self.player.pk),
                       services.state(self.campaign.pk, self.streamer.pk), services.view(self.scene)):
            self.assertNotIn("automationVariables", json.dumps(public))
            self.assertNotIn("private-plan", json.dumps(public))
        from gravewright.journals.services import member
        for user in (self.player, self.streamer):
            projected = objects.layer_state(self.scene, member(self.campaign.pk, user.pk))
            self.assertNotIn("automationVariables", json.dumps(projected))
            self.client.force_login(user)
            self.assertEqual(self.client.get(f"/api/maps/{self.scene.pk}/automation").status_code, 404)
        self.scene.refresh_from_db()
        memory = automation_variables(self.scene)
        self.assertIn("Progress", memory["scene"])
        self.assertIn("Secret", memory["elements"][str(self.door_object.pk)])

    def test_reset_is_gm_only_compare_and_swap_and_idempotent_without_events(self):
        self.configure(chain("interact", variable(), variable("local", "element", "Done", "boolean", True)))
        self.generated()
        self.command()
        for user in (self.player, self.streamer):
            with self.subTest(role=user), self.assertRaises(Exception):
                self.reset("scene", "Progress", {"type": "number", "value": 3}, user=user)
        with self.assertRaisesMessage(MapError, "variable changed") as error:
            self.reset("scene", "Progress", {"type": "number", "value": 2})
        self.assertEqual(error.exception.code, "conflict")
        request_id = uuid.uuid4()
        first = self.reset("scene", "Progress", {"type": "number", "value": 3}, request_id=request_id)
        self.assertEqual(self.reset("scene", "Progress", {"type": "number", "value": 3}, request_id=request_id), first)
        self.reset("element", "Done", {"type": "boolean", "value": True}, element=self.door_object)
        self.scene.refresh_from_db()
        self.assertEqual(automation_variables(self.scene), {"scene": {}, "elements": {}})
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 1)

    def test_linked_update_preserves_memory_without_adopting_manual_native_edits(self):
        self.configure(chain("interact", variable(), variable("local", "element")))
        self.generated()
        self.command()
        self.update_scene()
        self.scene.refresh_from_db()
        self.door_object.refresh_from_db()
        self.assertIn("Progress", self.scene.settings["automationVariables"])
        self.assertIn("Progress", self.door_object.data["automationVariables"])
        self.door_object.data["x1"] += 5
        self.door_object.save(update_fields=["data"])
        with self.assertRaisesMessage(MapError, "changed"):
            self.update_scene()

    def test_native_edits_preserve_own_memory_but_paste_resets_it(self):
        self.configure(chain("interact", variable(scope="element")))
        self.generated()
        self.command()
        self.door_object.refresh_from_db()
        self.command(action="update", x1=200, expected_version=self.door_object.version)
        self.door_object.refresh_from_db()
        self.assertIn("Progress", self.door_object.data["automationVariables"])
        result = objects.apply(self.scene, self.membership, "wall-selection", "paste", {"walls": [{
            **self.door_object.data, "x1": 300, "x2": 400}]})
        clone = SceneObject.objects.get(pk=result["walls"][0])
        self.assertNotIn("automationVariables", clone.data)

    def test_scene_type_conflict_rejected_before_source_save(self):
        self.configure(chain("interact", variable()))
        second = deepcopy(self.doc["doors"][0])
        second.update(id=str(uuid.uuid4()), x1=5, x2=6,
            blueprint=chain("interact", variable(value_type="text", value="wrong")))
        self.doc["doors"].append(second)
        response = self.save()
        self.assertEqual(response.status_code, 400)
        self.assertFalse(MapBuilderProject.objects.exists())

    def test_archive_clone_preserves_memory_and_uuid_text_but_remaps_targets(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        literal = str(self.door.pk)
        name = "Signal." + literal
        raw = chain("interact", variable("local", "element", "Literal", "text", literal),
                    variable("shared", "scene", "Global", "text", literal),
                    node("emit", "emitEvent", scope="element", name=name))
        raw["graphs"].update(chain("signal:" + name, variable("other", "element", "Other", "text", literal))["graphs"])
        self.configure(raw)
        self.generated()
        self.command()
        restored = import_campaign(export_campaign(self.campaign), self.gm, "Imported variables")
        scene = Scene.objects.get(campaign=restored)
        door = SceneObject.objects.get(scene=scene, kind="walls", data__kind="door")
        self.assertEqual(scene.settings["automationVariables"]["Global"]["value"], literal)
        self.assertEqual(door.data["automationVariables"]["Literal"]["value"], literal)
        self.assertIn("signal:" + name, door.data["blueprint"]["graphs"])
        self.assertEqual(door.data["blueprint"]["graphs"]["interact"]["nodes"][1]["value"], literal)
        self.assertNotEqual(door.pk, self.door_object.pk)

    def test_scene_variable_type_change_requires_explicit_gm_reset_before_update(self):
        self.configure(chain("interact", variable()))
        self.generated()
        self.command()
        source = MapBuilderProject.objects.get(pk=self.project_id)
        changed = deepcopy(source.document)
        changed["doors"][0]["blueprint"] = chain("interact", variable(value_type="text", value="new"))
        builder_services.save(self.campaign.pk, self.gm.pk, self.project_id, {
            "request_id": str(uuid.uuid4()), "expected_version": source.version,
            "folder_id": str(self.folder.pk), "document": changed})
        with self.assertRaisesMessage(MapError, "same type"):
            self.update_scene()
        self.reset("scene", "Progress", {"type": "number", "value": 3})
        self.update_scene()
        self.command("closed")
        self.command()
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.settings["automationVariables"]["Progress"], {"type": "text", "value": "new"})

    def test_runtime_variable_count_limit_rolls_back_the_entire_operation(self):
        for scope in ("element", "scene"):
            with self.subTest(scope=scope):
                self.configure(chain("interact", variable(scope=scope)))
                if not hasattr(self, "scene"):
                    self.generated()
                memory = {f"V{i}": {"type": "number", "value": i} for i in range(64)}
                self.scene.refresh_from_db()
                self.door_object.refresh_from_db()
                self.door_object.data["blueprint"] = self.doc["doors"][0]["blueprint"]
                if scope == "scene":
                    self.door_object.data.pop("automationVariables", None)
                    self.scene.settings["automationVariables"] = memory
                    self.scene.save(update_fields=["settings"])
                else:
                    self.door_object.data["automationVariables"] = memory
                self.door_object.save(update_fields=["data"])
                before = deepcopy(self.door_object.data)
                with self.assertRaisesMessage(MapError, "too many variables"):
                    self.command()
                self.door_object.refresh_from_db()
                self.assertEqual(self.door_object.data, before)

    def test_reset_rejects_a_foreign_scene_element(self):
        self.generated()
        foreign = Scene.objects.create(campaign=self.campaign, name="Other scene", width=100, height=100)
        other = SceneObject.objects.create(scene=foreign, kind="walls", data={**self.door_object.data,
            "automationVariables": {"Progress": {"type": "number", "value": 3}}})
        with self.assertRaisesMessage(MapError, "element from this scene"):
            self.reset("element", "Progress", {"type": "number", "value": 3}, element=other)
        other.refresh_from_db()
        self.assertIn("Progress", other.data["automationVariables"])
