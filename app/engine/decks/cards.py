from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
import random
from typing import Any


class DeckScope(StrEnum):
    CAMPAIGN = "campaign"
    ROOM = "room"
    PLAYER = "player"
    PACKAGE = "package"


class PileKind(StrEnum):
    DRAW = "draw"
    DISCARD = "discard"
    HAND = "hand"
    TABLE = "table"
    REVEALED = "revealed"
    REMOVED = "removed"
    ARCHIVE = "archive"
    CUSTOM = "custom"


class CardVisibility(StrEnum):
    GM_ONLY = "gm_only"
    OWNER_ONLY = "owner_only"
    PLAYERS = "players"
    ROOM = "room"
    PUBLIC = "public"
    HIDDEN_UNTIL_REVEALED = "hidden_until_revealed"
    SECRET = "secret"


class CardFaceState(StrEnum):
    FACE_DOWN = "face_down"
    FACE_UP = "face_up"


class DrawMode(StrEnum):
    TOP = "top"
    BOTTOM = "bottom"
    RANDOM = "random"
    CHOOSE = "choose"


class DrawDestination(StrEnum):
    HAND = "hand"
    PILE = "pile"
    CHAT = "chat"
    SCENE = "scene"
    DISCARD = "discard"
    REMOVED = "removed"


class CardEventType(StrEnum):
    DECK_CREATED = "deck.created"
    DECK_UPDATED = "deck.updated"
    DECK_DELETED = "deck.deleted"
    DECK_INSTANTIATED = "deck.instantiated"
    DECK_SHUFFLED = "deck.shuffled"
    DECK_RESET = "deck.reset"
    CARD_DRAWN = "card.drawn"
    CARDS_DEALT = "cards.dealt"
    CARD_MOVED = "card.moved"
    CARD_REVEALED = "card.revealed"
    CARD_HIDDEN = "card.hidden"
    CARD_DISCARDED = "card.discarded"
    CARD_PLAYED_TO_SCENE = "card.played_to_scene"
    CARD_REMOVED_FROM_SCENE = "card.removed_from_scene"
    PILE_CREATED = "pile.created"
    PILE_UPDATED = "pile.updated"


class CardError(Exception):
    pass


class InvalidDrawError(CardError):
    pass


class InvalidCardMoveError(CardError):
    pass


@dataclass(frozen=True)
class CardAssetRef:
    asset_id: str
    thumbnail_asset_id: str | None = None
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None
    sha256: str | None = None


@dataclass(frozen=True)
class CardDefinition:
    id: str
    deck_definition_id: str
    name: str
    front_asset: CardAssetRef | None = None
    back_asset: CardAssetRef | None = None
    subtitle: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    sort_key: str | None = None
    quantity: int = 1


@dataclass(frozen=True)
class CardInstance:
    id: str
    campaign_id: str
    deck_instance_id: str
    card_definition_id: str
    current_pile_id: str | None
    current_scene_id: str | None
    owner_user_id: str | None
    face_state: CardFaceState
    visibility: CardVisibility
    locked: bool
    metadata: dict[str, Any] = field(default_factory=dict)


def validate_draw_count(count: int, *, maximum: int) -> None:
    if count < 1:
        raise InvalidDrawError("draw count must be positive")
    if count > maximum:
        raise InvalidDrawError("not enough cards available")


def compute_shuffled_order(
    card_ids: Sequence[str],
    *,
    rng: random.Random | None = None,
) -> list[str]:
    shuffled = list(card_ids)
    (rng or random.SystemRandom()).shuffle(shuffled)
    return shuffled


def select_cards_for_draw(
    ordered_card_ids: Sequence[str],
    *,
    count: int,
    mode: DrawMode,
    chosen_card_ids: Sequence[str] | None = None,
    rng: random.Random | None = None,
) -> tuple[list[str], list[str]]:
    validate_draw_count(count, maximum=len(ordered_card_ids))
    cards = list(ordered_card_ids)
    if mode == DrawMode.TOP:
        return cards[:count], cards[count:]
    if mode == DrawMode.BOTTOM:
        return cards[-count:], cards[:-count]
    if mode == DrawMode.RANDOM:
        pool = cards[:]
        drawn: list[str] = []
        chooser = rng or random.SystemRandom()
        for _ in range(count):
            index = chooser.randrange(len(pool))
            drawn.append(pool.pop(index))
        return drawn, pool
    if mode == DrawMode.CHOOSE:
        chosen = [str(card_id) for card_id in chosen_card_ids or []]
        if len(chosen) != count or len(set(chosen)) != len(chosen):
            raise InvalidDrawError("chosen cards do not match draw count")
        available = set(cards)
        if any(card_id not in available for card_id in chosen):
            raise InvalidDrawError("chosen card is not available")
        remaining = [card_id for card_id in cards if card_id not in set(chosen)]
        return chosen, remaining
    raise InvalidDrawError("unsupported draw mode")


def apply_move_between_piles(
    source_order: Sequence[str],
    target_order: Sequence[str],
    card_ids: Sequence[str],
    *,
    target_position: int | None = None,
) -> tuple[list[str], list[str]]:
    moving = [str(card_id) for card_id in card_ids]
    if not moving:
        return list(source_order), list(target_order)
    source_set = set(source_order)
    if any(card_id not in source_set for card_id in moving):
        raise InvalidCardMoveError("card is not in source pile")
    moving_set = set(moving)
    new_source = [card_id for card_id in source_order if card_id not in moving_set]
    new_target = [card_id for card_id in target_order if card_id not in moving_set]
    insert_at = len(new_target) if target_position is None else max(0, min(target_position, len(new_target)))
    new_target[insert_at:insert_at] = moving
    return new_source, new_target


def normalize_pile_positions(card_ids: Sequence[str]) -> list[tuple[str, int]]:
    return [(str(card_id), index) for index, card_id in enumerate(card_ids)]


def compute_visibility_for_destination(
    destination: DrawDestination,
    *,
    owner_user_id: str | None,
    requested_visibility: CardVisibility | None,
) -> CardVisibility:
    if requested_visibility is not None:
        return requested_visibility
    if destination == DrawDestination.HAND:
        return CardVisibility.OWNER_ONLY if owner_user_id else CardVisibility.GM_ONLY
    if destination == DrawDestination.CHAT:
        return CardVisibility.ROOM
    if destination == DrawDestination.SCENE:
        return CardVisibility.ROOM
    if destination == DrawDestination.DISCARD:
        return CardVisibility.ROOM
    return CardVisibility.GM_ONLY


def should_card_front_be_visible(
    card: CardInstance,
    *,
    viewer_user_id: str,
    viewer_role: str,
    owner_can_view: bool = True,
    gm_can_peek: bool = True,
) -> bool:
    if viewer_role in {"gm", "assistant_gm"} and gm_can_peek:
        return card.visibility != CardVisibility.SECRET
    if (
        card.visibility == CardVisibility.OWNER_ONLY
        and owner_can_view
        and card.owner_user_id == viewer_user_id
    ):
        return True
    if card.face_state != CardFaceState.FACE_UP:
        return False
    if card.visibility in {CardVisibility.ROOM, CardVisibility.PLAYERS, CardVisibility.PUBLIC}:
        return True
    return False


def redact_card_for_viewer(
    card: CardInstance,
    definition: CardDefinition | None,
    *,
    viewer_user_id: str,
    viewer_role: str,
    gm_can_peek: bool,
) -> dict:
    visible = should_card_front_be_visible(
        card,
        viewer_user_id=viewer_user_id,
        viewer_role=viewer_role,
        gm_can_peek=gm_can_peek,
    )
    base = {
        "id": card.id,
        "deck_instance_id": card.deck_instance_id,
        "current_pile_id": card.current_pile_id,
        "current_scene_id": card.current_scene_id,
        "owner_user_id": card.owner_user_id if card.owner_user_id == viewer_user_id or viewer_role in {"gm", "assistant_gm"} else None,
        "face_state": card.face_state.value,
        "visibility": card.visibility.value,
        "locked": card.locked,
    }
    if visible and definition is not None:
        return base | {
            "definition_id": definition.id,
            "name": definition.name,
            "subtitle": definition.subtitle,
            "description": definition.description,
            "front_asset_id": definition.front_asset.asset_id if definition.front_asset else None,
            "back_asset_id": (
                definition.back_asset.asset_id
                if definition.back_asset is not None
                else None
            ),
            "tags": list(definition.tags),
            "metadata": dict(definition.metadata),
        }
    return base | {
        "definition_id": None,
        "name": "Hidden card",
        "subtitle": None,
        "description": None,
        "front_asset_id": None,
        "back_asset_id": definition.back_asset.asset_id if definition and definition.back_asset else None,
        "tags": [],
        "metadata": {},
    }
