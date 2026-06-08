from __future__ import annotations

from dataclasses import dataclass
import inspect
from typing import Annotated

from litestar import Request, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect

from app.domain.roles import SystemRole
from app.engine.modules.module_install_service import ModuleInstallService
from app.observability.diagnostics import emit_diagnostic
from app.realtime.metrics import realtime_metrics
from app.helpers.auth import require_user
from app.persistence.rows import Row


@dataclass
class ModuleActionForm:
    module_id: str = ""


@dataclass
class CampaignModuleActionForm:
    campaign_id: str = ""
    module_id: str = ""



async def _read_upload_file(upload: object) -> bytes:
    read = getattr(upload, "read", None)
    if read is None:
        return b""
    data = read()
    if inspect.isawaitable(data):
        data = await data
    return data


def _upload_filename(upload: object) -> str:
    return str(getattr(upload, "filename", "") or "")


def _record_module_action(
    *,
    action: str,
    user_id: str | None,
    module_id: str | None,
    campaign_id: str | None = None,
    success: bool,
    error_key: str | None = None,
) -> None:
    realtime_metrics.increment(f"modules.{action}.count")
    if success:
        realtime_metrics.increment(f"modules.{action}.success")
    else:
        realtime_metrics.increment(f"modules.{action}.failure")
    emit_diagnostic(
        f"modules.{action}",
        user_id=user_id,
        module_id=module_id,
        campaign_id=campaign_id,
        success=success,
        error_key=error_key,
    )


def _redirect_error(error_key: str) -> Redirect:
    return Redirect(path=f"/inside?modules_error_key={error_key}")


def _redirect_ok(message_key: str) -> Redirect:
    return Redirect(path=f"/inside?modules_message_key={message_key}")


def _guard(current_user: Row):
    if str(current_user["system_role"]) != SystemRole.OWNER.value:
        return None, _redirect_error("inside.modules.errors.owner_required")
    return current_user, None



@post("/modules/upload", guards=[require_user])
async def upload_module_package(
    request: Request,
    current_user: Row,
    module_install_service: ModuleInstallService,
) -> Redirect:
    user, early = _guard(current_user)
    if early is not None:
        return early
    form = await request.form()
    upload = form.get("module_file")
    result = module_install_service.install_uploaded_package(
        filename=_upload_filename(upload),
        data=await _read_upload_file(upload),
        user_id=user["id"],
    )
    _record_module_action(action="upload", user_id=user["id"], module_id=result.module_id, success=result.success, error_key=result.error_key)
    if not result.success:
        return _redirect_error(result.error_key or "inside.modules.errors.package_invalid")
    return _redirect_ok("inside.modules.messages.uploaded")


@post("/modules/install", guards=[require_user])
async def install_module(
    current_user: Row,
    module_install_service: ModuleInstallService,
    data: Annotated[ModuleActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    user, early = _guard(current_user)
    if early is not None:
        return early
    result = module_install_service.install(package_id=data.module_id.strip(), user_id=user["id"])
    _record_module_action(action="install", user_id=user["id"], module_id=result.module_id or data.module_id.strip(), success=result.success, error_key=result.error_key)
    if not result.success:
        return _redirect_error(result.error_key or "inside.modules.errors.not_found")
    return _redirect_ok("inside.modules.messages.installed")


@post("/modules/enable", guards=[require_user])
async def enable_module(
    current_user: Row,
    module_install_service: ModuleInstallService,
    data: Annotated[ModuleActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    _, early = _guard(current_user)
    if early is not None:
        return early
    result = module_install_service.enable(package_id=data.module_id.strip())
    _record_module_action(action="enable", user_id=current_user["id"], module_id=result.module_id or data.module_id.strip(), success=result.success, error_key=result.error_key)
    if not result.success:
        return _redirect_error(result.error_key or "inside.modules.errors.not_installed")
    return _redirect_ok("inside.modules.messages.enabled")


@post("/modules/disable", guards=[require_user])
async def disable_module(
    current_user: Row,
    module_install_service: ModuleInstallService,
    data: Annotated[ModuleActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    _, early = _guard(current_user)
    if early is not None:
        return early
    result = module_install_service.disable(package_id=data.module_id.strip())
    _record_module_action(action="disable", user_id=current_user["id"], module_id=result.module_id or data.module_id.strip(), success=result.success, error_key=result.error_key)
    if not result.success:
        return _redirect_error(result.error_key or "inside.modules.errors.not_installed")
    return _redirect_ok("inside.modules.messages.disabled")


@post("/modules/remove", guards=[require_user])
async def remove_module(
    current_user: Row,
    module_install_service: ModuleInstallService,
    data: Annotated[ModuleActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    _, early = _guard(current_user)
    if early is not None:
        return early
    result = module_install_service.remove(package_id=data.module_id.strip())
    _record_module_action(action="remove", user_id=current_user["id"], module_id=result.module_id or data.module_id.strip(), success=result.success, error_key=result.error_key)
    if not result.success:
        return _redirect_error(result.error_key or "inside.modules.errors.not_installed")
    return _redirect_ok("inside.modules.messages.removed")


@post("/campaigns/modules/enable", guards=[require_user])
async def enable_campaign_module(
    current_user: Row,
    module_install_service: ModuleInstallService,
    data: Annotated[CampaignModuleActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    result = module_install_service.enable_for_campaign(
        campaign_id=data.campaign_id.strip(),
        user_id=current_user["id"],
        module_id=data.module_id.strip(),
    )
    _record_module_action(action="campaign_enable", user_id=current_user["id"], module_id=result.module_id or data.module_id.strip(), campaign_id=data.campaign_id.strip(), success=result.success, error_key=result.error_key)
    if not result.success:
        return _redirect_error(result.error_key or "inside.modules.errors.not_installed")
    return _redirect_ok("inside.modules.messages.campaign_enabled")


@post("/campaigns/modules/disable", guards=[require_user])
async def disable_campaign_module(
    current_user: Row,
    module_install_service: ModuleInstallService,
    data: Annotated[CampaignModuleActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    result = module_install_service.disable_for_campaign(
        campaign_id=data.campaign_id.strip(),
        user_id=current_user["id"],
        module_id=data.module_id.strip(),
    )
    _record_module_action(action="campaign_disable", user_id=current_user["id"], module_id=result.module_id or data.module_id.strip(), campaign_id=data.campaign_id.strip(), success=result.success, error_key=result.error_key)
    if not result.success:
        return _redirect_error(result.error_key or "inside.modules.errors.not_installed")
    return _redirect_ok("inside.modules.messages.campaign_disabled")
