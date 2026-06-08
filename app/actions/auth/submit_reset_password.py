from __future__ import annotations

from dataclasses import dataclass
from app.persistence.rows import Row
from typing import Annotated

from litestar import Request, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect, Template

from app.business.auth.auth_service import AuthService
from app.config import config
from app.helpers.request import get_client_ip
from app.helpers.view import view_context


@dataclass
class ResetPasswordForm:
    token: str
    password: str


@post("/reset-password")
async def submit_reset_password(
    request: Request,
    cookies: dict[str, str],
    current_user: Row | None,
    auth_service: AuthService,
    data: Annotated[ResetPasswordForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect | Template:
    if current_user is not None:
        return Redirect(path="/inside")

    t = view_context(cookies)["t"]

    result = auth_service.reset_password(
        token=data.token,
        password=data.password,
        client_ip=get_client_ip(request),
    )

    if not result.success:
        return Template(
            template_name="pages/auth/reset_password.html",
            context=view_context(
                cookies,
                app_name=config.app_name,
                error=t(result.error_key or "auth.errors.invalid_reset_link"),
                message=None,
                token=data.token,
                token_is_valid=True,
            ),
        )

    return Template(
        template_name="pages/auth/reset_password.html",
        context=view_context(
            cookies,
            app_name=config.app_name,
            error=None,
            message=t("auth.reset.success"),
            token="",
            token_is_valid=False,
        ),
    )
