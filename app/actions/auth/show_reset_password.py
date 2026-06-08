from __future__ import annotations

from app.persistence.rows import Row

from litestar import get
from litestar.params import FromQuery
from litestar.response import Redirect, Template

from app.business.auth.auth_service import AuthService
from app.config import config
from app.helpers.view import view_context


@get("/reset-password")
async def show_reset_password(
    cookies: dict[str, str],
    current_user: Row | None,
    auth_service: AuthService,
    token: FromQuery[str] = "",
) -> Redirect | Template:
    if current_user is not None:
        return Redirect(path="/inside")

    t = view_context(cookies)["t"]
    token_is_valid = auth_service.is_valid_reset_token(token)

    return Template(
        template_name="pages/auth/reset_password.html",
        context=view_context(
            cookies,
            app_name=config.app_name,
            error=None if token_is_valid else t("auth.errors.invalid_reset_link"),
            message=None,
            token=token,
            token_is_valid=token_is_valid,
        ),
    )
