from __future__ import annotations

import time
import uuid

from sqlalchemy import delete, insert, select, update

from app.persistence.database import all_dicts, engine_begin, engine_connect, one_or_none
from app.persistence.tables import combat_combatants as combatants_table
from app.persistence.tables import combat_encounters as encounters_table


class CombatEncounterRepository:
    """One active encounter per campaign, plus its combatants.

    Rows are stored in insertion order; the turn order is derived from
    ``sort_value`` at read time, so nothing has to be rewritten when a single
    value changes.
    """

    def get_active(self, *, campaign_id: str) -> dict | None:
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(encounters_table)
                    .where(encounters_table.c.campaign_id == campaign_id)
                    .where(encounters_table.c.status == "active")
                    .order_by(encounters_table.c.created_at.desc())
                    .limit(1)
                )
            )
        return dict(row) if row is not None else None

    def create(
        self, *, campaign_id: str, scene_id: str | None, created_by_user_id: str
    ) -> dict:
        now = int(time.time())
        combat_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                update(encounters_table)
                .where(encounters_table.c.campaign_id == campaign_id)
                .where(encounters_table.c.status == "active")
                .values(status="ended", ended_at=now, updated_at=now)
            )
            conn.execute(
                insert(encounters_table).values(
                    id=combat_id,
                    campaign_id=campaign_id,
                    scene_id=scene_id,
                    status="active",
                    round_number=1,
                    turn_index=0,
                    created_by_user_id=created_by_user_id,
                    started_at=now,
                    ended_at=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            row = self._get(conn, combat_id)
        if row is None:
            raise RuntimeError("Created combat encounter could not be read back.")
        return dict(row)

    def set_position(self, *, combat_id: str, round_number: int, turn_index: int) -> dict | None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(encounters_table)
                .where(encounters_table.c.id == combat_id)
                .values(
                    round_number=max(1, int(round_number)),
                    turn_index=max(0, int(turn_index)),
                    updated_at=now,
                )
            )
            row = self._get(conn, combat_id)
        return dict(row) if row is not None else None

    def end(self, *, combat_id: str) -> dict | None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(encounters_table)
                .where(encounters_table.c.id == combat_id)
                .values(status="ended", ended_at=now, updated_at=now)
            )
            row = self._get(conn, combat_id)
        return dict(row) if row is not None else None

    def list_combatants(self, *, combat_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(combatants_table)
                    .where(combatants_table.c.combat_id == combat_id)
                    .order_by(combatants_table.c.created_at.asc())
                )
            )
        return [_decode(row) for row in rows]

    def add_combatant(
        self,
        *,
        combat_id: str,
        actor_id: str | None,
        token_id: str | None,
        name: str,
        hidden: bool = False,
    ) -> dict:
        now = int(time.time())
        combatant_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                insert(combatants_table).values(
                    id=combatant_id,
                    combat_id=combat_id,
                    actor_id=actor_id,
                    token_id=token_id,
                    name=name,
                    initiative=None,
                    sort_value=None,
                    tie_break=0,
                    hidden=1 if hidden else 0,
                    defeated=0,
                    created_at=now,
                    updated_at=now,
                )
            )
            row = one_or_none(
                conn.execute(
                    select(combatants_table)
                    .where(combatants_table.c.id == combatant_id)
                    .limit(1)
                )
            )
        if row is None:
            raise RuntimeError("Created combatant could not be read back.")
        return _decode(row)

    def remove_combatant(self, *, combat_id: str, combatant_id: str) -> None:
        with engine_begin() as conn:
            conn.execute(
                delete(combatants_table)
                .where(combatants_table.c.combat_id == combat_id)
                .where(combatants_table.c.id == combatant_id)
            )

    def set_initiative(
        self,
        *,
        combatant_id: str,
        initiative: str | None,
        sort_value: float | None,
        tie_break: float = 0,
    ) -> None:
        with engine_begin() as conn:
            conn.execute(
                update(combatants_table)
                .where(combatants_table.c.id == combatant_id)
                .values(
                    initiative=initiative,
                    sort_value=sort_value,
                    tie_break=float(tie_break),
                    updated_at=int(time.time()),
                )
            )

    def set_label(self, *, combatant_id: str, initiative: str | None) -> None:
        """Write the displayed value without touching where the row sorts.

        Systems that do not sort by the value keep their order in ``sort_value``
        independently, so relabelling must leave it alone.
        """
        with engine_begin() as conn:
            conn.execute(
                update(combatants_table)
                .where(combatants_table.c.id == combatant_id)
                .values(initiative=initiative, updated_at=int(time.time()))
            )

    def renumber(self, *, combatant_ids: list[str]) -> None:
        """Write a hand-arranged order back as descending sort values.

        Renumbering the whole list on every move keeps the column dense and
        means a manual order never has to reason about gaps or ties.
        """
        now = int(time.time())
        total = len(combatant_ids)
        with engine_begin() as conn:
            for index, combatant_id in enumerate(combatant_ids):
                conn.execute(
                    update(combatants_table)
                    .where(combatants_table.c.id == combatant_id)
                    .values(sort_value=float(total - index), updated_at=now)
                )

    def set_flags(
        self, *, combatant_id: str, hidden: bool | None = None, defeated: bool | None = None
    ) -> None:
        values: dict = {"updated_at": int(time.time())}
        if hidden is not None:
            values["hidden"] = 1 if hidden else 0
        if defeated is not None:
            values["defeated"] = 1 if defeated else 0
        with engine_begin() as conn:
            conn.execute(
                update(combatants_table)
                .where(combatants_table.c.id == combatant_id)
                .values(**values)
            )

    def _get(self, conn, combat_id: str) -> dict | None:
        return one_or_none(
            conn.execute(
                select(encounters_table).where(encounters_table.c.id == combat_id).limit(1)
            )
        )


def _decode(row: dict) -> dict:
    row["hidden"] = bool(row.get("hidden"))
    row["defeated"] = bool(row.get("defeated"))
    initiative = row.get("initiative")
    row["initiative"] = str(initiative) if initiative is not None else None
    sort_value = row.get("sort_value")
    row["sort_value"] = float(sort_value) if sort_value is not None else None
    row["tie_break"] = float(row.get("tie_break") or 0)
    return row
