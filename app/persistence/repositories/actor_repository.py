from __future__ import annotations

import time
import uuid

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update
from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.engine import upsert_statement
from app.persistence.tables import actor_owners
from app.persistence.tables import actors_core
from app.persistence.tables import users


class ActorRepository:
    """Persistence for actors, implemented with SQLAlchemy Core."""

    def create(
        self,
        *,
        campaign_id: str,
        system_id: str,
        actor_type: str,
        name: str,
        created_by_user_id: str,
        folder_id: str | None = None,
        permissions_json: str = "{}",
        owner_user_ids: list[str] | None = None,
    ) -> str:
        now = int(time.time())
        actor_id = uuid.uuid4().hex
        owners = owner_user_ids or []
        with engine_begin() as conn:
            conn.execute(
                insert(actors_core).values(
                    id=actor_id,
                    campaign_id=campaign_id,
                    system_id=system_id,
                    type=actor_type,
                    name=name,
                    folder_id=folder_id,
                    permissions_json=permissions_json,
                    status="active",
                    version=1,
                    created_by_user_id=created_by_user_id,
                    created_at=now,
                    updated_at=now,
                )
            )
            for owner_id in owners:
                self._insert_owner_ignore(conn, actor_id=actor_id, user_id=owner_id)
        return actor_id

    def get(self, actor_id: str) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(
                conn.execute(select(actors_core).where(actors_core.c.id == actor_id).limit(1))
            )

    def list_active_for_campaign(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(actors_core)
                    .where(actors_core.c.campaign_id == campaign_id)
                    .where(actors_core.c.status == "active")
                    .order_by(actors_core.c.created_at.asc())
                )
            )

    def update_core(
        self,
        *,
        actor_id: str,
        name: str,
        folder_id: str | None,
        portrait_asset_id: str | None,
        token_asset_id: str | None,
    ) -> int:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(actors_core)
                .where(actors_core.c.id == actor_id)
                .values(
                    name=name,
                    folder_id=folder_id,
                    portrait_asset_id=portrait_asset_id,
                    token_asset_id=token_asset_id,
                    version=actors_core.c.version + 1,
                    updated_at=now,
                )
            )
            row = one_or_none(
                conn.execute(
                    select(actors_core.c.version).where(actors_core.c.id == actor_id).limit(1)
                )
            )
        return int(row["version"]) if row is not None else 0

    def set_asset(self, *, actor_id: str, kind: str, storage_path: str) -> None:
        field = {
            "portrait": actors_core.c.portrait_asset_id,
            "token": actors_core.c.token_asset_id,
        }.get(kind)
        if field is None:
            raise ValueError("kind is invalid")

        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(actors_core)
                .where(actors_core.c.id == actor_id)
                .values(
                    {field.key: storage_path, "version": actors_core.c.version + 1, "updated_at": now}
                )
            )

    def set_folder(self, *, actor_id: str, folder_id: str | None) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(actors_core)
                .where(actors_core.c.id == actor_id)
                .values(folder_id=folder_id, updated_at=now)
            )

    def clear_folder(self, *, folder_id: str) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(actors_core)
                .where(actors_core.c.folder_id == folder_id)
                .values(folder_id=None, updated_at=now)
            )

                                                                              

    def has_owner(self, *, actor_id: str, user_id: str) -> bool:
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(actor_owners.c.actor_id)
                    .where(actor_owners.c.actor_id == actor_id)
                    .where(actor_owners.c.user_id == user_id)
                    .limit(1)
                )
            )
        return row is not None

    def add_owner(self, *, actor_id: str, user_id: str) -> None:
        with engine_begin() as conn:
            self._insert_owner_ignore(conn, actor_id=actor_id, user_id=user_id)

    def remove_owner(self, *, actor_id: str, user_id: str) -> None:
        with engine_begin() as conn:
            conn.execute(
                delete(actor_owners)
                .where(actor_owners.c.actor_id == actor_id)
                .where(actor_owners.c.user_id == user_id)
            )

    def list_owners_for_actor(self, *, actor_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(users.c.id, users.c.name)
                    .select_from(actor_owners.join(users, users.c.id == actor_owners.c.user_id))
                    .where(actor_owners.c.actor_id == actor_id)
                    .order_by(users.c.name.asc())
                )
            )
        return rows

    def list_owners_for_campaign_actors(self, *, campaign_id: str) -> dict[str, list[dict]]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(
                        actor_owners.c.actor_id,
                        users.c.id.label("user_id"),
                        users.c.name.label("user_name"),
                    )
                    .select_from(
                        actor_owners
                        .join(users, users.c.id == actor_owners.c.user_id)
                        .join(actors_core, actors_core.c.id == actor_owners.c.actor_id)
                    )
                    .where(actors_core.c.campaign_id == campaign_id)
                    .order_by(users.c.name.asc())
                )
            )

        owners_by_actor: dict[str, list[dict]] = {}
        for row in rows:
            owners_by_actor.setdefault(row["actor_id"], []).append(
                {"id": row["user_id"], "name": row["user_name"]}
            )
        return owners_by_actor

    def soft_delete(self, *, actor_id: str) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(actors_core)
                .where(actors_core.c.id == actor_id)
                .values(status="deleted", updated_at=now)
            )

    @staticmethod
    def _insert_owner_ignore(conn, *, actor_id: str, user_id: str) -> None:                
        values = {"actor_id": actor_id, "user_id": user_id}
        conn.execute(
            upsert_statement(
                dialect_name=conn.dialect.name,
                table=actor_owners,
                values=values,
                index_elements=["actor_id", "user_id"],
                set_={"actor_id": actor_id},
            )
        )
