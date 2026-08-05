from __future__ import annotations

from dataclasses import dataclass
from app.persistence.rows import Row
from typing import Annotated, Any

from litestar import post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Response

from app.business.campaigns.campaign_service import CampaignService
from app.business.permissions import PermissionService
from app.domain.permissions.permissions import TablePermission


@dataclass
class UpdateTableSettingsForm:
    campaign_id: str = ""
    measure_flash_seconds: int = 6


@post("/game/settings/table")
async def update_table_settings(
    current_user: Row,
    data: Annotated[UpdateTableSettingsForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
    permission_service: PermissionService,
    campaign_service: CampaignService,
) -> Response[dict[str, Any]]:
    campaign_id = data.campaign_id.strip()
    if not campaign_id:
        return Response({"ok": False, "error_key": "inside.campaigns.errors.not_found"}, status_code=400)

    if not permission_service.can(
        campaign_id=campaign_id,
        user_id=current_user["id"],
        permission=TablePermission.SETTINGS_UPDATE_PERMISSIONS,
    ):
        return Response({"ok": False, "error_key": "permissions.errors.denied"}, status_code=403)

    seconds = max(1, min(60, int(data.measure_flash_seconds or 6)))
    result = campaign_service.update_measure_flash_seconds(
        campaign_id=campaign_id,
        seconds=seconds,
    )
    if not result.success:
        return Response({"ok": False, "error_key": "inside.campaigns.errors.not_found"}, status_code=404)

    return Response({"ok": True, "measure_flash_seconds": seconds}, status_code=200)
