from __future__ import annotations

from typing import Annotated

from litestar import post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from app.persistence.rows import Row

from litestar.response import Redirect, Template

from app.actions.inside.campaign_forms import UpdateCampaignForm
from app.actions.inside.render_inside import render_inside
from app.business.campaigns.campaign_service import CampaignService
from app.engine.sdk.package_install_service import PackageInstallService
from app.helpers.auth import require_user
from app.helpers.view import view_context


@post("/campaigns/update", guards=[require_user])
async def update_campaign(
    cookies: dict[str, str],
    current_user: Row,
    campaign_service: CampaignService,
    package_install_service: PackageInstallService,
    data: Annotated[UpdateCampaignForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect | Template:
    user = current_user
    result = campaign_service.update_campaign(
        campaign_id=data.campaign_id,
        user_id=user["id"],
        title=data.title,
        description=data.description,
    )

    if result.success:
        return Redirect(path="/inside")

    t = view_context(cookies)["t"]

    return render_inside(
        cookies=cookies,
        user=user,
        campaign_service=campaign_service,
        package_install_service=package_install_service,
        campaign_error=t(result.error_key or "inside.campaigns.errors.update_failed"),
    )