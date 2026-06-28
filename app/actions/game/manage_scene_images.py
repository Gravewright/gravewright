from __future__ import annotations

import inspect
from typing import Any

from litestar import Request
from litestar import get
from litestar import post
from litestar.params import FromPath
from litestar.response import Response

from app.engine.scenes.scene_image_service import SceneImageService
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


async def _read_upload_file(upload: object) -> bytes:
    read = getattr(upload, "read", None)
    if read is None:
        return b""
    data = read()
    if inspect.isawaitable(data):
        data = await data
    return data


def _response(result, *, status_code: int = 200) -> Response[dict[str, Any]]:
    if not result.success:
        code = 403 if result.error_key == "permissions.errors.denied" else 400
        return Response({"error_key": result.error_key}, status_code=code)
    return Response(result.payload, status_code=status_code)


async def _broadcast_state(campaign_id: str, user_id: str) -> None:
    await RealtimeTransport().to_room(
        room_id=campaign_id,
        event=TransportEvent.SCENE_IMAGES_UPDATED,
        payload={"room_id": campaign_id, "updated_by": user_id},
    )


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


VALID_LAYERS = {"game", "gm", "composition"}


def _layer(value: Any, default: str | None = "game") -> str | None:
    return value if value in VALID_LAYERS else default


@get("/game/scene-images/state/{campaign_id:str}")
async def get_scene_images_state(
    campaign_id: FromPath[str],
    current_user: dict,
    scene_image_service: SceneImageService,
) -> Response[dict[str, Any]]:
    result = scene_image_service.get_state(campaign_id=campaign_id, user_id=current_user["id"])
    return _response(result)


@post("/game/scene-images/place")
async def place_asset_on_scene(
    request: Request,
    current_user: dict,
    scene_image_service: SceneImageService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    result = scene_image_service.place_asset(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        scene_id=str(body.get("scene_id") or ""),
        asset_id=str(body.get("asset_id") or ""),
        x=_float(body.get("x")),
        y=_float(body.get("y")),
        rotation=_float(body.get("rotation")),
        scale=_float(body.get("scale"), 0.0) or None,
        layer=_layer(body.get("layer")),
    )
    if result.success:
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result, status_code=201)


@post("/game/scene-images/upload")
async def upload_scene_image(
    request: Request,
    current_user: dict,
    scene_image_service: SceneImageService,
) -> Response[dict[str, Any]]:
    form = await request.form()
    upload = form.get("file")
    campaign_id = str(form.get("campaign_id") or "")
    result = scene_image_service.upload_and_place(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        scene_id=str(form.get("scene_id") or ""),
        x=_float(form.get("x")),
        y=_float(form.get("y")),
        filename=str(getattr(upload, "filename", "") or ""),
        content_type=str(getattr(upload, "content_type", "") or ""),
        data=await _read_upload_file(upload),
        layer=_layer(str(form.get("layer") or "game")),
    )
    if result.success:
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result, status_code=201)


@post("/game/scene-images/update")
async def update_scene_image(
    request: Request,
    current_user: dict,
    scene_image_service: SceneImageService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")

    def _opt_float(key: str) -> float | None:
        return _float(body.get(key)) if body.get(key) is not None else None

    z_index = int(body["z_index"]) if isinstance(body.get("z_index"), (int, float)) else None
    layer = _layer(body.get("layer"), default=None) if body.get("layer") is not None else None
    result = scene_image_service.update_placement(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        placement_id=str(body.get("placement_id") or ""),
        x=_opt_float("x"),
        y=_opt_float("y"),
        rotation=_opt_float("rotation"),
        scale=_opt_float("scale"),
        z_index=z_index,
        layer=layer,
    )
    if result.success:
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result)


@post("/game/scene-images/delete")
async def delete_scene_image(
    request: Request,
    current_user: dict,
    scene_image_service: SceneImageService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    result = scene_image_service.delete_placement(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        placement_id=str(body.get("placement_id") or ""),
    )
    if result.success:
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result)
