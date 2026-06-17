from __future__ import annotations

from app.persistence.rows import Row
from typing import Any
from urllib.parse import quote

from litestar import Request
from litestar import post
from litestar.response import Redirect
from litestar.response import Response

from app.business.permissions import PermissionService
from app.domain.permissions.groups import CONFIGURABLE_ROLES


def _wants_json(request: Request) -> bool:
    return "application/json" in request.headers.get("accept", "")


@post("/campaigns/permissions")
async def update_campaign_permissions(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    permission_service: PermissionService,
) -> Redirect | Response[dict[str, Any]]:
    json_response = _wants_json(request)
    user = current_user

    form = await request.form()

    campaign_id = str(form.get("campaign_id") or "")

    if not campaign_id:
        if json_response:
            return Response(
                content={"ok": False, "error_key": "inside.campaigns.errors.not_found"},
                status_code=400,
            )
        return Redirect(path="/game?permissions_error_key=inside.campaigns.errors.not_found")

    role_permissions: dict[str, list[str]] = {
        role: [str(v) for v in form.getall(f"permissions__{role}", [])]
        for role in CONFIGURABLE_ROLES
    }

    result = permission_service.update_roles_permissions(
        campaign_id=campaign_id,
        user_id=user["id"],
        role_permissions=role_permissions,
    )

    if json_response:
        if result.success:
            return Response(
                content={"ok": True, "message_key": result.message_key or ""},
                status_code=200,
            )
        return Response(
            content={"ok": False, "error_key": result.error_key or ""},
            status_code=400,
        )

    if result.success:
        return Redirect(path=f"/game?permissions_message_key={quote(result.message_key or '')}")

    return Redirect(path=f"/game?permissions_error_key={quote(result.error_key or '')}")
