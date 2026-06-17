from __future__ import annotations

from app.persistence.rows import Row

from litestar import get
from litestar.response import Redirect, Template

from app.business.inside_settings_service import InsideSettingsService
from app.config import config
from app.helpers.view import view_context


@get(["/", "/login"])
async def show_login(cookies: dict[str, str], current_user: Row | None) -> Redirect | Template:
    if current_user is not None:
        return Redirect(path="/inside")

    inside_settings = InsideSettingsService()
    privacy = inside_settings.privacy_for_login()

    return Template(
        template_name="pages/auth/login.html",
        context=view_context(
            cookies,
            app_name=inside_settings.app_name() or config.app_name,
            privacy=privacy,
            error=None,
        ),
    )
