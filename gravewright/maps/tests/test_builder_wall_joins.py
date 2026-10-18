"""Derived wall networks keep source IDs, door gaps, phase and single alpha."""

from copy import deepcopy
from unittest.mock import patch

from django.test import SimpleTestCase
from PIL import Image, ImageColor, ImageDraw

from gravewright.maps import builder_render, builder_services
from gravewright.maps.wall_joins import wall_join_geometry
from . import test_builder_wall_art as fixtures


class BuilderWallJoinTests(SimpleTestCase):
    setUp = fixtures.BuilderWallArtworkTests.setUp
    asset = fixtures.BuilderWallArtworkTests.asset
    striped_wall = fixtures.BuilderWallArtworkTests.striped_wall
    wall = fixtures.BuilderWallArtworkTests.wall
    render = fixtures.BuilderWallArtworkTests.render

    def test_l_miter_fills_the_outer_corner_and_composites_transparent_art_once(self):
        art = self.asset(Image.new("RGBA", (16, 16), (255, 0, 0, 128)))
        self.wall(art, (2, 2, 6, 2))
        self.wall(art, (6, 2, 6, 6))
        image = self.render()
        for y in range(26, 38):
            for x in range(90, 102):
                self.assertEqual(image.getpixel((x, y)), (136, 17, 25), (x, y))

    def test_t_split_is_visual_only_and_the_center_has_no_gap_or_double_alpha(self):
        art = self.asset(Image.new("RGBA", (16, 16), (255, 0, 0, 128)))
        self.wall(art, (1, 4, 9, 4))
        self.wall(art, (5, 4, 5, 8))
        before = deepcopy(self.doc)
        native_before = list(builder_services.segments(self.doc))
        image = self.render()
        for y in range(58, 70):
            for x in range(74, 86):
                self.assertEqual(image.getpixel((x, y)), (136, 17, 25), (x, y))
        self.assertEqual(self.doc, before)
        self.assertEqual(list(builder_services.segments(self.doc)), native_before)
        self.assertEqual(len(self.doc["walls"]), 2)

    def test_reversed_adjacent_pieces_share_the_unsplit_wall_texture_phase(self):
        art = self.striped_wall()
        self.wall(art, (1, 3, 10, 3))
        original = self.render().copy()
        self.addCleanup(original.close)
        self.doc["walls"] = []
        self.wall(art, (1, 3, 4, 3))
        self.wall(art, (10, 3, 4, 3))
        split = self.render()
        self.assertEqual(split.tobytes(), original.tobytes())
        self.assertEqual(split.getpixel((76, 44)), ImageColor.getrgb("yellow"))

    def test_legacy_overlaps_and_reversed_duplicates_have_one_alpha_with_a_t_on_the_boundary(self):
        art = self.asset(Image.new("RGBA", (16, 16), (255, 0, 0, 128)))
        self.wall(art, (1, 4, 6, 4))
        self.wall(art, (10, 4, 4, 4))
        self.wall(art, (6, 4, 1, 4))
        self.wall(art, (6, 4, 6, 8))
        image = self.render()
        for point in ((70, 62), (90, 62), (100, 66), (100, 78), (146, 62)):
            self.assertEqual(image.getpixel(point), (136, 17, 25), point)

    def test_door_opening_stays_empty_even_when_another_wall_ends_at_its_edge(self):
        art = self.asset(Image.new("RGBA", (16, 16), "red"))
        self.wall(art, (1, 3, 11, 3))
        self.wall(art, (4.5, 3, 4.5, 6))
        self.doc["doors"] = [{"id": "door", "layerId": "base", "assetId": None,
            "x1": 2.5, "y1": 3, "x2": 4.5, "y2": 3, "thickness": 1, "state": "open"}]
        image = self.render()
        for point in ((56, 44), (68, 44)):
            self.assertEqual(image.getpixel(point), (17, 34, 51))

    def test_different_layers_do_not_join_but_material_changes_on_one_layer_do(self):
        art = self.asset(Image.new("RGBA", (16, 16), "red"))
        other = self.asset(Image.new("RGBA", (16, 16), "blue"))
        self.wall(art, (2, 2, 6, 2))
        branch = self.wall(other, (6, 2, 6, 6))
        self.assertNotEqual(self.render().getpixel((100, 28)), (17, 34, 51))
        self.doc["layers"].append({"id": "other", "name": "Other", "visible": True, "locked": False})
        branch["layerId"] = "other"
        self.assertEqual(self.render().getpixel((100, 28)), (17, 34, 51))

    def test_geometry_work_limit_rejects_without_mutating_a_source(self):
        self.wall(None, (1, 1, 5, 1))
        before = deepcopy(self.doc)
        with patch("gravewright.maps.wall_joins.MAX_WORK", 0):
            with self.assertRaisesMessage(builder_services.services.MapError, "The map produces too many wall segments."):
                wall_join_geometry(self.doc, list(builder_services.segments(self.doc)))
        self.assertEqual(self.doc, before)

    def test_diagonal_door_at_a_node_does_not_block_unrelated_wall_joins(self):
        self.wall(None, (1, 3, 5, 3))
        self.wall(None, (5, 3, 5, 7))
        before = self.render().copy()
        self.addCleanup(before.close)
        self.doc["doors"] = [{"id": "door", "layerId": "base", "assetId": None,
            "x1": 4, "y1": 2, "x2": 6, "y2": 4, "thickness": 1, "state": "open"}]
        self.assertEqual(self.render().tobytes(), before.tobytes())

    def test_other_layer_independent_door_keeps_its_collinear_opening_edge_hard(self):
        self.wall(None, (1, 3, 5, 3))
        self.wall(None, (5, 3, 5, 7))
        self.doc["layers"].append({"id": "other", "name": "Other", "visible": True, "locked": False})
        self.doc["doors"] = [{"id": "door", "layerId": "other", "assetId": None,
            "x1": 5, "y1": 3, "x2": 7, "y2": 3, "thickness": 1, "state": "open"}]
        self.assertEqual(self.render().getpixel((84, 44)), (17, 34, 51))

    def test_cached_integer_repeat_preserves_pixels_alpha_and_negative_phase(self):
        with Image.new("RGBA", (32, 8), (255, 0, 0, 128)) as art:
            ImageDraw.Draw(art).rectangle((8, 0, 15, 7), fill=(0, 255, 0, 64))
            ImageDraw.Draw(art).rectangle((24, 0, 31, 7), fill=(0, 0, 255, 0))
            with art.transform((16, 4), Image.Transform.AFFINE, (2, 0, 0, 0, 2, 0), Image.Resampling.BICUBIC) as repeat:
                for phase in (0, 3, -3):
                    with self.subTest(phase=phase), builder_render._wall_strip(art, 35, 4, phase) as original:
                        with builder_render._wall_strip(art, 35, 4, phase, repeat) as cached:
                            self.assertEqual(cached.tobytes(), original.tobytes())
