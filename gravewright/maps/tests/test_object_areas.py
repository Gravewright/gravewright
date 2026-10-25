"""Object area events start authored graphs on committed token crossings."""

from copy import deepcopy
from unittest.mock import patch
import uuid

from django.test import TestCase, override_settings

from gravewright.actors.models import Actor
from gravewright.maps import blueprint_testing, objects, regions, services
from gravewright.maps.blueprints import clean_blueprint, default_blueprint
from gravewright.maps.models import AutomationRun, Receipt, SceneObject
from gravewright.maps.zones import Geometry

from . import test_builder_blueprints as fixtures
from .test_levers import execution, node
from . import test_regions as region_fixtures


def area_blueprint(kind="lever", *, enter=None, exit=None):
    blueprint = default_blueprint(kind)
    for event, action in (("presence:enter", enter), ("presence:exit", exit)):
        if action is not None:
            blueprint["graphs"][event] = {"nodes": [node("event", "event", event=event), action],
                                           "edges": [execution("event", action["id"])]}
    return blueprint


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class ObjectAreaTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    token_command = region_fixtures.RegionTests.token_command
    place = region_fixtures.RegionTests.place
    move = region_fixtures.RegionTests.move

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.doc["doors"][0].pop("blueprint")
        self.art = self.asset("object-area.png", "#557722")
        self.doc["assets"].append({"assetId": str(self.art.pk), "role": "decoration"})
        self.object_id = str(uuid.uuid4())
        self.doc["decorations"] = [{"id": self.object_id, "layerId": self.doc["layers"][0]["id"],
            "assetId": str(self.art.pk), "x": 2, "y": 1, "width": 2, "height": 1, "rotation": 0,
            "lever": {"state": "off"}, "blueprint": area_blueprint(
                enter=node("light", "light", targetId=self.light_id, enabled=True),
                exit=node("light", "light", targetId=self.light_id, enabled=False))}]
        self.actor = Actor.objects.create(campaign=self.campaign, name="Area hero", data={},
                                          permissions={str(self.player.pk): "owner"})

    def owner(self):
        return self.scene.elements.get(kind="images", data__lever__isnull=False)

    def test_circular_area_runs_outside_artwork_without_interaction(self):
        self.doc["decorations"][0].update(presenceRadius=2, interactionEnabled=False)
        self.generated()
        owner = self.owner()
        self.assertEqual(owner.data["presenceRadius"], 128)
        shape = regions.object_shape(owner.data)
        self.assertTrue(Geometry.contains(shape, 192, 192, 0))
        self.assertFalse(Geometry.contains(shape, 310, 210, 0))
        token = self.place(0, 2.5)
        self.move(token, 2.5, 2.5, user=self.player)
        self.assertTrue(self.light_enabled())
        self.assertEqual(self.owner().data["lever"]["state"], "off")
        self.move(token, 5, 2.5, user=self.player)
        self.assertFalse(self.light_enabled())
        self.assertEqual([event["event"] for event in self.events()], ["presence:enter", "presence:exit"])

    def test_crossing_entire_circle_runs_enter_and_exit(self):
        self.doc["decorations"][0]["presenceRadius"] = 2
        self.generated()
        token = self.place(0, 2.5)
        self.move(token, 5, 2.5)
        self.assertEqual([event["event"] for event in self.events()], ["presence:enter", "presence:exit"])
        self.assertEqual(self.owner().data["areaPresence"]["occupants"], [])

    def test_circle_is_private_and_survives_native_move_and_source_projection(self):
        from gravewright.maps import builder_sync, extra_objects
        self.doc["decorations"][0]["presenceRadius"] = 2
        self.generated()
        owner = self.owner()
        moved = extra_objects.image(self.scene, {"x": 256}, owner.data)
        self.assertEqual(moved["presenceRadius"], 128)
        self.assertEqual(regions.object_shape(moved)["geometry"]["x"], 256)
        projected = builder_sync.projection(moved, "images", 64, {})
        self.assertEqual(projected["presenceRadius"], 2)
        reset = extra_objects.image(self.scene, {"presenceRadius": None}, moved)
        self.assertNotIn("presenceRadius", reset)
        self.assertEqual(regions.object_shape(reset)["geometry"]["shape"], "rect")
        state = objects.layer_state(self.scene, services.member(self.campaign.pk, self.player.pk))
        self.assertTrue(state["images"])
        self.assertTrue(all("presenceRadius" not in image for image in state["images"]))

    def test_builder_rejects_invalid_or_non_smart_activation_area(self):
        from gravewright.maps import builder_services
        who = services.member(self.campaign.pk, self.gm.pk)
        for radius in (True, 0, -.1, 201, "2", None):
            with self.subTest(radius=radius), self.assertRaises(services.MapError):
                self.doc["decorations"][0]["presenceRadius"] = radius
                builder_services.clean_document(self.doc, who)
        self.doc["decorations"][0]["presenceRadius"] = 2
        self.doc["decorations"][0].pop("lever")
        self.doc["decorations"][0].pop("blueprint")
        with self.assertRaises(services.MapError):
            builder_services.clean_document(self.doc, who)


    def events(self):
        return [event for run in AutomationRun.objects.filter(scene=self.scene).order_by("created_at", "id")
                for event in run.data["events"]]

    def light_enabled(self):
        self.light_object.refresh_from_db()
        return self.light_object.data["enabled"]

    def test_lever_and_torch_accept_area_starts_but_doors_keep_their_own_events(self):
        for kind in ("lever", "torch"):
            blueprint = area_blueprint(kind, enter=node("state", "state", targetState="on"),
                                       exit=node("state", "state", targetState="off"))
            self.assertEqual(set(clean_blueprint(blueprint)["graphs"]), {"presence:enter", "presence:exit"})
        invalid = default_blueprint("door")
        invalid["graphs"] = area_blueprint(enter=node("state", "state", targetState="on"))["graphs"]
        with self.assertRaises(services.MapError):
            clean_blueprint(invalid)

    def test_each_entry_and_exit_starts_without_changing_state_or_internal_movement_repeats(self):
        self.generated()
        one, two = self.place(), self.place()
        one.refresh_from_db()
        self.move(one, 2, user=self.player)
        self.assertTrue(self.light_enabled())
        self.assertEqual(self.owner().data["lever"]["state"], "off")
        self.move(one, 3)
        self.assertEqual(len(self.events()), 1)
        self.move(two, 2)
        self.assertEqual(self.owner().data["areaPresence"]["occupants"], sorted([str(one.pk), str(two.pk)]))
        self.move(one, 0)
        self.assertFalse(self.light_enabled(), "exit starts for every token, without an implicit last-token check")
        self.move(two, 0)
        self.assertEqual([event["event"] for event in self.events()],
                         ["presence:enter", "presence:enter", "presence:exit", "presence:exit"])
        runs = list(AutomationRun.objects.filter(scene=self.scene).order_by("created_at", "id"))
        self.assertEqual([run.data["context"]["count"] for run in runs], [1, 2, 1, 0])
        self.assertEqual(runs[0].data["context"]["tokenId"], str(one.pk))
        self.assertEqual(runs[0].data["context"]["actorId"], str(self.actor.pk))
        self.assertEqual(runs[0].data["context"]["userId"], str(self.player.pk))
        self.assertTrue(all(run.data["stateBefore"] == run.data["stateAfter"] == "off" for run in runs))

    def test_crossing_whole_area_in_one_committed_segment_starts_both_in_order(self):
        self.generated()
        token = self.place()
        self.move(token, 5, path=[[0, 0], [5, 0]])
        self.assertFalse(self.events(), "the accepted detour misses the object")
        self.move(token, 0)
        self.assertEqual([event["event"] for event in self.events()], ["presence:enter", "presence:exit"])
        self.assertEqual(self.owner().data["areaPresence"]["occupants"], [])
        self.assertFalse(self.light_enabled())

    def test_movement_along_distant_extension_of_area_edge_does_not_start_events(self):
        self.generated()
        token = self.place(0, .5)
        self.move(token, .5, .5)
        self.assertFalse(self.events())
        self.assertEqual(self.owner().data["areaPresence"]["occupants"], [])

    def test_movement_along_distant_extension_of_rotated_edge_does_not_start_events(self):
        self.doc["decorations"][0]["rotation"] = 45
        self.generated()
        points = regions.object_shape(self.owner().data)["geometry"]["points"]
        end, start = points[2], points[3]
        dx, dy = end["x"] - start["x"], end["y"] - start["y"]
        token = self.place((end["x"] + dx) / 64 - .5, (end["y"] + dy) / 64 - .5)
        self.move(token, (end["x"] + 2 * dx) / 64 - .5, (end["y"] + 2 * dy) / 64 - .5)
        self.assertFalse(self.events())

    def test_rotated_object_uses_oriented_box_and_not_its_axis_aligned_envelope(self):
        self.doc["decorations"][0]["rotation"] = 45
        self.generated()
        shape = regions.object_shape(self.owner().data)
        self.assertFalse(Geometry.contains(shape, 128, 64, 0))
        self.assertTrue(Geometry.contains(shape, 192, 96, 0))
        token = self.place(1.5, .5)
        self.assertFalse(self.events())
        self.move(token, 2.5)
        self.assertEqual([event["event"] for event in self.events()], ["presence:enter"])
        self.move(token, 1.5, .5)
        self.assertEqual([event["event"] for event in self.events()], ["presence:enter", "presence:exit"])

    def test_authored_box_includes_fitted_art_padding(self):
        self.generated()
        owner = self.owner()
        self.assertEqual(owner.data["natural_width"] * owner.data["scale"], 64)
        self.assertEqual(owner.data["lever"]["width"], 128)
        token = self.place(3.4)
        self.assertEqual(self.owner().data["areaPresence"]["occupants"], [str(token.pk)])
        self.assertTrue(self.light_enabled())

    def test_empty_object_can_explicitly_change_state_on_area_starts_without_art(self):
        source = self.doc["decorations"][0]
        source.update(empty=True, assetId=None, blueprint=area_blueprint(
            enter=node("state", "state", targetState="on"), exit=node("state", "state", targetState="off")))
        self.generated()
        token = self.place(2)
        self.assertEqual(self.owner().data["lever"]["state"], "on")
        self.move(token, 0)
        owner = self.owner()
        self.assertEqual(owner.data["lever"]["state"], "off")
        self.assertIsNone(owner.data["asset_id"])
        self.assertEqual(owner.data["src"], "")

    def test_torch_area_event_does_not_rotate_or_toggle_mechanism(self):
        source = self.doc["decorations"][0]
        source.pop("lever")
        source["torch"] = {"state": "off", "lit": True, "lightId": self.light_id}
        source["blueprint"]["kind"] = "torch"
        self.generated()
        token = self.place(2)
        self.move(token, 0)
        owner = self.scene.elements.get(kind="images", data__torch__isnull=False)
        self.assertEqual(owner.data["torch"]["state"], "off")
        self.assertTrue(owner.data["torch"]["lit"])
        self.assertEqual(owner.data["rotation"], 0)
        self.assertEqual(len(self.events()), 2)

    def test_authored_torch_turn_quietly_rebaselines_the_new_oriented_area(self):
        source = self.doc["decorations"][0]
        source.pop("lever")
        source["torch"] = {"state": "off", "lit": True, "lightId": self.light_id}
        source["blueprint"] = area_blueprint("torch", enter=node("state", "state", targetState="on"))
        self.generated()
        token = self.place(1.6)
        owner = self.scene.elements.get(kind="images", data__torch__isnull=False)
        self.assertEqual(owner.data["torch"]["state"], "on")
        self.assertEqual(owner.data["rotation"], 90)
        self.assertEqual(owner.data["areaPresence"]["occupants"], [],
                         "turning geometry is a quiet baseline, without a synthetic exit")
        self.assertEqual([event["event"] for event in self.events()], ["presence:enter"])
        self.move(token, 2.5)
        owner.refresh_from_db()
        self.assertEqual(owner.data["areaPresence"]["occupants"], [str(token.pk)])
        self.assertEqual([event["event"] for event in self.events()], ["presence:enter", "presence:enter"])

    def test_object_baseline_rejects_exceeding_scene_capacity_and_allows_existing_boundary(self):
        self.generated()
        owner = self.owner()
        candidate = SceneObject(scene=self.scene, kind="images", data=deepcopy(owner.data))
        with patch("gravewright.maps.regions.MAX_REGIONS", 1):
            regions.rebaseline_object(self.scene, owner)
            with self.assertRaisesMessage(services.MapError, "too many presence regions"):
                regions.rebaseline_object(self.scene, candidate)
            candidate.data.pop("blueprint")
            regions.rebaseline_object(self.scene, candidate)
        self.assertNotIn("areaPresence", candidate.data)

    def test_preview_and_blocked_movement_do_not_fire_or_change_membership(self):
        from gravewright.tokens import services as tokens
        self.generated()
        token = self.place()
        tokens.preview(self.campaign.pk, self.gm.pk, self.scene.pk,
                       [{"id": str(token.pk), "gridX": 2, "gridY": 1, "expectedVersion": token.version}], {})
        SceneObject.objects.create(scene=self.scene, kind="walls", data=objects.wall({
            "x1": 64, "y1": 0, "x2": 64, "y2": 128}))
        with self.assertRaisesMessage(services.MapError, "blocked"):
            self.move(token, 2, user=self.player)
        self.assertFalse(self.events())
        self.assertEqual(self.owner().data["areaPresence"]["occupants"], [])

    def test_retry_does_not_repeat_crossing_events(self):
        self.generated()
        token, request_id = self.place(), uuid.uuid4()
        version = token.version
        self.move(token, 2, rid=request_id)
        self.token_command("move", {"id": str(token.pk), "gridX": 2, "gridY": 1,
                           "expectedVersion": version}, rid=request_id)
        self.assertEqual(len(self.events()), 1)

    def test_paused_crossings_update_membership_but_only_future_events_execute_after_resume(self):
        self.generated()
        token = self.place()
        self.scene.settings["automationPaused"] = True
        self.scene.save(update_fields=["settings"])
        self.move(token, 2)
        self.assertFalse(self.events())
        self.assertEqual(self.owner().data["areaPresence"]["occupants"], [str(token.pk)])
        self.scene.settings["automationPaused"] = False
        self.scene.save(update_fields=["settings"])
        self.move(token, 3)
        self.assertFalse(self.events())
        self.move(token, 0)
        self.assertEqual([event["event"] for event in self.events()], ["presence:exit"])

    def test_failing_area_action_rolls_back_movement_ledger_and_receipt(self):
        self.generated()
        token, request_id = self.place(), uuid.uuid4()
        with override_settings(DYNAMIC_LIGHTING_ENABLED=False):
            with self.assertRaisesMessage(services.MapError, "Dynamic lighting is disabled"):
                self.move(token, 2, user=self.player, rid=request_id)
        token.refresh_from_db()
        self.assertEqual(token.grid_x, 0)
        self.assertEqual(self.owner().data["areaPresence"]["occupants"], [])
        self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())

    def test_token_removal_starts_exit_and_clears_ledger(self):
        self.generated()
        token = self.place(2)
        self.token_command("remove", {"tokenIds": [str(token.pk)]})
        self.assertEqual([event["event"] for event in self.events()], ["presence:enter", "presence:exit"])
        self.assertEqual(self.owner().data["areaPresence"]["occupants"], [])

    def test_area_event_budget_rolls_back_entire_move(self):
        self.generated()
        token = self.place()
        with patch("gravewright.maps.regions.MAX_PRESENCE_EVENTS", 1):
            with self.assertRaisesMessage(services.MapError, "too many presence regions"):
                self.move(token, 5)
        token.refresh_from_db()
        self.assertEqual(token.grid_x, 0)
        self.assertEqual(self.owner().data["areaPresence"]["occupants"], [])
        self.assertFalse(self.light_enabled())

    def test_unconnected_event_has_no_runtime_area_or_implicit_state_change(self):
        source = self.doc["decorations"][0]
        source["blueprint"]["graphs"] = {"presence:enter": {
            "nodes": [node("event", "event", event="presence:enter")], "edges": []}}
        self.generated()
        token = self.place(2)
        self.move(token, 0)
        self.assertFalse(self.events())
        self.assertNotIn("areaPresence", self.owner().data)
        self.assertEqual(self.owner().data["lever"]["state"], "off")

    def test_scene_rehearsal_accepts_object_area_event_and_preserves_real_state(self):
        self.generated()
        token = self.place(2)
        owner = self.owner()
        before = deepcopy(owner.data)
        count = AutomationRun.objects.filter(scene=self.scene).count()
        result = blueprint_testing.run(self.campaign.pk, self.gm.pk, self.scene.pk, owner.pk, {
            "request_id": str(uuid.uuid4()), "event": "presence:exit", "expected_version": owner.version,
            "tokenId": str(token.pk)})
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["run"]["stateAfter"], "off")
        self.assertEqual(result["run"]["context"]["presence"], "exit")
        self.assertEqual(result["run"]["context"]["count"], 1)
        self.assertFalse(next(row["after"]["data"]["enabled"] for row in result["changes"]["elements"]
                              if row["id"] == str(self.light_object.pk)))
        self.assertEqual(self.owner().data, before)
        self.assertTrue(self.light_enabled())
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)

    def test_draft_rehearsal_places_test_actor_inside_object_and_discards_everything(self):
        source = self.doc["decorations"][0]
        source.update(empty=True, assetId=None, blueprint=area_blueprint(enter=node("state", "state", targetState="on")))
        before = list(SceneObject.objects.order_by("pk").values())
        result = blueprint_testing.run_draft(self.campaign.pk, self.gm.pk, {
            "request_id": str(uuid.uuid4()), "document": self.doc, "elementId": self.object_id,
            "event": "presence:enter", "actorId": str(self.actor.pk)})
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["run"]["stateAfter"], "on")
        self.assertEqual(result["run"]["context"]["count"], 1)
        self.assertEqual(result["run"]["context"]["actorId"], str(self.actor.pk))
        self.assertEqual(list(SceneObject.objects.order_by("pk").values()), before)

    def test_teleport_from_object_area_updates_departure_and_arrival_without_stale_membership(self):
        destination_id = str(uuid.uuid4())
        self.doc["regions"] = [{"id": destination_id, "layerId": self.doc["layers"][0]["id"],
            "name": "Arrival", "x": 6, "y": 5, "width": 2, "height": 1, "enabled": True}]
        self.doc["decorations"][0]["blueprint"] = area_blueprint(
            enter=node("travel", "teleport", destinationId=destination_id),
            exit=node("light", "light", targetId=self.light_id, enabled=True))
        self.generated()
        token = self.place()
        self.move(token, 2, user=self.player)
        self.assertGreaterEqual(token.grid_x, 6)
        self.assertEqual(self.owner().data["areaPresence"]["occupants"], [])
        arrival = self.scene.elements.get(kind="zones", data__region__isnull=False)
        self.assertEqual(arrival.data["region"]["occupants"], [str(token.pk)])
        self.assertTrue(self.light_enabled())
        self.assertEqual([event["event"] for event in self.events()], ["presence:enter", "presence:exit"])
