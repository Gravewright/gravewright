from __future__ import annotations

from app.domain.roles import PlayerRole
from app.engine.decks.cards import CardVisibility


GM_ROLES = {PlayerRole.GM.value, PlayerRole.ASSISTANT_GM.value}


def _is_gm(role: str | None) -> bool:
    return role in GM_ROLES


def can_create_deck(*, actor_role: str) -> bool:
    return _is_gm(actor_role)


def can_create_deck_instance(*, actor_role: str) -> bool:
    return _is_gm(actor_role)


def can_shuffle_deck_instance(*, actor_role: str, owner_user_id: str | None, actor_user_id: str) -> bool:
    return _is_gm(actor_role) or owner_user_id == actor_user_id


def can_draw_from_pile(
    *,
    actor_user_id: str,
    actor_role: str,
    pile: dict,
    deck_owner_user_id: str | None,
) -> bool:
    if _is_gm(actor_role):
        return True
    if actor_role == PlayerRole.STREAMER.value:
        return False
    if pile.get("kind") != "draw":
        return False
    return deck_owner_user_id in {None, actor_user_id}


def can_view_pile(
    *,
    viewer_user_id: str,
    viewer_role: str,
    pile: dict,
    gm_can_peek: bool = True,
) -> bool:
    if _is_gm(viewer_role) and gm_can_peek:
        return True
    visibility = pile.get("visibility")
    if visibility in {CardVisibility.ROOM.value, CardVisibility.PLAYERS.value, CardVisibility.PUBLIC.value}:
        return True
    if visibility == CardVisibility.OWNER_ONLY.value:
        return pile.get("owner_user_id") == viewer_user_id
    return False


def can_view_card_front(
    *,
    viewer_user_id: str,
    viewer_role: str,
    card_instance: dict,
    gm_can_peek: bool = True,
) -> bool:
    visibility = card_instance.get("visibility")
    if _is_gm(viewer_role) and gm_can_peek and visibility != CardVisibility.SECRET.value:
        return True
    if visibility == CardVisibility.OWNER_ONLY.value:
        return card_instance.get("owner_user_id") == viewer_user_id
    if card_instance.get("face_state") != "face_up":
        return False
    if visibility in {CardVisibility.ROOM.value, CardVisibility.PLAYERS.value, CardVisibility.PUBLIC.value}:
        return True
    return False


def can_move_card(
    *,
    actor_user_id: str,
    actor_role: str,
    card_instance: dict,
) -> bool:
    if _is_gm(actor_role):
        return True
    if actor_role == PlayerRole.STREAMER.value:
        return False
    return card_instance.get("owner_user_id") == actor_user_id and not bool(card_instance.get("locked"))


def can_play_card_to_scene(
    *,
    actor_user_id: str,
    actor_role: str,
    card_instance: dict,
) -> bool:
    return can_move_card(actor_user_id=actor_user_id, actor_role=actor_role, card_instance=card_instance)


def can_reveal_card(*, actor_user_id: str, actor_role: str, card_instance: dict) -> bool:
    return can_move_card(actor_user_id=actor_user_id, actor_role=actor_role, card_instance=card_instance)


def can_discard_card(*, actor_user_id: str, actor_role: str, card_instance: dict) -> bool:
    return can_move_card(actor_user_id=actor_user_id, actor_role=actor_role, card_instance=card_instance)
