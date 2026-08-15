from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image
from PIL import UnidentifiedImageError

try:
    import pyvips
    pyvips.cache_set_max_mem(64 * 1024 * 1024)
    pyvips.cache_set_max(256)
except (ImportError, OSError):  # Development fallback; packaged builds include it.
    pyvips = None


DEFAULT_MAX_DIMENSION = 10_000


Image.MAX_IMAGE_PIXELS = DEFAULT_MAX_DIMENSION * DEFAULT_MAX_DIMENSION


@dataclass(frozen=True)
class DecodedImage:
    image: object
    width: int
    height: int
    format: str


@dataclass(frozen=True)
class EncodedRegion:
    data: bytes
    width: int
    height: int
    content_type: str
    extension: str


class VipsRegionImage:
    """Pillow-compatible crop facade backed by libvips demand evaluation.

    Only the requested region is materialized as a Pillow image.  The encoded
    source and libvips operation graph remain lazy, so peak decoded memory is
    bounded by the current tile rather than the complete raster.
    """

    def __init__(self, image) -> None:
        self._image = image
        self.width = int(image.width)
        self.height = int(image.height)
        self.has_alpha = bool(image.hasalpha())

    def crop(self, box: tuple[int, int, int, int]) -> Image.Image:
        encoded = self.crop_encoded(box)
        with Image.open(BytesIO(encoded.data)) as tile:
            tile.load()
            return tile.convert("RGBA")

    def crop_encoded(self, box: tuple[int, int, int, int]) -> EncodedRegion:
        """Materialize one region directly as its final PNG payload.

        Map tiling uses this method to avoid decoding the libvips output into
        Pillow and encoding the same pixels a second time.
        """
        left, upper, right, lower = (int(value) for value in box)
        width = right - left
        height = lower - upper
        if left < 0 or upper < 0 or width <= 0 or height <= 0:
            raise ValueError("invalid crop region")
        region = self._image.crop(left, upper, width, height)
        if self.has_alpha:
            data = region.pngsave_buffer(compression=6, strip=True)
            content_type, extension = "image/png", ".png"
        else:
            data = region.webpsave_buffer(Q=84, effort=4, strip=True)
            content_type, extension = "image/webp", ".webp"
        return EncodedRegion(
            data=bytes(data), width=width, height=height,
            content_type=content_type, extension=extension,
        )

    def for_lod(self, lod: int) -> "VipsRegionImage":
        if lod < 0:
            raise ValueError("lod must be zero or positive")
        if lod == 0:
            return self
        scale = 1.0 / (2**lod)
        return VipsRegionImage(self._image.resize(scale, kernel="lanczos3"))


class ImageDecoder:
    def __init__(
        self,
        *,
        max_width: int = DEFAULT_MAX_DIMENSION,
        max_height: int = DEFAULT_MAX_DIMENSION,
        max_dimension: int | None = None,
    ) -> None:

        self.max_width = max_dimension if max_dimension is not None else max_width
        self.max_height = max_dimension if max_dimension is not None else max_height

    def decode(self, data: bytes) -> DecodedImage:
        try:
            with Image.open(BytesIO(data)) as image:
                if image.width > self.max_width or image.height > self.max_height:
                    raise ValueError("image dimensions out of range")

                image.load()
                decoded = image.convert("RGBA")
                return DecodedImage(
                    image=decoded,
                    width=image.width,
                    height=image.height,
                    format=image.format or "",
                )
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
            raise ValueError("invalid image") from exc

    def decode_regions(self, data: bytes) -> DecodedImage:
        """Decode a raster lazily for region-based map tiling.

        Packaged builds use the self-contained pyvips binary. Pillow remains a
        compatibility fallback for source/test environments where the optional
        native module cannot be loaded.
        """
        if pyvips is None:
            return self.decode(data)
        try:
            # A tile row revisits the same source scanlines for each X region,
            # therefore random demand access is required. The bounded libvips
            # cache above keeps this region-based without unbounded RAM growth.
            image = pyvips.Image.new_from_buffer(data, "", access="random", fail_on="error")
            if image.width > self.max_width or image.height > self.max_height:
                raise ValueError("image dimensions out of range")
            return DecodedImage(
                image=VipsRegionImage(image),
                width=int(image.width),
                height=int(image.height),
                format=str(image.get("vips-loader") if image.get_typeof("vips-loader") else ""),
            )
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("invalid image") from exc
