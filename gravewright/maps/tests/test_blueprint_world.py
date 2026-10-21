"""Recipient-safe presentation and bounded same-scene portal transport."""

from copy import deepcopy
from datetime import timedelta
import uuid
from unittest.mock import patch

from django.db import DatabaseError
from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.campaigns.models import Membership
from gravewright.journals.models import Journal
from gravewright.maps import objects, services
from gravewright.maps.blueprints import clean_blueprint, default_blueprint, evaluate_graph
from gravewright.maps.blueprint_world import presentation_catalog, presentation_for
from gravewright.maps.models import AutomationDelay, AutomationRun, Broadcast, Scene, SceneObject
from gravewright.tokens.models import Token

from . import test_builder_blueprints as fixtures
from . import test_regions as region_fixtures
from . import test_blueprint_delays as delay_fixtures
from .test_blueprint_references import blueprint, data, execution, node


EVENT = "interact"


def chain(*actions, event=EVENT, kind="door"):
    raw = blueprint({event: (list(actions), [execution(a["id"], b["id"])
        for a, b in zip([node("event", "event", event=event), *actions], actions)])})
    raw["kind"] = kind
    raw["states"] = default_blueprint(kind)["states"]
    return raw


def audience(scope="trigger", **values):
    return {"scope": scope, **values}


class WorldContractTests(SimpleTestCase):
    def test_new_actions_are_v2_and_keep_layout_separate_from_focus(self):
        identifiers = [str(uuid.uuid4()) for _ in range(3)]
        actions = [node("visible", "setVisibility", visible=False), node("art", "setAppearance", assetId=identifiers[0]),
                   node("message", "showMessage", text="  " + identifiers[1] + "  ", audience=audience()),
                   node("handout", "showHandout", journalId=identifiers[1], audience=audience("players")),
                   node("camera", "cameraFocus", focusX=1000, focusY=0, audience=audience()),
                   node("portal", "teleport", destinationId=identifiers[2])]
        raw = chain(*actions)
        before = deepcopy(raw)
        result = evaluate_graph(raw, EVENT, "closed")
        self.assertEqual(result["actions"], actions)
        self.assertEqual(result["actions"][4]["x"], actions[4]["x"])
        self.assertEqual(result["actions"][4]["focusX"], 1000)
        self.assertEqual(raw, before)
        for action in actions:
            legacy = chain(action)
            legacy["version"] = 1
            for graph in legacy["graphs"].values():
                for edge in graph["edges"]:
                    edge.pop("kind", None)
            with self.assertRaisesMessage(services.MapError, "node type"):
                clean_blueprint(legacy)

    def test_audience_shape_uuid_uniqueness_and_limits_are_strict(self):
        identifier = str(uuid.uuid4())
        valid = node("message", "showMessage", text="Hello", audience=audience("users", userIds=[identifier]))
        clean_blueprint(chain(valid))
        for value in ({}, {"scope": "everyone"}, audience(userIds=[]), audience("players", userIds=[identifier]),
                      audience("users"), audience("users", userIds=[]), audience("users", userIds=["bad"]),
                      audience("users", userIds=[identifier, identifier.upper()]),
                      audience("users", userIds=[str(uuid.uuid4()) for _ in range(65)])):
            with self.subTest(audience=value), self.assertRaises(services.MapError):
                clean_blueprint(chain({**valid, "audience": value}))

    def test_messages_coordinates_visibility_and_references_are_validated(self):
        actions = [node("message", "showMessage", text=value, audience=audience())
                   for value in ("", " ", "A\x00", "a" * 2001, False)]
        actions += [node("camera", "cameraFocus", focusX=value, focusY=0, audience=audience())
                    for value in (-1, 1000.1, True, float("nan"), float("inf"))]
        actions += [node("visible", "setVisibility", visible=1), node("art", "setAppearance", assetId="bad"),
                    node("portal", "teleport", destinationId="bad"),
                    node("handout", "showHandout", journalId="bad", audience=audience())]
        for action in actions:
            with self.subTest(action=action), self.assertRaises(services.MapError):
                clean_blueprint(chain(action))
        with self.assertRaises(services.MapError):
            clean_blueprint(chain(node("art", "setAppearance", assetId=str(uuid.uuid4()))), asset_ids=[])

    def test_world_actions_have_no_untrusted_token_or_recipient_data_inputs(self):
        raw = chain(node("portal", "teleport", destinationId=str(uuid.uuid4())))
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("target", "reference", targetId=str(uuid.uuid4())))
        graph["edges"].append(data("target", "door", "portal", "target"))
        with self.assertRaisesMessage(services.MapError, "connection input"):
            clean_blueprint(raw)
        raw = chain(node("portal", "teleport", destinationId=str(uuid.uuid4()), tokenId=str(uuid.uuid4())))
        with self.assertRaisesMessage(services.MapError, "Unknown blueprint"):
            clean_blueprint(raw)

    def test_visual_nodes_share_materials_while_state_art_remains_restricted(self):
        material = str(uuid.uuid4())
        raw = chain(node("art", "setAppearance", assetId=material))
        clean_blueprint(raw, asset_ids=[], appearance_asset_ids=[material])
        raw["graphs"][EVENT]["nodes"][1] = node("art", "sprite", appearance="asset", assetId=material)
        clean_blueprint(raw, asset_ids=[], appearance_asset_ids=[material])
        raw["states"]["open"] = {"appearance": "asset", "assetId": material}
        with self.assertRaises(services.MapError):
            clean_blueprint(raw, asset_ids=[], appearance_asset_ids=[material])


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class WorldPresentationTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    command = fixtures.BuilderBlueprintTests.command
    update_scene = fixtures.BuilderBlueprintTests.update_scene
    due = delay_fixtures.DelayRuntimeTests.due

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.doc["doors"][0]["blueprint"] = chain()
        self.journal = Journal.objects.create(campaign=self.campaign, title="Readable handout", visibility="shared")

    def test_catalog_is_gm_only_and_contains_campaign_owned_entries(self):
        Journal.objects.create(campaign=self.other, title="Other private document")
        result = presentation_catalog(self.membership)
        self.assertEqual({row["id"] for row in result["users"]}, {str(self.gm.pk), str(self.player.pk), str(self.streamer.pk)})
        self.assertEqual(result["handouts"], [{"id": str(self.journal.pk), "name": self.journal.title, "type": self.journal.type}])
        with self.assertRaises(services.MapError):
            presentation_catalog(Membership.objects.get(campaign=self.campaign, user=self.player))

    def test_presentations_commit_once_plain_text_and_convert_focus_cells(self):
        text = "<img src=x onerror=alert(1)> Authored message"
        self.doc["doors"][0]["blueprint"] = chain(
            node("message", "showMessage", text=text, audience=audience()),
            node("handout", "showHandout", journalId=str(self.journal.pk), audience=audience()),
            node("camera", "cameraFocus", focusX=2, focusY=3, audience=audience()))
        self.generated()
        request_id = uuid.uuid4()
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            self.command("closed", user=self.player, request_id=request_id)
            self.assertFalse(send.called)
        events = [call.args[1] for call in send.call_args_list if call.args[1]["type"] == "room.automation_presentation"]
        self.assertEqual([event["payload"]["type"] for event in events], ["message", "handout", "camera"])
        self.assertTrue(all(event["recipients"] == [str(self.player.pk)] for event in events))
        self.assertEqual(events[0]["payload"]["text"], text)
        self.assertEqual((events[2]["payload"]["x"], events[2]["payload"]["y"]), (128, 192))
        self.assertEqual(len({event["payload"]["id"] for event in events}), 3)
        with patch("gravewright.realtime.dispatch.send") as repeated, self.captureOnCommitCallbacks(execute=True):
            self.command("closed", user=self.player, request_id=request_id)
        self.assertFalse(repeated.called)

    def test_failed_later_action_discards_every_presentation(self):
        self.doc["doors"][0]["blueprint"] = chain(node("message", "showMessage", text="Must roll back", audience=audience()),
            node("camera", "cameraFocus", focusX=1000, focusY=1000, audience=audience()))
        self.generated()
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            with self.assertRaisesMessage(services.MapError, "outside the map"):
                self.command("closed", user=self.player)
        self.assertFalse(any(call.args[1]["type"] == "room.automation_presentation" for call in send.call_args_list))

    def test_handout_permissions_and_scene_access_are_rechecked_at_delivery(self):
        self.generated()
        payload = {"id": str(uuid.uuid4()), "sceneId": str(self.scene.pk), "type": "handout", "journalId": str(self.journal.pk)}
        self.assertEqual(presentation_for(self.campaign.pk, self.player.pk, payload), payload)
        self.journal.visibility = "private"
        self.journal.save(update_fields=["visibility"])
        self.assertIsNone(presentation_for(self.campaign.pk, self.player.pk, payload))
        self.assertEqual(presentation_for(self.campaign.pk, self.gm.pk, payload), payload)
        self.scene.visibility = "gm"
        self.scene.save(update_fields=["visibility"])
        self.assertIsNone(presentation_for(self.campaign.pk, self.player.pk, {**payload, "type": "message", "text": "Hidden"}))

    def test_players_audience_filters_private_handouts_without_granting_access(self):
        self.journal.visibility = "private"
        self.journal.save(update_fields=["visibility"])
        self.doc["doors"][0]["blueprint"] = chain(node("message", "showMessage", text="Public", audience=audience("players")),
            node("handout", "showHandout", journalId=str(self.journal.pk), audience=audience("players")))
        self.generated()
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            self.command("closed", user=self.player)
        events = [call.args[1] for call in send.call_args_list if call.args[1]["type"] == "room.automation_presentation"]
        self.assertEqual(len(events), 1)
        self.assertEqual(set(events[0]["recipients"]), {str(self.player.pk), str(self.streamer.pk)})
        self.assertFalse(self.journal.access.exists())

    def test_visual_actions_keep_collision_and_preserve_native_image_transform(self):
        self.generated()
        from gravewright.maps.extra_objects import image
        picture = SceneObject.objects.create(scene=self.scene, kind="images", data=image(self.scene, {
            "asset_id": str(self.floor.pk), "x": 10, "y": 20, "rotation": 45}))
        raw = chain(node("hide", "setVisibility", visible=False), node("art", "setAppearance", assetId=str(self.alternate.pk)))
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("ref", "reference", targetId=str(picture.pk)))
        graph["edges"].extend([data("ref", "door", name, "target") for name in ("hide", "art")])
        self.command("closed", action="update", version=self.door_object.version, blueprint=raw)
        self.door_object.refresh_from_db()
        before = deepcopy(self.door_object.data)
        self.command("closed", user=self.player)
        picture.refresh_from_db()
        self.assertEqual((picture.data["x"], picture.data["y"], picture.data["rotation"]), (10, 20, 45))
        self.assertEqual(picture.data["layer"], "gm-image-layer")
        self.assertEqual(picture.data["asset_id"], str(self.alternate.pk))
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data, before)

    def test_generated_assets_are_not_appearance_materials_or_authored_image_inputs(self):
        from gravewright.maps.blueprint_runtime import clean_native_blueprint
        from gravewright.maps.extra_objects import image
        from gravewright.maps.models import MapAsset
        self.generated()
        artifact = MapAsset.objects.create(campaign=self.campaign, generated_for=self.scene,
            name="Generated mask", file=self.floor.file.name, width=16, height=16)
        raw = chain(node("art", "setAppearance", assetId=str(artifact.pk)))
        with self.assertRaisesMessage(services.MapError, "asset not found"):
            clean_native_blueprint(raw, self.campaign.pk, self.scene.pk)
        with self.assertRaisesMessage(services.MapError, "cannot be reused"):
            image(self.scene, {"asset_id": str(artifact.pk), "x": 1, "y": 2})

    def test_deleted_material_removes_appearance_action_preserves_text_and_cancels_wait(self):
        from gravewright.maps.models import MapBuilderProject
        authored = "Keep " + str(self.alternate.pk)
        raw = chain(node("wait", "delay", seconds=.1), node("art", "setAppearance", assetId=str(self.alternate.pk)),
                    node("message", "showMessage", text=authored, audience=audience()))
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("group", "elementGroup", name=authored, memberType="element", targetIds=[self.doc["doors"][0]["id"]]))
        graph["edges"].append(data("group", "targets", "art", "target"))
        self.doc["doors"][0]["blueprint"] = raw
        self.generated()
        self.command("closed", user=self.player)
        job = AutomationDelay.objects.get(status="pending")
        response = self.client.post(f"/api/containers/{self.campaign.pk}/library/assets/delete",
                                    {"asset_id": str(self.alternate.pk)}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.door_object.refresh_from_db()
        source = MapBuilderProject.objects.get(pk=self.project_id)
        for raw in (source.document["doors"][0]["blueprint"], self.door_object.data["blueprint"]):
            graph = raw["graphs"][EVENT]
            self.assertFalse(any(item["type"] == "setAppearance" for item in graph["nodes"]))
            self.assertIn(execution("wait", "message"), graph["edges"])
            self.assertFalse(any(edge["from"] == "group" for edge in graph["edges"]))
            self.assertEqual(next(item for item in graph["nodes"] if item["id"] == "message")["text"], authored)
            self.assertEqual(next(item for item in graph["nodes"] if item["id"] == "group")["name"], authored)
        self.assertEqual(self.due(job)["cancelled"], 1)
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            self.command("closed", user=self.player)
            self.assertEqual(self.due(AutomationDelay.objects.get(status="pending"))["completed"], 1)
        events = [call.args[1] for call in send.call_args_list if call.args[1]["type"] == "room.automation_presentation"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["payload"]["text"], authored)

    def test_wall_material_crop_is_read_once_per_request_without_retaining_image_bytes(self):
        from gravewright.maps.blueprint_world import world_request
        from gravewright.maps.builder_dynamic import set_appearance
        self.generated()
        row = SceneObject(scene=self.scene, kind="images", data={"surface": {"kind": "wall"}})
        storage = self.alternate.file.storage
        with patch.object(storage, "open", wraps=storage.open) as opened:
            with world_request(uuid.uuid4()) as request:
                for _ in range(32):
                    self.assertTrue(set_appearance(self.scene, row, self.alternate.pk))
                    self.assertEqual(row.data["surface"]["materialCrop"], [0, 0, 16, 16])
                    row.data["surface"]["materialCrop"][0] = 100
                self.assertEqual(request.material_crops[str(self.alternate.pk)], (0, 0, 16, 16))
            self.assertEqual(opened.call_count, 1)
            with world_request(uuid.uuid4()):
                set_appearance(self.scene, row, self.alternate.pk)
            self.assertEqual(opened.call_count, 2)

    def test_surface_material_cleanup_restores_base_and_preserves_generated_masks(self):
        from gravewright.maps.blueprint_runtime import detach_scene_art
        self.doc["floors"][0]["dynamic"] = True
        self.doc["walls"][0]["dynamic"] = True
        raw = chain(node("art", "setAppearance", assetId=str(self.alternate.pk)))
        graph = raw["graphs"][EVENT]
        graph["nodes"].append(node("group", "elementGroup", name="Surfaces", memberType="element",
            targetIds=[self.doc["floors"][0]["id"], self.doc["walls"][0]["id"]]))
        graph["edges"].append(data("group", "targets", "art", "target"))
        self.doc["doors"][0]["blueprint"] = raw
        self.generated()
        before_files = self.files()
        self.command("closed")
        self.assertEqual(self.files(), before_files)
        surfaces = list(self.scene.elements.filter(kind="images", data__surface__isnull=False))
        self.assertEqual(len(surfaces), 2)
        before = {row.pk: (row.data["asset_id"], row.data["surface"]["maskId"]) for row in surfaces}
        for row in surfaces:
            self.assertEqual(row.data["surface"]["materialId"], str(self.alternate.pk))
        self.assertIn(self.scene.pk, detach_scene_art(self.campaign.pk, self.alternate.pk))
        for row in surfaces:
            row.refresh_from_db()
            self.assertNotIn("materialId", row.data["surface"])
            self.assertNotIn("materialCrop", row.data["surface"])
            self.assertEqual((row.data["asset_id"], row.data["surface"]["maskId"]), before[row.pk])
        response = self.client.post(f"/api/containers/{self.campaign.pk}/library/assets/delete",
                                    {"asset_id": str(self.alternate.pk)}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        for row in surfaces:
            row.refresh_from_db()
            self.assertEqual((row.data["asset_id"], row.data["surface"]["maskId"]), before[row.pk])


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class PortalTests(TestCase):
    asset = region_fixtures.RegionTests.asset
    post = region_fixtures.RegionTests.post
    save = region_fixtures.RegionTests.save
    generate = region_fixtures.RegionTests.generate
    files = region_fixtures.RegionTests.files
    generated = region_fixtures.RegionTests.generated
    update_scene = region_fixtures.RegionTests.update_scene
    token_command = region_fixtures.RegionTests.token_command
    place = region_fixtures.RegionTests.place
    move = region_fixtures.RegionTests.move
    due = delay_fixtures.DelayRuntimeTests.due

    def setUp(self):
        region_fixtures.RegionTests.setUp(self)
        self.destination_id = str(uuid.uuid4())
        self.doc["regions"][0]["blueprint"] = chain(node("travel", "teleport", destinationId=self.destination_id),
            event="presence:enter", kind="region")
        self.doc["regions"][0]["blueprint"]["graphs"].update(chain(
            node("departed", "setVariable", scope="element", name="Departed", valueType="boolean", value=True),
            event="presence:exit", kind="region")["graphs"])
        destination = deepcopy(self.doc["regions"][0])
        destination.update(id=self.destination_id, name="Arrival", x=6, y=5, width=2, height=1)
        destination["blueprint"] = chain(node("light", "light", targetId=self.light_id, enabled=True),
            node("return", "teleport", destinationId=self.region_id), event="presence:enter", kind="region")
        self.doc["regions"].append(destination)

    def area(self, name):
        return self.scene.elements.get(kind="zones", data__region__name=name)

    def test_identity_placement_arrival_departure_and_retry_are_stable_without_bounce(self):
        self.generated()
        token = self.place()
        scene_version = self.scene.version
        tile_url = services.manifest(self.scene)["tileUrlTemplate"]
        before = (token.pk, token.actor_id, token.linked, deepcopy(token.snapshot), deepcopy(token.conditions), token.rotation)
        rid = uuid.uuid4()
        version = token.version
        result = self.move(token, 2, user=self.player, rid=rid)
        self.assertEqual((token.grid_x, token.grid_y), (6, 5))
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.version, scene_version)
        self.assertEqual(services.manifest(self.scene)["tileUrlTemplate"], tile_url)
        self.assertEqual(result["teleports"], [{"id": str(token.pk), "version": token.version}])
        self.assertEqual((token.pk, token.actor_id, token.linked, token.snapshot, token.conditions, token.rotation), before)
        self.assertEqual(self.area("Pressure plate").data["region"]["occupants"], [])
        arrival = self.area("Arrival")
        self.assertEqual(arrival.data["region"]["occupants"], [str(token.pk)])
        self.assertEqual(arrival.data["region"]["arrivalGates"], [str(token.pk)])
        self.light_object.refresh_from_db()
        self.assertTrue(self.light_object.data["enabled"])
        runs = list(AutomationRun.objects.filter(scene=self.scene))
        events = [event["event"] for run in runs for event in run.data["events"]]
        self.assertEqual(events.count("presence:enter"), 2)
        self.assertEqual(events.count("presence:exit"), 1)
        replay = self.token_command("move", {"id": str(token.pk), "gridX": 2, "gridY": 1, "expectedVersion": version},
                                    user=self.player, rid=rid)
        self.assertEqual(replay, result)
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y), (6, 5))
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), len(runs))

    def test_transport_markers_commit_with_the_final_revision_and_expire_on_later_moves(self):
        self.generated()
        token = self.place()
        self.assertNotIn("teleports", self.move(token, 0, 2, user=self.player))
        rid = uuid.uuid4()
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            result = self.move(token, 2, user=self.player, rid=rid)
            self.assertFalse(send.called)
        marker = {"id": str(token.pk), "version": token.version}
        self.assertEqual(result["teleports"], [marker])
        notifications = [call.args[1] for call in send.call_args_list if call.args[1]["type"] == "room.tokens"]
        self.assertTrue(notifications)
        self.assertTrue(all(event.get("teleports") == [marker] for event in notifications))
        self.assertTrue(all(event.get("mapId") == str(self.scene.pk) for event in notifications))
        self.assertTrue(all("teleports" not in call.args[1]
                            for call in send.call_args_list if call.args[1]["type"] != "room.tokens"))
        self.assertNotIn("room.maps", [call.args[1]["type"] for call in send.call_args_list])
        self.assertNotIn("teleports", self.move(token, 5, 5, user=self.player))
        current_version = token.version
        replay = self.token_command("move", {"id": str(token.pk), "gridX": 2, "gridY": 1,
            "expectedVersion": 1}, user=self.player, rid=rid)
        self.assertNotIn("teleports", replay)
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y, token.version), (5, 5, current_version))

    def test_delayed_transport_publishes_the_final_marker_only_after_commit(self):
        self.doc["regions"][0]["blueprint"] = chain(node("wait", "delay", seconds=.1),
            node("travel", "teleport", destinationId=self.destination_id), event="presence:enter", kind="region")
        self.generated()
        token = self.place()
        scene_version = self.scene.version
        tile_url = services.manifest(self.scene)["tileUrlTemplate"]
        self.assertNotIn("teleports", self.move(token, 2, user=self.player))
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.due()["completed"], 1)
            self.assertFalse(send.called)
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y), (6, 5))
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.version, scene_version)
        self.assertEqual(services.manifest(self.scene)["tileUrlTemplate"], tile_url)
        self.assertNotIn("room.maps", [call.args[1]["type"] for call in send.call_args_list])
        notifications = [call.args[1] for call in send.call_args_list if call.args[1]["type"] == "room.tokens"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["teleports"], [{"id": str(token.pk), "version": token.version}])
        self.assertEqual(notifications[0]["mapId"], str(self.scene.pk))

    def test_a_later_failure_rolls_back_transport_and_every_transport_notification(self):
        self.doc["regions"][1]["blueprint"] = chain(
            node("invalid", "cameraFocus", focusX=1000, focusY=1000, audience=audience()),
            event="presence:enter", kind="region")
        self.generated()
        token = self.place()
        version = token.version
        with patch("gravewright.realtime.dispatch.send") as send, self.captureOnCommitCallbacks(execute=True):
            with self.assertRaisesMessage(services.MapError, "outside the map"):
                self.move(token, 2, user=self.player)
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y, token.version), (0, 1, version))
        self.assertFalse(send.called)

    def test_arrival_gate_survives_timer_then_clears_only_after_leaving(self):
        destination = self.doc["regions"][1]["blueprint"]
        destination["graphs"]["presence:enter"] = chain(node("timer", "timer", name="Return", action="start", seconds=.1),
            event="presence:enter", kind="region")["graphs"]["presence:enter"]
        destination["graphs"].update(chain(node("return", "teleport", destinationId=self.region_id),
            event="signal:Return", kind="region")["graphs"])
        self.generated()
        token = self.place()
        self.move(token, 2, user=self.player)
        job = AutomationDelay.objects.get(status="pending")
        self.assertEqual(self.due(job)["completed"], 1)
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y), (6, 5))
        self.move(token, 5, 5, user=self.player)
        self.assertEqual(self.area("Arrival").data["region"].get("arrivalGates", []), [])
        self.move(token, 6, 5, user=self.player)
        self.assertEqual(self.due(AutomationDelay.objects.get(status="pending"))["completed"], 1)
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y), (2, 1))

    def test_capacity_failure_rolls_back_move_and_scene_revision(self):
        self.generated()
        token = self.place()
        for x in (6, 7):
            Token.objects.create(scene=self.scene, actor=self.actor, grid_x=x, grid_y=5, hidden=True)
        self.scene.refresh_from_db()
        version, token_version = self.scene.version, token.version
        with self.assertRaisesMessage(services.MapError, "no available placement"):
            self.move(token, 2, user=self.player)
        token.refresh_from_db()
        self.scene.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y, token.version), (0, 1, token_version))
        self.assertEqual(self.scene.version, version)
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())

    def test_placement_skips_walls_and_occupied_cells_in_stable_order(self):
        self.doc["regions"][1].update(width=2, height=2)
        self.generated()
        Token.objects.create(scene=self.scene, actor=self.actor, grid_x=6, grid_y=5)
        SceneObject.objects.create(scene=self.scene, kind="walls", data=objects.wall({
            "x1": 7.5 * 64, "y1": 5 * 64, "x2": 7.5 * 64, "y2": 6 * 64}))
        token = self.place()
        self.move(token, 2, user=self.player)
        self.assertEqual((token.grid_x, token.grid_y), (6, 6))

    def test_oversized_footprint_and_disabled_destination_leave_token_unchanged(self):
        self.doc["regions"][1]["enabled"] = False
        self.generated()
        token = self.place()
        with self.assertRaisesMessage(services.MapError, "destination is unavailable"):
            self.move(token, 2, user=self.player)
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y), (0, 1))
        region = self.area("Arrival")
        region.data["enabled"] = True
        region.save(update_fields=["data"])
        self.actor.data = {"token": {"size": 2}}
        self.actor.save(update_fields=["data"])
        with self.assertRaisesMessage(services.MapError, "no available placement"):
            self.move(token, 2, user=self.player)

    def test_delayed_transport_rechecks_control_and_current_actor_identity(self):
        self.doc["regions"][0]["blueprint"] = chain(node("wait", "delay", seconds=.1),
            node("travel", "teleport", destinationId=self.destination_id), event="presence:enter", kind="region")
        self.generated()
        token = self.place()
        self.move(token, 2, user=self.player)
        job = AutomationDelay.objects.get(status="pending")
        self.actor.permissions = {}
        self.actor.save(update_fields=["permissions"])
        self.assertEqual(self.due(job)["cancelled"], 1)
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y), (2, 1))

    def test_resumed_arrival_random_choice_is_stable_after_transaction_rollback(self):
        from gravewright.maps import blueprint_runtime, blueprint_world
        self.doc["regions"][0]["blueprint"] = chain(node("wait", "delay", seconds=.1),
            node("travel", "teleport", destinationId=self.destination_id), event="presence:enter", kind="region")
        raw = chain(event="presence:enter", kind="region")
        raw["graphs"]["presence:enter"].update(nodes=[node("event", "event", event="presence:enter"),
            node("choose", "random", weights=[1, 1]),
            node("first", "showMessage", text="First", audience=audience()),
            node("second", "showMessage", text="Second", audience=audience())], edges=[execution("event", "choose"),
                execution("choose", "first", "branch1"), execution("choose", "second", "branch2")])
        self.doc["regions"][1]["blueprint"] = raw
        self.generated()
        token = self.place()
        self.move(token, 2, user=self.player)
        job = AutomationDelay.objects.get(status="pending")
        original_present, original_draw = blueprint_world.present, blueprint_runtime._random_draw
        attempts = []

        def fail_once(*args):
            attempts.append(args[2]["text"])
            if len(attempts) == 1:
                raise DatabaseError("Synthetic interrupted transaction")
            return original_present(*args)

        with patch("gravewright.maps.blueprint_runtime._random_draw", wraps=original_draw) as draw, \
                patch("gravewright.maps.blueprint_world.present", side_effect=fail_once):
            with self.assertRaisesMessage(DatabaseError, "interrupted"):
                self.due(job)
            token.refresh_from_db()
            job.refresh_from_db()
            self.assertEqual((token.grid_x, token.grid_y), (2, 1))
            self.assertEqual(job.status, "pending")
            self.assertEqual(self.due(job)["completed"], 1)
        self.assertEqual(len(draw.call_args_list), 2)
        self.assertEqual(draw.call_args_list[0], draw.call_args_list[1])
        self.assertEqual(attempts[0], attempts[1])
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y), (6, 5))

    def test_missing_context_cannot_be_forged_and_foreign_destination_is_rejected(self):
        self.generated()
        token = self.place()
        raw = chain(node("travel", "teleport", destinationId=str(self.area("Arrival").pk)))
        self.door_object.data["blueprint"] = raw
        self.door_object.save(update_fields=["data"])
        with self.assertRaisesMessage(services.MapError, "requires the triggering token"):
            fixtures.BuilderBlueprintTests.command(self, "closed", user=self.player,
                context={"tokenId": str(token.pk), "actorId": str(self.actor.pk)})
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y), (0, 1))
        foreign = Scene.objects.create(campaign=self.other, name="Foreign", width=512, height=512)
        row = SceneObject.objects.create(scene=foreign, kind="zones", data=deepcopy(self.area("Arrival").data))
        from gravewright.maps.blueprint_runtime import clean_native_blueprint
        with self.assertRaisesMessage(services.MapError, "from this scene"):
            clean_native_blueprint(chain(node("travel", "teleport", destinationId=str(row.pk))), self.campaign.pk, self.scene.pk)

    def test_private_gate_is_not_projected_and_native_edit_cannot_forge_it(self):
        self.generated()
        token = self.place()
        self.move(token, 2)
        projected = objects.layer_state(self.scene, self.membership)
        self.assertNotIn("arrivalGates", str(projected))
        arrival = self.area("Arrival")
        with self.assertRaisesMessage(services.MapError, "Invalid presence region"):
            services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk), "area": "zones",
                "action": "update", "data": {"id": str(arrival.pk), "expected_version": arrival.version,
                "patch": {"region": {"arrivalGates": []}}}}, uuid.uuid4())

    def test_linked_update_preserves_arrival_gate_until_the_token_leaves(self):
        self.generated()
        token = self.place()
        scene_version = self.scene.version
        self.move(token, 2)
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.version, scene_version)
        arrival_id = self.area("Arrival").pk
        count = AutomationRun.objects.filter(scene=self.scene).count()
        self.update_scene()
        self.scene.refresh_from_db()
        self.assertEqual(self.scene.version, scene_version + 1)
        self.assertEqual(self.area("Arrival").pk, arrival_id)
        self.assertEqual(self.area("Arrival").data["region"]["arrivalGates"], [str(token.pk)])
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)
        self.move(token, 5, 5)
        self.assertEqual(self.area("Arrival").data["region"].get("arrivalGates", []), [])

    def test_delayed_token_reference_never_applies_to_a_reassigned_actor(self):
        from gravewright.actors.models import Actor
        self.doc["regions"][0]["blueprint"] = chain(node("wait", "delay", seconds=.1),
            node("travel", "teleport", destinationId=self.destination_id), event="presence:enter", kind="region")
        self.generated()
        token = self.place()
        self.move(token, 2, user=self.player)
        job = AutomationDelay.objects.get(status="pending")
        replacement = Actor.objects.create(campaign=self.campaign, name="Different traveler", data={},
            permissions={str(self.player.pk): "owner"})
        Token.objects.filter(pk=token.pk).update(actor=replacement)
        self.assertEqual(self.due(job)["failed"], 1)
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y, token.actor_id), (2, 1, replacement.pk))

    def test_destination_cannot_fit_a_footprint_larger_than_the_scene(self):
        from gravewright.maps.blueprint_world import teleport, world_request
        from gravewright.maps.regions import authentic_context
        self.generated()
        self.actor.data = {"token": {"size": 9}}
        self.actor.save(update_fields=["data"])
        token = Token.objects.create(scene=self.scene, actor=self.actor)
        destination = self.area("Arrival")
        destination.data["geometry"].update(x=0, y=0, width=1024, height=1024)
        destination.save(update_fields=["data"])
        context = authentic_context(self.membership, self.area("Pressure plate"), token,
            token_id=str(token.pk), presence="enter", count=1)
        with world_request(uuid.uuid4()), self.assertRaisesMessage(services.MapError, "no available placement"):
            teleport(self.scene, self.membership, {"destinationId": str(destination.pk)}, context)
        token.refresh_from_db()
        self.assertEqual((token.grid_x, token.grid_y), (0, 0))
