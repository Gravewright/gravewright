"""Authored intelligent-object graphs are bounded, isolated data."""

from copy import deepcopy
from uuid import uuid4

from django.test import SimpleTestCase

from gravewright.maps.blueprints import (
    DOOR_EVENTS, clean_blueprint, convert_blueprint, default_blueprint, evaluate_graph,
)
from gravewright.maps.services import MapError


def event_graph(event="interact", *actions):
    nodes = [{"id": "event", "type": "event", "event": event, "x": 0, "y": 0}]
    nodes.extend({"x": 240 * (index + 1), "y": 0, **action} for index, action in enumerate(actions))
    edges = [
        {"from": nodes[index]["id"], "to": nodes[index + 1]["id"], "output": "next", "kind": "execution"}
        for index in range(len(nodes) - 1)
    ]
    return {"nodes": nodes, "edges": edges}


class BlueprintValidationTests(SimpleTestCase):
    def setUp(self):
        self.asset = str(uuid4())
        self.light = str(uuid4())
        self.track = str(uuid4())
        self.blueprint = default_blueprint()

    def clean(self, blueprint=None, **kwargs):
        return clean_blueprint(
            blueprint or self.blueprint,
            asset_ids={self.asset}, light_ids={self.light}, track_ids={self.track},
            **kwargs,
        )

    def test_default_graph_preserves_native_state_appearance_and_is_independent(self):
        first = default_blueprint()
        second = default_blueprint()
        self.assertEqual(clean_blueprint(first), second)
        first["states"]["open"]["appearance"] = "hidden"
        self.assertEqual(second["states"]["open"]["appearance"], "inherit")
        self.assertEqual(evaluate_graph(second, "interact", "open"), {"trace": [], "actions": []})

    def test_cleaner_copies_author_data_and_normalizes_layout(self):
        self.blueprint["states"]["open"] = {"appearance": "asset", "assetId": self.asset.upper()}
        self.blueprint["graphs"]["interact"] = event_graph()
        self.blueprint["graphs"]["interact"]["nodes"][0]["x"] = 1.23456
        original = deepcopy(self.blueprint)
        result = self.clean()
        self.assertEqual(self.blueprint, original)
        self.assertEqual(result["states"]["open"]["assetId"], self.asset)
        self.assertEqual(result["graphs"]["interact"]["nodes"][0]["x"], 1.235)
        result["states"]["open"]["appearance"] = "hidden"
        self.assertEqual(self.blueprint["states"]["open"]["appearance"], "asset")

    def test_unknown_or_incomplete_document_contract_is_rejected(self):
        variants = [None, [], {}, {**self.blueprint, "version": True},
                    {**self.blueprint, "version": 1.0}, {**self.blueprint, "version": 3},
                    {**self.blueprint, "kind": "system-door"}, {**self.blueprint, "script": "run()"}]
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises(MapError):
                clean_blueprint(raw)

    def test_all_native_door_states_are_required_and_only_supported_states_allowed(self):
        for state in ("closed", "open", "locked"):
            raw = deepcopy(self.blueprint)
            del raw["states"][state]
            with self.subTest(state=state), self.assertRaises(MapError):
                self.clean(raw)
        self.blueprint["states"]["destroyed"] = {"appearance": "hidden"}
        with self.assertRaises(MapError):
            self.clean()

    def test_appearance_reference_requires_asset_mode_and_owned_asset(self):
        for entry in ({"appearance": "asset"}, {"appearance": "asset", "assetId": "invalid"},
                      {"appearance": "asset", "assetId": str(uuid4())},
                      {"appearance": "hidden", "assetId": self.asset},
                      {"appearance": "inherit", "script": "x"}, {"appearance": "other"}):
            self.blueprint["states"]["open"] = entry
            with self.subTest(entry=entry), self.assertRaises(MapError):
                self.clean()

    def test_typed_owned_actions_and_base_events_are_accepted(self):
        for event in DOOR_EVENTS:
            self.blueprint["graphs"][event] = event_graph(
                event,
                {"id": "light", "type": "light", "targetId": self.light, "enabled": True},
                {"id": "sound", "type": "sound", "trackId": self.track, "volume": 0.5},
                {"id": "state", "type": "state", "targetState": "closed"},
            )
        self.assertEqual(set(self.clean()["graphs"]), {"interact", "destroy"})

    def test_resource_ownership_is_optional_only_when_not_supplied(self):
        self.blueprint["graphs"]["interact"] = event_graph(
            "interact", {"id": "light", "type": "light", "targetId": self.light, "enabled": True}
        )
        self.assertEqual(clean_blueprint(self.blueprint), self.blueprint)
        self.assertEqual(clean_blueprint(self.blueprint, light_ids={__import__("uuid").UUID(self.light)}), self.blueprint)
        with self.assertRaisesMessage(MapError, "light not found"):
            clean_blueprint(self.blueprint, light_ids=set())

    def test_invalid_action_fields_and_values_are_rejected(self):
        actions = [
            {"id": "a", "type": "light", "targetId": self.light, "enabled": 1},
            {"id": "a", "type": "light", "targetId": str(uuid4()), "enabled": False},
            {"id": "a", "type": "sound", "trackId": self.track, "volume": True},
            {"id": "a", "type": "sound", "trackId": self.track, "volume": -0.1},
            {"id": "a", "type": "sound", "trackId": self.track, "volume": 1.1},
            {"id": "a", "type": "sound", "trackId": str(uuid4()), "volume": 0.5},
            {"id": "a", "type": "state", "targetState": "destroyed"},
            {"id": "a", "type": "condition", "state": "destroyed"},
            {"id": "a", "type": "script", "source": "alert(1)"},
            {"id": "a", "type": "state", "targetState": "open", "script": "x"},
        ]
        for action in actions:
            self.blueprint["graphs"]["interact"] = event_graph("interact", action)
            with self.subTest(action=action), self.assertRaises(MapError):
                self.clean()

    def test_node_ids_and_positions_are_bounded(self):
        node = event_graph()["nodes"][0]
        for field, value in (("id", ""), ("id", "0start"), ("id", "a" * 65), ("id", "<script>"),
                             ("x", True), ("x", -1), ("x", 5001), ("x", float("nan")),
                             ("y", float("inf")), ("y", 10 ** 1000), ("x", "5")):
            graph = {"nodes": [{**node, field: value}], "edges": []}
            self.blueprint["graphs"]["interact"] = graph
            with self.subTest(field=field, value=str(value)[:20]), self.assertRaises(MapError):
                self.clean()

    def test_graph_requires_matching_single_event(self):
        for graph in (
            {"nodes": [], "edges": []},
            event_graph("destroy"),
            {"nodes": [{"id": "state", "type": "state", "targetState": "open", "x": 0, "y": 0}], "edges": []},
            {"nodes": [*event_graph()["nodes"], {**event_graph()["nodes"][0], "id": "other"}], "edges": []},
        ):
            self.blueprint["graphs"]["interact"] = graph
            with self.subTest(graph=graph), self.assertRaises(MapError):
                self.clean()
        self.blueprint["graphs"] = {"tick:open": event_graph("tick:open")}
        with self.assertRaises(MapError):
            self.clean()

    def test_graph_rejects_duplicate_ids_and_dangling_or_invalid_connections(self):
        graph = event_graph("interact", {"id": "a", "type": "state", "targetState": "closed"})
        variants = [
            {"kind": "execution", "from": "missing", "to": "a", "output": "next"},
            {"kind": "execution", "from": "event", "to": "missing", "output": "next"},
            {"kind": "execution", "from": "event", "to": "a", "output": "true"},
            {"kind": "execution", "from": "a", "to": "event", "output": "next"},
            {"kind": "execution", "from": "event", "to": "a", "output": "next", "script": "x"},
            {"from": "event", "to": "a", "output": "next"},
            {"from": "event", "to": "a"},
        ]
        for edge in variants:
            self.blueprint["graphs"]["interact"] = {**graph, "edges": [edge]}
            with self.subTest(edge=edge), self.assertRaises(MapError):
                self.clean()
        self.blueprint["graphs"]["interact"] = {
            "nodes": [graph["nodes"][0], {**graph["nodes"][1], "id": "event"}], "edges": []
        }
        with self.assertRaisesMessage(MapError, "Duplicate"):
            self.clean()

    def test_duplicate_connections_are_rejected_but_both_condition_branches_are_allowed(self):
        graph = event_graph("interact", {"id": "a", "type": "state", "targetState": "closed"})
        graph["edges"].append(deepcopy(graph["edges"][0]))
        self.blueprint["graphs"]["interact"] = graph
        with self.assertRaisesMessage(MapError, "Duplicate blueprint connection"):
            self.clean()

        graph = event_graph("interact", {"id": "condition", "type": "condition", "state": "open"})
        graph["nodes"].append({"id": "a", "type": "state", "targetState": "closed", "x": 500, "y": 0})
        graph["edges"].extend([
            {"kind": "execution", "from": "condition", "to": "a", "output": "true"},
            {"kind": "execution", "from": "condition", "to": "a", "output": "false"},
        ])
        self.blueprint["graphs"]["interact"] = graph
        self.assertEqual(self.clean(), self.blueprint)

    def test_cycles_in_reachable_or_disconnected_nodes_are_rejected(self):
        graph = event_graph(
            "interact", {"id": "a", "type": "state", "targetState": "open"},
            {"id": "b", "type": "state", "targetState": "closed"},
        )
        graph["edges"].append({"kind": "execution", "from": "b", "to": "a", "output": "next"})
        for edges in (graph["edges"], graph["edges"][1:]):
            self.blueprint["graphs"]["interact"] = {**graph, "edges": edges}
            with self.subTest(edges=edges), self.assertRaisesMessage(MapError, "cycle"):
                self.clean()

    def test_graph_and_blueprint_node_limits_are_bounded(self):
        graph = event_graph()
        graph["nodes"].extend({"id": f"n{i}", "type": "state", "targetState": "open", "x": 0, "y": 0} for i in range(31))
        self.blueprint["graphs"]["interact"] = graph
        self.clean()
        graph["nodes"].append({"id": "extra", "type": "state", "targetState": "open", "x": 0, "y": 0})
        with self.assertRaisesMessage(MapError, "graph limit"):
            self.clean()
        graph["nodes"].pop()
        self.blueprint["graphs"] = {
            event: {"nodes": [{**node, **({"event": event} if node["type"] == "event" else {})} for node in graph["nodes"]], "edges": []}
            for event in (f"signal:Limit{i}" for i in range(4))
        }
        self.assertEqual(sum(len(entry["nodes"]) for entry in self.clean()["graphs"].values()), 128)
        self.blueprint["graphs"]["signal:Overflow"] = event_graph("signal:Overflow")
        with self.assertRaisesMessage(MapError, "node limit"):
            self.clean()


class BlueprintEvaluationTests(SimpleTestCase):
    def setUp(self):
        self.light = str(uuid4())
        self.track = str(uuid4())
        self.blueprint = default_blueprint()

    def test_action_order_and_trace_follow_connections_not_authored_array_order(self):
        graph = event_graph(
            "interact", {"id": "sound", "type": "sound", "trackId": self.track, "volume": 0.7},
            {"id": "light", "type": "light", "targetId": self.light, "enabled": True},
        )
        graph["nodes"] = list(reversed(graph["nodes"]))
        self.blueprint["graphs"]["interact"] = graph
        before = deepcopy(self.blueprint)
        result = evaluate_graph(self.blueprint, "interact", "open")
        self.assertEqual(result["trace"], ["event", "sound", "light"])
        self.assertEqual([action["type"] for action in result["actions"]], ["sound", "light"])
        self.assertEqual(self.blueprint, before)
        result["actions"][0]["volume"] = 0
        self.assertEqual(self.blueprint, before)

    def test_only_matching_condition_branch_executes(self):
        graph = event_graph("interact", {"id": "condition", "type": "condition", "state": "locked"})
        graph["nodes"].extend([
            {"id": "sound", "type": "sound", "trackId": self.track, "volume": 1, "x": 500, "y": 0},
            {"id": "light", "type": "light", "targetId": self.light, "enabled": False, "x": 500, "y": 200},
        ])
        graph["edges"].extend([
            {"kind": "execution", "from": "condition", "to": "sound", "output": "true"},
            {"kind": "execution", "from": "condition", "to": "light", "output": "false"},
        ])
        self.blueprint["graphs"]["interact"] = graph
        for current, branch in (("locked", "sound"), ("closed", "light")):
            with self.subTest(current=current):
                result = evaluate_graph(self.blueprint, "interact", current)
                self.assertEqual(result["trace"], ["event", "condition", branch])
                self.assertEqual([action["id"] for action in result["actions"]], [branch])

    def test_disconnected_nodes_and_unconnected_condition_outputs_do_not_execute(self):
        graph = event_graph("interact", {"id": "condition", "type": "condition", "state": "closed"})
        graph["nodes"].append({"id": "unused", "type": "light", "targetId": self.light, "enabled": True, "x": 500, "y": 0})
        self.blueprint["graphs"]["interact"] = graph
        result = evaluate_graph(self.blueprint, "interact", "open")
        self.assertEqual(result, {"trace": ["event", "condition"], "actions": [],
                                  "values": {}, "decisions": {"condition": False}})

    def test_state_action_is_returned_and_conditions_observe_event_initial_state(self):
        graph = event_graph(
            "interact", {"id": "state", "type": "state", "targetState": "closed"},
            {"id": "condition", "type": "condition", "state": "open"},
        )
        graph["nodes"].append({"id": "sound", "type": "sound", "trackId": self.track, "volume": 1, "x": 700, "y": 0})
        graph["edges"].append({"kind": "execution", "from": "condition", "to": "sound", "output": "true"})
        self.blueprint["graphs"]["interact"] = graph
        result = evaluate_graph(self.blueprint, "interact", "open")
        self.assertEqual(result["trace"], ["event", "state", "condition", "sound"])
        self.assertEqual([action["type"] for action in result["actions"]], ["state", "sound"])

    def test_invalid_evaluation_context_and_malformed_input_fail_closed(self):
        for event, state in (("tick:open", "open"), ("interact", "destroyed"), (None, "open")):
            with self.subTest(event=event, state=state), self.assertRaises(MapError):
                evaluate_graph(self.blueprint, event, state)
        self.blueprint["graphs"]["interact"] = event_graph("destroy")
        with self.assertRaises(MapError):
            evaluate_graph(self.blueprint, "interact", "open")


class BlueprintExecutionConnectionTests(SimpleTestCase):
    def setUp(self):
        self.track = str(uuid4())
        self.light = str(uuid4())
        self.legacy = default_blueprint()
        self.legacy["version"] = 1
        self.legacy["graphs"]["interact"] = event_graph(
            "interact",
            {"id": "sound", "type": "sound", "trackId": self.track, "volume": 0.7},
            {"id": "light", "type": "light", "targetId": self.light, "enabled": True},
        )
        for edge in self.legacy["graphs"]["interact"]["edges"]:
            edge.pop("kind")

    def branch_graph(self):
        blueprint = convert_blueprint(self.legacy)
        graph = blueprint["graphs"]["interact"]
        graph["edges"] = [
            {"kind": "execution", "from": "event", "to": "sound", "output": "next"},
            {"kind": "execution", "from": "event", "to": "light", "output": "next"},
        ]
        return blueprint, graph

    def test_historical_format_normalizes_surviving_event_without_mutating_input(self):
        before = deepcopy(self.legacy)
        converted = convert_blueprint(
            self.legacy, asset_ids=set(), light_ids={self.light}, track_ids={self.track}
        )
        self.assertEqual(self.legacy, before)
        self.assertEqual(clean_blueprint(self.legacy), converted)
        self.assertEqual(converted["version"], 2)
        self.assertEqual(converted["states"], before["states"])
        graph = converted["graphs"]["interact"]
        self.assertEqual(graph["nodes"], before["graphs"]["interact"]["nodes"])
        self.assertTrue(all(edge["kind"] == "execution" for edge in graph["edges"]))
        self.assertEqual(
            evaluate_graph(converted, "interact", "open"),
            evaluate_graph(before, "interact", "open"),
        )
        converted["graphs"]["interact"]["nodes"][1]["volume"] = 0
        self.assertEqual(self.legacy, before)

    def test_current_conversion_is_independent_and_resource_checks_are_retained(self):
        current = convert_blueprint(self.legacy)
        copied = convert_blueprint(current)
        self.assertEqual(copied, current)
        copied["graphs"]["interact"]["edges"].clear()
        self.assertEqual(len(current["graphs"]["interact"]["edges"]), 2)
        with self.assertRaisesMessage(MapError, "sound not found"):
            convert_blueprint(self.legacy, track_ids=set())
        for version in (1, 3, True, 2.0):
            with self.subTest(version=version), self.assertRaisesMessage(MapError, "conversion"):
                convert_blueprint(current, version=version)

    def test_current_edges_require_execution_kind_and_legacy_edges_remain_untyped(self):
        current, graph = self.branch_graph()
        for kind in (None, "data", "reference", 1, [], {}):
            invalid = deepcopy(current)
            edge = invalid["graphs"]["interact"]["edges"][0]
            if kind is None:
                del edge["kind"]
            else:
                edge["kind"] = kind
            with self.subTest(kind=kind), self.assertRaises(MapError):
                clean_blueprint(invalid)
        graph["edges"][0]["kind"] = "execution"
        self.assertEqual(clean_blueprint(current), current)
        self.legacy["graphs"]["interact"]["edges"][0]["kind"] = "execution"
        with self.assertRaisesMessage(MapError, "Unknown"):
            clean_blueprint(self.legacy)

    def test_current_fanout_preserves_edge_order_and_legacy_fanout_is_rejected(self):
        current, graph = self.branch_graph()
        graph["nodes"] = list(reversed(graph["nodes"]))
        self.assertEqual(clean_blueprint(current), current)
        self.assertEqual(evaluate_graph(current, "interact", "open")["trace"],
                         ["event", "sound", "light"])
        graph["edges"].reverse()
        self.assertEqual(evaluate_graph(current, "interact", "open")["trace"],
                         ["event", "light", "sound"])
        legacy = deepcopy(current)
        legacy["version"] = 1
        for edge in legacy["graphs"]["interact"]["edges"]:
            del edge["kind"]
        with self.assertRaisesMessage(MapError, "one blueprint connection"):
            clean_blueprint(legacy)

    def test_current_duplicate_edges_and_cycles_remain_invalid(self):
        current, graph = self.branch_graph()
        graph["edges"].append(deepcopy(graph["edges"][0]))
        with self.assertRaisesMessage(MapError, "Duplicate blueprint connection"):
            clean_blueprint(current)
        graph["edges"].pop()
        graph["edges"].extend([
            {"kind": "execution", "from": "sound", "to": "light", "output": "next"},
            {"kind": "execution", "from": "light", "to": "sound", "output": "next"},
        ])
        with self.assertRaisesMessage(MapError, "cycle"):
            clean_blueprint(current)
        del graph["edges"][:2]
        with self.assertRaisesMessage(MapError, "cycle"):
            clean_blueprint(current)

    def test_fanout_executes_depth_first_and_shared_descendant_only_once(self):
        current, graph = self.branch_graph()
        graph["nodes"].append({"id": "shared", "type": "sound", "trackId": self.track,
                               "volume": 0.2, "x": 800, "y": 200})
        graph["edges"].extend([
            {"kind": "execution", "from": "sound", "to": "shared", "output": "next"},
            {"kind": "execution", "from": "light", "to": "shared", "output": "next"},
        ])
        before = deepcopy(current)
        result = evaluate_graph(current, "interact", "open")
        self.assertEqual(result["trace"], ["event", "sound", "shared", "light"])
        self.assertEqual([node["id"] for node in result["actions"]], ["sound", "shared", "light"])
        self.assertEqual(current, before)
        result["actions"][0]["volume"] = 0
        self.assertEqual(current, before)

    def test_each_condition_output_can_fanout_but_only_matching_branch_runs(self):
        current, graph = self.branch_graph()
        graph["nodes"].extend([
            {"id": "check", "type": "condition", "state": "open", "x": 200, "y": 0},
            {"id": "other", "type": "state", "targetState": "open", "x": 500, "y": 400},
        ])
        graph["edges"] = [
            {"kind": "execution", "from": "event", "to": "check", "output": "next"},
            {"kind": "execution", "from": "check", "to": "sound", "output": "true"},
            {"kind": "execution", "from": "check", "to": "light", "output": "true"},
            {"kind": "execution", "from": "check", "to": "other", "output": "false"},
        ]
        self.assertEqual(evaluate_graph(current, "interact", "open")["trace"],
                         ["event", "check", "sound", "light"])
        self.assertEqual(evaluate_graph(current, "interact", "closed")["trace"],
                         ["event", "check", "other"])

    def test_current_graph_remains_bounded_and_rejects_incoming_event_connections(self):
        current, graph = self.branch_graph()
        graph["edges"].append(
            {"kind": "execution", "from": "sound", "to": "event", "output": "next"}
        )
        with self.assertRaisesMessage(MapError, "events cannot have incoming"):
            clean_blueprint(current)
        graph["edges"] = [deepcopy(graph["edges"][0]) for _ in range(65)]
        with self.assertRaisesMessage(MapError, "graph limit"):
            clean_blueprint(current)
