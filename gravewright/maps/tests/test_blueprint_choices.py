"""Typed branching and private retry-stable random choices stay transaction-owned."""

from copy import deepcopy
import json
from unittest.mock import patch
import uuid

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.campaigns.models import Membership
from gravewright.maps import blueprint_runtime, objects
from gravewright.maps.blueprints import clean_blueprint, evaluate_graph, execution_outputs
from gravewright.maps.models import AutomationDelay, AutomationRun, Receipt, SceneObject
from gravewright.maps.services import MapError

from . import test_blueprint_delays as delays
from . import test_builder_blueprints as fixtures
from . import test_regions as region_fixtures
from .test_blueprint_references import blueprint, data, execution, node


EVENT = "interact"


def choice(kind="switch", **parameters):
    defaults = ({"valueType": "number", "value": 1, "cases": [{"id": "case1", "value": 1}, {"id": "case2", "value": 2}]}
                if kind == "switch" else {"weights": [1, 1]})
    return node("choice", kind, **{**defaults, **parameters})


def branching(selected=None, *, event=EVENT):
    selected = selected or choice()
    ports = execution_outputs(selected)
    return blueprint({event: ([selected, *[node(port, "setVariable", scope="element", name="Selected",
        valueType="text", value=port) for port in ports]], [execution("event", "choice"),
        *[execution("choice", port, port) for port in ports]])})


class ChoiceContractTests(SimpleTestCase):
    def test_nested_request_context_preserves_root_ordinals_and_restores_other_requests(self):
        from gravewright.maps.blueprint_delays import automation_request, current_request_id, next_chain_ordinal
        request_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        with automation_request(request_id):
            self.assertEqual(next_chain_ordinal(), 0)
            with automation_request(str(request_id)):
                self.assertEqual(current_request_id(), request_id)
                self.assertEqual(next_chain_ordinal(), 1)
            self.assertEqual(next_chain_ordinal(), 2)
            with automation_request(uuid.UUID("00000000-0000-0000-0000-000000000002")):
                self.assertEqual(next_chain_ordinal(), 0)
            self.assertEqual(current_request_id(), request_id)
            self.assertEqual(next_chain_ordinal(), 3)
        with automation_request(request_id):
            self.assertEqual(next_chain_ordinal(), 0)

    def test_switch_uses_only_the_matching_typed_case_or_default(self):
        for value, output in ((1, "case1"), (2, "case2"), (3, "default")):
            raw = branching(choice(value=value))
            result = evaluate_graph(raw, EVENT, "closed")
            self.assertEqual(result["decisions"]["choice"], output)
            self.assertEqual(result["actions"][0]["value"], output)
        for kind, values in (("boolean", [False, True]), ("text", ["", "1"]), ("number", [0, 1])):
            for value in values:
                raw = branching(choice(valueType=kind, value=value,
                    cases=[{"id": "case4", "value": values[0]}, {"id": "case2", "value": values[1]}]))
                self.assertEqual(evaluate_graph(raw, EVENT, "closed")["decisions"]["choice"],
                                 "case4" if value == values[0] else "case2")

    def test_switch_data_input_replaces_fallback_and_connections_are_typed(self):
        raw = branching()
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("read", "getVariable", scope="scene", name="Stage", valueType="number", default=2))
        graph["edges"].append(data("read", "value", "choice", "value"))
        self.assertEqual(evaluate_graph(raw, EVENT, "closed")["decisions"]["choice"], "case2")
        result = evaluate_graph(raw, EVENT, "closed", variables={"scene": {"Stage": {"type": "number", "value": 7}}})
        self.assertEqual(result["decisions"]["choice"], "default")
        graph["nodes"][-1].update(valueType="boolean", default=True)
        with self.assertRaisesMessage(MapError, "connection input"):
            clean_blueprint(raw)

    def test_switch_fields_cases_ids_values_and_outputs_are_strict(self):
        invalid = [[], [None], [{"id": "case1", "value": 1, "extra": 2}],
            [{"id": "case1", "value": 1}, {"id": "case1", "value": 2}],
            [{"id": "case1", "value": 0}, {"id": "case2", "value": -0.0}],
            [{"id": "case1", "value": True}], [{"id": "case1", "value": "1"}],
            [{"id": "case5", "value": 1}], [{"id": "case1\n", "value": 1}],
            [{"id": f"case{index + 1}", "value": index} for index in range(5)]]
        for cases in invalid:
            raw = blueprint({EVENT: ([choice(cases=cases)], [execution("event", "choice")])})
            with self.subTest(cases=cases), self.assertRaises(MapError):
                clean_blueprint(raw)
        for value in (True, "1", None, 1_000_001, float("nan")):
            raw = blueprint({EVENT: ([choice(value=value)], [])})
            with self.subTest(value=value), self.assertRaises(MapError):
                clean_blueprint(raw)
        raw = branching()
        raw["graphs"][EVENT]["edges"][1]["output"] = "case3"
        with self.assertRaisesMessage(MapError, "connection output"):
            clean_blueprint(raw)

    def test_boolean_cases_cannot_exceed_two_and_authored_order_is_preserved(self):
        raw = branching(choice(valueType="boolean", value=False,
            cases=[{"id": "case4", "value": True}, {"id": "case1", "value": False}]))
        self.assertEqual(execution_outputs(clean_blueprint(raw)["graphs"][EVENT]["nodes"][1]),
                         ("case4", "case1", "default"))
        raw["graphs"][EVENT]["nodes"][1]["cases"].append({"id": "case2", "value": True})
        with self.assertRaises(MapError):
            clean_blueprint(raw)

    def test_random_weighted_boundaries_and_zero_branches(self):
        raw = branching(choice("random", weights=[0, 2, 3, 0]))
        for draw, expected in ((0, "branch2"), (1, "branch2"), (2, "branch3"), (4, "branch3")):
            calls = []
            def generate(identifier, total):
                calls.append((identifier, total))
                return draw
            result = evaluate_graph(raw, EVENT, "closed", random_draw=generate)
            self.assertEqual(calls, [("choice", 5)])
            self.assertEqual(result["decisions"]["choice"], expected)
            self.assertEqual(result["actions"][0]["value"], expected)
        self.assertEqual(evaluate_graph(raw, EVENT, "closed")["decisions"]["choice"], "branch2")

    def test_random_requires_bounded_integer_weights_and_a_valid_draw(self):
        for weights in (None, [], [1], [1] * 5, [0, 0], [True, 1], [1.5, 1], [-1, 1], [1001, 1], ["1", 1]):
            raw = blueprint({EVENT: ([choice("random", weights=weights)], [])})
            with self.subTest(weights=weights), self.assertRaisesMessage(MapError, "random weights"):
                clean_blueprint(raw)
        raw = branching(choice("random", weights=[1000, 1000, 1000, 1000]))
        self.assertEqual(evaluate_graph(raw, EVENT, "closed", random_draw=lambda *_: 3999)["decisions"]["choice"], "branch4")
        for draw in (-1, 4000, True, 1.5, None, float("nan")):
            with self.subTest(draw=draw), self.assertRaisesMessage(MapError, "random draw"):
                evaluate_graph(raw, EVENT, "closed", random_draw=lambda *_: draw)

    def test_choices_are_v2_only_and_have_no_next_or_data_output(self):
        for selected in (choice(), choice("random")):
            raw = branching(selected)
            raw["version"] = 1
            for graph in raw["graphs"].values():
                for edge in graph["edges"]:
                    edge.pop("kind", None)
            with self.assertRaisesMessage(MapError, "node type"):
                clean_blueprint(raw)
            raw = branching(selected)
            raw["graphs"][EVENT]["edges"][1]["output"] = "next"
            with self.assertRaises(MapError):
                clean_blueprint(raw)

    def test_disconnected_selection_ends_the_branch_without_reroll(self):
        for selected, output in ((choice(value=1), "case1"), (choice("random"), "branch1")):
            raw = branching(selected)
            raw["graphs"][EVENT]["edges"] = [edge for edge in raw["graphs"][EVENT]["edges"] if edge["output"] != output]
            result = evaluate_graph(raw, EVENT, "closed")
            self.assertEqual(result["actions"], [])
            self.assertEqual(result["decisions"]["choice"], output)

    def test_shared_descendants_execute_once_and_drafts_remain_immutable(self):
        raw = branching(choice("random"))
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("shared", "reveal"))
        graph["edges"].extend([execution("choice", "branch2", "branch1"),
            execution("branch1", "shared"), execution("branch2", "shared")])
        before = deepcopy(raw)
        calls = []
        result = evaluate_graph(raw, EVENT, "closed", random_draw=lambda *args: calls.append(args) or 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["trace"].count("shared"), 1)
        self.assertEqual(raw, before)

    def test_delay_preserves_choice_and_never_draws_an_already_visited_random_again(self):
        for selected in (choice(value=2), choice("random")):
            raw = branching(selected)
            graph = raw["graphs"][EVENT]
            graph["nodes"].append(node("wait", "delay", seconds=1))
            graph["edges"] = [execution("event", "choice"), execution("choice", "wait", execution_outputs(selected)[1]),
                              execution("wait", execution_outputs(selected)[1])]
            first = evaluate_graph(raw, EVENT, "closed", random_draw=lambda *_: 1)
            self.assertIn("delay", first)
            checkpoint = deepcopy(first["delay"]["continuation"])
            def forbidden(*_):
                self.fail("An already selected random node was evaluated again")
            final = evaluate_graph(raw, EVENT, "open", continuation=checkpoint, random_draw=forbidden)
            self.assertEqual(final["decisions"]["choice"], execution_outputs(selected)[1])
            self.assertEqual(final["actions"][0]["value"], execution_outputs(selected)[1])
            self.assertEqual(checkpoint, first["delay"]["continuation"])

    def test_delay_before_random_defers_drawing_until_resumption(self):
        raw = branching(choice("random"))
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("wait", "delay", seconds=1))
        graph["edges"][0] = execution("event", "wait")
        graph["edges"].append(execution("wait", "choice"))
        calls = []
        first = evaluate_graph(raw, EVENT, "closed", random_draw=lambda *args: calls.append(args) or 1)
        self.assertEqual(calls, [])
        final = evaluate_graph(raw, EVENT, "closed", continuation=first["delay"]["continuation"],
                               random_draw=lambda *args: calls.append(args) or 1)
        self.assertEqual(calls, [("choice", 2)])
        self.assertEqual(final["actions"][0]["value"], "branch2")

    def test_forged_continuation_decisions_are_rejected(self):
        for selected, invalid in ((choice(), [True, "case3", "next", "default\n"]),
                                  (choice("random", weights=[0, 1]), [False, "branch1", "branch3", "case1"])):
            raw = branching(selected)
            graph = raw["graphs"][EVENT]
            graph["nodes"].append(node("wait", "delay", seconds=1))
            graph["edges"] = [execution("event", "wait")]
            first = evaluate_graph(raw, EVENT, "closed")
            for decision in invalid:
                checkpoint = deepcopy(first["delay"]["continuation"])
                checkpoint["decisions"]["choice"] = decision
                with self.subTest(node=selected["type"], decision=decision), self.assertRaisesMessage(MapError, "continuation"):
                    evaluate_graph(raw, EVENT, "closed", continuation=checkpoint)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class ChoiceRuntimeTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    command = fixtures.BuilderBlueprintTests.command
    update_scene = fixtures.BuilderBlueprintTests.update_scene
    edit_source = delays.DelayRuntimeTests.edit_source
    due = delays.DelayRuntimeTests.due

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.doc["doors"][0]["blueprint"] = branching(choice("random"))

    def stored(self, key="Selected"):
        self.door_object.refresh_from_db()
        return self.door_object.data["automationVariables"][key]["value"]

    def test_successful_receipt_retry_does_not_draw_or_write_again(self):
        self.generated()
        request_id = uuid.uuid4()
        with patch.object(blueprint_runtime, "_random_draw", wraps=blueprint_runtime._random_draw) as draw:
            first = self.command("closed", request_id=request_id, user=self.player)
            selected = self.stored()
            self.assertEqual(self.command("closed", request_id=request_id, user=self.player), first)
            self.assertEqual(draw.call_count, 1)
        self.assertIn(selected, ("branch1", "branch2"))
        self.assertEqual(AutomationRun.objects.count(), 1)

    def test_failed_command_retry_uses_original_request_uuid_and_same_draw(self):
        raw = self.doc["doors"][0]["blueprint"]
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("fail", "light", targetId=self.light_id, enabled=True))
        graph["edges"].extend([execution("branch1", "fail"), execution("branch2", "fail")])
        self.generated()
        request_id, samples = uuid.uuid4(), []
        original = blueprint_runtime._random_draw
        def capture(*args):
            result = original(*args)
            samples.append((args, result))
            return result
        with patch.object(blueprint_runtime, "_random_draw", side_effect=capture), override_settings(DYNAMIC_LIGHTING_ENABLED=False):
            for unused in range(2):
                with self.assertRaisesMessage(MapError, "lighting is disabled"):
                    self.command("closed", request_id=request_id)
        self.assertEqual(samples[0], samples[1])
        self.assertEqual(samples[0][0][0], request_id)
        self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())
        self.door_object.refresh_from_db()
        self.assertNotIn("automationVariables", self.door_object.data)
        self.command("closed", request_id=request_id)
        self.assertEqual(self.stored(), "branch" + str(samples[0][1] + 1))

    @override_settings(SECRET_KEY="synthetic-choice-draw-domain-separation")
    def test_private_generator_is_stable_domain_separated_and_bounded(self):
        request_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        args = (request_id, 0, "element", EVENT, "choice", 1_000_000)
        first = blueprint_runtime._random_draw(*args)
        self.assertEqual(blueprint_runtime._random_draw(*args), first)
        values = {blueprint_runtime._random_draw(request_id, index, "element", EVENT, "choice", 1_000_000)
                  for index in range(12)}
        self.assertGreater(len(values), 1)
        self.assertTrue(all(0 <= value < 1_000_000 for value in values))
        for position, replacement in ((0, uuid.UUID("00000000-0000-0000-0000-000000000002")),
                                      (2, "other"), (3, "signal:Other"), (4, "another")):
            changed = list(args)
            changed[position] = replacement
            self.assertNotEqual(blueprint_runtime._random_draw(*changed), first)
        self.assertNotEqual(blueprint_runtime._random_draw(*args, root_ordinal=1), first)

    def test_gm_log_records_typed_value_and_selected_weight_without_player_metadata(self):
        raw = branching(choice(valueType="text", value="Key", cases=[{"id": "case4", "value": "Key"}]))
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("random", "random", weights=[0, 3]))
        graph["edges"].append(execution("case4", "random"))
        self.doc["doors"][0]["blueprint"] = raw
        self.generated()
        self.command("closed", user=self.player)
        steps = AutomationRun.objects.get().data["events"][0]["steps"]
        self.assertIn({"id": "choice", "type": "switch", "output": "case4", "valueType": "text", "value": "Key"}, steps)
        self.assertIn({"id": "random", "type": "random", "output": "branch2", "weight": 3, "total": 3}, steps)
        for user in (self.player, self.streamer):
            self.client.force_login(user)
            self.assertEqual(self.client.get(f"/api/maps/{self.scene.pk}/automation").status_code, 404)
            projected = json.dumps(objects.layer_state(self.scene, Membership.objects.get(campaign=self.campaign, user=user)))
            self.assertNotIn("weights", projected)
            self.assertNotIn("cases", projected)

    def test_random_counter_continues_across_delay_without_replaying_prior_draws(self):
        raw = self.doc["doors"][0]["blueprint"]
        graph = raw["graphs"][EVENT]
        graph["nodes"].extend([node("wait", "delay", seconds=.1), node("second", "random", weights=[1, 1]),
            node("after", "setVariable", scope="element", name="After", valueType="boolean", value=True)])
        graph["edges"].extend([execution("branch1", "wait"), execution("branch2", "wait"),
            execution("wait", "second"), execution("second", "after", "branch1"), execution("second", "after", "branch2")])
        self.generated()
        with patch.object(blueprint_runtime, "_random_draw", wraps=blueprint_runtime._random_draw) as draw:
            self.command("closed")
            row = AutomationDelay.objects.get(status="pending")
            self.assertEqual(row.data["budget"]["randomDraws"], 1)
            self.assertEqual(self.due(row)["completed"], 1)
            self.assertEqual([call.args[1] for call in draw.call_args_list], [0, 1])
        self.assertTrue(self.stored("After"))

    def test_old_wait_budget_defaults_to_zero_and_corrupt_counter_is_rejected(self):
        self.doc["doors"][0]["blueprint"] = blueprint({EVENT: (
            [node("wait", "delay", seconds=.1), choice("random")],
            [execution("event", "wait"), execution("wait", "choice")])})
        self.generated()
        self.command("closed")
        row = AutomationDelay.objects.get(status="pending")
        del row.data["budget"]["randomDraws"]
        del row.data["budget"]["randomRoot"]
        row.save(update_fields=["data"])
        with patch.object(blueprint_runtime, "_random_draw", wraps=blueprint_runtime._random_draw) as draw:
            self.assertEqual(self.due(row)["completed"], 1)
            self.assertEqual(draw.call_args.args[1], 0)
            self.assertEqual(draw.call_args.args[-1], 0)
        for key in ("randomDraws", "randomRoot"):
            for value in (True, -1, 1.5, "1"):
                self.command("closed")
                row = AutomationDelay.objects.get(status="pending")
                row.data["budget"][key] = value
                row.save(update_fields=["data"])
                self.assertEqual(self.due(row)["failed"], 1)

    def test_timer_expiry_switch_reads_current_variables_and_inherits_draw_ordinal(self):
        raw = self.doc["doors"][0]["blueprint"]
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("timer", "timer", name="Choose", action="start", seconds=.1))
        graph["edges"].extend([execution("branch1", "timer"), execution("branch2", "timer")])
        listener = branching(choice(), event="signal:Choose")["graphs"]["signal:Choose"]
        listener["nodes"].extend([node("read", "getVariable", scope="scene", name="Stage", valueType="number", default=0),
                                  node("random", "random", weights=[1, 1])])
        listener["edges"].extend([data("read", "value", "choice", "value"), execution("case2", "random")])
        raw["graphs"]["signal:Choose"] = listener
        self.generated()
        self.command("closed")
        row = AutomationDelay.objects.get(status="pending")
        self.scene.settings["automationVariables"] = {"Stage": {"type": "number", "value": 2}}
        self.scene.save(update_fields=["settings"])
        with patch.object(blueprint_runtime, "_random_draw", wraps=blueprint_runtime._random_draw) as draw:
            self.assertEqual(self.due(row)["completed"], 1)
            self.assertEqual(draw.call_args.args[1], 1)
        self.assertEqual(self.stored(), "case2")

    def test_player_random_branch_cannot_unlock_or_lock_without_authored_permission(self):
        raw = blueprint({EVENT: ([choice("random", weights=[0, 1]), node("lock", "state", targetState="locked")],
                                 [execution("event", "choice"), execution("choice", "lock", "branch2")])})
        self.doc["doors"][0]["blueprint"] = raw
        self.generated()
        with self.assertRaisesMessage(MapError, "cannot be operated"):
            self.command("closed", user=self.player)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")

    def test_campaign_archive_and_native_copy_preserve_uuid_looking_case_text(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        from gravewright.maps.models import MapBuilderProject
        authored = str(self.alternate.pk)
        self.doc["doors"][0]["blueprint"] = branching(choice(valueType="text", value=authored,
            cases=[{"id": "case3", "value": authored}]))
        self.generated()
        self.door_object.refresh_from_db()
        copied = objects.apply(self.scene, self.membership, "wall-selection", "paste", {"walls": [self.door_object.data]})
        clone = SceneObject.objects.get(pk=copied["walls"][0])
        self.assertEqual(clone.data["blueprint"], self.door_object.data["blueprint"])
        restored = import_campaign(export_campaign(self.campaign), self.gm, "Imported choices")
        source = MapBuilderProject.objects.get(campaign=restored)
        for raw in [source.document["doors"][0]["blueprint"],
                    *[row.data["blueprint"] for row in source.scene.elements.filter(kind="walls", data__kind="door")]]:
            selected = raw["graphs"][EVENT]["nodes"][1]
            self.assertEqual(selected["value"], authored)
            self.assertEqual(selected["cases"], [{"id": "case3", "value": authored}])


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class ChoicePresenceTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    region = region_fixtures.RegionTests.region
    token_command = region_fixtures.RegionTests.token_command
    place = region_fixtures.RegionTests.place
    move = region_fixtures.RegionTests.move

    def setUp(self):
        region_fixtures.RegionTests.setUp(self)
        self.doc["regions"][0]["blueprint"]["graphs"] = {
            event: branching(choice("random"), event=event)["graphs"][event]
            for event in ("presence:enter", "presence:exit")}

    def test_batch_token_placements_allocate_distinct_roots_and_retries_never_repeat(self):
        self.doc["regions"][0]["height"] = 3
        self.generated()
        one, two = self.place(2, 1), self.place(2, 1)
        request_id = uuid.uuid4()
        with patch.object(blueprint_runtime, "_random_draw", wraps=blueprint_runtime._random_draw) as draw:
            first = self.token_command("duplicate", {"tokenIds": [str(one.pk), str(two.pk)]}, rid=request_id)
            self.assertEqual(len(first["createdIds"]), 2)
            self.assertEqual([call.args[-1] for call in draw.call_args_list], [0, 1])
            self.assertEqual(draw.call_args_list[0].args[:-1], draw.call_args_list[1].args[:-1])
            repeated = self.token_command("duplicate", {"tokenIds": [str(one.pk), str(two.pk)]}, rid=request_id)
            self.assertEqual(repeated["createdIds"], first["createdIds"])
            self.assertEqual(draw.call_count, 2)

    def test_repeated_path_presence_events_get_distinct_roots_and_retries_keep_the_sequence(self):
        graph = self.doc["regions"][0]["blueprint"]["graphs"]["presence:exit"]
        graph["nodes"].extend([node("counter", "counter", target=2),
            node("light", "light", targetId=self.light_id, enabled=True)])
        graph["edges"].extend([execution("branch1", "counter"), execution("branch2", "counter"),
                               execution("counter", "light", "true")])
        self.generated()
        token = self.place()
        request_id, samples = uuid.uuid4(), []
        original = blueprint_runtime._random_draw
        def capture(*args):
            result = original(*args)
            samples.append((args, result))
            return result
        with patch.object(blueprint_runtime, "_random_draw", side_effect=capture):
            with override_settings(DYNAMIC_LIGHTING_ENABLED=False):
                for unused in range(2):
                    with self.assertRaisesMessage(MapError, "lighting is disabled"):
                        self.move(token, 0, rid=request_id, path=[[3, 1], [0, 1], [3, 1]])
                    token.refresh_from_db()
                    self.assertEqual(token.grid_x, 0)
                    self.assertEqual(self.region().data["region"]["occupants"], [])
                    self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())
            self.assertEqual(samples[:4], samples[4:8])
            self.assertEqual([sample[0][-1] for sample in samples[:4]], [0, 1, 2, 3])
            self.assertEqual(samples[0][0][3], samples[2][0][3])
            self.assertEqual(samples[0][0][:-1], samples[2][0][:-1])
            self.move(token, 0, rid=request_id, path=[[3, 1], [0, 1], [3, 1]])
            self.assertEqual(samples[8:12], samples[:4])
            self.move(token, 0, rid=request_id, path=[[3, 1], [0, 1], [3, 1]])
            self.assertEqual(len(samples), 12)

    def test_actor_delete_rollback_retries_use_the_original_receipt_identity(self):
        from gravewright.actors import services as actors
        from gravewright.actors.models import Actor
        graph = self.doc["regions"][0]["blueprint"]["graphs"]["presence:exit"]
        graph["nodes"].append(node("light", "light", targetId=self.light_id, enabled=True))
        graph["edges"].extend([execution("branch1", "light"), execution("branch2", "light")])
        self.generated()
        self.place(2, 1)
        self.place(3, 1)
        request_id, samples = uuid.uuid4(), []
        original = blueprint_runtime._random_draw
        def capture(*args):
            result = original(*args)
            samples.append((args, result))
            return result
        with patch.object(blueprint_runtime, "_random_draw", side_effect=capture):
            with override_settings(DYNAMIC_LIGHTING_ENABLED=False):
                for unused in range(2):
                    with self.assertRaisesMessage(MapError, "lighting is disabled"):
                        actors.command(self.campaign.pk, self.gm.pk, "actor.delete", {"id": str(self.actor.pk)}, request_id)
                    self.assertTrue(Actor.objects.filter(pk=self.actor.pk).exists())
                    self.assertEqual(self.scene.tokens.count(), 2)
                    self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())
            self.assertEqual(samples[0], samples[1])
            self.assertEqual(samples[0][0][0], request_id)
            actors.command(self.campaign.pk, self.gm.pk, "actor.delete", {"id": str(self.actor.pk)}, request_id)
            self.assertEqual(samples[2], samples[0])
            self.assertEqual([sample[0][-1] for sample in samples[2:]], [0, 1])
            self.assertFalse(self.scene.tokens.exists())

    def test_recursive_folder_delete_keeps_original_request_and_root_on_delayed_work(self):
        from gravewright.actors import services as actors
        from gravewright.actors.models import Actor, Folder
        from gravewright.maps.blueprint_delays import process_due_delays
        graph = self.doc["regions"][0]["blueprint"]["graphs"]["presence:exit"]
        graph["nodes"].append(node("wait", "delay", seconds=.1))
        graph["edges"].extend([execution("branch1", "wait"), execution("branch2", "wait")])
        self.generated()
        parent = Folder.objects.create(campaign=self.campaign, name="Actors")
        one = Folder.objects.create(campaign=self.campaign, parent=parent, name="First",
                                    id=uuid.UUID("00000000-0000-0000-0000-000000000001"))
        two = Folder.objects.create(campaign=self.campaign, parent=parent, name="Second",
                                    id=uuid.UUID("00000000-0000-0000-0000-000000000002"))
        self.actor.folder = two
        self.actor.save(update_fields=["folder"])
        another = Actor.objects.create(campaign=self.campaign, folder=one, name="Other", data={})
        first = self.place(2, 1)
        second = self.token_command("place", {"actorId": str(another.pk), "gridX": 3, "gridY": 1})["createdIds"][0]
        request_id = uuid.uuid4()
        with patch.object(blueprint_runtime, "_random_draw", wraps=blueprint_runtime._random_draw) as draw:
            actors.command(self.campaign.pk, self.gm.pk, "folder.delete", {"id": str(parent.pk), "recursive": True}, request_id)
            self.assertEqual([call.args[-1] for call in draw.call_args_list], [0, 1])
            jobs = list(AutomationDelay.objects.filter(status="pending").order_by("created_at", "id"))
            self.assertEqual(len(jobs), 2)
            self.assertEqual([job.request_id for job in jobs], [request_id, request_id])
            self.assertEqual([job.data["budget"]["randomRoot"] for job in jobs], [0, 1])
            self.assertEqual([job.data["budget"]["randomDraws"] for job in jobs], [1, 1])
            self.assertEqual([job.data["context"]["tokenId"] for job in jobs], [str(second), str(first.pk)])
            actors.command(self.campaign.pk, self.gm.pk, "folder.delete", {"id": str(parent.pk), "recursive": True}, request_id)
            self.assertEqual(draw.call_count, 2)
            self.assertEqual(process_due_delays(now=jobs[-1].due_at)["completed"], 2)
            self.assertEqual(draw.call_count, 2)
