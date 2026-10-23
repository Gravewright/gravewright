"""Portable scene interchange validates geometry, raster limits and publication receipts."""

import base64
from copy import deepcopy
from io import BytesIO
import json
import struct
from unittest.mock import patch
import uuid
import zlib

from django.test import SimpleTestCase, TestCase, override_settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from gravewright.journals.services import JournalError

from gravewright.maps import builder_dynamic, builder_services, extra_objects, objects, services, universal_vtt as uvtt
from gravewright.maps.blueprint_actions import change_sprite, validate_campaign_sprites
from gravewright.maps.blueprints import default_blueprint
from gravewright.maps.models import Broadcast, MapAsset, MapBuilderProject, Receipt, Scene, SceneObject, Tile
from . import test_builder_projects as fixtures
from . import test_builder_free_paint as free_fixtures
from .test_builder_terrain_brush import brush


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"], GRAVEWRIGHT_MAP_TILER="pillow", ALLOWED_HOSTS=["testserver"])
class UniversalVttTests(TestCase):
    setUp = free_fixtures.BuilderFreePaintTests.setUp
    asset = fixtures.BuilderProjectTests.asset
    post = fixtures.BuilderProjectTests.post
    save = fixtures.BuilderProjectTests.save
    generate = fixtures.BuilderProjectTests.generate
    files = fixtures.BuilderProjectTests.files

    def document(self):
        with Image.new("RGBA", (128, 128), (17, 34, 51, 255)) as image, BytesIO() as output:
            image.save(output, "PNG")
            encoded = base64.b64encode(output.getvalue()).decode()
        return {"format": .2, "resolution": {"map_origin": {"x": 10.5, "y": -2.25}, "map_size": {"x": 4, "y": 4}, "pixels_per_grid": 32},
                "line_of_sight": [[{"x": 10.5, "y": -2.25}, {"x": 14.5, "y": -2.25}]], "objects_line_of_sight": [],
                "portals": [{"bounds": [{"x": 11.5, "y": -2.25}, {"x": 12.5, "y": -2.25}], "position": {"x": 12, "y": -2.25},
                             "rotation": 0, "closed": False, "freestanding": False}],
                "environment": {"baked_lighting": False, "ambient_light": "ff808080"},
                "lights": [{"position": {"x": 11.5, "y": -1.25}, "range": 3, "intensity": .8, "color": "80ff0000", "shadows": True}], "image": encoded}

    def raw(self, document=None):
        return json.dumps(document if document is not None else self.document()).encode()

    def imported(self, raw=None, **options):
        return uvtt.import_map(self.campaign.pk, self.gm.pk, raw or self.raw(), name="Imported room", request_id=str(uuid.uuid4()), **options)

    def pixels(self, response):
        with Image.open(BytesIO(base64.b64decode(response["document"]["image"]))) as image:
            return image.convert("RGBA")

    def test_import_native_grid_origin_portal_cut_and_argb_lights_without_editable_source(self):
        result = self.imported()
        scene = Scene.objects.get(pk=result["scene"]["id"])
        self.assertFalse(result["builderEditable"])
        self.assertFalse(MapBuilderProject.objects.exists())
        self.assertEqual(scene.visibility, "gm")
        self.assertEqual((scene.width, scene.height), (128, 128))
        self.assertEqual((scene.settings["gridSize"], scene.settings["gridOffsetX"], scene.settings["gridOffsetY"]), (32, 16, 8))
        self.assertEqual(sorted((row.data["x1"], row.data["x2"]) for row in scene.elements.filter(kind="walls", data__kind="wall")), [(0, 32), (64, 128)])
        door = scene.elements.get(kind="walls", data__kind="door").data
        self.assertEqual((door["x1"], door["x2"], door["door_state"]), (32, 64, "open"))
        light = scene.elements.get(kind="lights").data
        self.assertEqual((light["x"], light["y"], light["dim_radius"], light["color"]), (32, 32, 3, "#ff0000"))
        self.assertAlmostEqual(light["intensity"], .8 * 128 / 255)
        self.assertTrue(scene.tiles.exists())

    def test_receipt_retry_reuses_scene_and_changed_request_payload_is_rejected(self):
        request_id, raw = str(uuid.uuid4()), self.raw()
        result = uvtt.import_map(self.campaign.pk, self.gm.pk, raw, name="First", request_id=request_id)
        files = self.files()
        with patch.object(uvtt, "parse", side_effect=AssertionError("Retry must not decode")):
            self.assertEqual(uvtt.import_map(self.campaign.pk, self.gm.pk, raw, name="First", request_id=request_id), result)
        self.assertEqual(self.files(), files)
        self.assertEqual(Scene.objects.count(), 1)
        with self.assertRaises(services.MapError) as error:
            uvtt.import_map(self.campaign.pk, self.gm.pk, raw, name="Changed", request_id=request_id)
        self.assertEqual(error.exception.code, "conflict")

    def test_gm_authority_foreign_folder_and_cross_campaign_scene_are_enforced(self):
        for user in (self.player, self.streamer):
            with self.subTest(user=user.pk), patch.object(uvtt, "parse") as parser, self.assertRaises((services.MapError, JournalError)):
                uvtt.import_map(self.campaign.pk, user.pk, self.raw(), name="Denied", request_id=str(uuid.uuid4()))
            parser.assert_not_called()
        with self.assertRaises(services.MapError):
            self.imported(folder_id=str(self.foreign_folder.pk))
        scene_id = self.imported()["scene"]["id"]
        for campaign, user in ((self.campaign, self.player), (self.campaign, self.streamer), (self.other, self.gm)):
            with self.subTest(user=user.pk, campaign=campaign.pk), self.assertRaises((services.MapError, JournalError)):
                uvtt.export_map(campaign.pk, user.pk, scene_id)

    def test_invalid_json_types_geometry_and_complexity_fail_before_image_decode(self):
        bad = []
        for version in (True, .4, "0.2"):
            doc = self.document(); doc["format"] = version; bad.append(self.raw(doc))
        doc = self.document(); doc["resolution"]["pixels_per_grid"] = True; bad.append(self.raw(doc))
        doc = self.document(); doc["portals"][0]["closed"] = "false"; bad.append(self.raw(doc))
        doc = self.document(); doc["lights"][0]["color"] = "#wrong"; bad.append(self.raw(doc))
        doc = self.document(); doc["resolution"]["map_origin"]["x"] = 10 ** 500; bad.append(self.raw(doc))
        doc = self.document(); doc["line_of_sight"] = [[{"x": 0, "y": 0}]]; bad.append(self.raw(doc))
        doc = self.document(); doc["line_of_sight"] = [[{"x": 0, "y": 0}, {"x": 1, "y": 0}]] * 5001; bad.append(self.raw(doc))
        bad.extend((b'{"format":0.2,"format":0.2}', b'{"format":NaN}', b'[' * 1100 + b']' * 1100))
        for raw in bad:
            with self.subTest(raw=raw[:50]), patch.object(uvtt, "_image") as decoder, self.assertRaises(services.MapError):
                uvtt.parse(raw)
            decoder.assert_not_called()
        self.assertFalse(Scene.objects.exists())

    def test_embedded_image_format_resolution_base64_and_pixel_headers_are_bounded(self):
        for encoded in ("../private.png", "data:image/png;base64,xxx", "?" * 30):
            doc = self.document(); doc["image"] = encoded
            with self.subTest(encoded=encoded), self.assertRaises(services.MapError): uvtt.parse(self.raw(doc))
        doc = self.document(); doc["resolution"]["map_size"]["x"] = 3
        with self.assertRaisesRegex(services.MapError, "does not match"): uvtt.parse(self.raw(doc))
        data = bytearray(base64.b64decode(self.document()["image"])); data[16:24] = struct.pack(">II", 5000, 5000)
        data[29:33] = struct.pack(">I", zlib.crc32(data[12:29]))
        doc = self.document(); doc["image"] = base64.b64encode(data).decode()
        with self.assertRaisesRegex(services.MapError, "pixel limit"): uvtt.parse(self.raw(doc))
        with override_settings(GRAVEWRIGHT_MAP_MAX_PIXELS=100), patch.object(uvtt, "_image") as decoder, self.assertRaises(services.MapError): uvtt.parse(self.raw())
        decoder.assert_not_called()

    def test_failure_after_tile_storage_rolls_back_scene_receipt_and_owned_files(self):
        before = self.files()
        with patch.object(SceneObject.objects, "bulk_create", side_effect=OSError("Synthetic storage failure")), self.assertRaises(OSError):
            self.imported()
        self.assertFalse(Scene.objects.exists())
        self.assertFalse(Tile.objects.exists())
        self.assertFalse(Receipt.objects.exists())
        self.assertEqual(self.files(), before)

    def test_baked_color_shadows_and_zero_range_produce_explicit_warnings(self):
        doc = self.document(); doc["environment"].update(baked_lighting=True, ambient_light="ff102030")
        doc["lights"][0].update(shadows=False, range=0)
        result = self.imported(self.raw(doc), activate=True)
        scene = Scene.objects.get(pk=result["scene"]["id"])
        self.assertEqual(Broadcast.objects.get(campaign=self.campaign).scene, scene)
        self.assertEqual(scene.visibility, "players")
        self.assertFalse(scene.elements.get(kind="lights").data["enabled"])
        for snippet in ("baked", "ambient", "shadow", "Zero-range"):
            self.assertTrue(any(snippet in note for note in result["warnings"]), snippet)

    def test_export_roundtrip_keeps_current_portal_grid_pixels_and_light_color(self):
        scene = Scene.objects.get(pk=self.imported()["scene"]["id"])
        exported = uvtt.export_map(self.campaign.pk, self.gm.pk, scene.pk)
        self.assertEqual(exported["document"]["format"], .2)
        self.assertEqual(exported["document"]["resolution"]["map_origin"], {"x": -.5, "y": -.25})
        self.assertFalse(exported["document"]["portals"][0]["closed"])
        self.assertEqual(exported["document"]["lights"][0]["color"], "ffff0000")
        with self.pixels(exported) as image: self.assertEqual(image.getpixel((60, 60)), (17, 34, 51, 255))
        copied = Scene.objects.get(pk=self.imported(self.raw(exported["document"]))["scene"]["id"])
        self.assertEqual(copied.settings["gridOffsetX"], 16)
        self.assertEqual(copied.elements.get(kind="lights").data["x"], 32)
        self.assertEqual(copied.elements.get(data__kind="door").data["door_state"], "open")

    def test_external_light_scales_are_clamped_with_warnings_and_invalid_numbers_rejected(self):
        document = self.document(); document["lights"][0].update(range=250, intensity=10, color="ffffffff")
        result = self.imported(self.raw(document))
        light = Scene.objects.get(pk=result["scene"]["id"]).elements.get(kind="lights").data
        self.assertEqual((light["dim_radius"], light["intensity"]), (200, 1))
        self.assertTrue(any("ranges above 200" in note for note in result["warnings"]))
        self.assertTrue(any("intensities above 1" in note for note in result["warnings"]))
        for key, value in (("range", -1), ("intensity", -1), ("range", float("inf")), ("intensity", True), ("range", 1_000_001)):
            document["lights"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(services.MapError): uvtt.parse(self.raw(document))
            document["lights"][0][key] = 1

    def test_export_uses_native_images_current_door_state_and_omits_hidden_artwork(self):
        scene = Scene.objects.get(pk=self.imported()["scene"]["id"])
        blue = self.asset("blue.png", "#2050d0")
        private = self.asset("private.png", "#ff00ff")
        for asset, layer in ((blue, "map"), (private, "gm-image-layer")):
            data = extra_objects.image(scene, {"asset_id": str(asset.pk), "x": 64, "y": 64, "scale": 2, "layer": layer})
            SceneObject.objects.create(scene=scene, kind="images", data=data)
        door = scene.elements.get(data__kind="door")
        door.data.update(door_state="locked", asset_id=str(self.door.pk), thickness=10)
        door.save()
        exported = uvtt.export_map(self.campaign.pk, self.gm.pk, scene.pk)
        with self.pixels(exported) as image: self.assertEqual(image.getpixel((64, 64))[:3], (32, 80, 208))
        self.assertTrue(exported["document"]["portals"][0]["closed"])
        self.assertTrue(any("Hidden GM" in note for note in exported["warnings"]))
        self.assertTrue(any("locks" in note for note in exported["warnings"]))
        self.assertNotIn(str(private.pk), json.dumps(exported))

    def test_export_open_door_art_rotates_around_each_authored_pivot_and_closes_in_place(self):
        scene = Scene.objects.get(pk=self.imported()["scene"]["id"])
        door = scene.elements.get(data__kind="door")
        for anchor, probe in (("start", (32, 48)), ("center", (48, 24)), ("end", (64, 16))):
            with self.subTest(anchor=anchor):
                door.data = objects.wall({"kind": "door", "door_state": "open", "rotationAnchor": anchor,
                                          "asset_id": str(self.door.pk), "thickness": 8,
                                          "x1": 32, "y1": 32, "x2": 64, "y2": 32},
                                         campaign_id=self.campaign.pk)
                door.save(update_fields=["data"])
                exported = uvtt.export_map(self.campaign.pk, self.gm.pk, scene.pk)
                self.assertFalse(exported["document"]["portals"][0]["closed"])
                with self.pixels(exported) as image:
                    self.assertEqual(image.getpixel(probe)[:3], (32, 176, 32))
                    self.assertEqual(image.getpixel((40, 32))[:3], (17, 34, 51))
                door.data["door_state"] = "closed"
                door.save(update_fields=["data"])
                with self.pixels(uvtt.export_map(self.campaign.pk, self.gm.pk, scene.pk)) as image:
                    self.assertEqual(image.getpixel((40, 32))[:3], (32, 176, 32))
                    self.assertEqual(image.getpixel(probe)[:3], (17, 34, 51))

    def test_export_open_anchored_door_respects_hidden_appearance_and_discovery(self):
        scene = Scene.objects.get(pk=self.imported()["scene"]["id"])
        door = scene.elements.get(data__kind="door")
        raw = {"kind": "door", "door_state": "open", "rotationAnchor": "start",
               "asset_id": str(self.door.pk), "thickness": 8, "x1": 32, "y1": 32, "x2": 64, "y2": 32}
        hidden = default_blueprint()
        hidden["states"]["open"] = {"appearance": "hidden"}
        for patch_data, visible in (({"presentation": "secret"}, False), ({"presentation": "invisible"}, False),
                                    ({"presentation": "secret", "discovered": True}, True),
                                    ({"blueprint": hidden}, False)):
            with self.subTest(patch_data=patch_data):
                door.data = objects.wall({**raw, **patch_data}, campaign_id=self.campaign.pk)
                door.save(update_fields=["data"])
                with self.pixels(uvtt.export_map(self.campaign.pk, self.gm.pk, scene.pk)) as image:
                    self.assertEqual(image.getpixel((32, 48))[:3], (32, 176, 32) if visible else (17, 34, 51))

    def test_export_fitted_sprite_artwork_preserves_size_outside_native_editor_scale_limits(self):
        scene = Scene.objects.get(pk=self.imported()["scene"]["id"])
        for source_scale, size in ((.1, (2048, 2048)), (100, (1, 1))):
            with self.subTest(source_scale=source_scale, size=size):
                with Image.new("RGB", size, "#229955") as image, BytesIO() as content:
                    image.save(content, "PNG")
                    artwork = MapAsset(campaign=self.campaign, name="Fitted sprite", width=size[0], height=size[1])
                    artwork.file.save("fitted-sprite.png", ContentFile(content.getvalue()), save=False)
                    artwork.save()
                data = extra_objects.image(scene, {"asset_id": str(self.floor.pk), "x": 64, "y": 64, "scale": source_scale})
                row = SceneObject(scene=scene, kind="images", data=data)
                self.assertTrue(change_sprite(scene, row, {"appearance": "asset", "assetId": str(artwork.pk)}))
                row.data = extra_objects.image(scene, {}, row.data)
                row.save()
                validate_campaign_sprites(self.campaign)
                self.assertFalse(.001 <= row.data["scale"] <= 100)
                self.assertAlmostEqual(row.data["natural_width"] * row.data["scale"], self.floor.width * source_scale)
                before = deepcopy(row.data)
                with self.pixels(uvtt.export_map(self.campaign.pk, self.gm.pk, scene.pk)) as image:
                    self.assertEqual(image.getpixel((64, 64))[:3], (34, 153, 85))
                    self.assertEqual(image.size, (128, 128))
                    if source_scale == .1:
                        self.assertEqual(image.getpixel((62, 64))[:3], (17, 34, 51))
                row.refresh_from_db()
                self.assertEqual(row.data, before)
                row.delete()

    def test_dynamic_floor_material_mask_and_eraser_flatten_without_stale_baked_pixels(self):
        self.doc["floors"][0]["dynamic"] = True
        erased = deepcopy(self.doc["floors"][0]); erased.update(id=str(uuid.uuid4()), assetId=None, dynamic=False,
                                                                x=5, y=5, width=1, height=1, brush=brush("erase", alpha=1, hardness=1))
        self.doc["floors"].append(erased)
        self.assertEqual(self.save().status_code, 200)
        self.assertEqual(self.generate().status_code, 200)
        scene = Scene.objects.get(campaign=self.campaign)
        floor = scene.elements.get(kind="images", data__surface__kind="floor")
        blue = self.asset("blue.png", "#2050d0")
        builder_dynamic.set_appearance(scene, floor, str(blue.pk)); floor.save()
        exported = uvtt.export_map(self.campaign.pk, self.gm.pk, scene.pk)
        with self.pixels(exported) as image:
            self.assertEqual(image.getpixel((128, 128))[:3], (32, 80, 208))
            self.assertEqual(image.getpixel((352, 352))[:3], (17, 34, 51))
        builder_dynamic.set_visibility(scene, floor, False); floor.save()
        hidden = uvtt.export_map(self.campaign.pk, self.gm.pk, scene.pk)
        with self.pixels(hidden) as image: self.assertEqual(image.getpixel((128, 128))[:3], (17, 34, 51))

    def test_export_is_read_only_reports_unsupported_content_and_rejects_incomplete_tiles(self):
        scene = Scene.objects.get(pk=self.imported()["scene"]["id"])
        SceneObject.objects.create(scene=scene, kind="particles", data={"name": "Authored effect"})
        source = SceneObject.objects.create(scene=scene, kind="images", data=extra_objects.image(scene, {"asset_id": str(self.floor.pk), "layer": "map"}))
        source.data["blueprint"] = {"graphs": {"signal:private": {"nodes": [{"text": "Private content"}]}}}; source.save()
        scene.environment.fog = {"enabled": True}; scene.environment.save()
        before = (self.files(), list(Scene.objects.values()), list(SceneObject.objects.values()), Receipt.objects.count())
        exported = uvtt.export_map(self.campaign.pk, self.gm.pk, scene.pk)
        self.assertTrue(any("behaviors" in note for note in exported["warnings"]))
        self.assertTrue(any("particles" in note for note in exported["warnings"]))
        self.assertTrue(any("fog" in note for note in exported["warnings"]))
        self.assertNotIn("Private content", json.dumps(exported))
        self.assertEqual((self.files(), list(Scene.objects.values()), list(SceneObject.objects.values()), Receipt.objects.count()), before)
        scene.tiles.all().delete()
        with self.assertRaisesRegex(services.MapError, "incomplete"): uvtt.export_map(self.campaign.pk, self.gm.pk, scene.pk)

    def test_export_composition_budget_is_enforced_before_excessive_raster_work(self):
        scene = Scene.objects.get(pk=self.imported()["scene"]["id"])
        with override_settings(GRAVEWRIGHT_MAP_PILLOW_MAX_PIXELS=100), patch.object(uvtt.Image, "new") as allocate, self.assertRaises(services.MapError):
            uvtt.export_map(self.campaign.pk, self.gm.pk, scene.pk)
        allocate.assert_not_called()
        data = extra_objects.image(scene, {"asset_id": str(self.floor.pk), "x": 64, "y": 64, "scale": 8})
        SceneObject.objects.create(scene=scene, kind="images", data=data)
        with patch.object(uvtt, "MAX_WORK_PIXELS", 20_000), self.assertRaisesRegex(services.MapError, "composition limit"):
            uvtt.export_map(self.campaign.pk, self.gm.pk, scene.pk)

    def test_dynamic_wall_material_uses_its_generated_mask_without_changing_barriers(self):
        self.doc["walls"][0]["dynamic"] = True
        self.assertEqual(self.save().status_code, 200)
        self.assertEqual(self.generate().status_code, 200)
        scene = Scene.objects.get(campaign=self.campaign)
        wall = scene.elements.get(kind="images", data__surface__kind="wall")
        blue = self.asset("blue.png", "#2050d0")
        barriers = list(scene.elements.filter(kind="walls").values())
        builder_dynamic.set_appearance(scene, wall, str(blue.pk)); wall.save()
        exported = uvtt.export_map(self.campaign.pk, self.gm.pk, scene.pk)
        with self.pixels(exported) as image:
            self.assertEqual(image.getpixel((128, 192))[:3], (32, 80, 208))
            self.assertEqual(image.getpixel((128, 160))[:3], (176, 32, 32))
        self.assertEqual(list(scene.elements.filter(kind="walls").values()), barriers)

    def test_http_multipart_import_and_json_export_use_the_service_contract(self):
        url = f"/api/containers/{self.campaign.pk}/universal-vtt/import"
        response = self.client.post(url, {"file": SimpleUploadedFile("room.dd2vtt", self.raw(), content_type="application/json"),
                                          "name": "HTTP room", "request_id": str(uuid.uuid4()), "folderId": str(self.folder.pk)})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(response.json()["builderEditable"])
        scene = Scene.objects.get(pk=response.json()["scene"]["id"])
        self.assertEqual(scene.folder, self.folder)
        exported = self.client.get(f"/api/maps/{scene.pk}/universal-vtt")
        self.assertEqual(exported.status_code, 200, exported.content[:100])
        self.assertEqual(exported.json()["document"]["format"], .2)
        self.assertEqual(exported.json()["filename"], "HTTP room.uvtt")

    def test_http_anonymous_and_players_cannot_import_or_export(self):
        scene = Scene.objects.get(pk=self.imported()["scene"]["id"])
        scene.visibility = "players"; scene.save()
        Broadcast.objects.create(campaign=self.campaign, scene=scene)
        for user in (self.player, None):
            if user: self.client.force_login(user)
            else: self.client.logout()
            response = self.client.post(f"/api/containers/{self.campaign.pk}/universal-vtt/import", {})
            self.assertIn(response.status_code, (403, 404))
            response = self.client.get(f"/api/maps/{scene.pk}/universal-vtt")
            self.assertIn(response.status_code, (403, 404))


class UniversalVttCompatibilityTests(SimpleTestCase):
    """Synthetic interchange geometry requires no campaign or persisted files."""

    document = UniversalVttTests.document
    raw = UniversalVttTests.raw

    def parsed(self, document):
        result = uvtt.parse(self.raw(document))
        self.addCleanup(result["image"].close)
        return result

    def test_version_three_and_integral_decimal_grid_keep_origin_phase_and_safe_source(self):
        document = self.document()
        document.update(format=.3, software=" Dungeondraft ", creator="Synthetic fixture", private={"secret": "Never copy"})
        document["resolution"]["pixels_per_grid"] = 32.0
        parsed = self.parsed(document)
        self.assertEqual(parsed["cell"], 32)
        self.assertIs(type(parsed["cell"]), int)
        self.assertEqual(parsed["grid"], {"size": 32, "offsetX": 16, "offsetY": 8})
        self.assertEqual(parsed["source"], {"format": .3, "coordinateSystem": "pixels",
                                            "software": "Dungeondraft", "creator": "Synthetic fixture"})
        self.assertEqual(parsed["origin"], {"x": 10.5, "y": -2.25})
        self.assertEqual((parsed["width"], parsed["height"]), (128, 128))

    def test_source_ignores_nested_oversized_and_control_character_extensions(self):
        for software, creator in (({"name": "Untrusted"}, "x" * 201), ("Producer\nextra", ["Not a label"])):
            with self.subTest(software=software):
                document = self.document()
                document.update(software=software, creator=creator)
                self.assertEqual(self.parsed(document)["source"], {"format": .2, "coordinateSystem": "pixels"})

    def test_rounded_portal_coordinates_cut_wall_and_preserve_door_bounds(self):
        document = self.document()
        document["portals"][0]["bounds"][0]["y"] += .0005
        document["portals"][0]["bounds"][1]["y"] -= .0005
        parsed = self.parsed(document)
        walls = [data for kind, data in parsed["rows"] if kind == "walls" and data["kind"] == "wall"]
        self.assertEqual([(wall["x1"], wall["x2"]) for wall in walls], [(0, 32), (64, 128)])
        door = next(data for kind, data in parsed["rows"] if kind == "walls" and data["kind"] == "door")
        self.assertAlmostEqual(door["y1"], .016)
        self.assertAlmostEqual(door["y2"], -.016)

    def test_nearby_parallel_portal_does_not_cut_unrelated_wall(self):
        document = self.document()
        for point in document["portals"][0]["bounds"]:
            point["y"] += .01
        parsed = self.parsed(document)
        walls = [data for kind, data in parsed["rows"] if kind == "walls" and data["kind"] == "wall"]
        self.assertEqual([(wall["x1"], wall["x2"]) for wall in walls], [(0, 128)])

    def test_overlapping_reversed_diagonal_portals_cut_both_wall_sources_once(self):
        document = self.document()
        origin = document["resolution"]["map_origin"]

        def point(value):
            return {"x": origin["x"] + value, "y": origin["y"] + value}

        document["line_of_sight"] = [[point(0), point(2), point(4)]]
        document["objects_line_of_sight"] = [[point(4), point(0)]]
        document["portals"] = [{"bounds": [point(3), point(1)], "closed": True},
                               {"bounds": [point(2), point(3.5)], "closed": False}]
        parsed = self.parsed(document)
        walls = [data for kind, data in parsed["rows"] if kind == "walls" and data["kind"] == "wall"]
        self.assertEqual(len(walls), 4)
        for wall in walls:
            self.assertAlmostEqual(wall["x1"], wall["y1"])
            self.assertAlmostEqual(wall["x2"], wall["y2"])
            self.assertFalse(32 < (wall["x1"] + wall["x2"]) / 2 < 112)
        doors = [data for kind, data in parsed["rows"] if kind == "walls" and data["kind"] == "door"]
        self.assertEqual(len(doors), 2)
        self.assertEqual([door["door_state"] for door in doors], ["closed", "open"])

    def test_expanding_portal_cuts_are_bounded_before_image_decode(self):
        document = self.document()
        origin = document["resolution"]["map_origin"]

        def point(x, y=0):
            return {"x": origin["x"] + x, "y": origin["y"] + y}

        document["line_of_sight"] = [[point(0), point(4)], [point(0, 1), point(4, 1)]]
        document["lights"] = []
        document["portals"] = [{"bounds": [point(start), point(start + .5)], "closed": False}
                               for start in (.5, 1.5, 2.5)]
        with patch.object(uvtt, "MAX_OBJECTS", 5), patch.object(uvtt, "_image") as decoder:
            with self.assertRaisesRegex(services.MapError, "complexity limit"):
                uvtt.parse(self.raw(document))
            decoder.assert_not_called()

    def test_unknown_versions_and_fractional_grid_fail_before_image_decode(self):
        for key, value in (("format", .1), ("format", .31), ("format", "0.3"), ("pixels_per_grid", 32.5)):
            document = self.document()
            if key == "format":
                document[key] = value
            else:
                document["resolution"][key] = value
            with self.subTest(key=key, value=value), patch.object(uvtt, "_image") as decoder:
                with self.assertRaises(services.MapError):
                    uvtt.parse(self.raw(document))
                decoder.assert_not_called()
