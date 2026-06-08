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
class ForgotPasswordForm:
    email: str


@post("/forgot-password")
async def submit_forgot_password(
    request: Request,
    cookies: dict[str, str],
    current_user: Row | None,
    auth_service: AuthService,
    data: Annotated[ForgotPasswordForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect | Template:
    if current_user is not None:
        return Redirect(path="/inside")

    t = view_context(cookies)["t"]
    base_url = config.public_base_url or str(request.base_url).rstrip("/")

    await auth_service.forgot_password(
        email=data.email,
        client_ip=get_client_ip(request),
        reset_base_url=base_url,
    )

    return Template(
        template_name="pages/auth/forgot_password.html",
        context=view_context(
            cookies,
            app_name=config.app_name,
            error=None,
            message=t("auth.forgot.sent"),
        ),
    )
