"""Continuous floor coverage round-trips and rasterizes with bounded masks."""

from copy import deepcopy
import math
from unittest.mock import patch
import uuid

from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image, ImageDraw

from gravewright.maps import builder_render, builder_services, services
from gravewright.maps.models import MapBuilderProject, Scene

from . import test_builder_projects as fixtures
from . import test_builder_render_expansion as raster_fixtures


RECTANGLE = [[0, 0], [1, 0], [1, 1], [0, 1]]


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
                   ALLOWED_HOSTS=["testserver"], GRAVEWRIGHT_MAP_TILER="pillow")
class BuilderFreePaintTests(TestCase):
    asset = fixtures.BuilderProjectTests.asset
    post = fixtures.BuilderProjectTests.post
    save = fixtures.BuilderProjectTests.save
    generate = fixtures.BuilderProjectTests.generate
    files = fixtures.BuilderProjectTests.files

    def setUp(self):
        fixtures.BuilderProjectTests.setUp(self)
        self.legacy = deepcopy(self.doc)
        self.doc["schemaVersion"] = 3
        self.layer = str(uuid.uuid4())
        self.doc["layers"] = [{"id": self.layer, "name": "Free paint", "visible": True, "locked": False}]
        for kind in ("floors", "walls", "doors"):
            for row in self.doc[kind]:
                row["layerId"] = self.layer
        self.doc["floors"][0]["rotation"] = 0
        self.doc["decorations"] = []
        self.doc["lights"] = []

    def vector(self):
        self.doc["floors"][0]["shape"] = {"contours": [deepcopy(RECTANGLE)], "cuts": []}
        return self.doc["floors"][0]

    def clean(self, document=None):
        return builder_services.clean_document(document or self.doc, self.membership)

    def test_fractional_subcell_floor_and_cut_roundtrip_generate_and_update(self):
        floor = self.vector()
        floor.update(x=1.237, y=1.352, width=.021, height=.034, rotation=90)
        floor["shape"]["cuts"] = [[[.25, .25], [.75, .25], [.75, .75], [.25, .75]]]
        source = deepcopy(self.doc)
        saved = self.save()
        self.assertEqual(saved.status_code, 200, saved.content)
        self.assertEqual(saved.json()["project"]["document"], source)
        self.assertEqual(self.client.get(self.url).json()["project"]["document"], source)
        generated = self.generate()
        self.assertEqual(generated.status_code, 200, generated.content)
        scene = Scene.objects.get()
        native_ids = set(scene.elements.values_list("pk", flat=True))
        changed = deepcopy(source)
        changed["floors"][0].update(x=2.123, width=.043)
        saved = self.save(expected_version=1, document=changed)
        self.assertEqual(saved.status_code, 200, saved.content)
        payload = {"request_id": str(uuid.uuid4()), "expected_version": 2, "expected_scene_version": scene.version}
        updated = self.post(self.url + "/update", payload)
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(set(scene.elements.values_list("pk", flat=True)), native_ids)
        self.assertEqual(self.client.get(self.url).json()["project"]["document"], changed)
        self.assertEqual(MapBuilderProject.objects.get(pk=self.project_id).document, changed)

    def test_schema_three_without_shapes_preserves_legacy_rows_and_minimum_size(self):
        self.assertEqual(self.clean(), self.doc)
        self.assertNotIn("shape", self.clean()["floors"][0])
        self.doc["floors"][0]["width"] = .049
        with self.assertRaises(services.MapError):
            self.clean()
        self.vector()["width"] = .001
        self.assertEqual(self.clean()["floors"][0]["width"], .001)
        self.doc["floors"][0]["width"] = .00099
        with self.assertRaises(services.MapError):
            self.clean()

    def test_legacy_schema_versions_reject_vector_fields(self):
        for version in (1, 2):
            document = deepcopy(self.legacy)
            document["schemaVersion"] = version
            document["doors"] = []
            document["floors"][0]["shape"] = {"contours": [RECTANGLE], "cuts": []}
            with self.subTest(version=version), self.assertRaisesRegex(services.MapError, "Invalid floor fields"):
                self.clean(document)

    def test_shape_validation_rejects_invalid_coordinates_types_and_degenerate_rings(self):
        invalid = [None, [], {}, {"contours": [RECTANGLE]}, {"contours": [], "cuts": []},
                   {"contours": [RECTANGLE], "cuts": None}, {"contours": [RECTANGLE], "cuts": [], "extra": 1},
                   {"contours": [[[0, 0], [1, 1]]], "cuts": []},
                   {"contours": [[[0, 0], [.5, .5], [1, 1]]], "cuts": []}]
        for value in (True, False, "0", None, -.00001, 1.00001, 10 ** 400):
            ring = deepcopy(RECTANGLE); ring[0][0] = value
            invalid.append({"contours": [ring], "cuts": []})
        for point in ([0], [0, 0, 1], "0,0", {"x": 0, "y": 0}):
            ring = deepcopy(RECTANGLE); ring[0] = point
            invalid.append({"contours": [ring], "cuts": []})
        original = deepcopy(self.doc)
        for shape in invalid:
            document = deepcopy(original); document["floors"][0]["shape"] = shape
            with self.subTest(shape=shape), self.assertRaisesRegex(services.MapError, "Invalid floor shape"):
                self.clean(document)
        for value in (float("nan"), float("inf"), -float("inf")):
            document = deepcopy(original)
            ring = deepcopy(RECTANGLE); ring[0][0] = value
            document["floors"][0]["shape"] = {"contours": [ring], "cuts": []}
            with self.assertRaisesRegex(services.MapError, "Invalid map project document"):
                self.clean(document)
        self.assertEqual(self.doc, original)

    def test_even_odd_self_intersections_and_independent_rings_are_valid(self):
        floor = self.vector()
        floor["shape"] = {"contours": [[[0, 0], [1, 1], [0, 1], [1, 0]], RECTANGLE * 2], "cuts": [RECTANGLE]}
        before = deepcopy(self.doc)
        cleaned = self.clean()
        self.assertEqual(cleaned, before)
        cleaned["floors"][0]["shape"]["contours"][0][0][0] = .5
        self.assertEqual(self.doc, before)

    def test_combined_ring_and_per_ring_point_limits(self):
        floor = self.vector(); floor.update(width=.05, height=.05)
        triangle = [[0, 0], [1, 0], [0, 1]]
        floor["shape"] = {"contours": [triangle], "cuts": [triangle] * 127}
        self.assertEqual(len(self.clean()["floors"][0]["shape"]["cuts"]), 127)
        floor["shape"]["cuts"].append(triangle)
        with self.assertRaisesRegex(services.MapError, "floor shapes are too complex"):
            self.clean()
        floor["shape"] = {"contours": [RECTANGLE * 64], "cuts": []}
        self.assertEqual(len(self.clean()["floors"][0]["shape"]["contours"][0]), 256)
        floor["shape"]["contours"][0].append([0, 0])
        with self.assertRaisesRegex(services.MapError, "too many floor shape points"):
            self.clean()

    def test_per_floor_and_document_point_limits_include_excluded_cuts(self):
        floor = self.vector(); floor.update(width=.05, height=.05)
        ring = RECTANGLE * 64
        floor["shape"] = {"contours": [ring] * 8, "cuts": [ring] * 8}
        self.assertEqual(sum(len(ring) for rings in self.clean()["floors"][0]["shape"].values() for ring in rings), 4096)
        floor["shape"]["cuts"].append(ring)
        with self.assertRaisesRegex(services.MapError, "too many floor shape points"):
            self.clean()
        floor["shape"]["cuts"].pop()
        self.doc["floors"] = [{**deepcopy(floor), "id": str(uuid.uuid4())} for _ in range(4)]
        self.assertEqual(len(self.clean()["floors"]), 4)
        self.doc["floors"].append({**deepcopy(floor), "id": str(uuid.uuid4())})
        with self.assertRaisesRegex(services.MapError, "too many floor shape points"):
            self.clean()

    def test_mask_edge_scanline_work_is_bounded_independently_of_document_size(self):
        self.doc.update(columns=4, rows=128, cellSize=128, walls=[], doors=[])
        floor = self.vector(); floor.update(x=0, y=0, width=4, height=128)
        ring = RECTANGLE * 64
        floor["shape"] = {"contours": [ring, ring], "cuts": []}
        self.assertEqual(len(self.clean()["floors"][0]["shape"]["contours"]), 2)
        floor["shape"]["cuts"].append(ring)
        with self.assertRaisesRegex(services.MapError, "floor shapes are too complex"):
            self.clean()

    def test_repeated_large_cut_masks_are_charged_against_paint_pixel_budget(self):
        self.doc.update(columns=200, rows=200, cellSize=16, walls=[], doors=[])
        floor = self.vector(); floor.update(x=0, y=0, width=200, height=200)
        floor["shape"] = {"contours": [RECTANGLE], "cuts": [RECTANGLE] * 5}
        with self.assertRaisesRegex(services.MapError, "too many overlapping painted surfaces"):
            self.clean()

    def test_shape_payload_is_still_subject_to_document_size_limit(self):
        floor = self.vector()
        floor["shape"]["contours"] = [[[0, 0]] * 200_000]
        with self.assertRaisesRegex(services.MapError, "map project is too large"):
            self.clean()


class BuilderFreePaintRasterTests(SimpleTestCase):
    setUp = raster_fixtures.BuilderExpandedRasterTests.setUp
    asset = raster_fixtures.BuilderExpandedRasterTests.asset
    render = raster_fixtures.BuilderExpandedRasterTests.render

    def floor(self, asset, **values):
        return {"id": str(uuid.uuid4()), "layerId": "base", "assetId": asset,
                "x": 0, "y": 0, "width": 4, "height": 2, "rotation": 0, **values}

    def test_normalized_contours_union_and_overlapping_cuts_exclude_without_cancelling(self):
        blue = self.asset(Image.new("RGB", (16, 16), "blue"), "floor")
        red = self.asset(Image.new("RGB", (16, 16), "red"), "floor")
        shape = {"contours": [[[0, 0], [.75, 0], [.75, 1], [0, 1]],
                               [[.25, 0], [1, 0], [1, 1], [.25, 1]]], "cuts": []}
        self.doc["floors"] = [self.floor(blue), self.floor(red, shape=shape)]
        raster = self.render()
        self.assertEqual(raster.getpixel((32, 16)), (255, 0, 0))
        shape["cuts"] = [[[.375, .25], [.625, .25], [.625, .75], [.375, .75]],
                         [[.5, .25], [.75, .25], [.75, .75], [.5, .75]]]
        raster = self.render()
        self.assertEqual(raster.getpixel((36, 16)), (0, 0, 255))
        self.assertEqual(raster.getpixel((8, 16)), (255, 0, 0))

    def test_even_odd_rings_cover_pentagram_arms_but_not_center_or_twice_wound_ring(self):
        red = self.asset(Image.new("RGB", (16, 16), "red"), "floor")
        vertices = [[.5 + .48 * math.cos(-math.pi / 2 + index * 2 * math.pi / 5),
                     .5 + .48 * math.sin(-math.pi / 2 + index * 2 * math.pi / 5)] for index in range(5)]
        star = [vertices[index] for index in (0, 2, 4, 1, 3)]
        self.doc["floors"] = [self.floor(red, shape={"contours": [star], "cuts": []})]
        raster = self.render()
        self.assertEqual(raster.getpixel((32, 16)), (17, 34, 51))
        self.assertEqual(raster.getpixel((32, 4)), (255, 0, 0))
        self.doc["floors"][0]["shape"]["contours"] = [RECTANGLE * 2]
        self.assertEqual(set(self.render().getdata()), {(17, 34, 51)})

    def test_fractional_bounds_and_cut_edges_use_continuous_pixel_center_coverage(self):
        red = self.asset(Image.new("RGB", (16, 16), "red"), "floor")
        self.doc["floors"] = [self.floor(red, x=.25, y=.25, width=.5, height=.5,
            shape={"contours": [RECTANGLE], "cuts": [[[.25, 0], [.75, 0], [.75, 1], [.25, 1]]]})]
        raster = self.render()
        for x, color in ((3, (17, 34, 51)), (4, (255, 0, 0)), (5, (255, 0, 0)),
                         (6, (17, 34, 51)), (9, (17, 34, 51)), (10, (255, 0, 0)), (12, (17, 34, 51))):
            self.assertEqual(raster.getpixel((x, 6)), color, x)

    def test_round_contour_is_antialiased_without_expanding_to_cells(self):
        red = self.asset(Image.new("RGB", (16, 16), "red"), "floor")
        circle = [[.5 + .5 * math.cos(index * math.tau / 64), .5 + .5 * math.sin(index * math.tau / 64)] for index in range(64)]
        self.doc["floors"] = [self.floor(red, x=.25, y=.25, width=1.5, height=1.5,
            shape={"contours": [circle], "cuts": []})]
        before = deepcopy(self.doc)
        raster = self.render()
        self.assertEqual(raster.getpixel((5, 5)), (17, 34, 51))
        self.assertEqual(raster.getpixel((16, 5)), (255, 0, 0))
        self.assertTrue(set(raster.getdata()) - {(255, 0, 0), (17, 34, 51)})
        self.assertEqual(self.doc, before)

    def test_mask_preserves_texture_world_phase_rotation_and_transparent_alpha(self):
        blue = self.asset(Image.new("RGB", (16, 16), "blue"), "floor")
        texture = Image.new("RGBA", (16, 16), (255, 0, 0, 0))
        ImageDraw.Draw(texture).rectangle((0, 0, 7, 15), fill=(255, 0, 0, 128))
        red = self.asset(texture, "floor")
        self.doc["floors"] = [self.floor(blue), self.floor(red, x=.25, y=.25, width=3.5, height=1.5,
            shape={"contours": [RECTANGLE], "cuts": []})]
        raster = self.render()
        self.assertEqual(raster.getpixel((5, 5)), (128, 0, 127))
        self.assertEqual(raster.getpixel((12, 5)), (0, 0, 255))
        self.assertEqual(raster.getpixel((21, 5)), (128, 0, 127))
        self.doc["floors"][1]["rotation"] = 90
        raster = self.render()
        self.assertEqual(raster.getpixel((5, 5)), (128, 0, 127))
        self.assertEqual(raster.getpixel((5, 12)), (0, 0, 255))

    def test_unmasked_legacy_floor_and_full_rectangle_shape_have_identical_png_bytes(self):
        red = self.asset(Image.new("RGB", (16, 16), "red"), "floor")
        self.doc["floors"] = [self.floor(red)]
        with patch("gravewright.maps.builder_render.MapAsset.objects.filter", return_value=self.assets):
            legacy = builder_render.render(self.doc, uuid.uuid4())
            self.addCleanup(legacy.close)
            self.doc["floors"][0]["shape"] = {"contours": [RECTANGLE], "cuts": []}
            vector = builder_render.render(self.doc, uuid.uuid4())
            self.addCleanup(vector.close)
        self.assertEqual(legacy.read(), vector.read())
