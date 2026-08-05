"""Change a package setting value (scoped global/campaign/user).

Campaign-scoped settings require the caller to be the campaign GM; user-scoped
settings are always allowed for the signed-in user.
"""

from __future__ import annotations

from typing import Any

from litestar import Request, post
from litestar.response import Response

from app.domain.roles import PlayerRole
from app.domain.roles import SystemRole
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_settings_service import PackageSettingsService
from app.helpers.auth import require_user
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.rows import Row


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


@post("/sdk/packages/settings", guards=[require_user])
async def update_package_setting(
    request: Request,
    current_user: Row,
    package_settings_service: PackageSettingsService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    package_id = str(body.get("package_id") or "").strip()
    key = str(body.get("key") or "").strip()
    campaign_id = str(body.get("campaign_id") or "").strip() or None

    package_install_service = PackageInstallService()
    record = package_install_service.get(package_id)
    manifest = package_install_service.get_manifest(package_id)
    if record is None or record["status"] != "enabled" or manifest is None:
        return Response({"success": False, "error_key": "sdk.errors.not_enabled"}, status_code=400)
    if "settings" not in manifest.capabilities:
        return Response(
            {"success": False, "error_key": "sdk.errors.capability_required"},
            status_code=403,
        )

    definitions = {d["key"]: d for d in package_settings_service.definitions(package_id)}
    definition = definitions.get(key)
    if definition is None:
        return Response({"success": False, "error_key": "sdk.errors.setting_unknown"}, status_code=400)

    if definition["scope"] == "global":
        if str(current_user["system_role"]) != SystemRole.OWNER.value:
            return Response({"success": False, "error_key": "sdk.errors.owner_required"}, status_code=403)

    # Campaign-scoped writes are GM-only; user-scoped writes belong to the user.
    if definition["scope"] == "campaign":
        if not campaign_id:
            return Response({"success": False, "error_key": "sdk.errors.campaign_required"}, status_code=400)
        role = CampaignRepository().get_member_role(campaign_id=campaign_id, user_id=current_user["id"])
        if role != PlayerRole.GM.value:
            return Response({"success": False, "error_key": "inside.campaigns.errors.gm_required"}, status_code=403)

    result = package_settings_service.set(
        package_id=package_id,
        key=key,
        value=body.get("value"),
        campaign_id=campaign_id,
        user_id=current_user["id"],
    )
    if not result.success:
        code = result.error.code if result.error else "sdk.errors.setting_invalid"
        return Response(
            {"success": False, "error_key": code, "code": code},
            status_code=400,
        )
    value = package_settings_service.get(package_id, key, campaign_id, current_user["id"])
    return Response({"success": True, "package_id": package_id, "key": key, "value": value})
