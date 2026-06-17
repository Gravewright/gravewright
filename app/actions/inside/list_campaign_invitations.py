from __future__ import annotations

from app.persistence.rows import Row
from typing import Any

from litestar import get
from litestar.response import Redirect
from litestar.response import Response

from app.business.campaigns.campaign_invitation_service import CampaignInvitationService


@get("/inside/invitations/pending")
async def list_campaign_invitations(
    cookies: dict[str, str],
    current_user: Row | None,
    campaign_invitation_service: CampaignInvitationService,
) -> Response[dict[str, Any]] | Redirect:
    user = current_user

    if user is None:
        return Redirect(path="/login")

    invitations = campaign_invitation_service.list_pending_for_user(user["id"])

    return Response(
        content={
            "ok": True,
            "invitations": [dict(invitation) for invitation in invitations],
        },
        status_code=200,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )