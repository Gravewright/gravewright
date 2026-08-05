from __future__ import annotations

from app.persistence.rows import Row
from typing import Any

from litestar import Request, get, post
from litestar.exceptions import NotAuthorizedException
from litestar.exceptions import NotFoundException
from litestar.params import FromPath
from litestar.response import Response

from app.engine.scenes.scene_asset_read_service import SceneAssetReadService
from app.engine.tokens.token_hp_service import TokenHpService
from app.engine.tokens.token_service import TokenService
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@get("/game/scenes/{scene_id:str}/tokens")
async def get_scene_tokens(
    scene_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    token_service: TokenService,
    scene_asset_read_service: SceneAssetReadService,
) -> Response[dict[str, Any]]:
    user = current_user
    campaign_id = scene_asset_read_service.campaign_id_for_scene(scene_id=scene_id)
    if campaign_id is None:
        raise NotFoundException()

    result = token_service.get_snapshot(
        campaign_id=campaign_id,
        scene_id=scene_id,
        user_id=user["id"],
    )

    if not result.success:
        if result.error_key == "tokens.errors.scene_not_found":
            raise NotFoundException()
        raise NotAuthorizedException()

    return Response(
        content={
            "scene_id": scene_id,
            "tokens": result.tokens or [],
        }
    )


@post("/game/token/hp")
async def update_token_hp(
    request: Request,
    current_user: Row,
    token_hp_service: TokenHpService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    amount = body.get("amount")
    value = body.get("value")
    result = token_hp_service.update_hp(
        campaign_id=str(body.get("campaign_id") or body.get("room_id") or ""),
        scene_id=str(body.get("scene_id") or ""),
        token_id=str(body.get("token_id") or ""),
        user_id=current_user["id"],
        operation=str(body.get("operation") or ""),
        amount=_optional_int(amount),
        value=_optional_int(value),
    )
    if not result.success:
        status = 403 if result.error_key == "tokens.errors.permission_denied" else 400
        if result.error_key in {"tokens.errors.not_found", "tokens.errors.scene_not_found"}:
            status = 404
        return Response({"error_key": result.error_key}, status_code=status)

    transport = RealtimeTransport()
    if result.linked_actor:
        await token_service.refresh_actor_tokens(
            campaign_id=result.campaign_id or "",
            actor_id=result.actor_id or "",
            transport=transport,
        )
    else:
        token = token_service.tokens.get_by_id(result.token_id or "")
        payload = {
            "room_id": result.campaign_id,
            "scene_id": result.scene_id,
            "tokens": [
                {
                    "token_id": result.token_id,
                    "version": result.token_version,
                    "changed": {"bars": result.token_view.get("bars", {})},
                }
            ],
            "updated_by": current_user["id"],
            "changed_paths": result.changed_paths,
        }
        await transport.to_gm(room_id=result.campaign_id or "", event=TransportEvent.TOKENS_UPDATED, payload=payload)
        if token is not None and not token.get("hidden"):
            await transport.to_players_in_room(
                room_id=result.campaign_id or "",
                event=TransportEvent.TOKENS_UPDATED,
                payload=payload,
            )

    return Response(
        {
            "token_id": result.token_id,
            "actor_id": result.actor_id,
            "scene_id": result.scene_id,
            "campaign_id": result.campaign_id,
            "operation": result.operation,
            "amount": result.amount,
            "value_before": result.value_before,
            "value_after": result.value_after,
            "max_value": result.max_value,
            "value_path": result.value_path,
            "version": result.version,
            "token_version": result.token_version,
            "linked_actor": result.linked_actor,
            "token_view": result.token_view,
        },
        status_code=200,
    )
