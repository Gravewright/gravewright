from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from app.business.permissions import PermissionService
from app.config import config
from app.domain.permissions.permissions import TablePermission
from app.engine.scenes.scene_visibility_service import SceneVisibilityService
from app.helpers.env import PROJECT_ROOT
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository


@dataclass(frozen=True)
class SceneTileReadResult:
    success: bool
    path: Path | None = None
    media_type: str = "image/png"
    error_key: str | None = None


class SceneTileReadService:
    _CACHE_TTL = 60.0
    _CACHE_MAX = 50_000

    def __init__(
        self,
        *,
        scenes: SceneRepository | None = None,
        layers: SceneLayerRepository | None = None,
        permissions: PermissionService | None = None,
        visibility: SceneVisibilityService | None = None,
    ) -> None:
        self.scenes = scenes or SceneRepository()
        self.layers = layers or SceneLayerRepository()
        self.permissions = permissions or PermissionService()
        self.visibility = visibility or SceneVisibilityService(permissions=self.permissions)
        self._auth_cache: OrderedDict[tuple[str, str, str], tuple[bool, float]] = OrderedDict()

    def get_tile(
        self,
        *,
        scene_id: str,
        layer_id: str,
        tx: int,
        ty: int,
        user_id: str,
        cookies: dict[str, str],
    ) -> SceneTileReadResult:
        if not self._can_view_tile(
            user_id=user_id,
            cookies=cookies,
            scene_id=scene_id,
            layer_id=layer_id,
        ):
            return SceneTileReadResult(success=False, error_key="not_authorized")

        if tx < 0 or ty < 0:
            return SceneTileReadResult(success=False, error_key="not_found")

        path = (
            PROJECT_ROOT
            / "storage"
            / "scenes"
            / scene_id
            / "assets"
            / "tiles"
            / layer_id
            / f"{tx}_{ty}.png"
        )
        if not path.is_file():
            return SceneTileReadResult(success=False, error_key="not_found")

        return SceneTileReadResult(success=True, path=path)

    def _can_view_tile(
        self,
        *,
        user_id: str,
        cookies: dict[str, str],
        scene_id: str,
        layer_id: str,
    ) -> bool:
        session_id = cookies.get(config.session_cookie_name, "")
        if not session_id:
            return False

        key = (session_id, scene_id, layer_id)
        now = time.monotonic()
        entry = self._auth_cache.get(key)
        if entry is not None and entry[1] > now:
            return entry[0]

        scene = self.scenes.get_by_id(scene_id)
        if scene is None:
            return False

        if not self.permissions.can(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            permission=TablePermission.SCENE_VIEW,
        ):
            self._evict_and_set(key, False, now)
            return False

        layer = self.layers.get_by_id(layer_id)
        if layer is None or layer["scene_id"] != scene_id:
            return False

        if not self.visibility.can_view_layer(
            user_id=user_id,
            campaign_id=scene["campaign_id"],
            layer=layer,
        ):
            self._evict_and_set(key, False, now)
            return False

        self._evict_and_set(key, True, now)
        return True

    def _evict_and_set(self, key: tuple[str, str, str], value: bool, now: float) -> None:
        if len(self._auth_cache) >= self._CACHE_MAX:
            self._auth_cache.popitem(last=False)
        self._auth_cache[key] = (value, now + self._CACHE_TTL)
