from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from litestar import Request, get, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.params import FromPath
from litestar.response import Redirect, Response

from app.business.campaigns.streamer_link_service import StreamerLinkService
from app.config import config
from app.persistence.rows import Row


@dataclass
class StreamerLinkForm:
    campaign_id: str = ""


def _streamer_url(request: Request, token: str) -> str:
    """Public bearer URL for a streamer token.

    Prefer the configured ``PUBLIC_BASE_URL`` (canonical in production); fall
    back to the request's own base in development where it may be unset.
    """
    base = (config.public_base_url or "").rstrip("/")
    if not base:
        base = str(request.base_url).rstrip("/")
    return f"{base}/stream/{token}"


@post("/game/streamer-link")
async def generate_streamer_link(
    request: Request,
    current_user: Row,
    streamer_link_service: StreamerLinkService,
    data: Annotated[StreamerLinkForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, Any]]:
    campaign_id = data.campaign_id.strip()
    if not campaign_id:
        return Response({"ok": False, "error_key": "inside.campaigns.errors.not_found"}, status_code=400)

    result = streamer_link_service.generate(campaign_id=campaign_id, user_id=current_user["id"])
    if not result.success:
        status = 403 if result.error_key == "game.streamer.errors.gm_required" else 400
        return Response({"ok": False, "error_key": result.error_key}, status_code=status)

    return Response(
        {
            "ok": True,
            "url": _streamer_url(request, result.token or ""),
            "expires_at": result.expires_at,
        },
        status_code=200,
    )


@post("/game/streamer-link/revoke")
async def revoke_streamer_link(
    current_user: Row,
    streamer_link_service: StreamerLinkService,
    data: Annotated[StreamerLinkForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, Any]]:
    campaign_id = data.campaign_id.strip()
    if not campaign_id:
        return Response({"ok": False, "error_key": "inside.campaigns.errors.not_found"}, status_code=400)

    result = streamer_link_service.revoke(campaign_id=campaign_id, user_id=current_user["id"])
    if not result.success:
        status = 403 if result.error_key == "game.streamer.errors.gm_required" else 400
        return Response({"ok": False, "error_key": result.error_key}, status_code=status)

    return Response({"ok": True}, status_code=200)


@get("/stream/{token:str}")
async def consume_streamer_link(
    request: Request,
    token: FromPath[str],
    streamer_link_service: StreamerLinkService,
) -> Redirect:
    """Public bearer entrypoint: opens a read-only streamer guest session.

    No login required — the link itself is the credential. On success the visitor
    gets a ``streamer`` guest session (read-only by permission defaults) and is
    sent to the game. An invalid/expired/revoked token falls through to login.
    """
    resolved = streamer_link_service.consume(token=token)
    if resolved is None:
        return Redirect(path="/login")

    request.set_session({"user_id": resolved["guest_user_id"]})
    return Redirect(path="/game")
