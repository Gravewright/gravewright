from __future__ import annotations

from app.domain.roles import PlayerRole

GM_ROLES = {PlayerRole.GM.value, PlayerRole.ASSISTANT_GM.value}
MANAGE_ROLES = {PlayerRole.GM.value, PlayerRole.ASSISTANT_GM.value, PlayerRole.PLAYER.value}


def can_view_assets(*, actor_role: str | None) -> bool:
    return actor_role is not None


def can_manage_assets(*, actor_role: str | None) -> bool:
    """Upload images, create folders and move assets between folders."""
    return actor_role in MANAGE_ROLES
