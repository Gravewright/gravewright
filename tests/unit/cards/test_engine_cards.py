from __future__ import annotations

import random

import pytest

from app.engine.decks.cards import CardAssetRef
from app.engine.decks.cards import CardDefinition
from app.engine.decks.cards import CardFaceState
from app.engine.decks.cards import CardInstance
from app.engine.decks.cards import CardVisibility
from app.engine.decks.cards import DrawDestination
from app.engine.decks.cards import DrawMode
from app.engine.decks.cards import InvalidCardMoveError
from app.engine.decks.cards import InvalidDrawError
from app.engine.decks.cards import apply_move_between_piles
from app.engine.decks.cards import compute_shuffled_order
from app.engine.decks.cards import compute_visibility_for_destination
from app.engine.decks.cards import redact_card_for_viewer
from app.engine.decks.cards import select_cards_for_draw
from app.engine.decks.cards import should_card_front_be_visible


def test_select_cards_for_top_draw_removes_from_front():
    drawn, remaining = select_cards_for_draw(["a", "b", "c"], count=2, mode=DrawMode.TOP)

    assert drawn == ["a", "b"]
    assert remaining == ["c"]


def test_select_cards_for_bottom_draw_removes_from_end():
    drawn, remaining = select_cards_for_draw(["a", "b", "c"], count=2, mode=DrawMode.BOTTOM)

    assert drawn == ["b", "c"]
    assert remaining == ["a"]


def test_select_cards_for_random_draw_uses_injected_rng():
    drawn, remaining = select_cards_for_draw(
        ["a", "b", "c", "d"],
        count=2,
        mode=DrawMode.RANDOM,
        rng=random.Random(7),
    )

    assert drawn == ["c", "a"]
    assert remaining == ["b", "d"]


def test_draw_count_cannot_be_negative():
    with pytest.raises(InvalidDrawError):
        select_cards_for_draw(["a"], count=0, mode=DrawMode.TOP)


def test_draw_count_cannot_exceed_available_cards():
    with pytest.raises(InvalidDrawError):
        select_cards_for_draw(["a"], count=2, mode=DrawMode.TOP)


def test_move_between_piles_preserves_relative_order():
    source, target = apply_move_between_piles(
        ["a", "b", "c", "d"],
        ["x"],
        ["b", "d"],
        target_position=1,
    )

    assert source == ["a", "c"]
    assert target == ["x", "b", "d"]


def test_move_between_piles_rejects_missing_source_card():
    with pytest.raises(InvalidCardMoveError):
        apply_move_between_piles(["a"], [], ["b"])


def test_shuffle_preserves_all_card_ids():
    original = ["a", "b", "c", "d"]

    shuffled = compute_shuffled_order(original, rng=random.Random(1))

    assert set(shuffled) == set(original)
    assert original == ["a", "b", "c", "d"]


def test_hand_destination_defaults_owner_only():
    visibility = compute_visibility_for_destination(
        DrawDestination.HAND,
        owner_user_id="user-a",
        requested_visibility=None,
    )

    assert visibility == CardVisibility.OWNER_ONLY


def test_redact_hidden_card_removes_front_asset_and_metadata():
    card = CardInstance(
        id="card-1",
        campaign_id="campaign",
        deck_instance_id="deck",
        card_definition_id="definition",
        current_pile_id="pile",
        current_scene_id=None,
        owner_user_id="owner",
        face_state=CardFaceState.FACE_DOWN,
        visibility=CardVisibility.OWNER_ONLY,
        locked=False,
    )
    definition = CardDefinition(
        id="definition",
        deck_definition_id="deck-definition",
        name="Ace",
        front_asset=CardAssetRef("front"),
        back_asset=CardAssetRef("back"),
        metadata={"rank": "A"},
    )

    redacted = redact_card_for_viewer(
        card,
        definition,
        viewer_user_id="other",
        viewer_role="player",
        gm_can_peek=True,
    )

    assert redacted["name"] == "Hidden card"
    assert redacted["definition_id"] is None
    assert redacted["front_asset_id"] is None
    assert redacted["metadata"] == {}


def test_visible_card_includes_front_asset_and_metadata():
    card = CardInstance(
        id="card-1",
        campaign_id="campaign",
        deck_instance_id="deck",
        card_definition_id="definition",
        current_pile_id="pile",
        current_scene_id=None,
        owner_user_id=None,
        face_state=CardFaceState.FACE_UP,
        visibility=CardVisibility.ROOM,
        locked=False,
    )
    definition = CardDefinition(
        id="definition",
        deck_definition_id="deck-definition",
        name="Ace",
        front_asset=CardAssetRef("front"),
        metadata={"rank": "A"},
    )

    visible = redact_card_for_viewer(
        card,
        definition,
        viewer_user_id="other",
        viewer_role="player",
        gm_can_peek=True,
    )

    assert visible["name"] == "Ace"
    assert visible["definition_id"] == "definition"
    assert visible["front_asset_id"] == "front"
    assert visible["metadata"] == {"rank": "A"}


def test_owner_can_see_front_of_face_down_private_hand_card():
    card = CardInstance(
        id="card-1",
        campaign_id="campaign",
        deck_instance_id="deck",
        card_definition_id="definition",
        current_pile_id="hand",
        current_scene_id=None,
        owner_user_id="owner",
        face_state=CardFaceState.FACE_DOWN,
        visibility=CardVisibility.OWNER_ONLY,
        locked=False,
    )

    assert should_card_front_be_visible(
        card,
        viewer_user_id="owner",
        viewer_role="player",
        gm_can_peek=True,
    )
    assert not should_card_front_be_visible(
        card,
        viewer_user_id="other",
        viewer_role="player",
        gm_can_peek=True,
    )
