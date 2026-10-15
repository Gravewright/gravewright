from io import BytesIO
import math
import os
from pathlib import Path
import queue
import tempfile
import threading
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image, ImageChops, ImageOps

from gravewright.maps import tiling
from gravewright.maps.services import MapError


def encoded_image(image, format="PNG", **options):
    with BytesIO() as stream:
        image.save(stream, format, **options)
        return stream.getvalue()


def trailing_png_exif(data):
    chunks = []
    position = 8
    while position < len(data):
        length = int.from_bytes(data[position:position + 4], "big") + 12
        chunks.append(data[position:position + length])
        position += length
    exif = next(chunk for chunk in chunks if chunk[4:8] == b"eXIf")
    return data[:8] + b"".join(chunk for chunk in chunks[:-1] if chunk is not exif) + exif + chunks[-1]


class PyramidCases:
    backend = "pillow"

    def setUp(self):
        super().setUp()
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        settings = override_settings(
            GRAVEWRIGHT_MAP_TILER=self.backend,
            FILE_UPLOAD_TEMP_DIR=self.scratch.name,
        )
        settings.enable()
        self.addCleanup(settings.disable)
        if self.backend == "vips" and tiling._load_vips() is None:
            self.skipTest("The optional libvips dependency is not installed.")

    def generate(self, data):
        tiles = {}

        def save(lod, x, y, content):
            key = (lod, x, y)
            self.assertNotIn(key, tiles)
            size = content.size
            tiles[key] = content.read()
            self.assertEqual(len(tiles[key]), size)

        result = tiling.generate_pyramid(SimpleUploadedFile("map.png", data), save)
        self.assertEqual(list(Path(self.scratch.name).iterdir()), [])
        return result, tiles

    def test_even_odd_small_and_skinny_pyramid_layout(self):
        for width, height in ((32, 21), (512, 512), (1024, 512), (1025, 513),
                              (1, 1025), (1025, 1)):
            with self.subTest(size=(width, height)):
                with Image.new("RGB", (width, height), "#354b66") as image:
                    result, tiles = self.generate(encoded_image(image))
                top = max(0, math.ceil(math.log2(max(width, height) / 512)))
                self.assertEqual(result, (width, height, top))
                expected = {}
                for lod in range(top + 1):
                    w, h = math.ceil(width / 2**lod), math.ceil(height / 2**lod)
                    for y in range(math.ceil(h / 512)):
                        for x in range(math.ceil(w / 512)):
                            expected[lod, x, y] = (min(512, w - x * 512), min(512, h - y * 512))
                self.assertEqual(set(tiles), set(expected))
                for key, data in tiles.items():
                    with Image.open(BytesIO(data)) as tile:
                        self.assertEqual(tile.format, "WEBP")
                        self.assertEqual(tile.size, expected[key])
                        self.assertEqual(tile.convert("RGB").getextrema(), ((53, 53), (75, 75), (102, 102)))

    def test_full_resolution_rgb_is_lossless(self):
        with Image.new("RGB", (65, 33)) as image:
            image.putdata([(x * 3 % 256, y * 7 % 256, (x + y) * 5 % 256)
                           for y in range(image.height) for x in range(image.width)])
            result, tiles = self.generate(encoded_image(image))
            with Image.open(BytesIO(tiles[0, 0, 0])) as tile:
                self.assertEqual(result, (65, 33, 0))
                self.assertEqual(tile.convert("RGB").tobytes(), image.tobytes())

    def test_full_resolution_edge_tiles_match_source_coordinates(self):
        with Image.new("RGB", (1025, 37)) as image:
            image.putdata([(x * 3 % 256, y * 7 % 256, (x + y) * 5 % 256)
                           for y in range(image.height) for x in range(image.width)])
            _, tiles = self.generate(encoded_image(image))
            for x in range(3):
                with Image.open(BytesIO(tiles[0, x, 0])) as tile:
                    with image.crop((x * 512, 0, min((x + 1) * 512, 1025), 37)) as expected:
                        self.assertEqual(tile.convert("RGB").tobytes(), expected.tobytes())

    def test_full_resolution_preserves_alpha_and_palette_transparency(self):
        with Image.new("RGBA", (31, 23)) as rgba, Image.new("P", (31, 23)) as palette:
            colors = [(0, 0, 0, 0), (120, 30, 10, 64), (20, 160, 40, 128), (10, 40, 200, 255)]
            indices = [(x + y) % 4 for y in range(23) for x in range(31)]
            rgba.putdata([colors[index] for index in indices])
            palette.putpalette([channel for color in colors for channel in color[:3]] + [0] * (768 - 12))
            palette.putdata(indices)
            palette.info["transparency"] = bytes(color[3] for color in colors)
            for image in (rgba, palette):
                with self.subTest(mode=image.mode):
                    _, tiles = self.generate(encoded_image(image))
                    with Image.open(BytesIO(tiles[0, 0, 0])) as tile:
                        self.assertIn("A", tile.getbands())
                        self.assertEqual(tile.convert("RGBA").tobytes(), rgba.tobytes())

    def test_reduced_levels_retain_alpha(self):
        with Image.new("RGBA", (1025, 3), (120, 30, 10, 128)) as image:
            _, tiles = self.generate(encoded_image(image))
        for key, data in tiles.items():
            with self.subTest(tile=key), Image.open(BytesIO(data)) as tile:
                self.assertIn("A", tile.getbands())
                self.assertEqual(tile.getchannel("A").getextrema(), (128, 128))

    def test_exif_orientation_changes_dimensions_and_pixels(self):
        with Image.new("RGB", (39, 21)) as image:
            image.putdata([(x * 6, y * 11, (x + y) * 4)
                           for y in range(image.height) for x in range(image.width)])
            for orientation in range(1, 9):
                with self.subTest(orientation=orientation):
                    exif = Image.Exif()
                    exif[0x0112] = orientation
                    data = encoded_image(image, "JPEG", quality=95, subsampling=0, exif=exif)
                    result, tiles = self.generate(data)
                    self.assertEqual(result, (21, 39, 0) if orientation >= 5 else (39, 21, 0))
                    with Image.open(BytesIO(data)) as source, Image.open(BytesIO(tiles[0, 0, 0])) as tile:
                        with ImageOps.exif_transpose(source) as expected:
                            # JPEG decoder builds can differ by a rounding step;
                            # PNG lossless tests do not permit this tolerance.
                            difference = ImageChops.difference(tile.convert("RGB"), expected.convert("RGB"))
                            self.assertLessEqual(max(high for low, high in difference.getextrema()), 2)

    def test_png_exif_after_pixels_is_applied_and_dimensions_revalidated(self):
        with Image.new("RGB", (39, 21)) as image:
            image.putdata([(x * 6, y * 11, (x + y) * 4)
                           for y in range(image.height) for x in range(image.width)])
            exif = Image.Exif()
            exif[0x0112] = 6
            data = trailing_png_exif(encoded_image(image, exif=exif))
            with image.transpose(Image.Transpose.ROTATE_270) as expected:
                result, tiles = self.generate(data)
                self.assertEqual(result, (21, 39, 0))
                with Image.open(BytesIO(tiles[0, 0, 0])) as tile:
                    self.assertEqual(tile.convert("RGB").tobytes(), expected.tobytes())
        with self.settings(MAP_IMAGE_MAX_HEIGHT=30):
            saved = []
            with self.assertRaisesMessage(MapError, "Map dimensions exceed the configured limit."):
                tiling.generate_pyramid(SimpleUploadedFile("map.png", data), lambda *tile: saved.append(tile))
            self.assertEqual(saved, [])
            self.assertEqual(list(Path(self.scratch.name).iterdir()), [])

    def test_invalid_headers_and_unsupported_format_emit_no_tiles(self):
        with Image.new("RGB", (12, 9)) as image:
            gif = encoded_image(image, "GIF")
        for data in (b"not an image", gif):
            with self.subTest(data=data[:12]):
                saved = []
                with self.assertRaisesMessage(MapError, tiling.INVALID_IMAGE_ERROR):
                    tiling.generate_pyramid(SimpleUploadedFile("map.png", data), lambda *tile: saved.append(tile))
                self.assertEqual(saved, [])
                self.assertEqual(list(Path(self.scratch.name).iterdir()), [])

    def test_malformed_png_tail_is_rejected_before_decode(self):
        with Image.new("RGB", (12, 9)) as image:
            png = encoded_image(image)
            exif = Image.Exif()
            exif[0x0112] = 6
            late_exif = bytearray(trailing_png_exif(encoded_image(image, exif=exif)))
        # The byte before IEND belongs to the trailing eXIf checksum.
        late_exif[-13] ^= 1
        for data in (png[:-6], bytes(late_exif)):
            with (self.subTest(tail=data[-16:]),
                  patch("PIL.PngImagePlugin.PngImageFile.load", side_effect=AssertionError("decoded malformed PNG"))):
                saved = []
                with self.assertRaisesMessage(MapError, tiling.INVALID_IMAGE_ERROR):
                    tiling.generate_pyramid(SimpleUploadedFile("map.png", data), lambda *tile: saved.append(tile))
                self.assertEqual(saved, [])
                self.assertEqual(list(Path(self.scratch.name).iterdir()), [])

    def test_storage_callback_errors_propagate_and_remove_staging(self):
        with Image.new("RGB", (1024, 512), "#354b66") as image:
            data = encoded_image(image)
        for error in (OSError("simulated disk full"), ValueError("storage rejected the file")):
            with self.subTest(error=type(error).__name__):
                saved = []

                def fail_second(lod, x, y, content):
                    saved.append((lod, x, y))
                    if len(saved) == 2:
                        raise error

                with self.assertRaises(type(error)) as raised:
                    tiling.generate_pyramid(SimpleUploadedFile("map.png", data), fail_second)
                self.assertIs(raised.exception, error)
                self.assertEqual(len(saved), 2)
                self.assertEqual(list(Path(self.scratch.name).iterdir()), [])
                self.assertFalse(tiling._processing.locked())


class PillowPyramidTests(PyramidCases, SimpleTestCase):
    def test_truncated_pixel_data_is_an_input_error(self):
        with Image.new("RGB", (512, 512), "#354b66") as image:
            data = encoded_image(image)
        with self.assertRaisesMessage(MapError, tiling.INVALID_IMAGE_ERROR):
            self.generate(data[:len(data) // 2])

    def test_guard_accepts_configured_pixels_above_old_pillow_threshold(self):
        with Image.new("RGB", (21, 21)) as image:
            data = encoded_image(image)
        with (patch.object(Image, "MAX_IMAGE_PIXELS", 100),
              patch.object(tiling, "_DEFAULT_MAX_IMAGE_PIXELS", 100),
              self.settings(GRAVEWRIGHT_MAP_MAX_PIXELS=500, GRAVEWRIGHT_MAP_PILLOW_MAX_PIXELS=500)):
            tiling.configure_pillow_limit()
            self.assertEqual(Image.MAX_IMAGE_PIXELS, 500)
            self.assertEqual(self.generate(data)[0], (21, 21, 0))
            with self.settings(GRAVEWRIGHT_MAP_MAX_PIXELS=50):
                tiling.configure_pillow_limit()
                self.assertEqual(Image.MAX_IMAGE_PIXELS, 100)

    def test_exact_pixel_limit_and_fallback_memory_ceiling_precede_decode(self):
        with Image.new("RGB", (21, 21)) as image:
            data = encoded_image(image)
        for limits, message in (
            ({"GRAVEWRIGHT_MAP_MAX_PIXELS": 440}, tiling.PIXEL_LIMIT_ERROR),
            ({"GRAVEWRIGHT_MAP_MAX_PIXELS": 500, "GRAVEWRIGHT_MAP_PILLOW_MAX_PIXELS": 440}, "Pillow pixel limit"),
        ):
            with (self.subTest(limits=limits), self.settings(**limits),
                  patch("PIL.PngImagePlugin.PngImageFile.load", side_effect=AssertionError("decoded before guard"))):
                with self.assertRaisesMessage(MapError, message):
                    self.generate(data)

    def test_pillow_bomb_error_has_pixel_limit_diagnostic(self):
        with patch.object(tiling.Image, "open", side_effect=Image.DecompressionBombError("too large")):
            with self.assertRaisesMessage(MapError, tiling.PIXEL_LIMIT_ERROR):
                self.generate(b"header")

    def test_concurrent_uploads_serialize_header_decode_and_storage(self):
        with Image.new("RGB", (12, 9)) as image:
            data = encoded_image(image)
        decode_entered, release_decode = threading.Event(), threading.Event()
        callback_entered, release_callback = threading.Event(), threading.Event()
        second_started, second_opened = threading.Event(), threading.Event()
        errors = queue.Queue()
        original_open = Image.open

        def opened(*args, **kwargs):
            if threading.current_thread().name == "first-map":
                decode_entered.set()
                if not release_decode.wait(5):
                    raise RuntimeError("first decode was not released")
            else:
                second_opened.set()
            return original_open(*args, **kwargs)

        def save(*args):
            if threading.current_thread().name == "first-map":
                callback_entered.set()
                if not release_callback.wait(5):
                    raise RuntimeError("first callback was not released")

        def upload():
            try:
                if threading.current_thread().name == "second-map":
                    second_started.set()
                tiling.generate_pyramid(SimpleUploadedFile("map.png", data), save)
            except BaseException as error:
                errors.put(error)

        first = threading.Thread(target=upload, name="first-map", daemon=True)
        second = threading.Thread(target=upload, name="second-map", daemon=True)
        with patch.object(tiling.Image, "open", side_effect=opened):
            try:
                first.start()
                self.assertTrue(decode_entered.wait(5))
                second.start()
                self.assertTrue(second_started.wait(5))
                self.assertFalse(second_opened.wait(0.15), "second upload decoded during first decode")
                release_decode.set()
                self.assertTrue(callback_entered.wait(5))
                self.assertFalse(second_opened.wait(0.15), "second upload decoded during first storage callback")
            finally:
                release_decode.set()
                release_callback.set()
                first.join(5)
                if second.ident is not None:
                    second.join(5)
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertTrue(second_opened.is_set())
        self.assertEqual(list(errors.queue), [])


class VipsPyramidTests(PyramidCases, SimpleTestCase):
    backend = "vips"

    def test_native_open_error_is_an_input_error_and_removes_staging(self):
        pyvips = tiling._load_vips()
        with Image.new("RGB", (12, 9)) as image:
            data = encoded_image(image)
        with patch.object(pyvips.Image, "new_from_file", side_effect=pyvips.Error("invalid input")):
            with self.assertRaisesMessage(MapError, tiling.INVALID_IMAGE_ERROR):
                self.generate(data)
        self.assertEqual(list(Path(self.scratch.name).iterdir()), [])

    def test_native_generation_error_propagates_and_removes_staging(self):
        pyvips = tiling._load_vips()
        error = pyvips.Error("simulated native output failure")
        with Image.new("RGB", (12, 9)) as image:
            data = encoded_image(image)
        with patch.object(pyvips.Image, "dzsave", side_effect=error):
            with self.assertRaises(pyvips.Error) as raised:
                self.generate(data)
        self.assertIs(raised.exception, error)
        self.assertEqual(list(Path(self.scratch.name).iterdir()), [])


class TilerConfigurationTests(SimpleTestCase):
    def test_engine_selection_and_missing_optional_dependency(self):
        with patch.object(tiling, "_load_vips", return_value=None) as load:
            with self.settings(GRAVEWRIGHT_MAP_TILER="pillow"):
                self.assertEqual(tiling.engine(), "pillow")
                load.assert_not_called()
            with self.settings(GRAVEWRIGHT_MAP_TILER="auto"):
                self.assertEqual(tiling.engine(), "pillow")
            with self.settings(GRAVEWRIGHT_MAP_TILER="vips"):
                with self.assertRaisesMessage(ImproperlyConfigured, "uv sync --locked --extra vips"):
                    tiling.engine()
        with patch.object(tiling, "_load_vips", return_value=object()):
            for choice in ("auto", "vips"):
                with self.subTest(choice=choice), self.settings(GRAVEWRIGHT_MAP_TILER=choice):
                    self.assertEqual(tiling.engine(), "vips")
        with self.settings(GRAVEWRIGHT_MAP_TILER="unknown"):
            with self.assertRaises(ImproperlyConfigured):
                tiling.engine()

    def test_scratch_defaults_are_independent_of_global_temp_and_media(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            stale = base / "stale-global"
            roots = [base / "Install A espaço", base / "Install B 日本語"]
            with patch.dict(os.environ, {"GRAVEWRIGHT_RUNNER_ROOT": "", "TMP": str(stale), "TEMP": str(stale), "TMPDIR": str(stale)}):
                for root in roots:
                    with self.subTest(root=root), self.settings(BASE_DIR=root, FILE_UPLOAD_TEMP_DIR=None, MEDIA_ROOT=stale):
                        actual = tiling._scratch_root()
                        self.assertEqual(actual, (root / "data/runner/tmp").resolve())
                        self.assertTrue(actual.is_dir())
            self.assertNotEqual(roots[0], roots[1])
            self.assertFalse(stale.exists())

    def test_scratch_respects_explicit_overrides_and_fails_without_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.settings(BASE_DIR=root, FILE_UPLOAD_TEMP_DIR=None):
                with patch.dict(os.environ, {"GRAVEWRIGHT_RUNNER_ROOT": "custom tools"}):
                    self.assertEqual(tiling._scratch_root(), (root / "custom tools/tmp").resolve())
            with self.settings(BASE_DIR=root, FILE_UPLOAD_TEMP_DIR="upload tmp"):
                self.assertEqual(tiling._scratch_root(), (root / "upload tmp").resolve())
                error = PermissionError("cannot create installation/upload tmp")
                with patch.object(Path, "mkdir", side_effect=error) as mkdir:
                    with self.assertRaises(PermissionError) as raised:
                        tiling._scratch_root()
                    self.assertIs(raised.exception, error)
                    mkdir.assert_called_once()
