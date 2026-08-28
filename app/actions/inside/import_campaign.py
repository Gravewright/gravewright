from __future__ import annotations

from litestar import Request, post
from litestar.exceptions import NotFoundException
from litestar.response import Redirect, Response

from app.business.campaigns.campaign_import_service import CampaignImportService
from app.config import config
from app.helpers.auth import require_user
from app.helpers.http_responses import json_error, json_ok, wants_json
from app.persistence.rows import Row


@post(
    "/campaigns/import",
    guards=[require_user],
    request_max_body_size=None,
)
async def import_campaign(
    request: Request,
    current_user: Row,
    campaign_import_service: CampaignImportService,
) -> Redirect | Response:
    if not config.campaign_export_enabled:
        raise NotFoundException()
    form = await request.form()
    upload = form.get("campaign_file")
    reader = getattr(upload, "read", None)
    if reader is None:
        if wants_json(request):
            return json_error(error_key="campaign.import.errors.invalid")
        return Redirect(path="/inside?campaign_error_key=campaign.import.errors.invalid")
    archive = await reader()
    result = campaign_import_service.import_archive(
        archive=archive,
        user_id=str(current_user["id"]),
        title=str(form.get("title") or ""),
    )
    if not result.success:
        if wants_json(request):
            return json_error(error_key=result.error_key or "campaign.import.errors.failed")
        return Redirect(path=f"/inside?campaign_error_key={result.error_key or 'campaign.import.errors.failed'}")
    if wants_json(request):
        return json_ok(
            message_key="campaign.import.created",
            data={"campaign_id": result.campaign_id, "summary": result.summary},
        )
    return Redirect(path="/inside?campaign_message_key=campaign.import.created")
