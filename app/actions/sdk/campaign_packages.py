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
from app.business.campaigns.campaign_system_service import resolved_area_marker_presets


@dataclass
class CampaignPackageForm:
    campaign_id: str = ""
    package_id: str = ""


def _wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "application/json" in accept


def _redirect(
    campaign_id: str, *, error_key: str | None = None, message_key: str | None = None
) -> Redirect:
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

async def _emit_cancelled_presentations(campaign_id: str, presentations: tuple[dict, ...]) -> None:
    transport=RealtimeTransport()
    for presentation in presentations:
        recipients=list(dict.fromkeys([*((presentation.get("audience") or {}).get("ids") or []),str(presentation.get("ownerUserId") or "")]))
        await transport.to_players(player_ids=[value for value in recipients if value],event=TransportEvent.UI_PRESENTATION_CHANGED,payload={"room_id":campaign_id,"presentation_id":presentation["id"],"closed":False,"status":"cancelled","completion_reason":"package-unload","presentation":presentation,"schema_version":1})

async def _emit_cancelled_semantics(campaign_id: str, instances: tuple[dict, ...]) -> None:
    transport=RealtimeTransport();events={"workflow":TransportEvent.WORKFLOW_CHANGED,"gameplay-flow":TransportEvent.GAMEPLAY_FLOW_CHANGED,"timeline":TransportEvent.TIMELINE_CHANGED}
    for instance in instances:
        await transport.to_room(room_id=campaign_id,event=events[instance["domain"]],payload={"room_id":campaign_id,"status":"CANCELLED","completion_reason":"package-unload",f"{instance['domain'].replace('-','_')}_id":instance["id"],"schema_version":1})


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
    await _emit_cancelled_presentations(data.campaign_id,result.cancelled_presentations)
    await _emit_cancelled_semantics(data.campaign_id,result.cancelled_semantics)
    await _emit_packages_changed(data.campaign_id, data.package_id.strip(), "deactivate")
    if not json_response:
        return _redirect(data.campaign_id, message_key="sdk.messages.campaign_disabled")
    return Response({"success": True})


@post("/sdk/campaigns/ruleset", guards=[require_user])
async def set_campaign_ruleset(
    request: Request,
    current_user: Row,
    package_activation_service: PackageActivationService,
    data: Annotated[CampaignPackageForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, Any]] | Redirect:
    """Define (ou solta) o ruleset da campanha.

    Responde JSON quando o cliente pede, para o painel nao precisar de um POST
    de formulario que recarrega a pagina inteira. O redirect continua servindo
    quem chega sem JavaScript.
    """
    wants_json = "application/json" in request.headers.get("accept", "")
    campaign_id = data.campaign_id

    def fail(error_key: str, status: int) -> Response[dict[str, Any]] | Redirect:
        if wants_json:
            return Response({"ok": False, "error_key": error_key}, status_code=status)
        return Redirect(path=f"/game?room={campaign_id}&system_error_key={error_key}")

    if not _is_gm(campaign_id, current_user["id"]):
        return fail("inside.campaigns.errors.gm_required", 403)
    package_id = data.package_id.strip() or None
    result = package_activation_service.set_campaign_ruleset(
        campaign_id, package_id, current_user["id"]
    )
    if not result.success:
        return fail(result.error_key or "inside.campaigns.errors.invalid", 400)

    details = package_activation_service.install.get_details(package_id) if package_id else None
    await RealtimeTransport().to_room(
        room_id=campaign_id,
        event=TransportEvent.CAMPAIGN_SYSTEM_CHANGED,
        payload={
            "room_id": campaign_id,
            "system_id": package_id,
            "area_markers": resolved_area_marker_presets(
                details.get("area_markers", []) if details else []
            ),
        },
    )
    if wants_json:
        return Response(
            {"ok": True, "message_key": "inside.rulesets.assigned", "system_id": package_id},
            status_code=200,
        )
    return Redirect(path=f"/game?room={campaign_id}&system_message_key=inside.rulesets.assigned")
