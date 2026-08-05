from __future__ import annotations

from app.persistence.rows import Row

from litestar import get
from litestar.response import Redirect, Template

from app.business.auth.auth_service import AuthService
from app.config import config
from app.helpers.view import view_context


@get("/register")
async def show_register(cookies: dict[str, str], current_user: Row | None, auth_service: AuthService) -> Redirect | Template:
    if current_user is not None:
        return Redirect(path="/inside")

    return Template(
        template_name="pages/auth/register.html",
        context=view_context(
            cookies,
            app_name=config.app_name,
            error=None,
            is_first_user=auth_service.is_first_user(),
        ),
    )
