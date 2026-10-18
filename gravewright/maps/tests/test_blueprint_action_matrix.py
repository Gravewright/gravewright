"""Cross-capability execution matrix using real generated native scene objects.

Each subtest runs through validated GM commands in its own rolled-back savepoint.
Assertions distinguish actual effects, unsupported capabilities and absent bindings;
passing validation alone is never treated as a successful runtime action.
"""

from copy import deepcopy
from contextlib import contextmanager
import uuid

from django.db import transaction
from django.test import TestCase, override_settings

from gravewright.audio.models import Playback, Track
from gravewright.maps import objects, services
from gravewright.maps.blueprints import KIND_STATES, WRITABLE_STATES, default_blueprint
from gravewright.maps.models import AutomationRun, Broadcast, Scene, SceneObject

from . import test_levers as fixtures
from .test_builder_blueprints import graph
from .test_blueprint_references import data, execution, node


ELEMENT_ACTIONS = (
    "state", "interact", "flame", "reveal", "barrier", "move", "rotate",
    "setInteraction", "setRegion", "setVisibility", "setAppearance", "emitEvent",
)
KINDS = ("door", "lever", "torch", "empty", "region", "image", "light")
SUPPORT = {
    "state": {"door", "lever", "torch", "empty"},
    "interact": {"door", "lever", "torch", "empty"},
    "flame": {"torch"}, "reveal": {"door"}, "barrier": {"door"},
    "move": set(KINDS), "rotate": set(KINDS),
    "setInteraction": {"door", "lever", "torch", "empty"},
    "setRegion": {"region"},
    "setVisibility": {"door", "lever", "torch", "image"},
    "setAppearance": {"door", "lever", "torch", "image"},
    "emitEvent": {"door", "lever", "torch", "empty", "region"},
}


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class ActionTargetMatrixTests(TestCase):
    asset = fixtures.LeverTests.asset
    post = fixtures.LeverTests.post
    save = fixtures.LeverTests.save
    generate = fixtures.LeverTests.generate
    files = fixtures.LeverTests.files

    def setUp(self):
        fixtures.LeverTests.setUp(self)
        self.doc["doors"][0]["blueprint"] = default_blueprint("door")
        self.source_id = self.doc["doors"][0]["id"]
        layer = self.doc["layers"][0]["id"]
        door = {**deepcopy(self.doc["doors"][0]), "id": str(uuid.uuid4()),
                "x1": 1, "x2": 2, "y1": 2, "y2": 2,
                "blueprint": self.handler("door")}
        self.doc["doors"].append(door)
        self.ids = {"door": door["id"], "lever": self.lever_id}
        lever = self.doc["decorations"][0]
        lever["blueprint"] = self.handler("lever")
        for index, kind in enumerate(("torch", "empty", "image")):
            identifier = self.ids[kind] = str(uuid.uuid4())
            decoration = {"id": identifier, "layerId": layer, "assetId": str(self.handle_off.pk),
                          "x": index + 1, "y": 5, "width": 1, "height": 1, "rotation": 0}
            if kind == "empty":
                decoration.update(empty=True, assetId=None, lever={"state": "off"},
                                  blueprint=self.handler("lever"))
            elif kind == "torch":
                decoration.update(torch={"state": "off", "lit": True, "lightId": self.light_id},
                                  blueprint=self.handler("torch"))
            self.doc["decorations"].append(decoration)
        identifier = self.ids["region"] = str(uuid.uuid4())
        self.doc["regions"] = [{"id": identifier, "layerId": layer, "name": "Matrix area",
            "x": 1, "y": 1, "width": 2, "height": 1, "enabled": True,
            "blueprint": self.handler("region")}]
        self.ids["light"] = self.light_id
        self.doc["lights"][0]["enabled"] = True
        saved = self.save()
        self.assertEqual(saved.status_code, 200, saved.content)
        generated = self.generate()
        self.assertEqual(generated.status_code, 200, generated.content)
        self.scene = Scene.objects.get(pk=generated.json()["scene"]["id"])
        self.scene.visibility = "players"
        self.scene.save(update_fields=["visibility"])
        Broadcast.objects.update_or_create(campaign=self.campaign, defaults={"scene": self.scene})
        self.door_object = self.scene.elements.get(pk=uuid.uuid5(self.scene.pk, self.source_id))
        self.targets = {kind: self.scene.elements.get(pk=uuid.uuid5(self.scene.pk, identifier))
                        for kind, identifier in self.ids.items()}
        self.light_object = self.targets["light"] = SceneObject.objects.create(scene=self.scene, kind="lights",
            data=objects.light({"x": 96, "y": 96, "enabled": False}))
        # Native configuration makes Reveal's effect observable, independently of artwork.
        target = self.targets["door"]
        target.data.update(presentation="secret", discovered=False)
        target.save(update_fields=["data"])
        self.foreign_scene = Scene.objects.create(campaign=self.other, name="Foreign", width=512, height=512)
        self.foreign_door = SceneObject.objects.create(scene=self.foreign_scene, kind="walls",
            data=objects.wall({"x1": 10, "y1": 10, "x2": 70, "y2": 10, "kind": "door"}))
        self.foreign_light = SceneObject.objects.create(scene=self.foreign_scene, kind="lights",
            data=objects.light({"x": 10, "y": 10}))
        self.foreign_sound = Track.objects.create(campaign=self.other, name="Foreign sound", duration=1)

    @staticmethod
    def handler(kind):
        result = default_blueprint(kind)
        marker = {"type": "setVariable", "scope": "element", "name": "MatrixHandled",
                  "valueType": "text", "value": "interact"}
        if kind != "region":
            result["graphs"]["interact"] = graph("interact",
                {"type": "state", "targetState": "open" if kind == "door" else "on"}, marker)
        result["graphs"]["signal:Probe"] = graph("signal:Probe", {**marker, "value": "signal"})
        return result

    @contextmanager
    def cell(self, **labels):
        with self.subTest(**labels), transaction.atomic():
            try:
                yield
            finally:
                transaction.set_rollback(True)

    def action(self, kind, target_kind="lever"):
        fields = {
            "state": {"targetState": "open" if target_kind == "door" else "on"},
            "interact": {}, "flame": {"enabled": False}, "reveal": {},
            "barrier": {"channel": "movement", "mode": "pass"},
            "move": {"dx": 1, "dy": .5}, "rotate": {"degrees": 90},
            "setInteraction": {"enabled": False}, "setRegion": {"enabled": False},
            "setVisibility": {"visible": False}, "setAppearance": {"assetId": str(self.handle_on.pk)},
            "emitEvent": {"scope": "element", "name": "Probe"},
            "light": {"targetId": str(self.light_object.pk), "enabled": True},
            "sound": {"trackId": str(self.sound.pk), "volume": .6},
            "soundControl": {"trackId": str(self.sound.pk), "volume": .2, "action": "volume"},
        }
        return node("act", kind, **fields[kind])

    def definition(self, action, identifiers, *, resource="element", group=False, before=()):
        result = default_blueprint("door")
        if group:
            reference = node("ref", "elementGroup", name="Matrix targets", memberType=resource,
                             targetIds=identifiers)
            output = "targets"
        else:
            kind, field, output = {"element": ("reference", "targetId", "door"),
                                  "light": ("lightReference", "targetId", "light"),
                                  "sound": ("soundReference", "trackId", "sound")}[resource]
            reference = node("ref", kind, **{field: identifiers[0]})
        nodes = [node("event", "event", event="interact"), reference, *before, action]
        ordered = ["event", *[item["id"] for item in before], "act"]
        result["graphs"]["interact"] = {"nodes": nodes,
            "edges": [execution(a, b) for a, b in zip(ordered, ordered[1:])]
                + [data("ref", output, "act", "target")]}
        return result

    def configure(self, blueprint):
        self.door_object.refresh_from_db()
        return services.command(self.campaign.pk, self.gm.pk, "objects", {
            "mapId": str(self.scene.pk), "area": "walls", "action": "update",
            "data": {"wall_id": str(self.door_object.pk), "version": self.door_object.version,
                     "blueprint": blueprint}}, uuid.uuid4())

    def run_action(self, blueprint):
        self.configure(blueprint)
        services.command(self.campaign.pk, self.gm.pk, "objects", {
            "mapId": str(self.scene.pk), "area": "walls", "action": "door",
            "data": {"wall_id": str(self.door_object.pk), "door_state": "open"}}, uuid.uuid4())
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed",
                         "The event and a connected target must never toggle Self.")
        events = AutomationRun.objects.filter(scene=self.scene).latest("created_at").data["events"]
        return next(step for step in events[0]["steps"] if step["id"] == "act"), events

    def assert_effect(self, action, kind, before, after):
        if action in ("state", "interact"):
            state = after["door_state"] if kind == "door" else after["torch" if kind == "torch" else "lever"]["state"]
            self.assertEqual(state, "open" if kind == "door" else "on")
            if action == "state":
                self.assertNotIn("automationVariables", after, "State never executes a target handler.")
            else:
                self.assertEqual(after["automationVariables"]["MatrixHandled"]["value"], "interact")
        elif action == "flame":
            self.assertFalse(after["torch"]["lit"])
            self.assertEqual(after["torch"]["state"], "off")
        elif action == "reveal":
            self.assertTrue(after["discovered"])
        elif action == "barrier":
            self.assertEqual(after["movement_behavior"], "pass")
        elif action == "move":
            if kind == "door":
                self.assertEqual((after["x1"], after["x2"]), (before["x1"] + 64, before["x2"] + 64))
                self.assertEqual(after["y1"], before["y1"] + 32)
            else:
                previous, current = (before["geometry"], after["geometry"]) if kind == "region" else (before, after)
                self.assertEqual((current["x"], current["y"]), (previous["x"] + 64, previous["y"] + 32))
        elif action == "rotate":
            if kind == "door":
                self.assertAlmostEqual(after["x1"], after["x2"])
                self.assertNotEqual(after["y1"], after["y2"])
            elif kind == "region":
                self.assertEqual((after["geometry"]["width"], after["geometry"]["height"]),
                                 (before["geometry"]["height"], before["geometry"]["width"]))
            else:
                self.assertEqual(after["rotation"], (before.get("rotation", 0) + 90) % 360)
        elif action == "setInteraction":
            self.assertIs(after["interactionEnabled"], False)
        elif action == "setRegion":
            self.assertIs(after["enabled"], False)
            self.assertEqual(after["region"]["occupants"], [])
        elif action == "setVisibility":
            if kind == "image":
                self.assertEqual(after["layer"], "gm-image-layer")
            else:
                self.assertEqual(after["sprite"], {"appearance": "hidden"})
        elif action == "setAppearance":
            if kind == "door":
                self.assertEqual(after["sprite"], {"appearance": "asset", "assetId": str(self.handle_on.pk)})
            else:
                self.assertEqual(after["asset_id"], str(self.handle_on.pk))
        elif action == "emitEvent":
            self.assertEqual(after["automationVariables"]["MatrixHandled"]["value"], "signal")

    def test_element_actions_by_native_kind_and_single_or_group_binding(self):
        """168 cells: twelve actions × seven target kinds × two binding types."""
        for action in ELEMENT_ACTIONS:
            for kind in KINDS:
                for group in (False, True):
                    with self.cell(action=action, kind=kind, group=group):
                        target = SceneObject.objects.get(pk=self.targets[kind].pk)
                        before, version = deepcopy(target.data), target.version
                        resource = "light" if kind == "light" and action in ("move", "rotate") else "element"
                        definition = self.definition(self.action(action, kind), [str(target.pk)],
                                                     resource=resource, group=group)
                        # A group promises its resource kind; unlike legacy singular
                        # references, element groups cannot contain native lights.
                        if kind == "light" and resource == "element" and group:
                            with self.assertRaisesMessage(services.MapError, "this scene"):
                                self.configure(definition)
                            target.refresh_from_db()
                            self.assertEqual((target.data, target.version), (before, version))
                            continue
                        step, events = self.run_action(definition)
                        target.refresh_from_db()
                        if kind in SUPPORT[action]:
                            self.assertFalse(step.get("missing"), step)
                            self.assertFalse(step.get("unsupported"), step)
                            self.assert_effect(action, kind, before, target.data)
                            if group or action in ("interact", "move", "rotate", "setInteraction", "setRegion", "setVisibility", "setAppearance"):
                                self.assertEqual(step["targetIds"], [str(target.pk)])
                            expected = "interact" if action == "interact" else "signal:Probe" if action == "emitEvent" else None
                            self.assertEqual([event["event"] for event in events[1:]], [expected] if expected else [])
                        else:
                            self.assertTrue(step.get("unsupported"), step)
                            self.assertEqual(step.get("unsupportedIds"), [str(target.pk)])
                            self.assertFalse(step.get("missing"), step)
                            self.assertEqual((target.data, target.version), (before, version))
                            self.assertEqual(len(events), 1)

    def test_absent_targets_are_inert_without_falling_back_to_self(self):
        """24 cells: every element action with absent singular/group bindings."""
        for action in ELEMENT_ACTIONS:
            for group in (False, True):
                with self.cell(action=action, group=group):
                    missing = str(uuid.uuid4())
                    before = [(row.pk, deepcopy(row.data), row.version) for row in self.targets.values()]
                    step, events = self.run_action(self.definition(self.action(action), [missing], group=group))
                    self.assertTrue(step.get("missing"), step)
                    self.assertEqual(step.get("missingIds"), [missing])
                    self.assertEqual(len(events), 1)
                    self.assertEqual([(pk, SceneObject.objects.get(pk=pk).data, SceneObject.objects.get(pk=pk).version)
                                      for pk, _, _ in before], before)

    def test_mixed_element_groups_apply_valid_members_once_and_report_missing_members(self):
        """12 cells: valid, unsupported and missing members in one typed set."""
        for action in ELEMENT_ACTIONS:
            with self.cell(action=action):
                good_kind = next(kind for kind in KINDS if kind in SUPPORT[action] and kind != "light")
                bad_kind = next((kind for kind in KINDS if kind not in SUPPORT[action] and kind != "light"), None)
                good = SceneObject.objects.get(pk=self.targets[good_kind].pk)
                before = deepcopy(good.data)
                missing = str(uuid.uuid4())
                identifiers = [str(good.pk), missing]
                if bad_kind:
                    bad = SceneObject.objects.get(pk=self.targets[bad_kind].pk)
                    bad_before = (deepcopy(bad.data), bad.version)
                    identifiers.append(str(bad.pk))
                step, _ = self.run_action(self.definition(self.action(action, good_kind), identifiers, group=True))
                good.refresh_from_db()
                self.assert_effect(action, good_kind, before, good.data)
                self.assertEqual(step["targetIds"], [str(good.pk)])
                self.assertTrue(step["missing"])
                self.assertEqual(step["missingIds"], [missing])
                if bad_kind:
                    bad.refresh_from_db()
                    self.assertEqual((bad.data, bad.version), bad_before)
                    self.assertTrue(step.get("unsupported"), step)
                    self.assertEqual(step.get("unsupportedIds"), [str(bad.pk)])

    def test_cross_scene_bindings_never_modify_foreign_objects(self):
        """24 cells: all actions reject typed foreign sets or leave legacy refs inert."""
        for action in ELEMENT_ACTIONS:
            for group in (False, True):
                with self.cell(action=action, group=group):
                    before = (deepcopy(self.foreign_door.data), self.foreign_door.version)
                    definition = self.definition(self.action(action, "door"), [str(self.foreign_door.pk)], group=group)
                    if group:
                        with self.assertRaisesMessage(services.MapError, "this scene"):
                            self.configure(definition)
                    else:
                        step, events = self.run_action(definition)
                        self.assertTrue(step["missing"])
                        self.assertEqual(step["missingIds"], [str(self.foreign_door.pk)])
                        self.assertEqual(len(events), 1)
                    self.foreign_door.refresh_from_db()
                    self.assertEqual((self.foreign_door.data, self.foreign_door.version), before)

    def test_light_actions_bind_only_scene_lights_and_keep_missing_bindings_inert(self):
        """18 cells: enable/disable × legacy/reference/set × live/absent/foreign."""
        for enabled in (False, True):
            for binding in ("legacy", "reference", "group"):
                for status in ("live", "missing", "foreign"):
                    with self.cell(enabled=enabled, binding=binding, status=status):
                        target = self.scene.elements.get(pk=self.light_object.pk)
                        target.data["enabled"] = not enabled
                        target.save(update_fields=["data"])
                        before = (deepcopy(target.data), target.version)
                        identifier = str(target.pk) if status == "live" else (
                            str(self.foreign_light.pk) if status == "foreign" else str(uuid.uuid4()))
                        action = {**self.action("light"), "targetId": identifier, "enabled": enabled}
                        if binding == "legacy":
                            definition = default_blueprint("door")
                            definition["graphs"]["interact"] = graph("interact", action)
                        else:
                            # Connected bindings replace a valid legacy fallback.
                            action["targetId"] = str(target.pk)
                            definition = self.definition(action, [identifier], resource="light", group=binding == "group")
                        if status == "foreign" or status == "missing" and binding == "legacy":
                            with self.assertRaises(services.MapError):
                                self.configure(definition)
                            self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())
                        else:
                            step, _ = self.run_action(definition)
                            target.refresh_from_db()
                            if status == "live":
                                self.assertIs(target.data["enabled"], enabled)
                                if binding != "legacy":
                                    self.assertEqual(step["targetIds"], [identifier])
                            else:
                                self.assertTrue(step["missing"])
                                self.assertEqual(step["missingIds"], [identifier])
                        if status != "live":
                            target.refresh_from_db()
                            self.assertEqual((target.data, target.version), before)
                        self.foreign_light.refresh_from_db()
                        self.assertTrue(self.foreign_light.data["enabled"])

    def test_sound_actions_bind_campaign_tracks_and_preserve_authored_order(self):
        """27 cells: play/volume/stop × legacy/reference/set × live/absent/foreign."""
        for operation in ("play", "volume", "stop"):
            for binding in ("legacy", "reference", "group"):
                for status in ("live", "missing", "foreign"):
                    with self.cell(operation=operation, binding=binding, status=status):
                        identifier = str(self.sound.pk) if status == "live" else (
                            str(self.foreign_sound.pk) if status == "foreign" else str(uuid.uuid4()))
                        action = self.action("sound" if operation == "play" else "soundControl")
                        if operation != "play":
                            action["action"] = operation
                        action["trackId"] = identifier if binding == "legacy" else str(self.sound.pk)
                        before = [] if operation == "play" else [node("play", "sound", trackId=str(self.sound.pk), volume=.6)]
                        if binding == "legacy":
                            definition = default_blueprint("door")
                            definition["graphs"]["interact"] = graph("interact", *before, action)
                            # graph() generates action identifiers rather than retaining act.
                            definition["graphs"]["interact"]["nodes"][-1]["id"] = "act"
                            definition["graphs"]["interact"]["edges"][-1]["to"] = "act"
                        else:
                            definition = self.definition(action, [identifier], resource="sound",
                                group=binding == "group", before=before)
                        if status == "foreign" or status == "missing" and binding == "legacy":
                            with self.assertRaises(services.MapError):
                                self.configure(definition)
                            self.assertFalse(Playback.objects.filter(scene=self.scene).exists())
                            continue
                        step, _ = self.run_action(definition)
                        playback = Playback.objects.filter(scene=self.scene).first()
                        ambient = playback.data["ambient"] if playback else []
                        if status == "missing":
                            self.assertTrue(step["missing"])
                            self.assertEqual(step["missingIds"], [identifier])
                            self.assertEqual([voice["volume"] for voice in ambient], [] if operation == "play" else [.6])
                        elif operation == "stop":
                            self.assertEqual([(voice["trackId"], voice["status"], voice["position"]) for voice in ambient],
                                             [(str(self.sound.pk), "stopped", 0)])
                        else:
                            self.assertEqual([(voice["trackId"], voice["volume"]) for voice in ambient],
                                             [(str(self.sound.pk), .6 if operation == "play" else .2)])
                        if status == "live" and binding != "legacy":
                            self.assertEqual(step["targetIds"], [identifier])
                        self.assertFalse(Playback.objects.filter(scene=self.foreign_scene).exists())

    def test_all_writable_states_against_every_target_capability(self):
        """70 cells: all five writable state values × seven kinds × two bindings."""
        for state in WRITABLE_STATES:
            for kind in KINDS:
                for group in (False, True):
                    with self.cell(state=state, kind=kind, group=group):
                        target = SceneObject.objects.get(pk=self.targets[kind].pk)
                        before = (deepcopy(target.data), target.version)
                        definition = self.definition({**self.action("state", kind), "targetState": state},
                                                     [str(target.pk)], group=group)
                        if kind == "light" and group:
                            with self.assertRaisesMessage(services.MapError, "this scene"):
                                self.configure(definition)
                            continue
                        step, events = self.run_action(definition)
                        target.refresh_from_db()
                        target_kind = "lever" if kind == "empty" else kind
                        if kind in SUPPORT["state"] and state in KIND_STATES[target_kind]:
                            field = "torch" if kind == "torch" else "lever"
                            actual = target.data["door_state"] if kind == "door" else target.data[field]["state"]
                            self.assertEqual(actual, state)
                            self.assertFalse(step.get("unsupported"), step)
                            self.assertNotIn("automationVariables", target.data)
                        else:
                            self.assertTrue(step["unsupported"])
                            self.assertEqual(step.get("unsupportedIds"), [str(target.pk)])
                            self.assertEqual((target.data, target.version), before)
                        self.assertEqual(len(events), 1, "State values never start target graphs.")

    def test_interaction_distinguishes_native_authored_empty_and_authored_handlers(self):
        """15 cells: each intelligent kind with native/empty/explicit handlers."""
        for kind in ("door", "lever", "torch", "empty", "region"):
            for behavior in ("native", "empty", "explicit"):
                with self.cell(kind=kind, behavior=behavior):
                    target = SceneObject.objects.get(pk=self.targets[kind].pk)
                    target_kind = "lever" if kind == "empty" else kind
                    if behavior == "native":
                        target.data.pop("blueprint", None)
                    elif behavior == "empty":
                        target.data["blueprint"] = default_blueprint(target_kind)
                    # Player interaction flags do not block authored GM automation.
                    if kind != "region":
                        target.data["interactionEnabled"] = False
                    target.save(update_fields=["data"])
                    before = (deepcopy(target.data), target.version)
                    step, events = self.run_action(self.definition(self.action("interact", kind), [str(target.pk)]))
                    target.refresh_from_db()
                    if kind == "region":
                        self.assertTrue(step["unsupported"])
                        self.assertEqual(step.get("unsupportedIds"), [str(target.pk)])
                        self.assertEqual((target.data, target.version), before)
                    elif behavior == "empty":
                        self.assertEqual((target.data, target.version), before)
                        self.assertNotIn("automationVariables", target.data)
                    else:
                        field = "torch" if kind == "torch" else "lever"
                        actual = target.data["door_state"] if kind == "door" else target.data[field]["state"]
                        self.assertEqual(actual, "open" if kind == "door" else "on")
                        if behavior == "native":
                            self.assertNotIn("automationVariables", target.data)
                        else:
                            self.assertEqual(target.data["automationVariables"]["MatrixHandled"]["value"], "interact")
                    if kind == "torch" and behavior in ("native", "explicit"):
                        self.assertEqual(target.data["rotation"], 90)
                        self.assertIs(target.data["torch"]["lit"], True)

    def test_resource_groups_apply_each_live_member_and_isolate_missing_members(self):
        """Four cells: light/play/volume/stop with two resources and an absent UUID."""
        other_light = SceneObject.objects.create(scene=self.scene, kind="lights",
            data=objects.light({"x": 192, "y": 192, "enabled": False}))
        other_sound = Track.objects.create(campaign=self.campaign, name="Other real sound", duration=1,
            content_type=self.sound.content_type, kind="effect", loop=False, file=self.sound.file.name)
        for operation in ("light", "play", "volume", "stop"):
            with self.cell(operation=operation):
                missing = str(uuid.uuid4())
                resource = "light" if operation == "light" else "sound"
                identifiers = ([str(self.light_object.pk), str(other_light.pk)] if resource == "light"
                               else [str(self.sound.pk), str(other_sound.pk)])
                action = self.action("light" if operation == "light" else "sound" if operation == "play" else "soundControl")
                before = []
                if operation in ("volume", "stop"):
                    action["action"] = operation
                    before = [node("play" + str(index), "sound", trackId=identifier, volume=.6)
                              for index, identifier in enumerate(identifiers)]
                step, _ = self.run_action(self.definition(action, [*identifiers, missing], resource=resource,
                                                         group=True, before=before))
                self.assertEqual(step["targetIds"], identifiers)
                self.assertEqual(step["targetsCount"], 2)
                self.assertTrue(step["missing"])
                self.assertEqual(step["missingIds"], [missing])
                if operation == "light":
                    self.assertTrue(all(SceneObject.objects.get(pk=identifier).data["enabled"]
                                        for identifier in identifiers))
                else:
                    voices = Playback.objects.get(scene=self.scene).data["ambient"]
                    self.assertEqual([voice["trackId"] for voice in voices], identifiers)
                    self.assertEqual([voice["volume"] for voice in voices], [.2, .2] if operation == "volume" else [.6, .6])
                    self.assertEqual([voice["status"] for voice in voices], ["stopped", "stopped"]
                                     if operation == "stop" else ["playing", "playing"])
