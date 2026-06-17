from __future__ import annotations

from dataclasses import dataclass
from app.persistence.rows import Row

from app.business.permissions.permission_service import PermissionService
from app.contracts.chunk_storage import ChunkStorageContract
from app.contracts.transport import RealtimeGatewayContract
from app.domain.permissions.permissions import TablePermission
from app.domain.scenes import SceneChunkEncoding
from app.infrastructure.storage.local_chunk_storage import LocalChunkStorage
from app.persistence.repositories.scene_chunk_repository import SceneChunkRepository
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.realtime.events import TransportEvent
from app.engine.scenes.scene_visibility_service import SceneVisibilityService


@dataclass(frozen=True)
class SceneChunkServiceResult:
    success: bool
    chunk: Row | None = None
    chunks: list[Row] | None = None
    data: bytes | None = None
    data_by_coord: dict[tuple[int, int], bytes] | None = None
    error_key: str | None = None


class SceneChunkService:
    def __init__(
        self,
        *,
        scenes: SceneRepository | None = None,
        layers: SceneLayerRepository | None = None,
        chunks: SceneChunkRepository | None = None,
        storage: ChunkStorageContract | None = None,
        permissions: PermissionService | None = None,
        visibility: SceneVisibilityService | None = None,
    ) -> None:
        self.scenes = scenes or SceneRepository()
        self.layers = layers or SceneLayerRepository()
        self.chunks = chunks or SceneChunkRepository()
        self.storage = storage or LocalChunkStorage()
        self.permissions = permissions or PermissionService()
        self.visibility = visibility or SceneVisibilityService(permissions=self.permissions)

    async def write_chunk(
        self,
        *,
        scene_id: str,
        layer_id: str,
        cx: int,
        cy: int,
        data: bytes,
        user_id: str,
        encoding: SceneChunkEncoding = SceneChunkEncoding.UINT32_TILE_REFS_V1,
        transport: RealtimeGatewayContract | None = None,
    ) -> SceneChunkServiceResult:
        context = self._get_scene_layer_context(scene_id=scene_id, layer_id=layer_id)

        if context is None:
            return SceneChunkServiceResult(
                success=False,
                error_key="game.scenes.errors.not_found",
            )

        scene, _layer = context

        if not self._can_write_chunks(user_id=user_id, campaign_id=scene["campaign_id"]):
            return SceneChunkServiceResult(
                success=False,
                error_key="permissions.errors.denied",
            )

        try:
            chunk_hash = self.storage.write_chunk(
                scene_id=scene_id,
                layer_id=layer_id,
                cx=cx,
                cy=cy,
                data=data,
            )
        except ValueError:
            return SceneChunkServiceResult(
                success=False,
                error_key="game.scenes.errors.invalid_chunk",
            )

        chunk = self.chunks.record_write(
            scene_id=scene_id,
            layer_id=layer_id,
            cx=cx,
            cy=cy,
            hash=chunk_hash,
            byte_size=len(data),
            encoding=encoding,
        )

        if transport is not None:
            await transport.to_room(
                room_id=scene["campaign_id"],
                event=TransportEvent.SCENE_CHUNK_UPDATED,
                payload={
                    "room_id": scene["campaign_id"],
                    "scene_id": scene_id,
                    "layer_id": layer_id,
                    "cx": cx,
                    "cy": cy,
                    "version": chunk["version"],
                    "hash": chunk["hash"],
                    "byte_size": chunk["byte_size"],
                },
            )

        return SceneChunkServiceResult(
            success=True,
            chunk=chunk,
        )

    def read_chunk(
        self,
        *,
        scene_id: str,
        layer_id: str,
        cx: int,
        cy: int,
        user_id: str,
    ) -> SceneChunkServiceResult:
        context = self._get_scene_layer_context(scene_id=scene_id, layer_id=layer_id)

        if context is None:
            return SceneChunkServiceResult(
                success=False,
                error_key="game.scenes.errors.not_found",
            )

        scene, layer = context

        if not self.visibility.can_view_layer(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            layer=layer,
        ):
            return SceneChunkServiceResult(
                success=False,
                error_key="permissions.errors.denied",
            )

        try:
            data = self.storage.read_chunk(
                scene_id=scene_id,
                layer_id=layer_id,
                cx=cx,
                cy=cy,
            )
        except ValueError:
            return SceneChunkServiceResult(
                success=False,
                error_key="game.scenes.errors.invalid_chunk",
            )

        chunk = self.chunks.get_metadata(layer_id=layer_id, cx=cx, cy=cy)

        if chunk is None or data is None:
            return SceneChunkServiceResult(
                success=False,
                error_key="game.scenes.errors.chunk_not_found",
            )

        return SceneChunkServiceResult(
            success=True,
            chunk=chunk,
            data=data,
        )

    def read_chunks(
        self,
        *,
        scene_id: str,
        layer_id: str,
        coords: tuple[tuple[int, int], ...],
        user_id: str,
    ) -> SceneChunkServiceResult:
        context = self._get_scene_layer_context(scene_id=scene_id, layer_id=layer_id)

        if context is None:
            return SceneChunkServiceResult(
                success=False,
                error_key="game.scenes.errors.not_found",
            )

        scene, layer = context

        if not self.visibility.can_view_layer(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            layer=layer,
        ):
            return SceneChunkServiceResult(
                success=False,
                error_key="permissions.errors.denied",
            )

        if not coords:
            return SceneChunkServiceResult(success=True, data_by_coord={})

        if any(cx < 0 or cy < 0 for cx, cy in coords):
            return SceneChunkServiceResult(
                success=False,
                error_key="game.scenes.errors.invalid_chunk",
            )

        metadata_by_coord = {
            (chunk["cx"], chunk["cy"]): chunk
            for chunk in self.chunks.list_by_coordinates(
                scene_id=scene_id,
                layer_id=layer_id,
                coords=coords,
            )
        }

        try:
            storage_data = self.storage.read_chunks(
                scene_id=scene_id,
                layer_id=layer_id,
                coords=tuple(metadata_by_coord.keys()),
            )
        except ValueError:
            return SceneChunkServiceResult(
                success=False,
                error_key="game.scenes.errors.invalid_chunk",
            )

        return SceneChunkServiceResult(
            success=True,
            chunks=list(metadata_by_coord.values()),
            data_by_coord=storage_data,
        )

    def list_chunk_metadata_for_viewport(
        self,
        *,
        scene_id: str,
        layer_id: str,
        cx0: int,
        cy0: int,
        cx1: int,
        cy1: int,
        user_id: str,
    ) -> SceneChunkServiceResult:
        context = self._get_scene_layer_context(scene_id=scene_id, layer_id=layer_id)

        if context is None:
            return SceneChunkServiceResult(
                success=False,
                error_key="game.scenes.errors.not_found",
            )

        scene, layer = context

        if not self.visibility.can_view_layer(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            layer=layer,
        ):
            return SceneChunkServiceResult(
                success=False,
                error_key="permissions.errors.denied",
            )

        if min(cx0, cy0, cx1, cy1) < 0:
            return SceneChunkServiceResult(
                success=False,
                error_key="game.scenes.errors.invalid_chunk",
            )

        return SceneChunkServiceResult(
            success=True,
            chunks=self.chunks.list_by_viewport_chunk_range(
                scene_id=scene_id,
                layer_id=layer_id,
                cx0=cx0,
                cy0=cy0,
                cx1=cx1,
                cy1=cy1,
            ),
        )

    def _get_scene_layer_context(
        self,
        *,
        scene_id: str,
        layer_id: str,
    ) -> tuple[Row, Row] | None:
        scene = self.scenes.get_by_id(scene_id)

        if scene is None:
            return None

        layer = self.layers.get_by_id(layer_id)

        if layer is None or layer["scene_id"] != scene_id:
            return None

        return scene, layer

    def _can_write_chunks(
        self,
        *,
        user_id: str,
        campaign_id: str,
    ) -> bool:
        return self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.MAP_EDIT,
        ) or self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.MAP_PAINT,
        )
