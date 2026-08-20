from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from app.persistence.rows import Row
from typing import Annotated
from urllib.parse import quote

from litestar import Request
from litestar import get
from litestar import post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.params import FromPath
from litestar.response import Redirect
from litestar.response import Response
from litestar.response import Template

from app.business.game_page_service import GamePageService
from app.helpers.view import view_context
from app.domain.scenes import SceneVisibility
from app.domain.scenes import SCENE_NATIVE_CHUNK_SIZE
from app.engine.scenes.map_upload_service import MapUploadService
from app.engine.scenes.scene_service import SceneService
from app.engine.scenes.scene_service import effective_darkness
from app.engine.scenes.scene_service import normalized_lighting_mode
from app.config import config
from app.realtime.transport import RealtimeTransport


HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


@dataclass
class CreateSceneGroupForm:
    campaign_id: str = ""
    name: str = ""
    color: str = "#8ea8ff"


@dataclass
class ActivateSceneForm:
    campaign_id: str = ""
    scene_id: str = ""


@dataclass
class UpdateSceneForm:
    campaign_id: str = ""
    scene_id: str = ""
    name: str = ""
    group_id: str = ""
    visibility: str = SceneVisibility.PLAYERS.value
    grid_visible: str = ""
    grid_color: str = "#6fddb4"
    grid_opacity: str = "0.4"
    tile_size: str = ""
    image_scale: str = ""


@dataclass
class DeleteSceneForm:
    campaign_id: str = ""
    scene_id: str = ""


@dataclass
class UpdateSceneStartPointForm:
    campaign_id: str = ""
    scene_id: str = ""
    start_world_x: str = ""
    start_world_y: str = ""
    start_zoom: str = ""


def _scene_modal_id(campaign_id: str | None) -> str:
    return f"panel-scenes-{campaign_id}" if campaign_id else ""


def _redirect_error(error_key: str, *, campaign_id: str | None = None) -> Redirect:
    path = f"/game?scenes_error_key={quote(error_key)}"
    modal_id = _scene_modal_id(campaign_id)

    if modal_id:
        path = f"{path}&open_modal={quote(modal_id)}"

    return Redirect(path=path)


def _redirect_message(message_key: str, *, campaign_id: str | None = None) -> Redirect:
    path = f"/game?scenes_message_key={quote(message_key)}"
    modal_id = _scene_modal_id(campaign_id)

    if modal_id:
        path = f"{path}&open_modal={quote(modal_id)}"

    return Redirect(path=path)


def _valid_color(color: str, fallback: str) -> str:
    normalized = color.strip()

    if HEX_COLOR_RE.match(normalized):
        return normalized.lower()

    return fallback


def _clamp_opacity(value: str, fallback: float) -> float:
    try:
        opacity = float(value)
    except (ValueError, TypeError):
        return fallback

    return round(max(0.0, min(1.0, opacity)), 2)


def _parse_visibility(value: str) -> SceneVisibility:
    try:
        return SceneVisibility(value)
    except ValueError:
        return SceneVisibility.PLAYERS


def _parse_int(value: object) -> int:
    try:
        return int(str(value or "0"))
    except ValueError:
        return 0


def _parse_float(value: object, fallback: float) -> float:
    try:
        return float(str(value or "").strip())
    except (TypeError, ValueError):
        return fallback


async def _read_upload_file(upload: object) -> bytes:
    read = getattr(upload, "read", None)

    if read is None:
        return b""

    data = read()

    if inspect.isawaitable(data):
        data = await data

    return data


def _upload_filename(upload: object) -> str:
    return str(getattr(upload, "filename", "") or "")


def _upload_content_type(upload: object) -> str:
    return str(getattr(upload, "content_type", "") or "")


@post("/game/scenes/group")
async def create_scene_group(
    cookies: dict[str, str],
    current_user: Row,
    scene_service: SceneService,
    data: Annotated[CreateSceneGroupForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    user = current_user

    result = scene_service.create_group(
        campaign_id=data.campaign_id,
        user_id=user["id"],
        name=data.name,
        color=_valid_color(data.color, "#8ea8ff"),
    )
    if not result.success:
        return _redirect_error(
            result.error_key or "permissions.errors.denied",
            campaign_id=data.campaign_id,
        )

    return _redirect_message("game.scenes.groups.created", campaign_id=data.campaign_id)


@post("/game/scenes/activate")
async def activate_scene(
    cookies: dict[str, str],
    current_user: Row,
    scene_service: SceneService,
    data: Annotated[ActivateSceneForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    user = current_user

    result = await scene_service.activate_scene(
        scene_id=data.scene_id,
        user_id=user["id"],
        transport=RealtimeTransport(),
    )

    if not result.success:
        return _redirect_error(
            result.error_key or "game.scenes.errors.not_found",
            campaign_id=data.campaign_id,
        )

    return _redirect_message("game.scenes.activated", campaign_id=data.campaign_id)


@post("/game/scenes/update")
async def update_scene(
    cookies: dict[str, str],
    current_user: Row,
    scene_service: SceneService,
    map_upload_service: MapUploadService,
    data: Annotated[UpdateSceneForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    user = current_user

    scene_result = scene_service.get_scene_for_management(
        scene_id=data.scene_id, user_id=user["id"]
    )
    if scene_result.scene is None:
        return _redirect_error("game.scenes.errors.not_found", campaign_id=data.campaign_id)
    scene = scene_result.scene
    if not scene_result.success:
        return _redirect_error("permissions.errors.denied", campaign_id=scene["campaign_id"])

    normalized_name = " ".join(data.name.strip().split())

    if len(normalized_name) < 2:
        return _redirect_error("game.scenes.errors.invalid_name", campaign_id=scene["campaign_id"])

    group_id = scene_service.normalize_group_id(
        group_id=data.group_id.strip() or None,
        campaign_id=scene["campaign_id"],
    )

    current_grid_size = scene.get("grid_size") or scene["tile_size"]
    new_grid_size = _parse_int(data.tile_size) if data.tile_size.strip() else current_grid_size
    if new_grid_size < 8:
        new_grid_size = current_grid_size

    raw_scale = data.image_scale.strip()
    try:
        new_image_scale = (
            round(float(raw_scale), 4) if raw_scale else float(scene["image_scale"] or 1.0)
        )
    except (ValueError, IndexError):
        new_image_scale = 1.0
    new_image_scale = max(0.1, min(10.0, new_image_scale))

    scene_service.update_scene_metadata(
        scene_id=data.scene_id,
        name=normalized_name,
        group_id=group_id,
        visibility=_parse_visibility(data.visibility),
        grid_visible=data.grid_visible == "on",
        grid_color=_valid_color(data.grid_color, "#6fddb4"),
        grid_opacity=_clamp_opacity(data.grid_opacity, 0.4),
        darkness=None,
        tile_size=scene["tile_size"],
        grid_size=new_grid_size,
        image_scale=new_image_scale,
        tile_table_version=scene["tile_table_version"],
    )



    await scene_service.broadcast_scene_update(
        scene_id=data.scene_id,
        transport=RealtimeTransport(),
    )

    return _redirect_message("game.scenes.updated", campaign_id=scene["campaign_id"])


@get("/game/scenes/panel/{campaign_id:str}")
async def scenes_panel_fragment(
    campaign_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    game_page_service: GamePageService,
) -> Redirect | Template:
    """Arvore do painel de cenas, buscada pelo cliente para atualizar em lugar
    depois de uma mutacao -- o mesmo contrato do fragmento de atores."""
    room = next(
        (
            r
            for r in game_page_service.build_context(user_id=current_user["id"]).rooms
            if r["id"] == campaign_id
        ),
        None,
    )
    if room is None:
        return Redirect(path="/game")
    return Template(
        template_name="pages/game/_scenes_panel.html",
        context=view_context(cookies, room=room),
    )


@post("/game/scenes/move")
async def move_scene_to_group(
    request: Request,
    current_user: Row,
    scene_service: SceneService,
) -> Response:
    """Arrastar uma cena para uma pasta na biblioteca do mestre."""
    body = await request.json()
    scene_id = str(body.get("scene_id") or "")
    scene_result = scene_service.get_scene_for_management(
        scene_id=scene_id, user_id=current_user["id"]
    )
    if scene_result.scene is None:
        return Response({"error_key": "game.scenes.errors.not_found"}, status_code=404)
    if not scene_result.success:
        return Response({"error_key": "permissions.errors.denied"}, status_code=403)

    moved = scene_service.move_scene_to_group(
        scene_id=scene_id,
        group_id=str(body.get("group_id") or "") or None,
        campaign_id=scene_result.scene["campaign_id"],
    )
    if not moved:
        return Response({"error_key": "game.scenes.errors.not_found"}, status_code=404)
    return Response({"scene_id": scene_id}, status_code=200)


def _valid_group_color(value: str) -> str:
    return value if HEX_COLOR_RE.match(value or "") else "#8ea8ff"


async def _group_form(request: Request) -> dict:
    form = await request.form()
    return {k: str(form.get(k) or "") for k in ("folder_id", "campaign_id", "name", "color")}


@post("/game/scene-folder/rename")
async def rename_scene_folder(
    request: Request, current_user: Row, scene_service: SceneService
) -> Response:
    data = await _group_form(request)
    ok = scene_service.rename_group(
        group_id=data["folder_id"], name=data["name"], user_id=current_user["id"]
    )
    if not ok:
        return Response({"error_key": "permissions.errors.denied"}, status_code=403)
    return Response({"folder_id": data["folder_id"]}, status_code=200)


@post("/game/scene-folder/color")
async def set_scene_folder_color(
    request: Request, current_user: Row, scene_service: SceneService
) -> Response:
    data = await _group_form(request)
    ok = scene_service.set_group_color(
        group_id=data["folder_id"],
        color=_valid_group_color(data["color"]),
        user_id=current_user["id"],
    )
    if not ok:
        return Response({"error_key": "permissions.errors.denied"}, status_code=403)
    return Response({"folder_id": data["folder_id"]}, status_code=200)


@post("/game/scene-folder/delete")
async def delete_scene_folder(
    request: Request, current_user: Row, scene_service: SceneService
) -> Response:
    """Apaga so a pasta: as cenas dela voltam para a raiz da biblioteca."""
    data = await _group_form(request)
    ok = scene_service.delete_group(group_id=data["folder_id"], user_id=current_user["id"])
    if not ok:
        return Response({"error_key": "permissions.errors.denied"}, status_code=403)
    return Response({"folder_id": data["folder_id"]}, status_code=200)


@post("/game/scenes/lighting")
async def update_scene_lighting(
    request: Request,
    current_user: Row,
    scene_service: SceneService,
) -> Response:
    """Regime de luz da cena: visao total, iluminacao dinamica ou manual.

    A nevoa manual continua com os proprios comandos, pelo WebSocket: sair do
    modo manual dispara um fog.disable no cliente, que ja transmite para a sala
    inteira. Aqui so registramos o regime escolhido.
    """
    body = await request.json()
    scene_id = str(body.get("scene_id") or "")
    scene_result = scene_service.get_scene_for_management(
        scene_id=scene_id, user_id=current_user["id"]
    )
    scene = scene_result.scene
    if scene is None:
        return Response({"error_key": "game.scenes.errors.not_found"}, status_code=404)
    if not scene_result.success:
        return Response({"error_key": "permissions.errors.denied"}, status_code=403)

    mode = normalized_lighting_mode(body.get("mode") or scene.get("lighting_mode"))
    darkness = (
        _clamp_opacity(str(body.get("darkness")), float(scene.get("darkness") or 0.0))
        if body.get("darkness") is not None
        else None
    )
    lights_out = bool(body.get("lights_out")) if body.get("lights_out") is not None else None

    updated = scene_service.update_scene_lighting(
        scene_id=scene_id, mode=mode, darkness=darkness, lights_out=lights_out
    )
    if updated is None:
        return Response({"error_key": "game.scenes.errors.not_found"}, status_code=404)

    await scene_service.broadcast_scene_update(
        scene_id=scene_id,
        transport=RealtimeTransport(),
    )

    return Response(
        {
            "scene_id": scene_id,
            "lighting_mode": normalized_lighting_mode(updated.get("lighting_mode")),
            "darkness": float(updated.get("darkness") or 0.0),
            "lights_out": bool(updated.get("lights_out", 1)),
            "effective_darkness": effective_darkness(updated),
        },
        status_code=200,
    )


@post("/game/scenes/delete")
async def delete_scene(
    cookies: dict[str, str],
    current_user: Row,
    map_upload_service: MapUploadService,
    data: Annotated[DeleteSceneForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    user = current_user

    result = await map_upload_service.delete_scene(
        scene_id=data.scene_id,
        user_id=user["id"],
        transport=RealtimeTransport(),
    )

    if not result.success:
        return _redirect_error(
            result.error_key or "game.scenes.errors.not_found",
            campaign_id=data.campaign_id,
        )

    return _redirect_message("game.scenes.deleted", campaign_id=data.campaign_id)


@get("/game/scenes/{scene_id:str}/edit-modal")
async def scene_edit_modal(
    scene_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    scene_service: SceneService,
) -> Redirect | Template:
    user = current_user

    result = scene_service.get_edit_page(scene_id=scene_id, user_id=user["id"])
    if not result.success or result.scene is None:
        return Redirect(path="/game")
    scene = result.scene

    return Template(
        template_name="pages/game/scene_edit_modal.html",
        context=view_context(
            cookies,
            scene=scene,
            room={
                "id": scene["campaign_id"],
                "scene_groups": (result.manifest or {}).get("groups", []),
            },
        ),
    )


@post("/game/scenes/start-point")
async def update_scene_start_point(
    cookies: dict[str, str],
    current_user: Row,
    scene_service: SceneService,
    data: Annotated[UpdateSceneStartPointForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    user = current_user

    scene_result = scene_service.get_scene_for_management(
        scene_id=data.scene_id, user_id=user["id"]
    )
    if scene_result.scene is None:
        return _redirect_error("game.scenes.errors.not_found", campaign_id=data.campaign_id)
    scene = scene_result.scene
    if not scene_result.success:
        return _redirect_error("permissions.errors.denied", campaign_id=scene["campaign_id"])

    start_world_x = max(
        0.0, min(float(scene["width"]), _parse_float(data.start_world_x, scene["width"] / 2))
    )
    start_world_y = max(
        0.0, min(float(scene["height"]), _parse_float(data.start_world_y, scene["height"] / 2))
    )
    start_zoom = max(0.35, min(3.2, _parse_float(data.start_zoom, 1.0)))

    scene_service.update_scene_start_point(
        scene_id=data.scene_id,
        start_world_x=start_world_x,
        start_world_y=start_world_y,
        start_zoom=start_zoom,
    )

    return _redirect_message("game.scenes.start_point_updated", campaign_id=scene["campaign_id"])


@post(
    "/game/scenes/upload-map",
    # Multipart framing and the other form fields need a small allowance above
    # the configured map payload. The map service still enforces the exact cap.
    request_max_body_size=config.map_upload_max_bytes + 1024 * 1024,
)
async def upload_scene_map(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    scene_service: SceneService,
    map_upload_service: MapUploadService,
) -> Redirect:
    user = current_user
    form = await request.form()
    campaign_id = str(form.get("campaign_id") or "")

    upload = form.get("map_file")
    data = await _read_upload_file(upload)
    group_id = str(form.get("group_id") or "") or None
    activate_after_upload = str(form.get("activate_after_upload") or "") == "on"
    upload_id = str(form.get("upload_id") or "")[:64] or None

    group_id = scene_service.normalize_group_id(group_id=group_id, campaign_id=campaign_id)

    result = await map_upload_service.upload_raster_map(
        campaign_id=campaign_id,
        user_id=user["id"],
        name=str(form.get("name") or ""),
        filename=_upload_filename(upload),
        content_type=_upload_content_type(upload),
        data=data,
        tile_size=None,
        grid_size=_parse_int(form.get("tile_size")),
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
        group_id=group_id,
        visibility=_parse_visibility(str(form.get("visibility") or "")),
        grid_visible=str(form.get("grid_visible") or "") == "on",
        grid_color=_valid_color(str(form.get("grid_color") or ""), "#6fddb4"),
        grid_opacity=_clamp_opacity(str(form.get("grid_opacity") or ""), 0.4),
        transport=RealtimeTransport(),
        upload_id=upload_id,
    )

    if not result.success or result.scene is None:
        return _redirect_error(
            result.error_key or "game.maps.errors.invalid_image",
            campaign_id=campaign_id,
        )

    if activate_after_upload:
        await scene_service.activate_scene(
            scene_id=result.scene["id"],
            user_id=user["id"],
            transport=RealtimeTransport(),
        )

    return _redirect_message("game.maps.uploaded", campaign_id=campaign_id)
