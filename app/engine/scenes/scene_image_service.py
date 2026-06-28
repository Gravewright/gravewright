from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from app.engine.assets.asset_library_service import AssetLibraryService
from app.engine.assets.asset_library_service import asset_src
from app.persistence.repositories.asset_repository import AssetRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_image_repository import SceneImageRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.security.scene_image_permissions import can_delete_scene_image
from app.security.scene_image_permissions import can_move_scene_image
from app.security.scene_image_permissions import can_set_gm_layer
from app.security.scene_image_permissions import can_upload_scene_image
from app.security.scene_image_permissions import can_view_gm_layer

DEFAULT_PLACEMENT_LONG_EDGE = 180.0


def _default_scale(width: int, height: int) -> float:
    longest = max(int(width or 0), int(height or 0))
    if longest <= 0:
        return 1.0
    return max(0.05, min(20.0, DEFAULT_PLACEMENT_LONG_EDGE / float(longest)))


@dataclass(frozen=True)
class SceneImageResult:
    success: bool
    payload: dict[str, Any] = field(default_factory=dict)
    error_key: str | None = None


class SceneImageService:
    """Places and manipulates asset-library images on a scene's image layer.

    Library/folder management lives in the assets domain
    (:class:`app.engine.assets.asset_library_service.AssetLibraryService`); this
    service only consumes ready library assets by ``asset_id``.
    """

    def __init__(
        self,
        *,
        placements: SceneImageRepository | None = None,
        assets: AssetRepository | None = None,
        campaigns: CampaignRepository | None = None,
        scenes: SceneRepository | None = None,
        library: AssetLibraryService | None = None,
    ) -> None:
        self.placements = placements or SceneImageRepository()
        self.assets = assets or AssetRepository()
        self.campaigns = campaigns or CampaignRepository()
        self.scenes = scenes or SceneRepository()
        self.library = library or AssetLibraryService()

    def get_state(self, *, campaign_id: str, user_id: str) -> SceneImageResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        if role is None:
            return SceneImageResult(success=False, error_key="game.scene_images.errors.not_found")
        sees_gm_layer = can_view_gm_layer(actor_role=role)
        placements = [
            self._present(placement)
            for placement in self.placements.list_for_campaign(campaign_id=campaign_id)
            if sees_gm_layer or placement.get("layer") != "gm"
        ]
        return SceneImageResult(
            success=True,
            payload={"campaign_id": campaign_id, "placements": placements},
        )

    def upload_and_place(
        self,
        *,
        campaign_id: str,
        user_id: str,
        scene_id: str,
        x: float,
        y: float,
        filename: str,
        content_type: str,
        data: bytes,
        layer: str = "game",
    ) -> SceneImageResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        if role is None or not can_upload_scene_image(actor_role=role):
            return SceneImageResult(success=False, error_key="permissions.errors.denied")
        if not self._layer_allowed(role=role, layer=layer):
            return SceneImageResult(success=False, error_key="permissions.errors.denied")
        scene = self.scenes.get_by_id(scene_id)
        if scene is None or scene.get("campaign_id") != campaign_id:
            return SceneImageResult(success=False, error_key="game.scene_images.errors.scene_not_found")

        created = self.library.create_asset(
            campaign_id=campaign_id,
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            data=data,
        )
        if not created.success:
            return SceneImageResult(success=False, error_key=created.error_key)
        asset = created.payload["asset"]
        decoded = created.payload["decoded"]

        placement = self.placements.create(
            campaign_id=campaign_id,
            scene_id=scene_id,
            asset_id=asset["id"],
            owner_user_id=user_id,
            x=float(x),
            y=float(y),
            natural_width=decoded.width,
            natural_height=decoded.height,
            scale=_default_scale(decoded.width, decoded.height),
            layer=layer,
        )
        return SceneImageResult(success=True, payload={"placement": self._present(placement)})

    def place_asset(
        self,
        *,
        campaign_id: str,
        user_id: str,
        scene_id: str,
        asset_id: str,
        x: float,
        y: float,
        rotation: float = 0.0,
        scale: float | None = None,
        layer: str = "game",
    ) -> SceneImageResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        if role is None or not can_upload_scene_image(actor_role=role):
            return SceneImageResult(success=False, error_key="permissions.errors.denied")
        if not self._layer_allowed(role=role, layer=layer):
            return SceneImageResult(success=False, error_key="permissions.errors.denied")
        scene = self.scenes.get_by_id(scene_id)
        if scene is None or scene.get("campaign_id") != campaign_id:
            return SceneImageResult(success=False, error_key="game.scene_images.errors.scene_not_found")
        asset = self.assets.get_by_id(asset_id)
        if asset is None or asset.get("campaign_id") != campaign_id:
            return SceneImageResult(success=False, error_key="game.scene_images.errors.invalid_image")
        placement = self.placements.create(
            campaign_id=campaign_id,
            scene_id=scene_id,
            asset_id=asset_id,
            owner_user_id=user_id,
            x=float(x),
            y=float(y),
            natural_width=int(asset.get("width") or 0),
            natural_height=int(asset.get("height") or 0),
            rotation=float(rotation),
            scale=scale if scale is not None else _default_scale(int(asset.get("width") or 0), int(asset.get("height") or 0)),
            layer=layer,
        )
        return SceneImageResult(success=True, payload={"placement": self._present(placement)})

    def update_placement(
        self,
        *,
        campaign_id: str,
        user_id: str,
        placement_id: str,
        x: float | None = None,
        y: float | None = None,
        rotation: float | None = None,
        scale: float | None = None,
        z_index: int | None = None,
        layer: str | None = None,
    ) -> SceneImageResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        placement = self.placements.get(placement_id)
        if role is None:
            return SceneImageResult(success=False, error_key="permissions.errors.denied")
        if placement is None or placement.get("campaign_id") != campaign_id:
            return SceneImageResult(success=False, error_key="game.scene_images.errors.placement_not_found")
        if not can_move_scene_image(actor_user_id=user_id, actor_role=role, placement=placement):
            return SceneImageResult(success=False, error_key="permissions.errors.denied")
        if layer is not None and not self._layer_allowed(role=role, layer=layer):
            return SceneImageResult(success=False, error_key="permissions.errors.denied")
        updated = self.placements.update(
            placement_id=placement_id,
            x=x,
            y=y,
            rotation=rotation,
            scale=scale,
            z_index=z_index,
            layer=layer,
        )
        if updated is None:
            return SceneImageResult(success=False, error_key="game.scene_images.errors.placement_not_found")
        return SceneImageResult(success=True, payload={"placement": self._present(updated)})

    def delete_placement(self, *, campaign_id: str, user_id: str, placement_id: str) -> SceneImageResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        placement = self.placements.get(placement_id)
        if role is None:
            return SceneImageResult(success=False, error_key="permissions.errors.denied")
        if placement is None or placement.get("campaign_id") != campaign_id:
            return SceneImageResult(success=False, error_key="game.scene_images.errors.placement_not_found")
        if not can_delete_scene_image(actor_user_id=user_id, actor_role=role, placement=placement):
            return SceneImageResult(success=False, error_key="permissions.errors.denied")
        self.placements.delete(placement_id)
        return SceneImageResult(success=True, payload={"placement_id": placement_id})

    def _layer_allowed(self, *, role: str | None, layer: str) -> bool:
        """The GM/composition layers are GM-authored; the default game layer is open."""
        if layer == "game":
            return True
        return can_set_gm_layer(actor_role=role)

    def _role(self, *, campaign_id: str, user_id: str) -> str | None:
        return self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)

    def _present(self, placement: dict) -> dict:
        return {**placement, "src": asset_src(placement["asset_id"])}
