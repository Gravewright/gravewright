from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from litestar import Request, get, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect, Response

from app.domain.roles import SystemRole
from app.engine.sdk.marketplace_installer import MarketplaceInstaller
from app.engine.sdk.marketplace_service import MarketplaceService
from app.helpers.auth import require_user
from app.persistence.rows import Row


@dataclass
class MarketplaceInstallForm:
    package_id: str = ""


def _owner(user: Row) -> bool:
    return str(user["system_role"]) == SystemRole.OWNER.value


@get("/sdk/marketplace", guards=[require_user], sync_to_thread=True)
def marketplace_catalog(current_user: Row) -> Response[dict[str, Any]]:
    return Response(MarketplaceService().catalog())


@post("/sdk/marketplace/refresh", guards=[require_user], sync_to_thread=True)
def marketplace_refresh(request: Request, current_user: Row) -> Response[dict[str, Any]] | Redirect:
    wants_json = "application/json" in (request.headers.get("accept") or "")
    if not _owner(current_user):
        return Response({"ok": False, "error_key": "sdk.errors.owner_required"}, status_code=403) if wants_json else Redirect("/inside?packages_error_key=sdk.errors.owner_required#marketplace")
    catalog = MarketplaceService().refresh()
    ok = catalog.get("refreshStatus") == "ok"
    if wants_json:
        return Response({"ok": ok, "catalog": MarketplaceService().catalog(), "error_key": catalog.get("refreshError")})
    return Redirect("/inside#marketplace")


@post("/sdk/marketplace/install", guards=[require_user], sync_to_thread=True)
def marketplace_install(
    request: Request,
    current_user: Row,
    data: Annotated[MarketplaceInstallForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Response[dict[str, Any]] | Redirect:
    wants_json = "application/json" in (request.headers.get("accept") or "")
    if not _owner(current_user):
        return Response({"ok": False, "error_key": "sdk.errors.owner_required"}, status_code=403) if wants_json else Redirect("/inside?packages_error_key=sdk.errors.owner_required#marketplace")
    result = MarketplaceInstaller().install(package_id=data.package_id.strip(), user_id=str(current_user["id"]))
    if wants_json:
        return Response({"ok": result.success, "package_id": result.package_id, "error_key": result.error_key}, status_code=200 if result.success else 422)
    key = "sdk.messages.installed" if result.success else result.error_key
    field = "packages_message_key" if result.success else "packages_error_key"
    return Redirect(f"/inside?{field}={key}#marketplace")
