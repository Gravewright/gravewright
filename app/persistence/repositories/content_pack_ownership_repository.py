"""Quem alcança cada pack de compêndio, por papel."""
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
from app.persistence.tables import content_pack_ownership as table


class ContentPackOwnershipRepository:
    def list_for_campaign(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(select(table).where(table.c.campaign_id == campaign_id))
            )

    def get(self, *, campaign_id: str, package_id: str, pack_id: str, role: str) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(
                conn.execute(
                    select(table)
                    .where(
                        table.c.campaign_id == campaign_id,
                        table.c.package_id == package_id,
                        table.c.pack_id == pack_id,
                        table.c.role == role,
                    )
                    .limit(1)
                )
            )

    def set_level(
        self, *, campaign_id: str, package_id: str, pack_id: str, role: str, level: str
    ) -> None:
        """Grava o nível; "none" apaga a linha em vez de guardar o padrão.

        Ausência de linha já significa "none", então persistir o padrão só criaria
        lixo que cresce a cada pack que o mestre abriu e fechou de novo.
        """
        now = int(time.time())
        existing = self.get(
            campaign_id=campaign_id, package_id=package_id, pack_id=pack_id, role=role
        )
        with engine_begin() as conn:
            if level == "none":
                if existing is not None:
                    conn.execute(delete(table).where(table.c.id == existing["id"]))
                return
            if existing is None:
                conn.execute(
                    insert(table).values(
                        id=uuid.uuid4().hex,
                        campaign_id=campaign_id,
                        package_id=package_id,
                        pack_id=pack_id,
                        role=role,
                        level=level,
                        created_at=now,
                        updated_at=now,
                    )
                )
                return
            conn.execute(
                update(table)
                .where(table.c.id == existing["id"])
                .values(level=level, updated_at=now)
            )
