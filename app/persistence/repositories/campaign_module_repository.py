from __future__ import annotations

import time
import uuid

from sqlalchemy import delete
from sqlalchemy import select

from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import campaign_modules
from app.persistence.tables import modules_installed


class CampaignModuleRepository:
    def enable(self, *, campaign_id: str, module_id: str, enabled_by_user_id: str | None) -> None:
        now = int(time.time())
        values = {
            "id": uuid.uuid4().hex,
            "campaign_id": campaign_id,
            "module_id": module_id,
            "enabled_by_user_id": enabled_by_user_id,
            "created_at": now,
            "updated_at": now,
        }
        with engine_begin() as connection:
            connection.execute(
                upsert_statement(
                    dialect_name=connection.dialect.name,
                    table=campaign_modules,
                    values=values,
                    index_elements=[campaign_modules.c.campaign_id, campaign_modules.c.module_id],
                    set_={
                        "enabled_by_user_id": enabled_by_user_id,
                        "updated_at": now,
                    },
                )
            )

    def disable(self, *, campaign_id: str, module_id: str) -> None:
        with engine_begin() as connection:
            connection.execute(
                delete(campaign_modules)
                .where(campaign_modules.c.campaign_id == campaign_id)
                .where(campaign_modules.c.module_id == module_id)
            )

    def is_enabled(self, *, campaign_id: str, module_id: str) -> bool:
        with engine_connect() as connection:
            row = connection.execute(
                select(campaign_modules.c.id)
                .where(campaign_modules.c.campaign_id == campaign_id)
                .where(campaign_modules.c.module_id == module_id)
                .limit(1)
            ).first()
        return row is not None

    def list_enabled_module_ids(self, *, campaign_id: str) -> list[str]:
        with engine_connect() as connection:
            rows = connection.execute(
                select(campaign_modules.c.module_id)
                .where(campaign_modules.c.campaign_id == campaign_id)
                .order_by(campaign_modules.c.module_id.asc())
            ).all()
        return [str(row[0]) for row in rows]

    def list_enabled_records_for_campaign(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as connection:
            rows = (
                connection.execute(
                    select(modules_installed)
                    .join(campaign_modules, campaign_modules.c.module_id == modules_installed.c.id)
                    .where(campaign_modules.c.campaign_id == campaign_id)
                    .where(modules_installed.c.status == "enabled")
                    .order_by(modules_installed.c.name.asc())
                )
                .mappings()
                .all()
            )
        return [dict(row) for row in rows]

    def enabled_campaign_ids_by_module(self, *, campaign_ids: list[str]) -> dict[str, set[str]]:
        if not campaign_ids:
            return {}
        with engine_connect() as connection:
            rows = connection.execute(
                select(campaign_modules.c.module_id, campaign_modules.c.campaign_id)
                .where(campaign_modules.c.campaign_id.in_(campaign_ids))
            ).all()
        out: dict[str, set[str]] = {}
        for module_id, campaign_id in rows:
            out.setdefault(str(module_id), set()).add(str(campaign_id))
        return out


    def list_campaign_ids_for_module(self, *, module_id: str) -> list[str]:
        with engine_connect() as connection:
            rows = connection.execute(
                select(campaign_modules.c.campaign_id)
                .where(campaign_modules.c.module_id == module_id)
                .order_by(campaign_modules.c.campaign_id.asc())
            ).all()
        return [str(row[0]) for row in rows]

    def has_campaigns_for_module(self, *, module_id: str) -> bool:
        with engine_connect() as connection:
            row = (
                connection.execute(
                    select(campaign_modules.c.id)
                    .where(campaign_modules.c.module_id == module_id)
                    .limit(1)
                )
                .first()
            )
        return row is not None

    def delete_for_module(self, *, module_id: str) -> None:
        with engine_begin() as connection:
            connection.execute(delete(campaign_modules).where(campaign_modules.c.module_id == module_id))
