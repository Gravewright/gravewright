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
from app.helpers.http_responses import json_error, json_ok, wants_json


@dataclass
class InviteToCampaignForm:
    campaign_id: str = ""
    email: str = ""
    role: str = ""


@post("/campaigns/invitations", sync_to_thread=True)
def invite_to_campaign(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    campaign_invitation_service: CampaignInvitationService,
    data: Annotated[InviteToCampaignForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, str | bool]] | Redirect:
    user = current_user
    json_response = wants_json(request)

    result = campaign_invitation_service.create_invitation(
        campaign_id=data.campaign_id,
        invited_by_user_id=user["id"],
        invited_email=data.email,
        role=data.role,
    )

    if json_response:
        if result.success:
            return json_ok(message_key=result.message_key or "game.invite.success")
        return json_error(error_key=result.error_key or "game.invite.errors.invalid_email")

    if result.success:
        return Redirect(path=f"/game?invite_message_key={quote(result.message_key or '')}")

    return Redirect(path=f"/game?invite_error_key={quote(result.error_key or '')}")