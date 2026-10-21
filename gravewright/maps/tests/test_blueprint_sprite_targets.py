"""Every author can use the node catalog, including targeted sprite changes."""

from contextlib import contextmanager
from copy import deepcopy
import uuid

from django.db import transaction
from django.test import SimpleTestCase, TestCase, override_settings

from gravewright.accounts.services import AuthError
from gravewright.actors.models import Actor
from gravewright.administration.archives import export_campaign, import_campaign
from gravewright.campaigns.models import Campaign
from gravewright.maps import blueprint_testing, objects, services
from gravewright.maps.blueprint_actions import change_sprite, change_visual, validate_campaign_sprites
from gravewright.maps.blueprint_runtime import element_state
from gravewright.maps.blueprints import NODE_TYPES, clean_blueprint, default_blueprint, evaluate_graph
from gravewright.maps.models import AutomationRun, MapAsset, MapBuilderProject, Receipt, SceneObject

from . import test_blueprint_action_matrix as matrix
from . import test_regions as token_fixtures
from . import test_surface_archives as archive_fixtures
from .test_levers import data, execution, node


def catalog_fields(identifier):
    """Independent valid examples make newly added catalog nodes require coverage."""
    return {
        "event": {"event": "signal:Probe"}, "light": {"targetId": identifier, "enabled": True},
        "sound": {"trackId": identifier, "volume": .5}, "state": {"targetState": "on"},
        "interact": {}, "condition": {"state": "off"}, "sequence": {},
        "sprite": {"appearance": "asset", "assetId": identifier}, "property": {"property": "state"},
        "compare": {"state": "on"}, "reference": {"targetId": identifier}, "reveal": {},
        "barrier": {"channel": "movement", "mode": "pass"},
        "soundControl": {"trackId": identifier, "action": "stop", "volume": .5},
        "flame": {"enabled": True}, "all": {}, "any": {},
        "getVariable": {"scope": "element", "name": "Probe", "valueType": "number", "default": 0},
        "setVariable": {"scope": "element", "name": "Probe", "valueType": "number", "value": 1},
        "compareValue": {"valueType": "number", "operator": "eq", "expected": 1},
        "emitEvent": {"scope": "element", "name": "Probe"}, "delay": {"seconds": .1},
        "timer": {"name": "Probe", "action": "start", "seconds": 1},
        "switch": {"valueType": "number", "value": 1, "cases": [{"id": "case1", "value": 1}]},
        "random": {"weights": [1, 1]},
        "elementGroup": {"name": "Targets", "memberType": "element", "targetIds": [identifier]},
        "lightReference": {"targetId": identifier}, "soundReference": {"trackId": identifier},
        "eventContext": {"property": "count"}, "move": {"dx": 1, "dy": 0},
        "rotate": {"degrees": 90}, "setInteraction": {"enabled": True},
        "setRegion": {"enabled": True}, "setVisibility": {"visible": True},
        "setAppearance": {"assetId": identifier},
        "showMessage": {"text": "Probe", "audience": {"scope": "trigger"}},
        "showHandout": {"journalId": identifier, "audience": {"scope": "trigger"}},
        "requestRoll": {"expression": "1d20", "label": "Probe", "visibility": "public", "audience": {"scope": "trigger"}},
        "setQuestStatus": {"journalId": identifier, "status": "active"},
        "cameraFocus": {"focusX": 1, "focusY": 1, "audience": {"scope": "trigger"}},
        "teleport": {"destinationId": identifier}, "once": {}, "counter": {"target": 2},
        "cooldown": {"seconds": 1},
    }


def sprite_graph(event, identifiers, *, mode="asset", asset=None, group=False):
    action = node("art", "sprite", appearance=mode, **({"assetId": asset} if mode == "asset" else {}))
    reference = (node("ref", "elementGroup", name="Artwork targets", memberType="element", targetIds=identifiers)
                 if group else node("ref", "reference", targetId=identifiers[0]))
    return {"nodes": [node("event", "event", event=event), reference, action],
            "edges": [execution("event", "art"),
                      data("ref", "targets" if group else "door", "art", "target")]}


class UniversalNodeDefinitionTests(SimpleTestCase):
    def test_every_catalog_node_can_be_authored_by_every_blueprint_kind(self):
        examples = catalog_fields(str(uuid.uuid4()))
        self.assertEqual(set(examples), set(NODE_TYPES))
        for kind in ("door", "lever", "torch", "region"):
            for node_type, fields in examples.items():
                with self.subTest(owner=kind, node=node_type):
                    value = default_blueprint(kind)
                    event = node("event", "event", event="signal:Probe")
                    value["graphs"] = {"signal:Probe": {
                        "nodes": [event] + ([] if node_type == "event" else [node("draft", node_type, **fields)]),
                        "edges": []}}
                    before = deepcopy(value)
                    cleaned = clean_blueprint(value)
                    self.assertEqual(cleaned["graphs"]["signal:Probe"]["nodes"][-1]["type"], node_type)
                    self.assertEqual(evaluate_graph(cleaned, "signal:Probe", next(iter(value["states"])))
                                     ["actions"], [], "Disconnected drafts must not execute.")
                    self.assertEqual(value, before)

    def test_sprite_targets_accept_elements_and_groups_but_refuse_other_resource_types(self):
        identifier = str(uuid.uuid4())
        for group in (False, True):
            value = default_blueprint("region")
            value["graphs"]["presence:enter"] = sprite_graph("presence:enter", [identifier],
                mode="asset", asset=identifier, group=group)
            cleaned = clean_blueprint(value)
            result = evaluate_graph(cleaned, "presence:enter", "empty")
            self.assertEqual(result["actions"][0]["target"], [identifier] if group else identifier)
        for resource in ("light", "sound"):
            for group in (False, True):
                with self.subTest(resource=resource, group=group), self.assertRaisesMessage(services.MapError, "connection"):
                    value = default_blueprint("lever")
                    graph = sprite_graph("interact", [identifier], mode="inherit", group=group)
                    if group:
                        graph["nodes"][1]["memberType"] = resource
                    else:
                        graph["nodes"][1] = node("ref", resource + "Reference",
                            **{"targetId" if resource == "light" else "trackId": identifier})
                        graph["edges"][1]["output"] = resource
                    value["graphs"]["interact"] = graph
                    clean_blueprint(value)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class SpriteTargetTests(TestCase):
    asset = matrix.ActionTargetMatrixTests.asset
    post = matrix.ActionTargetMatrixTests.post
    save = matrix.ActionTargetMatrixTests.save
    generate = matrix.ActionTargetMatrixTests.generate
    files = matrix.ActionTargetMatrixTests.files
    handler = staticmethod(matrix.ActionTargetMatrixTests.handler)
    token_command = token_fixtures.RegionTests.token_command
    place = token_fixtures.RegionTests.place
    move = token_fixtures.RegionTests.move

    def setUp(self):
        matrix.ActionTargetMatrixTests.setUp(self)
        matrix.fixtures.LeverTests.replace_asset_pixels(self, self.handle_on, (40, 20))
        self.source = self.targets["empty"]
        services.command(self.campaign.pk, self.gm.pk, "objects", {
            "mapId": str(self.scene.pk), "area": "images", "action": "update",
            "data": {"placement_id": str(self.source.pk), "x": 192, "y": 96,
                     "natural_width": 128, "natural_height": 64}}, uuid.uuid4())
        self.source.refresh_from_db()
        self.actor = Actor.objects.create(campaign=self.campaign, name="Artwork visitor", data={},
            permissions={str(self.player.pk): "owner"})

    @contextmanager
    def cell(self, **labels):
        with self.subTest(**labels), transaction.atomic():
            try:
                yield
            finally:
                transaction.set_rollback(True)

    def configure(self, definition, owner=None):
        owner = owner or self.source
        owner.refresh_from_db()
        if owner.kind == "zones":
            area, values = "zones", {"id": str(owner.pk), "expected_version": owner.version,
                                      "patch": {"blueprint": definition}}
        elif owner.kind == "walls":
            area, values = "walls", {"wall_id": str(owner.pk), "version": owner.version, "blueprint": definition}
        else:
            area, values = "images", {"placement_id": str(owner.pk), "blueprint": definition}
        return services.command(self.campaign.pk, self.gm.pk, "objects", {
            "mapId": str(self.scene.pk), "area": area, "action": "update", "data": values}, uuid.uuid4())

    def definition(self, identifiers, *, owner=None, mode="asset", group=False, event="presence:enter"):
        owner = owner or self.source
        kind = "region" if owner.kind == "zones" else "door" if owner.kind == "walls" else (
            "torch" if "torch" in owner.data else "lever")
        result = default_blueprint(kind)
        result["graphs"][event] = sprite_graph(event, identifiers, mode=mode,
            asset=str(self.handle_on.pk), group=group)
        return result

    def enter(self, *, rid=None):
        token = self.place()
        original_version = token.version
        result = self.move(token, 2, user=self.player, rid=rid)
        return token, original_version, result

    def step(self):
        run = AutomationRun.objects.filter(scene=self.scene, door_id=self.source.pk).latest("created_at")
        return next(step for step in run.data["events"][0]["steps"] if step["id"] == "art")

    def edit_image(self, target, **values):
        return services.command(self.campaign.pk, self.gm.pk, "objects", {
            "mapId": str(self.scene.pk), "area": "images", "action": "update",
            "data": {"placement_id": str(target.pk), **values}}, uuid.uuid4())

    def update_source(self):
        project = MapBuilderProject.objects.get(pk=self.project_id)
        saved = self.save(expected_version=project.version)
        self.assertEqual(saved.status_code, 200, saved.content)
        project.refresh_from_db()
        self.scene.refresh_from_db()
        return self.post(self.url + "/update", {"request_id": str(uuid.uuid4()),
            "expected_version": project.version, "expected_scene_version": self.scene.version})

    def test_empty_area_changes_each_visual_kind_with_reference_or_group(self):
        """24 committed crossings check actual visual effects and untouched logic."""
        for kind in ("door", "lever", "torch", "image"):
            for group in (False, True):
                for mode in ("asset", "hidden", "inherit"):
                    with self.cell(kind=kind, group=group, appearance=mode):
                        target = self.scene.elements.get(pk=self.targets[kind].pk)
                        before = deepcopy(target.data)
                        self.configure(self.definition([str(target.pk)], mode=mode, group=group))
                        self.enter()
                        target.refresh_from_db()
                        step = self.step()
                        self.assertFalse(step.get("unsupported"), step)
                        self.assertFalse(step.get("missing"), step)
                        self.assertEqual(step["targetIds"], [str(target.pk)])
                        if kind == "image":
                            if mode == "asset":
                                self.assertEqual(target.data["asset_id"], str(self.handle_on.pk))
                                self.assertEqual((target.data["natural_width"], target.data["natural_height"]), (40, 20))
                                self.assertEqual(target.data["scale"], min(
                                    before["natural_width"] * before["scale"] / 40,
                                    before["natural_height"] * before["scale"] / 20))
                            elif mode == "hidden":
                                self.assertEqual(target.data["layer"], "gm-image-layer")
                            else:
                                self.assertEqual(target.data["asset_id"], before["asset_id"])
                                self.assertEqual(target.data["layer"], before["layer"])
                        else:
                            self.assertEqual(target.data["sprite"], {"appearance": mode,
                                **({"assetId": str(self.handle_on.pk)} if mode == "asset" else {})})
                            self.assertEqual(element_state(target), "closed" if kind == "door" else "off")
                            if kind in ("lever", "torch") and mode != "hidden":
                                self.assertEqual(target.data["asset_id"],
                                    str(self.handle_on.pk) if mode == "asset" else before["asset_id"])
                        for field in ("x", "y", "x1", "x2", "y1", "y2", "rotation"):
                            if field in before:
                                self.assertEqual(target.data[field], before[field])
                        self.assertNotIn("automationVariables", target.data,
                            "Changing artwork must not start the target's interaction handler.")
                        self.source.refresh_from_db()
                        self.assertEqual(self.source.data["lever"]["state"], "off")
                        self.assertEqual((self.source.data["asset_id"], self.source.data["src"]), (None, ""))

    def test_enter_and_exit_restore_original_image_and_receipt_retry_is_exact(self):
        target = self.targets["image"]
        before = deepcopy(target.data)
        definition = self.definition([str(target.pk)])
        definition["graphs"]["presence:exit"] = sprite_graph("presence:exit", [str(target.pk)], mode="inherit")
        self.configure(definition)
        rid = uuid.uuid4()
        token, version, result = self.enter(rid=rid)
        target.refresh_from_db()
        self.assertEqual(target.data["asset_id"], str(self.handle_on.pk))
        changed_version = target.version
        self.assertEqual(self.token_command("move", {"id": str(token.pk), "gridX": 2, "gridY": 1,
            "expectedVersion": version}, user=self.player, rid=rid), result)
        target.refresh_from_db()
        self.assertEqual(target.version, changed_version)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene, door_id=self.source.pk).count(), 1)
        self.move(token, 0, user=self.player)
        target.refresh_from_db()
        self.assertEqual(target.data["asset_id"], before["asset_id"])
        self.assertEqual(target.data["layer"], before["layer"])
        for field in ("x", "y", "rotation", "scale", "natural_width", "natural_height"):
            self.assertEqual(target.data[field], before[field])
        self.assertNotIn("sprite", target.data)
        self.assertNotIn("spriteBase", target.data)
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene, door_id=self.source.pk).count(), 2)

    def test_region_and_all_other_owners_can_target_another_objects_sprite(self):
        target = self.targets["image"]
        for kind in ("door", "lever", "torch", "empty", "region"):
            with self.cell(owner=kind):
                owner = self.targets[kind]
                event = "presence:enter" if kind == "region" else "interact"
                self.configure(self.definition([str(target.pk)], owner=owner, event=event), owner)
                owner.refresh_from_db()
                before_state = element_state(owner)
                if kind == "region":
                    self.enter()
                else:
                    area = "walls" if kind == "door" else "images"
                    values = {"wall_id": str(owner.pk), "door_state": "open"} if kind == "door" else {
                        "image_id": str(owner.pk)}
                    services.command(self.campaign.pk, self.gm.pk, "objects", {
                        "mapId": str(self.scene.pk), "area": area,
                        "action": "door" if kind == "door" else "interact", "data": values}, uuid.uuid4())
                target.refresh_from_db()
                self.assertEqual(target.data["asset_id"], str(self.handle_on.pk))
                owner.refresh_from_db()
                if kind != "region":
                    self.assertEqual(element_state(owner), before_state)
                self.assertNotIn("automationVariables", target.data)

    def test_mixed_group_applies_supported_targets_and_identifies_incompatible_and_missing(self):
        missing = str(uuid.uuid4())
        ids = [str(self.targets[kind].pk) for kind in ("image", "door", "empty", "region")] + [missing]
        self.configure(self.definition(ids, group=True))
        self.enter()
        self.assertEqual(self.step()["targetIds"], ids[:2])
        self.assertEqual(self.step()["unsupportedIds"], ids[2:4])
        self.assertEqual(self.step()["missingIds"], [missing])
        self.source.refresh_from_db()
        self.assertEqual((self.source.data["asset_id"], self.source.data["src"]), (None, ""))
        region = self.targets["region"]
        region.refresh_from_db()
        self.assertNotIn("sprite", region.data)

    def test_self_visual_drafts_save_on_image_free_owners_and_skip_only_the_action(self):
        for kind in ("empty", "region"):
            for mode in ("asset", "hidden", "inherit"):
                with self.cell(owner=kind, appearance=mode):
                    owner = self.targets[kind]
                    definition = self.definition([str(owner.pk)], owner=owner, mode=mode)
                    graph = definition["graphs"]["presence:enter"]
                    graph["nodes"] = [value for value in graph["nodes"] if value["id"] != "ref"]
                    graph["edges"] = [edge for edge in graph["edges"] if edge["kind"] != "data"]
                    self.configure(definition, owner)
                    owner.refresh_from_db()
                    result = blueprint_testing.run(self.campaign.pk, self.gm.pk, self.scene.pk, owner.pk,
                        {"request_id": str(uuid.uuid4()), "event": "presence:enter", "expected_version": owner.version})
                    self.assertTrue(result["ok"], result)
                    step = next(step for step in result["run"]["events"][0]["steps"] if step["id"] == "art")
                    self.assertEqual(step["unsupportedIds"], [str(owner.pk)])
                    self.assertEqual(result["changes"]["elements"], [])

    def test_failure_after_sprite_rolls_back_image_token_presence_and_receipt(self):
        target = self.targets["image"]
        before = deepcopy(target.data)
        definition = self.definition([str(target.pk)])
        graph = definition["graphs"]["presence:enter"]
        graph["nodes"].append(node("fail", "light", targetId=str(self.light_object.pk), enabled=True))
        graph["edges"].append(execution("art", "fail"))
        self.configure(definition)
        token, rid = self.place(), uuid.uuid4()
        with override_settings(DYNAMIC_LIGHTING_ENABLED=False):
            with self.assertRaisesMessage(services.MapError, "Dynamic lighting is disabled"):
                self.move(token, 2, user=self.player, rid=rid)
        target.refresh_from_db()
        token.refresh_from_db()
        self.source.refresh_from_db()
        self.assertEqual(target.data, before)
        self.assertEqual(token.grid_x, 0)
        self.assertEqual(self.source.data["areaPresence"]["occupants"], [])
        self.assertFalse(Receipt.objects.filter(request_id=rid).exists())
        self.assertFalse(AutomationRun.objects.filter(scene=self.scene).exists())

    def test_private_image_snapshot_survives_move_resize_and_cannot_be_forged(self):
        target = self.targets["image"]
        original = deepcopy(target.data)
        definition = self.definition([str(target.pk)])
        definition["graphs"]["presence:exit"] = sprite_graph("presence:exit", [str(target.pk)], mode="inherit")
        self.configure(definition)
        token, _, _ = self.enter()
        target.refresh_from_db()
        base = deepcopy(target.data["spriteBase"])
        for user in (self.player, self.streamer):
            state = objects.layer_state(self.scene, services.member(self.campaign.pk, user.pk))
            image = next(row for row in state["images"] if row["id"] == str(target.pk))
            self.assertNotIn("spriteBase", image)
        self.edit_image(target, x=target.data["x"] + 5, y=target.data["y"] + 7)
        target.refresh_from_db()
        self.assertEqual(target.data["spriteBase"], base)
        self.assertEqual(target.data["sprite"], {"appearance": "asset", "assetId": str(self.handle_on.pk)})
        self.edit_image(target, scale=target.data["scale"] * 2)
        target.refresh_from_db()
        self.assertEqual(target.data["spriteBase"], {**base, "width": base["width"] * 2, "height": base["height"] * 2})
        self.move(token, 0)
        target.refresh_from_db()
        self.assertEqual(target.data["asset_id"], original["asset_id"])
        self.assertEqual(target.data["scale"], original["scale"] * 2)
        self.assertEqual((target.data["x"], target.data["y"]), (original["x"] + 5, original["y"] + 7))
        self.assertNotIn("spriteBase", target.data)
        self.edit_image(target, spriteBase={"assetId": str(self.foreign_asset.pk), "layer": "map", "width": 1, "height": 1},
            sprite={"appearance": "asset", "assetId": str(self.foreign_asset.pk)})
        target.refresh_from_db()
        self.assertNotIn("spriteBase", target.data)
        self.assertNotIn("sprite", target.data)
        self.assertEqual(target.data["asset_id"], original["asset_id"])

    def test_native_artwork_replaces_override_and_layer_edit_updates_its_base_layer(self):
        for field in ("asset_id", "layer"):
            with self.cell(field=field):
                target = self.scene.elements.get(pk=self.targets["image"].pk)
                self.configure(self.definition([str(target.pk)]))
                self.enter()
                self.edit_image(target, **({"asset_id": str(self.handle_off.pk)} if field == "asset_id" else {
                    "layer": "gm-image-layer"}))
                target.refresh_from_db()
                if field == "asset_id":
                    self.assertNotIn("spriteBase", target.data)
                    self.assertNotIn("sprite", target.data)
                else:
                    self.assertEqual(target.data["spriteBase"]["layer"], "gm-image-layer")
                    self.assertEqual(target.data["sprite"], {"appearance": "asset", "assetId": str(self.handle_on.pk)})
                self.assertEqual(target.data[field], str(self.handle_off.pk) if field == "asset_id" else "gm-image-layer")

    def test_source_update_keeps_live_artwork_until_authored_image_changes(self):
        # Restore the fixture's moved controller; native geometry is deliberately
        # protected from being overwritten by a builder update.
        source = next(row for row in self.doc["decorations"] if row["id"] == self.ids["empty"])
        self.edit_image(self.source, x=(source["x"] + source["width"] / 2) * 64,
            y=(source["y"] + source["height"] / 2) * 64,
            natural_width=source["width"] * 64, natural_height=source["height"] * 64)
        # The shared target fixture also made one generated door secret by a
        # native edit, which is unrelated to this image-update case.
        door = self.targets["door"]
        original = next(row for row in MapBuilderProject.objects.get(pk=self.project_id).generation["objects"]
            if row["id"] == str(door.pk))
        door.data = deepcopy(original["data"])
        door.save(update_fields=["data"])
        target = self.targets["image"]
        self.assertTrue(change_sprite(self.scene, target, {"appearance": "asset", "assetId": str(self.handle_on.pk)}))
        target.version += 1
        target.save(update_fields=["data", "version"])
        base = deepcopy(target.data["spriteBase"])
        response = self.update_source()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["scene"]["id"], str(self.scene.pk))
        target.refresh_from_db()
        self.assertEqual(target.data["asset_id"], str(self.handle_on.pk))
        self.assertEqual(target.data["spriteBase"], base)
        # Visibility actions update the acknowledged runtime layer, without
        # turning the image override into a conflicting native manual edit.
        for visible in (False, True):
            self.assertTrue(change_visual(self.scene, target, {"type": "setVisibility", "visible": visible}))
            target.version += 1
            target.save(update_fields=["data", "version"])
            validate_campaign_sprites(self.campaign)
            response = self.update_source()
            self.assertEqual(response.status_code, 200, response.content)
            target.refresh_from_db()
            self.assertEqual(target.data["asset_id"], str(self.handle_on.pk))
            self.assertEqual(target.data["spriteBase"], base)
        replacement = self.asset("New authored artwork", "#aabb33")
        self.doc["assets"].append({"assetId": str(replacement.pk), "role": "decoration"})
        source = next(row for row in self.doc["decorations"] if row["id"] == self.ids["image"])
        source["assetId"] = str(replacement.pk)
        response = self.update_source()
        self.assertEqual(response.status_code, 200, response.content)
        target.refresh_from_db()
        self.assertEqual(target.data["asset_id"], str(replacement.pk))
        self.assertNotIn("sprite", target.data)
        self.assertNotIn("spriteBase", target.data)

    def test_deleting_overridden_art_restores_base_and_deleting_base_removes_placement(self):
        for deleting in ("override", "base"):
            with self.cell(deleting=deleting):
                target = self.scene.elements.get(pk=self.targets["image"].pk)
                original_asset = target.data["asset_id"]
                self.configure(self.definition([str(target.pk)]))
                self.enter()
                asset = self.handle_on if deleting == "override" else self.handle_off
                response = self.post(f"/api/containers/{self.campaign.pk}/library/assets/delete", {"asset_id": str(asset.pk)})
                self.assertEqual(response.status_code, 200, response.content)
                if deleting == "override":
                    target.refresh_from_db()
                    self.assertEqual(target.data["asset_id"], original_asset)
                    self.assertNotIn("sprite", target.data)
                    self.assertNotIn("spriteBase", target.data)
                else:
                    self.assertFalse(self.scene.elements.filter(pk=target.pk).exists())

    def test_archive_roundtrip_remaps_live_and_base_artwork_and_restores_the_copy(self):
        target = self.targets["image"]
        self.configure(self.definition([str(target.pk)]))
        self.enter()
        cloned = import_campaign(export_campaign(self.campaign), self.gm, "Copied sprite targets")
        copied = SceneObject.objects.get(scene__campaign=cloned, data__spriteBase__isnull=False)
        self.assertNotEqual(copied.pk, target.pk)
        base_id, active_id = copied.data["spriteBase"]["assetId"], copied.data["asset_id"]
        self.assertNotEqual(base_id, str(self.handle_off.pk))
        self.assertNotEqual(active_id, str(self.handle_on.pk))
        self.assertEqual(MapAsset.objects.get(pk=base_id).campaign_id, cloned.pk)
        self.assertEqual(MapAsset.objects.get(pk=active_id).campaign_id, cloned.pk)
        self.assertEqual(copied.data["sprite"]["assetId"], active_id)
        self.assertTrue(change_sprite(copied.scene, copied, {"appearance": "inherit"}))
        self.assertEqual(copied.data["asset_id"], base_id)
        self.assertNotIn("spriteBase", copied.data)
        target.refresh_from_db()
        self.assertEqual(target.data["asset_id"], str(self.handle_on.pk), "Restoring the copy must not change the source.")

    def test_corrupted_archive_rejects_foreign_or_invalid_sprite_snapshot_without_partial_import(self):
        target = self.targets["image"]
        self.configure(self.definition([str(target.pk)]))
        self.enter()
        for invalid in ("foreign-base", "foreign-active", "boolean-width", "wrong-scale"):
            with self.subTest(invalid=invalid):
                def corrupt(payload):
                    data_ = next(record["fields"]["data"] for record in payload["records"]
                        if record["model"] == "gravewright_maps.sceneobject"
                        and "spriteBase" in record["fields"]["data"])
                    if invalid == "foreign-base":
                        data_["spriteBase"]["assetId"] = str(self.foreign_asset.pk)
                    elif invalid == "foreign-active":
                        data_["sprite"]["assetId"] = str(self.foreign_asset.pk)
                    elif invalid == "boolean-width":
                        data_["spriteBase"]["width"] = True
                    else:
                        data_["scale"] *= 2
                archive = archive_fixtures.SurfaceArchiveTests.corrupted_archive(self, corrupt)
                campaigns, assets, files = Campaign.objects.count(), MapAsset.objects.count(), self.files()
                with self.assertRaises(AuthError):
                    import_campaign(archive, self.gm, "Rejected sprite archive")
                self.assertEqual(Campaign.objects.count(), campaigns)
                self.assertEqual(MapAsset.objects.count(), assets)
                self.assertEqual(self.files(), files)

    def test_extreme_fitted_artwork_stays_editable_after_layer_and_asset_replacement(self):
        tiny = self.asset("Tiny replacement", "#cc4444")
        matrix.fixtures.LeverTests.replace_asset_pixels(self, tiny, (1, 1))
        for native_scale, artwork in ((.001, self.handle_on), (100, tiny)):
            with self.cell(native_scale=native_scale):
                target = self.scene.elements.get(pk=self.targets["image"].pk)
                self.edit_image(target, scale=native_scale)
                definition = self.definition([str(target.pk)])
                definition["graphs"]["presence:enter"]["nodes"][-1]["assetId"] = str(artwork.pk)
                definition["graphs"]["presence:exit"] = sprite_graph("presence:exit", [str(target.pk)], mode="inherit")
                self.configure(definition)
                token, _, _ = self.enter()
                target.refresh_from_db()
                self.assertFalse(.001 <= target.data["scale"] <= 100)
                validate_campaign_sprites(self.campaign)
                self.edit_image(target, layer="gm-image-layer")
                target.refresh_from_db()
                self.assertEqual(target.data["spriteBase"]["layer"], "gm-image-layer")
                self.edit_image(target, asset_id=str(self.handle_off.pk))
                target.refresh_from_db()
                self.assertEqual(target.data["spriteBase"]["assetId"], str(self.handle_off.pk))
                self.assertEqual(target.data["sprite"], {"appearance": "asset", "assetId": str(self.handle_off.pk)})
                self.edit_image(target, x=target.data["x"] + 1)
                validate_campaign_sprites(self.campaign)
                self.move(token, 0)
                target.refresh_from_db()
                self.assertEqual(target.data["asset_id"], str(self.handle_off.pk))
                self.assertIn("spriteBase", target.data,
                    "An extreme restored fit needs its validated box for later native edits.")
                self.edit_image(target, x=target.data["x"] + 1)
                validate_campaign_sprites(self.campaign)

    def test_foreign_resources_cannot_modify_other_campaigns(self):
        for foreign in ("asset", "reference", "group"):
            with self.cell(foreign=foreign):
                self.source.refresh_from_db()
                before = deepcopy(self.source.data)
                target_before = deepcopy(self.foreign_door.data)
                definition = self.definition([str(self.foreign_door.pk) if foreign != "asset"
                    else str(self.targets["image"].pk)], group=foreign == "group")
                if foreign == "asset":
                    definition["graphs"]["presence:enter"]["nodes"][-1]["assetId"] = str(self.foreign_asset.pk)
                if foreign == "reference":
                    self.configure(definition)
                    self.enter()
                    self.assertEqual(self.step()["missingIds"], [str(self.foreign_door.pk)])
                else:
                    with self.assertRaises(services.MapError):
                        self.configure(definition)
                self.source.refresh_from_db()
                self.foreign_door.refresh_from_db()
                if foreign != "reference":
                    self.assertEqual(self.source.data, before)
                self.assertEqual(self.foreign_door.data, target_before)
