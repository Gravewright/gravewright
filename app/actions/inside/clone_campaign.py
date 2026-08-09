from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from litestar import Request, post
from litestar.enums import RequestEncodingType
from litestar.exceptions import NotFoundException
from litestar.params import Body
from litestar.response import Redirect, Response

from app.business.campaigns.campaign_clone_service import (
    CampaignCloneOptions,
    CampaignCloneService,
)
from app.config import config
from app.helpers.http_responses import json_error, json_ok, wants_json
from app.helpers.auth import require_user
from app.persistence.rows import Row


@dataclass
class CloneCampaignForm:
    source_campaign_id: str = ""
    title: str = ""
    packages: bool = False
    scenes: bool = False
    actors: bool = False
    items: bool = False
    journals: bool = False
    settings: bool = False

    def options(self) -> CampaignCloneOptions:
        return CampaignCloneOptions(
            packages=self.packages,
            scenes=self.scenes,
            actors=self.actors,
            items=self.items,
            journals=self.journals,
            settings=self.settings,
        )


@post("/campaigns/clone/preview", guards=[require_user], sync_to_thread=True)
def preview_campaign_clone(
    current_user: Row,
    campaign_clone_service: CampaignCloneService,
    data: Annotated[CloneCampaignForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response:
    if not config.campaign_clone_enabled:
        raise NotFoundException()
    result = campaign_clone_service.preview(
        source_campaign_id=data.source_campaign_id,
        user_id=str(current_user["id"]),
        options=data.options(),
    )
    if not result.success:
        return json_error(
            error_key=result.error_key or "campaign.clone.errors.denied", status_code=403
        )
    return json_ok(data={"summary": result.summary})


@post("/campaigns/clone", guards=[require_user], sync_to_thread=True)
def clone_campaign(
    request: Request,
    current_user: Row,
    campaign_clone_service: CampaignCloneService,
    data: Annotated[CloneCampaignForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response | Redirect:
    if not config.campaign_clone_enabled:
        raise NotFoundException()
    result = campaign_clone_service.clone(
        source_campaign_id=data.source_campaign_id,
        user_id=str(current_user["id"]),
        title=data.title,
        options=data.options(),
    )
    if not result.success:
        status = 403 if result.error_key == "campaign.clone.errors.denied" else 400
        if wants_json(request):
            return json_error(
                error_key=result.error_key or "campaign.clone.errors.failed", status_code=status
            )
        return Redirect(path=f"/inside?campaign_error_key={result.error_key}")
    if wants_json(request):
        return json_ok(
            message_key="campaign.clone.completed",
            data={"campaign_id": result.campaign_id, "summary": result.summary},
        )
    return Redirect(path="/inside?campaign_message_key=campaign.clone.completed")
