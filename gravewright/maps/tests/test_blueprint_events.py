"""Base events start authored logic while preserving native authority."""

from copy import deepcopy
from datetime import timedelta
import uuid

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.maps import objects
from gravewright.maps.blueprint_delays import process_due_delays
from gravewright.maps.blueprints import clean_blueprint, default_blueprint, evaluate_graph, has_event_path
from gravewright.maps.models import AutomationDelay, AutomationRun, MapBuilderProject, Receipt, Scene
from gravewright.maps.services import MapError

from . import test_builder_blueprints as fixtures
from . import test_regions as region_fixtures
from . import test_torches as torch_fixtures
from . import test_levers as lever_fixtures
from .test_levers import data, execution, node


def graph(event, *actions):
    nodes = [node("event", "event", event=event), *actions]
    return {"nodes": nodes, "edges": [execution(before["id"], after["id"])
        for before, after in zip(nodes, nodes[1:])]}


def definition(kind="door", **graphs):
    result = default_blueprint(kind)
    result.update(version=2, graphs=graphs)
    return result


def set_value(identifier, value=True):
    return node(identifier, "setVariable", scope="element", name=identifier, valueType="boolean", value=value)


def toggle(event="interact", off="closed", on="open"):
    return {"nodes": [node("event", "event", event=event), node("check", "condition", state=on),
                      node("off", "state", targetState=off), node("on", "state", targetState=on)],
            "edges": [execution("event", "check"), execution("check", "off", "true"),
                      execution("check", "on", "false")]}


class VerbEventContractTests(SimpleTestCase):
    def test_base_events_are_explicit_and_retired_graphs_are_discarded(self):
        for kind in ("door", "lever", "torch", "region"):
            for event in ("destroy", "signal:Ready", "interact", "presence:enter", "presence:exit"):
                raw = definition(kind, **{event: graph(event)})
                if (kind == "region" and event == "interact") or (kind == "door" and event.startswith("presence:")):
                    with self.assertRaises(MapError):
                        clean_blueprint(raw)
                else:
                    self.assertEqual(clean_blueprint(raw), raw)
        raw = definition(interact=graph("interact"), change=None,
                         **{"enter:open": {"retired": True}, "exit:closed": [], "interact:locked": None})
        raw["version"] = 1
        before = deepcopy(raw)
        normalized = clean_blueprint(raw)
        self.assertEqual(normalized, definition(interact=graph("interact")))
        self.assertEqual(raw, before)
        for event in ("change", "enter:open", "exit:closed", "interact:locked", "onInteract", "enter:unknown"):
            with self.subTest(event=event), self.assertRaises(MapError):
                evaluate_graph(normalized, event, "closed")
        with self.assertRaises(MapError):
            clean_blueprint(definition(onInteract=graph("onInteract")))
        with self.assertRaises(MapError):
            clean_blueprint(definition(interact=None))

    def test_connected_event_requires_execution_from_root_and_preserves_drafts(self):
        raw = definition(interact=graph("interact", set_value("Touched")))
        self.assertTrue(has_event_path(raw, "interact"))
        raw["graphs"]["interact"]["edges"] = []
        before = deepcopy(raw)
        self.assertFalse(has_event_path(raw, "interact"))
        raw["graphs"]["interact"]["edges"] = [data("event", "value", "Touched", "value")]
        self.assertFalse(has_event_path(raw, "interact"))
        self.assertEqual(before["graphs"]["interact"]["nodes"], raw["graphs"]["interact"]["nodes"])

    def test_interaction_context_and_unread_values_after_delay_keep_event_snapshot(self):
        raw = definition(interact={"nodes": [node("event", "event", event="interact"),
            node("wait", "delay", seconds=1), node("current", "eventContext", property="state"),
            node("previous", "eventContext", property="previous"), node("old", "compare", state="closed"),
            node("check", "compare", state="open"), node("both", "all"), node("branch", "condition", state="open"),
            set_value("Correct")], "edges": [execution("event", "wait"), execution("wait", "branch"),
                data("current", "value", "check", "value"), data("previous", "value", "old", "value"),
                data("check", "result", "both", "a"), data("old", "result", "both", "b"),
                data("both", "result", "branch", "test"),
                execution("branch", "Correct", "true")]})
        result = evaluate_graph(raw, "interact", "open", "closed")
        resumed = evaluate_graph(raw, "interact", "locked", "open", continuation=result["delay"]["continuation"])
        self.assertEqual([action["id"] for action in resumed["actions"]], ["Correct"])
        self.assertEqual(resumed["values"]["current"], "open")
        self.assertEqual(resumed["values"]["previous"], "closed")

    def test_template_file_roundtrip_preserves_base_graphs_and_discards_retired_graphs(self):
        from gravewright.maps import blueprint_templates as templates
        raw = definition(interact=toggle(), change=graph("change", set_value("Changed")),
                         **{"enter:open": graph("enter:open", set_value("Legacy")),
                            "signal:Ready": graph("signal:Ready", set_value("Signalled"))})
        saved = {"version": 1, "blueprint": raw, "bindings": [], "parameters": []}
        cleaned = templates.clean_definition(saved)
        resolved = templates.resolve_definition(cleaned, {}, owner_id=str(uuid.uuid4()))
        self.assertEqual(resolved, clean_blueprint(raw))
        self.assertEqual(set(resolved["graphs"]), {"interact", "signal:Ready"})

    def test_verb_control_memory_survives_subsequent_event_evaluation(self):
        for event in ("destroy", "interact", "signal:Ready"):
            for kind, fields in (("counter", {"target": 2}), ("once", {}), ("cooldown", {"seconds": 2})):
                with self.subTest(event=event, kind=kind):
                    raw = definition(**{event: {"nodes": [node("event", "event", event=event),
                        node("gate", kind, **fields), set_value("Passed")],
                        "edges": [execution("event", "gate"), execution("gate", "Passed", "true")]}})
                    first = evaluate_graph(raw, event, "open", "closed", now=1000)
                    second = evaluate_graph(raw, event, "closed", "open", memory=first["memory"], now=1500)
                    self.assertEqual(bool(second["actions"]), kind == "counter")
                    self.assertIn(event, second["memory"])


class EventFixture:
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    command = fixtures.BuilderBlueprintTests.command
    update_scene = fixtures.BuilderBlueprintTests.update_scene

    def values(self, row=None):
        row = row or self.door_object
        row.refresh_from_db()
        return row.data.get("automationVariables", {})

    def events(self):
        return [event for event in AutomationRun.objects.filter(scene=self.scene).first().data["events"]]


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class VerbEventRuntimeTests(EventFixture, TestCase):
    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.doc["doors"][0]["blueprint"] = definition()

    def test_explicit_signal_observes_state_action_once_and_receipt_retry_is_idempotent(self):
        ready = {"nodes": [node("event", "event", event="signal:Ready"),
            node("current", "eventContext", property="state"),
            node("currentIsOpen", "compare", state="open"),
            node("branch", "condition", state="closed"), set_value("Observed")],
            "edges": [execution("event", "branch"), execution("branch", "Observed", "true"),
                data("current", "value", "currentIsOpen", "value"),
                data("currentIsOpen", "result", "branch", "test")]}
        self.doc["doors"][0]["blueprint"]["graphs"] = {
            "interact": graph("interact", set_value("Interacted"), node("open", "state", targetState="open"),
                              node("send", "emitEvent", scope="element", name="Ready")),
            "signal:Ready": ready}
        self.generated()
        rid = uuid.uuid4()
        first = self.command(request_id=rid)
        self.assertEqual(self.command(request_id=rid), first)
        self.assertEqual(set(self.values()), {"Interacted", "Observed"})
        self.assertEqual([event["event"] for event in self.events()], ["interact", "signal:Ready"])
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 1)
        signal_event = self.events()[-1]
        values = {step["id"]: step.get("value") for step in signal_event["steps"]}
        self.assertEqual(values["current"], "open")
        # A new interaction starts even when its state action repeats the current state.
        self.command("open")
        self.assertEqual([event["event"] for event in self.events()], ["interact", "signal:Ready"])

    def test_generic_interaction_controls_both_states_and_discards_retired_graphs(self):
        self.doc["doors"][0]["blueprint"]["graphs"] = {
            "interact": toggle(), "interact:closed": graph("interact:closed", set_value("Legacy")),
            "change": graph("change", set_value("Changed"))}
        self.generated()
        before = deepcopy(self.door_object.data["blueprint"])
        self.assertEqual(set(before["graphs"]), {"interact"})
        self.command("open", user=self.player)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")
        self.command("closed", user=self.player)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertNotIn("Legacy", self.values())
        self.assertEqual(self.door_object.data["blueprint"], before)
        self.assertNotIn("Changed", self.values())
        self.assertEqual([event["event"] for event in self.events()], ["interact"])

    def test_only_an_explicit_signal_starts_the_followup_and_keeps_control_memory(self):
        self.doc["doors"][0]["blueprint"]["graphs"] = {
            "interact": graph("interact", node("open", "state", targetState="open"),
                              node("send", "emitEvent", scope="element", name="Return")),
            "signal:Return": {"nodes": [node("event", "event", event="signal:Return"),
                                  node("back", "state", targetState="closed"), node("count", "counter", target=2),
                                  set_value("Twice")],
                       "edges": [execution("event", "back"), execution("back", "count"),
                                 execution("count", "Twice", "true")]}}
        self.generated()
        self.command("open")
        self.assertNotIn("Twice", self.values())
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertEqual([event["event"] for event in self.events()], ["interact", "signal:Return"])
        self.command("open")
        self.assertTrue(self.values()["Twice"]["value"])
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertEqual([event["event"] for event in self.events()], ["interact", "signal:Return"])

    def test_removed_exit_hook_cannot_veto_an_explicit_state_action_or_emit_change(self):
        self.doc["doors"][0]["blueprint"]["graphs"] = {
            "interact": graph("interact", node("open", "state", targetState="open")),
            "exit:closed": graph("exit:closed", node("stay", "state", targetState="closed")),
            "change": graph("change", set_value("Changed"))}
        self.generated()
        self.command("open")
        self.assertEqual(self.values(), {})
        self.assertEqual(self.door_object.data["door_state"], "open")
        self.assertEqual([event["event"] for event in self.events()], ["interact"])

    def test_generic_interaction_without_state_action_does_not_implicitly_toggle(self):
        self.doc["doors"][0]["blueprint"]["graphs"]["interact"] = graph("interact", set_value("Touched"))
        self.generated()
        self.command("open")
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertTrue(self.values()["Touched"]["value"])
        self.assertEqual([event["event"] for event in self.events()], ["interact"])

    def test_empty_generic_draft_discards_retired_graphs_and_never_toggles_natively(self):
        self.doc["doors"][0]["blueprint"]["graphs"] = {
            "interact": graph("interact"), "interact:closed": graph("interact:closed", set_value("Legacy"))}
        self.generated()
        self.command("open")
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertEqual(set(self.door_object.data["blueprint"]["graphs"]), {"interact"})
        self.assertEqual(self.values(), {})
        self.assertEqual([event["event"] for event in self.events()], ["interact"])
        self.command("closed")
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")

    def test_generic_locked_interaction_does_not_bypass_authored_unlock_permission(self):
        self.doc["doors"][0]["state"] = "locked"
        self.doc["doors"][0]["blueprint"]["graphs"]["interact"] = graph("interact", set_value("Touched"))
        self.generated()
        self.command("open", user=self.player)
        self.assertTrue(self.values()["Touched"]["value"])
        self.assertEqual(self.door_object.data["door_state"], "locked")
        row = self.door_object
        row.data["blueprint"]["graphs"]["interact"] = graph("interact", node("unlock", "state", targetState="open"))
        row.save(update_fields=["data"])
        with self.assertRaises(MapError):
            self.command("open", user=self.player)
        row.refresh_from_db()
        row.data["blueprint"]["graphs"]["interact"]["nodes"][1]["players"] = True
        row.save(update_fields=["data"])
        self.command("open", user=self.player)
        row.refresh_from_db()
        self.assertEqual(row.data["door_state"], "open")

    def test_public_interaction_flag_exposes_only_connected_handler_and_respects_pause_and_secrecy(self):
        self.doc["doors"][0]["state"] = "locked"
        self.doc["doors"][0]["blueprint"]["graphs"]["interact"] = graph("interact", set_value("PrivateAction"))
        self.generated()
        viewer = self.campaign.memberships.get(user=self.player)

        def public():
            return next(row for row in objects.layer_state(self.scene, viewer)["walls"]
                        if row["id"] == str(self.door_object.pk))

        row = public()
        self.assertIs(row["blueprintInteraction"], True)
        self.assertNotIn("blueprint", row)
        self.assertNotIn("PrivateAction", str(row))
        result = self.command("open", user=self.player)
        self.assertIs(result["wall"]["blueprintInteraction"], True)
        self.scene.settings = {**self.scene.settings, "automationPaused": True}
        self.scene.save(update_fields=["settings"])
        self.assertIs(public()["blueprintInteraction"], False)
        self.scene.settings.pop("automationPaused")
        self.scene.save(update_fields=["settings"])
        self.door_object.refresh_from_db()
        self.door_object.data["interactionEnabled"] = False
        self.door_object.save(update_fields=["data"])
        self.assertIs(public()["blueprintInteraction"], False)
        self.door_object.data.update(interactionEnabled=True, presentation="secret", discovered=False)
        self.door_object.save(update_fields=["data"])
        hidden = public()
        self.assertEqual(hidden["kind"], "wall")
        self.assertNotIn("blueprintInteraction", hidden)

    def test_explicit_signal_cycle_rolls_back_actions_state_and_receipt(self):
        self.doc["doors"][0]["blueprint"]["graphs"] = {
            "interact": graph("interact", set_value("Partial"), node("open", "state", targetState="open"),
                              node("send", "emitEvent", scope="element", name="Loop")),
            "signal:Loop": graph("signal:Loop", node("send", "emitEvent", scope="element", name="Loop"))}
        self.generated()
        before = deepcopy(self.door_object.data)
        rid = uuid.uuid4()
        with self.assertRaisesMessage(MapError, "repeating chain"):
            self.command(request_id=rid)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data, before)
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertEqual(self.values(), {})
        self.assertFalse(Receipt.objects.filter(request_id=rid).exists())
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).first().outcome, "failed")

    def test_generation_and_source_update_never_start_authored_graphs(self):
        self.doc["doors"][0]["blueprint"]["graphs"]["interact"] = graph("interact", set_value("Interacted"))
        self.generated()
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        self.assertEqual(self.values(), {})
        self.update_scene()
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        self.assertEqual(self.values(), {})
        source = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual(source.document["doors"][0]["blueprint"], self.doc["doors"][0]["blueprint"])

    def test_interaction_delay_and_named_timer_resume_without_replaying(self):
        self.doc["doors"][0]["blueprint"]["graphs"] = {
            "interact": graph("interact", node("timer", "timer", name="Pulse", action="start", seconds=2),
                              node("open", "state", targetState="open"),
                              node("wait", "delay", seconds=1), set_value("Continued")),
            "signal:Pulse": graph("signal:Pulse", set_value("Expired"))}
        self.generated()
        self.command()
        jobs = list(AutomationDelay.objects.filter(scene=self.scene, status="pending"))
        self.assertEqual({job.event for job in jobs}, {"interact", "signal:Pulse"})
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")
        self.assertEqual(self.values(), {})
        result = process_due_delays(now=max(job.due_at for job in jobs) + timedelta(seconds=1))
        self.assertEqual(result["completed"], 2)
        self.assertEqual(set(self.values()), {"Continued", "Expired"})
        self.assertEqual(AutomationDelay.objects.filter(scene=self.scene).count(), 2)
        self.assertEqual(process_due_delays(now=max(job.due_at for job in jobs) + timedelta(seconds=2))["processed"], 0)
        self.assertEqual(AutomationDelay.objects.filter(scene=self.scene, status="completed").count(), 2)

    def test_archive_roundtrip_keeps_only_base_graphs_without_starting_events(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        self.doc["doors"][0]["blueprint"]["graphs"] = {
            "interact": toggle(), "change": graph("change", set_value("Changed")),
            "enter:open": graph("enter:open", set_value("Legacy"))}
        self.generated()
        restored = import_campaign(export_campaign(self.campaign), self.gm, "Verb clone")
        source = MapBuilderProject.objects.get(campaign=restored)
        self.assertEqual(source.document["doors"][0]["blueprint"], clean_blueprint(self.doc["doors"][0]["blueprint"]))
        self.assertEqual(set(source.document["doors"][0]["blueprint"]["graphs"]), {"interact"})
        native = Scene.objects.get(campaign=restored).elements.get(kind="walls", data__kind="door")
        self.assertEqual(native.data["blueprint"], self.door_object.data["blueprint"])
        self.assertFalse(AutomationRun.objects.filter(scene__campaign=restored).exists())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class LeverVerbEventTests(EventFixture, TestCase):
    lever = lever_fixtures.LeverTests.lever
    interact = lever_fixtures.LeverTests.interact

    def setUp(self):
        lever_fixtures.LeverTests.setUp(self)
        interact = toggle(off="off", on="on")
        interact["nodes"].append(set_value("Interacted"))
        interact["edges"].extend([execution("off", "Interacted"), execution("on", "Interacted")])
        self.doc["decorations"][0]["blueprint"] = definition("lever", interact=interact)

    def test_single_interaction_graph_branches_on_lever_state_in_both_directions(self):
        self.generated()
        self.interact(user=self.player)
        self.assertEqual(self.lever().data["lever"]["state"], "on")
        self.assertEqual([event["event"] for event in self.events()], ["interact"])
        self.interact(user=self.player)
        self.assertEqual(self.lever().data["lever"]["state"], "off")
        self.assertEqual([event["event"] for event in self.events()], ["interact"])
        branch = next(step for step in self.events()[0]["steps"] if step["id"] == "check")
        self.assertTrue(branch["result"])
        self.assertIn("Interacted", self.values(self.lever()))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class TorchVerbEventTests(EventFixture, TestCase):
    torch = torch_fixtures.TorchTests.torch
    torch_command = torch_fixtures.TorchTests.command

    def setUp(self):
        torch_fixtures.TorchTests.setUp(self)
        interact = toggle(off="off", on="on")
        interact["nodes"].append(set_value("Interacted"))
        interact["edges"].extend([execution("off", "Interacted"), execution("on", "Interacted")])
        self.doc["decorations"][0]["blueprint"] = definition("torch", interact=interact)

    def test_torch_interaction_changes_mechanism_but_flame_does_not_start_any_event(self):
        self.generated()
        self.torch_command(user=self.player)
        self.assertEqual(self.torch().data["torch"]["state"], "on")
        self.assertIn("Interacted", self.values(self.torch()))
        self.assertEqual([event["event"] for event in self.events()], ["interact"])
        count = AutomationRun.objects.filter(scene=self.scene).count()
        self.torch_command("torch-light", lit=False)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)
        self.assertEqual(self.torch().data["torch"]["state"], "on")
        self.torch_command()
        self.assertEqual(self.torch().data["torch"]["state"], "off")

    def test_flame_and_art_actions_in_interaction_leave_mechanism_state_untouched(self):
        self.doc["decorations"][0]["blueprint"]["graphs"]["interact"] = graph("interact",
            node("flame", "flame", enabled=False), node("art", "sprite", appearance="hidden"))
        self.generated()
        self.torch_command()
        parent = self.torch()
        self.assertEqual(parent.data["torch"]["state"], "off")
        self.assertFalse(parent.data["torch"]["lit"])
        self.assertEqual(parent.data["layer"], "gm-image-layer")
        self.assertEqual(self.values(parent), {})
        self.assertEqual([event["event"] for event in self.events()], ["interact"])


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class RegionVerbEventTests(EventFixture, TestCase):
    region = region_fixtures.RegionTests.region
    token_command = region_fixtures.RegionTests.token_command
    place = region_fixtures.RegionTests.place
    move = region_fixtures.RegionTests.move

    def setUp(self):
        region_fixtures.RegionTests.setUp(self)
        def presence(event, count, marker, boundary):
            return {"nodes": [node("event", "event", event=event), set_value(marker),
                node("count", "eventContext", property="count"),
                node("boundary", "compareValue", valueType="number", operator="eq", expected=count),
                node("check", "condition", state="empty"), set_value(boundary)],
                "edges": [execution("event", marker), execution(marker, "check"),
                    data("count", "value", "boundary", "value"), data("boundary", "result", "check", "test"),
                    execution("check", boundary, "true")]}
        self.doc["regions"][0]["blueprint"] = definition("region", **{
            "presence:enter": presence("presence:enter", 1, "Entered", "First"),
            "presence:exit": presence("presence:exit", 0, "Exited", "Last")})

    def test_region_events_start_per_token_and_nodes_decide_first_enter_and_last_exit(self):
        self.generated()
        first, second = self.place(), self.place(0, 2)
        first.refresh_from_db()
        self.move(first, 2)
        self.assertEqual([event["event"] for event in self.events()], ["presence:enter"])
        self.assertEqual(set(self.values(self.region())), {"Entered", "First"})
        self.assertEqual(self.region().data["region"]["state"], "occupied")
        self.move(second, 3)
        self.assertEqual([event["event"] for event in self.events()], ["presence:enter"])
        self.assertFalse(next(step for step in self.events()[0]["steps"] if step["id"] == "check")["result"])
        self.move(first, 0)
        self.assertEqual([event["event"] for event in self.events()], ["presence:exit"])
        self.assertNotIn("Last", self.values(self.region()))
        self.assertEqual(self.region().data["region"]["state"], "occupied")
        self.move(second, 0)
        self.assertEqual([event["event"] for event in self.events()], ["presence:exit"])
        self.assertEqual(self.region().data["region"]["state"], "empty")
        self.assertEqual(set(self.values(self.region())), {"Entered", "First", "Exited", "Last"})
        runs = list(AutomationRun.objects.filter(scene=self.scene).order_by("created_at"))
        self.assertEqual([run.data["context"]["count"] for run in runs], [1, 2, 1, 0])
        self.assertEqual([event["event"] for run in runs for event in run.data["events"]],
                         ["presence:enter", "presence:enter", "presence:exit", "presence:exit"])
