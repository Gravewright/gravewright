"""Instance-owner admin endpoints (inside): delete any campaign, manage users.

Owner-gated server-side (UI gating alone is not enough). Form-encoded + redirect,
mirroring :mod:`manage_systems`.
"""

from __future__ import annotations

from dataclasses import dataclass
from app.persistence.rows import Row
from typing import Annotated

from litestar import post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect

from app.business.admin.admin_service import AdminService
from app.domain.roles import SystemRole
from app.helpers.auth import require_user


@dataclass
class UserDeleteForm:
    user_id: str = ""


@dataclass
class UserResetPasswordForm:
    user_id: str = ""
    new_password: str = ""


def _redirect_error(error_key: str) -> Redirect:
    return Redirect(path=f"/inside?admin_error_key={error_key}")


def _redirect_ok(message_key: str) -> Redirect:
    return Redirect(path=f"/inside?admin_message_key={message_key}")


def _is_owner(current_user: Row) -> bool:
    return str(current_user["system_role"]) == SystemRole.OWNER.value


@post("/inside/admin/users/delete", guards=[require_user])
async def admin_delete_user(
    current_user: Row,
    data: Annotated[UserDeleteForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    if not _is_owner(current_user):
        return _redirect_error("inside.admin.errors.not_owner")
    result = AdminService().delete_user(
        requester_user_id=current_user["id"], target_user_id=data.user_id
    )
    if not result.success:
        return _redirect_error(result.error_key or "inside.admin.errors.failed")
    return _redirect_ok("inside.admin.messages.user_deleted")


@post("/inside/admin/users/reset-password", guards=[require_user])
async def admin_reset_user_password(
    current_user: Row,
    data: Annotated[UserResetPasswordForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect:
    if not _is_owner(current_user):
        return _redirect_error("inside.admin.errors.not_owner")
    result = AdminService().reset_password(
        requester_user_id=current_user["id"],
        target_user_id=data.user_id,
        new_password=data.new_password,
    )
    if not result.success:
        return _redirect_error(result.error_key or "inside.admin.errors.failed")
    return _redirect_ok("inside.admin.messages.password_reset")
