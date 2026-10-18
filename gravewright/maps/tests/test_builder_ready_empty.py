"""Ready-made map bases and image-free intelligent objects keep native contracts."""

from copy import deepcopy
from io import BytesIO
import uuid

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from PIL import Image

from gravewright.administration.archives import export_campaign, import_campaign, options, records
from gravewright.accounts.services import AuthError
from gravewright.compendiums.graph import select
from gravewright.maps import builder_render, builder_services, objects, services
from gravewright.maps.blueprint_controls import control
from gravewright.maps.blueprint_network import state as network_state
from gravewright.maps.blueprint_testing import run_draft
from gravewright.maps.blueprints import default_blueprint
from gravewright.maps.models import Broadcast, MapAsset, MapBuilderProject, Scene

from . import test_builder_projects as fixtures
from . import test_surface_archives as surface_fixtures


def node(identifier, kind, **fields):
    return {"id": identifier, "type": kind, "x": 0, "y": 0, **fields}


def execution(origin, target, output="next"):
    return {"from": origin, "to": target, "output": output, "kind": "execution"}


def data(origin, target, *, output="door", port="target"):
    return {"from": origin, "to": target, "output": output, "input": port, "kind": "data"}


def graph(event, *actions):
    nodes = [node("event", "event", event=event), *actions]
    return {"nodes": nodes, "edges": [execution(a["id"], b["id"]) for a, b in zip(nodes, nodes[1:])]}


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow", DYNAMIC_LIGHTING_ENABLED=True)
class ReadyEmptyTests(TestCase):
    asset = fixtures.BuilderProjectTests.asset
    post = fixtures.BuilderProjectTests.post
    save = fixtures.BuilderProjectTests.save
    generate = fixtures.BuilderProjectTests.generate
    files = fixtures.BuilderProjectTests.files

    def setUp(self):
        fixtures.BuilderProjectTests.setUp(self)
        self.layer_id, self.empty_id = str(uuid.uuid4()), str(uuid.uuid4())
        self.doc.update(schemaVersion=3, layers=[{"id": self.layer_id, "name": "Details", "visible": True, "locked": False}],
                        decorations=[], lights=[])
        for kind in ("floors", "walls", "doors"):
            for row in self.doc[kind]:
                row["layerId"] = self.layer_id
        self.doc["floors"][0]["rotation"] = 0
        blueprint = default_blueprint("lever")
        blueprint["graphs"]["interact"] = graph("interact", node("on", "state", targetState="on"))
        self.empty = {"id": self.empty_id, "layerId": self.layer_id, "empty": True, "assetId": None,
                      "name": "Invisible switch", "x": 5, "y": 5, "width": 1, "height": 1, "rotation": 0,
                      "lever": {"state": "off"}, "blueprint": blueprint}
        self.doc["decorations"] = [self.empty]

    def generated(self):
        saved = self.save()
        self.assertEqual(saved.status_code, 200, saved.content)
        response = self.generate()
        self.assertEqual(response.status_code, 200, response.content)
        self.scene = Scene.objects.get(pk=response.json()["scene"]["id"])
        self.scene.visibility = "players"
        self.scene.save(update_fields=["visibility"])
        Broadcast.objects.update_or_create(campaign=self.campaign, defaults={"scene": self.scene})
        return self.scene.elements.get(kind="images", data__empty=True)

    def interact(self, row, user=None, request_id=None):
        return services.command(self.campaign.pk, (user or self.gm).pk, "objects", {
            "mapId": str(self.scene.pk), "area": "images", "action": "interact", "data": {"image_id": str(row.pk)}
        }, request_id or uuid.uuid4())

    def edit(self, row, **patch):
        return services.command(self.campaign.pk, self.gm.pk, "objects", {
            "mapId": str(self.scene.pk), "area": "images", "action": "update",
            "data": {"placement_id": str(row.pk), **patch}}, uuid.uuid4())

    def raster(self, document=None, **kwargs):
        with builder_render.render(document or self.doc, self.campaign.pk, **kwargs) as content:
            with Image.open(content) as image:
                return image.convert("RGBA")

    def test_background_is_independent_of_brush_roles_and_roundtrips(self):
        background = self.asset("Finished dungeon.png", "#336699")
        self.doc["backgroundImage"] = {"assetId": str(background.pk)}
        self.assertNotIn(str(background.pk), [row["assetId"] for row in self.doc["assets"]])
        self.generated()
        self.assertEqual(MapBuilderProject.objects.get(pk=self.project_id).document, self.doc)
        self.assertEqual(self.client.get(self.url).json()["project"]["document"]["backgroundImage"],
                         {"assetId": str(background.pk)})
        self.assertFalse(self.scene.elements.filter(data__asset_id=str(background.pk)).exists(),
                         "The full map is baked once, never also emitted as a tile or decoration.")

    def test_background_stretches_once_below_paint_and_alpha_preserves_color(self):
        output = BytesIO()
        with Image.new("RGBA", (8, 1)) as image:
            image.putdata([(12, 40, 80, 255)] * 4 + [(250, 200, 100, 0)] * 4)
            image.save(output, "PNG")
        background = MapAsset.objects.create(campaign=self.campaign, name="Two halves", width=8, height=1,
            file=ContentFile(output.getvalue(), name="halves.png"))
        self.doc["backgroundImage"] = {"assetId": str(background.pk)}
        self.doc["walls"], self.doc["doors"] = [], []
        with self.raster() as image:
            self.assertEqual(image.getpixel((0, 0)), (12, 40, 80, 255))
            self.assertEqual(image.getpixel((511, 511)), (17, 34, 51, 255))
            self.assertEqual(image.getpixel((128, 128)), (176, 32, 32, 255), "Paint covers the ready-made base.")

    def test_background_never_appears_in_dynamic_planes_or_masks(self):
        self.doc["backgroundImage"] = {"assetId": str(self.wall.pk)}
        selection = {"floors": [self.doc["floors"][0]["id"]]}
        with self.raster(selection=selection, crop=(0, 0, 512, 512)) as image:
            self.assertEqual(image.getpixel((0, 0))[3], 0)
            self.assertEqual(image.getpixel((128, 128)), (176, 32, 32, 255))
        with self.raster(selection=selection, crop=(0, 0, 512, 512), mask=True) as image:
            self.assertEqual(image.getpixel((0, 0))[3], 0)

    def test_background_rejects_foreign_generated_malformed_and_old_schema(self):
        generated_for = Scene.objects.create(campaign=self.campaign, name="Generated", width=512, height=512)
        generated = self.asset("Generated pixels", "#aabbcc")
        generated.generated_for = generated_for
        generated.save(update_fields=["generated_for"])
        mutations = [{"assetId": str(self.foreign_asset.pk)}, {"assetId": str(generated.pk)},
                     {"assetId": str(uuid.uuid4())}, {"assetId": "bad"}, None,
                     {"assetId": str(self.floor.pk), "repeat": True}]
        for value in mutations:
            with self.subTest(value=value):
                doc = {**self.doc, "backgroundImage": value}
                self.assertEqual(self.save(document=doc).status_code, 400)
        doc = {**self.doc, "schemaVersion": 2, "backgroundImage": {"assetId": str(self.floor.pk)}}
        self.assertEqual(self.save(document=doc).status_code, 400)

    def test_background_asset_deletion_updates_source_and_generation_recipe(self):
        self.doc["backgroundImage"] = {"assetId": str(self.wall.pk)}
        self.generated()
        source = MapBuilderProject.objects.get(pk=self.project_id)
        source.generation["dynamicDocument"] = deepcopy(source.document)
        source.save(update_fields=["generation"])
        builder_services.detach_project_art(self.campaign.pk, self.wall.pk)
        source.refresh_from_db()
        self.assertNotIn("backgroundImage", source.document)
        self.assertNotIn("backgroundImage", source.generation["dynamicDocument"])
        self.assertEqual(source.version, 2)
        self.assertTrue(source.document["decorations"][0]["empty"])

    def test_generated_empty_has_no_asset_but_keeps_geometry_name_and_private_rules(self):
        count = MapAsset.objects.count()
        row = self.generated()
        self.assertEqual(MapAsset.objects.count(), count, "No hidden bitmap is created for empty objects.")
        self.assertEqual((row.data["empty"], row.data["asset_id"], row.data["src"]), (True, None, ""))
        self.assertEqual(row.data["layer"], "gm-image-layer")
        self.assertEqual(row.data["lever"], {"state": "off", "baseAssetId": None, "baseLayer": "gm-image-layer", "width": 64, "height": 64})
        self.assertEqual((row.data["natural_width"], row.data["natural_height"], row.data["scale"]), (64, 64, 1))
        player = services.member(self.campaign.pk, self.player.pk)
        self.assertFalse(any(entry["id"] == str(row.pk) for entry in objects.layer_state(self.scene, player)["images"]))
        network = network_state(self.campaign.pk, self.gm.pk, self.scene.pk)
        entry = next(entry for entry in network["elements"] if entry["id"] == str(row.pk))
        self.assertTrue(entry["empty"])
        self.assertEqual(entry["name"], "Invisible switch")

    def test_empty_gm_interaction_runs_once_on_retry_and_controls_other_objects(self):
        blueprint = self.empty["blueprint"]
        blueprint["graphs"]["interact"] = graph("interact", node("on", "state", targetState="on"),
            node("open", "state", targetState="open"),
            node("value", "setVariable", scope="element", name="Uses", valueType="number", value=1))
        graph_ = blueprint["graphs"]["interact"]
        graph_["nodes"].append(node("door", "reference", targetId=self.doc["doors"][0]["id"]))
        graph_["edges"].append(data("door", "open"))
        row = self.generated()
        rid = uuid.uuid4()
        with self.assertRaises(services.MapError):
            self.interact(row, self.player)
        first = self.interact(row, self.gm, rid)
        self.assertEqual(self.interact(row, self.gm, rid), first)
        row.refresh_from_db()
        door = self.scene.elements.get(data__kind="door")
        self.assertEqual(row.data["lever"]["state"], "on")
        self.assertEqual(door.data["door_state"], "open")
        self.assertEqual(row.data["automationVariables"]["Uses"], {"type": "number", "value": 1})
        self.assertEqual((row.data["asset_id"], row.data["src"]), (None, ""))

    def test_empty_receives_named_signal_from_another_object(self):
        self.empty["blueprint"]["graphs"]["signal:Wake"] = graph("signal:Wake", node("on", "state", targetState="on"))
        door = self.doc["doors"][0]
        door["blueprint"] = default_blueprint()
        door["blueprint"]["graphs"]["interact"] = graph("interact", node("signal", "emitEvent", scope="element", name="Wake"))
        graph_ = door["blueprint"]["graphs"]["interact"]
        graph_["nodes"].append(node("empty", "reference", targetId=self.empty_id))
        graph_["edges"].append(data("empty", "signal"))
        row = self.generated()
        native_door = self.scene.elements.get(data__kind="door")
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk), "area": "walls", "action": "door",
            "data": {"wall_id": str(native_door.pk), "door_state": "closed"}}, uuid.uuid4())
        row.refresh_from_db()
        self.assertEqual(row.data["lever"]["state"], "on")

    def test_empty_rejects_source_art_and_state_art(self):
        mutations = [lambda row: row.update(assetId=str(self.floor.pk)), lambda row: row.update(empty=False),
            lambda row: row.update(empty="true"), lambda row: row.update(torch={}),
            lambda row: row.pop("lever"), lambda row: row.update(name="x"*121),
            lambda row: row["blueprint"]["states"]["on"].update(appearance="hidden")]
        for mutation in mutations:
            document = deepcopy(self.doc)
            mutation(document["decorations"][0])
            with self.subTest(document=document):
                response = self.save(document=document)
                self.assertEqual(response.status_code, 400, response.content)

    def test_empty_can_author_visual_nodes_with_external_or_self_references(self):
        blueprint = self.empty["blueprint"]
        blueprint["graphs"]["interact"] = graph("interact", node("art", "setAppearance", assetId=str(self.floor.pk)))
        graph_ = blueprint["graphs"]["interact"]
        graph_["nodes"].append(node("target", "reference", targetId=self.doc["doors"][0]["id"]))
        graph_["edges"].append(data("target", "art"))
        self.assertEqual(self.save().status_code, 200)
        graph_["nodes"][-1]["targetId"] = self.empty_id
        response = self.save(expected_version=1)
        self.assertEqual(response.status_code, 200, response.content)

    def test_empty_self_appearance_group_and_native_drafts_stay_image_free_at_execution(self):
        bp = self.empty["blueprint"]
        bp["graphs"]["interact"] = graph("interact", node("art", "setAppearance", assetId=str(self.floor.pk)))
        value = bp["graphs"]["interact"]
        value["nodes"].append(node("group", "elementGroup", memberType="element", name="Controllers", targetIds=[self.empty_id]))
        value["edges"].append(data("group", "art", output="targets"))
        row = self.generated()
        self.interact(row)
        row.refresh_from_db()
        self.assertEqual((row.data["asset_id"], row.data["src"]), (None, ""))
        self.assertNotIn("sprite", row.data)
        bp = default_blueprint("lever")
        bp["graphs"]["interact"] = graph("interact", node("art", "setAppearance", assetId=str(self.floor.pk)))
        value = bp["graphs"]["interact"]
        value["nodes"].append(node("owner", "reference", targetId=str(row.pk)))
        value["edges"].append(data("owner", "art"))
        self.edit(row, blueprint=bp)
        self.interact(row)
        row.refresh_from_db()
        self.assertEqual((row.data["asset_id"], row.data["src"]), (None, ""))
        self.assertNotIn("sprite", row.data)

    def test_visual_action_from_other_object_cannot_assign_empty_an_image(self):
        blueprint = default_blueprint()
        blueprint["graphs"]["interact"] = graph("interact", node("art", "setAppearance", assetId=str(self.floor.pk)),
            node("open", "state", targetState="open"))
        graph_ = blueprint["graphs"]["interact"]
        graph_["nodes"].append(node("empty", "reference", targetId=self.empty_id))
        graph_["edges"].append(data("empty", "art"))
        self.doc["doors"][0]["blueprint"] = blueprint
        row = self.generated()
        native_door = self.scene.elements.get(data__kind="door")
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk), "area": "walls", "action": "door",
            "data": {"wall_id": str(native_door.pk), "door_state": "closed"}}, uuid.uuid4())
        row.refresh_from_db()
        native_door.refresh_from_db()
        self.assertEqual((row.data["asset_id"], row.data["src"]), (None, ""))
        self.assertNotIn("sprite", row.data)
        self.assertEqual(native_door.data["door_state"], "open", "The inert artwork action does not block later actions.")

    def test_native_empty_move_resize_rename_preserves_rules_and_cannot_receive_art(self):
        row = self.generated()
        self.interact(row)
        row.refresh_from_db()
        blueprint = deepcopy(row.data["blueprint"])
        self.edit(row, x=200, y=210, rotation=45, scale=1.5, name="Controller")
        row.refresh_from_db()
        self.assertEqual((row.data["x"], row.data["y"], row.data["rotation"]), (200, 210, 45))
        self.assertEqual(row.data["name"], "Controller")
        self.assertEqual(row.data["lever"]["state"], "on")
        self.assertEqual((row.data["lever"]["width"], row.data["lever"]["height"]), (96, 96))
        self.assertEqual(row.data["blueprint"], blueprint)
        for patch in ({"asset_id": str(self.floor.pk)}, {"src": "/game/map-assets/anything"}, {"empty": False}):
            with self.subTest(patch=patch), self.assertRaises(services.MapError):
                self.edit(row, **patch)
        with self.assertRaises(services.MapError):
            control(self.campaign.pk, self.gm.pk, self.scene.pk, row.pk, {"request_id": str(uuid.uuid4()),
                "expected_version": row.version, "action": "appearance", "value": str(self.floor.pk)})

    def test_native_empty_copy_keeps_geometry_and_rules_without_creating_an_asset(self):
        row = self.generated()
        count = MapAsset.objects.count()
        result = services.command(self.campaign.pk, self.gm.pk, "objects", {
            "mapId": str(self.scene.pk), "area": "images", "action": "create",
            "data": {**deepcopy(row.data), "x": 128, "y": 192, "name": "Copied controller"}}, uuid.uuid4())
        copy = self.scene.elements.get(pk=result["image"]["id"])
        self.assertNotEqual(copy.pk, row.pk)
        self.assertEqual((copy.data["x"], copy.data["y"], copy.data["name"]), (128, 192, "Copied controller"))
        self.assertEqual(copy.data["blueprint"], row.data["blueprint"])
        self.assertEqual((copy.data["empty"], copy.data["asset_id"], copy.data["src"]), (True, None, ""))
        self.assertEqual(MapAsset.objects.count(), count)

    def test_empty_interaction_authority_and_native_revision_conflict(self):
        self.empty["interactionEnabled"] = False
        row = self.generated()
        with self.assertRaises(services.MapError):
            self.interact(row, self.player)
        with self.assertRaises(services.MapError):
            self.edit(row, expected_version=0, x=100)
        self.interact(row)
        row.refresh_from_db()
        self.assertEqual(row.data["lever"]["state"], "on")
        self.assertFalse(row.data["interactionEnabled"])

    def test_empty_draft_rehearsal_runs_without_creating_art_or_mutating_the_project(self):
        count = MapAsset.objects.count()
        response = run_draft(self.campaign.pk, self.gm.pk, {"request_id": str(uuid.uuid4()),
            "document": self.doc, "elementId": self.empty_id, "event": "interact"})
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["run"]["stateAfter"], "on")
        self.assertEqual(MapAsset.objects.count(), count)
        self.assertFalse(MapBuilderProject.objects.exists())
        self.assertFalse(Scene.objects.exists())

    def test_empty_destroy_handler_runs_before_removal(self):
        blueprint = self.empty["blueprint"]
        blueprint["graphs"]["destroy"] = graph("destroy", node("open", "state", targetState="open"))
        graph_ = blueprint["graphs"]["destroy"]
        graph_["nodes"].append(node("door", "reference", targetId=self.doc["doors"][0]["id"]))
        graph_["edges"].append(data("door", "open"))
        row = self.generated()
        services.command(self.campaign.pk, self.gm.pk, "objects", {"mapId": str(self.scene.pk), "area": "images", "action": "delete",
            "data": {"placement_id": str(row.pk)}}, uuid.uuid4())
        self.assertFalse(self.scene.elements.filter(pk=row.pk).exists())
        self.assertEqual(self.scene.elements.get(data__kind="door").data["door_state"], "open")

    def test_archive_and_scene_pack_remap_background_and_keep_empty_image_free(self):
        ready = self.asset("Only referenced by background.png", "#112244")
        self.doc["backgroundImage"] = {"assetId": str(ready.pk)}
        row = self.generated()
        cloned = import_campaign(export_campaign(self.campaign), self.gm, "Imported ready map")
        project = MapBuilderProject.objects.get(campaign=cloned)
        background = MapAsset.objects.get(pk=project.document["backgroundImage"]["assetId"])
        self.assertEqual(background.campaign_id, cloned.pk)
        self.assertNotEqual(background.pk, ready.pk)
        empty = project.scene.elements.get(data__empty=True)
        self.assertNotEqual(empty.pk, row.pk)
        self.assertEqual((empty.data["asset_id"], empty.data["src"], empty.data["lever"]["baseAssetId"]), (None, "", None))
        builder_services.clean_document(project.document, services.member(cloned.pk, self.gm.pk))
        selected = select(records(self.campaign, options()), ("gravewright_maps.scene", str(self.scene.pk)))
        self.assertIn(("gravewright_maps.mapasset", str(ready.pk)), [(entry["model"], str(entry["pk"])) for entry in selected])

    def test_import_rejects_art_in_empty_or_a_foreign_background_and_rolls_back(self):
        self.doc["backgroundImage"] = {"assetId": str(self.floor.pk)}
        self.generated()
        def native_asset(payload):
            record = next(row for row in payload["records"] if row["model"] == "gravewright_maps.sceneobject"
                          and row["fields"]["data"].get("empty"))
            record["fields"]["data"]["asset_id"] = str(self.floor.pk)
        def native_base_asset(payload):
            record = next(row for row in payload["records"] if row["model"] == "gravewright_maps.sceneobject"
                          and row["fields"]["data"].get("empty"))
            record["fields"]["data"]["lever"]["baseAssetId"] = str(self.floor.pk)
        def foreign_background(payload):
            record = next(row for row in payload["records"] if row["model"] == "gravewright_maps.mapbuilderproject")
            record["fields"]["document"]["backgroundImage"]["assetId"] = str(self.foreign_asset.pk)
        def source_empty_art(payload):
            record = next(row for row in payload["records"] if row["model"] == "gravewright_maps.mapbuilderproject")
            record["fields"]["document"]["decorations"][0]["assetId"] = str(self.floor.pk)
        before_files, before_campaigns = self.files(), self.campaign.__class__.objects.count()
        for mutate in (native_asset, native_base_asset, foreign_background, source_empty_art):
            with self.subTest(mutate=mutate.__name__):
                archive = surface_fixtures.SurfaceArchiveTests.corrupted_archive(self, mutate)
                with self.assertRaises(AuthError):
                    import_campaign(archive, self.gm, "Invalid empty map")
                self.assertEqual(self.campaign.__class__.objects.count(), before_campaigns)
                self.assertEqual(self.files(), before_files)

    def test_uvtt_export_omits_empty_controllers_and_preserves_the_ready_map(self):
        import base64
        from gravewright.maps.universal_vtt import export_map
        self.doc["backgroundImage"] = {"assetId": str(self.floor.pk)}
        self.generated()
        result = export_map(self.campaign.pk, self.gm.pk, self.scene.pk)
        with Image.open(BytesIO(base64.b64decode(result["document"]["image"]))) as image:
            self.assertEqual(image.size, (512, 512))
            # The empty controller's box occupies this point, but it adds no art.
            self.assertEqual(image.convert("RGB").getpixel((350, 350)), (176, 32, 32))

    def test_update_keeps_empty_live_state_and_new_background_without_duplicates(self):
        row = self.generated()
        self.interact(row)
        self.doc["backgroundImage"] = {"assetId": str(self.floor.pk)}
        saved = self.save(expected_version=1)
        self.assertEqual(saved.status_code, 200, saved.content)
        self.scene.refresh_from_db()
        response = self.post(self.url + "/update", {"request_id": str(uuid.uuid4()), "expected_version": 2,
            "expected_scene_version": self.scene.version})
        self.assertEqual(response.status_code, 200, response.content)
        row.refresh_from_db()
        self.assertEqual(row.data["lever"]["state"], "on")
        self.assertEqual(self.scene.elements.filter(data__empty=True).count(), 1)
        self.assertEqual((row.data["asset_id"], row.data["src"]), (None, ""))
