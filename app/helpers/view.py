from __future__ import annotations

import time
from typing import Any

from app.helpers.i18n import get_locale_from_cookies, translator_for_locale

# A per-process cache-busting token for core static assets. It changes on every
# server start, so a restart always forces browsers to refetch versioned core
# JS/CSS (e.g. ``gravewright-sdk.js?v={{ asset_version }}``) instead of serving a
# stale cached copy. Templates that hardcode a dated ``?v=`` keep doing so.
ASSET_VERSION = str(int(time.time()))


def view_context(
    cookies: dict[str, str],
    **context: Any,
) -> dict[str, Any]:
    locale = get_locale_from_cookies(cookies)

    return {
        **context,
        "locale": locale,
        "t": translator_for_locale(locale),
        "asset_version": ASSET_VERSION,
    }