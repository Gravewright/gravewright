from __future__ import annotations

from typing import Any

from litestar import Request, post
from litestar.response import Response

from app.engine.modules.module_settings_service import ModuleSettingsService
from app.persistence.rows import Row


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


@post("/modules/settings")
async def update_module_setting(
    request: Request,
    current_user: Row,
    module_settings_service: ModuleSettingsService,
) -> Response[dict[str, Any]]:
    body = await _json_body(request)
    result = module_settings_service.set_value(
        module_id=str(body.get("module_id") or "").strip(),
        setting_key_value=str(body.get("key") or "").strip(),
        raw_value=body.get("value"),
        user_id=current_user["id"],
        user_system_role=current_user["system_role"],
        campaign_id=str(body.get("campaign_id") or "").strip() or None,
    )
    if not result.success:
        return Response({"success": False, "error_key": result.error_key}, status_code=400)
    return Response(
        {
            "success": True,
            "module_id": result.module_id,
            "key": result.setting_key,
            "value": result.value,
        }
    )
