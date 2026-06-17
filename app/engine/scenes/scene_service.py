from __future__ import annotations

from dataclasses import dataclass
from app.persistence.rows import Row
from typing import Any

from app.business.permissions.permission_service import PermissionService
from app.contracts.transport import RealtimeGatewayContract
from app.domain.permissions.permissions import TablePermission
from app.domain.scenes import SceneDimensions
from app.domain.scenes import SceneLayerKind
from app.engine.scenes.scene_manifest_service import SceneManifestService
from app.engine.scenes.scene_visibility_service import SceneVisibilityService
from app.persistence.repositories.scene_asset_repository import SceneAssetRepository
from app.persistence.repositories.scene_group_repository import SceneGroupRepository
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.realtime.events import TransportEvent


@dataclass(frozen=True)
class SceneServiceResult:
    success: bool
    scene: Row | None = None
    scenes: list[Row] | None = None
    manifest: dict[str, Any] | None = None
    error_key: str | None = None


class SceneService:
    def __init__(
        self,
        *,
        scenes: SceneRepository | None = None,
        layers: SceneLayerRepository | None = None,
        groups: SceneGroupRepository | None = None,
        assets: SceneAssetRepository | None = None,
        permissions: PermissionService | None = None,
        visibility: SceneVisibilityService | None = None,
        manifests: SceneManifestService | None = None,
    ) -> None:
        self.scenes = scenes or SceneRepository()
        self.layers = layers or SceneLayerRepository()
        self.groups = groups or SceneGroupRepository()
        self.assets = assets or SceneAssetRepository()
        self.permissions = permissions or PermissionService()
        self.visibility = visibility or SceneVisibilityService(permissions=self.permissions)
        self.manifests = manifests or SceneManifestService(
            scenes=self.scenes,
            layers=self.layers,
            assets=self.assets,
            permissions=self.permissions,
            visibility=self.visibility,
        )

    def create_group(
        self,
        *,
        campaign_id: str,
        user_id: str,
        name: str,
        color: str,
    ) -> SceneServiceResult:
        if not (
            self.permissions.can(
                user_id=user_id,
                campaign_id=campaign_id,
                permission=TablePermission.SCENE_MANAGE,
            )
            or self.permissions.can(
                user_id=user_id,
                campaign_id=campaign_id,
                permission=TablePermission.SCENE_CREATE,
            )
        ):
            return SceneServiceResult(success=False, error_key="permissions.errors.denied")

        normalized_name = " ".join(name.strip().split())
        if len(normalized_name) < 2:
            return SceneServiceResult(
                success=False,
                error_key="game.scenes.groups.errors.invalid_name",
            )

        self.groups.create(campaign_id=campaign_id, name=normalized_name, color=color)
        return SceneServiceResult(success=True)

    def get_scene_for_management(self, *, scene_id: str, user_id: str) -> SceneServiceResult:
        scene = self.scenes.get_by_id(scene_id)
        if scene is None:
            return SceneServiceResult(success=False, error_key="game.scenes.errors.not_found")
        if not self.permissions.can(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            permission=TablePermission.SCENE_MANAGE,
        ):
            return SceneServiceResult(success=False, error_key="permissions.errors.denied")
        return SceneServiceResult(success=True, scene=scene)

    def get_edit_page(self, *, scene_id: str, user_id: str) -> SceneServiceResult:
        result = self.get_scene_for_management(scene_id=scene_id, user_id=user_id)
        if not result.success or result.scene is None:
            return result
        return SceneServiceResult(
            success=True,
            scene=result.scene,
            manifest={"groups": self.groups.list_by_campaign(result.scene["campaign_id"])},
        )

    def normalize_group_id(self, *, group_id: str | None, campaign_id: str) -> str | None:
        if not group_id:
            return None
        group = self.groups.get_by_id(group_id)
        if group is None or group["campaign_id"] != campaign_id:
            return None
        return group_id

    def update_scene_metadata(self, **kwargs: Any) -> None:
        self.scenes.update_metadata(**kwargs)

    def update_scene_start_point(self, **kwargs: Any) -> None:
        self.scenes.update_start_point(**kwargs)

    def create_scene(
        self,
        *,
        campaign_id: str,
        user_id: str,
        name: str,
        width: int,
        height: int,
        tile_size: int,
        chunk_size: int,
    ) -> SceneServiceResult:
        if not self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.SCENE_CREATE,
        ):
            return SceneServiceResult(
                success=False,
                error_key="permissions.errors.denied",
            )

        normalized_name = " ".join(name.strip().split())

        if len(normalized_name) < 2:
            return SceneServiceResult(
                success=False,
                error_key="game.scenes.errors.invalid_name",
            )

        try:
            dimensions = SceneDimensions(
                width=width,
                height=height,
                tile_size=tile_size,
                chunk_size=chunk_size,
            )
        except ValueError:
            return SceneServiceResult(
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
        )

        return SceneServiceResult(success=True, scene=scene)

    def list_scenes_for_campaign(
        self,
        *,
        campaign_id: str,
        user_id: str,
    ) -> SceneServiceResult:
        if not self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.SCENE_VIEW,
        ):
            return SceneServiceResult(
                success=False,
                error_key="permissions.errors.denied",
            )

        return SceneServiceResult(
            success=True,
            scenes=self.scenes.list_by_campaign(campaign_id),
        )

    def _scene_activation_payload(self, scene: Row) -> dict[str, Any]:
        ground_layer = next(
            (
                layer
                for layer in self.layers.list_by_scene(scene["id"])
                if layer["kind"] == SceneLayerKind.RASTER_TILE_REFS.value
            ),
            None,
        )

        return {
            "id": scene["id"],
            "name": scene["name"],
            "width": scene["width"],
            "height": scene["height"],
            "tile_size": scene["tile_size"],
            "grid_visible": bool(scene["grid_visible"]),
            "grid_color": scene["grid_color"],
            "grid_opacity": float(scene["grid_opacity"]),
            "image_scale": float(scene["image_scale"]),
            "start_world_x": float(scene["start_world_x"]),
            "start_world_y": float(scene["start_world_y"]),
            "start_zoom": float(scene["start_zoom"]),
            "layer_id": ground_layer["id"] if ground_layer else "",
            "tile_table_version": scene["tile_table_version"],
            "scene_epoch": scene["scene_epoch"],
        }

    async def activate_scene(
        self,
        *,
        scene_id: str,
        user_id: str,
        transport: RealtimeGatewayContract | None = None,
    ) -> SceneServiceResult:
        scene = self.scenes.get_by_id(scene_id)

        if scene is None:
            return SceneServiceResult(
                success=False,
                error_key="game.scenes.errors.not_found",
            )

        campaign_id = scene["campaign_id"]

        if not self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.SCENE_ACTIVATE,
        ):
            return SceneServiceResult(
                success=False,
                error_key="permissions.errors.denied",
            )

        previous_scene = self.scenes.get_active_scene(campaign_id)
        activated = self.scenes.set_active_scene(
            campaign_id=campaign_id,
            scene_id=scene_id,
        )

        if activated is None:
            return SceneServiceResult(
                success=False,
                error_key="game.scenes.errors.not_found",
            )

        if transport is not None:
            await transport.to_room(
                room_id=campaign_id,
                event=TransportEvent.SCENE_ACTIVATED,
                payload={
                    "room_id": campaign_id,
                    "scene_id": scene_id,
                    "previous_scene_id": previous_scene["id"] if previous_scene else None,
                    "scene_epoch": activated["scene_epoch"],
                    "scene": self._scene_activation_payload(activated),
                },
            )

        return SceneServiceResult(success=True, scene=activated)

    def get_scene_manifest(
        self,
        *,
        scene_id: str,
        user_id: str,
    ) -> SceneServiceResult:
        result = self.manifests.get_manifest(scene_id=scene_id, user_id=user_id)

        return SceneServiceResult(
            success=result.success,
            scene=result.scene,
            manifest=result.manifest,
            error_key=result.error_key,
        )

    def assert_user_can_view_scene(
        self,
        *,
        scene: Row,
        user_id: str,
    ) -> bool:
        return self.permissions.can(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            permission=TablePermission.SCENE_VIEW,
        )

    def assert_user_can_manage_scene(
        self,
        *,
        scene: Row,
        user_id: str,
    ) -> bool:
        return self.permissions.can(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            permission=TablePermission.SCENE_MANAGE,
        )
