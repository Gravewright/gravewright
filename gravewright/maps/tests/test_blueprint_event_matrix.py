"""Cross-kind event contracts, authenticated crossings and reversible rehearsals.

The explicit inventory has 22 supported owner/event pairs and 47
owner/event/state pairs. Empty objects intentionally use the lever capability.
"""

from copy import deepcopy
import uuid
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.actors.models import Actor
from gravewright.journals.models import Journal
from gravewright.maps import blueprint_testing, services
from gravewright.maps.blueprint_runtime import element_state
from gravewright.maps.blueprints import clean_blueprint, default_blueprint, evaluate_graph
from gravewright.maps.models import AutomationDelay, AutomationRun, Receipt

from . import test_levers as fixtures
from . import test_regions as token_fixtures
from .test_levers import data, execution, node


OWNERS = {
    "door": {"kind": "door", "states": ("closed", "open", "locked"),
             "events": ("interact", "destroy", "signal:Ready")},
    "lever": {"kind": "lever", "states": ("off", "on"),
              "events": ("interact", "presence:enter", "presence:exit", "destroy", "signal:Ready")},
    "torch": {"kind": "torch", "states": ("off", "on"),
              "events": ("interact", "presence:enter", "presence:exit", "destroy", "signal:Ready")},
    "empty": {"kind": "lever", "states": ("off", "on"),
              "events": ("interact", "presence:enter", "presence:exit", "destroy", "signal:Ready")},
    "region": {"kind": "region", "states": ("empty", "occupied"),
               "events": ("presence:enter", "presence:exit", "destroy", "signal:Ready")},
}
CONTEXT = {"tokenId": "text", "actorId": "text", "userId": "text", "sourceId": "text",
           "event": "text", "presence": "text", "count": "number", "hasToken": "boolean"}


def chain(event, *actions):
    nodes = [node("event", "event", event=event), *actions]
    return {"nodes": nodes, "edges": [execution(left["id"], right["id"])
            for left, right in zip(nodes, nodes[1:])]}


def capture(event, *, scope="element"):
    """Read every contextual field through typed ports in authored order."""
    graph = chain(event, *(node("save" + key, "setVariable", scope=scope, name=key,
                               valueType=kind, value=False if kind == "boolean" else 0 if kind == "number" else "")
                           for key, kind in CONTEXT.items()))
    for key in CONTEXT:
        graph["nodes"].append(node("read" + key, "eventContext", property=key))
        graph["edges"].append(data("read" + key, "value", "save" + key, "value"))
    return graph


def blueprint(owner, *, scope="element"):
    result = default_blueprint(OWNERS[owner]["kind"])
    result["graphs"] = {event: capture(event, scope=scope) for event in OWNERS[owner]["events"]}
    return result


class EventMatrixDefinitionTests(SimpleTestCase):
    def test_all_47_event_state_pairs_start_without_implicit_state_checks(self):
        cells = 0
        for owner, spec in OWNERS.items():
            definition = clean_blueprint(blueprint(owner))
            for event in spec["events"]:
                for state in spec["states"]:
                    with self.subTest(owner=owner, event=event, state=state):
                        result = evaluate_graph(definition, event, state)
                        self.assertEqual([action["name"] for action in result["actions"]], list(CONTEXT))
                        self.assertTrue(all(action["type"] == "setVariable" for action in result["actions"]))
                        self.assertEqual(result["values"]["readevent"], event)
                        # Removing all execution wires must leave all value nodes dormant.
                        disconnected = deepcopy(definition)
                        disconnected["graphs"][event]["edges"] = [
                            edge for edge in disconnected["graphs"][event]["edges"] if edge["kind"] == "data"]
                        result = evaluate_graph(disconnected, event, state)
                        self.assertEqual((result["actions"], result["values"]), ([], {}))
                        cells += 1
        self.assertEqual(cells, 47)

    def test_all_141_event_state_control_pairs_keep_gate_memory_separate(self):
        cells = 0
        for owner, spec in OWNERS.items():
            for event in spec["events"]:
                for state in spec["states"]:
                    for control, fields in (("once", {}), ("counter", {"target": 2}),
                                            ("cooldown", {"seconds": 2})):
                        with self.subTest(owner=owner, event=event, state=state, control=control):
                            definition = default_blueprint(spec["kind"])
                            definition["graphs"] = {event: {
                                "nodes": [node("event", "event", event=event), node("gate", control, **fields),
                                          node("done", "setVariable", scope="element", name="Done", valueType="boolean", value=True)],
                                "edges": [execution("event", "gate"), execution("gate", "done", "true")]}}
                            first = evaluate_graph(definition, event, state, now=1000)
                            second = evaluate_graph(definition, event, state, memory=first["memory"], now=1500)
                            self.assertEqual(bool(first["actions"]), control != "counter")
                            self.assertEqual(bool(second["actions"]), control == "counter")
                            self.assertEqual(set(second["memory"]), {event})
                            cells += 1
        self.assertEqual(cells, 141)

    def test_unsupported_event_kind_pairs_remain_validation_errors(self):
        for owner, events in (("door", ("presence:enter", "presence:exit")), ("region", ("interact",))):
            for event in events:
                with self.subTest(owner=owner, event=event), self.assertRaises(services.MapError):
                    definition = default_blueprint(OWNERS[owner]["kind"])
                    definition["graphs"][event] = chain(event)
                    clean_blueprint(definition)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class EventMatrixRuntimeTests(TestCase):
    asset = fixtures.LeverTests.asset
    post = fixtures.LeverTests.post
    save = fixtures.LeverTests.save
    generate = fixtures.LeverTests.generate
    files = fixtures.LeverTests.files
    generated = fixtures.LeverTests.generated
    token_command = token_fixtures.RegionTests.token_command
    place = token_fixtures.RegionTests.place
    move = token_fixtures.RegionTests.move

    def setUp(self):
        fixtures.LeverTests.setUp(self)
        self.sources = {"door": self.doc["doors"][0], "lever": self.doc["decorations"][0]}
        for owner in ("torch", "empty"):
            source = deepcopy(self.sources["lever"])
            source["id"] = str(uuid.uuid4())
            if owner == "torch":
                source.pop("lever")
                source["torch"] = {"state": "off", "lit": False, "lightId": self.light_id}
            else:
                source.update(empty=True, assetId=None)
            self.doc["decorations"].append(source)
            self.sources[owner] = source
        self.sources["region"] = {"id": str(uuid.uuid4()), "layerId": self.doc["layers"][0]["id"],
            "name": "Matrix region", "x": 2, "y": 1, "width": 2, "height": 1, "enabled": True}
        self.doc["regions"] = [self.sources["region"]]
        for owner, source in self.sources.items():
            source["blueprint"] = blueprint(owner)
            if owner != "door":
                source.update(x=2, y=1, width=2, height=1)
        self.actor = Actor.objects.create(campaign=self.campaign, name="Matrix traveler", data={},
                                          permissions={str(self.player.pk): "owner"})

    def row(self, owner):
        return self.scene.elements.get(pk=uuid.uuid5(self.scene.pk, self.sources[owner]["id"]))

    def snapshot(self):
        self.scene.refresh_from_db()
        return {"elements": list(self.scene.elements.order_by("pk").values("id", "data", "version")),
                "tokens": list(self.scene.tokens.order_by("pk").values()), "settings": deepcopy(self.scene.settings),
                "runs": AutomationRun.objects.filter(scene=self.scene).count(),
                "receipts": Receipt.objects.count(), "waits": list(AutomationDelay.objects.filter(scene=self.scene).values())}

    def rehearse(self, row, event, *, user=None, **extra):
        return blueprint_testing.run(self.campaign.pk, (user or self.gm).pk, self.scene.pk, row.pk,
            {"request_id": str(uuid.uuid4()), "expected_version": row.version, "event": event, **extra})

    def test_all_44_event_pause_pairs_rehearse_authenticated_context_and_roll_back(self):
        # Scene scope keeps a destroy handler's observable result after its owner is removed.
        for owner, source in self.sources.items():
            source["blueprint"] = blueprint(owner, scope="scene")
        self.generated()
        token = self.place()
        cells = 0
        for paused in (False, True):
            self.scene.settings["automationPaused"] = paused
            self.scene.save(update_fields=["settings"])
            before = self.snapshot()
            for owner, spec in OWNERS.items():
                for event in spec["events"]:
                    with self.subTest(owner=owner, event=event, paused=paused):
                        row = self.row(owner)
                        result = self.rehearse(row, event, tokenId=str(token.pk))
                        self.assertTrue(result["ok"], result)
                        values = result["changes"]["sceneVariables"]["after"]
                        expected = {"tokenId": str(token.pk), "actorId": str(self.actor.pk),
                            "userId": str(self.gm.pk), "sourceId": str(row.pk), "event": event,
                            "presence": event.split(":", 1)[1] if event.startswith("presence:") else "",
                            "count": 0, "hasToken": True}
                        self.assertEqual(values, {key: {"type": CONTEXT[key], "value": value}
                                                  for key, value in expected.items()})
                        self.assertEqual("automation-paused" in result["warnings"], paused)
                        removed = {change["id"] for change in result["changes"]["elements"] if change["after"] is None}
                        self.assertEqual(str(row.pk) in removed, event == "destroy")
                        if event != "destroy":
                            self.assertEqual((result["run"]["stateBefore"], result["run"]["stateAfter"]),
                                             (element_state(row), element_state(row)))
                        self.assertEqual(self.snapshot(), before)
                        cells += 1
        self.assertEqual(cells, 44)

    def test_all_44_non_gm_rehearsal_pairs_are_forbidden_without_mutation(self):
        self.generated()
        before = self.snapshot()
        cells = 0
        for user in (self.player, self.streamer):
            for owner, spec in OWNERS.items():
                for event in spec["events"]:
                    with self.subTest(owner=owner, event=event, user=user.pk), self.assertRaises(services.MapError):
                        self.rehearse(self.row(owner), event, user=user)
                    self.assertEqual(self.snapshot(), before)
                    cells += 1
        self.assertEqual(cells, 44)

    def test_66_event_audience_pairs_present_and_teleport_only_in_rolled_back_rehearsal(self):
        """All owner/event starts retain identity across world actions and audience scopes."""
        handout = Journal.objects.create(campaign=self.campaign, title="Matrix handout", visibility="shared")
        destination_id = str(uuid.uuid4())
        self.doc["regions"].append({"id": destination_id, "layerId": self.doc["layers"][0]["id"],
            "name": "Matrix arrival", "x": 6, "y": 5, "width": 2, "height": 1, "enabled": True})
        for owner, source in self.sources.items():
            definition = blueprint(owner)
            for event, graph in definition["graphs"].items():
                actions = [node("message", "showMessage", text="Matrix message", audience={"scope": "trigger"}),
                    node("handout", "showHandout", journalId=str(handout.pk), audience={"scope": "trigger"}),
                    node("camera", "cameraFocus", focusX=6, focusY=5, audience={"scope": "trigger"}),
                    node("transport", "teleport", destinationId=destination_id)]
                graph["nodes"].extend(actions)
                graph["edges"] = [edge for edge in graph["edges"] if edge["from"] != "event"]
                graph["edges"].extend([execution("event", "message"), execution("message", "handout"),
                    execution("handout", "camera"), execution("camera", "transport"), execution("transport", "savetokenId")])
            source["blueprint"] = definition
        self.generated()
        token = self.place()
        before = self.snapshot()
        cells = 0
        scopes = (({"scope": "trigger"}, 1), ({"scope": "users", "userIds": [str(self.player.pk)]}, 1),
                  ({"scope": "players"}, 2))
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            for audience, recipients in scopes:
                for owner, spec in OWNERS.items():
                    for event in spec["events"]:
                        with self.subTest(owner=owner, event=event, audience=audience["scope"]):
                            row = self.row(owner)
                            definition = deepcopy(row.data["blueprint"])
                            for action in definition["graphs"][event]["nodes"]:
                                if action["type"] in ("showMessage", "showHandout", "cameraFocus"):
                                    action["audience"] = audience
                            result = self.rehearse(row, event, tokenId=str(token.pk), blueprint=definition)
                            self.assertTrue(result["ok"], result)
                            steps = result["run"]["events"][0]["steps"]
                            world = [step for step in steps if step["type"] in ("showMessage", "showHandout", "cameraFocus")]
                            self.assertEqual([(step["type"], step["recipients"]) for step in world],
                                [("showMessage", recipients), ("showHandout", recipients), ("cameraFocus", recipients)])
                            moved = next(change for change in result["changes"]["tokens"] if change["id"] == str(token.pk))
                            self.assertEqual((moved["after"]["grid_x"], moved["after"]["grid_y"]), (6, 5))
                            self.assertEqual(result["run"]["context"]["actorId"], str(token.actor_id))
                            self.assertEqual(result["run"]["context"]["tokenId"], str(token.pk))
                            self.assertIn("presentation-not-delivered", result["warnings"])
                            self.assertEqual(self.snapshot(), before)
                            cells += 1
        send.assert_not_called()
        self.assertEqual(cells, 66)

    def test_all_22_event_pairs_schedule_both_timing_nodes_and_destroy_cancels_owned_work(self):
        for owner, source in self.sources.items():
            for event, graph in source["blueprint"]["graphs"].items():
                graph["nodes"].extend([node("clock", "timer", name="Ready", action="start", seconds=2),
                                       node("wait", "delay", seconds=1)])
                graph["edges"] = [edge for edge in graph["edges"] if edge["from"] != "event"]
                graph["edges"].extend([execution("event", "clock"), execution("clock", "wait"),
                                       execution("wait", "savetokenId")])
        self.generated()
        token = self.place()
        before = self.snapshot()
        cells = 0
        for owner, spec in OWNERS.items():
            for event in spec["events"]:
                with self.subTest(owner=owner, event=event):
                    result = self.rehearse(self.row(owner), event, tokenId=str(token.pk))
                    self.assertTrue(result["ok"], result)
                    steps = result["run"]["events"][0]["steps"]
                    self.assertEqual([step["type"] for step in steps], ["event", "timer", "delay"])
                    self.assertIn("timing-not-advanced", result["warnings"])
                    self.assertEqual("destruction-timing-cancelled" in result["warnings"], event == "destroy")
                    scheduled = [change["after"] for change in result["scheduled"]]
                    if event == "destroy":
                        self.assertEqual(scheduled, [])
                    else:
                        self.assertEqual({(entry["kind"], entry["seconds"], entry["event"]) for entry in scheduled},
                                         {("timer", 2, "signal:Ready"), ("delay", 1, event)})
                        self.assertTrue(all(entry["status"] == "pending" for entry in scheduled))
                    self.assertEqual(self.snapshot(), before)
                    cells += 1
        self.assertEqual(cells, 22)

    def test_16_live_object_region_token_crossings_keep_per_owner_context_and_state(self):
        self.generated()
        one, two = self.place(), self.place()
        one.refresh_from_db()
        stages = ((one, 2, self.player, "presence:enter", 1), (two, 2, self.gm, "presence:enter", 2),
                  (one, 0, self.player, "presence:exit", 1), (two, 0, self.gm, "presence:exit", 0))
        cells = 0
        for token, x, user, event, count in stages:
            self.move(token, x, user=user)
            for owner in ("lever", "torch", "empty", "region"):
                with self.subTest(owner=owner, event=event, count=count):
                    row = self.row(owner)
                    expected = {"tokenId": str(token.pk), "actorId": str(self.actor.pk), "userId": str(user.pk),
                        "sourceId": str(row.pk), "event": event, "presence": event.split(":")[1],
                        "count": count, "hasToken": True}
                    self.assertEqual(row.data["automationVariables"],
                                     {key: {"type": CONTEXT[key], "value": value} for key, value in expected.items()})
                    expected_state = ("occupied" if count else "empty") if owner == "region" else "off"
                    self.assertEqual(element_state(row), expected_state)
                    if owner != "region":
                        self.assertEqual(element_state(row), "off", "A crossing must not toggle its mechanism.")
                    if owner == "empty":
                        self.assertEqual((row.data["asset_id"], row.data["src"]), (None, ""))
                    if owner == "torch":
                        self.assertEqual((row.data["rotation"], row.data["torch"]["lit"]), (0, False))
                    cells += 1
        runs = list(AutomationRun.objects.filter(scene=self.scene))
        self.assertEqual(len(runs), 16)
        self.assertEqual({run.data["context"]["tokenId"] for run in runs}, {str(one.pk), str(two.pk)})
        self.assertEqual(cells, 16)

    def test_paused_crossings_baseline_all_four_owner_types_without_replaying_on_resume(self):
        self.generated()
        token = self.place()
        self.scene.settings["automationPaused"] = True
        self.scene.save(update_fields=["settings"])
        self.move(token, 2, user=self.player)
        for owner in ("lever", "torch", "empty", "region"):
            row = self.row(owner)
            ledger = row.data["region" if owner == "region" else "areaPresence"]
            self.assertEqual(ledger["occupants"], [str(token.pk)])
            self.assertNotIn("automationVariables", row.data)
        self.scene.refresh_from_db()
        self.scene.settings["automationPaused"] = False
        self.scene.save(update_fields=["settings"])
        self.move(token, 2.5, user=self.player)
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
        self.move(token, 0, user=self.player)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 4)
        for owner in ("lever", "torch", "empty", "region"):
            self.assertEqual(self.row(owner).data["automationVariables"]["event"]["value"], "presence:exit")
