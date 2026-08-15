from __future__ import annotations

from dataclasses import dataclass
from app.persistence.rows import Row
from typing import Annotated
from typing import Any

from litestar import Request
from litestar import post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect
from litestar.response import Response

from app.business.campaigns.campaign_service import CampaignService
from app.helpers.async_blocking import run_blocking
from app.helpers.http_responses import wants_json
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport
from app.realtime.transport import websocket_manager


@dataclass
class BanMemberForm:
    campaign_id: str = ""
    user_id: str = ""


@post("/game/member/ban")
async def ban_member(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    campaign_service: CampaignService,
    data: Annotated[BanMemberForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, Any]] | Redirect:
    user = current_user
    json_response = wants_json(request)



    result = await run_blocking(
        campaign_service.ban_member,
        campaign_id=data.campaign_id,
        requester_user_id=user["id"],
        target_user_id=data.user_id,
    )

    if result.success and result.member is not None:
        transport = RealtimeTransport()
        removal_payload = {
            "room_id": data.campaign_id,
            "user_id": result.member["user_id"],
            "name": result.member["name"],
            "role": result.member["role"],
            "reason": "banned",
        }
        # The banned member is no longer present in room_user_ids. Deliver the
        # redirect event explicitly before closing their live room sockets.
        await transport.to_player(
            player_id=result.member["user_id"],
            event=TransportEvent.MEMBER_REMOVED,
            payload=removal_payload,
        )
        await transport.to_players(
            player_ids=result.room_user_ids or [],
            event=TransportEvent.MEMBER_REMOVED,
            payload=removal_payload,
        )
        await websocket_manager.evict_user_from_room(
            user_id=result.member["user_id"],
            room_id=data.campaign_id,
        )

    if json_response:
        if result.success:
            return Response(
                content={"ok": True, "message_key": "game.players.banned"},
                status_code=200,
            )
        return Response(
            content={"ok": False, "error_key": result.error_key or "game.players.errors.not_found"},
            status_code=400,
        )

    return Redirect(path="/game")
