from __future__ import annotations

from app.persistence.rows import Row
from typing import Any

from litestar import post
from litestar.response import Response

from app.business.campaigns.campaign_service import CampaignService
from app.realtime.presence import PresenceService
from app.realtime.transport import RealtimeTransport


@post("/game/presence/leave")
async def leave_game(
    cookies: dict[str, str],
    current_user: Row,
    campaign_service: CampaignService,
    presence_service: PresenceService,
) -> Response[dict[str, Any]]:
    user = current_user
    transport = RealtimeTransport()

    rooms = campaign_service.list_for_user(user["id"])
    room_ids = [room["id"] for room in rooms]

    await presence_service.leave(
        user_id=user["id"],
        room_ids=room_ids,
        transport=transport,
    )

    return Response(
        content={
            "ok": True,
        },
        status_code=200,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )
