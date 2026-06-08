from __future__ import annotations

import json

from app.persistence.rows import Row

from litestar import get
from litestar.params import FromQuery
from litestar.response import Redirect
from litestar.response import Template

from app.config import config
from app.business.game_page_service import GamePageService
from app.business.users import UserPreferenceService
from app.engine.systems.system_asset_service import SystemAssetService
from app.engine.modules.module_asset_service import ModuleAssetService
from app.helpers.view import view_context
from app.realtime.transport import websocket_manager



def _safe_json_script(value: object) -> str:
    return json.dumps(value, separators=(",", ":")).replace("</", "<\\/")


def _game_client_context(*, user: Row, rooms: list[dict], active_room_id: str) -> dict:
    active_room = next((room for room in rooms if room["id"] == active_room_id), None)
    active_scene = active_room.get("active_scene") if active_room else None
    return {
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "system_role": user["system_role"],
        },
        "campaign": (
            {
                "id": active_room["id"],
                "title": active_room["title"],
                "member_role": active_room["member_role"],
                "active_system_id": active_room.get("active_system_id"),
            }
            if active_room
            else None
        ),
        "scene": (
            {
                "id": active_scene["id"],
                "name": active_scene["name"],
                "width": active_scene["width"],
                "height": active_scene["height"],
                "tile_size": active_scene["tile_size"],
            }
            if active_scene
            else None
        ),
    }

def _module_asset_urls(module_asset_service: ModuleAssetService, *, campaign_id: str | None) -> dict[str, list]:
    """Build cache-busted URLs for module UI assets enabled in a campaign."""
    styles: list[str] = []
    scripts: list[dict] = []
    if not campaign_id:
        return {"styles": styles, "scripts": scripts}
    for entry in module_asset_service.list_enabled_assets(campaign_id=campaign_id, entrypoint="game"):
        module_id = entry["module_id"]
        version = entry["version"]
        for path in entry["styles"]:
            styles.append(f"/modules/{module_id}/asset/{path}?v={version}")
        for path in entry["scripts"]:
            src = f"/modules/{module_id}/asset/{path}?v={version}"
            scripts.append({"src": src, "type": "module" if path.endswith(".mjs") else "text/javascript"})
    return {"styles": styles, "scripts": scripts}

def _system_asset_urls(system_asset_service: SystemAssetService) -> dict[str, list[str]]:
    """Build cache-busted ``/systems/<id>/asset/<path>`` URLs for the system UI
    assets the table should load (one entry per enabled system that ships any)."""
    styles: list[str] = []
    scripts: list[str] = []
    for entry in system_asset_service.list_enabled_assets():
        system_id = entry["system_id"]
        version = entry["version"]
        for path in entry["styles"]:
            styles.append(f"/systems/{system_id}/asset/{path}?v={version}")
        for path in entry["scripts"]:
            scripts.append(f"/systems/{system_id}/asset/{path}?v={version}")
    return {"styles": styles, "scripts": scripts}


@get("/game")
async def show_game(
    cookies: dict[str, str],
    current_user: Row,
    game_page_service: GamePageService,
    user_preference_service: UserPreferenceService,
    system_asset_service: SystemAssetService,
    module_asset_service: ModuleAssetService,
    invite_error_key: FromQuery[str | None] = None,
    invite_message_key: FromQuery[str | None] = None,
    permissions_error_key: FromQuery[str | None] = None,
    permissions_message_key: FromQuery[str | None] = None,
    system_error_key: FromQuery[str | None] = None,
    system_message_key: FromQuery[str | None] = None,
    scenes_error_key: FromQuery[str | None] = None,
    scenes_message_key: FromQuery[str | None] = None,
    open_modal: FromQuery[str | None] = None,
    detached_modal: FromQuery[str | None] = None,
    room: FromQuery[str | None] = None,
) -> Redirect | Template:
    user = current_user

    ctx = game_page_service.build_context(user_id=user["id"])
    game_layout_mode = user_preference_service.get_game_layout_mode(user["id"])

                                                                            
                                                                              
    room_ids = [r["id"] for r in ctx.rooms]
    active_room_id = room if room in room_ids else (room_ids[0] if room_ids else "")

    # Reflect live WebSocket presence in the initial render so other connected
    # players show as online immediately (build_context renders everyone offline;
    # the WS snapshot otherwise only corrects this after the socket connects).
    online_by_room = await websocket_manager.connected_user_ids_by_room(room_ids)
    for ctx_room in ctx.rooms:
        online_ids = online_by_room.get(ctx_room["id"], set())
        for member in ctx_room.get("members", []):
            member["is_online"] = member["user_id"] in online_ids

    system_assets = _system_asset_urls(system_asset_service)
    module_assets = _module_asset_urls(module_asset_service, campaign_id=active_room_id or None)
    module_manifests = (
        module_asset_service.list_enabled_client_manifests(campaign_id=active_room_id, user_id=user["id"], entrypoint="game")
        if active_room_id
        else []
    )
    game_client_context = _game_client_context(user=user, rooms=ctx.rooms, active_room_id=active_room_id)

    return Template(
        template_name="pages/game/index.html",
        context=view_context(
            cookies,
            app_name=config.app_name,
            user={
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "system_role": user["system_role"],
            },
            rooms=ctx.rooms,
            active_room_id=active_room_id,
            available_systems=ctx.available_systems,
            system_styles=[*system_assets["styles"], *module_assets["styles"]],
            system_scripts=system_assets["scripts"],
            module_scripts=module_assets["scripts"],
            game_layout_mode=game_layout_mode,
            module_manifests_json=_safe_json_script(module_manifests),
            game_client_context_json=_safe_json_script(game_client_context),
            open_modal=open_modal or "",
            detached_modal=detached_modal or "",
            invite_error_key=invite_error_key,
            invite_message_key=invite_message_key,
            permissions_error_key=permissions_error_key,
            permissions_message_key=permissions_message_key,
            system_error_key=system_error_key,
            system_message_key=system_message_key,
            scenes_error_key=scenes_error_key,
            scenes_message_key=scenes_message_key,
        ),
    )
