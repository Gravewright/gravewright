"""Door references: typed targets, bounded chains, authority and missing targets."""

from copy import deepcopy
import uuid

from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.maps import services
from gravewright.maps.blueprints import clean_blueprint, default_blueprint, evaluate_graph
from gravewright.maps.models import Receipt
from gravewright.maps.services import MapError

from . import test_builder_blueprints as fixtures


def execution(origin, target, output="next"):
    return {"from": origin, "to": target, "output": output, "kind": "execution"}


def data(origin, output, target, port):
    return {"from": origin, "to": target, "output": output, "input": port, "kind": "data"}


def node(identifier, kind, **fields):
    return {"id": identifier, "type": kind, "x": 0, "y": 0, **fields}


def blueprint(graphs):
    result = default_blueprint()
    result["version"] = 2
    for event, (nodes, edges) in graphs.items():
        result["graphs"][event] = {"nodes": [node("event", "event", event=event), *nodes], "edges": edges}
    return result


def aim(event, other, state="open", *extra_nodes, extra_edges=(), self_state=None):
    """A graph whose Change state targets ``other`` through an Element reference."""
    nodes = [node("ref", "reference", targetId=other), node("act", "state", targetState=state), *extra_nodes]
    edges = [data("ref", "door", "act", "target"), *extra_edges]
    if self_state is None:
        edges.insert(0, execution("event", "act"))
    else:
        nodes.append(node("self", "state", targetState=self_state))
        edges[:0] = [execution("event", "self"), execution("self", "act")]
    return {event: (nodes, edges)}


class ReferenceContractTests(SimpleTestCase):
    def setUp(self):
        self.other = str(uuid.uuid4())

    def test_reference_feeds_typed_targets_and_reads_other_door_state(self):
        raw = blueprint({"interact": (
            [node("ref", "reference", targetId=self.other.upper()), node("prop", "property", property="state"),
             node("cmp", "compare", state="locked"), node("check", "condition", state="open"),
             node("act", "state", targetState="open"), node("show", "reveal")],
            [execution("event", "check"), execution("check", "act", "true"), execution("check", "show", "false"),
             data("ref", "door", "prop", "target"), data("prop", "value", "cmp", "value"),
             data("cmp", "result", "check", "test"), data("ref", "door", "act", "target")])})
        cleaned = clean_blueprint(raw)
        self.assertEqual(cleaned["graphs"]["interact"]["nodes"][1]["targetId"], self.other)
        locked = evaluate_graph(cleaned, "interact", "open", "closed", {self.other: "locked"})
        action, = locked["actions"]
        self.assertEqual((action["id"], action["target"]), ("act", self.other))
        self.assertEqual(locked["values"]["prop"], "locked")
        # A missing door reads as no state, so the comparison is false.
        missing = evaluate_graph(cleaned, "interact", "open", "closed", {})
        self.assertIsNone(missing["values"]["prop"])
        self.assertEqual([row["id"] for row in missing["actions"]], ["show"])
        self.assertNotIn("target", missing["actions"][0], "an unconnected Target means Self")

    def test_references_need_version_two_uuid_and_matching_input_types(self):
        valid = blueprint(aim("interact", self.other))
        clean_blueprint(valid)
        for change in ("bad id", "boolean input", "version one"):
            raw = deepcopy(valid)
            graph = raw["graphs"]["interact"]
            if change == "bad id":
                graph["nodes"][1]["targetId"] = "door-b"
            elif change == "boolean input":
                graph["nodes"].append(node("check", "condition", state="open"))
                graph["edges"].append(data("ref", "door", "check", "test"))
            else:
                raw["version"] = 1
                for edge in graph["edges"]:
                    edge.pop("kind")
            with self.subTest(change=change), self.assertRaises(MapError):
                clean_blueprint(raw)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class ReferenceChainTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    command = fixtures.BuilderBlueprintTests.command

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.generated()
        self.first = self.door_object
        created = services.command(self.campaign.pk, self.gm.pk, "objects",
            {"mapId": str(self.scene.pk), "area": "walls", "action": "create",
             "data": {"x1": 70, "y1": 700, "x2": 210, "y2": 700, "kind": "door"}}, uuid.uuid4())
        self.second = self.scene.elements.get(pk=created["wall"]["id"])

    def configure(self, door, graphs):
        door.refresh_from_db()
        services.command(self.campaign.pk, self.gm.pk, "objects",
            {"mapId": str(self.scene.pk), "area": "walls", "action": "update",
             "data": {"wall_id": str(door.pk), "version": door.version, "blueprint": blueprint(graphs)}}, uuid.uuid4())
        door.refresh_from_db()

    def operate(self, door, state, user=None, request_id=None):
        return services.command(self.campaign.pk, (user or self.gm).pk, "objects",
            {"mapId": str(self.scene.pk), "area": "walls", "action": "door",
             "data": {"wall_id": str(door.pk), "door_state": state}}, request_id or uuid.uuid4())

    def set_state(self, door, state):
        """Set up a native GM state without starting the interaction graph."""
        door.refresh_from_db()
        services.command(self.campaign.pk, self.gm.pk, "objects",
            {"mapId": str(self.scene.pk), "area": "walls", "action": "update",
             "data": {"wall_id": str(door.pk), "version": door.version, "door_state": state}}, uuid.uuid4())
        door.refresh_from_db()

    def runs(self):
        return self.client.get(f"/api/maps/{self.scene.pk}/automation").json()["runs"]

    def test_opening_one_door_opens_and_reveals_another_in_one_logged_chain(self):
        self.second.data.update(presentation="secret", discovered=False)
        self.second.save(update_fields=["data"])
        self.configure(self.first, aim("interact", str(self.second.pk), "open", node("show", "reveal"),
                                       extra_edges=[execution("act", "show"), data("ref", "door", "show", "target")],
                                       self_state="open"))
        result = self.operate(self.first, "open")
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.assertEqual(self.first.data["door_state"], "open")
        self.assertEqual(self.second.data["door_state"], "open")
        self.assertIs(self.second.data["discovered"], True)
        self.assertEqual([entry["event"] for entry in result["blueprint"]["trace"]], ["interact"])
        run = self.runs()[0]
        steps = run["events"][0]["steps"]
        # The reference joins the trace when the first action reads it.
        self.assertEqual([step["type"] for step in steps], ["event", "state", "state", "reference", "reveal"])
        aimed = [step for step in steps if step["id"] in ("act", "show")]
        self.assertTrue(all(step["doorId"] == str(self.second.pk) for step in aimed), steps)

    def test_cross_target_state_does_not_start_the_targets_interaction_or_toggle_the_source(self):
        self.configure(self.second, {"interact": (
            [node("closer", "state", targetState="closed")], [execution("event", "closer")])})
        self.configure(self.first, aim("interact", str(self.second.pk)))
        self.operate(self.first, "open")
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.assertEqual((self.first.data["door_state"], self.second.data["door_state"]), ("closed", "open"))
        self.assertEqual([(entry.get("doorId"), entry["event"]) for entry in self.runs()[0]["events"]],
                         [(None, "interact")])

    def test_targeted_signals_run_other_graphs_and_repeating_chains_roll_back_without_a_receipt(self):
        self.configure(self.second, {"signal:Close": (
            [node("closer", "state", targetState="closed")], [execution("event", "closer")])})
        self.configure(self.first, aim("interact", str(self.second.pk), "open",
            node("send", "emitEvent", scope="element", name="Close"),
            extra_edges=[execution("act", "send"), data("ref", "door", "send", "target")], self_state="open"))
        self.operate(self.first, "open")
        self.second.refresh_from_db()
        self.assertEqual(self.second.data["door_state"], "closed", "the targeted signal explicitly closes the other door")
        run = self.runs()[0]
        self.assertEqual([(entry.get("doorId"), entry["event"]) for entry in run["events"]],
                         [(None, "interact"), (str(self.second.pk), "signal:Close")])
        # State actions do not start graphs; explicit signals can still form a bounded cycle.
        self.set_state(self.first, "closed")
        self.set_state(self.second, "closed")
        send = node("send", "emitEvent", scope="element", name="Bounce")
        edges = [execution("act", "send"), data("ref", "door", "send", "target")]
        self.configure(self.first, {**aim("interact", str(self.second.pk), "open", send,
                                         extra_edges=edges, self_state="open"),
                                    **aim("signal:Bounce", str(self.second.pk), "open", send, extra_edges=edges)})
        self.configure(self.second, aim("signal:Bounce", str(self.first.pk), "closed", send, extra_edges=edges))
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        before = [(deepcopy(door.data), door.version) for door in (self.first, self.second)]
        request_id = uuid.uuid4()
        with self.assertRaisesMessage(MapError, "repeating chain"):
            self.operate(self.first, "open", request_id=request_id)
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.assertEqual([(door.data, door.version) for door in (self.first, self.second)], before)
        self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())
        self.assertEqual(self.runs()[0]["outcome"], "failed")
        # A failed operation leaves no receipt: repairing the graph permits that operation's retry.
        self.configure(self.second, aim("signal:Bounce", str(self.first.pk), "closed"))
        completed = self.operate(self.first, "open", request_id=request_id)
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        after = [(deepcopy(door.data), door.version) for door in (self.first, self.second)]
        self.assertEqual([door.data["door_state"] for door in (self.first, self.second)], ["closed", "open"])
        self.assertEqual(self.operate(self.first, "open", request_id=request_id), completed)
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.assertEqual([(door.data, door.version) for door in (self.first, self.second)], after)
        self.assertEqual(Receipt.objects.filter(request_id=request_id).count(), 1)
        self.assertEqual(self.runs()[0]["outcome"], "completed")

    def test_player_chain_skips_locking_another_door_and_missing_targets_are_logged(self):
        self.operate(self.second, "locked")
        self.configure(self.first, aim("interact", str(self.second.pk), "open", self_state="open"))
        self.operate(self.first, "open", user=self.player)
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.assertEqual((self.first.data["door_state"], self.second.data["door_state"]), ("open", "locked"))
        refused = self.runs()[0]["events"][-1]
        self.assertEqual((refused["doorId"], refused["message"]), (str(self.second.pk), "This door cannot be operated."))
        self.set_state(self.first, "closed")
        missing = str(uuid.uuid4())
        self.configure(self.first, aim("interact", missing, self_state="open"))
        self.operate(self.first, "open")
        self.first.refresh_from_db()
        self.assertEqual(self.first.data["door_state"], "open")
        step, = [row for row in self.runs()[0]["events"][0]["steps"] if row["id"] == "act"]
        self.assertIs(step["missing"], True)

    def test_authorized_change_state_lets_a_player_lever_unlock_another_door(self):
        self.operate(self.second, "locked")
        lever = aim("interact", str(self.second.pk), "open")
        lever["interact"][0][1]["players"] = True
        self.configure(self.first, lever)
        self.operate(self.first, "open", user=self.player)
        self.second.refresh_from_db()
        self.assertEqual(self.second.data["door_state"], "open")
        state_step, = [row for row in self.runs()[0]["events"][0]["steps"] if row["type"] == "state"]
        self.assertIs(state_step["players"], True)

    def test_authorized_interaction_opens_its_own_locked_door_for_a_player(self):
        self.configure(self.first, {"interact": (
            [node("open", "state", targetState="open", players=True)], [execution("event", "open")])})
        self.set_state(self.first, "locked")
        self.operate(self.first, "open", user=self.player)
        self.first.refresh_from_db()
        self.assertEqual(self.first.data["door_state"], "open")
        self.assertEqual(self.runs()[0]["outcome"], "completed")

    def test_set_barrier_and_control_sound_change_live_scene_state(self):
        from gravewright.audio.models import Playback
        track = str(self.sound.pk)
        self.configure(self.first, {"interact": (
            [node("ref", "reference", targetId=str(self.second.pk)),
             node("sight", "barrier", channel="vision", mode="pass"),
             node("walk", "barrier", channel="movement", mode="pass"),
             node("play", "sound", trackId=track, volume=.8),
             node("quiet", "soundControl", trackId=track, action="volume", volume=.2),
             node("stop", "soundControl", trackId=track, action="stop", volume=1)],
            [execution("event", "sight"), execution("sight", "walk"), execution("walk", "play"),
             execution("play", "quiet"), data("ref", "door", "sight", "target")])})
        self.operate(self.first, "open")
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.assertEqual((self.second.data["vision_behavior"], self.second.data["blocks_sight"]), ("pass", 0))
        self.assertEqual(self.first.data["movement_behavior"], "pass")
        voice, = [row for row in Playback.objects.get(scene=self.scene).data["ambient"] if row["trackId"] == track]
        self.assertEqual((voice["status"], voice["volume"]), ("playing", .2))
        steps = self.runs()[0]["events"][0]["steps"]
        self.assertIn({"id": "quiet", "type": "soundControl", "sound": "Door click", "action": "volume", "volume": .2}, steps)
        # The unconnected Stop control did not run, so the sound keeps playing.
        self.assertNotIn("stop", [step["id"] for step in steps])


class AuthorityContractTests(SimpleTestCase):
    def test_player_flag_barrier_modes_and_sound_controls_are_validated(self):
        track = str(uuid.uuid4())
        valid = blueprint({"interact": ([node("act", "state", targetState="open", players=True),
                                           node("wall", "barrier", channel="sound", mode="attenuate"),
                                           node("hush", "soundControl", trackId=track, action="stop", volume=1)],
                                          [execution("event", "act"), execution("act", "wall"), execution("wall", "hush")])})
        clean_blueprint(valid, track_ids={track})
        for path, value in (((1, "players"), False), ((2, "mode"), "attenuate_light"), ((2, "channel"), "smell"),
                            ((3, "action"), "pause"), ((3, "volume"), 2)):
            raw = deepcopy(valid)
            index, field = path
            raw["graphs"]["interact"]["nodes"][index][field] = value
            if field == "mode" and value == "attenuate_light":
                raw["graphs"]["interact"]["nodes"][index].update(channel="vision", mode="attenuate")
            with self.subTest(field=field, value=value), self.assertRaises(MapError):
                clean_blueprint(raw, track_ids={track})
        with self.assertRaisesMessage(MapError, "sound not found"):
            clean_blueprint(valid, track_ids=set())
