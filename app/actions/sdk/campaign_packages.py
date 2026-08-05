"""Per-campaign SDK package activation routes (Campaign > Packages).

All of these are GM-only: setting the campaign ruleset and activating or
deactivating addon/theme/assets/content packages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any
from urllib.parse import quote

from litestar import Request, get, post
from litestar.enums import RequestEncodingType
from litestar.params import Body, FromQuery
from litestar.response import Redirect, Response

from app.domain.roles import PlayerRole
from app.engine.sdk.package_activation_service import PackageActivationService
from app.helpers.auth import require_user
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.rows import Row
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


@dataclass
class CampaignPackageForm:
    campaign_id: str = ""
    package_id: str = ""


def _wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "application/json" in accept


def _redirect(campaign_id: str, *, error_key: str | None = None, message_key: str | None = None) -> Redirect:
    query = f"room={quote(campaign_id)}"
    if error_key:
        query += f"&packages_error_key={quote(error_key)}"
    if message_key:
        query += f"&packages_message_key={quote(message_key)}"
    return Redirect(path=f"/inside?{query}")


def _is_gm(campaign_id: str, user_id: str) -> bool:
    role = CampaignRepository().get_member_role(campaign_id=campaign_id, user_id=user_id)
    return role == PlayerRole.GM.value


async def _emit_packages_changed(campaign_id: str, package_id: str, action: str) -> None:
    await RealtimeTransport().to_room(
        room_id=campaign_id,
        event=TransportEvent.CAMPAIGN_PACKAGES_CHANGED,
        payload={
            "room_id": campaign_id,
            "package_id": package_id,
            "action": action,
        },
    )


@get("/sdk/campaigns/packages", guards=[require_user], sync_to_thread=False)
def list_campaign_packages(
    campaign_id: FromQuery[str],
    current_user: Row,
    package_activation_service: PackageActivationService,
) -> Response[dict[str, Any]]:
    if not _is_gm(campaign_id, current_user["id"]):
        return Response({"error_key": "inside.campaigns.errors.gm_required"}, status_code=403)
    return Response(
        {
            "packages": package_activation_service.list_campaign_packages(campaign_id),
            "active_ruleset": package_activation_service.get_active_ruleset(campaign_id),
        }
    )


@post("/sdk/campaigns/packages/activate", guards=[require_user])
async def activate_campaign_package(
    request: Request,
    current_user: Row,
    package_activation_service: PackageActivationService,
    data: Annotated[CampaignPackageForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, Any]] | Redirect:
    json_response = _wants_json(request)
    if not _is_gm(data.campaign_id, current_user["id"]):
        if not json_response:
            return _redirect(data.campaign_id, error_key="inside.campaigns.errors.gm_required")
        return Response({"error_key": "inside.campaigns.errors.gm_required"}, status_code=403)
    result = package_activation_service.activate_package(
        data.campaign_id, data.package_id.strip(), current_user["id"]
    )
    if not result.success:
        if not json_response:
            return _redirect(data.campaign_id, error_key=result.error_key)
        return Response({"error_key": result.error_key}, status_code=400)
    await _emit_packages_changed(data.campaign_id, data.package_id.strip(), "activate")
    if not json_response:
        return _redirect(data.campaign_id, message_key="sdk.messages.campaign_enabled")
    return Response({"success": True})


@post("/sdk/campaigns/packages/deactivate", guards=[require_user])
async def deactivate_campaign_package(
    request: Request,
    current_user: Row,
    package_activation_service: PackageActivationService,
    data: Annotated[CampaignPackageForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, Any]] | Redirect:
    json_response = _wants_json(request)
    if not _is_gm(data.campaign_id, current_user["id"]):
        if not json_response:
            return _redirect(data.campaign_id, error_key="inside.campaigns.errors.gm_required")
        return Response({"error_key": "inside.campaigns.errors.gm_required"}, status_code=403)
    result = package_activation_service.deactivate_package(
        data.campaign_id, data.package_id.strip(), current_user["id"]
    )
    if not result.success:
        if not json_response:
            return _redirect(data.campaign_id, error_key=result.error_key)
        return Response({"error_key": result.error_key}, status_code=400)
    await _emit_packages_changed(data.campaign_id, data.package_id.strip(), "deactivate")
    if not json_response:
        return _redirect(data.campaign_id, message_key="sdk.messages.campaign_disabled")
    return Response({"success": True})


@post("/sdk/campaigns/ruleset", guards=[require_user])
async def set_campaign_ruleset(
    current_user: Row,
    package_activation_service: PackageActivationService,
    data: Annotated[CampaignPackageForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    """Set (or detach) the campaign ruleset. This is a form-driven GM action, so
    it redirects back to the table rather than returning JSON."""
    campaign_id = data.campaign_id
    if not _is_gm(campaign_id, current_user["id"]):
        return Redirect(path=f"/game?room={campaign_id}&system_error_key=inside.campaigns.errors.gm_required")
    package_id = data.package_id.strip() or None
    result = package_activation_service.set_campaign_ruleset(
        campaign_id, package_id, current_user["id"]
    )
    if not result.success:
        return Redirect(path=f"/game?room={campaign_id}&system_error_key={result.error_key}")

    details = package_activation_service.install.get_details(package_id) if package_id else None
    await RealtimeTransport().to_room(
        room_id=campaign_id,
        event=TransportEvent.CAMPAIGN_SYSTEM_CHANGED,
        payload={
            "room_id": campaign_id,
            "system_id": package_id,
            "area_markers": details.get("area_markers", []) if details else [],
        },
    )
    return Redirect(path=f"/game?room={campaign_id}&system_message_key=inside.rulesets.assigned")
