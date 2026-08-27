"""HTTP surface for the Actor + Sheet Data commands (Gravewright SDK, §14).

These are JSON command endpoints (no server-rendered UI yet: the declarative
Sheet renderer is a later slice). The backend stays authoritative: it validates
permissions, applies patches, bumps versions and emits realtime events.
"""

from __future__ import annotations

import inspect
import json
from app.persistence.rows import Row
from typing import Any

from litestar import Request, get, post
from litestar.exceptions import NotAuthorizedException, NotFoundException
from litestar.params import FromPath
from litestar.response import File, Redirect, Response, Template

from app.engine.actors.actor_asset_read_service import ActorAssetReadService
from app.engine.actors.actor_asset_service import ActorAssetService
from app.engine.actors.actor_service import ActorResult, ActorService
from app.engine.actors.actor_permissions import can_view_actor
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.engine.chat.chat_service import ChatService
from app.engine.combat.combat_service import CombatService
from app.domain.roles import PlayerRole
from app.engine.content.content_pack_access import ContentPackAccessService
from app.engine.content.content_pack_service import ContentPackService
from app.engine.sdk.package_content_service import PackageContentService
from app.engine.sheets.actor_sheet_service import ActorSheetService
from app.engine.sheets.item_sheet_service import ItemSheetService
from app.engine.sheets.sheet_action_service import ActionResult, SheetActionService
from app.engine.sheets.sheet_data_service import SheetDataResult, SheetDataService
from app.engine.sheets.sheet_drop_service import SheetDropService
from app.engine.sheets.sheet_item_service import SheetItemResult, SheetItemService
from app.engine.tokens.token_instance_sheet_service import TokenSheetDataResult
from app.engine.tokens.token_service import TokenService
from app.engine.tokens.token_instance_sheet_service import TokenInstanceSheetService
from app.helpers.env import PROJECT_ROOT
from app.config import config
from app.helpers.view import view_context
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport
from app.engine.rolls.roll_presentation_service import RollPresentationService
from app.engine.rolls.roll_reroll_service import RollRerollService


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


async def _emit_actor(event: TransportEvent, result: ActorResult, *, user_id: str) -> None:
    if not result.success or not result.campaign_id:
        return
    payload: dict[str, Any] = {
        "room_id": result.campaign_id,
        "actor_id": result.actor_id,
        "system_id": result.system_id or "",
        "updated_by": user_id,
    }
    if result.version is not None:
        payload["version"] = result.version
    actor = ActorRepository().get(str(result.actor_id or ""))
    members = CampaignRepository().list_members(campaign_id=result.campaign_id)
    audience = [member["user_id"] for member in members if actor and can_view_actor(actor=actor, campaign={"member_role": member["role"]}, user_id=member["user_id"])]
    await RealtimeTransport().to_players(player_ids=audience, event=event, payload=payload)


@post("/game/actor")
async def create_actor(
    request: Request, cookies: dict[str, str], current_user: Row, actor_service: ActorService
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    result = actor_service.create_actor(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=user["id"],
        system_id=str(body.get("system_id", "")),
        actor_type=str(body.get("type", "")),
        name=str(body.get("name", "")),
        folder_id=str(body.get("folder_id", "")),
    )
    await _emit_actor(TransportEvent.ACTOR_CREATED, result, user_id=user["id"])
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response(
        {"actor_id": result.actor_id, "system_id": result.system_id, "version": result.version},
        status_code=201,
    )


@post("/game/actor/update-core")
async def update_actor_core(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    actor_service: ActorService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    result = actor_service.update_core(
        actor_id=str(body.get("actor_id", "")),
        user_id=user["id"],
        name=str(body.get("name", "")),
        folder_id=str(body["folder_id"]) if "folder_id" in body else None,
        portrait_asset_id=(
            str(body["portrait_asset_id"]) if "portrait_asset_id" in body else None
        ),
        token_asset_id=str(body["token_asset_id"]) if "token_asset_id" in body else None,
    )
    await _emit_actor(TransportEvent.ACTOR_UPDATED, result, user_id=user["id"])
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    await _refresh_actor_tokens(
        campaign_id=result.campaign_id,
        actor_id=result.actor_id,
        token_service=token_service,
    )
    return Response({"actor_id": result.actor_id, "version": result.version}, status_code=200)


@post("/game/actor/{actor_id:str}/image/{kind:str}")
async def upload_actor_image(
    actor_id: FromPath[str],
    kind: FromPath[str],
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    actor_asset_service: ActorAssetService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    form = await request.form()
    upload = form.get("image")
    result = actor_asset_service.upload_image(
        actor_id=actor_id,
        user_id=current_user["id"],
        kind=kind,
        filename=str(getattr(upload, "filename", "") or ""),
        content_type=str(getattr(upload, "content_type", "") or ""),
        data=await _read_upload_file(upload),
    )
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)

    await RealtimeTransport().to_room(
        room_id=result.campaign_id or "",
        event=TransportEvent.ACTOR_UPDATED,
        payload={
            "room_id": result.campaign_id or "",
            "actor_id": result.actor_id,
            "updated_by": current_user["id"],
        },
    )
    await _refresh_actor_tokens(
        campaign_id=result.campaign_id,
        actor_id=result.actor_id,
        token_service=token_service,
    )
    return Response({"url": result.url}, status_code=201)


@get("/game/actor/{actor_id:str}/image/{kind:str}")
async def serve_actor_image(
    actor_id: FromPath[str],
    kind: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    actor_asset_read_service: ActorAssetReadService,
) -> File:
    result = actor_asset_read_service.get_image(
        actor_id=actor_id,
        user_id=current_user["id"],
        kind=kind,
        project_root=PROJECT_ROOT,
    )
    if result.error_key == "not_found":
        raise NotFoundException()
    if not result.success:
        raise NotAuthorizedException()
    if result.path is None or result.media_type is None:
        raise NotFoundException()

    return File(path=result.path, media_type=result.media_type)


@post("/game/actor/delete")
async def delete_actor(
    request: Request, cookies: dict[str, str], current_user: Row, actor_service: ActorService
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    result = actor_service.delete_actor(actor_id=str(body.get("actor_id", "")), user_id=user["id"])
    await _emit_actor(TransportEvent.ACTOR_DELETED, result, user_id=user["id"])
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response({"ok": True}, status_code=200)


@get("/game/actor/sheet/modal/{actor_id:str}")
async def show_actor_sheet_modal(
    actor_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    actor_sheet_service: ActorSheetService,
) -> Redirect | Template:
    user = current_user
    base_context = view_context(cookies)
    bundle = actor_sheet_service.build_bundle(
        actor_id=actor_id,
        user_id=user["id"],
        locale=base_context["locale"],
    )
    if bundle is None:
        return Redirect(path="/game")
    member_role = actor_sheet_service.get_member_role(
        campaign_id=bundle.campaign_id, user_id=user["id"]
    )
    context = {
        **base_context,
        "actor": bundle,
        "actor_core_version": (ActorRepository().get(bundle.actor_id) or {}).get("version", 0),
        "bundle_json": json.dumps(actor_sheet_service.to_dict(bundle), separators=(",", ":")),
        "room_id": bundle.campaign_id,
        "is_gm": member_role == "gm",
    }
    return Template(template_name="pages/game/_actor_sheet_modal.html", context=context)


@get("/game/actor/{actor_id:str}/sheet-bundle")
async def get_sheet_bundle(
    actor_id: FromPath[str],
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    actor_sheet_service: ActorSheetService,
) -> Response[dict[str, Any]]:
    user = current_user
    locale = view_context(cookies)["locale"]
    bundle = actor_sheet_service.build_bundle(actor_id=actor_id, user_id=user["id"], locale=locale)
    if bundle is None:
        return Response({"error_key": "game.actors.errors.not_found"}, status_code=404)
    return Response(actor_sheet_service.to_dict(bundle), status_code=200)


@get("/game/actor/{actor_id:str}/sheet-data")
async def get_sheet_data(
    actor_id: FromPath[str],
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    sheet_data_service: SheetDataService,
) -> Response[dict[str, Any]]:
    user = current_user
    result = sheet_data_service.get_data(actor_id=actor_id, user_id=user["id"])
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response(
        {
            "actor_id": result.actor_id,
            "system_id": result.system_id,
            "version": result.version,
            "data": result.data or {},
        },
        status_code=200,
    )


@get("/game/token/sheet/modal/{token_id:str}")
async def show_token_sheet_modal(
    token_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    token_instance_sheet_service: TokenInstanceSheetService,
) -> Redirect | Template:
    user = current_user
    base_context = view_context(cookies)
    bundle = token_instance_sheet_service.build_bundle(
        token_id=token_id,
        user_id=user["id"],
        locale=base_context["locale"],
    )
    if bundle is None:
        return Redirect(path="/game")
    member_role = token_instance_sheet_service.campaigns.get_member_role(
        campaign_id=bundle.campaign_id,
        user_id=user["id"],
    )
    context = {
        **base_context,
        "actor": bundle,
        "bundle_json": json.dumps(
            token_instance_sheet_service.to_dict(bundle), separators=(",", ":")
        ),
        "room_id": bundle.campaign_id,
        "is_gm": member_role == "gm",
    }
    return Template(template_name="pages/game/_actor_sheet_modal.html", context=context)


@get("/game/token/{token_id:str}/sheet-bundle")
async def get_token_sheet_bundle(
    token_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    token_instance_sheet_service: TokenInstanceSheetService,
) -> Response[dict[str, Any]]:
    user = current_user
    locale = view_context(cookies)["locale"]
    bundle = token_instance_sheet_service.build_bundle(
        token_id=token_id, user_id=user["id"], locale=locale
    )
    if bundle is None:
        return Response({"error_key": "tokens.errors.not_found"}, status_code=404)
    return Response(token_instance_sheet_service.to_dict(bundle), status_code=200)


@post("/game/token/sheet-data/patch")
async def patch_token_sheet_data(
    request: Request,
    current_user: Row,
    token_instance_sheet_service: TokenInstanceSheetService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    patch = body.get("patch")
    result = token_instance_sheet_service.patch_data(
        token_id=str(body.get("token_id", "")),
        user_id=user["id"],
        patch=patch if isinstance(patch, dict) else {},
    )
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    await _emit_token_sheet_data(result, user_id=user["id"], token_service=token_service)
    return Response(
        {
            "token_id": result.token_id,
            "version": result.version,
            "changed_paths": result.changed_paths,
        },
        status_code=200,
    )


@post("/game/token/item/patch")
async def patch_token_item_instance(
    request: Request,
    current_user: Row,
    token_instance_sheet_service: TokenInstanceSheetService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    patch = body.get("patch")
    result = token_instance_sheet_service.patch_item(
        token_id=str(body.get("token_id", "")),
        user_id=current_user["id"],
        item_instance_id=str(body.get("item_instance_id", "")),
        patch=patch if isinstance(patch, dict) else {},
    )
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    await _emit_token_sheet_data(result, user_id=current_user["id"], token_service=token_service)
    return Response(
        {
            "token_id": result.token_id,
            "version": result.version,
            "changed_paths": result.changed_paths,
        },
        status_code=200,
    )


async def _emit_token_sheet_data(
    result: "TokenSheetDataResult", *, user_id: str, token_service: TokenService
) -> None:
    """Tell the room a token's own sheet changed (same shape the patch uses)."""
    token = token_service.tokens.get_by_id(result.token_id or "")
    if not (result.campaign_id and result.scene_id and token is not None):
        return
    payload = {
        "room_id": result.campaign_id,
        "scene_id": result.scene_id,
        "actor_id": token.get("actor_id"),
        "tokens": [
            {
                "token_id": result.token_id,
                "version": result.version or token.get("version"),
                "changed": {"overrides": result.overrides or {}},
            }
        ],
        "updated_by": user_id,
    }
    transport = RealtimeTransport()
    await transport.to_gm(
        room_id=result.campaign_id, event=TransportEvent.TOKENS_UPDATED, payload=payload
    )
    if not token.get("hidden"):
        await transport.to_players_in_room(
            room_id=result.campaign_id, event=TransportEvent.TOKENS_UPDATED, payload=payload
        )


async def _refresh_actor_tokens(
    *, campaign_id: str | None, actor_id: str | None, token_service: TokenService
) -> None:
    """Recompute on-canvas tokens linked to an actor after its sheet data changes."""
    if not campaign_id or not actor_id:
        return
    await token_service.refresh_actor_tokens(
        campaign_id=campaign_id,
        actor_id=actor_id,
        transport=RealtimeTransport(),
    )


async def _emit_sheet_data(
    result: SheetDataResult, *, user_id: str, token_service: TokenService
) -> None:
    if not result.success or not result.campaign_id:
        return
    await RealtimeTransport().to_room(
        room_id=result.campaign_id,
        event=TransportEvent.SHEET_DATA_UPDATED,
        payload={
            "room_id": result.campaign_id,
            "system_id": result.system_id or "",
            "actor_id": result.actor_id,
            "version": result.version or 0,
            "updated_by": user_id,
            "changed_paths": result.changed_paths,
        },
    )
    await _refresh_actor_tokens(
        campaign_id=result.campaign_id, actor_id=result.actor_id, token_service=token_service
    )


async def _emit_applied_damage(applied: dict, *, user_id: str, token_service: TokenService) -> None:
    """Tell the room a roll changed a target actor or token resource."""
    campaign_id = applied.get("campaignId")
    actor_id = applied.get("targetActorId")
    if not campaign_id or not actor_id:
        return

    target_token_id = applied.get("targetTokenId")
    scene_id = applied.get("sceneId")
    if target_token_id and scene_id:
        await RealtimeTransport().to_room(
            room_id=campaign_id,
            event=TransportEvent.TOKENS_UPDATED,
            payload={
                "room_id": campaign_id,
                "scene_id": scene_id,
                "tokens": [
                    {
                        "token_id": target_token_id,
                        "version": applied.get("tokenVersion") or applied.get("version") or 0,
                    }
                ],
                "updated_by": user_id,
                "changed_paths": [applied.get("resourcePath") or ""],
            },
        )
        return

    await RealtimeTransport().to_room(
        room_id=campaign_id,
        event=TransportEvent.SHEET_DATA_UPDATED,
        payload={
            "room_id": campaign_id,
            "system_id": applied.get("systemId") or "",
            "actor_id": actor_id,
            "version": applied.get("version") or 0,
            "updated_by": user_id,
            "changed_paths": [applied.get("resourcePath") or ""],
        },
    )
    await _refresh_actor_tokens(
        campaign_id=campaign_id, actor_id=actor_id, token_service=token_service
    )


@post("/game/actor/sheet-data/patch")
async def patch_sheet_data(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    sheet_data_service: SheetDataService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    patch = body.get("patch")
    result = sheet_data_service.patch_data(
        actor_id=str(body.get("actor_id", "")),
        user_id=user["id"],
        patch=patch if isinstance(patch, dict) else {},
    )
    await _emit_sheet_data(result, user_id=user["id"], token_service=token_service)
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response(
        {
            "actor_id": result.actor_id,
            "version": result.version,
            "changed_paths": result.changed_paths,
        },
        status_code=200,
    )


async def _broadcast_roll(
    result: ActionResult,
    *,
    user: dict,
    chat_service: ChatService,
    roll_presentation_service: RollPresentationService,
) -> None:
    """Persist + broadcast a sheet roll as a chat ROLL message (chat + toast)."""
    if not result.campaign_id:
        return

    metadata = _roll_metadata_with_presentation(
        result, roll_presentation_service=roll_presentation_service
    )
    message = chat_service.create_roll_message(
        campaign_id=result.campaign_id,
        author_user_id=user["id"],
        author_name=user["name"],
        actor_name=result.actor_name,
        label=result.label,
        expression=result.expression,
        groups=result.groups,
        modifier=result.modifier,
        total=result.total,
        visibility=result.visibility,
        metadata=metadata,
    )
    if message is None:
        return

    transport = RealtimeTransport()
    gm_only = bool(message.pop("gm_only", False))
    if gm_only:
        await transport.chat_to_gm(room_id=result.campaign_id, message=message)
    else:
        await transport.chat_to_room(room_id=result.campaign_id, message=message)


async def _emit_action_mutation(
    result: ActionResult, *, user_id: str, token_service: TokenService
) -> None:
    if not result.campaign_id:
        return
    await RealtimeTransport().to_room(
        room_id=result.campaign_id,
        event=TransportEvent.SHEET_DATA_UPDATED,
        payload={
            "room_id": result.campaign_id,
            "system_id": result.system_id or "",
            "actor_id": result.actor_id,
            "version": result.version or 0,
            "updated_by": user_id,
            "changed_paths": result.changed_paths,
            "token_view": result.token_view or {},
        },
    )
    await _refresh_actor_tokens(
        campaign_id=result.campaign_id, actor_id=result.actor_id, token_service=token_service
    )


async def _emit_sheet_item_mutation(
    result: SheetItemResult, *, user_id: str, token_service: TokenService
) -> None:
    if not result.campaign_id:
        return
    await RealtimeTransport().to_room(
        room_id=result.campaign_id,
        event=TransportEvent.SHEET_DATA_UPDATED,
        payload={
            "room_id": result.campaign_id,
            "system_id": result.system_id or "",
            "actor_id": result.actor_id,
            "version": result.version or 0,
            "updated_by": user_id,
            "changed_paths": result.changed_paths,
            "token_view": result.token_view or {},
        },
    )
    await _refresh_actor_tokens(
        campaign_id=result.campaign_id, actor_id=result.actor_id, token_service=token_service
    )


def _roll_response(
    result: ActionResult, *, roll_presentation_service: RollPresentationService
) -> Response[dict[str, Any]]:
    metadata = _roll_metadata_with_presentation(
        result, roll_presentation_service=roll_presentation_service
    )

    return Response(
        {
            "actor_id": result.actor_id,
            "type": result.action_type,
            "label": result.label,
            "expression": result.expression,
            "groups": result.groups,
            "modifier": result.modifier,
            "total": result.total,
            "visibility": result.visibility,
            "metadata": metadata,
            "applied": result.applied,
        },
        status_code=200,
    )


def _roll_metadata_with_presentation(
    result: ActionResult, *, roll_presentation_service: RollPresentationService
) -> dict:
    metadata = dict(result.metadata or {})

    if "rendered" not in metadata:
        rendered = roll_presentation_service.render(
            system_id=result.system_id,
            metadata=metadata,
            actor_name=result.actor_name,
            label=result.label,
            expression=result.expression,
            groups=result.groups,
            modifier=result.modifier,
            total=result.total,
        ).as_metadata()

        if rendered:
            metadata["rendered"] = rendered

    return metadata


@post("/game/actor/action")
async def execute_action(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    sheet_action_service: SheetActionService,
    combat_service: CombatService,
    token_service: TokenService,
    chat_service: ChatService,
    roll_presentation_service: RollPresentationService,
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    inputs = body.get("inputs")
    roll_options = body.get("rollOptions")
    item = body.get("item")
    result = sheet_action_service.execute(
        actor_id=str(body.get("actor_id", "")),
        action_id=str(body.get("action_id", "")),
        user_id=user["id"],
        inputs=inputs if isinstance(inputs, dict) else {},
        item=item if isinstance(item, dict) else None,
        roll_options=roll_options if isinstance(roll_options, dict) else None,
        target_actor_id=str(body.get("target_actor_id") or "") or None,
        target_token_id=str(body.get("target_token_id") or "") or None,
        source_token_id=str(body.get("token_id") or "") or None,
        locale=view_context(cookies)["locale"],
    )
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)



    if result.action_type in {"roll", "chat"}:
        await _broadcast_roll(
            result,
            user=user,
            chat_service=chat_service,
            roll_presentation_service=roll_presentation_service,
        )
        if result.changed_paths:
            source_token_id = str(body.get("token_id") or "")
            source_token = token_service.tokens.get_by_id(source_token_id) if source_token_id else None
            if source_token is not None and source_token.get("actor_link_mode") == "unlinked":
                await _emit_token_sheet_data(
                    TokenSheetDataResult(
                        success=True, token_id=source_token_id,
                        actor_id=source_token.get("actor_id"), campaign_id=result.campaign_id,
                        scene_id=source_token.get("scene_id"), system_id=result.system_id,
                        version=source_token.get("version"), overrides=source_token.get("overrides"),
                        changed_paths=result.changed_paths,
                    ),
                    user_id=user["id"], token_service=token_service,
                )
            else:
                await _emit_action_mutation(result, user_id=user["id"], token_service=token_service)
        if (
            str(body.get("action_id", "")) == "roll.initiative"
            and result.campaign_id
            and result.actor_id
        ):
            combat_service.record_initiative_roll(
                campaign_id=result.campaign_id,
                actor_id=result.actor_id,
                token_id=str(body.get("token_id") or "") or None,
                user_id=user["id"],
                total=result.total,
            )
            combat_state = combat_service.get_state(
                campaign_id=result.campaign_id, user_id=user["id"]
            )
            if combat_state.success and combat_state.combat is not None:
                await RealtimeTransport().to_room(
                    room_id=result.campaign_id,
                    event=TransportEvent.COMBAT_UPDATED,
                    payload=combat_state.state_payload() | {"updated_by": user["id"]},
                )
        if result.applied:
            await _emit_applied_damage(
                result.applied, user_id=user["id"], token_service=token_service
            )
        return _roll_response(result, roll_presentation_service=roll_presentation_service)

    await _emit_action_mutation(result, user_id=user["id"], token_service=token_service)
    return Response(
        {
            "actor_id": result.actor_id,
            "version": result.version,
            "changed_paths": result.changed_paths,
        },
        status_code=200,
    )


@post("/game/actor/roll")
async def roll_actor_formula(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    sheet_action_service: SheetActionService,
    chat_service: ChatService,
    roll_presentation_service: RollPresentationService,
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    result = sheet_action_service.roll_formula(
        actor_id=str(body.get("actor_id", "")),
        formula=str(body.get("formula", "")),
        user_id=user["id"],
        label=str(body.get("label", "")),
    )
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    await _broadcast_roll(
        result,
        user=user,
        chat_service=chat_service,
        roll_presentation_service=roll_presentation_service,
    )
    return _roll_response(result, roll_presentation_service=roll_presentation_service)


@post("/game/roll/reroll")
async def reroll_chat_roll(
    request: Request,
    current_user: Row,
    roll_reroll_service: RollRerollService,
    chat_service: ChatService,
    roll_presentation_service: RollPresentationService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    result = roll_reroll_service.reroll(
        campaign_id=str(body.get("campaign_id") or ""),
        message_id=str(body.get("message_id") or ""),
        user_id=current_user["id"],
    )
    if not result.success or result.roll is None:
        return Response({"error_key": result.error_key}, status_code=400)
    await _broadcast_roll(result.roll, user=current_user, chat_service=chat_service, roll_presentation_service=roll_presentation_service)
    await RealtimeTransport().to_room(
        room_id=result.roll.campaign_id,
        event=TransportEvent.SHEET_DATA_UPDATED,
        payload={"room_id": result.roll.campaign_id, "system_id": result.roll.system_id, "actor_id": result.roll.actor_id, "version": result.version, "updated_by": current_user["id"], "changed_paths": ["bennies.value"]},
    )
    return _roll_response(result.roll, roll_presentation_service=roll_presentation_service)


@post("/game/actor/item/action")
async def execute_item_action(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    sheet_item_service: SheetItemService,
    token_service: TokenService,
    chat_service: ChatService,
    roll_presentation_service: RollPresentationService,
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    inputs = body.get("inputs")
    roll_options = body.get("rollOptions")
    result = sheet_item_service.execute_action(
        actor_id=str(body.get("actor_id", "")),
        user_id=user["id"],
        item_instance_id=str(body.get("item_instance_id", "")),
        action_id=str(body.get("action_id", "")),
        inputs=inputs if isinstance(inputs, dict) else {},
        roll_options=roll_options if isinstance(roll_options, dict) else None,
        target_actor_id=str(body.get("target_actor_id") or "") or None,
        target_token_id=str(body.get("target_token_id") or "") or None,
    )
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)


    if result.action_type in {"roll", "chat"}:
        await _broadcast_roll(
            result,
            user=user,
            chat_service=chat_service,
            roll_presentation_service=roll_presentation_service,
        )
        if result.changed_paths:
            await _emit_action_mutation(result, user_id=user["id"], token_service=token_service)
        if result.applied:
            await _emit_applied_damage(
                result.applied, user_id=user["id"], token_service=token_service
            )
        return _roll_response(result, roll_presentation_service=roll_presentation_service)
    await _emit_action_mutation(result, user_id=user["id"], token_service=token_service)
    return Response(
        {
            "actor_id": result.actor_id,
            "version": result.version,
            "changed_paths": result.changed_paths,
        },
        status_code=200,
    )


@post("/game/actor/item/patch")
async def patch_item_instance(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    sheet_item_service: SheetItemService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    patch = body.get("patch")
    result = sheet_item_service.patch_item(
        actor_id=str(body.get("actor_id", "")),
        user_id=user["id"],
        item_instance_id=str(body.get("item_instance_id", "")),
        patch=patch if isinstance(patch, dict) else {},
    )
    await _emit_sheet_item_mutation(result, user_id=user["id"], token_service=token_service)
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response(
        {
            "actor_id": result.actor_id,
            "version": result.version,
            "changed_paths": result.changed_paths,
        },
        status_code=200,
    )


@get("/game/actor/{actor_id:str}/item/{item_instance_id:str}/sheet-bundle")
async def get_embedded_item_sheet_bundle(
    actor_id: FromPath[str],
    item_instance_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    sheet_item_service: SheetItemService,
) -> Response[dict[str, Any]]:
    bundle = sheet_item_service.build_embedded_bundle(
        actor_id=actor_id,
        user_id=current_user["id"],
        item_instance_id=item_instance_id,
        locale=view_context(cookies)["locale"],
    )
    if bundle is None:
        return Response({"error_key": "game.sheet_items.errors.item_not_found"}, status_code=404)
    return Response(bundle, status_code=200)


@post("/game/actor/item/remove")
async def remove_item_instance(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    sheet_item_service: SheetItemService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    result = sheet_item_service.remove_item(
        actor_id=str(body.get("actor_id", "")),
        user_id=user["id"],
        item_instance_id=str(body.get("item_instance_id", "")),
    )
    await _emit_sheet_item_mutation(result, user_id=user["id"], token_service=token_service)
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response(
        {
            "actor_id": result.actor_id,
            "version": result.version,
            "changed_paths": result.changed_paths,
        },
        status_code=200,
    )


@get("/game/content/packs/{system_id:str}")
async def list_content_packs(
    system_id: FromPath[str],
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    content_pack_service: ContentPackService,
    content_pack_access: ContentPackAccessService,
) -> Response[dict[str, Any]]:
    campaign_id = str(request.query_params.get("campaign_id") or "")
    if not campaign_id:
        return Response({"error_key": "permissions.errors.denied"}, status_code=403)
    is_gm = content_pack_access.role_of(
        campaign_id=campaign_id, user_id=current_user["id"]
    ) == PlayerRole.GM.value
    niveis = content_pack_access.levels_for_campaign(campaign_id=campaign_id)
    packs = []
    for pack in content_pack_service.list_packs(system_id):
        pack_id = str(pack.get("id") or "")
        if not content_pack_access.can_read(
            campaign_id=campaign_id, package_id=system_id, pack_id=pack_id,
            user_id=current_user["id"],
        ):
            continue
        # O nivel viaja junto so para quem concede: e o que enche o seletor sem
        # uma segunda ida ao servidor por pack.
        if is_gm:
            pack = {
                **pack,
                "player_access": niveis.get((system_id, pack_id, PlayerRole.PLAYER.value), "none"),
            }
        packs.append(pack)
    return Response({"packs": packs, "can_grant": is_gm}, status_code=200)


@get("/game/content/pack/{system_id:str}/{pack_id:str}/entry/{entry_id:str}/sheet")
async def show_compendium_entry_sheet(
    system_id: FromPath[str],
    pack_id: FromPath[str],
    entry_id: FromPath[str],
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    package_content_service: PackageContentService,
    actor_sheet_service: ActorSheetService,
    item_sheet_service: ItemSheetService,
    content_pack_access: ContentPackAccessService,
) -> Redirect | Template:
    """A entrada do compendio aberta na ficha de verdade, em leitura.

    Nao existe uma "tela de compendio": o que o mestre e o jogador leem aqui e o
    mesmo renderizador de ficha do mundo, com can_edit falso. Manter duas telas
    para a mesma coisa e o que faz uma delas envelhecer.
    """
    campaign_id = str(request.query_params.get("campaign_id") or "")
    if not campaign_id or not content_pack_access.can_read(
        campaign_id=campaign_id, package_id=system_id, pack_id=pack_id,
        user_id=current_user["id"],
    ):
        return Redirect(path="/game")

    pack = package_content_service.get_pack(system_id, pack_id)
    entry = package_content_service.get_entry(system_id, pack_id, entry_id)
    # Compatibility for tests/older adapters which override get_pack only.
    if entry is None:
        entry = next(
            (e for e in (pack or {}).get("entries", []) if str(e.get("id") or "") == entry_id), None
        )
    if entry is None:
        return Redirect(path="/game")

    base_context = view_context(cookies)
    modal_id = f"compendium-{system_id}-{pack_id}-{entry_id}"
    campanha = CampaignRepository().get(campaign_id) or {}
    sistema = str(
        entry.get("systemId")
        or entry.get("system_id")
        or campanha.get("active_system_id")
        or ""
    )
    is_gm = content_pack_access.role_of(
        campaign_id=campaign_id, user_id=current_user["id"]
    ) == PlayerRole.GM.value
    tipo_do_pack = str((pack or {}).get("type") or "")
    comum = {
        **base_context,
        "compendium_modal_id": modal_id,
        "room_id": campaign_id,
        "is_gm": is_gm,
    }
    nome = str(entry.get("name") or entry.get("title") or "")
    dados = entry.get("data") if isinstance(entry.get("data"), dict) else {}

    # O tipo do PACK decide a ficha. Mandar tudo para a de ator desenhava um
    # arco curto com classe, raca e pontos de experiencia -- e sem layout, porque
    # nao existe ficha de ator do tipo "weapon".
    if tipo_do_pack in {"item_pack", "spell_pack"}:
        item_bundle = item_sheet_service.build_preview_bundle(
            preview_id=modal_id, campaign_id=campaign_id, system_id=sistema,
            item_type=str(entry.get("type") or ""), name=nome, data=dados,
            locale=base_context["locale"],
        )
        return Template(
            template_name="pages/game/_item_sheet_modal.html",
            context={
                **comum,
                "item": item_bundle,
                "bundle_json": json.dumps(
                    item_sheet_service.to_dict(item_bundle), separators=(",", ":")
                ),
                "targeted_handouts_enabled": config.targeted_handouts_enabled,
            },
        )

    bundle = actor_sheet_service.build_preview_bundle(
        preview_id=modal_id,
        campaign_id=campaign_id,
        system_id=sistema,
        actor_type=str(entry.get("type") or ""),
        name=nome,
        data=dados,
        locale=base_context["locale"],
    )
    return Template(
        template_name="pages/game/_actor_sheet_modal.html",
        context={
            **comum,
            "actor": bundle,
            "actor_core_version": 0,
            "bundle_json": json.dumps(actor_sheet_service.to_dict(bundle), separators=(",", ":")),
        },
    )


@post("/game/content/pack-access")
async def set_content_pack_access(
    request: Request,
    current_user: Row,
    content_pack_access: ContentPackAccessService,
) -> Response[dict[str, Any]]:
    """O mestre abre ou fecha um pack para um papel."""
    body = await _json_body(request)
    granted = content_pack_access.set_level(
        campaign_id=str(body.get("campaign_id") or ""),
        package_id=str(body.get("package_id") or ""),
        pack_id=str(body.get("pack_id") or ""),
        role=str(body.get("role") or PlayerRole.PLAYER.value),
        level=str(body.get("level") or "none"),
        user_id=current_user["id"],
    )
    if not granted:
        return Response({"error_key": "permissions.errors.denied"}, status_code=403)
    return Response({"level": str(body.get("level") or "none")}, status_code=200)


@get("/game/content/active-packages")
async def list_active_content_packages(
    request: Request,
    current_user: Row,
    package_content_service: PackageContentService,
) -> Response[dict[str, Any]]:
    campaign_id = str(request.query_params.get("campaign_id") or "")
    packages = package_content_service.list_active_packages(
        campaign_id=campaign_id,
        user_id=current_user["id"],
    )
    return Response({"packages": packages}, status_code=200)


@get("/game/content/pack/{system_id:str}/{pack_id:str}")
async def get_content_pack(
    system_id: FromPath[str],
    pack_id: FromPath[str],
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    content_pack_service: ContentPackService,
    content_pack_access: ContentPackAccessService,
) -> Response[dict[str, Any]]:
    campaign_id = str(request.query_params.get("campaign_id") or "")
    if not campaign_id or not content_pack_access.can_read(
        campaign_id=campaign_id, package_id=system_id, pack_id=pack_id, user_id=current_user["id"]
    ):
        return Response({"error_key": "permissions.errors.denied"}, status_code=403)
    query = str(request.query_params.get("q") or "")
    try:
        offset = int(request.query_params.get("offset") or 0)
        limit = int(request.query_params.get("limit") or 50)
    except (TypeError, ValueError):
        return Response({"error_key": "game.content.errors.invalid_query"}, status_code=400)
    pack = content_pack_service.get_index(
        system_id, pack_id, query=query, offset=offset, limit=limit
    )
    if pack is None:
        return Response({"error_key": "game.drop.errors.entry_not_found"}, status_code=404)
    return Response(pack, status_code=200)


@post("/game/actor/drop")
async def drop_on_actor(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    sheet_drop_service: SheetDropService,
    token_instance_sheet_service: TokenInstanceSheetService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    source = body.get("source") if isinstance(body.get("source"), dict) else {}
    target = body.get("target") if isinstance(body.get("target"), dict) else {}
    drop_zone = str(target.get("drop_zone", ""))




    token_id = str(body.get("token_id") or "")
    if token_id and str(body.get("token_link_mode") or "") != "linked":
        token_result = token_instance_sheet_service.drop(
            token_id=token_id, user_id=user["id"], source=source, drop_zone=drop_zone
        )
        if not token_result.success:
            return Response({"error_key": token_result.error_key}, status_code=400)
        await _emit_token_sheet_data(
            token_result, user_id=user["id"], token_service=token_service
        )
        return Response({"token_id": token_id, "version": token_result.version}, status_code=200)

    result = sheet_drop_service.drop(
        actor_id=str(body.get("actor_id", "")),
        user_id=user["id"],
        source=source,
        drop_zone=drop_zone,
    )
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)

    if result.campaign_id:
        await RealtimeTransport().to_room(
            room_id=result.campaign_id,
            event=TransportEvent.SHEET_DATA_UPDATED,
            payload={
                "room_id": result.campaign_id,
                "system_id": result.system_id or "",
                "actor_id": result.actor_id,
                "version": result.version or 0,
                "updated_by": user["id"],
                "changed_paths": result.changed_paths,
                "token_view": result.token_view or {},
            },
        )
        await _refresh_actor_tokens(
            campaign_id=result.campaign_id, actor_id=result.actor_id, token_service=token_service
        )
    return Response(
        {
            "actor_id": result.actor_id,
            "version": result.version,
            "changed_paths": result.changed_paths,
        },
        status_code=200,
    )


@post("/game/content/import")
async def import_content_entry(
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
    # Importar cria ator ou item na campanha: exige `owner` no pack, aqui e nao
    # so escondendo o botao. Quem tem `read` consulta, mas nao traz para a mesa.
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
    if result.campaign_id and result.actor_id:
        await RealtimeTransport().to_room(
            room_id=result.campaign_id,
            event=TransportEvent.ACTOR_CREATED,
            payload={
                "room_id": result.campaign_id,
                "actor_id": result.actor_id,
                "system_id": result.system_id or "",
                "updated_by": user["id"],
            },
        )
    if result.deck_id and result.campaign_id:
        await RealtimeTransport().to_room(
            room_id=result.campaign_id,
            event=TransportEvent.CARDS_STATE_UPDATED,
            payload={"room_id": result.campaign_id, "deck_id": result.deck_id,
                     "updated_by": user["id"]},
        )
    if result.item_id and result.campaign_id:
        await RealtimeTransport().to_room(
            room_id=result.campaign_id, event=TransportEvent.ITEM_CREATED,
            payload={"room_id": result.campaign_id, "item_id": result.item_id,
                     "system_id": result.system_id or "", "updated_by": user["id"]},
        )
    if result.journal_id and result.campaign_id:
        await RealtimeTransport().to_room(
            room_id=result.campaign_id, event=TransportEvent.JOURNAL_CREATED,
            payload={"room_id": result.campaign_id, "journal_id": result.journal_id,
                     "updated_by": user["id"]},
        )
    if result.scene_id and result.campaign_id:
        await RealtimeTransport().to_room(
            room_id=result.campaign_id, event=TransportEvent.SCENE_CREATED,
            payload={"room_id": result.campaign_id, "scene_id": result.scene_id,
                     "updated_by": user["id"]},
        )
    return Response(
        {"actor_id": result.actor_id, "item_id": result.item_id,
         "journal_id": result.journal_id, "deck_id": result.deck_id,
         "scene_id": result.scene_id},
        status_code=201,
    )


@post("/game/content/package/import")
async def import_content_package(
    request: Request,
    current_user: Row,
    package_content_service: PackageContentService,
    content_pack_access: ContentPackAccessService,
) -> Response[dict[str, Any]]:
    """Import every importable entry from one active content package."""
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    package_id = str(body.get("package_id") or "")
    created_items: list[str] = []
    created_actors: list[str] = []
    created_journals: list[str] = []
    created_decks: list[str] = []
    created_scenes: list[str] = []
    errors: list[dict[str, str]] = []
    active_package = next(
        (
            package
            for package in package_content_service.list_active_packages(
                campaign_id=campaign_id,
                user_id=current_user["id"],
            )
            if package["id"] == package_id
        ),
        None,
    )
    if active_package is None:
        return Response({"error_key": "sdk.errors.dependency_inactive"}, status_code=400)
    for summary in package_content_service.list_packs(package_id):
        pack_id = str(summary.get("id") or "")
        # Importar o pacote inteiro nao pode contornar o acesso pack a pack: o
        # que o usuario nao poderia trazer um a um, tambem nao vem no lote.
        if not content_pack_access.can_import(
            campaign_id=campaign_id, package_id=package_id, pack_id=pack_id,
            user_id=current_user["id"],
        ):
            continue
        pack = package_content_service.get_pack(package_id, pack_id)
        if pack is None:
            continue
        destination_folder_id = package_content_service.ensure_import_folder(
            campaign_id=campaign_id,
            user_id=current_user["id"],
            package_name=str(active_package["name"]),
            pack={**pack, "label": summary.get("label") or pack.get("label")},
        )
        entries = sorted(
            pack.get("entries", []),
            key=lambda entry: (
                (entry.get("data") or {}).get("importOrder", 999)
                if isinstance(entry.get("data"), dict)
                else 999
            ),
        )
        for entry in entries:
            entry_id = str(entry.get("id") or "")
            result = package_content_service.import_entry(
                campaign_id=campaign_id,
                user_id=current_user["id"],
                package_id=package_id,
                pack_id=pack_id,
                entry_id=entry_id,
                folder_id=destination_folder_id,
            )
            if not result.success:
                errors.append({"pack_id": pack_id, "entry_id": entry_id, "error_key": result.error_key or ""})
                continue
            if result.item_id:
                created_items.append(result.item_id)
                event = TransportEvent.ITEM_CREATED
                entity_id = result.item_id
            elif result.actor_id:
                created_actors.append(result.actor_id)
                event = TransportEvent.ACTOR_CREATED
                entity_id = result.actor_id
            elif result.journal_id:
                created_journals.append(result.journal_id)
                event = TransportEvent.JOURNAL_CREATED
                entity_id = result.journal_id
            elif result.deck_id:
                created_decks.append(result.deck_id)
                event = TransportEvent.CARDS_STATE_UPDATED
                entity_id = result.deck_id
            elif result.scene_id:
                created_scenes.append(result.scene_id)
                event = TransportEvent.SCENE_CREATED
                entity_id = result.scene_id
            else:
                continue
            await RealtimeTransport().to_room(
                room_id=campaign_id,
                event=event,
                payload={
                    "room_id": campaign_id,
                    (
                        "item_id"
                        if result.item_id
                        else "actor_id"
                        if result.actor_id
                        else "journal_id" if result.journal_id
                        else "deck_id" if result.deck_id
                        else "scene_id"
                    ): entity_id,
                    "system_id": result.system_id or "",
                    "updated_by": current_user["id"],
                },
            )
    return Response(
        {
            "imported": len(created_items) + len(created_actors) + len(created_journals) + len(created_decks) + len(created_scenes),
            "item_ids": created_items,
            "actor_ids": created_actors,
            "journal_ids": created_journals,
            "deck_ids": created_decks,
            "scene_ids": created_scenes,
            "errors": errors,
        },
        status_code=200,
    )


@post("/game/actor/sheet-data/set")
async def set_sheet_data(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    sheet_data_service: SheetDataService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    user = current_user
    body = await _json_body(request)
    data = body.get("data")
    result = sheet_data_service.set_data(
        actor_id=str(body.get("actor_id", "")),
        user_id=user["id"],
        data=data if isinstance(data, dict) else {},
    )
    await _emit_sheet_data(result, user_id=user["id"], token_service=token_service)
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response({"actor_id": result.actor_id, "version": result.version}, status_code=200)
