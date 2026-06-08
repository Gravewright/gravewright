from __future__ import annotations

from typing import Annotated

from litestar import post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from app.persistence.rows import Row

from litestar.response import Redirect, Template

from app.actions.inside.campaign_forms import CampaignIdForm
from app.actions.inside.render_inside import render_inside
from app.business.campaigns.campaign_service import CampaignService
from app.engine.systems.system_install_service import SystemInstallService
from app.engine.modules.module_install_service import ModuleInstallService
from app.helpers.auth import require_user
from app.helpers.view import view_context


@post("/campaigns/request-delete", guards=[require_user])
async def request_delete_campaign(
    cookies: dict[str, str],
    current_user: Row,
    campaign_service: CampaignService,
    system_install_service: SystemInstallService,
    module_install_service: ModuleInstallService,
    data: Annotated[CampaignIdForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect | Template:
    user = current_user
    result = campaign_service.generate_delete_code(
        campaign_id=data.campaign_id,
        user_id=user["id"],
    )

    t = view_context(cookies)["t"]

    if not result.success:
        return render_inside(
            cookies=cookies,
            user=user,
            campaign_service=campaign_service,
            system_install_service=system_install_service,
            module_install_service=module_install_service,
            campaign_error=t(result.error_key or "inside.campaigns.errors.delete_code_failed"),
        )

    return render_inside(
        cookies=cookies,
        user=user,
        campaign_service=campaign_service,
        system_install_service=system_install_service,
        module_install_service=module_install_service,
        pending_delete_campaign_id=data.campaign_id,
        removal_code=result.removal_code,
    )