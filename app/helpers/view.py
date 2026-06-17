from __future__ import annotations

from typing import Any

from app.helpers.i18n import get_locale_from_cookies, translator_for_locale


def view_context(
    cookies: dict[str, str],
    **context: Any,
) -> dict[str, Any]:
    locale = get_locale_from_cookies(cookies)

    return {
        **context,
        "locale": locale,
        "t": translator_for_locale(locale),
    }