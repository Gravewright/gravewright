from __future__ import annotations

from litestar import get
from litestar.exceptions import NotAuthorizedException
from litestar.exceptions import NotFoundException
from litestar.params import FromPath
from litestar.response import File
from app.persistence.rows import Row

from app.engine.scenes.scene_asset_read_service import SceneAssetReadService


                                                                             
                                                                                     
@get("/game/scenes/{scene_id:str}/image")
async def serve_scene_image(
    scene_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    scene_asset_read_service: SceneAssetReadService,
) -> File:
    result = scene_asset_read_service.get_original_image(
        scene_id=scene_id,
        user_id=current_user["id"],
    )
    if result.error_key == "not_found":
        raise NotFoundException()
    if not result.success:
        raise NotAuthorizedException()
    if result.path is None:
        raise NotFoundException()

    return File(path=result.path, media_type=result.media_type or "image/png")
