"""Explicit interactions start another object's handler in one bounded chain."""

from copy import deepcopy
from datetime import timedelta
import uuid

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.actors.models import Actor
from gravewright.maps import blueprint_testing, services
from gravewright.maps.blueprint_delays import process_due_delays
from gravewright.maps.blueprints import clean_blueprint, default_blueprint, evaluate_graph
from gravewright.maps.models import AutomationDelay, AutomationRun, Receipt

from . import test_levers as fixtures
from . import test_regions as region_fixtures
from .test_levers import data, execution, node


def targeted(event, identifier, *, kind="interact", **fields):
    return {"nodes": [node("event", "event", event=event),
                      node("reference", "reference", targetId=identifier), node("action", kind, **fields)],
            "edges": [execution("event", "action"), data("reference", "door", "action", "target")]}


class InteractDefinitionTests(SimpleTestCase):
    def test_typed_target_is_optional_and_element_sets_are_supported(self):
        blueprint = default_blueprint("lever")
        blueprint["graphs"]["interact"] = {
            "nodes": [node("event", "event", event="interact"), node("action", "interact")],
            "edges": [execution("event", "action")]}
        self.assertNotIn("target", evaluate_graph(clean_blueprint(blueprint), "interact", "off")["actions"][0])
        identifiers = [str(uuid.uuid4()), str(uuid.uuid4())]
        graph = blueprint["graphs"]["interact"]
        graph["nodes"].append(node("group", "elementGroup", name="Switches", memberType="element", targetIds=identifiers))
        graph["edges"].append(data("group", "targets", "action", "target"))
        self.assertEqual(evaluate_graph(clean_blueprint(blueprint), "interact", "off")["actions"][0]["target"], identifiers)

    def test_interact_action_rejects_unknown_fields_version_one_and_wrong_target_types(self):
        valid = default_blueprint("door")
        valid["graphs"]["interact"] = targeted("interact", str(uuid.uuid4()))
        for failure in ("field", "version", "type"):
            blueprint = deepcopy(valid)
            graph = blueprint["graphs"]["interact"]
            if failure == "field":
                graph["nodes"][-1]["event"] = "destroy"
            elif failure == "version":
                blueprint["version"] = 1
                for edge in graph["edges"]:
                    edge.pop("kind")
            else:
                graph["nodes"][1] = node("reference", "lightReference", targetId=str(uuid.uuid4()))
                graph["edges"][-1]["output"] = "light"
            with self.subTest(failure=failure), self.assertRaises(services.MapError):
                clean_blueprint(blueprint)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class InteractActionTests(TestCase):
    asset = fixtures.LeverTests.asset
    post = fixtures.LeverTests.post
    save = fixtures.LeverTests.save
    generate = fixtures.LeverTests.generate
    files = fixtures.LeverTests.files
    generated = fixtures.LeverTests.generated
    token_command = region_fixtures.RegionTests.token_command
    place = region_fixtures.RegionTests.place
    move = region_fixtures.RegionTests.move

    def setUp(self):
        fixtures.LeverTests.setUp(self)
        self.doc["doors"][0].pop("blueprint")
        self.target_source = self.doc["decorations"][0]
        blueprint = default_blueprint("lever")
        blueprint["graphs"]["interact"] = {
            "nodes": [node("event", "event", event="interact"), node("check", "condition", state="off"),
                      node("on", "state", targetState="on"), node("off", "state", targetState="off"),
                      node("onImage", "sprite", appearance="asset", assetId=str(self.handle_on.pk)),
                      node("offImage", "sprite", appearance="asset", assetId=str(self.handle_off.pk)),
                      node("onLight", "light", targetId=self.light_id, enabled=True),
                      node("offLight", "light", targetId=self.light_id, enabled=False)],
            "edges": [execution("event", "check"), execution("check", "on", "true"),
                      execution("on", "onImage"), execution("onImage", "onLight"),
                      execution("check", "off", "false"), execution("off", "offImage"),
                      execution("offImage", "offLight")]}
        self.target_source["blueprint"] = blueprint
        self.empty_id = str(uuid.uuid4())
        behavior = default_blueprint("lever")
        behavior["graphs"] = {event: targeted(event, self.lever_id)
                              for event in ("presence:enter", "presence:exit", "interact")}
        self.empty_source = {"id": self.empty_id, "layerId": self.doc["layers"][0]["id"],
            "assetId": None, "empty": True, "x": 2, "y": 1, "width": 2, "height": 1,
            "rotation": 0, "lever": {"state": "off"}, "blueprint": behavior}
        self.doc["decorations"].append(self.empty_source)
        self.actor = Actor.objects.create(campaign=self.campaign, name="Area traveler", data={},
                                          permissions={str(self.player.pk): "owner"})

    def target(self):
        return self.scene.elements.get(pk=uuid.uuid5(self.scene.pk, self.lever_id))

    def empty(self):
        return self.scene.elements.get(pk=uuid.uuid5(self.scene.pk, self.empty_id))

    def use_visible_player_controller(self):
        """Direct player interactions start from visible artwork, not a GM controller."""
        self.empty_source.pop("empty")
        self.empty_source["assetId"] = str(self.handle_off.pk)

    def events(self):
        return [event for run in AutomationRun.objects.filter(scene=self.scene).order_by("created_at", "id")
                for event in run.data["events"]]

    def interact(self, *, user=None, request_id=None):
        return services.command(self.campaign.pk, (user or self.gm).pk, "objects", {
            "mapId": str(self.scene.pk), "area": "images", "action": "interact",
            "data": {"image_id": str(self.empty().pk)}}, request_id or uuid.uuid4())

    def test_area_entry_and_exit_run_target_state_image_and_light_without_changing_empty(self):
        self.generated()
        token = self.place()
        self.move(token, 2, user=self.player)
        target = self.target()
        self.assertEqual((target.data["lever"]["state"], target.data["asset_id"]), ("on", str(self.handle_on.pk)))
        self.light_object.refresh_from_db()
        self.assertTrue(self.light_object.data["enabled"])
        self.assertEqual(self.empty().data["lever"]["state"], "off")
        events = self.events()
        self.assertEqual([(event.get("doorId"), event["event"]) for event in events],
                         [(None, "presence:enter"), (str(target.pk), "interact")])
        action = next(step for step in events[0]["steps"] if step["type"] == "interact")
        self.assertEqual(action["targetIds"], [str(target.pk)])
        self.move(token, 0, user=self.player)
        target = self.target()
        self.assertEqual((target.data["lever"]["state"], target.data["asset_id"]), ("off", str(self.handle_off.pk)))
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])

    def test_state_only_still_does_not_run_target_actions_or_replace_persistent_sprite(self):
        self.empty_source["blueprint"]["graphs"]["presence:enter"] = targeted(
            "presence:enter", self.lever_id, kind="state", targetState="on")
        self.generated()
        target = self.target()
        target.data["sprite"] = {"appearance": "asset", "assetId": str(self.handle_off.pk)}
        target.save(update_fields=["data"])
        self.place(2)
        target = self.target()
        self.assertEqual(target.data["lever"]["state"], "on")
        self.assertEqual(target.data["asset_id"], str(self.handle_off.pk))
        self.light_object.refresh_from_db()
        self.assertFalse(self.light_object.data["enabled"])
        self.assertEqual([event["event"] for event in self.events()], ["presence:enter"])

    def test_retry_does_not_repeat_target_interaction(self):
        self.use_visible_player_controller()
        self.generated()
        request_id = uuid.uuid4()
        result = self.interact(user=self.player, request_id=request_id)
        before = (deepcopy(self.target().data), self.target().version, len(self.events()))
        self.assertEqual(self.interact(user=self.player, request_id=request_id), result)
        self.assertEqual((self.target().data, self.target().version, len(self.events())), before)
        self.assertEqual(self.target().data["lever"]["state"], "on")

    def test_authored_empty_target_interaction_does_nothing(self):
        self.target_source["blueprint"] = default_blueprint("lever")
        self.generated()
        self.interact()
        target = self.target()
        self.assertEqual((target.data["lever"]["state"], target.data["asset_id"]), ("off", str(self.handle_off.pk)))
        self.assertEqual([event["event"] for event in self.events()], ["interact"])

    def test_native_lever_without_blueprint_keeps_its_native_toggle(self):
        self.target_source.pop("blueprint")
        self.generated()
        self.interact()
        self.assertEqual(self.target().data["lever"]["state"], "on")
        self.interact()
        self.assertEqual(self.target().data["lever"]["state"], "off")

    def test_paused_source_runs_no_target_interaction(self):
        self.generated()
        self.scene.settings = {**self.scene.settings, "automationPaused": True}
        self.scene.save(update_fields=["settings"])
        before = (deepcopy(self.target().data), self.target().version)
        self.interact()
        self.assertEqual((self.target().data, self.target().version), before)
        self.assertEqual(AutomationRun.objects.get(scene=self.scene).outcome, "paused")

    def test_native_locked_door_does_not_unlock_for_player_chain(self):
        self.use_visible_player_controller()
        self.empty_source["blueprint"]["graphs"]["interact"] = targeted("interact", self.doc["doors"][0]["id"])
        self.generated()
        # Set up the native lock through its validated GM configuration.
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk),
            "area": "walls", "action": "update", "data": {"wall_id": str(self.door_object.pk),
                "version": self.door_object.version, "door_state": "locked"}}, uuid.uuid4())
        self.interact(user=self.player)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "locked")
        self.assertEqual(self.events()[-1]["event"], "refused")
        self.interact()
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")

    def test_native_door_toggle_opens_and_closes(self):
        self.use_visible_player_controller()
        self.empty_source["blueprint"]["graphs"]["interact"] = targeted("interact", self.doc["doors"][0]["id"])
        self.generated()
        for expected in ("open", "closed"):
            self.interact(user=self.player)
            self.door_object.refresh_from_db()
            self.assertEqual(self.door_object.data["door_state"], expected)

    def test_missing_or_unsupported_target_is_logged_without_changing_source(self):
        self.empty_source["blueprint"]["graphs"]["interact"] = targeted("interact", str(uuid.uuid4()))
        self.empty_source["blueprint"]["graphs"]["signal:Light"] = targeted("signal:Light", self.light_id)
        self.generated()
        self.interact()
        action = next(step for step in self.events()[0]["steps"] if step["type"] == "interact")
        self.assertTrue(action["missing"])
        row = self.empty()
        graph = row.data["blueprint"]["graphs"]["signal:Light"]
        row.data["blueprint"]["graphs"]["interact"] = deepcopy(graph)
        row.data["blueprint"]["graphs"]["interact"]["nodes"][0]["event"] = "interact"
        row.data["blueprint"]["graphs"]["interact"]["nodes"][1]["targetId"] = str(self.light_object.pk)
        row.save(update_fields=["data"])
        self.interact()
        action = next(step for step in self.events()[-1]["steps"] if step["type"] == "interact")
        self.assertTrue(action["unsupported"])
        self.assertEqual(self.empty().data["lever"]["state"], "off")

    def test_self_interaction_uses_same_budget_and_rolls_back_state_art_lights_and_receipt(self):
        graph = self.target_source["blueprint"]["graphs"]["interact"]
        graph["nodes"].append(node("again", "interact"))
        graph["edges"].extend([execution("onLight", "again"), execution("offLight", "again")])
        self.generated()
        before = [(row.pk, deepcopy(row.data), row.version) for row in self.scene.elements.order_by("pk")]
        request_id = uuid.uuid4()
        with self.assertRaisesMessage(services.MapError, "repeating chain"):
            self.interact(request_id=request_id)
        self.assertEqual([(row.pk, row.data, row.version) for row in self.scene.elements.order_by("pk")], before)
        self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())
        self.assertEqual(AutomationRun.objects.get(scene=self.scene).outcome, "failed")

    def test_cross_object_interaction_cycle_does_not_receive_fresh_budgets(self):
        self.target_source["blueprint"]["graphs"]["interact"] = targeted("interact", self.empty_id)
        self.generated()
        before = [(row.pk, deepcopy(row.data), row.version) for row in self.scene.elements.order_by("pk")]
        with self.assertRaisesMessage(services.MapError, "repeating chain"):
            self.interact()
        self.assertEqual([(row.pk, row.data, row.version) for row in self.scene.elements.order_by("pk")], before)

    def test_target_handler_receives_original_token_context(self):
        blueprint = self.target_source["blueprint"]
        graph = blueprint["graphs"]["interact"]
        graph["nodes"].extend([node("token", "eventContext", property="tokenId"),
            node("remember", "setVariable", scope="element", name="token", valueType="text", value="")])
        graph["edges"].extend([execution("onLight", "remember"), execution("offLight", "remember"),
            data("token", "value", "remember", "value")])
        self.generated()
        token = self.place()
        self.move(token, 2, user=self.player)
        self.assertEqual(self.target().data["automationVariables"]["token"], {"type": "text", "value": str(token.pk)})
        self.assertEqual(AutomationRun.objects.get(scene=self.scene).data["context"]["tokenId"], str(token.pk))

    def test_element_set_interacts_with_each_member_and_logs_the_resolved_targets(self):
        self.use_visible_player_controller()
        graph = self.empty_source["blueprint"]["graphs"]["interact"]
        graph["nodes"][1] = node("reference", "elementGroup", name="Room mechanisms", memberType="element",
                                  targetIds=[self.lever_id, self.doc["doors"][0]["id"]])
        graph["edges"][-1]["output"] = "targets"
        self.generated()
        self.interact(user=self.player)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")
        self.assertEqual(self.target().data["lever"]["state"], "on")
        action = next(step for step in self.events()[0]["steps"] if step["type"] == "interact")
        self.assertEqual(action["targetIds"], [str(self.target().pk), str(self.door_object.pk)])
        self.assertEqual(action["targetsCount"], 2)

    def test_composed_torch_handler_turns_mechanism_and_changes_native_flame_component(self):
        self.use_visible_player_controller()
        self.target_source.pop("lever")
        self.target_source["torch"] = {"state": "off", "lit": True, "lightId": self.light_id}
        self.doc["lights"][0].update(x=5.5, y=5, enabled=True)
        blueprint = default_blueprint("torch")
        blueprint["graphs"]["interact"] = {
            "nodes": [node("event", "event", event="interact"), node("state", "state", targetState="on"),
                      node("flame", "flame", enabled=False)],
            "edges": [execution("event", "state"), execution("state", "flame")]}
        self.target_source["blueprint"] = blueprint
        self.generated()
        before = self.scene.elements.get(pk=self.target().data["torch"]["components"]["lights"]["id"])
        self.assertTrue(before.data["enabled"])
        self.interact(user=self.player)
        target = self.target()
        self.assertEqual((target.data["torch"]["state"], target.data["rotation"], target.data["torch"]["lit"]),
                         ("on", 90, False))
        child = self.scene.elements.get(pk=target.data["torch"]["components"]["lights"]["id"])
        self.assertFalse(child.data["enabled"])
        self.assertNotEqual((child.data["x"], child.data["y"]), (before.data["x"], before.data["y"]))

    def test_native_torch_without_blueprint_turns_and_preserves_its_flame(self):
        self.use_visible_player_controller()
        self.target_source.pop("lever")
        self.target_source.pop("blueprint")
        self.target_source["torch"] = {"state": "off", "lit": True, "lightId": self.light_id}
        self.doc["lights"][0].update(x=5.5, y=5, enabled=True)
        self.generated()
        self.interact(user=self.player)
        target = self.target()
        self.assertEqual((target.data["torch"]["state"], target.data["rotation"], target.data["torch"]["lit"]),
                         ("on", 90, True))
        child = self.scene.elements.get(pk=target.data["torch"]["components"]["lights"]["id"])
        self.assertTrue(child.data["enabled"])

    def test_rehearsal_predicts_target_state_art_and_light_without_persisting(self):
        self.generated()
        before = [(row.pk, deepcopy(row.data), row.version) for row in self.scene.elements.order_by("pk")]
        row = self.empty()
        result = blueprint_testing.run(self.campaign.pk, self.gm.pk, self.scene.pk, row.pk,
            {"request_id": str(uuid.uuid4()), "expected_version": row.version, "event": "presence:enter"})
        self.assertTrue(result["ok"], result)
        predicted = {change["id"]: change["after"]["data"] for change in result["changes"]["elements"]}
        self.assertEqual(predicted[str(self.target().pk)]["lever"]["state"], "on")
        self.assertEqual(predicted[str(self.target().pk)]["asset_id"], str(self.handle_on.pk))
        self.assertTrue(predicted[str(self.light_object.pk)]["enabled"])
        self.assertEqual([(row.pk, row.data, row.version) for row in self.scene.elements.order_by("pk")], before)
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())

    def test_delayed_interaction_keeps_original_token_context_and_resumes_once(self):
        graph = self.empty_source["blueprint"]["graphs"]["presence:enter"]
        graph["nodes"].append(node("wait", "delay", seconds=1))
        graph["edges"][0:1] = [execution("event", "wait"), execution("wait", "action")]
        self.generated()
        token = self.place()
        self.move(token, 2, user=self.player)
        self.assertEqual(self.target().data["lever"]["state"], "off")
        scheduled = AutomationDelay.objects.get(scene=self.scene)
        self.assertEqual(self.empty().data["layer"], "gm-image-layer")
        self.assertEqual(scheduled.role, "player")
        self.assertEqual(scheduled.data["context"]["tokenId"], str(token.pk))
        processed = process_due_delays(now=scheduled.due_at + timedelta(seconds=1))
        self.assertEqual(processed["processed"], 1, processed)
        scheduled.refresh_from_db()
        self.assertEqual(scheduled.status, "completed")
        self.assertEqual(self.target().data["lever"]["state"], "on")
        before = (deepcopy(self.target().data), self.target().version)
        self.assertEqual(process_due_delays(now=scheduled.due_at + timedelta(seconds=2))["processed"], 0)
        self.assertEqual((self.target().data, self.target().version), before)
