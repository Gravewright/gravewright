from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from litestar import post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Response

from app.business.users import UserPreferenceService
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.rows import Row
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


@dataclass
class UpdatePingPreferenceForm:
    ping_color: str = ""


@post("/game/preferences/ping")
async def update_ping_preference(
    current_user: Row,
    user_preference_service: UserPreferenceService,
    data: Annotated[UpdatePingPreferenceForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, Any]]:
    result = user_preference_service.set_ping_color(
        user_id=current_user["id"], ping_color=data.ping_color
    )
    if not result.success:
        return Response({"error_key": result.error_key}, status_code=400)
    user_id = str(current_user["id"])
    transport = RealtimeTransport()
    for campaign in CampaignRepository().list_for_user(user_id):
        await transport.to_room(
            room_id=str(campaign["id"]),
            event=TransportEvent.USER_PRESENTATION_CHANGED,
            payload={"user_id": user_id, "color": result.ping_color},
        )
    return Response({"ok": True, "ping_color": result.ping_color}, status_code=200)
