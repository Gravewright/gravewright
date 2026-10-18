"""Layer order and texture orientation survive rasterization without baking live objects."""

from copy import deepcopy
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
import uuid

from django.test import SimpleTestCase
from PIL import Image, ImageDraw

from gravewright.maps import builder_render


class BuilderExpandedRasterTests(SimpleTestCase):
    def setUp(self):
        self.assets = []
        self.doc = {
            "schemaVersion": 3, "name": "Layered map", "columns": 4, "rows": 2,
            "cellSize": 16, "background": "#112233", "assets": [],
            "layers": [{"id": "base", "name": "Base", "visible": True, "locked": False},
                       {"id": "upper", "name": "Upper", "visible": False, "locked": True}],
            "floors": [], "walls": [], "doors": [], "decorations": [], "lights": [],
        }

    def asset(self, image, role):
        stream = BytesIO()
        image.save(stream, "PNG")
        image.close()
        payload = stream.getvalue()
        asset_id = str(uuid.uuid4())
        self.assets.append(SimpleNamespace(pk=asset_id, name=f"{role}.png",
                                          file=SimpleNamespace(open=lambda mode: BytesIO(payload))))
        self.doc["assets"].append({"assetId": asset_id, "role": role})
        return asset_id

    def render(self):
        with patch("gravewright.maps.builder_render.MapAsset.objects.filter", return_value=self.assets):
            result = builder_render.render(self.doc, uuid.uuid4())
        self.addCleanup(result.close)
        image = Image.open(result)
        image.load()
        self.addCleanup(image.close)
        return image

    def test_floor_texture_quarter_turns_are_clockwise_and_preserve_the_source(self):
        image = Image.new("RGB", (16, 16))
        draw = ImageDraw.Draw(image)
        for bounds, color in (((0, 0, 7, 7), "red"), ((8, 0, 15, 7), "green"),
                              ((0, 8, 7, 15), "blue"), ((8, 8, 15, 15), "yellow")):
            draw.rectangle(bounds, fill=color)
        asset_id = self.asset(image, "floor")
        self.doc["floors"] = [{"id": str(uuid.uuid4()), "assetId": asset_id, "layerId": "base",
                               "x": index, "y": 0, "width": 1, "height": 2, "rotation": rotation}
                              for index, rotation in enumerate((0, 90, 180, 270))]
        before = deepcopy(self.doc)
        raster = self.render()
        expected = [(255, 0, 0), (0, 0, 255), (255, 255, 0), (0, 128, 0)]
        for index, color in enumerate(expected):
            self.assertEqual(raster.getpixel((index * 16 + 2, 2)), color)
            self.assertEqual(raster.getpixel((index * 16 + 2, 18)), color)
        self.assertEqual(self.doc, before)

    def test_floor_and_wall_passes_each_follow_layer_order_even_when_layers_are_hidden(self):
        red = self.asset(Image.new("RGB", (16, 16), "red"), "floor")
        green = self.asset(Image.new("RGB", (16, 16), "green"), "floor")
        self.doc["floors"] = [
            {"id": "upper-floor", "assetId": green, "layerId": "upper", "x": 0, "y": 0, "width": 4, "height": 2},
            {"id": "base-floor", "assetId": red, "layerId": "base", "x": 0, "y": 0, "width": 4, "height": 2},
        ]
        blue = self.asset(Image.new("RGB", (16, 16), "blue"), "wall")
        yellow = self.asset(Image.new("RGB", (16, 16), "yellow"), "wall")
        self.doc["walls"] = [
            {"id": "upper-wall", "assetId": yellow, "layerId": "upper", "x1": 0, "y1": 1, "x2": 4, "y2": 1, "thickness": .5},
            {"id": "base-wall", "assetId": blue, "layerId": "base", "x1": 0, "y1": 1, "x2": 4, "y2": 1, "thickness": .5},
        ]
        raster = self.render()
        self.assertEqual(raster.getpixel((24, 2)), (0, 128, 0))
        self.assertEqual(raster.getpixel((24, 16)), (255, 255, 0))
        self.doc["layers"].reverse()
        reversed_raster = self.render()
        self.assertEqual(reversed_raster.getpixel((24, 2)), (255, 0, 0))
        self.assertEqual(reversed_raster.getpixel((24, 16)), (0, 0, 255))

    def test_decorations_lights_and_closed_door_art_stay_live_outside_the_raster(self):
        decoration = self.asset(Image.new("RGB", (16, 16), "blue"), "decoration")
        door = self.asset(Image.new("RGB", (16, 16), "green"), "door")
        self.doc["walls"] = [{"id": "wall", "assetId": None, "layerId": "base",
                               "x1": 0, "y1": 1, "x2": 4, "y2": 1, "thickness": .5}]
        self.doc["doors"] = [{"id": "door", "assetId": door, "layerId": "upper", "state": "closed",
                               "x1": 1, "y1": 1, "x2": 2, "y2": 1, "thickness": .5}]
        self.doc["decorations"] = [{"id": "decoration", "assetId": decoration, "layerId": "upper",
                                     "x": 0, "y": 0, "width": 4, "height": 2, "rotation": 45}]
        self.doc["lights"] = [{"id": "light", "layerId": "upper", "x": 2, "y": 1,
                                "brightRadius": 4, "dimRadius": 8, "color": "#ff0000", "intensity": 1, "enabled": True}]
        raster = self.render()
        self.assertEqual(raster.getpixel((24, 16)), (17, 34, 51))
        self.assertEqual(raster.getpixel((8, 16)), (141, 129, 112))
        self.assertEqual(raster.getpixel((8, 2)), (17, 34, 51))

    def test_rotated_transparent_floor_keeps_lower_layers_visible(self):
        blue = self.asset(Image.new("RGB", (16, 16), "blue"), "floor")
        transparent = Image.new("RGBA", (16, 16), (255, 0, 0, 0))
        ImageDraw.Draw(transparent).rectangle((0, 0, 7, 15), fill=(255, 0, 0, 255))
        red = self.asset(transparent, "floor")
        self.doc["floors"] = [
            {"id": "base", "layerId": "base", "assetId": blue, "x": 0, "y": 0, "width": 1, "height": 1},
            {"id": "upper", "layerId": "upper", "assetId": red, "x": 0, "y": 0, "width": 1, "height": 1, "rotation": 90},
        ]
        raster = self.render()
        self.assertEqual(raster.getpixel((2, 2)), (255, 0, 0))
        self.assertEqual(raster.getpixel((2, 14)), (0, 0, 255))
