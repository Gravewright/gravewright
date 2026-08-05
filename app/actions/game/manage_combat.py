from __future__ import annotations

from app.persistence.rows import Row
from typing import Any

from litestar import Request, get, post
from litestar.params import FromPath
from litestar.response import Response

from app.engine.chat.chat_service import ChatService
from app.engine.combat.turn_order_service import CombatResult, TurnOrderService
from app.engine.tokens.token_service import TokenService
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


def _tick_message(tick: dict) -> str:
    name = tick.get("actor_name") or tick.get("name") or "Alguém"
    amount = tick.get("amount") or 0
    after = tick.get("value_after")
    suffix = f" (HP {after})" if after is not None else ""
    if tick.get("operation") == "heal_over_time":
        return f"💚 {name} recuperou {amount} de vida{suffix}."
    dtype = tick.get("damage_type")
    type_text = f" de {dtype}" if dtype else ""
    return f"🩸 {name} sofreu {amount} de dano{type_text}{suffix}."


async def _announce_effect_ticks(result: CombatResult) -> None:
    """Post a system chat message for each recurring damage/heal tick of a turn."""
    ticks = result.effect_ticks or []
    if not ticks:
        return
    campaign_id = result.campaign_id or (result.combat or {}).get("campaign_id")
    if not campaign_id:
        return
    chat = ChatService()
    transport = RealtimeTransport()
    for tick in ticks:
        await chat.send_system_message(
            campaign_id=str(campaign_id), content=_tick_message(tick), transport=transport
        )


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


def _response(result: CombatResult, *, status_code: int = 200) -> Response[dict[str, Any]]:
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response(result.state_payload(), status_code=status_code)


async def _broadcast(result: CombatResult, *, user_id: str, event: TransportEvent, token_service: TokenService) -> None:
    if not result.success or not (result.campaign_id or (result.combat or {}).get("campaign_id")):
        return
    payload = result.state_payload() | {"updated_by": user_id}
    room_id = str(payload.get("campaign_id") or "")
    if not room_id:
        return
    transport = RealtimeTransport()
    await transport.to_room(room_id=room_id, event=event, payload=payload)
    for actor in result.updated_actors:
        actor_id = actor.get("actor_id")
        if not actor_id:
            continue
        await transport.to_room(
            room_id=room_id,
            event=TransportEvent.SHEET_DATA_UPDATED,
            payload={
                "room_id": room_id,
                "system_id": actor.get("system_id", ""),
                "actor_id": actor_id,
                "version": actor.get("version", 0),
                "updated_by": user_id,
                "changed_paths": ["sheet.effects"],
            },
        )
        await token_service.refresh_actor_tokens(campaign_id=room_id, actor_id=actor_id, transport=transport)


async def _body_and_auth(
    request: Request, cookies: dict[str, str], current_user: Row
) -> tuple[dict | None, dict | None, Response | None]:
    body = await _json_body(request)
    return body, current_user, None


@get("/game/combat/state/{campaign_id:str}")
async def get_combat_state(
    campaign_id: FromPath[str], cookies: dict[str, str], current_user: Row, turn_order_service: TurnOrderService
) -> Response[dict[str, Any]]:
    user = current_user
    result = turn_order_service.get_state(campaign_id=campaign_id, user_id=user["id"])
    return _response(result)


@post("/game/combat/start")
async def start_combat(request: Request, cookies: dict[str, str], current_user: Row, turn_order_service: TurnOrderService, token_service: TokenService) -> Response[dict[str, Any]]:
    body, user, early = await _body_and_auth(request, cookies, current_user)
    if early is not None:
        return early
    assert body is not None and user is not None
    actor_ids = body.get("actor_ids") if isinstance(body.get("actor_ids"), list) else []
    result = turn_order_service.start(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=user["id"],
        scene_id=str(body.get("scene_id") or "") or None,
        actor_ids=[str(actor_id) for actor_id in actor_ids],
    )
    await _broadcast(result, user_id=user["id"], event=TransportEvent.COMBAT_STARTED, token_service=token_service)
    return _response(result)


@post("/game/combat/end")
async def end_combat(request: Request, cookies: dict[str, str], current_user: Row, turn_order_service: TurnOrderService, token_service: TokenService) -> Response[dict[str, Any]]:
    body, user, early = await _body_and_auth(request, cookies, current_user)
    if early is not None:
        return early
    assert body is not None and user is not None
    result = turn_order_service.end(campaign_id=str(body.get("campaign_id", "")), user_id=user["id"])
    await _broadcast(result, user_id=user["id"], event=TransportEvent.COMBAT_ENDED, token_service=token_service)
    return _response(result)


@post("/game/combat/participants/add")
async def add_combat_participants(request: Request, cookies: dict[str, str], current_user: Row, turn_order_service: TurnOrderService, token_service: TokenService) -> Response[dict[str, Any]]:
    body, user, early = await _body_and_auth(request, cookies, current_user)
    if early is not None:
        return early
    assert body is not None and user is not None
    actor_ids = body.get("actor_ids") if isinstance(body.get("actor_ids"), list) else []
    token_ids = body.get("token_ids") if isinstance(body.get("token_ids"), list) else []
    result = turn_order_service.add_participants(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=user["id"],
        actor_ids=[str(actor_id) for actor_id in actor_ids],
        token_ids=[str(token_id) for token_id in token_ids],
    )
    await _broadcast(result, user_id=user["id"], event=TransportEvent.COMBAT_PARTICIPANT_ADDED, token_service=token_service)
    return _response(result)


@post("/game/combat/participants/remove")
async def remove_combat_participant(request: Request, cookies: dict[str, str], current_user: Row, turn_order_service: TurnOrderService, token_service: TokenService) -> Response[dict[str, Any]]:
    body, user, early = await _body_and_auth(request, cookies, current_user)
    if early is not None:
        return early
    assert body is not None and user is not None
    result = turn_order_service.remove_participant(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=user["id"],
        participant_id=str(body.get("participant_id", "")),
    )
    await _broadcast(result, user_id=user["id"], event=TransportEvent.COMBAT_PARTICIPANT_REMOVED, token_service=token_service)
    return _response(result)


@post("/game/combat/initiative/roll")
async def roll_combat_initiative(request: Request, cookies: dict[str, str], current_user: Row, turn_order_service: TurnOrderService, token_service: TokenService) -> Response[dict[str, Any]]:
    body, user, early = await _body_and_auth(request, cookies, current_user)
    if early is not None:
        return early
    assert body is not None and user is not None
    result = turn_order_service.roll_initiative(campaign_id=str(body.get("campaign_id", "")), user_id=user["id"])
    await _broadcast(result, user_id=user["id"], event=TransportEvent.COMBAT_STATE_UPDATED, token_service=token_service)
    return _response(result)


@post("/game/combat/initiative/roll-monsters")
async def roll_combat_monster_initiative(request: Request, cookies: dict[str, str], current_user: Row, turn_order_service: TurnOrderService, token_service: TokenService) -> Response[dict[str, Any]]:
    body, user, early = await _body_and_auth(request, cookies, current_user)
    if early is not None:
        return early
    assert body is not None and user is not None
    result = turn_order_service.roll_monster_initiative(campaign_id=str(body.get("campaign_id", "")), user_id=user["id"])
    await _broadcast(result, user_id=user["id"], event=TransportEvent.COMBAT_STATE_UPDATED, token_service=token_service)
    return _response(result)


@post("/game/combat/initiative/participant/roll")
async def roll_combat_participant_initiative(request: Request, cookies: dict[str, str], current_user: Row, turn_order_service: TurnOrderService, token_service: TokenService) -> Response[dict[str, Any]]:
    body, user, early = await _body_and_auth(request, cookies, current_user)
    if early is not None:
        return early
    assert body is not None and user is not None
    result = turn_order_service.roll_participant_initiative(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=user["id"],
        participant_id=str(body.get("participant_id", "")),
    )
    await _broadcast(result, user_id=user["id"], event=TransportEvent.COMBAT_STATE_UPDATED, token_service=token_service)
    return _response(result)


@post("/game/combat/turn/next")
async def next_combat_turn(request: Request, cookies: dict[str, str], current_user: Row, turn_order_service: TurnOrderService, token_service: TokenService) -> Response[dict[str, Any]]:
    body, user, early = await _body_and_auth(request, cookies, current_user)
    if early is not None:
        return early
    assert body is not None and user is not None
    result = turn_order_service.next_turn(campaign_id=str(body.get("campaign_id", "")), user_id=user["id"])
    await _broadcast(result, user_id=user["id"], event=TransportEvent.COMBAT_TURN_STARTED, token_service=token_service)
    await _announce_effect_ticks(result)
    return _response(result)


@post("/game/combat/turn/previous")
async def previous_combat_turn(request: Request, cookies: dict[str, str], current_user: Row, turn_order_service: TurnOrderService, token_service: TokenService) -> Response[dict[str, Any]]:
    body, user, early = await _body_and_auth(request, cookies, current_user)
    if early is not None:
        return early
    assert body is not None and user is not None
    result = turn_order_service.previous_turn(campaign_id=str(body.get("campaign_id", "")), user_id=user["id"])
    await _broadcast(result, user_id=user["id"], event=TransportEvent.COMBAT_STATE_UPDATED, token_service=token_service)
    return _response(result)


@post("/game/combat/turn/set")
async def set_combat_turn(request: Request, cookies: dict[str, str], current_user: Row, turn_order_service: TurnOrderService, token_service: TokenService) -> Response[dict[str, Any]]:
    body, user, early = await _body_and_auth(request, cookies, current_user)
    if early is not None:
        return early
    assert body is not None and user is not None
    result = turn_order_service.set_turn(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=user["id"],
        turn_index=int(body.get("turn_index") or 0),
    )
    await _broadcast(result, user_id=user["id"], event=TransportEvent.COMBAT_STATE_UPDATED, token_service=token_service)
    return _response(result)


@post("/game/combat/round/next")
async def next_combat_round_v1(request: Request, cookies: dict[str, str], current_user: Row, turn_order_service: TurnOrderService, token_service: TokenService) -> Response[dict[str, Any]]:
    body, user, early = await _body_and_auth(request, cookies, current_user)
    if early is not None:
        return early
    assert body is not None and user is not None
    result = turn_order_service.next_round(campaign_id=str(body.get("campaign_id", "")), user_id=user["id"])
    await _broadcast(result, user_id=user["id"], event=TransportEvent.COMBAT_ROUND_STARTED, token_service=token_service)
    return _response(result)


                                                                 
@post("/game/combat/next-round")
async def next_combat_round(request: Request, cookies: dict[str, str], current_user: Row, turn_order_service: TurnOrderService, token_service: TokenService) -> Response[dict[str, Any]]:
    return await next_combat_round_v1(request, cookies, current_user, turn_order_service, token_service)
