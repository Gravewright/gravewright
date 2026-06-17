from __future__ import annotations

from app.persistence.rows import Row

from app.business.permissions.permission_service import PermissionService
from app.domain.permissions.permissions import TablePermission
from app.domain.scenes import SceneLayerVisibility


class SceneVisibilityService:
    def __init__(self, *, permissions: PermissionService | None = None) -> None:
        self.permissions = permissions or PermissionService()

    def can_view_layer(
        self,
        *,
        user_id: str,
        campaign_id: str,
        layer: Row,
    ) -> bool:
        if not self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.SCENE_VIEW,
        ):
            return False

        visibility = layer["visibility"]

        if visibility == SceneLayerVisibility.VISIBLE.value:
            return True

        if visibility == SceneLayerVisibility.GM_ONLY.value:
            return self.permissions.can(
                user_id=user_id,
                campaign_id=campaign_id,
                permission=TablePermission.SCENE_MANAGE,
            )

        if visibility == SceneLayerVisibility.HIDDEN.value:
            return self.permissions.can(
                user_id=user_id,
                campaign_id=campaign_id,
                permission=TablePermission.SCENE_MANAGE,
            )

        return False
