from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from urllib.parse import quote

from litestar import Request, get, post
from litestar.connection import ASGIConnection
from litestar.enums import RequestEncodingType
from litestar.params import Body, FromPath, FromQuery
from litestar.response import Redirect, Response
from litestar.exceptions import NotFoundException

from app.business.campaigns.campaign_join_code_service import CampaignJoinCodeService
from app.config import config
from app.helpers.async_blocking import run_blocking
from app.helpers.auth import require_user
from app.helpers.http_responses import json_error, json_ok
from app.helpers.pending_join_code import (
    clear_pending_join_code,
    get_pending_join_code,
    store_pending_join_code,
)
from app.helpers.request import get_client_ip
from app.persistence.rows import Row
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


_NO_STORE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
}


def require_join_code_feature(connection: ASGIConnection, _) -> None:
    if not config.campaign_join_code_enabled:
        raise NotFoundException()


@dataclass
class GenerateJoinCodeForm:
    campaign_id: str = ""
    expires_in_hours: int | None = None
    max_uses: int | None = None
    role: str = "player"


@dataclass
class CampaignJoinCodeForm:
    campaign_id: str = ""


@dataclass
class RedeemJoinCodeForm:
    code: str = ""


@post(
    "/campaigns/join-code/generate",
    guards=[require_join_code_feature, require_user],
    sync_to_thread=True,
)
def generate_campaign_join_code(
    current_user: Row,
    campaign_join_code_service: CampaignJoinCodeService,
    data: Annotated[GenerateJoinCodeForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response:
    result = campaign_join_code_service.generate_or_rotate(
        campaign_id=data.campaign_id,
        user_id=str(current_user["id"]),
        expires_in_hours=data.expires_in_hours,
        max_uses=data.max_uses,
        role=data.role,
    )
    if not result.success:
        status_code = (
            403 if result.error_key == "campaign.join_code.errors.permission_denied" else 400
        )
        return json_error(
            error_key=result.error_key or "campaign.join_code.errors.unavailable",
            status_code=status_code,
        )
    return json_ok(
        message_key=result.message_key,
        data={"code": result.code, **result.payload},
        headers=_NO_STORE,
    )


@post(
    "/campaigns/join-code/revoke",
    guards=[require_join_code_feature, require_user],
    sync_to_thread=True,
)
def revoke_campaign_join_code(
    current_user: Row,
    campaign_join_code_service: CampaignJoinCodeService,
    data: Annotated[CampaignJoinCodeForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response:
    result = campaign_join_code_service.revoke(
        campaign_id=data.campaign_id, user_id=str(current_user["id"])
    )
    if not result.success:
        status_code = (
            403 if result.error_key == "campaign.join_code.errors.permission_denied" else 400
        )
        return json_error(
            error_key=result.error_key or "campaign.join_code.errors.unavailable",
            status_code=status_code,
        )
    return json_ok(message_key=result.message_key, data=result.payload, headers=_NO_STORE)


@get(
    "/campaigns/join-code/status",
    guards=[require_join_code_feature, require_user],
    sync_to_thread=True,
)
def campaign_join_code_status(
    campaign_id: FromQuery[str],
    current_user: Row,
    campaign_join_code_service: CampaignJoinCodeService,
) -> Response:
    result = campaign_join_code_service.status(
        campaign_id=campaign_id, user_id=str(current_user["id"])
    )
    if not result.success:
        status_code = (
            403 if result.error_key == "campaign.join_code.errors.permission_denied" else 400
        )
        return json_error(
            error_key=result.error_key or "campaign.join_code.errors.unavailable",
            status_code=status_code,
        )
    return json_ok(data=result.payload, headers=_NO_STORE)


@post("/campaigns/join-code/redeem", guards=[require_join_code_feature, require_user])
async def redeem_campaign_join_code(
    request: Request,
    current_user: Row,
    campaign_join_code_service: CampaignJoinCodeService,
    data: Annotated[RedeemJoinCodeForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response:
    pending_code = get_pending_join_code(request.session)
    code = data.code.strip() or pending_code or ""
    result = await run_blocking(
        campaign_join_code_service.redeem,
        code=code,
        user_id=str(current_user["id"]),
        client_ip=get_client_ip(request),
    )
    if not result.success:
        if not data.code.strip():
            request.set_session(clear_pending_join_code(request.session))
        status_code = 429 if result.rate_limited else 400
        return json_error(
            error_key=result.error_key or "campaign.join_code.errors.unavailable",
            status_code=status_code,
        )

    request.set_session(clear_pending_join_code(request.session))
    if result.payload.get("membership_created"):
        campaign = result.payload.get("campaign") or {}
        member = result.payload.get("member") or {}
        await RealtimeTransport().to_room(
            room_id=str(campaign["id"]),
            event=TransportEvent.MEMBER_JOINED,
            payload={
                "room_id": campaign["id"],
                "player": {
                    "user_id": member["user_id"],
                    "name": member["name"],
                    "role": member["role"],
                    "is_online": False,
                },
            },
        )
    campaign = result.payload.get("campaign") or {}
    return json_ok(
        message_key=result.message_key,
        data={**result.payload, "redirect": f"/game?room={quote(str(campaign['id']))}"},
        headers=_NO_STORE,
    )


@get("/join/{code:str}", guards=[require_join_code_feature], sync_to_thread=False)
def capture_campaign_join_code(
    code: FromPath[str], request: Request, current_user: Row | None
) -> Redirect:
    request.set_session(store_pending_join_code(request.session, code))
    return Redirect(path="/login" if current_user is None else "/inside?join_code_pending=1")


route_handlers = [
    generate_campaign_join_code,
    revoke_campaign_join_code,
    campaign_join_code_status,
    redeem_campaign_join_code,
    capture_campaign_join_code,
]
