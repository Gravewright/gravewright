from __future__ import annotations

from dataclasses import dataclass
from app.persistence.rows import Row
from typing import Annotated
from urllib.parse import quote

from litestar import Request
from litestar import post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect
from litestar.response import Response

from app.business.campaigns.campaign_invitation_service import CampaignInvitationService
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


@dataclass
class AcceptCampaignInvitationForm:
    invitation_id: str = ""


def wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    requested_with = request.headers.get("x-requested-with", "")

    return "application/json" in accept or requested_with == "XMLHttpRequest"


@post("/campaigns/invitations/accept")
async def accept_campaign_invitation(
    request: Request,
    cookies: dict[str, str],
    current_user: Row | None,
    campaign_invitation_service: CampaignInvitationService,
    data: Annotated[AcceptCampaignInvitationForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, object]] | Redirect:
    user = current_user
    json_response = wants_json(request)

    if user is None:
        if json_response:
            return Response(
                content={
                    "ok": False,
                    "error_key": "auth.errors.session_expired",
                },
                status_code=401,
            )

        return Redirect(path="/login")

    result = campaign_invitation_service.accept_invitation(
        invitation_id=data.invitation_id,
        user_id=user["id"],
    )

    if result.success and result.payload.get("campaign") and result.payload.get("member"):
        campaign = result.payload["campaign"]
        member = result.payload["member"]
        await RealtimeTransport().to_room(
            room_id=str(campaign["id"]),
            event=TransportEvent.MEMBER_JOINED,
            payload={
                "room_id": campaign["id"],
                "player": {
                    "user_id": member["user_id"],
                    "name": member["name"],
                    "email": member["email"],
                    "role": member["role"],
                    "is_online": False,
                },
            },
        )

    if json_response:
        if result.success:
            return Response(
                content={
                    "ok": True,
                    "message_key": result.message_key or "inside.invitations.accepted",
                    **result.payload,
                },
                status_code=200,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                },
            )

        return Response(
            content={
                "ok": False,
                "error_key": result.error_key or "inside.invitations.errors.not_found",
            },
            status_code=400,
        )

    if result.success:
        return Redirect(path=f"/inside?invitation_message_key={quote(result.message_key or '')}")

    return Redirect(path=f"/inside?invitation_error_key={quote(result.error_key or '')}")
