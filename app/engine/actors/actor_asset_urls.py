"""Pure URL helpers for actor portrait/token images.

Kept dependency-free (no image/storage stack) so the token projector and the
sheet bundle can build image URLs cheaply. The actor row stores the relative
storage path in ``portrait_asset_id`` / ``token_asset_id`` (or NULL when unset);
``updated_at`` is used as a cache-busting version.
"""

from __future__ import annotations

from typing import Any

_KINDS = ("portrait", "token")


def _field(actor: Any, name: str) -> Any:
    """Read a column from a row mapping or a dict (Row has no ``.get``)."""
    try:
        return actor[name]
    except (KeyError, IndexError, TypeError):
        return None


def actor_image_url(actor: Any, kind: str) -> str | None:
    if kind not in _KINDS or actor is None:
        return None
    if not _field(actor, f"{kind}_asset_id"):
        return None
    version = _field(actor, "updated_at") or _field(actor, "version") or 0
    return f"/game/actor/{_field(actor, 'id')}/image/{kind}?v={version}"


def actor_token_image_url(actor: Any) -> str | None:
    """Token image, falling back to the portrait when no token image is set."""
    return actor_image_url(actor, "token") or actor_image_url(actor, "portrait")
