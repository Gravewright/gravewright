from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engine.decks.cards import CardAssetRef
from app.engine.decks.cards import CardDefinition
from app.engine.decks.cards import CardEventType
from app.engine.decks.cards import CardFaceState
from app.engine.decks.cards import InvalidCardMoveError
from app.engine.decks.cards import CardInstance
from app.engine.decks.cards import CardVisibility
from app.engine.decks.cards import DeckScope
from app.engine.decks.cards import DrawDestination
from app.engine.decks.cards import DrawMode
from app.engine.decks.cards import InvalidDrawError
from app.engine.decks.cards import PileKind
from app.engine.decks.cards import compute_shuffled_order
from app.engine.decks.cards import compute_visibility_for_destination
from app.engine.decks.cards import redact_card_for_viewer
from app.engine.decks.cards import should_card_front_be_visible
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.card_repository import CardRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.security.card_permissions import can_create_deck
from app.security.card_permissions import can_create_deck_instance
from app.security.card_permissions import can_discard_card
from app.security.card_permissions import can_draw_from_pile
from app.security.card_permissions import can_play_card_to_scene
from app.security.card_permissions import can_reveal_card
from app.security.card_permissions import can_shuffle_deck_instance
from app.security.card_permissions import can_view_pile


@dataclass(frozen=True)
class CardServiceResult:
    success: bool
    payload: dict[str, Any] = field(default_factory=dict)
    error_key: str | None = None


class CardService:
    def __init__(self) -> None:
        self.campaigns = CampaignRepository()
        self.cards = CardRepository()
        self.scenes = SceneRepository()

    def get_state(self, *, campaign_id: str, user_id: str) -> CardServiceResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        if role is None:
            return CardServiceResult(success=False, error_key="game.cards.errors.not_found")
        deck_instances = self.cards.list_deck_instances(campaign_id=campaign_id)
        all_piles = self.cards.list_piles(campaign_id=campaign_id)
        all_cards = self.cards.list_cards_for_campaign(campaign_id=campaign_id)
        draw_pile_ids = {
            pile["deck_instance_id"]: pile["id"]
            for pile in all_piles
            if pile.get("kind") == PileKind.DRAW.value and pile.get("deck_instance_id")
        }
        draw_counts = {
            deck_id: sum(1 for card in all_cards if card.get("current_pile_id") == pile_id)
            for deck_id, pile_id in draw_pile_ids.items()
        }
        decks = [
            {**deck, "draw_count": draw_counts.get(deck["id"], 0)}
            for deck in deck_instances
        ]
        piles = [
            pile
            for pile in all_piles
            if can_view_pile(viewer_user_id=user_id, viewer_role=role, pile=pile)
        ]
        pile_ids = {pile["id"] for pile in piles}
        raw_cards = [
            card
            for card in all_cards
            if card.get("current_pile_id") in pile_ids or self._card_exists_visible(card=card, user_id=user_id, role=role)
        ]
        definitions = self.cards.definitions_by_id([card["card_definition_id"] for card in raw_cards])
        placements = [
            placement
            for placement in self.cards.list_scene_card_placements(campaign_id=campaign_id)
            if any(card["id"] == placement["card_instance_id"] for card in raw_cards)
        ]
        return CardServiceResult(
            success=True,
            payload={
                "campaign_id": campaign_id,
                "decks": decks,
                "piles": piles,
                "scene_placements": placements,
                "cards": [
                    self._redact(card, definitions.get(card["card_definition_id"]), user_id=user_id, role=role)
                    for card in raw_cards
                ],
            },
        )

    def create_deck_definition(
        self,
        *,
        campaign_id: str,
        user_id: str,
        name: str,
        description: str | None,
        cards: list[dict],
        default_back_asset_id: str | None = None,
        metadata: dict | None = None,
    ) -> CardServiceResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        if role is None or not can_create_deck(actor_role=role):
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        normalized_name = " ".join((name or "").split())
        if len(normalized_name) < 2:
            return CardServiceResult(success=False, error_key="game.cards.errors.invalid_deck_name")
        if not cards:
            return CardServiceResult(success=False, error_key="game.cards.errors.empty_deck")
        normalized_cards = [self._normalize_definition_input(card) for card in cards]
        if any(not str(card.get("front_asset_id") or "").strip() for card in normalized_cards):
            return CardServiceResult(success=False, error_key="game.cards.errors.missing_front_asset")
        deck = self.cards.create_deck_definition(
            campaign_id=campaign_id,
            package_id=None,
            owner_user_id=user_id,
            scope=DeckScope.CAMPAIGN,
            name=normalized_name[:191],
            description=description,
            default_back_asset_id=default_back_asset_id,
            editable=True,
            metadata=metadata or {},
            cards=normalized_cards[:500],
        )
        self.cards.create_event(
            campaign_id=campaign_id,
            room_id=campaign_id,
            actor_user_id=user_id,
            event_type=CardEventType.DECK_CREATED,
            payload={"deck_definition_id": deck["id"], "name": deck["name"]},
            visibility=CardVisibility.ROOM,
        )
        return CardServiceResult(success=True, payload={"deck": deck})

    def instantiate_deck(
        self,
        *,
        campaign_id: str,
        user_id: str,
        deck_definition_id: str,
        name: str | None = None,
    ) -> CardServiceResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        if role is None or not can_create_deck_instance(actor_role=role):
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        deck_definition = self.cards.get_deck_definition(deck_definition_id)
        if deck_definition is None or deck_definition.get("campaign_id") not in {None, campaign_id}:
            return CardServiceResult(success=False, error_key="game.cards.errors.deck_not_found")
        instance = self.cards.create_deck_instance(
            campaign_id=campaign_id,
            room_id=campaign_id,
            deck_definition_id=deck_definition_id,
            owner_user_id=None,
            name=(name or deck_definition["name"])[:191],
            metadata={},
        )
        self.cards.create_event(
            campaign_id=campaign_id,
            room_id=campaign_id,
            actor_user_id=user_id,
            event_type=CardEventType.DECK_INSTANTIATED,
            payload={"deck_instance_id": instance["id"], "deck_definition_id": deck_definition_id},
            visibility=CardVisibility.ROOM,
        )
        return CardServiceResult(success=True, payload={"deck": instance})

    def delete_deck_instance(self, *, campaign_id: str, user_id: str, deck_instance_id: str) -> CardServiceResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        deck = self.cards.get_deck_instance(deck_instance_id)
        if role is None or deck is None or deck.get("campaign_id") != campaign_id:
            return CardServiceResult(success=False, error_key="game.cards.errors.deck_not_found")
        if not can_create_deck_instance(actor_role=role):
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        self.cards.create_event(
            campaign_id=campaign_id,
            room_id=campaign_id,
            actor_user_id=user_id,
            event_type=CardEventType.DECK_DELETED,
            payload={"deck_instance_id": deck_instance_id, "name": deck.get("name")},
            visibility=CardVisibility.ROOM,
        )
        self.cards.delete_deck_instance(deck_instance_id=deck_instance_id)
        return CardServiceResult(success=True, payload={"deck_instance_id": deck_instance_id})

    def shuffle(self, *, campaign_id: str, user_id: str, deck_instance_id: str) -> CardServiceResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        deck = self.cards.get_deck_instance(deck_instance_id)
        if role is None or deck is None or deck.get("campaign_id") != campaign_id:
            return CardServiceResult(success=False, error_key="game.cards.errors.deck_not_found")
        if not can_shuffle_deck_instance(actor_role=role, owner_user_id=deck.get("owner_user_id"), actor_user_id=user_id):
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        draw = self.cards.find_pile(deck_instance_id=deck_instance_id, kind=PileKind.DRAW)
        if draw is None:
            return CardServiceResult(success=False, error_key="game.cards.errors.pile_not_found")
        shuffled = compute_shuffled_order(self.cards.get_pile_order(draw["id"]))
        self.cards.replace_pile_order(pile_id=draw["id"], card_ids=shuffled)
        self.cards.create_event(
            campaign_id=campaign_id,
            room_id=campaign_id,
            actor_user_id=user_id,
            event_type=CardEventType.DECK_SHUFFLED,
            payload={"deck_instance_id": deck_instance_id},
            visibility=CardVisibility.ROOM,
        )
        return CardServiceResult(success=True, payload={"deck_instance_id": deck_instance_id, "draw_count": len(shuffled)})

    def reset(
        self,
        *,
        campaign_id: str,
        user_id: str,
        deck_instance_id: str,
        shuffle: bool = True,
    ) -> CardServiceResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        deck = self.cards.get_deck_instance(deck_instance_id)
        if role is None or deck is None or deck.get("campaign_id") != campaign_id:
            return CardServiceResult(success=False, error_key="game.cards.errors.deck_not_found")
        if not can_shuffle_deck_instance(actor_role=role, owner_user_id=deck.get("owner_user_id"), actor_user_id=user_id):
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        draw = self.cards.find_pile(deck_instance_id=deck_instance_id, kind=PileKind.DRAW)
        if draw is None:
            return CardServiceResult(success=False, error_key="game.cards.errors.pile_not_found")
        card_ids = [card["id"] for card in self.cards.list_cards_for_deck(deck_instance_id=deck_instance_id)]
        if shuffle:
            card_ids = compute_shuffled_order(card_ids)
        self.cards.reset_deck_instance(
            deck_instance_id=deck_instance_id,
            draw_pile_id=draw["id"],
            ordered_card_ids=card_ids,
        )
        self.cards.create_event(
            campaign_id=campaign_id,
            room_id=campaign_id,
            actor_user_id=user_id,
            event_type=CardEventType.DECK_RESET,
            payload={"deck_instance_id": deck_instance_id, "shuffle": shuffle},
            visibility=CardVisibility.ROOM,
        )
        return CardServiceResult(success=True, payload={"deck_instance_id": deck_instance_id, "draw_count": len(card_ids)})

    def draw(
        self,
        *,
        campaign_id: str,
        user_id: str,
        deck_instance_id: str,
        count: int,
        destination: DrawDestination,
        mode: DrawMode = DrawMode.TOP,
        target_pile_id: str | None = None,
        reveal: bool = False,
    ) -> CardServiceResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        deck = self.cards.get_deck_instance(deck_instance_id)
        if role is None or deck is None or deck.get("campaign_id") != campaign_id:
            return CardServiceResult(success=False, error_key="game.cards.errors.deck_not_found")
        draw_pile = self.cards.find_pile(deck_instance_id=deck_instance_id, kind=PileKind.DRAW)
        if draw_pile is None:
            return CardServiceResult(success=False, error_key="game.cards.errors.pile_not_found")
        if not can_draw_from_pile(
            actor_user_id=user_id,
            actor_role=role,
            pile=draw_pile,
            deck_owner_user_id=deck.get("owner_user_id"),
        ):
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        if destination == DrawDestination.HAND:
            target = self.cards.create_hand_pile(campaign_id=campaign_id, owner_user_id=user_id)
            owner_user_id = user_id
        elif target_pile_id:
            target = self.cards.get_pile(target_pile_id)
            owner_user_id = target.get("owner_user_id") if target else None
        else:
            kind = PileKind.REVEALED if destination == DrawDestination.CHAT else PileKind.DISCARD
            target = self.cards.find_pile(deck_instance_id=deck_instance_id, kind=kind)
            owner_user_id = None
        if target is None or target.get("campaign_id") != campaign_id:
            return CardServiceResult(success=False, error_key="game.cards.errors.pile_not_found")
        visibility = compute_visibility_for_destination(
            destination,
            owner_user_id=owner_user_id,
            requested_visibility=CardVisibility.ROOM if reveal or destination == DrawDestination.CHAT else None,
        )
        face_state = CardFaceState.FACE_UP if reveal or destination == DrawDestination.CHAT else CardFaceState.FACE_DOWN
        try:
            drawn = self.cards.draw_cards_between_piles(
                source_pile_id=draw_pile["id"],
                target_pile_id=target["id"],
                count=max(1, min(50, int(count or 1))),
                mode=mode,
                owner_user_id=owner_user_id,
                visibility=visibility,
                face_state=face_state,
            )
        except InvalidDrawError:
            return CardServiceResult(success=False, error_key="game.cards.errors.invalid_draw")
        except InvalidCardMoveError:
            return CardServiceResult(success=False, error_key="game.cards.errors.invalid_draw")
        cards = self.cards.list_cards_for_pile(pile_id=target["id"])
        moved = [card for card in cards if card["id"] in set(drawn)]
        definitions = self.cards.definitions_by_id([card["card_definition_id"] for card in moved])
        event = self.cards.create_event(
            campaign_id=campaign_id,
            room_id=campaign_id,
            actor_user_id=user_id,
            event_type=CardEventType.CARD_DRAWN,
            payload={"deck_instance_id": deck_instance_id, "card_ids": drawn, "target_pile_id": target["id"]},
            visibility=visibility,
        )
        return CardServiceResult(
            success=True,
            payload={
                "event": event,
                "cards": [self._redact(card, definitions.get(card["card_definition_id"]), user_id=user_id, role=role) for card in moved],
                "target_pile_id": target["id"],
            },
        )

    def reveal(self, *, campaign_id: str, user_id: str, card_ids: list[str]) -> CardServiceResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        if role is None:
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        cards = [card for card_id in card_ids if (card := self.cards.get_card(card_id)) is not None]
        if not cards or any(card.get("campaign_id") != campaign_id for card in cards):
            return CardServiceResult(success=False, error_key="game.cards.errors.card_not_found")
        if any(not can_reveal_card(actor_user_id=user_id, actor_role=role, card_instance=card) for card in cards):
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        ids = [card["id"] for card in cards]
        self.cards.update_cards_face_visibility(card_ids=ids, visibility=CardVisibility.ROOM, face_state=CardFaceState.FACE_UP)
        self.cards.create_event(
            campaign_id=campaign_id,
            room_id=campaign_id,
            actor_user_id=user_id,
            event_type=CardEventType.CARD_REVEALED,
            payload={"card_ids": ids},
            visibility=CardVisibility.ROOM,
        )
        return CardServiceResult(success=True, payload={"card_ids": ids})

    def discard(self, *, campaign_id: str, user_id: str, card_ids: list[str]) -> CardServiceResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        if role is None:
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        cards = [card for card_id in card_ids if (card := self.cards.get_card(card_id)) is not None]
        if not cards or any(card.get("campaign_id") != campaign_id for card in cards):
            return CardServiceResult(success=False, error_key="game.cards.errors.card_not_found")
        if any(not can_discard_card(actor_user_id=user_id, actor_role=role, card_instance=card) for card in cards):
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        by_deck_and_pile: dict[tuple[str, str], list[dict]] = {}
        scene_cards: list[dict] = []
        for card in cards:
            if card.get("current_scene_id"):
                scene_cards.append(card)
                continue
            current_pile_id = str(card.get("current_pile_id") or "")
            by_deck_and_pile.setdefault((card["deck_instance_id"], current_pile_id), []).append(card)
        for card in scene_cards:
            discard = self.cards.find_pile(deck_instance_id=card["deck_instance_id"], kind=PileKind.DISCARD)
            placement = self.cards.get_scene_card_placement_for_card(card["id"])
            if discard is None or placement is None:
                return CardServiceResult(success=False, error_key="game.cards.errors.pile_not_found")
            self.cards.move_scene_card_to_pile(
                placement_id=placement["id"],
                target_pile_id=discard["id"],
                owner_user_id=None,
                visibility=CardVisibility.ROOM,
                face_state=CardFaceState.FACE_UP,
            )
        for (deck_instance_id, source_pile_id), deck_cards in by_deck_and_pile.items():
            discard = self.cards.find_pile(deck_instance_id=deck_instance_id, kind=PileKind.DISCARD)
            if discard is None:
                return CardServiceResult(success=False, error_key="game.cards.errors.pile_not_found")
            self.cards.move_cards_between_piles(
                source_pile_id=source_pile_id,
                target_pile_id=discard["id"],
                card_ids=[card["id"] for card in deck_cards],
                owner_user_id=None,
                visibility=CardVisibility.ROOM,
                face_state=CardFaceState.FACE_UP,
            )
        ids = [card["id"] for card in cards]
        self.cards.create_event(
            campaign_id=campaign_id,
            room_id=campaign_id,
            actor_user_id=user_id,
            event_type=CardEventType.CARD_DISCARDED,
            payload={"card_ids": ids},
            visibility=CardVisibility.ROOM,
        )
        return CardServiceResult(success=True, payload={"card_ids": ids})

    def card_front_asset(self, *, campaign_id: str, user_id: str, card_id: str) -> CardServiceResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        card = self.cards.get_card(card_id)
        if role is None:
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        if card is None or card.get("campaign_id") != campaign_id:
            return CardServiceResult(success=False, error_key="game.cards.errors.card_not_found")
        if not can_play_card_to_scene(actor_user_id=user_id, actor_role=role, card_instance=card):
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        definition = self.cards.definitions_by_id([card["card_definition_id"]]).get(card["card_definition_id"])
        front_asset_id = (definition or {}).get("front_asset_id")
        if not front_asset_id:
            return CardServiceResult(success=False, error_key="game.cards.errors.missing_front_asset")
        return CardServiceResult(success=True, payload={"asset_id": front_asset_id, "card_id": card_id})

    def play_to_scene(
        self,
        *,
        campaign_id: str,
        user_id: str,
        card_id: str,
        scene_id: str,
        x: float,
        y: float,
        rotation: float = 0.0,
        scale: float = 1.0,
        reveal: bool = True,
    ) -> CardServiceResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        card = self.cards.get_card(card_id)
        scene = self.scenes.get_by_id(scene_id)
        if role is None:
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        if card is None or card.get("campaign_id") != campaign_id:
            return CardServiceResult(success=False, error_key="game.cards.errors.card_not_found")
        if scene is None or scene.get("campaign_id") != campaign_id:
            return CardServiceResult(success=False, error_key="game.cards.errors.scene_not_found")
        if not can_play_card_to_scene(actor_user_id=user_id, actor_role=role, card_instance=card):
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        visibility = CardVisibility.ROOM
        face_state = CardFaceState.FACE_UP if reveal else CardFaceState.FACE_DOWN
        try:
            placement = self.cards.create_scene_card_placement(
                campaign_id=campaign_id,
                scene_id=scene_id,
                card_instance_id=card_id,
                owner_user_id=card.get("owner_user_id"),
                x=x,
                y=y,
                rotation=rotation,
                scale=scale,
                face_state=face_state,
                visibility=visibility,
            )
        except InvalidCardMoveError:
            return CardServiceResult(success=False, error_key="game.cards.errors.invalid_move")
        moved = self.cards.get_card(card_id)
        definitions = self.cards.definitions_by_id([moved["card_definition_id"]]) if moved else {}
        event = self.cards.create_event(
            campaign_id=campaign_id,
            room_id=campaign_id,
            actor_user_id=user_id,
            event_type=CardEventType.CARD_PLAYED_TO_SCENE,
            payload={"card_id": card_id, "scene_id": scene_id, "placement_id": placement["id"]},
            visibility=visibility,
        )
        return CardServiceResult(
            success=True,
            payload={
                "event": event,
                "placement": placement,
                "card": self._redact(moved, definitions.get(moved["card_definition_id"]), user_id=user_id, role=role) if moved else None,
            },
        )

    def update_scene_placement(
        self,
        *,
        campaign_id: str,
        user_id: str,
        placement_id: str,
        x: float | None = None,
        y: float | None = None,
        rotation: float | None = None,
        scale: float | None = None,
        z_index: int | None = None,
        face_state: CardFaceState | None = None,
    ) -> CardServiceResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        placement = self.cards.get_scene_card_placement(placement_id)
        if role is None:
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        if placement is None or placement.get("campaign_id") != campaign_id:
            return CardServiceResult(success=False, error_key="game.cards.errors.placement_not_found")
        card = self.cards.get_card(placement["card_instance_id"])
        if card is None or not can_play_card_to_scene(actor_user_id=user_id, actor_role=role, card_instance=card):
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        if placement.get("locked") and role not in {"gm", "assistant_gm"}:
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        visibility = CardVisibility.ROOM if face_state is not None else None
        updated = self.cards.update_scene_card_placement(
            placement_id=placement_id,
            x=x,
            y=y,
            rotation=rotation,
            scale=scale,
            z_index=z_index,
            face_state=face_state,
            visibility=visibility,
        )
        event_type = CardEventType.CARD_MOVED
        if face_state == CardFaceState.FACE_UP:
            event_type = CardEventType.CARD_REVEALED
        elif face_state == CardFaceState.FACE_DOWN:
            event_type = CardEventType.CARD_HIDDEN
        event = self.cards.create_event(
            campaign_id=campaign_id,
            room_id=campaign_id,
            actor_user_id=user_id,
            event_type=event_type,
            payload={"placement_id": placement_id, "card_id": placement["card_instance_id"]},
            visibility=CardVisibility.ROOM,
        )
        return CardServiceResult(success=True, payload={"event": event, "placement": updated})

    def discard_scene_placement(self, *, campaign_id: str, user_id: str, placement_id: str) -> CardServiceResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        placement = self.cards.get_scene_card_placement(placement_id)
        if role is None:
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        if placement is None or placement.get("campaign_id") != campaign_id:
            return CardServiceResult(success=False, error_key="game.cards.errors.placement_not_found")
        card = self.cards.get_card(placement["card_instance_id"])
        if card is None or not can_discard_card(actor_user_id=user_id, actor_role=role, card_instance=card):
            return CardServiceResult(success=False, error_key="permissions.errors.denied")
        discard = self.cards.find_pile(deck_instance_id=card["deck_instance_id"], kind=PileKind.DISCARD)
        if discard is None:
            return CardServiceResult(success=False, error_key="game.cards.errors.pile_not_found")
        card_id = self.cards.move_scene_card_to_pile(
            placement_id=placement_id,
            target_pile_id=discard["id"],
            owner_user_id=None,
            visibility=CardVisibility.ROOM,
            face_state=CardFaceState.FACE_UP,
        )
        event = self.cards.create_event(
            campaign_id=campaign_id,
            room_id=campaign_id,
            actor_user_id=user_id,
            event_type=CardEventType.CARD_DISCARDED,
            payload={"card_ids": [card_id], "placement_id": placement_id},
            visibility=CardVisibility.ROOM,
        )
        return CardServiceResult(success=True, payload={"event": event, "card_ids": [card_id]})

    def _role(self, *, campaign_id: str, user_id: str) -> str | None:
        return self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)

    def _normalize_definition_input(self, card: dict) -> dict:
        normalized = dict(card)
        if not normalized.get("front_asset_id") and normalized.get("front"):
            normalized["front_asset_id"] = normalized.get("front")
        if not normalized.get("back_asset_id") and normalized.get("back"):
            normalized["back_asset_id"] = normalized.get("back")
        return normalized

    def _card_exists_visible(self, *, card: dict, user_id: str, role: str) -> bool:
        visibility = card.get("visibility")
        if role in {"gm", "assistant_gm"} and visibility != CardVisibility.SECRET.value:
            return True
        if visibility in {CardVisibility.ROOM.value, CardVisibility.PLAYERS.value, CardVisibility.PUBLIC.value}:
            return True
        if visibility == CardVisibility.OWNER_ONLY.value and card.get("owner_user_id") == user_id:
            return True
        return should_card_front_be_visible(
            self._card_dataclass(card),
            viewer_user_id=user_id,
            viewer_role=role,
            gm_can_peek=True,
        )

    def _redact(self, card: dict, definition: dict | None, *, user_id: str, role: str) -> dict:
        return redact_card_for_viewer(
            self._card_dataclass(card),
            self._definition_dataclass(definition) if definition is not None else None,
            viewer_user_id=user_id,
            viewer_role=role,
            gm_can_peek=True,
        )

    def _card_dataclass(self, row: dict) -> CardInstance:
        return CardInstance(
            id=row["id"],
            campaign_id=row["campaign_id"],
            deck_instance_id=row["deck_instance_id"],
            card_definition_id=row["card_definition_id"],
            current_pile_id=row.get("current_pile_id"),
            current_scene_id=row.get("current_scene_id"),
            owner_user_id=row.get("owner_user_id"),
            face_state=CardFaceState(row.get("face_state") or CardFaceState.FACE_DOWN.value),
            visibility=CardVisibility(row.get("visibility") or CardVisibility.GM_ONLY.value),
            locked=bool(row.get("locked")),
            metadata=row.get("metadata") if isinstance(row.get("metadata"), dict) else {},
        )

    def _definition_dataclass(self, row: dict) -> CardDefinition:
        front_asset = CardAssetRef(row["front_asset_id"]) if row.get("front_asset_id") else None
        back_asset = CardAssetRef(row["back_asset_id"]) if row.get("back_asset_id") else None
        return CardDefinition(
            id=row["id"],
            deck_definition_id=row["deck_definition_id"],
            name=row["name"],
            front_asset=front_asset,
            back_asset=back_asset,
            subtitle=row.get("subtitle"),
            description=row.get("description"),
            tags=row.get("tags") if isinstance(row.get("tags"), list) else [],
            metadata=row.get("metadata") if isinstance(row.get("metadata"), dict) else {},
            sort_key=row.get("sort_key"),
            quantity=int(row.get("quantity") or 1),
        )
