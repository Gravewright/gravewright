from __future__ import annotations

from app.persistence.rows import Row

from litestar import get
from litestar.exceptions import NotAuthorizedException
from litestar.exceptions import NotFoundException
from litestar.params import FromPath
from litestar.response import File

from app.engine.scenes.scene_tile_read_service import SceneTileReadService


                                                                                

_TILE_CACHE_HEADERS = {"Cache-Control": "private, max-age=31536000, immutable"}


@get("/game/scenes/{scene_id:str}/layers/{layer_id:str}/tiles/{tx:int}/{ty:int}")
async def serve_scene_tile(
    scene_id: FromPath[str],
    layer_id: FromPath[str],
    tx: FromPath[int],
    ty: FromPath[int],
    cookies: dict[str, str],
    current_user: Row,
    scene_tile_read_service: SceneTileReadService,
) -> File:
    result = scene_tile_read_service.get_tile(
        scene_id=scene_id,
        layer_id=layer_id,
        tx=tx,
        ty=ty,
        user_id=current_user["id"],
        cookies=cookies,
    )
    if result.error_key == "not_authorized":
        raise NotAuthorizedException()
    if result.path is None:
        raise NotFoundException()

    return File(path=result.path, media_type=result.media_type, headers=_TILE_CACHE_HEADERS)
