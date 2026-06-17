from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from enum import StrEnum
from math import ceil


EMPTY_TILE_REF = 0
UINT32_MAX = (2**32) - 1
SCENE_MANIFEST_VERSION = 1
SCENE_NATIVE_CHUNK_SIZE = 16


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

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("width must be positive")
        if self.height <= 0:
            raise ValueError("height must be positive")
        if self.tile_size <= 0:
            raise ValueError("tile_size must be positive")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

    @property
    def grid_size(self) -> int:
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

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("version must be positive")
        if self.byte_size < 0:
            raise ValueError("byte_size must be zero or positive")


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
        if self.version != SCENE_MANIFEST_VERSION:
            raise ValueError("unsupported scene manifest version")
        if self.tile_table_version < 1:
            raise ValueError("tile_table_version must be positive")
        if self.scene_epoch < 1:
            raise ValueError("scene_epoch must be positive")
