from __future__ import annotations

from app.persistence.rows import Row

from litestar import get
from litestar.params import FromPath
from litestar.response import Redirect, Template

from app.business.campaigns.campaign_service import CampaignService
from app.business.permissions import PermissionService
from app.helpers.view import view_context


@get("/game/popup/permissions/{campaign_id:str}")
async def show_permissions_popup(
    campaign_id: FromPath[str],
    cookies: dict[str, str],
    current_user: Row,
    campaign_service: CampaignService,
    permission_service: PermissionService,
) -> Redirect | Template:
    user = current_user
    campaigns = campaign_service.list_for_user(user["id"])
    campaign = next((dict(c) for c in campaigns if c["id"] == campaign_id), None)
    if campaign is None:
        return Redirect(path="/game")

    campaign["permission_settings"] = permission_service.build_settings_context(
        campaign_id=campaign["id"],
        user_id=user["id"],
        member_role=campaign["member_role"],
    )

    return Template(
        template_name="pages/game/permissions_popup.html",
        context=view_context(
            cookies,
            room=campaign,
        ),
    )
