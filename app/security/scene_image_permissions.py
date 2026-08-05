from __future__ import annotations

from app.domain.roles import PlayerRole


GM_ROLES = {PlayerRole.GM.value, PlayerRole.ASSISTANT_GM.value}
UPLOAD_ROLES = {PlayerRole.GM.value, PlayerRole.ASSISTANT_GM.value, PlayerRole.PLAYER.value}
# Streamers are read-only omniscient viewers: they SEE the GM layer but never edit it.
GM_LAYER_VIEW_ROLES = {PlayerRole.GM.value, PlayerRole.ASSISTANT_GM.value, PlayerRole.STREAMER.value}


def _is_gm(role: str | None) -> bool:
    return role in GM_ROLES


def can_upload_scene_image(*, actor_role: str | None) -> bool:
    return actor_role in UPLOAD_ROLES


def can_view_gm_layer(*, actor_role: str | None) -> bool:
    return actor_role in GM_LAYER_VIEW_ROLES


def can_set_gm_layer(*, actor_role: str | None) -> bool:
    return actor_role in GM_ROLES


def can_move_scene_image(*, actor_user_id: str, actor_role: str | None, placement: dict) -> bool:
    if _is_gm(actor_role):
        return True
    if bool(placement.get("locked")):
        return False
    return placement.get("owner_user_id") == actor_user_id


def can_delete_scene_image(*, actor_user_id: str, actor_role: str | None, placement: dict) -> bool:
    return can_move_scene_image(actor_user_id=actor_user_id, actor_role=actor_role, placement=placement)
