from __future__ import annotations

from collections.abc import Sequence
import json
import time
import uuid
from typing import Any

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update

from app.engine.decks.cards import CardEventType
from app.engine.decks.cards import CardFaceState
from app.engine.decks.cards import DrawMode
from app.engine.decks.cards import InvalidCardMoveError
from app.engine.decks.cards import CardVisibility
from app.engine.decks.cards import DeckScope
from app.engine.decks.cards import PileKind
from app.engine.decks.cards import select_cards_for_draw
from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import card_deck_definitions
from app.persistence.tables import card_deck_instances
from app.persistence.tables import card_definitions
from app.persistence.tables import card_events
from app.persistence.tables import card_instances
from app.persistence.tables import card_pile_entries
from app.persistence.tables import card_piles
from app.persistence.tables import scene_card_placements


class CardRepository:
    def create_deck_definition(
        self,
        *,
        campaign_id: str | None,
        package_id: str | None,
        owner_user_id: str | None,
        scope: DeckScope,
        name: str,
        description: str | None = None,
        default_back_asset_id: str | None = None,
        editable: bool = True,
        metadata: dict | None = None,
        cards: Sequence[dict] = (),
    ) -> dict:
        now = int(time.time())
        deck_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                insert(card_deck_definitions).values(
                    id=deck_id,
                    campaign_id=campaign_id,
                    package_id=package_id,
                    owner_user_id=owner_user_id,
                    scope=scope.value,
                    name=name,
                    description=description,
                    default_back_asset_id=default_back_asset_id,
                    editable=1 if editable else 0,
                    metadata_json=_dump(metadata or {}),
                    created_at=now,
                    updated_at=now,
                )
            )
            for raw in cards:
                quantity = max(1, min(999, int(raw.get("quantity") or 1)))
                conn.execute(
                    insert(card_definitions).values(
                        id=uuid.uuid4().hex,
                        deck_definition_id=deck_id,
                        name=str(raw.get("name") or "Card")[:191],
                        subtitle=raw.get("subtitle"),
                        description=raw.get("description"),
                        front_asset_id=raw.get("front_asset_id"),
                        back_asset_id=raw.get("back_asset_id"),
                        tags_json=_dump(raw.get("tags") if isinstance(raw.get("tags"), list) else []),
                        metadata_json=_dump(raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}),
                        sort_key=raw.get("sort_key"),
                        quantity=quantity,
                        created_at=now,
                        updated_at=now,
                    )
                )
            row = self._get_deck_definition(conn, deck_id)
        if row is None:
            raise RuntimeError("Created card deck definition could not be read back.")
        return _decode_deck_definition(row)

    def get_deck_definition(self, deck_definition_id: str) -> dict | None:
        with engine_connect() as conn:
            row = self._get_deck_definition(conn, deck_definition_id)
        return _decode_deck_definition(row) if row is not None else None

    def list_deck_definitions(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(card_deck_definitions)
                    .where(
                        (card_deck_definitions.c.campaign_id == campaign_id)
                        | (card_deck_definitions.c.scope == DeckScope.PACKAGE.value)
                    )
                    .order_by(card_deck_definitions.c.created_at.desc())
                )
            )
        return [_decode_deck_definition(row) for row in rows]

    def list_card_definitions(self, *, deck_definition_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(card_definitions)
                    .where(card_definitions.c.deck_definition_id == deck_definition_id)
                    .order_by(card_definitions.c.sort_key.asc(), card_definitions.c.created_at.asc())
                )
            )
        return [_decode_card_definition(row) for row in rows]

    def create_deck_instance(
        self,
        *,
        campaign_id: str,
        room_id: str | None,
        deck_definition_id: str,
        owner_user_id: str | None,
        name: str,
        metadata: dict | None = None,
    ) -> dict:
        now = int(time.time())
        deck_instance_id = uuid.uuid4().hex
        draw_pile_id = uuid.uuid4().hex
        discard_pile_id = uuid.uuid4().hex
        revealed_pile_id = uuid.uuid4().hex
        removed_pile_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                insert(card_deck_instances).values(
                    id=deck_instance_id,
                    campaign_id=campaign_id,
                    room_id=room_id,
                    deck_definition_id=deck_definition_id,
                    owner_user_id=owner_user_id,
                    name=name,
                    active=1,
                    metadata_json=_dump(metadata or {}),
                    created_at=now,
                    updated_at=now,
                )
            )
            for pile_id, kind, pile_name, visibility in [
                (draw_pile_id, PileKind.DRAW, "Draw", CardVisibility.GM_ONLY),
                (discard_pile_id, PileKind.DISCARD, "Discard", CardVisibility.ROOM),
                (revealed_pile_id, PileKind.REVEALED, "Revealed", CardVisibility.ROOM),
                (removed_pile_id, PileKind.REMOVED, "Removed", CardVisibility.GM_ONLY),
            ]:
                conn.execute(
                    insert(card_piles).values(
                        id=pile_id,
                        campaign_id=campaign_id,
                        deck_instance_id=deck_instance_id,
                        owner_user_id=None,
                        kind=kind.value,
                        name=pile_name,
                        visibility=visibility.value,
                        ordered=1,
                        metadata_json="{}",
                        created_at=now,
                        updated_at=now,
                    )
                )
            position = 0
            definitions = all_dicts(
                conn.execute(
                    select(card_definitions)
                    .where(card_definitions.c.deck_definition_id == deck_definition_id)
                    .order_by(card_definitions.c.sort_key.asc(), card_definitions.c.created_at.asc())
                )
            )
            for definition in definitions:
                for _ in range(max(1, int(definition.get("quantity") or 1))):
                    card_id = uuid.uuid4().hex
                    conn.execute(
                        insert(card_instances).values(
                            id=card_id,
                            campaign_id=campaign_id,
                            deck_instance_id=deck_instance_id,
                            card_definition_id=definition["id"],
                            current_pile_id=draw_pile_id,
                            current_scene_id=None,
                            owner_user_id=None,
                            face_state=CardFaceState.FACE_DOWN.value,
                            visibility=CardVisibility.GM_ONLY.value,
                            locked=0,
                            metadata_json="{}",
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    conn.execute(
                        insert(card_pile_entries).values(
                            pile_id=draw_pile_id,
                            card_instance_id=card_id,
                            position=position,
                            inserted_at=now,
                        )
                    )
                    position += 1
            row = self._get_deck_instance(conn, deck_instance_id)
        if row is None:
            raise RuntimeError("Created card deck instance could not be read back.")
        return _decode_deck_instance(row)

    def get_deck_instance(self, deck_instance_id: str) -> dict | None:
        with engine_connect() as conn:
            row = self._get_deck_instance(conn, deck_instance_id)
        return _decode_deck_instance(row) if row is not None else None

    def list_deck_instances(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(card_deck_instances)
                    .where(card_deck_instances.c.campaign_id == campaign_id)
                    .where(card_deck_instances.c.active == 1)
                    .order_by(card_deck_instances.c.created_at.desc())
                )
            )
        return [_decode_deck_instance(row) for row in rows]

    def delete_deck_instance(self, *, deck_instance_id: str) -> None:
        # Tear down the whole deck instance: its placements, pile entries, cards
        # and piles, then the instance row. Explicit (not relying on FK cascade)
        # so it behaves the same regardless of SQLite PRAGMA settings.
        with engine_begin() as conn:
            card_ids = [
                str(row["id"])
                for row in all_dicts(
                    conn.execute(
                        select(card_instances.c.id)
                        .where(card_instances.c.deck_instance_id == deck_instance_id)
                    )
                )
            ]
            pile_ids = [
                str(row["id"])
                for row in all_dicts(
                    conn.execute(
                        select(card_piles.c.id)
                        .where(card_piles.c.deck_instance_id == deck_instance_id)
                    )
                )
            ]
            if card_ids:
                conn.execute(delete(scene_card_placements).where(scene_card_placements.c.card_instance_id.in_(card_ids)))
                conn.execute(delete(card_pile_entries).where(card_pile_entries.c.card_instance_id.in_(card_ids)))
            if pile_ids:
                conn.execute(delete(card_pile_entries).where(card_pile_entries.c.pile_id.in_(pile_ids)))
            if card_ids:
                conn.execute(delete(card_instances).where(card_instances.c.id.in_(card_ids)))
            conn.execute(delete(card_piles).where(card_piles.c.deck_instance_id == deck_instance_id))
            conn.execute(delete(card_deck_instances).where(card_deck_instances.c.id == deck_instance_id))

    def create_hand_pile(self, *, campaign_id: str, owner_user_id: str, name: str | None = None) -> dict:
        now = int(time.time())
        pile_id = uuid.uuid4().hex
        with engine_begin() as conn:
            existing = one_or_none(
                conn.execute(
                    select(card_piles)
                    .where(card_piles.c.campaign_id == campaign_id)
                    .where(card_piles.c.owner_user_id == owner_user_id)
                    .where(card_piles.c.kind == PileKind.HAND.value)
                    .limit(1)
                )
            )
            if existing is not None:
                return _decode_pile(existing)
            conn.execute(
                insert(card_piles).values(
                    id=pile_id,
                    campaign_id=campaign_id,
                    deck_instance_id=None,
                    owner_user_id=owner_user_id,
                    kind=PileKind.HAND.value,
                    name=name or "Hand",
                    visibility=CardVisibility.OWNER_ONLY.value,
                    ordered=1,
                    metadata_json="{}",
                    created_at=now,
                    updated_at=now,
                )
            )
            row = self._get_pile(conn, pile_id)
        if row is None:
            raise RuntimeError("Created card hand pile could not be read back.")
        return _decode_pile(row)

    def get_pile(self, pile_id: str) -> dict | None:
        with engine_connect() as conn:
            row = self._get_pile(conn, pile_id)
        return _decode_pile(row) if row is not None else None

    def find_pile(self, *, deck_instance_id: str, kind: PileKind) -> dict | None:
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(card_piles)
                    .where(card_piles.c.deck_instance_id == deck_instance_id)
                    .where(card_piles.c.kind == kind.value)
                    .limit(1)
                )
            )
        return _decode_pile(row) if row is not None else None

    def list_piles(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(card_piles)
                    .where(card_piles.c.campaign_id == campaign_id)
                    .order_by(card_piles.c.created_at.asc())
                )
            )
        return [_decode_pile(row) for row in rows]

    def get_pile_order(self, pile_id: str) -> list[str]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(card_pile_entries.c.card_instance_id)
                    .where(card_pile_entries.c.pile_id == pile_id)
                    .order_by(card_pile_entries.c.position.asc())
                )
            )
        return [str(row["card_instance_id"]) for row in rows]

    def replace_pile_order(self, *, pile_id: str, card_ids: Sequence[str]) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(delete(card_pile_entries).where(card_pile_entries.c.pile_id == pile_id))
            for index, card_id in enumerate(card_ids):
                conn.execute(
                    insert(card_pile_entries).values(
                        pile_id=pile_id,
                        card_instance_id=str(card_id),
                        position=index,
                        inserted_at=now,
                    )
                )
                conn.execute(
                    update(card_instances)
                    .where(card_instances.c.id == str(card_id))
                    .values(current_pile_id=pile_id, current_scene_id=None, updated_at=now)
                )

    def move_cards_between_piles(
        self,
        *,
        source_pile_id: str,
        target_pile_id: str,
        card_ids: Sequence[str],
        owner_user_id: str | None,
        visibility: CardVisibility,
        face_state: CardFaceState,
    ) -> None:
        now = int(time.time())
        moving = [str(card_id) for card_id in card_ids]
        if not moving:
            return
        with engine_begin() as conn:
            conn.execute(
                select(card_piles.c.id)
                .where(card_piles.c.id.in_([source_pile_id, target_pile_id]))
                .with_for_update()
            )
            source_rows = all_dicts(
                conn.execute(
                    select(card_pile_entries.c.card_instance_id)
                    .where(card_pile_entries.c.pile_id == source_pile_id)
                    .where(card_pile_entries.c.card_instance_id.in_(moving))
                )
            )
            if {row["card_instance_id"] for row in source_rows} != set(moving):
                raise InvalidCardMoveError("card is not in source pile")
            target_count = one_or_none(
                conn.execute(
                    select(card_pile_entries.c.position)
                    .where(card_pile_entries.c.pile_id == target_pile_id)
                    .order_by(card_pile_entries.c.position.desc())
                    .limit(1)
                )
            )
            next_position = int(target_count["position"]) + 1 if target_count is not None else 0
            conn.execute(
                delete(card_pile_entries)
                .where(card_pile_entries.c.pile_id == source_pile_id)
                .where(card_pile_entries.c.card_instance_id.in_(moving))
            )
            for offset, card_id in enumerate(moving):
                conn.execute(
                    insert(card_pile_entries).values(
                        pile_id=target_pile_id,
                        card_instance_id=card_id,
                        position=next_position + offset,
                        inserted_at=now,
                    )
                )
            conn.execute(
                update(card_instances)
                .where(card_instances.c.id.in_(moving))
                .where(card_instances.c.current_pile_id == source_pile_id)
                .values(
                    current_pile_id=target_pile_id,
                    current_scene_id=None,
                    owner_user_id=owner_user_id,
                    visibility=visibility.value,
                    face_state=face_state.value,
                    updated_at=now,
                )
            )

    def draw_cards_between_piles(
        self,
        *,
        source_pile_id: str,
        target_pile_id: str,
        count: int,
        mode: DrawMode,
        owner_user_id: str | None,
        visibility: CardVisibility,
        face_state: CardFaceState,
    ) -> list[str]:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                select(card_piles.c.id)
                .where(card_piles.c.id.in_([source_pile_id, target_pile_id]))
                .with_for_update()
            )
            order_rows = all_dicts(
                conn.execute(
                    select(card_pile_entries.c.card_instance_id)
                    .where(card_pile_entries.c.pile_id == source_pile_id)
                    .order_by(card_pile_entries.c.position.asc())
                    .with_for_update()
                )
            )
            order = [str(row["card_instance_id"]) for row in order_rows]
            drawn, _remaining = select_cards_for_draw(order, count=count, mode=mode)
            target_count = one_or_none(
                conn.execute(
                    select(card_pile_entries.c.position)
                    .where(card_pile_entries.c.pile_id == target_pile_id)
                    .order_by(card_pile_entries.c.position.desc())
                    .limit(1)
                    .with_for_update()
                )
            )
            next_position = int(target_count["position"]) + 1 if target_count is not None else 0
            deleted = conn.execute(
                delete(card_pile_entries)
                .where(card_pile_entries.c.pile_id == source_pile_id)
                .where(card_pile_entries.c.card_instance_id.in_(drawn))
            )
            if deleted.rowcount != len(drawn):
                raise InvalidCardMoveError("draw source changed before move")
            for offset, card_id in enumerate(drawn):
                conn.execute(
                    insert(card_pile_entries).values(
                        pile_id=target_pile_id,
                        card_instance_id=card_id,
                        position=next_position + offset,
                        inserted_at=now,
                    )
                )
            updated = conn.execute(
                update(card_instances)
                .where(card_instances.c.id.in_(drawn))
                .where(card_instances.c.current_pile_id == source_pile_id)
                .values(
                    current_pile_id=target_pile_id,
                    current_scene_id=None,
                    owner_user_id=owner_user_id,
                    visibility=visibility.value,
                    face_state=face_state.value,
                    updated_at=now,
                )
            )
            if updated.rowcount != len(drawn):
                raise InvalidCardMoveError("draw source changed before card update")
        return drawn

    def get_card(self, card_id: str) -> dict | None:
        with engine_connect() as conn:
            row = self._get_card(conn, card_id)
        return _decode_card_instance(row) if row is not None else None

    def list_cards_for_campaign(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(select(card_instances).where(card_instances.c.campaign_id == campaign_id))
            )
        return [_decode_card_instance(row) for row in rows]

    def list_cards_for_pile(self, *, pile_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(card_instances)
                    .select_from(
                        card_instances.join(
                            card_pile_entries,
                            card_pile_entries.c.card_instance_id == card_instances.c.id,
                        )
                    )
                    .where(card_pile_entries.c.pile_id == pile_id)
                    .order_by(card_pile_entries.c.position.asc())
                )
            )
        return [_decode_card_instance(row) for row in rows]

    def list_cards_for_deck(self, *, deck_instance_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(card_instances)
                    .where(card_instances.c.deck_instance_id == deck_instance_id)
                    .order_by(card_instances.c.created_at.asc())
                )
            )
        return [_decode_card_instance(row) for row in rows]

    def create_scene_card_placement(
        self,
        *,
        campaign_id: str,
        scene_id: str,
        card_instance_id: str,
        owner_user_id: str | None,
        x: float,
        y: float,
        rotation: float = 0.0,
        scale: float = 1.0,
        z_index: int | None = None,
        face_state: CardFaceState = CardFaceState.FACE_UP,
        visibility: CardVisibility = CardVisibility.ROOM,
        metadata: dict | None = None,
    ) -> dict:
        now = int(time.time())
        placement_id = uuid.uuid4().hex
        with engine_begin() as conn:
            card = self._get_card(conn, card_instance_id)
            if card is None or card.get("campaign_id") != campaign_id:
                raise InvalidCardMoveError("card is not in campaign")
            if card.get("current_scene_id"):
                raise InvalidCardMoveError("card is already on a scene")
            if card.get("current_pile_id"):
                conn.execute(
                    delete(card_pile_entries).where(card_pile_entries.c.card_instance_id == card_instance_id)
                )
            if z_index is None:
                current_top = one_or_none(
                    conn.execute(
                        select(scene_card_placements.c.z_index)
                        .where(scene_card_placements.c.scene_id == scene_id)
                        .order_by(scene_card_placements.c.z_index.desc())
                        .limit(1)
                    )
                )
                z_index = int(current_top["z_index"]) + 1 if current_top is not None else 0
            conn.execute(
                insert(scene_card_placements).values(
                    id=placement_id,
                    campaign_id=campaign_id,
                    scene_id=scene_id,
                    card_instance_id=card_instance_id,
                    owner_user_id=owner_user_id,
                    x=float(x),
                    y=float(y),
                    rotation=float(rotation),
                    scale=max(0.1, min(4.0, float(scale))),
                    z_index=int(z_index),
                    face_state=face_state.value,
                    visibility=visibility.value,
                    locked=0,
                    metadata_json=_dump(metadata or {}),
                    created_at=now,
                    updated_at=now,
                )
            )
            conn.execute(
                update(card_instances)
                .where(card_instances.c.id == card_instance_id)
                .values(
                    current_pile_id=None,
                    current_scene_id=scene_id,
                    owner_user_id=owner_user_id,
                    visibility=visibility.value,
                    face_state=face_state.value,
                    updated_at=now,
                )
            )
            row = self._get_scene_card_placement(conn, placement_id)
        if row is None:
            raise RuntimeError("Created scene card placement could not be read back.")
        return _decode_scene_card_placement(row)

    def get_scene_card_placement(self, placement_id: str) -> dict | None:
        with engine_connect() as conn:
            row = self._get_scene_card_placement(conn, placement_id)
        return _decode_scene_card_placement(row) if row is not None else None

    def get_scene_card_placement_for_card(self, card_instance_id: str) -> dict | None:
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(scene_card_placements)
                    .where(scene_card_placements.c.card_instance_id == card_instance_id)
                    .limit(1)
                )
            )
        return _decode_scene_card_placement(row) if row is not None else None

    def list_scene_card_placements(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(scene_card_placements)
                    .where(scene_card_placements.c.campaign_id == campaign_id)
                    .order_by(scene_card_placements.c.scene_id.asc(), scene_card_placements.c.z_index.asc())
                )
            )
        return [_decode_scene_card_placement(row) for row in rows]

    def update_scene_card_placement(
        self,
        *,
        placement_id: str,
        x: float | None = None,
        y: float | None = None,
        rotation: float | None = None,
        scale: float | None = None,
        z_index: int | None = None,
        face_state: CardFaceState | None = None,
        visibility: CardVisibility | None = None,
        locked: bool | None = None,
    ) -> dict | None:
        now = int(time.time())
        values: dict[str, Any] = {"updated_at": now}
        if x is not None:
            values["x"] = float(x)
        if y is not None:
            values["y"] = float(y)
        if rotation is not None:
            values["rotation"] = float(rotation)
        if scale is not None:
            values["scale"] = max(0.1, min(4.0, float(scale)))
        if z_index is not None:
            values["z_index"] = int(z_index)
        if face_state is not None:
            values["face_state"] = face_state.value
        if visibility is not None:
            values["visibility"] = visibility.value
        if locked is not None:
            values["locked"] = 1 if locked else 0
        with engine_begin() as conn:
            placement = self._get_scene_card_placement(conn, placement_id)
            if placement is None:
                return None
            conn.execute(update(scene_card_placements).where(scene_card_placements.c.id == placement_id).values(**values))
            card_values = {"updated_at": now}
            if face_state is not None:
                card_values["face_state"] = face_state.value
            if visibility is not None:
                card_values["visibility"] = visibility.value
            if card_values.keys() != {"updated_at"}:
                conn.execute(
                    update(card_instances)
                    .where(card_instances.c.id == placement["card_instance_id"])
                    .values(**card_values)
                )
            row = self._get_scene_card_placement(conn, placement_id)
        return _decode_scene_card_placement(row) if row is not None else None

    def move_scene_card_to_pile(
        self,
        *,
        placement_id: str,
        target_pile_id: str,
        owner_user_id: str | None,
        visibility: CardVisibility,
        face_state: CardFaceState,
    ) -> str:
        now = int(time.time())
        with engine_begin() as conn:
            placement = self._get_scene_card_placement(conn, placement_id)
            if placement is None:
                raise InvalidCardMoveError("scene placement not found")
            target_count = one_or_none(
                conn.execute(
                    select(card_pile_entries.c.position)
                    .where(card_pile_entries.c.pile_id == target_pile_id)
                    .order_by(card_pile_entries.c.position.desc())
                    .limit(1)
                )
            )
            next_position = int(target_count["position"]) + 1 if target_count is not None else 0
            card_id = str(placement["card_instance_id"])
            conn.execute(delete(scene_card_placements).where(scene_card_placements.c.id == placement_id))
            conn.execute(
                insert(card_pile_entries).values(
                    pile_id=target_pile_id,
                    card_instance_id=card_id,
                    position=next_position,
                    inserted_at=now,
                )
            )
            conn.execute(
                update(card_instances)
                .where(card_instances.c.id == card_id)
                .values(
                    current_pile_id=target_pile_id,
                    current_scene_id=None,
                    owner_user_id=owner_user_id,
                    visibility=visibility.value,
                    face_state=face_state.value,
                    updated_at=now,
                )
            )
        return card_id

    def reset_deck_instance(
        self,
        *,
        deck_instance_id: str,
        draw_pile_id: str,
        ordered_card_ids: Sequence[str],
    ) -> None:
        now = int(time.time())
        card_ids = [str(card_id) for card_id in ordered_card_ids]
        with engine_begin() as conn:
            conn.execute(
                delete(scene_card_placements).where(
                    scene_card_placements.c.card_instance_id.in_(card_ids)
                )
            )
            conn.execute(delete(card_pile_entries).where(card_pile_entries.c.card_instance_id.in_(card_ids)))
            for index, card_id in enumerate(card_ids):
                conn.execute(
                    insert(card_pile_entries).values(
                        pile_id=draw_pile_id,
                        card_instance_id=card_id,
                        position=index,
                        inserted_at=now,
                    )
                )
            conn.execute(
                update(card_instances)
                .where(card_instances.c.deck_instance_id == deck_instance_id)
                .values(
                    current_pile_id=draw_pile_id,
                    current_scene_id=None,
                    owner_user_id=None,
                    face_state=CardFaceState.FACE_DOWN.value,
                    visibility=CardVisibility.GM_ONLY.value,
                    updated_at=now,
                )
            )

    def definitions_by_id(self, definition_ids: Sequence[str]) -> dict[str, dict]:
        ids = [str(item) for item in definition_ids]
        if not ids:
            return {}
        with engine_connect() as conn:
            rows = all_dicts(conn.execute(select(card_definitions).where(card_definitions.c.id.in_(ids))))
        return {row["id"]: _decode_card_definition(row) for row in rows}

    def update_cards_face_visibility(
        self,
        *,
        card_ids: Sequence[str],
        visibility: CardVisibility,
        face_state: CardFaceState,
    ) -> None:
        ids = [str(card_id) for card_id in card_ids]
        if not ids:
            return
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(card_instances)
                .where(card_instances.c.id.in_(ids))
                .values(visibility=visibility.value, face_state=face_state.value, updated_at=now)
            )

    def create_event(
        self,
        *,
        campaign_id: str,
        room_id: str | None,
        actor_user_id: str,
        event_type: CardEventType,
        payload: dict,
        visibility: CardVisibility,
    ) -> dict:
        now = int(time.time())
        event_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                insert(card_events).values(
                    id=event_id,
                    campaign_id=campaign_id,
                    room_id=room_id,
                    actor_user_id=actor_user_id,
                    event_type=event_type.value,
                    payload_json=_dump(payload),
                    visibility=visibility.value,
                    created_at=now,
                )
            )
            row = one_or_none(conn.execute(select(card_events).where(card_events.c.id == event_id).limit(1)))
        if row is None:
            raise RuntimeError("Created card event could not be read back.")
        return _decode_event(row)

    def _get_deck_definition(self, conn, deck_definition_id: str) -> dict | None:
        return one_or_none(conn.execute(select(card_deck_definitions).where(card_deck_definitions.c.id == deck_definition_id).limit(1)))

    def _get_deck_instance(self, conn, deck_instance_id: str) -> dict | None:
        return one_or_none(conn.execute(select(card_deck_instances).where(card_deck_instances.c.id == deck_instance_id).limit(1)))

    def _get_pile(self, conn, pile_id: str) -> dict | None:
        return one_or_none(conn.execute(select(card_piles).where(card_piles.c.id == pile_id).limit(1)))

    def _get_card(self, conn, card_id: str) -> dict | None:
        return one_or_none(conn.execute(select(card_instances).where(card_instances.c.id == card_id).limit(1)))

    def _get_scene_card_placement(self, conn, placement_id: str) -> dict | None:
        return one_or_none(conn.execute(select(scene_card_placements).where(scene_card_placements.c.id == placement_id).limit(1)))


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode_json(raw: Any, fallback: Any) -> Any:
    if raw in (None, ""):
        return fallback
    if isinstance(raw, (dict, list)):
        return raw
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return fallback
    return parsed


def _decode_deck_definition(row: dict) -> dict:
    row["editable"] = bool(row.get("editable"))
    row["metadata"] = _decode_json(row.get("metadata_json"), {})
    return row


def _decode_card_definition(row: dict) -> dict:
    row["tags"] = _decode_json(row.get("tags_json"), [])
    row["metadata"] = _decode_json(row.get("metadata_json"), {})
    row["quantity"] = int(row.get("quantity") or 1)
    return row


def _decode_deck_instance(row: dict) -> dict:
    row["active"] = bool(row.get("active"))
    row["metadata"] = _decode_json(row.get("metadata_json"), {})
    return row


def _decode_pile(row: dict) -> dict:
    row["ordered"] = bool(row.get("ordered"))
    row["metadata"] = _decode_json(row.get("metadata_json"), {})
    return row


def _decode_card_instance(row: dict) -> dict:
    row["locked"] = bool(row.get("locked"))
    row["metadata"] = _decode_json(row.get("metadata_json"), {})
    return row


def _decode_scene_card_placement(row: dict) -> dict:
    row["locked"] = bool(row.get("locked"))
    row["metadata"] = _decode_json(row.get("metadata_json"), {})
    return row


def _decode_event(row: dict) -> dict:
    row["payload"] = _decode_json(row.get("payload_json"), {})
    return row
