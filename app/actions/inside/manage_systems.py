from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from litestar import post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from app.persistence.rows import Row

from litestar.response import Redirect

from app.domain.roles import SystemRole
from app.engine.systems.system_install_service import SystemInstallService
from app.helpers.auth import require_user


@dataclass
class SystemActionForm:
    system_id: str = ""


def _redirect_error(error_key: str) -> Redirect:
    return Redirect(path=f"/inside?systems_error_key={error_key}")


def _redirect_ok(message_key: str) -> Redirect:
    return Redirect(path=f"/inside?systems_message_key={message_key}")


def _guard(cookies: dict[str, str], current_user: Row, data: SystemActionForm):
    if str(current_user["system_role"]) != SystemRole.OWNER.value:
        return None, _redirect_error("inside.systems.errors.owner_required")
    return current_user, None


@post("/systems/install", guards=[require_user])
async def install_system(
    cookies: dict[str, str],
    current_user: Row,
    system_install_service: SystemInstallService,
    data: Annotated[SystemActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    user, early = _guard(cookies, current_user, data)
    if early is not None:
        return early
    result = system_install_service.install(package_id=data.system_id.strip(), user_id=user["id"])
    if not result.success:
        return _redirect_error(result.error_key or "inside.systems.errors.not_found")
    return _redirect_ok("inside.systems.messages.installed")


@post("/systems/enable", guards=[require_user])
async def enable_system(
    cookies: dict[str, str],
    current_user: Row,
    system_install_service: SystemInstallService,
    data: Annotated[SystemActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    _, early = _guard(cookies, current_user, data)
    if early is not None:
        return early
    result = system_install_service.enable(package_id=data.system_id.strip())
    if not result.success:
        return _redirect_error(result.error_key or "inside.systems.errors.not_installed")
    return _redirect_ok("inside.systems.messages.enabled")


@post("/systems/disable", guards=[require_user])
async def disable_system(
    cookies: dict[str, str],
    current_user: Row,
    system_install_service: SystemInstallService,
    data: Annotated[SystemActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    _, early = _guard(cookies, current_user, data)
    if early is not None:
        return early
    result = system_install_service.disable(package_id=data.system_id.strip())
    if not result.success:
        return _redirect_error(result.error_key or "inside.systems.errors.not_installed")
    return _redirect_ok("inside.systems.messages.disabled")


@post("/systems/remove", guards=[require_user])
async def remove_system(
    cookies: dict[str, str],
    current_user: Row,
    system_install_service: SystemInstallService,
    data: Annotated[SystemActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    _, early = _guard(cookies, current_user, data)
    if early is not None:
        return early
    result = system_install_service.remove(package_id=data.system_id.strip())
    if not result.success:
        return _redirect_error(result.error_key or "inside.systems.errors.not_installed")
    return _redirect_ok("inside.systems.messages.removed")
