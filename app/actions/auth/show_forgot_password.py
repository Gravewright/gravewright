from __future__ import annotations

from app.persistence.rows import Row

from litestar import get
from litestar.response import Redirect, Template

from app.config import config
from app.helpers.view import view_context


@get("/forgot-password")
async def show_forgot_password(
    cookies: dict[str, str], current_user: Row | None
) -> Redirect | Template:
    if current_user is not None:
        return Redirect(path="/inside")

    return Template(
        template_name="pages/auth/forgot_password.html",
        context=view_context(
            cookies,
            app_name=config.app_name,
            error=None,
            message=None,
        ),
    )
