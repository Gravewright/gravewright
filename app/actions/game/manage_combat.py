from __future__ import annotations

from typing import Any

from litestar import Request, get, post
from litestar.params import FromPath
from litestar.response import Response

from app.engine.chat.chat_service import ChatService
from app.engine.combat.combat_service import CombatResult, CombatService
from app.engine.tokens.token_service import TokenService
from app.persistence.rows import Row
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport

SCOPES = {"all", "npc", "missing"}


async def _body(request: Request) -> dict[str, Any]:
    try:
        parsed = await request.json()
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _response(result: CombatResult) -> Response[dict[str, Any]]:
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    return Response(result.state_payload(), status_code=200)


def _str_list(raw: Any) -> list[str]:
    return [str(item) for item in raw][:64] if isinstance(raw, list) else []


def _tick_message(tick: dict) -> str:
    name = tick.get("actor_name") or tick.get("name") or "?"
    amount = tick.get("amount") or 0
    after = tick.get("value_after")
    suffix = f" (HP {after})" if after is not None else ""
    if tick.get("operation") == "heal_over_time":
        return f"💚 {name} recuperou {amount} de vida{suffix}."
    damage_type = tick.get("damage_type")
    typed = f" de {damage_type}" if damage_type else ""
    return f"🩸 {name} sofreu {amount} de dano{typed}{suffix}."


async def _publish(
    result: CombatResult, *, user_id: str, event: TransportEvent, token_service: TokenService
) -> None:
    """Broadcast the new state, then anything the turn changed off to the side.

    Effect ticks reach the table as chat messages and as sheet/token refreshes,
    because the combat payload alone would not tell an open sheet to redraw.
    """
    if not result.success:
        return
    room_id = str(result.campaign_id or (result.combat or {}).get("campaign_id") or "")
    if not room_id:
        return
    transport = RealtimeTransport()
    await transport.to_room(
        room_id=room_id, event=event, payload=result.state_payload() | {"updated_by": user_id}
    )

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
        await token_service.refresh_actor_tokens(
            campaign_id=room_id, actor_id=actor_id, transport=transport
        )

    if result.effect_ticks:
        chat = ChatService()
        for tick in result.effect_ticks:
            await chat.send_system_message(
                campaign_id=room_id, content=_tick_message(tick), transport=transport
            )


@get("/game/combat/state/{campaign_id:str}")
async def get_combat_state(
    campaign_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    combat_service: CombatService,
) -> Response[dict[str, Any]]:
    return _response(
        combat_service.get_state(campaign_id=campaign_id, user_id=current_user["id"])
    )


@post("/game/combat/start")
async def start_combat(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    combat_service: CombatService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    body = await _body(request)
    result = combat_service.start(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=current_user["id"],
        scene_id=str(body.get("scene_id") or "") or None,
        actor_ids=_str_list(body.get("actor_ids")),
        token_ids=_str_list(body.get("token_ids")),
    )
    await _publish(
        result,
        user_id=current_user["id"],
        event=TransportEvent.COMBAT_STARTED,
        token_service=token_service,
    )
    return _response(result)


@post("/game/combat/end")
async def end_combat(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    combat_service: CombatService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    body = await _body(request)
    result = combat_service.end(
        campaign_id=str(body.get("campaign_id", "")), user_id=current_user["id"]
    )
    await _publish(
        result,
        user_id=current_user["id"],
        event=TransportEvent.COMBAT_ENDED,
        token_service=token_service,
    )
    return _response(result)


@post("/game/combat/combatants/add")
async def add_combatants(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    combat_service: CombatService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    body = await _body(request)
    result = combat_service.add_combatants(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=current_user["id"],
        actor_ids=_str_list(body.get("actor_ids")),
        token_ids=_str_list(body.get("token_ids")),
    )
    await _publish(
        result,
        user_id=current_user["id"],
        event=TransportEvent.COMBAT_UPDATED,
        token_service=token_service,
    )
    return _response(result)


@post("/game/combat/combatants/remove")
async def remove_combatant(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    combat_service: CombatService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    body = await _body(request)
    result = combat_service.remove_combatant(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=current_user["id"],
        combatant_id=str(body.get("combatant_id", "")),
    )
    await _publish(
        result,
        user_id=current_user["id"],
        event=TransportEvent.COMBAT_UPDATED,
        token_service=token_service,
    )
    return _response(result)


@post("/game/combat/combatants/flags")
async def update_combatant_flags(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    combat_service: CombatService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    """Toggle ``hidden`` (players cannot see who it is) or ``defeated``."""
    body = await _body(request)
    hidden = body.get("hidden")
    defeated = body.get("defeated")
    result = combat_service.set_flags(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=current_user["id"],
        combatant_id=str(body.get("combatant_id", "")),
        hidden=None if hidden is None else bool(hidden),
        defeated=None if defeated is None else bool(defeated),
    )
    await _publish(
        result,
        user_id=current_user["id"],
        event=TransportEvent.COMBAT_UPDATED,
        token_service=token_service,
    )
    return _response(result)


@post("/game/combat/initiative/roll")
async def roll_initiative(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    combat_service: CombatService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    """``scope`` is ``all``, ``npc`` or ``missing``; ``combatant_id`` rolls just one."""
    body = await _body(request)
    scope = str(body.get("scope") or "all")
    result = combat_service.roll_initiative(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=current_user["id"],
        scope=scope if scope in SCOPES else "all",
        combatant_id=str(body.get("combatant_id") or ""),
    )
    await _publish(
        result,
        user_id=current_user["id"],
        event=TransportEvent.COMBAT_UPDATED,
        token_service=token_service,
    )
    return _response(result)


@post("/game/combat/initiative/set")
async def set_initiative(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    combat_service: CombatService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    """``value`` is whatever the GM typed; the system decides how to read it.

    An empty or missing value clears the initiative.
    """
    body = await _body(request)
    raw = body.get("value")
    result = combat_service.set_initiative(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=current_user["id"],
        combatant_id=str(body.get("combatant_id", "")),
        value=None if raw is None else str(raw),
    )
    await _publish(
        result,
        user_id=current_user["id"],
        event=TransportEvent.COMBAT_UPDATED,
        token_service=token_service,
    )
    return _response(result)


@post("/game/combat/order")
async def move_combatant(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    combat_service: CombatService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    """Slide a combatant one place through a hand-arranged order.

    Only reaches anywhere on systems whose initiative is not sorted by value.
    """
    body = await _body(request)
    result = combat_service.move_combatant(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=current_user["id"],
        combatant_id=str(body.get("combatant_id", "")),
        delta=-1 if int(body.get("delta") or 1) < 0 else 1,
    )
    await _publish(
        result,
        user_id=current_user["id"],
        event=TransportEvent.COMBAT_UPDATED,
        token_service=token_service,
    )
    return _response(result)


@post("/game/combat/turn")
async def change_turn(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    combat_service: CombatService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    """``combatant_id`` jumps to a combatant; otherwise ``delta`` steps ±1."""
    body = await _body(request)
    combatant_id = str(body.get("combatant_id") or "")
    if combatant_id:
        result = combat_service.set_turn(
            campaign_id=str(body.get("campaign_id", "")),
            user_id=current_user["id"],
            combatant_id=combatant_id,
        )
    else:
        result = combat_service.advance_turn(
            campaign_id=str(body.get("campaign_id", "")),
            user_id=current_user["id"],
            delta=-1 if int(body.get("delta") or 1) < 0 else 1,
        )
    await _publish(
        result,
        user_id=current_user["id"],
        event=TransportEvent.COMBAT_UPDATED,
        token_service=token_service,
    )
    return _response(result)


@post("/game/combat/round")
async def change_round(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    combat_service: CombatService,
    token_service: TokenService,
) -> Response[dict[str, Any]]:
    body = await _body(request)
    result = combat_service.advance_round(
        campaign_id=str(body.get("campaign_id", "")),
        user_id=current_user["id"],
        delta=-1 if int(body.get("delta") or 1) < 0 else 1,
    )
    await _publish(
        result,
        user_id=current_user["id"],
        event=TransportEvent.COMBAT_UPDATED,
        token_service=token_service,
    )
    return _response(result)
