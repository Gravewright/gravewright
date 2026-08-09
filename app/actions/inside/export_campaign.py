from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from litestar import post
from litestar.enums import RequestEncodingType
from litestar.exceptions import NotFoundException
from litestar.params import Body
from litestar.response import Response

from app.business.audit import AuditService
from app.business.campaigns.campaign_export_service import (
    CampaignExportOptions, CampaignExportService,
)
from app.config import config
from app.helpers.auth import require_user
from app.persistence.rows import Row


@dataclass
class CampaignExportForm:
    campaign_id: str = ""
    packages: bool = False
    scenes: bool = False
    actors: bool = False
    items: bool = False
    journals: bool = False
    settings: bool = False


@post(
    "/campaigns/export", guards=[require_user], sync_to_thread=True,
)
def export_campaign(
    current_user: Row,
    campaign_export_service: CampaignExportService,
    audit_service: AuditService,
    data: Annotated[CampaignExportForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response:
    if not config.campaign_export_enabled:
        raise NotFoundException()
    result = campaign_export_service.export(
        campaign_id=data.campaign_id.strip(), user_id=str(current_user["id"]),
        options=CampaignExportOptions(
            packages=data.packages, scenes=data.scenes, actors=data.actors,
            items=data.items, journals=data.journals, settings=data.settings,
        ),
    )
    if not result.success:
        status = 403 if result.error_key == "campaign.export.errors.denied" else 400
        return Response({"ok": False, "error_key": result.error_key}, status_code=status)
    audit_service.record(
        campaign_id=data.campaign_id.strip(), actor_user_id=str(current_user["id"]),
        event_type="campaign.exported", subject_type="campaign",
        subject_id=data.campaign_id.strip(), action="export", result="success",
        metadata={
            "format_version": result.manifest["version"],
            "selected_count": len(result.manifest["selected"]),
        },
    )
    return Response(
        content=result.archive or b"", media_type="application/zip", status_code=200,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
