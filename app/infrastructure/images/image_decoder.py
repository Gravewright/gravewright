from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image
from PIL import UnidentifiedImageError


                                                                              
                                                                               
                                                                            
DEFAULT_MAX_DIMENSION = 10_000

                                                                            
                                                                              
                                         
Image.MAX_IMAGE_PIXELS = DEFAULT_MAX_DIMENSION * DEFAULT_MAX_DIMENSION


@dataclass(frozen=True)
class DecodedImage:
    image: Image.Image
    width: int
    height: int
    format: str


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
