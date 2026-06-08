from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update

from app.persistence.database import engine_begin
from app.persistence.rows import Row
from app.persistence.tables import scene_assets as scene_assets_table
from app.persistence.tables import scene_chunks as scene_chunks_table
from app.persistence.tables import scene_layers as scene_layers_table
from app.persistence.tables import scene_tiles as scene_tiles_table
from app.persistence.tables import scenes as scenes_table

from app.business.permissions.permission_service import PermissionService
from app.config import config
from app.contracts.chunk_storage import ChunkStorageContract
from app.contracts.transport import RealtimeGatewayContract
from app.domain.permissions.permissions import TablePermission
from app.domain.scenes import EMPTY_TILE_REF
from app.domain.scenes import SceneAssetKind
from app.domain.scenes import SceneChunkEncoding
from app.domain.scenes import SceneDimensions
from app.domain.scenes import SceneLayerKind
from app.domain.scenes import SceneLayerVisibility
from app.domain.scenes import SceneVisibility
from app.domain.scenes import SCENE_NATIVE_CHUNK_SIZE
from app.domain.scenes import UINT32_MAX
from app.engine.scenes.chunk_codec import encode_uint32_tile_refs
from app.engine.scenes.scene_chunk_service import SceneChunkService
from app.infrastructure.images.image_decoder import ImageDecoder
from app.infrastructure.storage.local_chunk_storage import LocalChunkStorage
from app.infrastructure.storage.local_scene_asset_storage import LocalSceneAssetStorage
from app.persistence.repositories.scene_asset_repository import SceneAssetRepository
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.scene_tile_repository import SceneTileRepository
from app.realtime.events import TransportEvent
from app.observability.diagnostics import emit_diagnostic
from app.realtime.metrics import realtime_metrics


UPLOAD_PHASE_PREPARING = "preparing"
UPLOAD_PHASE_TILING = "tiling"
UPLOAD_PHASE_CHUNKING = "chunking"
UPLOAD_PHASE_COMPLETE = "complete"

                                                                                 
                                                                             
_TILING_REPORT_STEPS = 200
_CHUNKING_REPORT_STEPS = 100

                                                                                
                                               
MAX_UPLOAD_BYTES = config.map_upload_max_bytes
MAX_IMAGE_WIDTH = config.map_image_max_width
MAX_IMAGE_HEIGHT = config.map_image_max_height
MAX_TILE_COUNT = config.map_max_tile_count
MIN_TILE_SIZE = 8
MAX_TILE_SIZE = 1024
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


class _UploadProgressReporter:
    """Emits throttled upload-progress events to the uploading GM only.

    Progress is measured in "work units" (one tile write + one chunk write each
    count as a unit) so the bar advances monotonically from 0 to 100 across both
    the tiling and chunking phases. Frames are only sent when the integer percent
    changes, keeping the WebSocket chatter bounded regardless of map size.
    """

    def __init__(
        self,
        *,
        transport: RealtimeGatewayContract | None,
        user_id: str,
        upload_id: str | None,
        scene_id: str,
        scene_name: str,
        total_units: int,
    ) -> None:
        self._transport = transport
        self._user_id = user_id
        self._upload_id = upload_id
        self._scene_id = scene_id
        self._scene_name = scene_name
        self._total = max(1, total_units)
        self._last_percent = -1

    @property
    def active(self) -> bool:
        return self._transport is not None and bool(self._upload_id)

    async def report(self, *, phase: str, done_units: int, force: bool = False) -> None:
        if not self.active:
            return

        percent = min(100, max(0, int(done_units * 100 / self._total)))
        if not force and percent == self._last_percent:
            return

        self._last_percent = percent
        await self._transport.to_player(
            self._user_id,
            TransportEvent.SCENE_UPLOAD_PROGRESS,
            {
                "upload_id": self._upload_id,
                "scene_id": self._scene_id,
                "scene_name": self._scene_name,
                "phase": phase,
                "processed": done_units,
                "total": self._total,
                "percent": percent,
            },
        )
                                                                          
        await asyncio.sleep(0)


@dataclass(frozen=True)
class MapUploadResult:
    success: bool
    scene: Row | None = None
    layer: Row | None = None
    original_asset: Row | None = None
    tile_count: int = 0
    chunk_count: int = 0
    error_key: str | None = None




def _record_map_operation(
    operation: str,
    *,
    campaign_id: str | None = None,
    scene_id: str | None = None,
    user_id: str | None = None,
    success: bool,
    error_key: str | None = None,
    tile_count: int = 0,
    chunk_count: int = 0,
) -> None:
    realtime_metrics.increment(f"map.{operation}.count")
    realtime_metrics.increment(f"map.{operation}.{'success' if success else 'failure'}")
    if error_key:
        realtime_metrics.increment(f"map.{operation}.error")
    emit_diagnostic(
        f"map.{operation}",
        campaign_id=campaign_id,
        scene_id=scene_id,
        user_id=user_id,
        success=success,
        error_key=error_key,
        tile_count=tile_count,
        chunk_count=chunk_count,
    )


@dataclass(frozen=True)
class _StagedRetileTile:
    tx: int
    ty: int
    tile_ref: int
    width: int
    height: int
    hash: str
    byte_size: int
    storage_path: str


@dataclass(frozen=True)
class _StagedRetileChunk:
    cx: int
    cy: int
    hash: str
    byte_size: int


@dataclass(frozen=True)
class _StagedRetileLayer:
    layer: dict
    tile_stage_dir: Path
    chunk_stage_dir: Path
    tiles: tuple[_StagedRetileTile, ...]
    chunks: tuple[_StagedRetileChunk, ...]


@dataclass(frozen=True)
class _PromotionBackup:
    layer: dict
    tile_backup_dir: Path | None
    chunk_backup_dir: Path | None


class MapUploadService:
    def __init__(
        self,
        *,
        scenes: SceneRepository | None = None,
        layers: SceneLayerRepository | None = None,
        assets: SceneAssetRepository | None = None,
        tiles: SceneTileRepository | None = None,
        chunk_service: SceneChunkService | None = None,
        asset_storage: LocalSceneAssetStorage | None = None,
        chunk_storage: ChunkStorageContract | None = None,
        image_decoder: ImageDecoder | None = None,
        permissions: PermissionService | None = None,
    ) -> None:
        self.scenes = scenes or SceneRepository()
        self.layers = layers or SceneLayerRepository()
        self.assets = assets or SceneAssetRepository()
        self.tiles = tiles or SceneTileRepository()
        self.permissions = permissions or PermissionService()
        self.asset_storage = asset_storage or LocalSceneAssetStorage()
        self.chunk_storage = chunk_storage or LocalChunkStorage()
        self.chunk_service = chunk_service or SceneChunkService(
            scenes=self.scenes,
            layers=self.layers,
            storage=self.chunk_storage,
            permissions=self.permissions,
        )
        self.image_decoder = image_decoder or ImageDecoder(
            max_width=config.map_image_max_width,
            max_height=config.map_image_max_height,
        )

    async def upload_raster_map(
        self,
        *,
        campaign_id: str,
        user_id: str,
        name: str,
        filename: str,
        content_type: str,
        data: bytes,
        tile_size: int,
        chunk_size: int,
        group_id: str | None = None,
        visibility: SceneVisibility = SceneVisibility.PLAYERS,
        grid_visible: bool = True,
        grid_color: str = "#6fddb4",
        grid_opacity: float = 0.4,
        transport: RealtimeGatewayContract | None = None,
        upload_id: str | None = None,
    ) -> MapUploadResult:
        emit_diagnostic(
            "map.upload.started",
            campaign_id=campaign_id,
            user_id=user_id,
            filename=filename,
            byte_size=len(data),
            tile_size=tile_size,
        )
        permission_error = self._validate_permissions(campaign_id=campaign_id, user_id=user_id)

        if permission_error is not None:
            return permission_error

        metadata_error = self._validate_upload_metadata(
            filename=filename,
            content_type=content_type,
            data=data,
        )

        if metadata_error is not None:
            return metadata_error

        normalized_name = " ".join(name.strip().split())

        if len(normalized_name) < 2:
            return MapUploadResult(
                success=False,
                error_key="game.scenes.errors.invalid_name",
            )

        try:
            decoded = self.image_decoder.decode(data)
        except ValueError:
            return MapUploadResult(
                success=False,
                error_key="game.maps.errors.invalid_image",
            )

        try:
            dimensions = self._validate_dimensions(
                width=decoded.width,
                height=decoded.height,
                tile_size=tile_size,
                chunk_size=chunk_size,
            )
        except ValueError:
            return MapUploadResult(
                success=False,
                error_key="game.scenes.errors.invalid_dimensions",
            )

        scene = self.scenes.create(
            campaign_id=campaign_id,
            name=normalized_name,
            width=dimensions.width,
            height=dimensions.height,
            tile_size=dimensions.tile_size,
            chunk_size=dimensions.chunk_size,
            group_id=group_id or None,
            visibility=visibility,
            grid_visible=grid_visible,
            grid_color=grid_color,
            grid_opacity=grid_opacity,
        )
        layer = self.layers.create(
            scene_id=scene["id"],
            name="Ground",
            kind=SceneLayerKind.RASTER_TILE_REFS,
            visibility=SceneLayerVisibility.VISIBLE,
            display_order=0,
            encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
        )

                                                                                
                                                                                
                                                              
        try:
            original_path = self.asset_storage.write_original(
                scene_id=scene["id"],
                filename=filename,
                data=data,
            )
            original_asset = self.assets.create(
                scene_id=scene["id"],
                kind=SceneAssetKind.ORIGINAL_IMAGE,
                storage_path=original_path,
                hash=hashlib.sha256(data).hexdigest(),
                byte_size=len(data),
                width=decoded.width,
                height=decoded.height,
                content_type=content_type,
            )

            tile_total = dimensions.tile_columns * dimensions.tile_rows
            chunk_total = dimensions.chunk_columns * dimensions.chunk_rows
            reporter = _UploadProgressReporter(
                transport=transport,
                user_id=user_id,
                upload_id=upload_id,
                scene_id=scene["id"],
                scene_name=scene["name"],
                total_units=tile_total + chunk_total,
            )
            await reporter.report(phase=UPLOAD_PHASE_PREPARING, done_units=0, force=True)

            tile_refs = await self._write_tiles(
                scene_id=scene["id"],
                layer_id=layer["id"],
                image=decoded.image,
                dimensions=dimensions,
                reporter=reporter,
            )
            chunk_count = await self._write_chunks(
                scene_id=scene["id"],
                layer_id=layer["id"],
                user_id=user_id,
                dimensions=dimensions,
                tile_refs=tile_refs,
                reporter=reporter,
                done_offset=tile_total,
            )

            await reporter.report(
                phase=UPLOAD_PHASE_COMPLETE,
                done_units=tile_total + chunk_total,
                force=True,
            )
        except Exception:
            self._discard_scene(scene["id"])
            _record_map_operation(
                "upload",
                campaign_id=campaign_id,
                scene_id=scene["id"],
                user_id=user_id,
                success=False,
                error_key="game.maps.errors.processing_failed",
            )
            return MapUploadResult(
                success=False,
                error_key="game.maps.errors.processing_failed",
            )

        if transport is not None:
            await self._emit_upload_events(
                transport=transport,
                campaign_id=campaign_id,
                scene=scene,
                layer=layer,
                dimensions=dimensions,
            )

        _record_map_operation(
            "upload",
            campaign_id=campaign_id,
            scene_id=scene["id"],
            user_id=user_id,
            success=True,
            tile_count=len(tile_refs),
            chunk_count=chunk_count,
        )
        return MapUploadResult(
            success=True,
            scene=scene,
            layer=layer,
            original_asset=original_asset,
            tile_count=len(tile_refs),
            chunk_count=chunk_count,
        )

    def _discard_scene(self, scene_id: str) -> None:
        """Best-effort removal of a partially-built scene (rows + storage)."""
        try:
            self.scenes.delete(scene_id)
        except Exception:
            pass
        try:
            self.asset_storage.delete_scene(scene_id=scene_id)
        except Exception:
            pass

    async def delete_scene(
        self,
        *,
        scene_id: str,
        user_id: str,
        transport: RealtimeGatewayContract | None = None,
    ) -> MapUploadResult:
        """Permanently delete a scene along with its original map, tiles and chunks.

        Dependent database rows (layers, tiles, chunks, assets) are removed via
        ON DELETE CASCADE; the on-disk tree — originals, tiles and chunks all live
        under ``<root>/<scene_id>/`` — is removed from storage.
        """
        scene = self.scenes.get_by_id(scene_id)
        if scene is None:
            return MapUploadResult(success=False, error_key="game.scenes.errors.not_found")

        campaign_id = scene["campaign_id"]
        if not self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.SCENE_MANAGE,
        ):
            return MapUploadResult(success=False, error_key="permissions.errors.denied")

        was_active = bool(scene["active"])

        self.scenes.delete(scene_id)
        try:
            self.asset_storage.delete_scene(scene_id=scene_id)
        except Exception:
            pass

        _record_map_operation(
            "delete",
            campaign_id=campaign_id,
            scene_id=scene_id,
            user_id=user_id,
            success=True,
        )

        if transport is not None:
            await transport.to_room(
                room_id=campaign_id,
                event=TransportEvent.SCENE_DELETED,
                payload={
                    "room_id": campaign_id,
                    "scene_id": scene_id,
                    "was_active": was_active,
                },
            )

        return MapUploadResult(success=True, scene=scene)

    async def retile_scene(
        self,
        *,
        scene_id: str,
        user_id: str,
        new_tile_size: int,
    ) -> MapUploadResult:
        scene = self.scenes.get_by_id(scene_id)
        if scene is None:
            return MapUploadResult(success=False, error_key="game.scenes.errors.not_found")

        if not self.permissions.can(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            permission=TablePermission.SCENE_MANAGE,
        ):
            return MapUploadResult(success=False, error_key="permissions.errors.denied")

        if new_tile_size < MIN_TILE_SIZE or new_tile_size > MAX_TILE_SIZE:
            return MapUploadResult(success=False, error_key="game.scenes.errors.invalid_dimensions")

        original_asset = self.assets.get_original_for_scene(scene_id)
        if original_asset is None:
            return MapUploadResult(success=False, error_key="game.scenes.errors.not_found")

        try:
            data = self.asset_storage.read_asset(original_asset["storage_path"])
            decoded = self.image_decoder.decode(data)
        except (ValueError, OSError):
            return MapUploadResult(success=False, error_key="game.maps.errors.invalid_image")

        try:
            dimensions = SceneDimensions(
                width=decoded.width,
                height=decoded.height,
                tile_size=new_tile_size,
                chunk_size=scene["chunk_size"],
            )
        except ValueError:
            return MapUploadResult(success=False, error_key="game.scenes.errors.invalid_dimensions")

        tile_count = dimensions.tile_columns * dimensions.tile_rows
        if tile_count > MAX_TILE_COUNT or tile_count > UINT32_MAX:
            return MapUploadResult(success=False, error_key="game.scenes.errors.invalid_dimensions")

        raster_layers = [
            dict(layer)
            for layer in self.layers.list_by_scene(scene_id)
            if layer["kind"] == SceneLayerKind.RASTER_TILE_REFS.value
        ]

        emit_diagnostic(
            "map.retile.started",
            campaign_id=scene["campaign_id"],
            scene_id=scene_id,
            user_id=user_id,
            tile_size=new_tile_size,
            staging=config.map_re_tile_use_staging,
        )
        if config.map_re_tile_use_staging:
            result = await asyncio.to_thread(
                self._retile_with_staging,
                scene_id=scene_id,
                raster_layers=raster_layers,
                image=decoded.image,
                dimensions=dimensions,
            )
        else:
            result = await asyncio.to_thread(
                self._retile_in_place,
                scene_id=scene_id,
                raster_layers=raster_layers,
                image=decoded.image,
                dimensions=dimensions,
            )
        _record_map_operation(
            "retile",
            campaign_id=scene["campaign_id"],
            scene_id=scene_id,
            user_id=user_id,
            success=result.success,
            error_key=result.error_key,
            tile_count=result.tile_count,
            chunk_count=result.chunk_count,
        )
        return result

    def _retile_with_staging(
        self,
        *,
        scene_id: str,
        raster_layers: list[dict],
        image,
        dimensions: SceneDimensions,
    ) -> MapUploadResult:
        """Retile via disk staging and metadata swap.

        New tile/chunk files are rendered under hidden staging directories first.
        Existing layer directories remain untouched during generation. Commit then
        swaps staged directories into their final locations, keeps backups of the
        old directories, writes all metadata in one database transaction, and only
        deletes backups after the transaction succeeds. If metadata commit fails,
        the previous directories are restored so readers keep seeing a consistent
        layer.
        """
        staged_layers: list[_StagedRetileLayer] = []
        backups: list[_PromotionBackup] = []

        try:
            for layer in raster_layers:
                staged_layers.append(
                    self._render_tiles(
                        scene_id=scene_id,
                        layer=layer,
                        image=image,
                        dimensions=dimensions,
                    )
                )
        except Exception:
            for staged in staged_layers:
                self._discard_staged_layer(staged)
            return MapUploadResult(success=False, error_key="game.maps.errors.processing_failed")

        try:
            for staged in staged_layers:
                tile_backup: Path | None = None
                chunk_backup: Path | None = None
                try:
                    tile_backup = self.asset_storage.promote_layer_tiles_staging(
                        scene_id=scene_id,
                        layer_id=staged.layer["id"],
                        staging_dir=staged.tile_stage_dir,
                    )
                    chunk_backup = self.chunk_storage.promote_layer_chunks_staging(
                        scene_id=scene_id,
                        layer_id=staged.layer["id"],
                        staging_dir=staged.chunk_stage_dir,
                    )
                except Exception:
                    if not staged.chunk_stage_dir.exists():
                        self.chunk_storage.restore_layer_chunks_backup(
                            scene_id=scene_id,
                            layer_id=staged.layer["id"],
                            backup_dir=chunk_backup,
                        )
                    if not staged.tile_stage_dir.exists():
                        self.asset_storage.restore_layer_tiles_backup(
                            scene_id=scene_id,
                            layer_id=staged.layer["id"],
                            backup_dir=tile_backup,
                        )
                    raise

                backups.append(
                    _PromotionBackup(
                        layer=staged.layer,
                        tile_backup_dir=tile_backup,
                        chunk_backup_dir=chunk_backup,
                    )
                )

            self._replace_retile_metadata_atomic(scene_id=scene_id, staged_layers=staged_layers)
        except Exception:
            for backup in reversed(backups):
                try:
                    self.chunk_storage.restore_layer_chunks_backup(
                        scene_id=scene_id,
                        layer_id=backup.layer["id"],
                        backup_dir=backup.chunk_backup_dir,
                    )
                except Exception:
                    pass
                try:
                    self.asset_storage.restore_layer_tiles_backup(
                        scene_id=scene_id,
                        layer_id=backup.layer["id"],
                        backup_dir=backup.tile_backup_dir,
                    )
                except Exception:
                    pass
            for staged in staged_layers:
                self._discard_staged_layer(staged)
            return MapUploadResult(success=False, error_key="game.maps.errors.processing_failed")

        for backup in backups:
            self.chunk_storage.discard_path(backup.chunk_backup_dir)
            self.asset_storage.discard_path(backup.tile_backup_dir)

        return MapUploadResult(
            success=True,
            tile_count=sum(len(staged.tiles) for staged in staged_layers),
            chunk_count=sum(len(staged.chunks) for staged in staged_layers),
        )

    def _retile_in_place(
        self,
        *,
        scene_id: str,
        raster_layers: list[dict],
        image,
        dimensions: SceneDimensions,
    ) -> MapUploadResult:
        for layer in raster_layers:
            self._clear_raster_layer_artifacts(scene_id=scene_id, layer_id=layer["id"])

        total_tiles = 0
        total_chunks = 0
        try:
            for layer in raster_layers:
                tile_refs = self._write_tiles_sync(
                    scene_id=scene_id,
                    layer_id=layer["id"],
                    image=image,
                    dimensions=dimensions,
                )
                chunk_count = self._write_chunks_internal(
                    scene_id=scene_id,
                    layer_id=layer["id"],
                    dimensions=dimensions,
                    tile_refs=tile_refs,
                )
                self.layers.update_metadata(
                    layer_id=layer["id"],
                    name=layer["name"],
                    visibility=SceneLayerVisibility(layer["visibility"]),
                    display_order=layer["display_order"],
                    tile_table_version=layer["tile_table_version"] + 1,
                )
                total_tiles += len(tile_refs)
                total_chunks += chunk_count
        except Exception:
            for layer in raster_layers:
                try:
                    self._clear_raster_layer_artifacts(scene_id=scene_id, layer_id=layer["id"])
                except Exception:
                    pass
            return MapUploadResult(success=False, error_key="game.maps.errors.processing_failed")

        return MapUploadResult(success=True, tile_count=total_tiles, chunk_count=total_chunks)

    def _render_tiles(
        self,
        *,
        scene_id: str,
        layer: dict,
        image,
        dimensions: SceneDimensions,
    ) -> _StagedRetileLayer:
        """Render a layer into disk staging directories only.

        The returned metadata references final storage paths, but the files still
        live in staging until promotion. This keeps peak memory bounded by a
        single tile/chunk rather than the entire map.
        """
        tile_stage_dir = self.asset_storage.create_layer_tiles_staging(
            scene_id=scene_id,
            layer_id=layer["id"],
        )
        chunk_stage_dir = self.chunk_storage.create_layer_chunks_staging(
            scene_id=scene_id,
            layer_id=layer["id"],
        )
        staged_tiles: list[_StagedRetileTile] = []
        tile_refs: dict[tuple[int, int], int] = {}
        tile_ref = 1

        try:
            for ty in range(dimensions.tile_rows):
                for tx in range(dimensions.tile_columns):
                    left = tx * dimensions.tile_size
                    upper = ty * dimensions.tile_size
                    right = min(left + dimensions.tile_size, dimensions.width)
                    lower = min(upper + dimensions.tile_size, dimensions.height)
                    tile_image = image.crop((left, upper, right, lower))

                    with BytesIO() as buffer:
                        tile_image.save(buffer, format="PNG", optimize=True)
                        data = buffer.getvalue()

                    tile_hash = hashlib.sha256(data).hexdigest()
                    self.asset_storage.write_staged_tile_bytes(
                        staging_dir=tile_stage_dir,
                        tx=tx,
                        ty=ty,
                        data=data,
                    )
                    staged_tiles.append(
                        _StagedRetileTile(
                            tx=tx,
                            ty=ty,
                            tile_ref=tile_ref,
                            width=tile_image.width,
                            height=tile_image.height,
                            hash=tile_hash,
                            byte_size=len(data),
                            storage_path=self.asset_storage.final_tile_storage_path(
                                scene_id=scene_id,
                                layer_id=layer["id"],
                                tx=tx,
                                ty=ty,
                            ),
                        )
                    )
                    tile_refs[(tx, ty)] = tile_ref
                    tile_ref += 1

            staged_chunks: list[_StagedRetileChunk] = []
            for cy in range(dimensions.chunk_rows):
                for cx in range(dimensions.chunk_columns):
                    data = self._encode_chunk_refs(
                        cx=cx,
                        cy=cy,
                        dimensions=dimensions,
                        tile_refs=tile_refs,
                    )
                    chunk_hash = self.chunk_storage.write_staged_chunk(
                        staging_dir=chunk_stage_dir,
                        cx=cx,
                        cy=cy,
                        data=data,
                    )
                    staged_chunks.append(
                        _StagedRetileChunk(
                            cx=cx,
                            cy=cy,
                            hash=chunk_hash,
                            byte_size=len(data),
                        )
                    )

            return _StagedRetileLayer(
                layer=layer,
                tile_stage_dir=tile_stage_dir,
                chunk_stage_dir=chunk_stage_dir,
                tiles=tuple(staged_tiles),
                chunks=tuple(staged_chunks),
            )
        except Exception:
            self.asset_storage.discard_path(tile_stage_dir)
            self.chunk_storage.discard_path(chunk_stage_dir)
            raise

    def _replace_retile_metadata_atomic(
        self,
        *,
        scene_id: str,
        staged_layers: list[_StagedRetileLayer],
    ) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            for staged in staged_layers:
                layer = staged.layer
                layer_id = layer["id"]
                asset_subquery = select(scene_tiles_table.c.asset_id).where(
                    scene_tiles_table.c.layer_id == layer_id
                )
                conn.execute(delete(scene_assets_table).where(scene_assets_table.c.id.in_(asset_subquery)))
                conn.execute(delete(scene_tiles_table).where(scene_tiles_table.c.layer_id == layer_id))
                conn.execute(delete(scene_chunks_table).where(scene_chunks_table.c.layer_id == layer_id))

                for tile in staged.tiles:
                    asset_id = uuid.uuid4().hex
                    conn.execute(
                        insert(scene_assets_table).values(
                            id=asset_id,
                            scene_id=scene_id,
                            kind=SceneAssetKind.RASTER_TILE.value,
                            storage_path=tile.storage_path,
                            hash=tile.hash,
                            byte_size=tile.byte_size,
                            width=tile.width,
                            height=tile.height,
                            content_type="image/png",
                            created_at=now,
                        )
                    )
                    conn.execute(
                        insert(scene_tiles_table).values(
                            scene_id=scene_id,
                            layer_id=layer_id,
                            tile_ref=tile.tile_ref,
                            asset_id=asset_id,
                            tx=tile.tx,
                            ty=tile.ty,
                            width=tile.width,
                            height=tile.height,
                            hash=tile.hash,
                            byte_size=tile.byte_size,
                            created_at=now,
                        )
                    )

                for chunk in staged.chunks:
                    conn.execute(
                        insert(scene_chunks_table).values(
                            id=uuid.uuid4().hex,
                            scene_id=scene_id,
                            layer_id=layer_id,
                            cx=chunk.cx,
                            cy=chunk.cy,
                            version=1,
                            hash=chunk.hash,
                            byte_size=chunk.byte_size,
                            encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1.value,
                            created_at=now,
                            updated_at=now,
                        )
                    )

                conn.execute(
                    update(scene_layers_table)
                    .where(scene_layers_table.c.id == layer_id)
                    .values(
                        name=layer["name"],
                        visibility=layer["visibility"],
                        display_order=layer["display_order"],
                        tile_table_version=int(layer["tile_table_version"]) + 1,
                        updated_at=now,
                    )
                )

            if staged_layers:
                conn.execute(
                    update(scenes_table)
                    .where(scenes_table.c.id == scene_id)
                    .values(scene_epoch=scenes_table.c.scene_epoch + 1, updated_at=now)
                )

    def _discard_staged_layer(self, staged: _StagedRetileLayer) -> None:
        self.asset_storage.discard_path(staged.tile_stage_dir)
        self.chunk_storage.discard_path(staged.chunk_stage_dir)

    def _clear_raster_layer_artifacts(self, *, scene_id: str, layer_id: str) -> None:
        self.assets.delete_tile_assets_by_layer(layer_id)
        self.tiles.delete_by_layer(layer_id)
        self.chunk_storage.delete_layer_chunks(scene_id=scene_id, layer_id=layer_id)
        self.chunk_service.chunks.delete_by_layer(layer_id)
        self.asset_storage.delete_layer_tiles(scene_id=scene_id, layer_id=layer_id)

    def _write_chunks_internal(
        self,
        *,
        scene_id: str,
        layer_id: str,
        dimensions: SceneDimensions,
        tile_refs: dict[tuple[int, int], int],
    ) -> int:
        chunk_count = 0
        for cy in range(dimensions.chunk_rows):
            for cx in range(dimensions.chunk_columns):
                data = self._encode_chunk_refs(
                    cx=cx,
                    cy=cy,
                    dimensions=dimensions,
                    tile_refs=tile_refs,
                )
                chunk_hash = self.chunk_storage.write_chunk(
                    scene_id=scene_id,
                    layer_id=layer_id,
                    cx=cx,
                    cy=cy,
                    data=data,
                )
                self.chunk_service.chunks.record_write(
                    scene_id=scene_id,
                    layer_id=layer_id,
                    cx=cx,
                    cy=cy,
                    hash=chunk_hash,
                    byte_size=len(data),
                    encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
                )
                chunk_count += 1
        return chunk_count

    def _validate_permissions(
        self,
        *,
        campaign_id: str,
        user_id: str,
    ) -> MapUploadResult | None:
        if not self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.MAP_UPLOAD,
        ):
            return MapUploadResult(
                success=False,
                error_key="permissions.errors.denied",
            )

        if not self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.SCENE_CREATE,
        ):
            return MapUploadResult(
                success=False,
                error_key="permissions.errors.denied",
            )

        return None

    def _validate_upload_metadata(
        self,
        *,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> MapUploadResult | None:
        if not data:
            return MapUploadResult(
                success=False,
                error_key="game.maps.errors.empty_file",
            )

        if len(data) > MAX_UPLOAD_BYTES:
            return MapUploadResult(
                success=False,
                error_key="game.maps.errors.file_too_large",
            )

        if content_type not in ALLOWED_CONTENT_TYPES:
            return MapUploadResult(
                success=False,
                error_key="game.maps.errors.unsupported_type",
            )

        if not any(filename.lower().endswith(extension) for extension in ALLOWED_EXTENSIONS):
            return MapUploadResult(
                success=False,
                error_key="game.maps.errors.unsupported_type",
            )

        return None

    def _validate_dimensions(
        self,
        *,
        width: int,
        height: int,
        tile_size: int,
        chunk_size: int,
    ) -> SceneDimensions:
        if tile_size < MIN_TILE_SIZE or tile_size > MAX_TILE_SIZE:
            raise ValueError("tile_size out of range")

        if chunk_size != SCENE_NATIVE_CHUNK_SIZE:
            raise ValueError("chunk_size must use native scene chunk size")

        if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
            raise ValueError("image dimensions out of range")

        dimensions = SceneDimensions(
            width=width,
            height=height,
            tile_size=tile_size,
            chunk_size=chunk_size,
        )

        tile_count = dimensions.tile_columns * dimensions.tile_rows

        if tile_count > MAX_TILE_COUNT or tile_count > UINT32_MAX:
            raise ValueError("tile count out of range")

        return dimensions

    def _persist_tile(
        self,
        *,
        scene_id: str,
        layer_id: str,
        image,
        dimensions: SceneDimensions,
        tx: int,
        ty: int,
        tile_ref: int,
    ) -> None:
        left = tx * dimensions.tile_size
        upper = ty * dimensions.tile_size
        right = min(left + dimensions.tile_size, dimensions.width)
        lower = min(upper + dimensions.tile_size, dimensions.height)
        tile_image = image.crop((left, upper, right, lower))
        storage_path, tile_data = self.asset_storage.write_tile_png(
            scene_id=scene_id,
            layer_id=layer_id,
            tx=tx,
            ty=ty,
            image=tile_image,
        )
        tile_hash = hashlib.sha256(tile_data).hexdigest()
        asset = self.assets.create(
            scene_id=scene_id,
            kind=SceneAssetKind.RASTER_TILE,
            storage_path=storage_path,
            hash=tile_hash,
            byte_size=len(tile_data),
            width=tile_image.width,
            height=tile_image.height,
            content_type="image/png",
        )
        self.tiles.create(
            scene_id=scene_id,
            layer_id=layer_id,
            tile_ref=tile_ref,
            asset_id=asset["id"],
            tx=tx,
            ty=ty,
            width=tile_image.width,
            height=tile_image.height,
            hash=tile_hash,
            byte_size=len(tile_data),
        )

    def _write_tiles_sync(
        self,
        *,
        scene_id: str,
        layer_id: str,
        image,
        dimensions: SceneDimensions,
    ) -> dict[tuple[int, int], int]:
        tile_refs: dict[tuple[int, int], int] = {}
        tile_ref = 1

        for ty in range(dimensions.tile_rows):
            for tx in range(dimensions.tile_columns):
                self._persist_tile(
                    scene_id=scene_id,
                    layer_id=layer_id,
                    image=image,
                    dimensions=dimensions,
                    tx=tx,
                    ty=ty,
                    tile_ref=tile_ref,
                )
                tile_refs[(tx, ty)] = tile_ref
                tile_ref += 1

        return tile_refs

    async def _write_tiles(
        self,
        *,
        scene_id: str,
        layer_id: str,
        image,
        dimensions: SceneDimensions,
        reporter: _UploadProgressReporter,
    ) -> dict[tuple[int, int], int]:
        tile_refs: dict[tuple[int, int], int] = {}
        tile_ref = 1
        tile_total = dimensions.tile_columns * dimensions.tile_rows
        step = max(1, tile_total // _TILING_REPORT_STEPS)
        processed = 0

        for ty in range(dimensions.tile_rows):
            for tx in range(dimensions.tile_columns):
                self._persist_tile(
                    scene_id=scene_id,
                    layer_id=layer_id,
                    image=image,
                    dimensions=dimensions,
                    tx=tx,
                    ty=ty,
                    tile_ref=tile_ref,
                )
                tile_refs[(tx, ty)] = tile_ref
                tile_ref += 1
                processed += 1

                if processed % step == 0:
                    await reporter.report(
                        phase=UPLOAD_PHASE_TILING,
                        done_units=processed,
                    )

        return tile_refs

    async def _write_chunks(
        self,
        *,
        scene_id: str,
        layer_id: str,
        user_id: str,
        dimensions: SceneDimensions,
        tile_refs: dict[tuple[int, int], int],
        reporter: _UploadProgressReporter | None = None,
        done_offset: int = 0,
    ) -> int:
        chunk_count = 0
        chunk_total = dimensions.chunk_columns * dimensions.chunk_rows
        step = max(1, chunk_total // _CHUNKING_REPORT_STEPS)

        for cy in range(dimensions.chunk_rows):
            for cx in range(dimensions.chunk_columns):
                data = self._encode_chunk_refs(
                    cx=cx,
                    cy=cy,
                    dimensions=dimensions,
                    tile_refs=tile_refs,
                )
                result = await self.chunk_service.write_chunk(
                    scene_id=scene_id,
                    layer_id=layer_id,
                    cx=cx,
                    cy=cy,
                    data=data,
                    user_id=user_id,
                    encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
                )

                if not result.success:
                    raise RuntimeError(result.error_key or "chunk write failed")

                chunk_count += 1

                if reporter is not None and chunk_count % step == 0:
                    await reporter.report(
                        phase=UPLOAD_PHASE_CHUNKING,
                        done_units=done_offset + chunk_count,
                    )

        return chunk_count

    def _encode_chunk_refs(
        self,
        *,
        cx: int,
        cy: int,
        dimensions: SceneDimensions,
        tile_refs: dict[tuple[int, int], int],
    ) -> bytes:
        refs = []

        for local_y in range(dimensions.chunk_size):
            for local_x in range(dimensions.chunk_size):
                tx = cx * dimensions.chunk_size + local_x
                ty = cy * dimensions.chunk_size + local_y
                refs.append(tile_refs.get((tx, ty), EMPTY_TILE_REF))

        return encode_uint32_tile_refs(refs)

    async def _emit_upload_events(
        self,
        *,
        transport: RealtimeGatewayContract,
        campaign_id: str,
        scene: Row,
        layer: Row,
        dimensions: SceneDimensions,
    ) -> None:
        await transport.to_room(
            room_id=campaign_id,
            event=TransportEvent.SCENE_CREATED,
            payload={
                "room_id": campaign_id,
                "scene_id": scene["id"],
                "name": scene["name"],
                "width": dimensions.width,
                "height": dimensions.height,
                "tile_size": dimensions.tile_size,
                "chunk_size": dimensions.chunk_size,
            },
        )
        await transport.to_room(
            room_id=campaign_id,
            event=TransportEvent.SCENE_LAYER_CREATED,
            payload={
                "room_id": campaign_id,
                "scene_id": scene["id"],
                "layer_id": layer["id"],
                "name": layer["name"],
                "kind": layer["kind"],
                "visibility": layer["visibility"],
                "order": layer["display_order"],
                "encoding": layer["encoding"],
            },
        )
