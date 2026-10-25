"""Generate lossless 512 px map tiles, with level zero at full resolution.

Decode and generation are serialized per process. The Pillow fallback decodes a
whole raster and has a separate pixel ceiling; libvips streams ordinary maps
through dzsave. Native codecs and rotations can also require temporary disk space.
The caller owns authorization, persistence and removal of already saved tiles.
"""

from contextlib import contextmanager
from functools import lru_cache
from importlib.util import find_spec
from io import BytesIO
import logging
import os
from pathlib import Path
import tempfile
import threading
import zlib

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile, File
from PIL import Image, ImageOps, UnidentifiedImageError

from .services import MapError

TILE_SIZE = 512
_DEFAULT_MAX_IMAGE_PIXELS = Image.MAX_IMAGE_PIXELS
_processing = threading.Lock()
logger = logging.getLogger(__name__)
PIXEL_LIMIT_ERROR = "This map exceeds the server image pixel limit."
INVALID_IMAGE_ERROR = "Choose a valid PNG, JPEG, WebP or TIFF image."


def configure_pillow_limit():
    """Align Pillow's process-wide header guard at startup, never per upload."""
    Image.MAX_IMAGE_PIXELS = max(
        _DEFAULT_MAX_IMAGE_PIXELS or 0, settings.GRAVEWRIGHT_MAP_MAX_PIXELS
    )


def max_lod(width, height):
    return max(0, (max(width, height) - 1).bit_length() - 9)


def level_size(width, height, lod):
    divisor = 2**lod
    return (width + divisor - 1) // divisor, (height + divisor - 1) // divisor


def tile_count(width, height):
    return sum(
        ((w + TILE_SIZE - 1) // TILE_SIZE) * ((h + TILE_SIZE - 1) // TILE_SIZE)
        for w, h in (level_size(width, height, lod) for lod in range(max_lod(width, height) + 1))
    )


def _scratch_root():
    # Preserve explicit upload-temp and Runner tool-root overrides. Neither the
    # current directory nor an OS-profile temp folder selects the default.
    if settings.FILE_UPLOAD_TEMP_DIR:
        root = Path(settings.FILE_UPLOAD_TEMP_DIR)
    else:
        root = Path(os.environ.get("GRAVEWRIGHT_RUNNER_ROOT") or "data/runner") / "tmp"
    if not root.is_absolute():
        root = Path(settings.BASE_DIR) / root
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


@lru_cache(maxsize=1)
def _load_vips():
    if find_spec("pyvips") is None:
        return None
    # GLib may cache its temp directory when loaded. Configure native spill files
    # before importing pyvips, including direct ASGI/manage.py entry points.
    root = str(_scratch_root())
    os.environ.update(TMPDIR=root, TMP=root, TEMP=root)
    try:
        import pyvips
    except (ImportError, OSError):
        logger.warning("libvips is unavailable; using the bounded Pillow tiler.", exc_info=True)
        return None
    # Do not retain source pipelines and their open temporary files across maps.
    pyvips.cache_set_max(0)
    return pyvips


def engine():
    choice = getattr(settings, "GRAVEWRIGHT_MAP_TILER", "auto")
    if choice not in {"auto", "vips", "pillow"}:
        raise ImproperlyConfigured("GRAVEWRIGHT_MAP_TILER must be auto, vips or pillow.")
    if choice == "pillow":
        return "pillow"
    if _load_vips() is not None:
        return "vips"
    if choice == "vips":
        raise ImproperlyConfigured(
            "GRAVEWRIGHT_MAP_TILER=vips requires libvips. Install it with uv sync --locked --extra vips."
        )
    return "pillow"


@contextmanager
def _reading_image():
    # Only input reads/decode belong here. Never wrap tile storage or dzsave:
    # their I/O failures are server errors rather than invalid user input.
    try:
        yield
    except Image.DecompressionBombError:
        raise MapError(PIXEL_LIMIT_ERROR) from None
    except (UnidentifiedImageError, ValueError, TypeError, SyntaxError, OSError):
        raise MapError(INVALID_IMAGE_ERROR) from None


def _validate_size(width, height):
    if width * height > settings.GRAVEWRIGHT_MAP_MAX_PIXELS:
        raise MapError(PIXEL_LIMIT_ERROR)
    if width > settings.MAP_IMAGE_MAX_WIDTH or height > settings.MAP_IMAGE_MAX_HEIGHT:
        raise MapError("Map dimensions exceed the configured limit.")
    if tile_count(width, height) > settings.MAP_MAX_TILE_COUNT:
        raise MapError("Map tile count exceeds the configured limit.")


def generate_solid_pyramid(width, height, color, save_tile):
    """Create bounded solid-color tiles without allocating a full-size raster."""
    if any(type(value) is not int or value < 1 for value in (width, height)):
        raise MapError("Use positive whole numbers for map dimensions.")
    from .services import color as validate_color
    color = validate_color(color)
    _validate_size(width, height)
    with _processing:
        encoded_sizes = {}
        top = max_lod(width, height)
        for lod in range(top + 1):
            w, h = level_size(width, height, lod)
            for y in range((h + TILE_SIZE - 1) // TILE_SIZE):
                for x in range((w + TILE_SIZE - 1) // TILE_SIZE):
                    size = (min(TILE_SIZE, w - x * TILE_SIZE), min(TILE_SIZE, h - y * TILE_SIZE))
                    if size not in encoded_sizes:
                        with Image.new("RGB", size, color) as image, BytesIO() as encoded:
                            image.save(encoded, format="WEBP", lossless=True)
                            encoded_sizes[size] = encoded.getvalue()
                    with ContentFile(encoded_sizes[size]) as content:
                        save_tile(lod, x, y, content)
    return width, height, top


def _png_exif(incoming):
    """Find PNG EXIF before or after IDAT without decoding or copying pixels.

    PNG permits eXIf after image data. Some native loaders ignore it there.
    Bound metadata and chunk traversal, and restore Pillow's stream position.
    """
    position = incoming.tell()
    try:
        incoming.seek(8)
        for _ in range(100_000):
            header = incoming.read(8)
            if len(header) != 8:
                raise ValueError("Truncated PNG chunk.")
            size = int.from_bytes(header[:4], "big")
            kind = header[4:]
            if size > 0x7fffffff or incoming.tell() + size + 4 > incoming.size:
                raise ValueError("Invalid PNG chunk length.")
            if kind == b"eXIf":
                if size > 1024 * 1024:
                    raise ValueError("PNG EXIF metadata exceeds 1 MiB.")
                data = incoming.read(size)
                checksum = int.from_bytes(incoming.read(4), "big")
                if zlib.crc32(kind + data) != checksum:
                    raise ValueError("Invalid PNG EXIF checksum.")
                return data
            if kind == b"IEND":
                return None
            incoming.seek(size + 4, 1)
        raise ValueError("PNG has too many chunks.")
    finally:
        incoming.seek(position)


def generate_pyramid(incoming, save_tile):
    """Validate an upload and call ``save_tile(lod, x, y, file)`` for each tile.

    Files are readable Django File objects, valid during the callback only.
    Return oriented ``(width, height, max_lod)``. Input errors raise MapError;
    storage/native generation errors propagate so the caller can clean up.
    """
    with _processing:
        with _reading_image():
            incoming.seek(0)
            source = Image.open(incoming)
        with source:
            if source.format not in {"PNG", "JPEG", "WEBP", "TIFF"}:
                raise MapError(INVALID_IMAGE_ERROR)
            if source.width * source.height > settings.GRAVEWRIGHT_MAP_MAX_PIXELS:
                raise MapError(PIXEL_LIMIT_ERROR)
            # PNG.getexif may decode to find trailing metadata. Scan its chunk
            # framing without caching empty EXIF before source.load instead.
            with _reading_image():
                if source.format == "PNG":
                    exif = Image.Exif()
                    metadata = source.info.get("exif") or _png_exif(incoming)
                    if metadata:
                        if len(metadata) > 1024 * 1024:
                            raise ValueError("PNG EXIF metadata exceeds 1 MiB.")
                        exif.load(metadata)
                else:
                    exif = source.getexif()
                orientation = exif.get(0x0112, 1)
                if type(orientation) is not int or not 1 <= orientation <= 8:
                    orientation = 1
            width, height = source.size
            if orientation in {5, 6, 7, 8}:
                width, height = height, width
            _validate_size(width, height)
            selected = engine()
            if selected == "vips":
                return _build_vips(incoming, save_tile, orientation)
            if width * height > getattr(settings, "GRAVEWRIGHT_MAP_PILLOW_MAX_PIXELS", 64_000_000):
                raise MapError(
                    "This map exceeds the Pillow pixel limit. Install the vips extra "
                    "or configure GRAVEWRIGHT_MAP_PILLOW_MAX_PIXELS."
                )
            return _build_pillow(source, save_tile)


def _build_pillow(source, save_tile):
    with _reading_image():
        source.load()
        ImageOps.exif_transpose(source, in_place=True)
        mode = "RGBA" if "A" in source.getbands() or "transparency" in source.info else "RGB"
        level = source if source.mode == mode else source.convert(mode)
    if level is not source:
        source.close()
    width, height = level.size
    top = max_lod(width, height)
    try:
        _validate_size(width, height)
        for lod in range(top + 1):
            if lod:
                smaller = level.resize(level_size(width, height, lod), Image.Resampling.LANCZOS)
                level.close()
                level = smaller
            for y in range((level.height + TILE_SIZE - 1) // TILE_SIZE):
                for x in range((level.width + TILE_SIZE - 1) // TILE_SIZE):
                    box = (x * TILE_SIZE, y * TILE_SIZE,
                           min((x + 1) * TILE_SIZE, level.width),
                           min((y + 1) * TILE_SIZE, level.height))
                    with level.crop(box) as chunk, BytesIO() as encoded:
                        chunk.save(encoded, format="WEBP", lossless=True)
                        with ContentFile(encoded.getvalue()) as content:
                            save_tile(lod, x, y, content)
    finally:
        level.close()
    return width, height, top


def _build_vips(incoming, save_tile, orientation):
    pyvips = _load_vips()
    root = _scratch_root()
    with tempfile.TemporaryDirectory(prefix="map-tiles-", dir=root) as scratch:
        # Always use a generated filename: vips interprets [options] in names.
        # Chunked spooling also avoids retaining an extra compressed image copy.
        path = Path(scratch) / "source"
        with path.open("wb") as stream:
            incoming.seek(0)
            for chunk in incoming.chunks():
                stream.write(chunk)
        image = None
        try:
            try:
                image = pyvips.Image.new_from_file(str(path), access="sequential", fail_on="error")
                native_orientation = image.get("orientation") if image.get_typeof("orientation") else 1
                if orientation in {2, 3, 4, 5, 6, 7, 8} or native_orientation not in (0, 1):
                    image = pyvips.Image.new_from_file(str(path), access="random", fail_on="error").copy()
                    # Use the validated EXIF value, including PNG metadata that
                    # libvips may have ignored after IDAT.
                    image.set_type(pyvips.GValue.gint_type, "orientation",
                                   orientation if orientation in {2, 3, 4, 5, 6, 7, 8} else native_orientation)
                    image = image.autorot()
                if image.interpretation != "srgb":
                    image = image.colourspace("srgb")
                if image.format != "uchar":
                    image = image.cast("uchar")
            except pyvips.Error:
                raise MapError(INVALID_IMAGE_ERROR) from None
            width, height = image.width, image.height
            _validate_size(width, height)
            top = max_lod(width, height)
            # Native decode and output can fail during evaluation. Preserve that
            # diagnostic as a server error; it can indicate disk exhaustion.
            image.dzsave(str(Path(scratch) / "map"), tile_size=TILE_SIZE,
                         overlap=0, depth="onetile", layout="dz", skip_blanks=-1,
                         suffix=".webp[lossless]")
            for lod in range(top + 1):
                w, h = level_size(width, height, lod)
                directory = Path(scratch) / "map_files" / str(top - lod)
                for y in range((h + TILE_SIZE - 1) // TILE_SIZE):
                    for x in range((w + TILE_SIZE - 1) // TILE_SIZE):
                        with (directory / f"{x}_{y}.webp").open("rb") as stream:
                            save_tile(lod, x, y, File(stream))
            return width, height, top
        finally:
            # Release native file handles before TemporaryDirectory cleanup on Windows.
            image = None
