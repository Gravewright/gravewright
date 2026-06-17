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
class RegisterForm:
    name: str
    email: str
    password: str


@post("/register")
async def submit_register(
    request: Request,
    cookies: dict[str, str],
    current_user: Row | None,
    auth_service: AuthService,
    data: Annotated[RegisterForm, Body(media_type=RequestEncodingType.URL_ENCODED)],
) -> Redirect | Template:
    if current_user is not None:
        return Redirect(path="/inside")

    result = auth_service.register(
        name=data.name,
        email=data.email,
        password=data.password,
        client_ip=get_client_ip(request),
    )

    if not result.success or result.user is None:
        t = view_context(cookies)["t"]

        return Template(
            template_name="pages/auth/register.html",
            context=view_context(
                cookies,
                app_name=config.app_name,
                error=t(result.error_key or "auth.errors.register_failed"),
                is_first_user=auth_service.is_first_user(),
            ),
        )

    request.set_session({"user_id": result.user["id"]})
    return Redirect(path="/inside")
