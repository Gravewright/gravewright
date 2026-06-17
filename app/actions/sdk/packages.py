"""Global SDK package management routes (Inside > Packages).

Listing is available to any signed-in user; install / enable / disable / remove
are owner-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from litestar import Request, get, post
from litestar.enums import RequestEncodingType
from litestar.params import Body, FromPath
from litestar.response import Redirect, Response

from app.domain.roles import SystemRole
from app.engine.sdk.package_install_service import PackageInstallService
from app.helpers.auth import require_user
from app.helpers.i18n import get_locale_from_cookies, translator_for_locale
from app.persistence.rows import Row

PACKAGE_EXISTS_KEY = "inside.addons.errors.package_exists"


@dataclass
class PackageActionForm:
    package_id: str = ""


def _is_owner(current_user: Row) -> bool:
    return str(current_user["system_role"]) == SystemRole.OWNER.value


def _redirect_error(error_key: str) -> Redirect:
    return Redirect(path=f"/inside?packages_error_key={error_key}")


def _redirect_ok(message_key: str) -> Redirect:
    return Redirect(path=f"/inside?packages_message_key={message_key}")


@get("/sdk/packages", guards=[require_user], sync_to_thread=False)
def list_packages(
    current_user: Row,
    package_install_service: PackageInstallService,
) -> Response[dict[str, Any]]:
    return Response({"packages": package_install_service.list_for_tab()})


@get("/sdk/packages/{package_id:str}", guards=[require_user], sync_to_thread=False)
def get_package(
    package_id: FromPath[str],
    current_user: Row,
    package_install_service: PackageInstallService,
) -> Response[dict[str, Any]]:
    details = package_install_service.get_details(str(package_id))
    if details is None:
        return Response({"error_key": "sdk.errors.not_found"}, status_code=404)
    return Response(details)


@post("/sdk/packages/install", guards=[require_user])
async def install_package(
    current_user: Row,
    package_install_service: PackageInstallService,
    data: Annotated[PackageActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    if not _is_owner(current_user):
        return _redirect_error("sdk.errors.owner_required")
    result = package_install_service.install(
        package_id=data.package_id.strip(), user_id=current_user["id"]
    )
    if not result.success:
        return _redirect_error(result.error_key or "sdk.errors.not_found")
    return _redirect_ok("sdk.messages.installed")


@post("/sdk/packages/upload", guards=[require_user])
async def upload_package(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    package_install_service: PackageInstallService,
) -> Redirect | Response[dict[str, Any]]:
    """Install a package from an uploaded ZIP.

    The Inside upload modals send ``Accept: application/json`` so they can prompt
    "replace?" on an id conflict while keeping the chosen file in memory; a plain
    form submit (no JS) still gets a redirect.
    """
    wants_json = "application/json" in (request.headers.get("accept") or "")

    def fail(error_key: str, *, conflict: bool = False) -> Redirect | Response[dict[str, Any]]:
        if wants_json:
            t = translator_for_locale(get_locale_from_cookies(cookies))
            return Response(
                {"ok": False, "conflict": conflict, "message": t(error_key)}, status_code=200
            )
        return _redirect_error(error_key)

    if not _is_owner(current_user):
        return fail("sdk.errors.owner_required")

    form = await request.form()
    upload = form.get("package_file")
    filename = str(getattr(upload, "filename", "") or "")
    data = await upload.read() if hasattr(upload, "read") else b""
    replace = str(form.get("replace", "")).strip().lower() in {"true", "on", "1", "yes"}
    expected_group = str(form.get("expected_group", "")).strip() or None

    result = package_install_service.install_uploaded_archive(
        filename=filename,
        data=data,
        user_id=current_user["id"],
        replace=replace,
        expected_group=expected_group,
    )
    if not result.success:
        return fail(
            result.error_key or "inside.addons.errors.package_invalid",
            conflict=result.error_key == PACKAGE_EXISTS_KEY,
        )

    message_key = (
        "inside.rulesets.messages.uploaded"
        if expected_group == "ruleset"
        else "inside.addons.messages.uploaded"
    )
    if wants_json:
        return Response(
            {"ok": True, "redirect": f"/inside?packages_message_key={message_key}"},
            status_code=200,
        )
    return _redirect_ok(message_key)


@post("/sdk/packages/enable", guards=[require_user])
async def enable_package(
    current_user: Row,
    package_install_service: PackageInstallService,
    data: Annotated[PackageActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    if not _is_owner(current_user):
        return _redirect_error("sdk.errors.owner_required")
    result = package_install_service.enable(package_id=data.package_id.strip())
    if not result.success:
        return _redirect_error(result.error_key or "sdk.errors.not_installed")
    return _redirect_ok("sdk.messages.enabled")


@post("/sdk/packages/disable", guards=[require_user])
async def disable_package(
    current_user: Row,
    package_install_service: PackageInstallService,
    data: Annotated[PackageActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    if not _is_owner(current_user):
        return _redirect_error("sdk.errors.owner_required")
    result = package_install_service.disable(package_id=data.package_id.strip())
    if not result.success:
        return _redirect_error(result.error_key or "sdk.errors.not_installed")
    return _redirect_ok("sdk.messages.disabled")


@post("/sdk/packages/remove", guards=[require_user])
async def remove_package(
    current_user: Row,
    package_install_service: PackageInstallService,
    data: Annotated[PackageActionForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    if not _is_owner(current_user):
        return _redirect_error("sdk.errors.owner_required")
    result = package_install_service.remove(package_id=data.package_id.strip(), delete_files=True)
    if not result.success:
        return _redirect_error(result.error_key or "sdk.errors.not_installed")
    return _redirect_ok("sdk.messages.removed")
