"""Tiles and Painting metadata preserve authored geometry and composite alpha."""

from copy import deepcopy
from unittest.mock import patch
import uuid

from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image, ImageDraw

from gravewright.maps import builder_render, builder_services, services
from gravewright.maps.models import MapBuilderProject, Scene

from . import test_builder_free_paint as free_fixtures
from . import test_builder_projects as project_fixtures
from . import test_builder_render_expansion as raster_fixtures


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow")
class BuilderPaintModeTests(TestCase):
    setUp = free_fixtures.BuilderFreePaintTests.setUp
    asset = project_fixtures.BuilderProjectTests.asset
    post = project_fixtures.BuilderProjectTests.post
    save = project_fixtures.BuilderProjectTests.save
    generate = project_fixtures.BuilderProjectTests.generate
    files = project_fixtures.BuilderProjectTests.files
    clean = free_fixtures.BuilderFreePaintTests.clean

    def test_mode_color_opacity_and_shape_roundtrip_generate_update_and_retry(self):
        self.doc["editingMode"] = "paint"
        floor = self.doc["floors"][0]
        floor.update(assetId=None, paint={"color": "#7d3388", "opacity": .35},
                     shape={"contours": [free_fixtures.RECTANGLE], "cuts": []})
        saved = self.save()
        self.assertEqual(saved.status_code, 200, saved.content)
        self.assertEqual(saved.json()["project"]["document"], self.doc)
        self.assertEqual(self.client.get(self.url).json()["project"]["document"], self.doc)
        generated = self.generate()
        self.assertEqual(generated.status_code, 200, generated.content)
        scene = Scene.objects.get()
        native_ids = set(scene.elements.values_list("pk", flat=True))
        changed = deepcopy(self.doc)
        changed["editingMode"] = "tiles"
        changed["floors"][0]["paint"]["opacity"] = .65
        saved = self.save(expected_version=1, document=changed)
        self.assertEqual(saved.status_code, 200, saved.content)
        payload = {"request_id": str(uuid.uuid4()), "expected_version": 2, "expected_scene_version": scene.version}
        updated = self.post(self.url + "/update", payload)
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(self.post(self.url + "/update", payload).json(), updated.json())
        self.assertEqual(set(scene.elements.values_list("pk", flat=True)), native_ids)
        self.assertEqual(self.client.get(self.url).json()["project"]["document"], changed)

    def test_absent_mode_and_paint_remain_absent_without_reinterpreting_legacy_rows(self):
        self.assertEqual(self.clean(), self.doc)
        self.assertNotIn("editingMode", self.clean())
        self.assertNotIn("paint", self.clean()["floors"][0])
        self.assertEqual(self.clean(self.legacy), self.legacy)
        for mode in ("tiles", "paint"):
            document = deepcopy(self.doc); document["editingMode"] = mode
            self.assertEqual(self.clean(document)["floors"], self.doc["floors"])

    def test_paint_and_shape_are_independently_optional_and_not_restricted_by_editor_mode(self):
        floor = self.doc["floors"][0]
        floor["paint"] = {"color": None, "opacity": .4}
        self.assertEqual(self.clean(), self.doc)
        self.assertNotIn("shape", self.clean()["floors"][0])
        floor["shape"] = {"contours": [free_fixtures.RECTANGLE], "cuts": []}
        for mode in ("tiles", "paint"):
            self.doc["editingMode"] = mode
            self.assertEqual(self.clean(), self.doc)
        del floor["paint"]
        self.assertEqual(self.clean(), self.doc)

    def test_mode_validation_is_schema_three_only_and_strict(self):
        for mode in (None, True, False, 0, "", "painting", "Tiles", [], {}):
            document = deepcopy(self.doc); document["editingMode"] = mode
            with self.subTest(mode=mode), self.assertRaisesRegex(services.MapError, "Invalid map editing mode"):
                self.clean(document)
        for version in (1, 2):
            document = deepcopy(self.legacy)
            document.update(schemaVersion=version, editingMode="paint", doors=[])
            with self.subTest(version=version), self.assertRaisesRegex(services.MapError, "Invalid map editing mode"):
                self.clean(document)
            del document["editingMode"]
            document["floors"][0]["paint"] = {"color": None, "opacity": .5}
            with self.assertRaisesRegex(services.MapError, "Invalid floor fields"):
                self.clean(document)

    def test_paint_validation_rejects_unknown_keys_color_texture_ambiguity_and_bad_alpha(self):
        invalid = [None, [], {}, {"color": "#112233"}, {"opacity": .5},
                   {"color": None, "opacity": .5, "hardness": .5}, {"color": "#112233", "opacity": .5}]
        for opacity in (True, False, None, "0.5", -.00001, 1.00001, 10 ** 400):
            invalid.append({"color": None, "opacity": opacity})
        for style in invalid:
            document = deepcopy(self.doc); document["floors"][0]["paint"] = style
            with self.subTest(style=style), self.assertRaisesRegex(services.MapError, "Invalid floor paint"):
                self.clean(document)
        for color in (True, 123, "red", "#123", "#12345678", "#zzzzzz", "#123456\x00"):
            document = deepcopy(self.doc)
            document["floors"][0].update(assetId=None, paint={"color": color, "opacity": .5})
            with self.subTest(color=color), self.assertRaisesRegex(services.MapError, "Invalid floor paint"):
                self.clean(document)
        for opacity in (float("nan"), float("inf"), -float("inf")):
            document = deepcopy(self.doc); document["floors"][0]["paint"] = {"color": None, "opacity": opacity}
            with self.assertRaisesRegex(services.MapError, "Invalid map project document"):
                self.clean(document)

    def test_solid_color_normalizes_and_transparent_texture_keeps_campaign_ownership(self):
        floor = self.doc["floors"][0]
        floor.update(assetId=None, paint={"color": "#AAbbCC", "opacity": 0})
        self.assertEqual(self.clean()["floors"][0]["paint"], {"color": "#aabbcc", "opacity": 0})
        floor.update(assetId=str(self.foreign_asset.pk), paint={"color": None, "opacity": 1})
        self.doc["assets"].append({"assetId": str(self.foreign_asset.pk), "role": "floor"})
        with self.assertRaisesRegex(services.MapError, "missing or belongs to another campaign"):
            self.clean()

    def test_campaign_archive_preserves_mode_and_styles_while_remapping_texture_ids(self):
        from gravewright.administration.archives import export_campaign, import_campaign

        self.doc["editingMode"] = "paint"
        self.doc["floors"][0]["paint"] = {"color": None, "opacity": .25}
        self.doc["floors"].append({**deepcopy(self.doc["floors"][0]), "id": str(uuid.uuid4()), "assetId": None,
                                   "paint": {"color": "#13579b", "opacity": .75}})
        self.assertEqual(self.save().status_code, 200)
        clone = import_campaign(export_campaign(self.campaign), self.gm, "Cloned painting source")
        project = MapBuilderProject.objects.get(campaign=clone)
        self.assertEqual(project.document["editingMode"], "paint")
        self.assertEqual([row["paint"] for row in project.document["floors"]], [row["paint"] for row in self.doc["floors"]])
        self.assertNotEqual(project.document["floors"][0]["assetId"], self.doc["floors"][0]["assetId"])
        self.assertIsNone(project.document["floors"][1]["assetId"])
        self.assertEqual(builder_services.clean_document(project.document, builder_services.authority(clone.pk, self.gm.pk)), project.document)


class BuilderPaintModeRasterTests(SimpleTestCase):
    setUp = raster_fixtures.BuilderExpandedRasterTests.setUp
    asset = raster_fixtures.BuilderExpandedRasterTests.asset
    render = raster_fixtures.BuilderExpandedRasterTests.render
    floor = free_fixtures.BuilderFreePaintRasterTests.floor

    def test_solid_color_strokes_accumulate_opacity_over_lower_layers(self):
        blue = self.asset(Image.new("RGB", (16, 16), "blue"), "floor")
        painted = self.floor(None, paint={"color": "#ff0000", "opacity": .5})
        self.doc["floors"] = [self.floor(blue), painted]
        self.assertEqual(self.render().getpixel((20, 12)), (128, 0, 127))
        self.doc["floors"].append({**deepcopy(painted), "id": str(uuid.uuid4())})
        self.assertEqual(self.render().getpixel((20, 12)), (192, 0, 63))

    def test_opacity_applies_once_to_union_coverage_and_preserves_excluded_cuts(self):
        blue = self.asset(Image.new("RGB", (16, 16), "blue"), "floor")
        shape = {"contours": [free_fixtures.RECTANGLE, free_fixtures.RECTANGLE],
                 "cuts": [[[.25, .25], [.75, .25], [.75, .75], [.25, .75]]]}
        self.doc["floors"] = [self.floor(blue), self.floor(None, shape=shape, paint={"color": "#ff0000", "opacity": .5})]
        self.assertEqual(self.render().getpixel((8, 12)), (128, 0, 127))
        self.assertEqual(self.render().getpixel((32, 12)), (0, 0, 255))

    def test_texture_alpha_opacity_world_phase_and_rotation_are_composed_together(self):
        blue = self.asset(Image.new("RGB", (16, 16), "blue"), "floor")
        texture = Image.new("RGBA", (16, 16), (255, 0, 0, 0))
        ImageDraw.Draw(texture).rectangle((0, 0, 7, 15), fill=(255, 0, 0, 128))
        red = self.asset(texture, "floor")
        self.doc["floors"] = [self.floor(blue), self.floor(red, x=.25, y=.25, width=3.5, height=1.5,
            shape={"contours": [free_fixtures.RECTANGLE], "cuts": []}, paint={"color": None, "opacity": .5})]
        before = deepcopy(self.doc)
        raster = self.render()
        self.assertEqual(raster.getpixel((5, 5)), (64, 0, 191))
        self.assertEqual(raster.getpixel((21, 5)), (64, 0, 191))
        self.assertEqual(raster.getpixel((12, 5)), (0, 0, 255))
        self.assertEqual(raster.mode, "RGB")
        with raster.convert("RGBA") as rgba:
            self.assertEqual(rgba.getpixel((5, 5)), (64, 0, 191, 255))
            self.assertEqual(rgba.getpixel((12, 5)), (0, 0, 255, 255))
        self.assertEqual(self.doc, before)
        self.doc["floors"][1]["rotation"] = 90
        raster = self.render()
        self.assertEqual(raster.getpixel((5, 5)), (64, 0, 191))
        self.assertEqual(raster.getpixel((5, 12)), (0, 0, 255))

    def test_zero_opacity_hides_floor_and_mode_switch_does_not_change_rendered_pixels(self):
        self.doc["floors"] = [self.floor(None, paint={"color": "#ff0000", "opacity": 0})]
        self.assertEqual(set(self.render().getdata()), {(17, 34, 51)})
        self.doc["floors"][0]["paint"]["opacity"] = .5
        pixels = self.render().tobytes()
        for mode in ("tiles", "paint"):
            self.doc["editingMode"] = mode
            self.assertEqual(self.render().tobytes(), pixels)

    def test_absent_style_and_explicit_full_texture_opacity_keep_identical_legacy_png(self):
        red = self.asset(Image.new("RGB", (16, 16), "red"), "floor")
        self.doc["floors"] = [self.floor(red)]
        with patch("gravewright.maps.builder_render.MapAsset.objects.filter", return_value=self.assets):
            legacy = builder_render.render(self.doc, uuid.uuid4())
            self.addCleanup(legacy.close)
            self.doc["floors"][0]["paint"] = {"color": None, "opacity": 1}
            self.doc["editingMode"] = "paint"
            explicit = builder_render.render(self.doc, uuid.uuid4())
            self.addCleanup(explicit.close)
        self.assertEqual(legacy.read(), explicit.read())
