from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.business.permissions import PermissionService
from app.domain.permissions.permissions import TablePermission
from app.helpers.env import PROJECT_ROOT
from app.persistence.repositories.scene_asset_repository import SceneAssetRepository
from app.persistence.repositories.scene_repository import SceneRepository


@dataclass(frozen=True)
class SceneAssetReadResult:
    success: bool
    path: Path | None = None
    media_type: str | None = None
    error_key: str | None = None


class SceneAssetReadService:
    def __init__(
        self,
        *,
        scenes: SceneRepository | None = None,
        assets: SceneAssetRepository | None = None,
        permissions: PermissionService | None = None,
    ) -> None:
        self.scenes = scenes or SceneRepository()
        self.assets = assets or SceneAssetRepository()
        self.permissions = permissions or PermissionService()

    def get_original_image(self, *, scene_id: str, user_id: str) -> SceneAssetReadResult:
        scene = self.scenes.get_by_id(scene_id)
        if scene is None:
            return SceneAssetReadResult(success=False, error_key="not_found")

        if not self.permissions.can(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            permission=TablePermission.SCENE_VIEW,
        ):
            return SceneAssetReadResult(success=False, error_key="not_authorized")

        asset = self.assets.get_original_for_scene(scene_id)
        if asset is None:
            return SceneAssetReadResult(success=False, error_key="not_found")

        path = PROJECT_ROOT / asset["storage_path"]
        if not path.exists():
            return SceneAssetReadResult(success=False, error_key="not_found")

        return SceneAssetReadResult(
            success=True,
            path=path,
            media_type=asset["content_type"] or "image/png",
        )

    def campaign_id_for_scene(self, *, scene_id: str) -> str | None:
        scene = self.scenes.get_by_id(scene_id)
        return scene["campaign_id"] if scene is not None else None
