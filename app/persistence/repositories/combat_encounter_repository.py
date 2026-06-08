from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update

from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import combat_encounters as encounters_table
from app.persistence.tables import combat_events as events_table
from app.persistence.tables import combat_participants as participants_table


class CombatEncounterRepository:
    def get_active(self, *, campaign_id: str) -> dict | None:
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(encounters_table)
                    .where(encounters_table.c.campaign_id == campaign_id)
                    .where(encounters_table.c.status.in_(["active", "paused"]))
                    .order_by(encounters_table.c.started_at.desc(), encounters_table.c.created_at.desc())
                    .limit(1)
                )
            )
        return _decode_encounter(row) if row is not None else None

    def get(self, *, combat_id: str) -> dict | None:
        with engine_connect() as conn:
            row = self._get_encounter(conn, combat_id)
        return _decode_encounter(row) if row is not None else None

    def create(
        self,
        *,
        campaign_id: str,
        scene_id: str | None,
        mode: str,
        strategy: str,
        settings: dict,
        created_by_user_id: str,
    ) -> dict:
        now = int(time.time())
        combat_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                update(encounters_table)
                .where(encounters_table.c.campaign_id == campaign_id)
                .where(encounters_table.c.status.in_(["active", "paused"]))
                .values(status="ended", ended_at=now, updated_at=now)
            )
            conn.execute(
                insert(encounters_table).values(
                    id=combat_id,
                    campaign_id=campaign_id,
                    scene_id=scene_id,
                    status="active",
                    mode=mode,
                    strategy=strategy,
                    round_number=1,
                    turn_index=0,
                    phase="combat.start",
                    settings_json=json.dumps(settings or {}, ensure_ascii=False),
                    created_by_user_id=created_by_user_id,
                    started_at=now,
                    ended_at=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            row = self._get_encounter(conn, combat_id)
        if row is None:
            raise RuntimeError("Created combat encounter could not be read back.")
        return _decode_encounter(row)

    def update_state(
        self,
        *,
        combat_id: str,
        status: str | None = None,
        round_number: int | None = None,
        turn_index: int | None = None,
        phase: str | None = None,
        settings: dict | None = None,
        ended_at: int | None = None,
    ) -> dict | None:
        current = self.get(combat_id=combat_id)
        if current is None:
            return None
        now = int(time.time())
        next_status = status or current["status"]
        next_round = int(round_number if round_number is not None else current.get("round_number") or 1)
        next_turn = int(turn_index if turn_index is not None else current.get("turn_index") or 0)
        next_phase = phase or current.get("phase") or "round.start"
        next_settings = settings if settings is not None else current.get("settings", {})
        next_ended_at = ended_at if ended_at is not None else current.get("ended_at")
        with engine_begin() as conn:
            conn.execute(
                update(encounters_table)
                .where(encounters_table.c.id == combat_id)
                .values(
                    status=next_status,
                    round_number=max(1, next_round),
                    turn_index=max(0, next_turn),
                    phase=next_phase,
                    settings_json=json.dumps(next_settings or {}, ensure_ascii=False),
                    ended_at=next_ended_at,
                    updated_at=now,
                )
            )
            row = self._get_encounter(conn, combat_id)
        return _decode_encounter(row) if row is not None else None

    def end(self, *, combat_id: str) -> dict | None:
        return self.update_state(combat_id=combat_id, status="ended", phase="combat.end", ended_at=int(time.time()))

    def list_participants(self, *, combat_id: str, include_hidden: bool = True) -> list[dict]:
        stmt = select(participants_table).where(participants_table.c.combat_id == combat_id)
        if not include_hidden:
            stmt = stmt.where(participants_table.c.visible_to_players == 1)
        stmt = stmt.order_by(
            participants_table.c.sort_key.desc(),
            participants_table.c.initiative_value.desc(),
            participants_table.c.name.asc(),
            participants_table.c.created_at.asc(),
        )
        with engine_connect() as conn:
            rows = all_dicts(conn.execute(stmt))
        return [_decode_participant(row) for row in rows]

    def add_participant(
        self,
        *,
        combat_id: str,
        actor_id: str | None,
        token_id: str | None,
        name: str,
        visible_to_players: bool = True,
        group_key: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        now = int(time.time())
        participant_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                insert(participants_table).values(
                    id=participant_id,
                    combat_id=combat_id,
                    actor_id=actor_id,
                    token_id=token_id,
                    name=name,
                    initiative_label="",
                    initiative_value=None,
                    initiative_data_json="{}",
                    sort_key=0,
                    group_key=group_key,
                    visible_to_players=1 if visible_to_players else 0,
                    defeated=0,
                    metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
                    created_at=now,
                    updated_at=now,
                )
            )
            row = one_or_none(conn.execute(select(participants_table).where(participants_table.c.id == participant_id).limit(1)))
        if row is None:
            raise RuntimeError("Created combat participant could not be read back.")
        return _decode_participant(row)

    def remove_participant(self, *, combat_id: str, participant_id: str) -> None:
        with engine_begin() as conn:
            conn.execute(
                delete(participants_table)
                .where(participants_table.c.combat_id == combat_id)
                .where(participants_table.c.id == participant_id)
            )

    def update_participant_order(
        self,
        *,
        participant_id: str,
        initiative_label: str,
        initiative_value: float | None,
        initiative_data: dict,
        sort_key: float,
    ) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(participants_table)
                .where(participants_table.c.id == participant_id)
                .values(
                    initiative_label=initiative_label,
                    initiative_value=initiative_value,
                    initiative_data_json=json.dumps(initiative_data or {}, ensure_ascii=False),
                    sort_key=sort_key,
                    updated_at=now,
                )
            )

    def reorder_participants(self, *, combat_id: str, participant_ids: list[str]) -> None:
        now = int(time.time())
        total = len(participant_ids)
        with engine_begin() as conn:
            for index, participant_id in enumerate(participant_ids):
                sort_key = float(total - index)
                conn.execute(
                    update(participants_table)
                    .where(participants_table.c.combat_id == combat_id)
                    .where(participants_table.c.id == participant_id)
                    .values(sort_key=sort_key, initiative_value=sort_key, initiative_label=str(index + 1), updated_at=now)
                )

    def add_event(
        self,
        *,
        combat_id: str,
        round_number: int,
        turn_index: int,
        participant_id: str | None,
        actor_id: str | None,
        event_type: str,
        payload: dict | None = None,
    ) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                insert(events_table).values(
                    id=uuid.uuid4().hex,
                    combat_id=combat_id,
                    round_number=max(1, int(round_number or 1)),
                    turn_index=max(0, int(turn_index or 0)),
                    participant_id=participant_id,
                    actor_id=actor_id,
                    event_type=event_type,
                    payload_json=json.dumps(payload or {}, ensure_ascii=False),
                    created_at=now,
                )
            )

    def _get_encounter(self, conn, combat_id: str) -> dict | None:
        return one_or_none(conn.execute(select(encounters_table).where(encounters_table.c.id == combat_id).limit(1)))


def _decode_json(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _decode_encounter(row: dict) -> dict:
    row["settings"] = _decode_json(row.get("settings_json"))
    row["round"] = int(row.get("round_number") or 0)
    row["turnIndex"] = int(row.get("turn_index") or 0)
    return row


def _decode_participant(row: dict) -> dict:
    row["initiative_data"] = _decode_json(row.get("initiative_data_json"))
    row["metadata"] = _decode_json(row.get("metadata_json"))
    row["visible_to_players"] = bool(row.get("visible_to_players"))
    row["defeated"] = bool(row.get("defeated"))
    row["sort_key"] = float(row.get("sort_key") or 0)
    value = row.get("initiative_value")
    row["initiative_value"] = float(value) if value is not None else None
    return row
