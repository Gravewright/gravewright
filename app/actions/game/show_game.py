from __future__ import annotations

import json
import secrets

from app.persistence.rows import Row

from litestar import get
from litestar.params import FromQuery
from litestar.response import Redirect
from litestar.response import Template

from app.config import config
from app.business.game_page_service import GamePageService
from app.business.users import UserPreferenceService
from app.engine.sdk.package_asset_service import PackageAssetService
from app.helpers.i18n import get_locale_from_cookies
from app.helpers.view import view_context
from app.realtime.transport import websocket_manager


def _safe_json_script(value: object) -> str:
    return json.dumps(value, separators=(",", ":")).replace("</", "<\\/")


def _game_client_context(
    *, user: Row, rooms: list[dict], active_room_id: str, package_nonces: dict[str, str]
) -> dict:
    active_room = next((room for room in rooms if room["id"] == active_room_id), None)
    active_scene = active_room.get("active_scene") if active_room else None
    return {
        # Surfaces ``window.GravewrightSDKDebug`` in the browser SDK runtime.
        # Gated on the server's debug flag so it is never exposed in production
        # (``APP_DEBUG`` must be false there). See docs/sdk/runtime.md.
        "debug": bool(config.app_debug),
        # Per-render {package_id: nonce}; the SDK validates a registering script's
        # nonce against this map. See docs/sdk/security.md.
        "packageNonces": dict(package_nonces),
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


def _package_assets(
    package_asset_service: PackageAssetService, *, campaign_id: str | None
) -> dict:
    """Flatten the active packages' declared styles/scripts for this render.

    Each script carries its owning ``package_id`` plus a fresh per-render
    ``nonce``. The browser SDK only honors a ``register({id})`` call from a
    ``<script>`` whose declared package id and nonce match what the server
    emitted, so a package script cannot register on behalf of another package
    (or be injected into the page by other code) — an explicit, testable
    upgrade over relying on ``document.currentScript.src`` alone.
    """
    styles: list[str] = []
    scripts: list[dict] = []
    nonces: dict[str, str] = {}
    if not campaign_id:
        return {"styles": styles, "scripts": scripts, "nonces": nonces}
    for entry in package_asset_service.list_assets_for_campaign(campaign_id, entrypoint="game"):
        styles.extend(entry["styles"])
        package_id = entry["package_id"]
        nonce = nonces.get(package_id) or secrets.token_urlsafe(16)
        nonces[package_id] = nonce
        for src in entry["scripts"]:
            scripts.append({"src": src, "package_id": package_id, "nonce": nonce})
    return {"styles": styles, "scripts": scripts, "nonces": nonces}


@get("/game")
async def show_game(
    cookies: dict[str, str],
    current_user: Row,
    game_page_service: GamePageService,
    user_preference_service: UserPreferenceService,
    package_asset_service: PackageAssetService,
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

    package_assets = _package_assets(package_asset_service, campaign_id=active_room_id or None)
    locale = get_locale_from_cookies(cookies)
    sdk_client_manifests = (
        package_asset_service.list_client_manifests(
            active_room_id, user_id=user["id"], entrypoint="game", locale=locale
        )
        if active_room_id
        else []
    )
    game_client_context = _game_client_context(
        user=user,
        rooms=ctx.rooms,
        active_room_id=active_room_id,
        package_nonces=package_assets["nonces"],
    )

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
            system_styles=package_assets["styles"],
            system_scripts=package_assets["scripts"],
            game_layout_mode=game_layout_mode,
            sdk_client_manifests_json=_safe_json_script(sdk_client_manifests),
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
