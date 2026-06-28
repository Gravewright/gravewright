from __future__ import annotations

import inspect
from typing import Any

from litestar import Request
from litestar import get
from litestar import post
from litestar.params import FromPath
from litestar.response import Response

from app.engine.chat.chat_service import ChatService
from app.engine.decks.card_asset_service import CardAssetService
from app.engine.decks.card_service import CardService
from app.engine.decks.cards import CardFaceState
from app.engine.decks.cards import DrawDestination
from app.engine.decks.cards import DrawMode
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
        event=TransportEvent.CARDS_STATE_UPDATED,
        payload={"room_id": campaign_id, "updated_by": user_id},
    )


@get("/game/cards/state/{campaign_id:str}")
async def get_card_state(
    campaign_id: FromPath[str],
    current_user: dict,
    card_service: CardService,
) -> Response[dict[str, Any]]:
    result = card_service.get_state(campaign_id=campaign_id, user_id=current_user["id"])
    return _response(result)


@post("/game/cards/decks")
async def create_card_deck(
    request: Request,
    current_user: dict,
    card_service: CardService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    raw_cards = body.get("cards") if isinstance(body.get("cards"), list) else []
    result = card_service.create_deck_definition(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        name=str(body.get("name") or ""),
        description=body.get("description") if isinstance(body.get("description"), str) else None,
        cards=[card for card in raw_cards if isinstance(card, dict)],
        default_back_asset_id=body.get("default_back_asset_id") if isinstance(body.get("default_back_asset_id"), str) else None,
        metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else {},
    )
    if result.success:
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result, status_code=201)


@post("/game/cards/assets/upload")
async def upload_card_asset(
    request: Request,
    current_user: dict,
    card_asset_service: CardAssetService,
) -> Response[dict[str, Any]]:
    form = await request.form()
    upload = form.get("file")
    result = card_asset_service.upload_image(
        campaign_id=str(form.get("campaign_id") or ""),
        user_id=current_user["id"],
        filename=str(getattr(upload, "filename", "") or ""),
        content_type=str(getattr(upload, "content_type", "") or ""),
        data=await _read_upload_file(upload),
        purpose=str(form.get("purpose") or "card_front"),
    )
    if not result.success:
        code = 403 if result.error_key == "permissions.errors.denied" else 400
        return Response({"error_key": result.error_key}, status_code=code)
    return Response(
        {
            "asset_id": result.asset_id,
            "src": result.src,
            "width": result.width,
            "height": result.height,
            "content_type": result.content_type,
            "byte_size": result.byte_size,
            "sha256": result.sha256,
        },
        status_code=201,
    )


@post("/game/cards/decks/instantiate")
async def instantiate_card_deck(
    request: Request,
    current_user: dict,
    card_service: CardService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    result = card_service.instantiate_deck(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        deck_definition_id=str(body.get("deck_definition_id") or ""),
        name=body.get("name") if isinstance(body.get("name"), str) else None,
    )
    if result.success:
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result, status_code=201)


@post("/game/cards/decks/delete")
async def delete_card_deck(
    request: Request,
    current_user: dict,
    card_service: CardService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    result = card_service.delete_deck_instance(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        deck_instance_id=str(body.get("deck_instance_id") or ""),
    )
    if result.success:
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result)


@post("/game/cards/decks/shuffle")
async def shuffle_card_deck(
    request: Request,
    current_user: dict,
    card_service: CardService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    result = card_service.shuffle(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        deck_instance_id=str(body.get("deck_instance_id") or ""),
    )
    if result.success:
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result)


@post("/game/cards/decks/reset")
async def reset_card_deck(
    request: Request,
    current_user: dict,
    card_service: CardService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    result = card_service.reset(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        deck_instance_id=str(body.get("deck_instance_id") or ""),
        shuffle=bool(body.get("shuffle", True)),
    )
    if result.success:
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result)


@post("/game/cards/draw")
async def draw_cards(
    request: Request,
    current_user: dict,
    card_service: CardService,
    chat_service: ChatService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    try:
        destination = DrawDestination(str(body.get("destination") or DrawDestination.HAND.value))
    except ValueError:
        destination = DrawDestination.HAND
    try:
        mode = DrawMode(str(body.get("mode") or DrawMode.TOP.value))
    except ValueError:
        mode = DrawMode.TOP
    result = card_service.draw(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        deck_instance_id=str(body.get("deck_instance_id") or ""),
        count=int(body.get("count") or 1),
        destination=destination,
        mode=mode,
        target_pile_id=body.get("target_pile_id") if isinstance(body.get("target_pile_id"), str) else None,
        reveal=bool(body.get("reveal")),
    )
    if result.success:
        if destination == DrawDestination.CHAT:
            cards = result.payload.get("cards") if isinstance(result.payload.get("cards"), list) else []
            count_label = len(cards) if cards else int(body.get("count") or 1)
            content = f"{current_user.get('name') or 'Player'} revealed {count_label} card"
            if count_label != 1:
                content += "s"
            await chat_service.send_card_message(
                campaign_id=campaign_id,
                sender_user_id=current_user["id"],
                sender_name=str(current_user.get("name") or "Player"),
                content=content,
                cards=cards,
                card_event=result.payload.get("event") if isinstance(result.payload.get("event"), dict) else {},
                transport=RealtimeTransport(),
            )
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result)


@post("/game/cards/reveal")
async def reveal_cards(
    request: Request,
    current_user: dict,
    card_service: CardService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    card_ids = body.get("card_ids") if isinstance(body.get("card_ids"), list) else []
    result = card_service.reveal(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        card_ids=[str(card_id) for card_id in card_ids],
    )
    if result.success:
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result)


@post("/game/cards/discard")
async def discard_cards(
    request: Request,
    current_user: dict,
    card_service: CardService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    card_ids = body.get("card_ids") if isinstance(body.get("card_ids"), list) else []
    result = card_service.discard(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        card_ids=[str(card_id) for card_id in card_ids],
    )
    if result.success:
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result)


@post("/game/cards/play-to-scene")
async def play_card_to_scene(
    request: Request,
    current_user: dict,
    card_service: CardService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    result = card_service.play_to_scene(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        card_id=str(body.get("card_id") or ""),
        scene_id=str(body.get("scene_id") or ""),
        x=float(body.get("x") or 0),
        y=float(body.get("y") or 0),
        rotation=float(body.get("rotation") or 0),
        scale=float(body.get("scale") or 1),
        reveal=bool(body.get("reveal", True)),
    )
    if result.success:
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result)


@post("/game/cards/scene-placement/update")
async def update_scene_card_placement(
    request: Request,
    current_user: dict,
    card_service: CardService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    face_state = None
    if isinstance(body.get("face_state"), str):
        try:
            face_state = CardFaceState(str(body.get("face_state")))
        except ValueError:
            face_state = None
    result = card_service.update_scene_placement(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        placement_id=str(body.get("placement_id") or ""),
        x=float(body["x"]) if body.get("x") is not None else None,
        y=float(body["y"]) if body.get("y") is not None else None,
        rotation=float(body["rotation"]) if body.get("rotation") is not None else None,
        scale=float(body["scale"]) if body.get("scale") is not None else None,
        z_index=int(body["z_index"]) if body.get("z_index") is not None else None,
        face_state=face_state,
    )
    if result.success:
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result)


@post("/game/cards/scene-placement/discard")
async def discard_scene_card_placement(
    request: Request,
    current_user: dict,
    card_service: CardService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    campaign_id = str(body.get("campaign_id") or "")
    result = card_service.discard_scene_placement(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        placement_id=str(body.get("placement_id") or ""),
    )
    if result.success:
        await _broadcast_state(campaign_id, current_user["id"])
    return _response(result)
