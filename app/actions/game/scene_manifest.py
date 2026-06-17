from __future__ import annotations

from app.persistence.rows import Row
from typing import Any

from litestar import get
from litestar.exceptions import NotAuthorizedException
from litestar.exceptions import NotFoundException
from litestar.params import FromPath
from litestar.response import Response

from app.engine.scenes.scene_service import SceneService


@get("/game/scenes/{scene_id:str}/manifest")
async def get_scene_manifest(
    scene_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    scene_service: SceneService,
) -> Response[dict[str, Any]]:
    user = current_user
    result = scene_service.get_scene_manifest(
        scene_id=scene_id,
        user_id=user["id"],
    )

    if not result.success:
        if result.error_key == "game.scenes.errors.not_found":
            raise NotFoundException()
        raise NotAuthorizedException()

    return Response(content=result.manifest or {})
