"""Lever decorations: generation, table interaction, chains, privacy and cleanup."""

from copy import deepcopy
from io import BytesIO
import uuid

from django.core.files.base import ContentFile
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image

from gravewright.journals.services import JournalError
from gravewright.maps import builder_services, objects, services
from gravewright.maps.blueprints import clean_blueprint, default_blueprint
from gravewright.maps.models import AutomationRun, MapBuilderProject, Receipt

from . import test_builder_blueprints as fixtures


def execution(origin, target, output="next"):
    return {"from": origin, "to": target, "output": output, "kind": "execution"}


def data(origin, output, target, port):
    return {"from": origin, "to": target, "output": output, "input": port, "kind": "data"}


def node(identifier, kind, **fields):
    return {"id": identifier, "type": kind, "x": 0, "y": 0, **fields}


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class LeverTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    update_scene = fixtures.BuilderBlueprintTests.update_scene

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.handle_off = self.asset("lever-off.png", "#553311")
        self.handle_on = self.asset("lever-on.png", "#33aa55")
        for row in (self.handle_off, self.handle_on):
            self.doc["assets"].append({"assetId": str(row.pk), "role": "decoration"})
        door_id = self.doc["doors"][0]["id"]
        self.lever_id = str(uuid.uuid4())
        self.doc["decorations"] = [{
            "id": self.lever_id, "layerId": self.doc["layers"][0]["id"], "assetId": str(self.handle_off.pk),
            "x": 5, "y": 5, "width": 1, "height": 1, "rotation": 0, "lever": {"state": "off"},
            "blueprint": {"version": 2, "kind": "lever",
                          "states": {"off": {"appearance": "inherit"},
                                     "on": {"appearance": "asset", "assetId": str(self.handle_on.pk)}},
                          "graphs": {"interact": {
                              "nodes": [node("event", "event", event="interact"),
                                        node("ref", "reference", targetId=door_id),
                                        node("open", "state", targetState="open"),
                                        node("check", "condition", state="off"),
                                        node("on", "state", targetState="on"),
                                        node("off", "state", targetState="off")],
                              "edges": [execution("event", "check"), execution("check", "on", "true"),
                                        execution("on", "open"), execution("check", "off", "false"),
                                        data("ref", "door", "open", "target")]}}}}]

    def lever(self):
        return self.scene.elements.get(kind="images", data__lever__isnull=False)

    def interact(self, user=None, request_id=None, **extra):
        return services.command(self.campaign.pk, (user or self.gm).pk, "objects",
            {"mapId": str(self.scene.pk), "area": "images", "action": "interact",
             "data": {"image_id": str(self.lever().pk), **extra}}, request_id or uuid.uuid4())

    def door_graph(self, event, target_state):
        """Create a door event aimed at this project's lever."""
        return {"nodes": [node("event", "event", event=event),
                          node("ref", "reference", targetId=self.lever_id),
                          node("act", "state", targetState=target_state)],
                "edges": [execution("event", "act"), data("ref", "door", "act", "target")]}

    def edit_image(self, **data):
        return services.command(self.campaign.pk, self.gm.pk, "objects",
            {"mapId": str(self.scene.pk), "area": "images", "action": "update",
             "data": {"placement_id": str(self.lever().pk), **data}}, uuid.uuid4())

    def delete_asset(self, asset):
        response = self.post(f"/api/containers/{self.campaign.pk}/library/assets/delete", {"asset_id": str(asset.pk)})
        self.assertEqual(response.status_code, 200, response.content)

    def replace_asset_pixels(self, asset, size):
        """Use real supported images with unusual dimensions, not fake metadata."""
        with Image.new("RGB", size, "#229955") as image:
            content = BytesIO()
            image.save(content, "PNG")
        asset.width, asset.height = size
        asset.file.save("state-image.png", ContentFile(content.getvalue()), save=False)
        asset.save(update_fields=["file", "width", "height"])

    def test_generated_lever_keeps_box_state_and_remapped_private_graph(self):
        self.generated()
        lever = self.lever()
        self.assertEqual(lever.data["lever"], {"state": "off", "baseAssetId": str(self.handle_off.pk),
                                               "baseLayer": "map", "width": 64, "height": 64})
        self.assertEqual(lever.data["asset_id"], str(self.handle_off.pk))
        reference = lever.data["blueprint"]["graphs"]["interact"]["nodes"][1]
        self.assertEqual(reference["targetId"], str(self.door_object.pk), "the project door ID maps to the native door")
        member = services.member(self.campaign.pk, self.player.pk)
        row, = [row for row in objects.layer_state(self.scene, member)["images"] if row["id"] == str(lever.pk)]
        self.assertEqual(row["lever"], {"state": "off"})
        self.assertNotIn("blueprint", row)

    def test_player_lever_runs_its_chain_swaps_its_image_and_logs_the_run(self):
        self.generated()
        result = self.interact(self.player)
        self.assertEqual(result["image"]["lever"], {"state": "on"})
        self.assertNotIn("blueprint", result)
        lever = self.lever()
        self.door_object.refresh_from_db()
        self.assertEqual(lever.data["lever"]["state"], "on")
        self.assertEqual(lever.data["asset_id"], str(self.handle_on.pk))
        self.assertEqual(lever.data["scale"], 4, "the On image fits the authored 64 px box")
        self.assertEqual(self.door_object.data["door_state"], "open")
        run = self.client.get(f"/api/maps/{self.scene.pk}/automation").json()
        self.assertEqual(run["runs"][0]["doorId"], str(lever.pk))
        self.assertIn({"id": str(lever.pk), "kind": "lever"}, [{k: d[k] for k in ("id", "kind")} for d in run["doors"]])
        self.interact(self.player)
        self.assertEqual((self.lever().data["lever"]["state"], self.lever().data["asset_id"]), ("off", str(self.handle_off.pk)))

    def test_paused_lever_does_not_toggle_and_gm_edits_keep_its_state(self):
        self.generated()
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk), "area": "automation",
                         "action": "pause", "data": {"paused": True}}, uuid.uuid4())
        self.interact()
        self.door_object.refresh_from_db()
        self.assertEqual((self.lever().data["lever"]["state"], self.door_object.data["door_state"]), ("off", "closed"))
        self.assertEqual(self.lever().data["asset_id"], str(self.handle_off.pk))
        self.assertEqual(AutomationRun.objects.get(scene=self.scene).outcome, "paused")
        lever = self.lever()
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk), "area": "images",
                         "action": "update", "data": {"placement_id": str(lever.pk), "x": 400}}, uuid.uuid4())
        lever.refresh_from_db()
        self.assertEqual(lever.data["x"], 400)
        self.assertEqual(lever.data["lever"]["state"], "off")
        self.assertIn("blueprint", lever.data)

    def test_scene_update_keeps_lever_state_and_deleting_the_on_image_reverts_it(self):
        self.generated()
        self.interact()
        self.update_scene()
        self.assertEqual(self.lever().data["lever"]["state"], "on")
        self.delete_asset(self.handle_on)
        lever = self.lever()
        self.assertEqual(lever.data["asset_id"], str(self.handle_off.pk))
        self.assertEqual(lever.data["blueprint"]["states"]["on"], {"appearance": "inherit"})
        self.update_scene()
        self.assertEqual(self.lever().data["lever"]["state"], "on")

    def test_deleting_the_base_image_promotes_an_existing_state_image(self):
        self.generated()
        self.interact()
        self.delete_asset(self.handle_off)
        lever = self.lever()
        self.assertEqual(lever.data["lever"]["baseAssetId"], str(self.handle_on.pk))
        self.assertEqual(lever.data["asset_id"], str(self.handle_on.pk))
        source = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertEqual(source.document["decorations"][0]["assetId"], str(self.handle_on.pk))
        builder_services.clean_document(source.document, self.membership)
        self.update_scene()
        self.assertEqual(self.lever().data["lever"]["state"], "on")

    def test_deleting_the_only_image_preserves_decoration_geometry_without_lever_behavior(self):
        self.doc["decorations"][0]["blueprint"]["states"]["on"] = {"appearance": "inherit"}
        self.generated()
        decoration = deepcopy(self.doc["decorations"][0])
        self.delete_asset(self.handle_off)
        self.assertFalse(self.scene.elements.filter(kind="images").exists())
        source = MapBuilderProject.objects.get(pk=self.project_id)
        remaining = source.document["decorations"][0]
        self.assertIsNone(remaining["assetId"])
        self.assertNotIn("lever", remaining)
        self.assertNotIn("blueprint", remaining)
        self.assertEqual({key: remaining[key] for key in ("id", "x", "y", "width", "height")},
                         {key: decoration[key] for key in ("id", "x", "y", "width", "height")})
        builder_services.clean_document(source.document, self.membership)
        self.update_scene()
        self.assertFalse(self.scene.elements.filter(kind="images").exists())

    def test_deleting_a_sound_cleans_lever_project_native_and_generation_graphs(self):
        graph = self.doc["decorations"][0]["blueprint"]["graphs"]["interact"]
        graph["nodes"].append(node("click", "sound", trackId=str(self.sound.pk), volume=.5))
        graph["edges"].append(execution("open", "click"))
        self.generated()
        self.delete_asset(self.sound)
        source = MapBuilderProject.objects.get(pk=self.project_id)
        for data_row in (source.document["decorations"][0], self.lever().data,
                         next(row["data"] for row in source.generation["objects"] if row["kind"] == "images")):
            self.assertNotIn("sound", [row["type"] for row in data_row["blueprint"]["graphs"]["interact"]["nodes"]])
        self.update_scene()
        self.interact()
        self.assertEqual(self.lever().data["lever"]["state"], "on")

    def test_blueprints_must_match_their_element_kind(self):
        invalid = deepcopy(self.doc)
        invalid["decorations"][0].pop("lever")
        self.assertEqual(self.save(document=invalid).status_code, 400)
        invalid = deepcopy(self.doc)
        invalid["decorations"][0]["blueprint"]["kind"] = "door"
        self.assertEqual(self.save(document=invalid).status_code, 400)
        invalid = deepcopy(self.doc)
        invalid["doors"][0]["blueprint"] = deepcopy(self.doc["decorations"][0]["blueprint"])
        self.assertEqual(self.save(document=invalid).status_code, 400)
        self.assertFalse(MapBuilderProject.objects.filter(pk=self.project_id).exists())

    def test_retry_does_not_toggle_again_or_replay_any_chain_effect(self):
        self.generated()
        request_id = uuid.uuid4()
        first = self.interact(self.player, request_id)
        before = deepcopy(self.lever().data)
        self.assertEqual(self.interact(self.player, request_id), first)
        self.assertEqual(self.lever().data, before)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), 1)
        self.assertEqual(Receipt.objects.filter(request_id=request_id).count(), 1)

    def test_player_chain_respects_a_locked_door(self):
        self.doc["doors"][0]["state"] = "locked"
        self.generated()
        self.interact(self.player)
        self.door_object.refresh_from_db()
        self.assertEqual(self.lever().data["lever"]["state"], "on")
        self.assertEqual(self.door_object.data["door_state"], "locked")
        run = AutomationRun.objects.get(scene=self.scene)
        self.assertEqual(run.data["events"][-1]["event"], "refused")
        self.assertEqual(run.data["events"][-1]["message"], "This door cannot be operated.")

    def test_player_chain_may_unlock_only_with_explicit_authorization(self):
        self.doc["doors"][0]["state"] = "locked"
        self.doc["decorations"][0]["blueprint"]["graphs"]["interact"]["nodes"][2]["players"] = True
        self.generated()
        self.interact(self.player)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")

    def test_door_can_signal_a_lever_to_run_its_explicit_activation_graph(self):
        blueprint = default_blueprint()
        blueprint["version"] = 2
        graph = self.door_graph("interact", "on")
        graph["nodes"][2] = node("act", "emitEvent", scope="element", name="Activate")
        blueprint["graphs"]["interact"] = graph
        lever = self.doc["decorations"][0]["blueprint"]
        lever["graphs"]["signal:Activate"] = deepcopy(lever["graphs"]["interact"])
        lever["graphs"]["signal:Activate"]["nodes"][0]["event"] = "signal:Activate"
        self.doc["doors"][0]["blueprint"] = blueprint
        self.generated()
        result = fixtures.BuilderBlueprintTests.command(self)
        self.assertEqual(self.lever().data["lever"]["state"], "on")
        self.assertEqual(self.lever().data["asset_id"], str(self.handle_on.pk))
        self.assertIn(str(self.lever().pk), [row.get("doorId") for row in result["blueprint"]["trace"]])
        self.assertEqual([row["event"] for row in result["blueprint"]["trace"]], ["interact", "signal:Activate"])

    def test_unsupported_state_is_skipped_and_diagnosed(self):
        blueprint = default_blueprint()
        blueprint["version"] = 2
        blueprint["graphs"]["interact"] = self.door_graph("interact", "locked")
        self.doc["doors"][0]["blueprint"] = blueprint
        self.generated()
        fixtures.BuilderBlueprintTests.command(self)
        self.assertEqual(self.lever().data["lever"]["state"], "off")
        steps = AutomationRun.objects.get(scene=self.scene).data["events"][0]["steps"]
        self.assertTrue(next(row for row in steps if row["type"] == "state")["unsupported"])

    def test_repeating_door_lever_chain_rolls_back_and_logs_its_failure(self):
        lever = self.doc["decorations"][0]["blueprint"]
        graph = lever["graphs"]["interact"]
        graph["nodes"].append(node("send", "emitEvent", scope="element", name="Bounce"))
        graph["edges"].extend([execution("open", "send"), data("ref", "door", "send", "target")])
        lever["graphs"]["signal:Bounce"] = deepcopy(graph)
        lever["graphs"]["signal:Bounce"]["nodes"][0]["event"] = "signal:Bounce"
        blueprint = default_blueprint()
        blueprint["version"] = 2
        graph = self.door_graph("signal:Bounce", "off")
        graph["nodes"].append(node("send", "emitEvent", scope="element", name="Bounce"))
        graph["edges"].extend([execution("act", "send"), data("ref", "door", "send", "target")])
        blueprint["graphs"] = {"signal:Bounce": graph}
        self.doc["doors"][0]["blueprint"] = blueprint
        self.generated()
        before = {str(row.pk): (deepcopy(row.data), row.version) for row in self.scene.elements.all()}
        request_id = uuid.uuid4()
        with self.assertRaisesMessage(services.MapError, "repeating chain"):
            self.interact(request_id=request_id)
        self.assertEqual({str(row.pk): (row.data, row.version) for row in self.scene.elements.all()}, before)
        self.assertFalse(Receipt.objects.filter(request_id=request_id).exists())
        run = AutomationRun.objects.get(scene=self.scene)
        self.assertEqual((run.outcome, run.door_id, run.data["stateAfter"]), ("failed", self.lever().pk, "off"))
        self.assertTrue(run.data["events"])

    def test_hidden_levers_and_inactive_images_are_private_and_streamers_cannot_toggle(self):
        self.doc["decorations"][0]["blueprint"]["states"]["on"] = {"appearance": "hidden"}
        self.generated()
        for user in (self.player, self.streamer):
            who = services.member(self.campaign.pk, user.pk)
            image, = objects.layer_state(self.scene, who)["images"]
            self.assertEqual(image["lever"], {"state": "off"})
            self.assertNotIn("blueprint", image)
            self.assertNotIn("baseAssetId", image["lever"])
            self.client.force_login(user)
            self.assertEqual(self.client.get(f"/game/map-assets/{self.handle_on.pk}").status_code, 404)
            self.assertEqual(self.client.get(f"/api/maps/{self.scene.pk}/automation").status_code, 404)
        with self.assertRaises(JournalError):
            self.interact(self.streamer)
        self.interact(self.player)
        with self.assertRaisesMessage(services.MapError, "cannot be used"):
            self.interact(self.player)
        for user in (self.player, self.streamer):
            who = services.member(self.campaign.pk, user.pk)
            self.assertEqual(objects.layer_state(self.scene, who)["images"], [])
            self.client.force_login(user)
            self.assertEqual(self.client.get(f"/game/map-assets/{self.handle_off.pk}").status_code, 404)
        failed = AutomationRun.objects.filter(scene=self.scene, outcome="failed").get()
        self.assertEqual(failed.data["events"], [])

    def test_moving_a_lever_keeps_its_authored_box_with_a_different_state_image_ratio(self):
        self.handle_on.width, self.handle_on.height = 32, 16
        self.handle_on.save(update_fields=["width", "height"])
        self.generated()
        self.interact()
        self.edit_image(x=400, scale=self.lever().data["scale"])
        lever = self.lever()
        self.assertEqual((lever.data["lever"]["width"], lever.data["lever"]["height"]), (64, 64))
        self.edit_image(scale=lever.data["scale"] * 2)
        self.assertEqual((self.lever().data["lever"]["width"], self.lever().data["lever"]["height"]), (128, 128))
        self.interact()
        self.assertEqual(self.lever().data["scale"], 8)

    def test_scene_update_refuses_a_manual_lever_resize(self):
        self.generated()
        self.edit_image(scale=2)
        before = deepcopy(self.lever().data)
        with self.assertRaisesMessage(services.MapError, "changed in the VTT"):
            self.update_scene()
        self.assertEqual(self.lever().data, before)

    def assert_extreme_state_image_can_move_and_resize(self, size):
        self.replace_asset_pixels(self.handle_on, size)
        self.doc["decorations"][0].update(width=3, height=3)
        self.generated()
        self.interact()
        expected = min(192 / size[0], 192 / size[1])
        self.assertEqual(self.lever().data["scale"], expected)
        self.edit_image(x=400, scale=expected)
        self.assertEqual((self.lever().data["lever"]["width"], self.lever().data["lever"]["height"]), (192, 192))
        self.edit_image(scale=expected * 2)
        self.assertEqual((self.lever().data["lever"]["width"], self.lever().data["lever"]["height"]), (384, 384))
        self.interact()
        self.assertEqual((self.lever().data["asset_id"], self.lever().data["scale"]), (str(self.handle_off.pk), 24))

    def test_one_pixel_state_art_fits_exactly_and_remains_editable_above_normal_image_scale(self):
        self.assert_extreme_state_image_can_move_and_resize((1, 1))

    def test_large_state_art_fits_exactly_and_remains_editable_below_normal_image_scale(self):
        self.assert_extreme_state_image_can_move_and_resize((262144, 1))

    def test_one_pixel_base_art_generates_and_updates_with_its_authored_box(self):
        self.replace_asset_pixels(self.handle_off, (1, 1))
        self.doc["decorations"][0].update(width=3, height=3)
        self.generated()
        self.assertEqual(self.lever().data["scale"], 192)
        self.update_scene()
        self.edit_image(x=400, scale=192)
        self.assertEqual((self.lever().data["lever"]["width"], self.lever().data["lever"]["height"]), (192, 192))

    def test_native_lever_scale_keeps_numeric_and_authored_box_limits(self):
        self.generated()
        before = deepcopy(self.lever().data)
        for scale in (True, False, float("inf"), float("nan"), 0, -1, 1e20):
            with self.subTest(scale=scale), self.assertRaises(services.MapError):
                self.edit_image(scale=scale)
            self.assertEqual(self.lever().data, before)

    def test_native_door_assignment_rejects_a_lever_blueprint(self):
        self.generated()
        with self.assertRaisesMessage(services.MapError, "object kind"):
            fixtures.BuilderBlueprintTests.command(self, action="update", blueprint=default_blueprint("lever"))

    def test_campaign_archive_remaps_lever_state_images_and_both_reference_kinds(self):
        from gravewright.administration.archives import export_campaign, import_campaign

        blueprint = default_blueprint()
        blueprint["version"] = 2
        blueprint["graphs"]["interact"] = self.door_graph("interact", "off")
        self.doc["doors"][0]["blueprint"] = blueprint
        self.generated()
        self.interact()
        restored = import_campaign(export_campaign(self.campaign), self.gm, "Lever clone")
        source = MapBuilderProject.objects.get(campaign=restored)
        lever = source.scene.elements.get(kind="images", data__lever__isnull=False)
        door = source.scene.elements.get(kind="walls", data__kind="door")
        self.assertEqual(lever.data["lever"]["state"], "on")
        self.assertNotEqual(lever.data["lever"]["baseAssetId"], str(self.handle_off.pk))
        self.assertEqual(lever.data["asset_id"], lever.data["blueprint"]["states"]["on"]["assetId"])
        self.assertEqual(lever.data["blueprint"]["graphs"]["interact"]["nodes"][1]["targetId"], str(door.pk))
        self.assertEqual(door.data["blueprint"]["graphs"]["interact"]["nodes"][1]["targetId"], str(lever.pk))
        builder_services.update(restored.pk, self.gm.pk, source.pk,
            {"request_id": str(uuid.uuid4()), "expected_version": source.version,
             "expected_scene_version": source.scene.version})
        lever.refresh_from_db()
        self.assertEqual(lever.data["lever"]["state"], "on")


class LeverContractTests(SimpleTestCase):
    def test_new_states_do_not_expand_version_one_or_accept_untyped_kinds(self):
        blueprint = default_blueprint()
        blueprint["version"] = 1
        blueprint["graphs"]["interact"] = fixtures.graph("interact", {"type": "state", "targetState": "on"})
        for edge in blueprint["graphs"]["interact"]["edges"]:
            edge.pop("kind", None)
        with self.assertRaises(services.MapError):
            clean_blueprint(blueprint)
        for kind in ([], {}, None):
            blueprint = default_blueprint("lever")
            blueprint["kind"] = kind
            with self.subTest(kind=kind), self.assertRaises(services.MapError):
                clean_blueprint(blueprint)
