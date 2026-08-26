"""HTTP surface for the Item + Item Sheet Data commands (Gravewright SDK).

Mirrors :mod:`manage_actors` but for standalone items: JSON command endpoints
plus the server-rendered sheet modal. Items are never on the canvas, so there is
no token refresh and no roll/action/drop surface (item sheets are field-only).
"""

from __future__ import annotations

import json
from app.persistence.rows import Row
from typing import Any

from litestar import Request, get, post
from litestar.params import FromPath
from litestar.response import Redirect, Response, Template

from app.config import config
from app.engine.items.item_service import ItemResult, ItemService
from app.engine.items.item_permissions import can_view_item
from app.persistence.repositories.item_repository import ItemRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.engine.content.content_pack_access import ContentPackAccessService
from app.engine.sdk.package_content_service import PackageContentService
from app.engine.sheets.item_sheet_data_service import ItemSheetDataResult, ItemSheetDataService
from app.engine.sheets.item_sheet_service import ItemSheetService
from app.helpers.view import view_context
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


async def _emit_item(event: TransportEvent, result: ItemResult, *, user_id: str) -> None:
    if not result.success or not result.campaign_id:
        return
    payload: dict[str, Any] = {
        "room_id": result.campaign_id,
        "item_id": result.item_id,
        "system_id": result.system_id or "",
        "updated_by": user_id,
    }
    if result.version is not None:
        payload["version"] = result.version
    item = ItemRepository().get(str(result.item_id or ""))
    members = CampaignRepository().list_members(campaign_id=result.campaign_id)
    audience = [member["user_id"] for member in members if item and can_view_item(item=item, campaign={"member_role": member["role"]}, user_id=member["user_id"])]
    await RealtimeTransport().to_players(player_ids=audience, event=event, payload=payload)


@post("/game/item")
async def create_item(
    request: Request, cookies: dict[str, str], current_user: Row, item_service: ItemService
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    result = item_service.create_item(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=user["id"],
        system_id=str(body.get("system_id", "")),
        item_type=str(body.get("type", "")),
        name=str(body.get("name", "")),
        folder_id=str(body.get("folder_id", "")),
    )
    await _emit_item(TransportEvent.ITEM_CREATED, result, user_id=user["id"])
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response(
        {"item_id": result.item_id, "system_id": result.system_id, "version": result.version},
        status_code=201,
    )


@post("/game/item/update-core")
async def update_item_core(
    request: Request, cookies: dict[str, str], current_user: Row, item_service: ItemService
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    result = item_service.update_core(
        item_id=str(body.get("item_id", "")),
        user_id=user["id"],
        name=str(body.get("name", "")),
        folder_id=str(body["folder_id"]) if "folder_id" in body else None,
        portrait_asset_id=(
            str(body["portrait_asset_id"]) if "portrait_asset_id" in body else None
        ),
    )
    await _emit_item(TransportEvent.ITEM_UPDATED, result, user_id=user["id"])
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response({"item_id": result.item_id, "version": result.version}, status_code=200)


@post("/game/item/delete")
async def delete_item(
    request: Request, cookies: dict[str, str], current_user: Row, item_service: ItemService
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    result = item_service.delete_item(item_id=str(body.get("item_id", "")), user_id=user["id"])
    await _emit_item(TransportEvent.ITEM_DELETED, result, user_id=user["id"])
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response({"ok": True}, status_code=200)


@get("/game/item/sheet/modal/{item_id:str}")
async def show_item_sheet_modal(
    item_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    item_sheet_service: ItemSheetService,
) -> Redirect | Template:
    user = current_user
    base_context = view_context(cookies)
    bundle = item_sheet_service.build_bundle(
        item_id=item_id,
        user_id=user["id"],
        locale=base_context["locale"],
    )
    if bundle is None:
        return Redirect(path="/game")
    member_role = item_sheet_service.get_member_role(
        campaign_id=bundle.campaign_id, user_id=user["id"]
    )
    context = {
        **base_context,
        "item": bundle,
        "bundle_json": json.dumps(item_sheet_service.to_dict(bundle), separators=(",", ":")),
        "room_id": bundle.campaign_id,
        "is_gm": member_role == "gm",
        "targeted_handouts_enabled": config.targeted_handouts_enabled,
    }
    return Template(template_name="pages/game/_item_sheet_modal.html", context=context)


@get("/game/item/{item_id:str}/sheet-bundle")
async def get_item_sheet_bundle(
    item_id: FromPath[str],
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    item_sheet_service: ItemSheetService,
) -> Response[dict[str, Any]]:
    user = current_user
    locale = view_context(cookies)["locale"]
    bundle = item_sheet_service.build_bundle(item_id=item_id, user_id=user["id"], locale=locale)
    if bundle is None:
        return Response({"error_key": "game.items.errors.not_found"}, status_code=404)
    return Response(item_sheet_service.to_dict(bundle), status_code=200)


@get("/game/item/{item_id:str}/sheet-data")
async def get_item_sheet_data(
    item_id: FromPath[str],
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    item_sheet_data_service: ItemSheetDataService,
) -> Response[dict[str, Any]]:
    user = current_user
    result = item_sheet_data_service.get_data(item_id=item_id, user_id=user["id"])
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response(
        {
            "item_id": result.item_id,
            "system_id": result.system_id,
            "version": result.version,
            "data": result.data or {},
        },
        status_code=200,
    )


async def _emit_item_sheet_data(result: ItemSheetDataResult, *, user_id: str) -> None:
    if not result.success or not result.campaign_id:
        return
    await RealtimeTransport().to_room(
        room_id=result.campaign_id,
        event=TransportEvent.SHEET_DATA_UPDATED,
        payload={
            "room_id": result.campaign_id,
            "system_id": result.system_id or "",
            "item_id": result.item_id,
            "version": result.version or 0,
            "updated_by": user_id,
            "changed_paths": result.changed_paths,
        },
    )


@post("/game/item/sheet-data/patch")
async def patch_item_sheet_data(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    item_sheet_data_service: ItemSheetDataService,
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    patch = body.get("patch")
    result = item_sheet_data_service.patch_data(
        item_id=str(body.get("item_id", "")),
        user_id=user["id"],
        patch=patch if isinstance(patch, dict) else {},
    )
    await _emit_item_sheet_data(result, user_id=user["id"])
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response(
        {
            "item_id": result.item_id,
            "version": result.version,
            "changed_paths": result.changed_paths,
        },
        status_code=200,
    )


@post("/game/item/sheet-data/set")
async def set_item_sheet_data(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    item_sheet_data_service: ItemSheetDataService,
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    data = body.get("data")
    result = item_sheet_data_service.set_data(
        item_id=str(body.get("item_id", "")),
        user_id=user["id"],
        data=data if isinstance(data, dict) else {},
    )
    await _emit_item_sheet_data(result, user_id=user["id"])
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response({"item_id": result.item_id, "version": result.version}, status_code=200)


@post("/game/item/content/import")
async def import_item_content(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    package_content_service: PackageContentService,
    content_pack_access: ContentPackAccessService,
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id", ""))
    package_id = str(body.get("package_id") or body.get("system_id") or "")
    pack_id = str(body.get("pack_id", ""))
    # Mesmo contrato do import de ator: trazer para a mesa exige `owner`.
    if not content_pack_access.can_import(
        campaign_id=campaign_id, package_id=package_id, pack_id=pack_id, user_id=user["id"]
    ):
        return Response({"error_key": "permissions.errors.denied"}, status_code=403)
    result = package_content_service.import_entry(
        campaign_id=campaign_id,
        user_id=user["id"],
        package_id=package_id,
        pack_id=pack_id,
        entry_id=str(body.get("entry_id", "")),
        folder_id=str(body.get("folder_id") or ""),
    )
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    if result.campaign_id and result.item_id:
        await RealtimeTransport().to_room(
            room_id=result.campaign_id,
            event=TransportEvent.ITEM_CREATED,
            payload={
                "room_id": result.campaign_id,
                "item_id": result.item_id,
                "system_id": result.system_id or "",
                "updated_by": user["id"],
            },
        )
    return Response({"item_id": result.item_id}, status_code=201)
