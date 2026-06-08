from __future__ import annotations

import json
import time
import uuid

from sqlalchemy import delete
from sqlalchemy import select

from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import module_settings


class ModuleSettingRepository:
    """Persist values for module-declared settings.

    Settings are keyed by ``module_id`` + ``scope`` + ``subject_id`` +
    ``setting_key``. ``subject_id`` is an empty string for global settings, the
    campaign id for campaign-scoped settings, and the user id for user-scoped
    settings. Using a non-null subject id keeps the unique key portable across
    SQLite/PostgreSQL/MySQL (NULLs in UNIQUE constraints differ by dialect).
    """

    def get_values(self, *, module_id: str, scope: str, subject_id: str = "") -> dict[str, object]:
        with engine_connect() as connection:
            rows = (
                connection.execute(
                    select(module_settings.c.setting_key, module_settings.c.value_json)
                    .where(module_settings.c.module_id == module_id)
                    .where(module_settings.c.scope == scope)
                    .where(module_settings.c.subject_id == (subject_id or ""))
                    .order_by(module_settings.c.setting_key.asc())
                )
                .mappings()
                .all()
            )
        out: dict[str, object] = {}
        for row in rows:
            try:
                out[str(row["setting_key"])] = json.loads(row["value_json"])
            except (TypeError, ValueError):
                continue
        return out

    def get_value(self, *, module_id: str, scope: str, setting_key: str, subject_id: str = "") -> object | None:
        with engine_connect() as connection:
            row = (
                connection.execute(
                    select(module_settings.c.value_json)
                    .where(module_settings.c.module_id == module_id)
                    .where(module_settings.c.scope == scope)
                    .where(module_settings.c.subject_id == (subject_id or ""))
                    .where(module_settings.c.setting_key == setting_key)
                    .limit(1)
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        try:
            return json.loads(row["value_json"])
        except (TypeError, ValueError):
            return None

    def upsert_value(
        self,
        *,
        module_id: str,
        scope: str,
        setting_key: str,
        value: object,
        subject_id: str = "",
        updated_by_user_id: str | None = None,
    ) -> None:
        now = int(time.time())
        values = {
            "id": uuid.uuid4().hex,
            "module_id": module_id,
            "scope": scope,
            "subject_id": subject_id or "",
            "setting_key": setting_key,
            "value_json": json.dumps(value, ensure_ascii=False, separators=(",", ":")),
            "updated_by_user_id": updated_by_user_id,
            "created_at": now,
            "updated_at": now,
        }
        with engine_begin() as connection:
            connection.execute(
                upsert_statement(
                    dialect_name=connection.dialect.name,
                    table=module_settings,
                    values=values,
                    index_elements=[
                        module_settings.c.module_id,
                        module_settings.c.scope,
                        module_settings.c.subject_id,
                        module_settings.c.setting_key,
                    ],
                    set_={
                        "value_json": values["value_json"],
                        "updated_by_user_id": updated_by_user_id,
                        "updated_at": now,
                    },
                )
            )

    def delete_for_module(self, *, module_id: str) -> None:
        with engine_begin() as connection:
            connection.execute(delete(module_settings).where(module_settings.c.module_id == module_id))

    def delete_for_campaign(self, *, campaign_id: str) -> None:
        with engine_begin() as connection:
            connection.execute(
                delete(module_settings)
                .where(module_settings.c.scope == "campaign")
                .where(module_settings.c.subject_id == campaign_id)
            )
