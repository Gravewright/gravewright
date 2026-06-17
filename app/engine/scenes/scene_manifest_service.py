from __future__ import annotations

from dataclasses import dataclass
from app.persistence.rows import Row
from typing import Any

import json

from app.business.permissions.permission_service import PermissionService
from app.domain.fog import FogInitialState
from app.domain.permissions.permissions import TablePermission
from app.domain.scenes import SCENE_MANIFEST_VERSION
from app.engine.scenes.scene_visibility_service import SceneVisibilityService
from app.persistence.repositories.scene_asset_repository import SceneAssetRepository
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.scene_tile_repository import SceneTileRepository


@dataclass(frozen=True)
class SceneManifestResult:
    success: bool
    scene: Row | None = None
    manifest: dict[str, Any] | None = None
    error_key: str | None = None


class SceneManifestService:
    def __init__(
        self,
        *,
        scenes: SceneRepository | None = None,
        layers: SceneLayerRepository | None = None,
        assets: SceneAssetRepository | None = None,
        tiles: SceneTileRepository | None = None,
        permissions: PermissionService | None = None,
        visibility: SceneVisibilityService | None = None,
    ) -> None:
        self.scenes = scenes or SceneRepository()
        self.layers = layers or SceneLayerRepository()
        self.assets = assets or SceneAssetRepository()
        self.tiles = tiles or SceneTileRepository()
        self.permissions = permissions or PermissionService()
        self.visibility = visibility or SceneVisibilityService(permissions=self.permissions)

    def get_manifest(
        self,
        *,
        scene_id: str,
        user_id: str,
    ) -> SceneManifestResult:
        scene = self.scenes.get_by_id(scene_id)

        if scene is None:
            return SceneManifestResult(
                success=False,
                error_key="game.scenes.errors.not_found",
            )

        if not self.permissions.can(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            permission=TablePermission.SCENE_VIEW,
        ):
            return SceneManifestResult(
                success=False,
                error_key="permissions.errors.denied",
            )

        return SceneManifestResult(
            success=True,
            scene=scene,
            manifest=self._build_manifest(scene=scene, user_id=user_id),
        )

    def _build_manifest(self, *, scene: Row, user_id: str) -> dict[str, Any]:
        layers = [
            layer
            for layer in self.layers.list_by_scene(scene["id"])
            if self.visibility.can_view_layer(
                user_id=user_id,
                campaign_id=scene["campaign_id"],
                layer=layer,
            )
        ]
        assets = self.assets.list_by_scene(scene["id"])

        fog_enabled = bool(scene["fog_enabled"])
        fog_baseline = scene["fog_baseline"] or FogInitialState.HIDE_ALL.value
        try:
            fog_ops = json.loads(scene["fog_ops_json"] or "[]")
            if not isinstance(fog_ops, list):
                fog_ops = []
        except Exception:
            fog_ops = []

        return {
            "version": SCENE_MANIFEST_VERSION,
            "scene_id": scene["id"],
            "campaign_id": scene["campaign_id"],
            "name": scene["name"],
            "width": scene["width"],
            "height": scene["height"],
            "tile_size": scene["tile_size"],
            "grid_size": scene["tile_size"],
            "chunk_size": scene["chunk_size"],
            "start_world_x": float(scene["start_world_x"]),
            "start_world_y": float(scene["start_world_y"]),
            "start_zoom": float(scene["start_zoom"]),
            "tile_table_version": scene["tile_table_version"],
            "scene_epoch": scene["scene_epoch"],
            "layers": [
                {
                    "layer_id": layer["id"],
                    "name": layer["name"],
                    "kind": layer["kind"],
                    "visible": layer["visibility"] == "visible",
                    "visibility": layer["visibility"],
                    "order": layer["display_order"],
                    "encoding": layer["encoding"],
                    "tile_table_version": layer["tile_table_version"],
                    "tiles": [
                        {
                            "tile_ref": tile["tile_ref"],
                            "asset_id": tile["asset_id"],
                            "tx": tile["tx"],
                            "ty": tile["ty"],
                            "width": tile["width"],
                            "height": tile["height"],
                            "hash": tile["hash"],
                            "byte_size": tile["byte_size"],
                            "url": self._tile_url(scene=scene, layer=layer, tile=tile),
                        }
                        for tile in self.tiles.list_by_layer(layer["id"])
                    ],
                }
                for layer in layers
            ],
            "assets": [
                {
                    "asset_id": asset["id"],
                    "kind": asset["kind"],
                    "hash": asset["hash"],
                    "byte_size": asset["byte_size"],
                    "width": asset["width"],
                    "height": asset["height"],
                    "content_type": asset["content_type"],
                }
                for asset in assets
            ],
            "fog": {
                "enabled": fog_enabled,
                "version": int(scene["fog_version"]),
                "baseline": fog_baseline,
                "ops": fog_ops if fog_enabled else [],
            },
        }

    def _tile_url(self, *, scene: Row, layer: Row, tile: Row) -> str:
                                                                                
                                                                               
                                                                              
                                                                            
        return (
            f"/game/scenes/{scene['id']}/layers/{layer['id']}/tiles/"
            f"{tile['tx']}/{tile['ty']}?v={tile['hash']}"
        )
