"""Composed torches keep flame, mechanism, native children and authority separate."""

from copy import deepcopy
import uuid

from django.test import TestCase, override_settings

from gravewright.journals.services import JournalError
from gravewright.maps import builder_services, objects, services
from gravewright.maps.blueprints import clean_blueprint, default_blueprint
from gravewright.maps.models import AutomationRun, MapBuilderProject, Receipt

from . import test_builder_blueprints as fixtures
from .test_levers import data, execution, node


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow",
                   DYNAMIC_LIGHTING_ENABLED=True)
class TorchTests(TestCase):
    asset = fixtures.BuilderBlueprintTests.asset
    post = fixtures.BuilderBlueprintTests.post
    save = fixtures.BuilderBlueprintTests.save
    generate = fixtures.BuilderBlueprintTests.generate
    files = fixtures.BuilderBlueprintTests.files
    generated = fixtures.BuilderBlueprintTests.generated
    update_scene = fixtures.BuilderBlueprintTests.update_scene

    def setUp(self):
        fixtures.BuilderBlueprintTests.setUp(self)
        self.art = self.asset("torch.png", "#ffb633")
        self.doc["assets"].append({"assetId": str(self.art.pk), "role": "decoration"})
        self.torch_id, self.particle_id, self.shader_id = [str(uuid.uuid4()) for _ in range(3)]
        layer = self.doc["layers"][0]["id"]
        self.doc["lights"][0].update(x=5.5, y=5, enabled=True, animation="torch")
        self.doc["particles"] = [{"id": self.particle_id, "layerId": layer, "x": 5.5, "y": 5,
            "kind": "ember", "scale": .5, "density": .5, "color": "#ffa200", "enabled": True,
            "rotation": 0, "light_response": 0, "light_emission": 1}]
        self.doc["shaders"] = [{"id": self.shader_id, "layerId": layer, "x": 5.5, "y": 5,
            "name": "Flame", "source": "void main(){gl_FragColor=vec4(1.0);}", "radius": 1,
            "scale": 1, "intensity": .6, "opacity": 1, "speed": 1, "color": "#ff9900",
            "rotation": 0, "blend_mode": "add", "enabled": False, "light_response": 0, "light_emission": 1}]
        blueprint = default_blueprint("torch")
        blueprint["graphs"]["interact"] = {
            "nodes": [node("event", "event", event="interact"),
                      node("door", "reference", targetId=self.doc["doors"][0]["id"]),
                      node("open", "state", targetState="open"),
                      node("check", "condition", state="off"),
                      node("on", "state", targetState="on"), node("off", "state", targetState="off")],
            "edges": [execution("event", "check"), execution("check", "on", "true"),
                      execution("on", "open"), execution("check", "off", "false"),
                      data("door", "door", "open", "target")]}
        self.doc["decorations"] = [{"id": self.torch_id, "assetId": str(self.art.pk), "layerId": layer,
            "x": 5, "y": 5, "width": 1, "height": 1, "rotation": 0,
            "torch": {"state": "off", "lit": True, "lightId": self.light_id,
                      "particleId": self.particle_id, "shaderId": self.shader_id}, "blueprint": blueprint}]

    def torch(self):
        return self.scene.elements.get(kind="images", data__torch__isnull=False)

    def children(self, parent=None):
        return {kind: self.scene.elements.get(pk=link["id"]) for kind, link in
                (parent or self.torch()).data["torch"]["components"].items()}

    def command(self, action="interact", user=None, request_id=None, **payload):
        return services.command(self.campaign.pk, (user or self.gm).pk, "objects",
            {"mapId": str(self.scene.pk), "area": "images", "action": action,
             "data": {"image_id": str(self.torch().pk), **payload}}, request_id or uuid.uuid4())

    def edit_image(self, **payload):
        return services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk),
            "area": "images", "action": "update", "data": {"placement_id": str(self.torch().pk), **payload}}, uuid.uuid4())

    def test_generation_owns_native_components_and_preserves_authored_enable_flags(self):
        self.generated()
        parent, children = self.torch(), self.children()
        self.assertEqual(parent.data["torch"]["baseRotation"], 0)
        self.assertEqual(set(children), {"lights", "particles", "shaders"})
        self.assertTrue(children["lights"].data["enabled"])
        self.assertFalse(children["shaders"].data["enabled"])
        self.assertNotEqual(parent.data["torch"]["components"]["lights"]["id"], self.light_id)
        self.assertEqual((children["lights"].data["x"], children["lights"].data["y"]), (352, 320))

    def test_player_turn_opens_door_but_extinguishing_preserves_mechanism_and_position(self):
        self.generated()
        response = self.command(user=self.player)
        self.assertEqual(response["image"]["torch"], {"state": "on", "lit": True})
        self.assertNotIn("blueprint", response)
        parent = self.torch()
        self.assertEqual(parent.data["rotation"], 90)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "open")
        children = self.children()
        self.assertAlmostEqual(children["lights"].data["x"], 384)
        self.assertAlmostEqual(children["lights"].data["y"], 352)
        count = AutomationRun.objects.filter(scene=self.scene).count()
        self.command("torch-light", user=self.player, lit=False)
        self.assertEqual((self.torch().data["rotation"], self.torch().data["torch"]["state"]), (90, "on"))
        self.assertTrue(all(not row.data["enabled"] for row in self.children().values()))
        self.assertEqual(AutomationRun.objects.filter(scene=self.scene).count(), count)
        self.command("torch-light", lit=True)
        self.assertTrue(self.children()["lights"].data["enabled"])
        self.assertFalse(self.children()["shaders"].data["enabled"])

    def test_generation_of_turned_torch_rotates_components_once(self):
        self.doc["decorations"][0]["torch"]["state"] = "on"
        self.generated()
        self.assertEqual(self.torch().data["rotation"], 90)
        self.assertAlmostEqual(self.children()["lights"].data["x"], 384)
        self.assertAlmostEqual(self.children()["lights"].data["y"], 352)
        self.update_scene()
        self.assertAlmostEqual(self.children()["lights"].data["x"], 384)

    def test_source_update_keeps_live_mechanism_and_flame_and_archive_remaps_links(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        self.generated()
        self.command()
        self.command("torch-light", lit=False)
        self.update_scene()
        self.assertEqual(self.torch().data["torch"]["state"], "on")
        self.assertFalse(self.torch().data["torch"]["lit"])
        self.assertAlmostEqual(self.children()["lights"].data["x"], 384)
        restored = import_campaign(export_campaign(self.campaign), self.gm, "Torch clone")
        source = MapBuilderProject.objects.get(campaign=restored)
        parent = source.scene.elements.get(kind="images", data__torch__isnull=False)
        child = source.scene.elements.get(pk=parent.data["torch"]["components"]["lights"]["id"])
        self.assertEqual(child.kind, "lights")
        self.assertNotEqual(str(child.pk), str(self.children()["lights"].pk))
        builder_services.update(restored.pk, self.gm.pk, source.pk, {"request_id": str(uuid.uuid4()),
            "expected_version": source.version, "expected_scene_version": source.scene.version})

    def test_native_transform_move_rotate_resize_keeps_components_together(self):
        self.generated()
        self.edit_image(x=400, y=400, rotation=90, scale=8)
        children = self.children()
        self.assertAlmostEqual(children["lights"].data["x"], 464)
        self.assertAlmostEqual(children["lights"].data["y"], 400)
        self.assertEqual(children["lights"].data["rotation"], 90)
        self.assertEqual(self.torch().data["torch"]["baseRotation"], 90)
        with self.assertRaisesMessage(services.MapError, "changed in the VTT"):
            self.update_scene()

    def test_native_duplicate_clones_children_and_private_graph_independently(self):
        self.generated()
        original = self.torch()
        result = self.command("duplicate", x=500, y=500)
        clone = self.scene.elements.get(pk=result["image"]["id"])
        self.assertNotEqual(str(clone.pk), str(original.pk))
        self.assertTrue({child["id"] for child in original.data["torch"]["components"].values()}.isdisjoint(
                        {child["id"] for child in clone.data["torch"]["components"].values()}))
        cloned_light = self.children(clone)["lights"]
        self.assertAlmostEqual(cloned_light.data["x"], 500)
        self.assertAlmostEqual(cloned_light.data["y"], 468)

    def test_invalid_reference_kind_foreign_layer_ownership_and_flags_are_rejected(self):
        original = deepcopy(self.doc)
        bad = [lambda d: d["decorations"][0]["torch"].update(lightId=self.particle_id),
               lambda d: d["decorations"][0]["torch"].update(lit="true"),
               lambda d: d["decorations"][0].update(lever={"state": "off"}),
               lambda d: d["decorations"].append({**deepcopy(d["decorations"][0]), "id": str(uuid.uuid4())}),
               lambda d: d["lights"][0].update(layerId=str(uuid.uuid4()))]
        for mutate in bad:
            self.doc = deepcopy(original)
            mutate(self.doc)
            with self.subTest(document=self.doc), self.assertRaises(services.MapError):
                builder_services.clean_document(self.doc, self.membership)

    def test_player_projection_and_hidden_torch_authority(self):
        self.generated()
        who = services.member(self.campaign.pk, self.player.pk)
        public, = objects.layer_state(self.scene, who)["images"]
        self.assertEqual(public["torch"], {"state": "off", "lit": True})
        self.assertNotIn("blueprint", public)
        self.edit_image(layer="gm-image-layer")
        self.assertEqual(objects.layer_state(self.scene, who)["images"], [])
        self.assertTrue(all(not child.data["enabled"] for child in self.children().values()))
        for action, payload in (("interact", {}), ("torch-light", {"lit": False})):
            with self.subTest(action=action), self.assertRaises(services.MapError):
                self.command(action, user=self.player, **payload)
        with self.assertRaises(JournalError):
            self.command("torch-light", user=self.streamer, lit=False)

    def test_paused_automation_preserves_native_mechanism_flame_and_retry(self):
        self.generated()
        self.scene.settings = {**self.scene.settings, "automationPaused": True}
        self.scene.save(update_fields=["settings"])
        request_id = uuid.uuid4()
        first = self.command(request_id=request_id)
        again = self.command(request_id=request_id)
        self.assertEqual(first, again)
        self.assertEqual(self.torch().data["rotation"], 0)
        self.assertAlmostEqual(self.children()["lights"].data["x"], 352)
        self.assertAlmostEqual(self.children()["lights"].data["y"], 320)
        self.assertEqual(AutomationRun.objects.get(scene=self.scene).outcome, "paused")
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.command("torch-light", lit=False)
        self.update_scene()
        self.assertFalse(self.torch().data["torch"]["lit"])

    def test_flame_graph_targets_torch_without_turning_or_exposes_unsupported_target(self):
        blueprint = self.doc["doors"][0]["blueprint"] = default_blueprint()
        blueprint["version"] = 2
        blueprint["graphs"]["interact"] = {"nodes": [node("event", "event", event="interact"),
            node("ref", "reference", targetId=self.torch_id), node("flame", "flame", enabled=False)],
            "edges": [execution("event", "flame"), data("ref", "door", "flame", "target")]}
        self.generated()
        fixtures.BuilderBlueprintTests.command(self)
        self.assertFalse(self.torch().data["torch"]["lit"])
        self.assertEqual(self.torch().data["torch"]["state"], "off")
        blueprint = default_blueprint()
        blueprint["graphs"]["interact"] = fixtures.graph("interact", {"type": "flame", "enabled": False})
        self.door_object.refresh_from_db()
        self.door_object.data["blueprint"] = clean_blueprint(blueprint)
        self.door_object.save(update_fields=["data"])
        fixtures.BuilderBlueprintTests.command(self)
        latest = AutomationRun.objects.filter(scene=self.scene).latest("created_at")
        self.assertTrue(next(step for step in latest.data["events"][0]["steps"] if step["type"] == "flame")["unsupported"])
        blueprint["version"] = 1
        for edge in blueprint["graphs"]["interact"]["edges"]:
            edge.pop("kind", None)
        with self.assertRaises(services.MapError):
            clean_blueprint(blueprint)

    def test_native_edit_off_component_does_not_accidentally_erase_enable_preference(self):
        self.generated()
        self.command("torch-light", lit=False)
        light = self.children()["lights"]
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk), "area": "lights",
            "action": "update", "data": {"light_id": str(light.pk), "color": "#ff0000", "enabled": False}}, uuid.uuid4())
        self.command("torch-light", lit=True)
        self.assertTrue(self.children()["lights"].data["enabled"])
        self.assertEqual(self.children()["lights"].data["color"], "#ff0000")

    def test_delete_owner_cascades_children_and_required_light_dissolves_group(self):
        self.generated()
        parent, child_ids = self.torch(), [child["id"] for child in self.torch().data["torch"]["components"].values()]
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk), "area": "lights",
            "action": "delete", "data": {"light_id": child_ids[0]}}, uuid.uuid4())
        parent.refresh_from_db()
        self.assertNotIn("torch", parent.data)
        self.assertFalse(self.scene.elements.filter(pk__in=child_ids).exists())

    def test_asset_removal_cleans_native_group_source_and_update_snapshot(self):
        self.doc["decorations"][0]["torch"]["state"] = "on"
        self.generated()
        response = self.post(f"/api/containers/{self.campaign.pk}/library/assets/delete", {"asset_id": str(self.art.pk)})
        self.assertEqual(response.status_code, 200, response.content)
        source = MapBuilderProject.objects.get(pk=self.project_id)
        self.assertIsNone(source.document["decorations"][0]["assetId"])
        self.assertNotIn("torch", source.document["decorations"][0])
        self.assertEqual(source.document["decorations"][0]["rotation"], 90)
        self.assertEqual(source.document["lights"], [])
        self.assertFalse(self.scene.elements.filter(kind__in=("images", "lights", "particles", "shaders")).exists())
        builder_services.clean_document(source.document, self.membership)
        self.update_scene()

    def test_native_child_edit_is_not_adopted_by_later_mechanism_or_flame_changes(self):
        self.generated()
        light = self.children()["lights"]
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk), "area": "lights",
            "action": "update", "data": {"light_id": str(light.pk), "x": 360, "color": "#00ff00"}}, uuid.uuid4())
        self.command()
        self.command("torch-light", lit=False)
        self.command("torch-light", lit=True)
        with self.assertRaisesMessage(services.MapError, "changed in the VTT"):
            self.update_scene()
        self.assertEqual(self.children()["lights"].data["color"], "#00ff00")

    def test_missing_child_rolls_back_whole_chain_including_opening_door(self):
        self.generated()
        parent_before = deepcopy(self.torch().data)
        self.children()["particles"].delete()
        with self.assertRaisesMessage(services.MapError, "component is missing"):
            self.command()
        self.assertEqual(self.torch().data, parent_before)
        self.door_object.refresh_from_db()
        self.assertEqual(self.door_object.data["door_state"], "closed")
        self.assertTrue(AutomationRun.objects.filter(scene=self.scene, outcome="failed").exists())

    def test_deleting_parent_removes_children_and_native_light_actions(self):
        self.generated()
        parent, children = self.torch(), self.children()
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk), "area": "images",
            "action": "delete", "data": {"placement_id": str(parent.pk)}}, uuid.uuid4())
        self.assertFalse(self.scene.elements.filter(pk__in=[child.pk for child in children.values()]).exists())
        self.door_object.refresh_from_db()
        self.assertTrue(all(node_["type"] != "light" for graph in self.door_object.data["blueprint"]["graphs"].values()
                            for node_ in graph["nodes"]))

    def test_deleting_optional_child_preserves_torch_and_other_components(self):
        self.generated()
        particle = self.children()["particles"]
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk), "area": "particles",
            "action": "delete", "data": {"emitter_id": str(particle.pk)}}, uuid.uuid4())
        self.assertNotIn("particles", self.torch().data["torch"]["components"])
        self.command("torch-light", lit=False)
        self.assertFalse(self.children()["lights"].data["enabled"])

    def test_resetting_hidden_live_sprite_restores_flame_and_keeps_mechanism(self):
        self.doc["decorations"][0]["blueprint"]["graphs"]["interact"] = {
            "nodes": [node("event", "event", event="interact"), node("turn", "state", targetState="on"),
                      node("hide", "sprite", appearance="hidden")],
            "edges": [execution("event", "turn"), execution("turn", "hide")]}
        self.generated()
        self.command()
        self.assertEqual(self.torch().data["layer"], "gm-image-layer")
        self.assertTrue(all(not child.data["enabled"] for child in self.children().values()))
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk), "area": "automation",
            "action": "clear-sprite", "data": {"wall_id": str(self.torch().pk)}}, uuid.uuid4())
        self.assertEqual(self.torch().data["layer"], "map")
        self.assertEqual(self.torch().data["rotation"], 90)
        self.assertTrue(self.children()["lights"].data["enabled"])

    def test_source_replacing_owned_light_keeps_live_mechanism_and_binds_new_component(self):
        self.generated()
        self.command()
        previous_id = self.light_id
        self.light_id = str(uuid.uuid4())
        self.doc["lights"][0]["id"] = self.light_id
        self.doc["decorations"][0]["torch"]["lightId"] = self.light_id
        for graph in self.doc["doors"][0]["blueprint"]["graphs"].values():
            for entry_ in graph["nodes"]:
                if entry_.get("targetId") == previous_id:
                    entry_["targetId"] = self.light_id
        response = self.save(expected_version=1)
        self.assertEqual(response.status_code, 200, response.content)
        self.update_scene()
        self.assertEqual(self.torch().data["torch"]["state"], "on")
        self.assertEqual(self.torch().data["rotation"], 90)
        self.assertTrue(self.children()["lights"].data["enabled"])

    def test_disabled_dynamic_lighting_blocks_native_and_paused_torch_writes_atomically(self):
        self.generated()
        before = {str(row.pk): deepcopy(row.data) for row in self.scene.elements.all()}
        commands = [("flame", lambda: self.command("torch-light", lit=False)), ("interact", lambda: self.command()),
                    ("move", lambda: self.edit_image(x=400)), ("duplicate", lambda: self.command("duplicate", x=400))]
        for paused in (False, True):
            self.scene.settings = {**self.scene.settings, "automationPaused": paused}
            self.scene.save(update_fields=["settings"])
            with self.settings(DYNAMIC_LIGHTING_ENABLED=False):
                for action, command in commands:
                    with self.subTest(paused=paused, action=action):
                        if paused and action == "interact":
                            response = command()
                            self.assertEqual(response["image"]["torch"], before[str(self.torch().pk)]["torch"])
                            self.assertEqual(AutomationRun.objects.filter(scene=self.scene).latest("created_at").outcome, "paused")
                        else:
                            with self.assertRaisesMessage(services.MapError, "Dynamic lighting is disabled"):
                                command()
                    self.assertEqual({str(row.pk): row.data for row in self.scene.elements.all()}, before)

    def test_disabled_dynamic_lighting_rolls_back_flame_chain_and_reports_failure(self):
        blueprint = self.doc["doors"][0]["blueprint"] = default_blueprint()
        blueprint["version"] = 2
        blueprint["graphs"]["interact"] = {"nodes": [node("event", "event", event="interact"),
            node("ref", "reference", targetId=self.torch_id), node("flame", "flame", enabled=False)],
            "edges": [execution("event", "flame"), data("ref", "door", "flame", "target")]}
        self.generated()
        before = {str(row.pk): deepcopy(row.data) for row in self.scene.elements.all()}
        with self.settings(DYNAMIC_LIGHTING_ENABLED=False), self.assertRaisesMessage(
                services.MapError, "Dynamic lighting is disabled"):
            fixtures.BuilderBlueprintTests.command(self)
        self.assertEqual({str(row.pk): row.data for row in self.scene.elements.all()}, before)
        failed = AutomationRun.objects.filter(scene=self.scene, outcome="failed").get()
        self.assertEqual(failed.data["message"], "Dynamic lighting is disabled.")
