from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from enum import StrEnum
from math import ceil, floor, log2


EMPTY_TILE_REF = 0
UINT32_MAX = (2**32) - 1
SCENE_MANIFEST_VERSION = 2
SCENE_LEGACY_MANIFEST_VERSION = 1
SCENE_NATIVE_CHUNK_SIZE = 16
DEFAULT_RASTER_TILE_SIZE = 512


class SceneStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class SceneVisibility(StrEnum):
    PLAYERS = "players"
    GM_ONLY = "gm_only"
    HIDDEN = "hidden"


class SceneLayerKind(StrEnum):
    RASTER_TILE_REFS = "raster_tile_refs"
    GRID = "grid"
    TOKENS = "tokens"
    NOTES = "notes"


class SceneLayerVisibility(StrEnum):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    GM_ONLY = "gm_only"


class SceneChunkEncoding(StrEnum):
    UINT32_TILE_REFS_V1 = "uint32_tile_refs_v1"
    UINT16_TILE_REFS_V1 = "uint16_tile_refs_v1"
    RASTER_BINARY_V1 = "raster_binary_v1"


class SceneAssetKind(StrEnum):
    ORIGINAL_IMAGE = "original_image"
    RASTER_TILE = "raster_tile"


class RenderPriority(IntEnum):
    IMMEDIATE = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4

    def promoted(self, levels: int = 1) -> RenderPriority:
        return RenderPriority(max(RenderPriority.IMMEDIATE, int(self) - max(0, levels)))


@dataclass(frozen=True)
class RenderPriorityAgingPolicy:
    promote_after_ms: int = 500
    max_aged_priority: RenderPriority = RenderPriority.HIGH

    def __post_init__(self) -> None:
        if self.promote_after_ms <= 0:
            raise ValueError("promote_after_ms must be positive")

    def effective_priority(
        self,
        *,
        base_priority: RenderPriority,
        waited_ms: int,
    ) -> RenderPriority:
        if waited_ms < self.promote_after_ms:
            return base_priority

        promotion_levels = waited_ms // self.promote_after_ms
        promoted_value = int(base_priority) - promotion_levels
        capped_value = max(int(self.max_aged_priority), promoted_value)

        return RenderPriority(capped_value)


@dataclass(frozen=True)
class SceneDimensions:
    width: int
    height: int
    tile_size: int
    chunk_size: int
    gameplay_grid_size: int | None = None

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("width must be positive")
        if self.height <= 0:
            raise ValueError("height must be positive")
        if self.tile_size <= 0:
            raise ValueError("tile_size must be positive")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.gameplay_grid_size is not None and self.gameplay_grid_size <= 0:
            raise ValueError("gameplay_grid_size must be positive")

    @property
    def grid_size(self) -> int:
        return self.gameplay_grid_size or self.tile_size

    @property
    def raster_tile_size(self) -> int:
        """Physical raster page size; ``tile_size`` remains its v1 alias."""
        return self.tile_size

    @property
    def tile_columns(self) -> int:
        return ceil(self.width / self.tile_size)

    @property
    def tile_rows(self) -> int:
        return ceil(self.height / self.tile_size)

    @property
    def chunk_columns(self) -> int:
        return ceil(self.tile_columns / self.chunk_size)

    @property
    def chunk_rows(self) -> int:
        return ceil(self.tile_rows / self.chunk_size)

    @property
    def chunk_pixel_size(self) -> int:
        return self.tile_size * self.chunk_size

    def for_lod(self, lod: int) -> SceneDimensions:
        if lod < 0:
            raise ValueError("lod must be zero or positive")
        divisor = 1 << lod
        return SceneDimensions(
            width=max(1, ceil(self.width / divisor)),
            height=max(1, ceil(self.height / divisor)),
            tile_size=self.raster_tile_size,
            chunk_size=self.chunk_size,
            gameplay_grid_size=self.grid_size,
        )


@dataclass(frozen=True, order=True)
class TileKey:
    scene_id: str
    layer_id: str
    lod: int
    x: int
    y: int

    def __post_init__(self) -> None:
        if not self.scene_id or not self.layer_id:
            raise ValueError("scene_id and layer_id are required")
        if self.lod < 0 or self.x < 0 or self.y < 0:
            raise ValueError("lod and tile coordinates must be zero or positive")

    def cache_key(self) -> str:
        return f"{self.scene_id}:{self.layer_id}:{self.lod}:{self.x}:{self.y}"


@dataclass(frozen=True)
class RasterLayerConfig:
    raster_tile_size: int
    max_lod: int = 0
    tile_index_version: int = 1

    def __post_init__(self) -> None:
        if self.raster_tile_size <= 0:
            raise ValueError("raster_tile_size must be positive")
        if self.max_lod < 0:
            raise ValueError("max_lod must be zero or positive")
        if self.tile_index_version < 1:
            raise ValueError("tile_index_version must be positive")


@dataclass(frozen=True)
class LodSelectionPolicy:
    """Selects a mip level with a dead-band to avoid zoom threshold churn."""

    hysteresis: float = 0.15

    def __post_init__(self) -> None:
        if not 0 <= self.hysteresis < 0.5:
            raise ValueError("hysteresis must be between 0 and 0.5")

    def select(self, *, zoom: float, max_lod: int, current_lod: int | None = None) -> int:
        if zoom <= 0:
            raise ValueError("zoom must be positive")
        if max_lod < 0:
            raise ValueError("max_lod must be zero or positive")
        ideal = min(max_lod, max(0, floor(log2(1 / zoom))))
        if current_lod is None or current_lod < 0 or current_lod > max_lod:
            return ideal
        if ideal == current_lod:
            return current_lod
        boundary = 2 ** (-max(ideal, current_lod))
        if ideal > current_lod and zoom > boundary * (1 - self.hysteresis):
            return current_lod
        if ideal < current_lod and zoom < boundary * (1 + self.hysteresis):
            return current_lod
        return ideal


def camera_relative(*, world_x: float, world_y: float, origin_x: float, origin_y: float) -> tuple[float, float]:
    return world_x - origin_x, world_y - origin_y


@dataclass(frozen=True)
class ChunkCoord:
    cx: int
    cy: int

    def __post_init__(self) -> None:
        if self.cx < 0:
            raise ValueError("cx must be zero or positive")
        if self.cy < 0:
            raise ValueError("cy must be zero or positive")


@dataclass(frozen=True)
class TileCoord:
    tx: int
    ty: int

    def __post_init__(self) -> None:
        if self.tx < 0:
            raise ValueError("tx must be zero or positive")
        if self.ty < 0:
            raise ValueError("ty must be zero or positive")


@dataclass(frozen=True)
class Scene:
    id: str
    campaign_id: str
    name: str
    status: SceneStatus
    visibility: SceneVisibility
    dimensions: SceneDimensions
    active: bool
    group_id: str | None
    grid_visible: bool
    grid_color: str
    tile_table_version: int
    scene_epoch: int
    created_at: int
    updated_at: int


@dataclass(frozen=True)
class SceneLayer:
    id: str
    scene_id: str
    name: str
    kind: SceneLayerKind
    visibility: SceneLayerVisibility
    order: int
    encoding: SceneChunkEncoding
    tile_table_version: int


@dataclass(frozen=True)
class SceneAsset:
    id: str
    scene_id: str
    kind: SceneAssetKind
    storage_path: str
    hash: str
    byte_size: int
    width: int | None = None
    height: int | None = None
    content_type: str | None = None


@dataclass(frozen=True)
class SceneTile:
    scene_id: str
    layer_id: str
    tile_ref: int
    asset_id: str
    coord: TileCoord
    width: int
    height: int
    hash: str
    byte_size: int
    lod: int = 0

    def __post_init__(self) -> None:
        if self.tile_ref <= EMPTY_TILE_REF:
            raise ValueError("tile_ref must be greater than zero")
        if self.tile_ref > UINT32_MAX:
            raise ValueError("tile_ref must fit in uint32")
        if self.width <= 0:
            raise ValueError("width must be positive")
        if self.height <= 0:
            raise ValueError("height must be positive")
        if self.byte_size < 0:
            raise ValueError("byte_size must be zero or positive")
        if self.lod < 0:
            raise ValueError("lod must be zero or positive")


@dataclass(frozen=True)
class SceneChunk:
    id: str
    scene_id: str
    layer_id: str
    coord: ChunkCoord
    version: int
    hash: str
    byte_size: int
    encoding: SceneChunkEncoding
    created_at: int
    updated_at: int
    lod: int = 0

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("version must be positive")
        if self.byte_size < 0:
            raise ValueError("byte_size must be zero or positive")
        if self.lod < 0:
            raise ValueError("lod must be zero or positive")


@dataclass(frozen=True)
class SceneManifest:
    version: int
    scene_id: str
    campaign_id: str
    name: str
    dimensions: SceneDimensions
    tile_table_version: int
    scene_epoch: int
    layers: tuple[SceneLayer, ...]
    assets: tuple[SceneAsset, ...] = ()

    def __post_init__(self) -> None:
        if self.version not in (SCENE_LEGACY_MANIFEST_VERSION, SCENE_MANIFEST_VERSION):
            raise ValueError("unsupported scene manifest version")
        if self.tile_table_version < 1:
            raise ValueError("tile_table_version must be positive")
        if self.scene_epoch < 1:
            raise ValueError("scene_epoch must be positive")
