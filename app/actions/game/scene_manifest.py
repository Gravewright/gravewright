from __future__ import annotations

from app.persistence.rows import Row
from typing import Any

from litestar import get
from litestar.exceptions import NotAuthorizedException
from litestar.exceptions import NotFoundException
from litestar.params import FromPath
from litestar.params import Parameter
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


@get("/game/scenes/{scene_id:str}/layers/{layer_id:str}/tile-index")
async def get_scene_tile_index(
    scene_id: FromPath[str],
    layer_id: FromPath[str],
    current_user: Row,
    scene_service: SceneService,
    lod: int = Parameter(ge=0, default=0),
    tx0: int = Parameter(ge=0, default=0),
    ty0: int = Parameter(ge=0, default=0),
    tx1: int = Parameter(ge=0, default=0),
    ty1: int = Parameter(ge=0, default=0),
    limit: int = Parameter(ge=1, le=4096, default=1024),
    after_ref: int = Parameter(ge=0, default=0),
) -> Response[dict[str, Any]]:
    result = scene_service.get_scene_tile_index(
        scene_id=scene_id, layer_id=layer_id, user_id=current_user["id"], lod=lod,
        tx0=tx0, ty0=ty0, tx1=tx1, ty1=ty1, limit=limit, after_ref=after_ref,
    )
    if not result.success:
        if result.error_key == "game.scenes.errors.not_found":
            raise NotFoundException()
        raise NotAuthorizedException()
    return Response(content=result.manifest or {})
