"""Typed Boolean composition observes live elements without counting interactions."""

from copy import deepcopy
from itertools import product
import uuid

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.journals.services import JournalError
from gravewright.maps import builder_services, objects, services
from gravewright.maps.blueprints import clean_blueprint, default_blueprint, evaluate_graph
from gravewright.maps.models import AutomationRun, Broadcast, MapBuilderProject, Receipt, Scene
from gravewright.maps.services import MapError

from . import test_builder_blueprints as fixtures
from .test_blueprint_data_nodes import blueprint, data, execution, node


def puzzle_graph(event, targets, destination, kind="all"):
    """Compare independent element states and set a door from the combined result."""
    nodes = [node("event", "event", event=event), node("gate", kind),
             node("check", "condition", state="on"), node("destination", "reference", targetId=destination),
             node("open", "state", targetState="open"), node("close", "state", targetState="closed")]
    edges = [execution("event", "check"), data("gate", "result", "check", "test"),
             execution("check", "open", "true"), execution("check", "close", "false"),
             data("destination", "door", "open", "target"), data("destination", "door", "close", "target")]
    for index, target in enumerate(targets):
        suffix = str(index)
        nodes.extend([node("ref" + suffix, "reference", targetId=target),
                      node("prop" + suffix, "property", property="state"),
                      node("cmp" + suffix, "compare", state="on")])
        edges.extend([data("ref" + suffix, "door", "prop" + suffix, "target"),
                      data("prop" + suffix, "value", "cmp" + suffix, "value"),
                      data("cmp" + suffix, "result", "gate", "abcd"[index])])
    return {"nodes": nodes, "edges": edges}


class BooleanLogicContractTests(SimpleTestCase):
    def setUp(self):
        self.targets = [str(uuid.uuid4()) for _ in range(4)]
        self.destination = str(uuid.uuid4())

    def definition(self, kind="all", count=3):
        result = default_blueprint("torch")
        result["graphs"]["interact"] = puzzle_graph("interact", self.targets[:count], self.destination, kind)
        return result

    def test_all_and_any_compare_every_combination_of_three_distinct_elements(self):
        for kind in ("all", "any"):
            raw = clean_blueprint(self.definition(kind))
            for bits in product((False, True), repeat=3):
                states = dict(zip(self.targets, ("on" if bit else "off" for bit in bits)))
                result = evaluate_graph(raw, "interact", "on", "off", states)
                expected = all(bits) if kind == "all" else any(bits)
                with self.subTest(kind=kind, bits=bits):
                    self.assertIs(result["values"]["gate"], expected)
                    self.assertIs(result["decisions"]["check"], expected)
                    self.assertEqual(result["actions"][0]["targetState"], "open" if expected else "closed")
                    self.assertEqual(result["actions"][0]["target"], self.destination)
                    self.assertEqual([value for value in result["trace"] if value.startswith("cmp")],
                                     ["cmp0", "cmp1", "cmp2"], "all inputs are traced even after a decisive value")
                self.assertEqual(states[self.targets[0]], "on" if bits[0] else "off")

    def test_fourth_input_and_authored_edge_order_do_not_change_port_order(self):
        raw = self.definition(count=4)
        raw["graphs"]["interact"]["edges"].reverse()
        states = {target: "on" for target in self.targets}
        self.assertIs(evaluate_graph(raw, "interact", "on", doors=states)["values"]["gate"], True)
        states[self.targets[3]] = "off"
        result = evaluate_graph(raw, "interact", "on", doors=states)
        self.assertIs(result["values"]["gate"], False)
        self.assertEqual([value for value in result["trace"] if value.startswith("cmp")],
                         ["cmp0", "cmp1", "cmp2", "cmp3"])

    def test_missing_reference_cannot_satisfy_all_and_is_visible_in_the_value_trace(self):
        states = {target: "on" for target in self.targets[1:]}
        result = evaluate_graph(self.definition(), "interact", "on", doors=states)
        self.assertIsNone(result["values"]["prop0"])
        self.assertIs(result["values"]["cmp0"], False)
        self.assertIs(result["values"]["gate"], False)
        self.assertEqual(result["actions"][0]["targetState"], "closed")
        # Any still accepts another present, satisfied condition.
        self.assertIs(evaluate_graph(self.definition("any"), "interact", "on", doors=states)["values"]["gate"], True)

    def test_incomplete_gate_drafts_never_open_a_door(self):
        for kind, count in product(("all", "any"), (0, 1)):
            raw = clean_blueprint(self.definition(kind, count))
            with self.subTest(kind=kind, count=count):
                result = evaluate_graph(raw, "interact", "on", doors={self.targets[0]: "on"})
                self.assertIs(result["values"]["gate"], False)
                self.assertEqual(result["actions"][0]["id"], "close")

    def test_nested_gates_reuse_values_once_and_allow_a_shared_source_on_two_inputs(self):
        raw = blueprint("interact", [node("current", "compare", state="open"),
            node("previous", "property", property="previous"), node("was", "compare", state="locked"),
            node("either", "any"), node("both", "all"), node("check", "condition", state="closed"),
            node("act", "state", targetState="closed")],
            [execution("event", "check"), execution("check", "act", "true"),
             data("previous", "value", "was", "value"), data("current", "result", "either", "a"),
             data("was", "result", "either", "d"), data("either", "result", "both", "a"),
             data("either", "result", "both", "c"), data("both", "result", "check", "test")])
        result = evaluate_graph(clean_blueprint(raw), "interact", "open", "closed")
        self.assertEqual([action["id"] for action in result["actions"]], ["act"])
        self.assertEqual(result["trace"], ["event", "check", "current", "previous", "was", "either", "both", "act"])
        self.assertEqual(result["values"], {"current": True, "previous": "closed", "was": False,
                                            "either": True, "both": True})

    def test_only_boolean_inputs_and_data_ports_are_accepted_without_weakening_limits(self):
        raw = self.definition()
        for bad in (data("ref0", "door", "gate", "a"), data("prop0", "value", "gate", "a"),
                    data("cmp0", "result", "gate", "e"), execution("event", "gate"),
                    execution("gate", "open"), data("gate", "result", "gate", "d")):
            invalid = deepcopy(raw)
            graph = invalid["graphs"]["interact"]
            graph["edges"] = [edge for edge in graph["edges"] if not (edge["to"] == "gate" and edge.get("input") == "a")]
            graph["edges"].append(bad)
            with self.subTest(edge=bad), self.assertRaises(MapError):
                clean_blueprint(invalid)
        invalid = deepcopy(raw)
        invalid["graphs"]["interact"]["nodes"][1]["count"] = 3
        with self.assertRaisesMessage(MapError, "Unknown blueprint node field"):
            clean_blueprint(invalid)

    def test_composite_nodes_are_rejected_in_version_one_even_when_disconnected(self):
        for kind in ("all", "any"):
            raw = default_blueprint()
            raw["version"] = 1
            raw["graphs"]["interact"] = {"nodes": [node("event", "event", event="interact"), node("gate", kind)],
                                                "edges": []}
            with self.subTest(kind=kind), self.assertRaisesMessage(MapError, "node type"):
                clean_blueprint(raw)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class BooleanPuzzleRuntimeTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    update_scene = fixtures.BuilderBlueprintTests.update_scene

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.art = self.asset("torch-puzzle.png", "#ffb633")
        self.doc["assets"].append({"assetId": str(self.art.pk), "role": "decoration"})
        self.torch_ids = [str(uuid.uuid4()) for _ in range(3)]
        light = deepcopy(self.doc["lights"][0])
        self.doc["lights"] = []
        self.doc["doors"][0]["blueprint"] = default_blueprint()
        for index, identifier in enumerate(self.torch_ids):
            light_id = str(uuid.uuid4())
            self.doc["lights"].append({**deepcopy(light), "id": light_id, "x": index + 2, "enabled": True})
            definition = default_blueprint("torch")
            definition["graphs"] = {
                "interact": {"nodes": [node("event", "event", event="interact"),
                    node("isOn", "condition", state="on"), node("off", "state", targetState="off"),
                    node("on", "state", targetState="on"),
                    node("evaluate", "emitEvent", scope="element", name="EvaluatePuzzle")],
                    "edges": [execution("event", "isOn"), execution("isOn", "off", "true"),
                        execution("isOn", "on", "false"), execution("off", "evaluate"), execution("on", "evaluate")]},
                "signal:EvaluatePuzzle": puzzle_graph("signal:EvaluatePuzzle", self.torch_ids, self.doc["doors"][0]["id"]),
            }
            self.doc["decorations"].append({"id": identifier, "assetId": str(self.art.pk), "layerId": light["layerId"],
                "x": index + 2, "y": 5, "width": 1, "height": 1, "rotation": 0,
                "torch": {"state": "off", "lit": True, "lightId": light_id}, "blueprint": definition})

    def generated(self):
        response = self.save()
        self.assertEqual(response.status_code, 200, response.content)
        response = self.generate()
        self.assertEqual(response.status_code, 200, response.content)
        self.scene = Scene.objects.get(pk=response.json()["scene"]["id"])
        self.scene.visibility = "players"
        self.scene.save(update_fields=["visibility"])
        Broadcast.objects.update_or_create(campaign=self.campaign, defaults={"scene": self.scene})
        self.door_object = self.scene.elements.get(kind="walls", data__kind="door")
        source = MapBuilderProject.objects.get(pk=self.project_id)
        ids = {row["sourceId"]: row["id"] for row in source.generation["objects"]}
        self.native_torches = [ids[identifier] for identifier in self.torch_ids]

    def torch(self, index):
        return self.scene.elements.get(pk=self.native_torches[index], kind="images")

    def turn(self, index, user=None, request_id=None):
        return services.command(self.campaign.pk, (user or self.gm).pk, "objects",
            {"mapId": str(self.scene.pk), "area": "images", "action": "interact",
             "data": {"image_id": str(self.torch(index).pk)}}, request_id or uuid.uuid4())

    def door_state(self):
        self.door_object.refresh_from_db()
        return self.door_object.data["door_state"]

    def test_repeated_turns_of_one_torch_do_not_satisfy_three_distinct_conditions(self):
        self.generated()
        for _ in range(3):
            self.turn(0, user=self.player)
            self.assertEqual(self.door_state(), "closed")
        self.turn(1, user=self.player)
        self.assertEqual(self.door_state(), "closed")
        operation = uuid.uuid4()
        response = self.turn(2, user=self.player, request_id=operation)
        self.assertEqual(self.door_state(), "open")
        self.assertNotIn("blueprint", response)
        self.assertEqual(self.turn(2, user=self.player, request_id=operation), response)
        self.assertEqual(self.door_state(), "open", "retry does not turn the same mechanism twice")
        run = AutomationRun.objects.filter(scene=self.scene).first()
        evaluated = next(event for event in run.data["events"] if event["event"] == "signal:EvaluatePuzzle")
        gate, = [step for step in evaluated["steps"] if step["type"] == "all"]
        self.assertIs(gate["value"], True)
        self.turn(1, user=self.player)
        self.assertEqual(self.door_state(), "closed")
        public = objects.layer_state(self.scene, services.member(self.campaign.pk, self.player.pk))
        self.assertTrue(all("blueprint" not in row for row in public["images"]))
        with self.assertRaisesMessage(JournalError, "read-only"):
            self.turn(0, user=self.streamer)

    def test_any_opens_on_one_torch_and_closes_only_after_all_return_to_normal(self):
        for row in self.doc["decorations"]:
            row["blueprint"]["graphs"]["signal:EvaluatePuzzle"]["nodes"][1]["type"] = "any"
        self.generated()
        self.turn(0)
        self.assertEqual(self.door_state(), "open")
        self.turn(1)
        self.turn(0)
        self.assertEqual(self.door_state(), "open")
        self.turn(1)
        self.assertEqual(self.door_state(), "closed")

    def test_missing_torch_reference_fails_closed_and_does_not_borrow_self_state(self):
        missing = str(uuid.uuid4())
        for row in self.doc["decorations"]:
            graph = row["blueprint"]["graphs"]["signal:EvaluatePuzzle"]
            next(item for item in graph["nodes"] if item["id"] == "ref2")["targetId"] = missing
        self.generated()
        for index in range(3):
            self.turn(index)
        self.assertEqual(self.door_state(), "closed")
        run = AutomationRun.objects.filter(scene=self.scene).first()
        evaluated = next(event for event in run.data["events"] if event["event"] == "signal:EvaluatePuzzle")
        prop, = [step for step in evaluated["steps"] if step["id"] == "prop2"]
        self.assertIsNone(prop["value"])

    def test_locked_door_permission_still_applies_to_a_satisfied_player_puzzle(self):
        self.doc["doors"][0]["state"] = "locked"
        self.generated()
        for index in range(3):
            self.turn(index, user=self.player)
        self.assertEqual(self.door_state(), "locked")
        self.assertTrue(all(self.torch(index).data["torch"]["state"] == "on" for index in range(3)))
        run = AutomationRun.objects.filter(scene=self.scene).first()
        self.assertTrue(any(event["event"] == "refused" and event["doorId"] == str(self.door_object.pk)
                            and event["message"] == "This door cannot be operated." for event in run.data["events"]))

    def test_save_update_and_archive_keep_composites_and_remap_each_torch_reference(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        self.generated()
        source = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual(source.document, self.doc)
        native_ids = {str(self.torch(index).pk) for index in range(3)}
        self.assertTrue(native_ids.isdisjoint(self.torch_ids))
        for index in range(3):
            self.turn(index)
        self.update_scene()
        self.assertEqual(self.door_state(), "open")
        self.assertEqual({str(self.torch(index).pk) for index in range(3)}, native_ids)
        restored = import_campaign(export_campaign(self.campaign), self.gm, "Logic clone")
        cloned = MapBuilderProject.objects.get(campaign=restored)
        cloned_ids = {str(row.pk) for row in cloned.scene.elements.filter(kind="images", data__torch__isnull=False)}
        self.assertTrue(cloned_ids.isdisjoint(native_ids))
        for row in cloned.scene.elements.filter(kind="images", data__torch__isnull=False):
            self.assertEqual(set(row.data["blueprint"]["graphs"]), {"interact", "signal:EvaluatePuzzle"})
            graph = row.data["blueprint"]["graphs"]["signal:EvaluatePuzzle"]
            self.assertEqual({item["targetId"] for item in graph["nodes"] if item["id"].startswith("ref")}, cloned_ids)
            self.assertEqual(next(item for item in graph["nodes"] if item["id"] == "gate")["type"], "all")
        builder_services.update(restored.pk, self.gm.pk, cloned.pk, {"request_id": str(uuid.uuid4()),
            "expected_version": cloned.version, "expected_scene_version": cloned.scene.version})

    def test_composite_conditions_preserve_repeating_chain_rollback_and_receipts(self):
        for row in self.doc["decorations"][1:]:
            row["torch"]["state"] = "on"
            row["blueprint"]["graphs"] = {}
        definition = self.doc["decorations"][0]["blueprint"]
        graph = definition["graphs"]["signal:EvaluatePuzzle"]
        next(item for item in graph["nodes"] if item["id"] == "destination")["targetId"] = self.torch_ids[0]
        next(item for item in graph["nodes"] if item["id"] == "open")["targetState"] = "off"
        next(item for item in graph["nodes"] if item["id"] == "close")["targetState"] = "on"
        graph["nodes"].append(node("repeat", "emitEvent", scope="element", name="EvaluatePuzzle"))
        graph["edges"].extend([execution("open", "repeat"), execution("close", "repeat")])
        self.generated()
        before = {str(row.pk): deepcopy(row.data) for row in self.scene.elements.all()}
        count = Receipt.objects.count()
        with self.assertRaisesMessage(MapError, "repeating chain"):
            self.turn(0)
        self.assertEqual({str(row.pk): row.data for row in self.scene.elements.all()}, before)
        self.assertEqual(Receipt.objects.count(), count)
        self.assertTrue(AutomationRun.objects.filter(scene=self.scene, outcome="failed").exists())
