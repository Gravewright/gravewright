"""Wall artwork follows each segment instead of a world-aligned square tile."""

from copy import deepcopy
from io import BytesIO
import math
from types import SimpleNamespace
from unittest.mock import patch
import uuid

from django.test import SimpleTestCase
from PIL import Image, ImageColor, ImageDraw

from gravewright.maps import builder_render


class BuilderWallArtworkTests(SimpleTestCase):
    def setUp(self):
        self.rows = []
        self.doc = {
            "schemaVersion": 3, "name": "Wall artwork", "columns": 12, "rows": 10,
            "cellSize": 16, "background": "#112233", "assets": [],
            "layers": [{"id": "base", "name": "Base", "visible": True, "locked": False}],
            "floors": [], "walls": [], "doors": [], "decorations": [], "lights": [],
        }

    def asset(self, image, role="wall"):
        stream = BytesIO()
        image.save(stream, "PNG")
        image.close()
        payload = stream.getvalue()
        asset_id = str(uuid.uuid4())
        self.rows.append(SimpleNamespace(pk=asset_id, name="Synthetic wall.png",
            file=SimpleNamespace(open=lambda mode: BytesIO(payload))))
        self.doc["assets"].append({"assetId": asset_id, "role": role})
        return asset_id

    def striped_wall(self):
        image = Image.new("RGBA", (80, 48))
        draw = ImageDraw.Draw(image)
        for index, (top, bottom) in enumerate(zip(
                ("red", "green", "blue", "yellow"), ("cyan", "magenta", "orange", "white"))):
            left = 8 + index * 16
            draw.rectangle((left, 16, left + 15, 23), fill=top)
            draw.rectangle((left, 24, left + 15, 31), fill=bottom)
        # Invisible export noise must not inflate the visible wall thickness.
        image.putpixel((0, 0), (255, 0, 0, 1))
        return self.asset(image)

    def wall(self, asset_id, endpoints, **extra):
        wall = {"id": str(uuid.uuid4()), "layerId": "base", "assetId": asset_id,
                "thickness": 1, **dict(zip(("x1", "y1", "x2", "y2"), endpoints)), **extra}
        self.doc["walls"].append(wall)
        return wall

    def render(self):
        before = deepcopy(self.doc)
        with patch("gravewright.maps.builder_render.MapAsset.objects.filter", return_value=self.rows):
            result = builder_render.render(self.doc, uuid.uuid4())
        self.addCleanup(result.close)
        image = Image.open(result)
        image.load()
        self.addCleanup(image.close)
        self.assertEqual(self.doc, before)
        return image

    def test_horizontal_wall_trims_padding_and_repeats_its_full_natural_aspect(self):
        self.wall(self.striped_wall(), (1, 3, 10, 3))
        image = self.render()
        for offset, color in ((8, "red"), (24, "green"), (40, "blue"), (56, "yellow"), (72, "red")):
            self.assertEqual(image.getpixel((16 + offset, 44)), ImageColor.getrgb(color))
        self.assertEqual(image.getpixel((24, 52)), (0, 255, 255))
        self.assertEqual(image.getpixel((24, 38)), (17, 34, 51))

    def test_vertical_wall_rotates_the_complete_strip_and_retains_its_sides(self):
        self.wall(self.striped_wall(), (3, 1, 3, 9))
        image = self.render()
        self.assertEqual(image.getpixel((52, 24)), (255, 0, 0))
        self.assertEqual(image.getpixel((44, 24)), (0, 255, 255))
        self.assertEqual(image.getpixel((52, 40)), (0, 128, 0))
        self.assertEqual(image.getpixel((52, 88)), (255, 0, 0))
        self.assertEqual(image.getpixel((38, 24)), (17, 34, 51))

    def test_diagonal_and_reversed_walls_follow_their_authored_direction(self):
        asset_id = self.striped_wall()
        self.wall(asset_id, (1, 1, 6, 6))
        self.wall(asset_id, (10, 8, 1, 8))
        image = self.render()
        unit = 1 / math.sqrt(2)
        point = (round(16 + 8 * unit + 4 * unit), round(16 + 8 * unit - 4 * unit))
        self.assertEqual(image.getpixel(point), (255, 0, 0))
        self.assertEqual(image.getpixel((152, 132)), (255, 0, 0))
        self.assertEqual(image.getpixel((152, 124)), (0, 255, 255))

    def test_door_cut_does_not_restart_texture_phase(self):
        self.wall(self.striped_wall(), (1, 5, 11, 5))
        self.doc["doors"] = [{"id": str(uuid.uuid4()), "layerId": "base", "assetId": None,
            "x1": 2.5, "y1": 5, "x2": 4.5, "y2": 5, "thickness": 1, "state": "closed"}]
        image = self.render()
        self.assertEqual(image.getpixel((52, 76)), (17, 34, 51))
        self.assertEqual(image.getpixel((76, 76)), (255, 255, 0))
        self.assertEqual(image.getpixel((88, 76)), (255, 0, 0))

    def test_internal_alpha_and_fully_transparent_art_keep_the_floor_visible(self):
        blue = self.asset(Image.new("RGB", (16, 16), "blue"), "floor")
        self.doc["floors"] = [{"id": "floor", "layerId": "base", "assetId": blue,
                               "x": 0, "y": 0, "width": 12, "height": 10}]
        art = Image.new("RGBA", (64, 16), "red")
        ImageDraw.Draw(art).rectangle((16, 0, 31, 15), fill=(0, 0, 0, 0))
        self.wall(self.asset(art), (1, 3, 10, 3))
        self.wall(self.asset(Image.new("RGBA", (64, 16))), (1, 6, 10, 6))
        image = self.render()
        self.assertEqual(image.getpixel((24, 48)), (255, 0, 0))
        self.assertEqual(image.getpixel((40, 48)), (0, 0, 255))
        self.assertEqual(image.getpixel((24, 96)), (0, 0, 255))

    def test_extreme_aspects_never_allocate_a_resized_full_length_tile(self):
        wide = self.asset(Image.new("RGBA", (8192, 1), "red"))
        narrow = self.asset(Image.new("RGBA", (1, 8192), "green"))
        self.wall(wide, (1, 3, 10, 3), thickness=2)
        self.wall(narrow, (1, 7, 10, 7), thickness=2)
        image = self.render()
        self.assertEqual(image.getpixel((24, 48)), (255, 0, 0))
        self.assertEqual(image.getpixel((24, 112)), (0, 128, 0))

    def test_fractional_repeat_boundaries_have_no_gaps_or_doubled_opacity(self):
        with Image.new("RGBA", (1972, 302), (255, 0, 0, 128)) as art:
            with builder_render._wall_strip(art, 1024, 14, 0) as strip:
                with strip.getchannel("A") as alpha:
                    self.assertEqual(alpha.getextrema(), (128, 128))
