"""Terrain dabs persist once per gesture and erase the composed active layer."""

from copy import deepcopy
from unittest.mock import patch
import uuid

from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image, ImageDraw

from gravewright.maps import builder_render, builder_services, services
from gravewright.maps.models import MapBuilderProject, Scene
from gravewright.maps.terrain_brush import clean_floor_brush, terrain_brush_cost, terrain_brush_mask
from . import test_builder_free_paint as free_fixtures
from . import test_builder_projects as project_fixtures
from . import test_builder_wall_art as raster_fixtures


def brush(operation="paint", alpha=.5, hardness=.5, points=None, radius=None):
    return {"operation": operation, "points": points or [[.5, .5, alpha]],
            "radius": radius or [.5, .5], "hardness": hardness}


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow")
class BuilderTerrainBrushTests(TestCase):
    setUp = free_fixtures.BuilderFreePaintTests.setUp
    asset = project_fixtures.BuilderProjectTests.asset
    post = project_fixtures.BuilderProjectTests.post
    save = project_fixtures.BuilderProjectTests.save
    generate = project_fixtures.BuilderProjectTests.generate
    files = project_fixtures.BuilderProjectTests.files
    clean = free_fixtures.BuilderFreePaintTests.clean

    def test_brush_and_eraser_roundtrip_generate_update_retries_and_native_identity(self):
        self.doc["editingMode"] = "paint"
        floor = self.doc["floors"][0]
        floor["brush"] = brush(points=[[.25, .5, .3], [.5, .5, .3], [.5, .5, .3]])
        self.doc["floors"].append({**deepcopy(floor), "id": str(uuid.uuid4()), "assetId": None,
                                   "brush": brush("erase", alpha=.2)})
        before = deepcopy(self.doc)
        saved = self.save()
        self.assertEqual(saved.status_code, 200, saved.content)
        self.assertEqual(saved.json()["project"]["document"], before)
        self.assertEqual(self.client.get(self.url).json()["project"]["document"], before)
        generated = self.generate()
        self.assertEqual(generated.status_code, 200, generated.content)
        scene = Scene.objects.get()
        native_ids = set(scene.elements.values_list("pk", flat=True))
        changed = deepcopy(before)
        changed["floors"][0]["brush"]["points"].append([.75, .5, .3])
        self.assertEqual(self.save(document=changed, expected_version=1).status_code, 200)
        payload = {"request_id": str(uuid.uuid4()), "expected_version": 2, "expected_scene_version": scene.version}
        updated = self.post(self.url + "/update", payload)
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(self.post(self.url + "/update", payload).json(), updated.json())
        self.assertEqual(set(scene.elements.values_list("pk", flat=True)), native_ids)
        self.assertEqual(MapBuilderProject.objects.get(pk=self.project_id).document, changed)

    def test_brush_is_optional_schema_three_data_independent_of_mode_shape_and_legacy_style(self):
        self.assertEqual(self.clean(), self.doc)
        self.assertNotIn("brush", self.clean()["floors"][0])
        self.assertEqual(self.clean(self.legacy), self.legacy)
        floor = self.doc["floors"][0]
        floor.update(brush=brush(), paint={"color": None, "opacity": .4},
                     shape={"contours": [free_fixtures.RECTANGLE], "cuts": []})
        for mode in ("tiles", "paint"):
            self.doc["editingMode"] = mode
            self.assertEqual(self.clean(), self.doc)
        floor.update(width=.001, height=.001)
        self.assertEqual(self.clean(), self.doc)
        for version in (1, 2):
            document = deepcopy(self.legacy)
            document.update(schemaVersion=version, doors=[])
            document["floors"][0]["brush"] = brush()
            with self.assertRaisesRegex(services.MapError, "Invalid floor fields"):
                self.clean(document)

    def test_brush_types_keys_numbers_and_erase_asset_are_strict(self):
        invalid = [None, [], {}, {**brush(), "extra": True}, {key: value for key, value in brush().items() if key != "operation"}]
        invalid += [{**brush(), "operation": value} for value in (None, True, [], "Paint", "blend")]
        invalid += [{**brush(), "points": value} for value in (None, [], [[.5, .5]], [[True, .5, .5]], [[-.1, .5, .5]], [[.5, 1.1, .5]], [[.5, .5, "0.5"]])]
        invalid += [{**brush(), "radius": value} for value in (None, [], [1], [True, .5], [0, .5], [-.1, .5], [10001, .5], [10 ** 400, .5])]
        invalid += [{**brush(), "hardness": value} for value in (True, None, "0.5", -.01, 1.01, 10 ** 400)]
        for value in invalid:
            with self.subTest(value=value), self.assertRaisesRegex(services.MapError, "Invalid floor brush"):
                clean_floor_brush(value)
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.assertRaisesRegex(services.MapError, "Invalid floor brush"):
                clean_floor_brush({**brush(), "hardness": value})
        self.doc["floors"][0]["brush"] = brush("erase")
        with self.assertRaisesRegex(services.MapError, "Invalid floor brush"):
            self.clean()

    def test_dab_counts_and_clipped_work_limits_reject_before_mutating_the_source(self):
        with self.assertRaisesRegex(services.MapError, "too many terrain brush dabs"):
            clean_floor_brush(brush(points=[[.5, .5, 0]] * 2049))
        document = deepcopy(self.doc)
        document["floors"][0]["brush"] = brush(points=[[.5, .5, .5]] * 2048, radius=[10000, 10000])
        before = deepcopy(document)
        with self.assertRaisesRegex(services.MapError, "terrain brushes are too complex"):
            self.clean(document)
        self.assertEqual(document, before)
        original = document["floors"][0]
        document["floors"] = [{**deepcopy(original), "id": str(uuid.uuid4()), "brush": brush(points=[[.5, .5, 0]] * 2048)} for _ in range(5)]
        with self.assertRaisesRegex(services.MapError, "too many terrain brush dabs"):
            self.clean(document)

    def test_foreign_assets_remain_forbidden_and_deleted_art_retains_brush_geometry(self):
        floor = self.doc["floors"][0]
        floor["brush"] = brush()
        foreign = deepcopy(self.doc)
        foreign["assets"].append({"assetId": str(self.foreign_asset.pk), "role": "floor"})
        foreign["floors"][0]["assetId"] = str(self.foreign_asset.pk)
        with self.assertRaisesRegex(services.MapError, "missing or belongs to another campaign"):
            self.clean(foreign)
        self.assertEqual(self.save().status_code, 200)
        builder_services.detach_project_art(self.campaign.pk, str(self.floor.pk))
        saved = MapBuilderProject.objects.get(pk=self.project_id).document
        self.assertIsNone(saved["floors"][0]["assetId"])
        self.assertEqual(saved["floors"][0]["brush"], floor["brush"])
        self.assertEqual(self.clean(saved), saved)

    def test_archive_remaps_art_while_preserving_parametric_paint_and_erase(self):
        from gravewright.administration.archives import export_campaign, import_campaign
        self.doc["floors"][0]["brush"] = brush()
        self.doc["floors"].append({**deepcopy(self.doc["floors"][0]), "id": str(uuid.uuid4()), "assetId": None,
                                   "brush": brush("erase")})
        self.assertEqual(self.save().status_code, 200)
        campaign = import_campaign(export_campaign(self.campaign), self.gm, "Cloned terrain")
        project = MapBuilderProject.objects.get(campaign=campaign)
        self.assertEqual([floor["brush"] for floor in project.document["floors"]], [floor["brush"] for floor in self.doc["floors"]])
        self.assertNotEqual(project.document["floors"][0]["assetId"], self.doc["floors"][0]["assetId"])
        self.assertEqual(builder_services.clean_document(project.document, builder_services.authority(campaign.pk, self.gm.pk)), project.document)


class BuilderTerrainRasterTests(SimpleTestCase):
    setUp = raster_fixtures.BuilderWallArtworkTests.setUp
    asset = raster_fixtures.BuilderWallArtworkTests.asset
    render = raster_fixtures.BuilderWallArtworkTests.render

    def floor(self, **extra):
        return {"id": str(uuid.uuid4()), "layerId": "base", "assetId": None,
                "x": 1, "y": 1, "width": 4, "height": 4, "rotation": 0, **extra}

    def test_dab_pixel_centers_feather_and_repeated_hold_use_explicit_integer_source_over(self):
        row = self.floor(x=0, y=0, width=1, height=1,
            brush=brush(hardness=0, points=[[.53125, .53125, .5], [.53125, .53125, .5]]))
        with terrain_brush_mask(row, 16, 0, 0, (16, 16)) as mask:
            self.assertEqual(mask.getpixel((8, 8)), 192)
            self.assertEqual(mask.getpixel((12, 8)), 112, "two soft dabs cannot be replaced by one combined-intensity dab")
            self.assertEqual(mask.getpixel((0, 0)), 0)
        self.assertEqual(terrain_brush_cost(row, 16), (2, 512))

    def test_shape_holes_texture_alpha_and_legacy_opacity_multiply_the_brush_mask(self):
        red = self.asset(Image.new("RGBA", (16, 16), (255, 0, 0, 128)), "floor")
        self.doc["background"] = "#000000"
        self.doc["floors"] = [self.floor(assetId=red, brush=brush(hardness=1, radius=[1, 1]),
            paint={"color": None, "opacity": .5}, shape={"contours": [free_fixtures.RECTANGLE],
                "cuts": [[[0, 0], [.5, 0], [.5, .5], [0, .5]]]})]
        image = self.render()
        self.assertEqual(image.getpixel((64, 64)), (32, 0, 0))
        self.assertEqual(image.getpixel((24, 24)), (0, 0, 0))

    def test_destination_out_erases_composed_alpha_once_and_preserves_the_other_layer(self):
        self.doc["layers"].append({"id": "paint", "name": "Paint", "visible": True, "locked": False})
        base = self.floor(paint={"color": "#0000ff", "opacity": 1})
        red = self.floor(layerId="paint", paint={"color": "#ff0000", "opacity": .5})
        erase = self.floor(layerId="paint", brush=brush("erase", hardness=1, radius=[1, 1]))
        self.doc["floors"] = [base, red, {**deepcopy(red), "id": str(uuid.uuid4())}, erase]
        image = self.render()
        self.assertEqual(image.getpixel((48, 48)), (96, 0, 159), "75% layer alpha erased by50% leaves37.5%, not43.75%")
        self.assertEqual(self.doc["floors"][0], base)
        self.doc["floors"].append(self.floor(layerId="paint", paint={"color": "#00ff00", "opacity": 1}))
        self.assertEqual(self.render().getpixel((48, 48)), (0, 255, 0), "later paint is outside the earlier eraser")

    def test_opaque_brush_preserves_world_texture_phase_and_quarter_rotation(self):
        art = Image.new("RGB", (16, 16), "red")
        ImageDraw.Draw(art).rectangle((8, 0, 15, 15), fill="green")
        material = self.asset(art, "floor")
        row = self.floor(assetId=material, x=1.25, y=1.25, rotation=90)
        self.doc["floors"] = [row]
        original = self.render().tobytes()
        row["brush"] = brush(alpha=1, hardness=1, radius=[10000, 10000])
        self.assertEqual(self.render().tobytes(), original)

    def test_layer_surface_is_bounded_to_floor_extent_and_tiles_do_not_allocate_it(self):
        row = self.floor(paint={"color": "#ff0000", "opacity": 1})
        self.doc["floors"] = [row]
        with patch("gravewright.maps.builder_render.Image.new", wraps=Image.new) as create:
            self.render()
        self.assertNotIn(("RGBA", (192, 160)), [call.args[:2] for call in create.call_args_list])
        self.doc["floors"].append(self.floor(brush=brush("erase")))
        with patch("gravewright.maps.builder_render.Image.new", wraps=Image.new) as create:
            self.render()
        self.assertNotIn(("RGBA", (192, 160)), [call.args[:2] for call in create.call_args_list])
        self.assertIn(("RGBA", (64, 64)), [call.args[:2] for call in create.call_args_list])

    def test_tiny_positive_radius_is_safe_and_zero_intensity_remains_empty(self):
        for radius in ([5e-324, 5e-324], [.5, .5]):
            row = self.floor(width=.001, height=.001, brush=brush(alpha=0 if radius[0] == .5 else 1, radius=radius))
            with terrain_brush_mask(row, 16, 16, 16, (1, 1)) as mask:
                self.assertIsNone(mask.getbbox())
