"""Sequence, Change Sprite and typed data nodes in version 2 door blueprints."""

from copy import deepcopy
import uuid

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.maps import builder_services, objects
from gravewright.maps.assets import visible_door_art
from gravewright.maps.blueprint_runtime import detach_scene_art
from gravewright.maps.blueprints import clean_blueprint, convert_blueprint, default_blueprint, evaluate_graph
from gravewright.maps.services import MapError

from . import test_builder_blueprints as fixtures


def execution(origin, target, output="next"):
    return {"from": origin, "to": target, "output": output, "kind": "execution"}


def data(origin, output, target, port):
    return {"from": origin, "to": target, "output": output, "input": port, "kind": "data"}


def node(identifier, kind, **fields):
    return {"id": identifier, "type": kind, "x": 0, "y": 0, **fields}


def blueprint(event, nodes, edges):
    result = default_blueprint()
    result["version"] = 2
    result["graphs"][event] = {"nodes": [node("event", "event", event=event), *nodes], "edges": edges}
    return result


class DataNodeValidationTests(SimpleTestCase):
    def setUp(self):
        self.asset = str(uuid.uuid4())

    def test_sequence_runs_numbered_outputs_in_order_and_each_branch_depth_first(self):
        raw = blueprint("interact", [
            node("sequence", "sequence"),
            node("first", "state", targetState="closed"),
            node("nested", "state", targetState="locked"),
            node("second", "state", targetState="open"),
        ], [execution("event", "sequence"), execution("sequence", "second", "then2"),
            execution("sequence", "first", "then1"), execution("first", "nested")])
        result = evaluate_graph(clean_blueprint(raw), "interact", "open")
        self.assertEqual(result["trace"], ["event", "sequence", "first", "nested", "second"])
        self.assertEqual([action["id"] for action in result["actions"]], ["first", "nested", "second"])
        for output in ("next", "then5", "true"):
            invalid = deepcopy(raw)
            invalid["graphs"]["interact"]["edges"][1]["output"] = output
            with self.subTest(output=output), self.assertRaisesMessage(MapError, "output"):
                clean_blueprint(invalid)

    def test_version_one_keeps_its_original_node_vocabulary(self):
        for kind, fields in (("sequence", {}), ("sprite", {"appearance": "hidden"}),
                             ("property", {"property": "state"}), ("compare", {"state": "open"})):
            raw = default_blueprint()
            raw["version"] = 1
            raw["graphs"]["interact"] = {"nodes": [node("event", "event", event="interact"),
                                                     node("new", kind, **fields)], "edges": []}
            with self.subTest(kind=kind), self.assertRaisesMessage(MapError, "node type"):
                clean_blueprint(raw)

    def test_change_sprite_validates_appearance_and_owned_image(self):
        valid = blueprint("interact", [node("art", "sprite", appearance="asset", assetId=self.asset.upper())],
                          [execution("event", "art")])
        cleaned = clean_blueprint(valid, asset_ids={self.asset})
        self.assertEqual(cleaned["graphs"]["interact"]["nodes"][1]["assetId"], self.asset)
        for fields in ({"appearance": "asset"}, {"appearance": "hidden", "assetId": self.asset},
                       {"appearance": "glow"}, {"appearance": "asset", "assetId": str(uuid.uuid4())}):
            raw = blueprint("interact", [node("art", "sprite", **fields)], [])
            with self.subTest(fields=fields), self.assertRaises(MapError):
                clean_blueprint(raw, asset_ids={self.asset})

    def graph_with_data(self):
        return blueprint("interact", [
            node("previous", "property", property="previous"),
            node("compare", "compare", state="locked"),
            node("check", "condition", state="open"),
            node("unlocked", "state", targetState="open"),
            node("closed", "state", targetState="locked"),
        ], [execution("event", "check"), execution("check", "unlocked", "true"),
            execution("check", "closed", "false"),
            data("previous", "value", "compare", "value"), data("compare", "result", "check", "test")])

    def test_condition_reads_typed_boolean_from_previous_state_comparison(self):
        raw = clean_blueprint(self.graph_with_data())
        unlocked = evaluate_graph(raw, "interact", "closed", "locked")
        self.assertEqual(unlocked["trace"], ["event", "check", "previous", "compare", "unlocked"])
        self.assertEqual(evaluate_graph(raw, "interact", "closed", "open")["actions"][0]["id"], "closed")
        # Without a transition the previous state is the current one.
        self.assertEqual(evaluate_graph(raw, "interact", "closed")["actions"][0]["id"], "closed")
        unconnected = deepcopy(raw)
        unconnected["graphs"]["interact"]["edges"] = unconnected["graphs"]["interact"]["edges"][:3]
        result = evaluate_graph(unconnected, "interact", "closed", "locked")
        self.assertEqual(result["trace"], ["event", "check", "closed"], "the state parameter applies without an input")

    def test_compare_without_input_reads_the_current_state(self):
        raw = blueprint("interact", [node("compare", "compare", state="locked"),
                                            node("check", "condition", state="open"),
                                            node("open", "state", targetState="open")],
                        [execution("event", "check"), execution("check", "open", "true"),
                         data("compare", "result", "check", "test")])
        self.assertEqual(evaluate_graph(raw, "interact", "locked")["actions"][0]["id"], "open")

    def test_data_edges_require_matching_types_one_source_per_input_and_no_execution_ports(self):
        valid = self.graph_with_data()
        clean_blueprint(valid)
        variants = {
            "type mismatch": data("previous", "value", "check", "test"),
            "unknown input": data("previous", "value", "compare", "other"),
            "execution source": data("check", "true", "compare", "value"),
            "duplicate input": data("previous", "value", "compare", "value"),
        }
        for name, edge in variants.items():
            raw = deepcopy(valid)
            edges = raw["graphs"]["interact"]["edges"]
            if name == "duplicate input":
                raw["graphs"]["interact"]["nodes"].append(node("again", "property", property="state"))
                edge = {**edge, "from": "again"}
            else:
                edges.pop(3 if name != "type mismatch" else 4)
            edges.append(edge)
            with self.subTest(name=name), self.assertRaises(MapError):
                clean_blueprint(raw)
        for edge in (execution("event", "previous"), execution("previous", "unlocked"),
                     {**data("previous", "value", "compare", "value"), "kind": "execution"},
                     {key: value for key, value in data("previous", "value", "compare", "value").items() if key != "input"}):
            raw = deepcopy(valid)
            raw["graphs"]["interact"]["edges"] = [*raw["graphs"]["interact"]["edges"][:3], edge]
            with self.subTest(edge=edge), self.assertRaises(MapError):
                clean_blueprint(raw)
        cleaned = clean_blueprint(valid)
        self.assertEqual(cleaned["graphs"]["interact"]["edges"][3], data("previous", "value", "compare", "value"))

    def test_conversion_preserves_current_data_graph_without_mutating_input(self):
        raw = self.graph_with_data()
        before = deepcopy(raw)
        self.assertEqual(convert_blueprint(raw), clean_blueprint(raw))
        self.assertEqual(raw, before)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class ChangeSpriteRuntimeTests(TestCase):
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
        current = default_blueprint()
        current["states"] = deepcopy(self.doc["doors"][0]["blueprint"]["states"])
        self.sprite = {"appearance": "asset", "assetId": str(self.alternate.pk)}
        current["graphs"]["interact"] = {
            "nodes": [node("event", "event", event="interact"), node("art", "sprite", **self.sprite)],
            "edges": [execution("event", "art")]}
        self.doc["doors"][0]["blueprint"] = clean_blueprint(current)

    def native_door(self):
        self.door_object.refresh_from_db()
        return self.door_object

    def test_explicit_sprite_survives_state_edits_until_another_visual_action_and_stays_private(self):
        self.generated()
        version = self.native_door().version
        result = self.command("closed")
        door = self.native_door()
        self.assertEqual(door.data["door_state"], "closed")
        self.assertEqual(door.data["sprite"], self.sprite)
        self.assertEqual(door.version, version + 1)
        self.assertEqual(result["blueprint"]["trace"], [{"event": "interact", "nodes": ["event", "art"]}])
        public = objects.door_presentation(objects.entry(door))
        self.assertNotIn("sprite", public)
        self.assertNotIn("blueprint", public)
        self.assertEqual(public["blueprintAppearance"], {"visible": True, "assetId": str(self.alternate.pk)})
        self.assertEqual(visible_door_art(self.scene.pk, self.alternate.pk), {str(self.alternate.pk)})

        # A GM edit keeps the live appearance; an authored payload cannot set one.
        self.command("closed", action="update", version=door.version, presentation="normal")
        self.assertEqual(self.native_door().data["sprite"], self.sprite)
        forged = objects.wall({**deepcopy(door.data), "sprite": {"appearance": "hidden"}},
                              campaign_id=self.campaign.pk, scene_id=self.scene.pk)
        self.assertNotIn("sprite", forged)

        # Scene updates treat the live appearance like the live door state.
        self.update_scene()
        self.assertEqual(self.native_door().data["sprite"], self.sprite)

        self.command("open", action="update", version=self.native_door().version)
        door = self.native_door()
        self.assertEqual(door.data["door_state"], "open")
        self.assertEqual(door.data["sprite"], self.sprite, "state edits do not reset an explicit visual action")
        self.assertEqual(objects.door_presentation(objects.entry(door))["blueprintAppearance"]["assetId"],
                         str(self.alternate.pk))
        door.data["blueprint"]["graphs"]["interact"]["nodes"][1] = node("art", "sprite", appearance="hidden")
        door.save(update_fields=["data"])
        self.command("closed")
        door = self.native_door()
        self.assertEqual(door.data["door_state"], "open", "the event does not choose the requested state")
        self.assertEqual(door.data["sprite"], {"appearance": "hidden"})
        self.assertEqual(objects.door_presentation(objects.entry(door))["blueprintAppearance"],
                         {"visible": False, "assetId": None})

    def test_deleting_the_sprite_image_clears_live_and_authored_references(self):
        self.generated()
        self.command("closed")
        scenes = detach_scene_art(self.campaign.pk, self.alternate.pk)
        builder_services.detach_project_art(self.campaign.pk, self.alternate.pk)
        self.assertIn(self.scene.pk, scenes)
        door = self.native_door()
        self.assertNotIn("sprite", door.data)
        art = door.data["blueprint"]["graphs"]["interact"]["nodes"][1]
        self.assertEqual(art, node("art", "sprite", appearance="inherit"))
        self.assertEqual(door.data["blueprint"]["states"]["open"], {"appearance": "inherit"})
