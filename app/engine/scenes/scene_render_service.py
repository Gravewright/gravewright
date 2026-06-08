from __future__ import annotations

from dataclasses import dataclass
from math import floor
from app.persistence.rows import Row

from app.business.permissions.permission_service import PermissionService
from app.domain.permissions.permissions import TablePermission
from app.domain.scenes import SceneChunkEncoding
from app.domain.scenes import SceneDimensions
from app.domain.scenes import SceneLayerKind
from app.engine.scenes.chunk_codec import decode_uint32_tile_refs
from app.engine.scenes.scene_chunk_service import SceneChunkService
from app.engine.scenes.scene_visibility_service import SceneVisibilityService
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.scene_tile_repository import SceneTileRepository


@dataclass(frozen=True)
class RenderTileProjection:
    tile_ref: int
    asset_id: str
    tx: int
    ty: int
    width: int
    height: int
    hash: str
    byte_size: int


@dataclass(frozen=True)
class RenderLayerProjection:
    layer_id: str
    name: str
    kind: str
    visibility: str
    order: int
    encoding: str
    tile_table_version: int
    tiles: tuple[RenderTileProjection, ...]


@dataclass(frozen=True)
class ActiveSceneRenderProjection:
    campaign_id: str
    scene_id: str
    name: str
    width: int
    height: int
    tile_size: int
    grid_size: int
    chunk_size: int
    chunk_pixel_size: int
    tile_table_version: int
    scene_epoch: int
    layers: tuple[RenderLayerProjection, ...]


@dataclass(frozen=True)
class ViewportChunkProjection:
    scene_id: str
    layer_id: str
    cx: int
    cy: int
    version: int
    hash: str
    byte_size: int
    encoding: str
    tile_refs: tuple[int, ...] | None = None
    data: bytes | None = None


@dataclass(frozen=True)
class SceneRenderResult:
    success: bool
    projection: ActiveSceneRenderProjection | None = None
    chunks: tuple[ViewportChunkProjection, ...] = ()
    error_key: str | None = None


class SceneRenderService:
    def __init__(
        self,
        *,
        scenes: SceneRepository | None = None,
        layers: SceneLayerRepository | None = None,
        tiles: SceneTileRepository | None = None,
        chunk_service: SceneChunkService | None = None,
        permissions: PermissionService | None = None,
        visibility: SceneVisibilityService | None = None,
    ) -> None:
        self.scenes = scenes or SceneRepository()
        self.layers = layers or SceneLayerRepository()
        self.tiles = tiles or SceneTileRepository()
        self.permissions = permissions or PermissionService()
        self.visibility = visibility or SceneVisibilityService(permissions=self.permissions)
        self.chunk_service = chunk_service or SceneChunkService(
            scenes=self.scenes,
            layers=self.layers,
            permissions=self.permissions,
            visibility=self.visibility,
        )

    def get_active_projection(
        self,
        *,
        campaign_id: str,
        user_id: str,
    ) -> SceneRenderResult:
        scene = self.scenes.get_active_scene(campaign_id)

        if scene is None:
            return SceneRenderResult(
                success=False,
                error_key="game.scenes.errors.not_found",
            )

        if not self._can_view_scene(user_id=user_id, campaign_id=campaign_id):
            return SceneRenderResult(
                success=False,
                error_key="permissions.errors.denied",
            )

        return SceneRenderResult(
            success=True,
            projection=self._build_projection(scene, user_id=user_id),
        )

    def get_viewport_chunks(
        self,
        *,
        campaign_id: str,
        user_id: str,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        include_data: bool = False,
        decode_refs: bool = False,
    ) -> SceneRenderResult:
        scene = self.scenes.get_active_scene(campaign_id)

        if scene is None:
            return SceneRenderResult(
                success=False,
                error_key="game.scenes.errors.not_found",
            )

        if not self._can_view_scene(user_id=user_id, campaign_id=campaign_id):
            return SceneRenderResult(
                success=False,
                error_key="permissions.errors.denied",
            )

        dimensions = self._dimensions_from_scene(scene)
        chunk_range = self._viewport_to_chunk_range(
            dimensions=dimensions,
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
        )

        if chunk_range is None:
            return SceneRenderResult(success=True)

        cx0, cy0, cx1, cy1 = chunk_range
        projected_chunks = []

        for layer in self._renderable_layers(
            scene_id=scene["id"],
            campaign_id=scene["campaign_id"],
            user_id=user_id,
        ):
            metadata_result = self.chunk_service.list_chunk_metadata_for_viewport(
                scene_id=scene["id"],
                layer_id=layer["id"],
                cx0=cx0,
                cy0=cy0,
                cx1=cx1,
                cy1=cy1,
                user_id=user_id,
            )

            if not metadata_result.success:
                return SceneRenderResult(
                    success=False,
                    error_key=metadata_result.error_key,
                )

            for chunk in metadata_result.chunks or []:
                data = None
                tile_refs = None

                if include_data or decode_refs:
                    read_result = self.chunk_service.read_chunk(
                        scene_id=scene["id"],
                        layer_id=layer["id"],
                        cx=chunk["cx"],
                        cy=chunk["cy"],
                        user_id=user_id,
                    )

                    if not read_result.success:
                        return SceneRenderResult(
                            success=False,
                            error_key=read_result.error_key,
                        )

                    data = read_result.data

                if decode_refs and data is not None:
                    tile_refs = tuple(decode_uint32_tile_refs(data))

                projected_chunks.append(
                    ViewportChunkProjection(
                        scene_id=scene["id"],
                        layer_id=layer["id"],
                        cx=chunk["cx"],
                        cy=chunk["cy"],
                        version=chunk["version"],
                        hash=chunk["hash"],
                        byte_size=chunk["byte_size"],
                        encoding=chunk["encoding"],
                        tile_refs=tile_refs,
                        data=data if include_data else None,
                    )
                )

        return SceneRenderResult(
            success=True,
            chunks=tuple(projected_chunks),
        )

    def _build_projection(self, scene: Row, *, user_id: str) -> ActiveSceneRenderProjection:
        dimensions = self._dimensions_from_scene(scene)

        return ActiveSceneRenderProjection(
            campaign_id=scene["campaign_id"],
            scene_id=scene["id"],
            name=scene["name"],
            width=dimensions.width,
            height=dimensions.height,
            tile_size=dimensions.tile_size,
            grid_size=dimensions.grid_size,
            chunk_size=dimensions.chunk_size,
            chunk_pixel_size=dimensions.chunk_pixel_size,
            tile_table_version=scene["tile_table_version"],
            scene_epoch=scene["scene_epoch"],
            layers=tuple(
                self._build_layer_projection(layer)
                for layer in self._renderable_layers(
                    scene_id=scene["id"],
                    campaign_id=scene["campaign_id"],
                    user_id=user_id,
                )
            ),
        )

    def _build_layer_projection(self, layer: Row) -> RenderLayerProjection:
        tiles = self.tiles.list_by_layer(layer["id"])

        return RenderLayerProjection(
            layer_id=layer["id"],
            name=layer["name"],
            kind=layer["kind"],
            visibility=layer["visibility"],
            order=layer["display_order"],
            encoding=layer["encoding"],
            tile_table_version=layer["tile_table_version"],
            tiles=tuple(
                RenderTileProjection(
                    tile_ref=tile["tile_ref"],
                    asset_id=tile["asset_id"],
                    tx=tile["tx"],
                    ty=tile["ty"],
                    width=tile["width"],
                    height=tile["height"],
                    hash=tile["hash"],
                    byte_size=tile["byte_size"],
                )
                for tile in tiles
            ),
        )

    def _renderable_layers(
        self,
        *,
        scene_id: str,
        campaign_id: str,
        user_id: str,
    ) -> list[Row]:
        return [
            layer
            for layer in self.layers.list_by_scene(scene_id)
            if layer["kind"] == SceneLayerKind.RASTER_TILE_REFS.value
            and layer["encoding"] == SceneChunkEncoding.UINT32_TILE_REFS_V1.value
            and self.visibility.can_view_layer(
                user_id=user_id,
                campaign_id=campaign_id,
                layer=layer,
            )
        ]

    def _viewport_to_chunk_range(
        self,
        *,
        dimensions: SceneDimensions,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
    ) -> tuple[int, int, int, int] | None:
        min_x = max(0, min(x0, x1))
        min_y = max(0, min(y0, y1))
        max_x = min(dimensions.width, max(x0, x1))
        max_y = min(dimensions.height, max(y0, y1))

        if min_x >= max_x or min_y >= max_y:
            return None

        chunk_pixel_size = dimensions.chunk_pixel_size

        cx0 = floor(min_x / chunk_pixel_size)
        cy0 = floor(min_y / chunk_pixel_size)
        cx1 = floor((max_x - 1) / chunk_pixel_size)
        cy1 = floor((max_y - 1) / chunk_pixel_size)

        return cx0, cy0, cx1, cy1

    def _dimensions_from_scene(self, scene: Row) -> SceneDimensions:
        return SceneDimensions(
            width=scene["width"],
            height=scene["height"],
            tile_size=scene["tile_size"],
            chunk_size=scene["chunk_size"],
        )

    def _can_view_scene(
        self,
        *,
        user_id: str,
        campaign_id: str,
    ) -> bool:
        return self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.SCENE_VIEW,
        )
