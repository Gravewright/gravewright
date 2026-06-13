from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from litestar import post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect

from app.persistence.rows import Row

from app.business.campaigns.campaign_system_service import CampaignSystemService
from app.helpers.auth import require_user
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


@dataclass
class SetCampaignSystemForm:
    campaign_id: str = ""
    system_id: str = ""


@post("/campaigns/set-system", guards=[require_user])
async def set_campaign_system(
    cookies: dict[str, str],
    current_user: Row,
    campaign_system_service: CampaignSystemService,
    data: Annotated[SetCampaignSystemForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    user = current_user
    system_id = data.system_id.strip() or None
    result = campaign_system_service.assign_to_campaign(
        campaign_id=data.campaign_id,
        user_id=user["id"],
        system_id=system_id,
    )

    if not result.success:
        return Redirect(path=f"/game?room={data.campaign_id}&system_error_key={result.error_key}")



    await RealtimeTransport().to_room(
        room_id=data.campaign_id,
        event=TransportEvent.CAMPAIGN_SYSTEM_CHANGED,
        payload={
            "room_id": data.campaign_id,
            "system_id": system_id,
            "area_markers": campaign_system_service.area_marker_presets(system_id),
        },
    )

    return Redirect(path=f"/game?room={data.campaign_id}&system_message_key=inside.systems.assigned")
