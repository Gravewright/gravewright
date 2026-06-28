from __future__ import annotations

from app.security.card_permissions import can_create_deck
from app.security.card_permissions import can_discard_card
from app.security.card_permissions import can_draw_from_pile
from app.security.card_permissions import can_reveal_card
from app.security.card_permissions import can_view_card_front
from app.security.card_permissions import can_view_pile


def test_gm_can_create_deck():
    assert can_create_deck(actor_role="gm")


def test_player_cannot_create_room_deck_by_default():
    assert not can_create_deck(actor_role="player")


def test_player_can_view_own_hand():
    pile = {"kind": "hand", "visibility": "owner_only", "owner_user_id": "user-a"}

    assert can_view_pile(viewer_user_id="user-a", viewer_role="player", pile=pile)


def test_player_cannot_view_other_player_hand():
    pile = {"kind": "hand", "visibility": "owner_only", "owner_user_id": "user-a"}

    assert not can_view_pile(viewer_user_id="user-b", viewer_role="player", pile=pile)


def test_gm_can_view_hidden_card_when_gm_peek_enabled():
    card = {"face_state": "face_up", "visibility": "owner_only", "owner_user_id": "user-a"}

    assert can_view_card_front(
        viewer_user_id="gm",
        viewer_role="gm",
        card_instance=card,
        gm_can_peek=True,
    )


def test_gm_cannot_view_hidden_card_when_gm_peek_disabled():
    card = {"face_state": "face_up", "visibility": "owner_only", "owner_user_id": "user-a"}

    assert not can_view_card_front(
        viewer_user_id="gm",
        viewer_role="gm",
        card_instance=card,
        gm_can_peek=False,
    )


def test_owner_can_view_face_down_card_in_private_hand():
    card = {"face_state": "face_down", "visibility": "owner_only", "owner_user_id": "user-a"}

    assert can_view_card_front(
        viewer_user_id="user-a",
        viewer_role="player",
        card_instance=card,
    )
    assert not can_view_card_front(
        viewer_user_id="user-b",
        viewer_role="player",
        card_instance=card,
    )


def test_spectator_cannot_mutate_card_state():
    card = {"owner_user_id": "user-a", "locked": False}

    assert not can_reveal_card(actor_user_id="user-a", actor_role="streamer", card_instance=card)
    assert not can_discard_card(actor_user_id="user-a", actor_role="streamer", card_instance=card)


def test_player_can_discard_owned_card():
    card = {"owner_user_id": "user-a", "locked": False}

    assert can_discard_card(actor_user_id="user-a", actor_role="player", card_instance=card)


def test_player_cannot_discard_unowned_private_card():
    card = {"owner_user_id": "user-a", "locked": False}

    assert not can_discard_card(actor_user_id="user-b", actor_role="player", card_instance=card)


def test_player_can_draw_from_unowned_room_draw_pile():
    pile = {"kind": "draw"}

    assert can_draw_from_pile(
        actor_user_id="user-a",
        actor_role="player",
        pile=pile,
        deck_owner_user_id=None,
    )
