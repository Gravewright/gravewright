from __future__ import annotations

import time
import uuid

from sqlalchemy import delete, select

from app.persistence.database import engine_begin, engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import package_settings

# NULL scopes are persisted as '' so the unique constraint is portable.
_NULL = ""


def _norm(value: str | None) -> str:
    return value if value else _NULL


class PackageSettingRepository:
    """Scoped setting values for SDK packages (global / campaign / user)."""

    def list_all(self) -> list[dict]:
        """Every stored setting value (operator audits / `grave doctor`)."""
        with engine_connect() as connection:
            rows = connection.execute(select(package_settings)).mappings().all()
        return [dict(row) for row in rows]

    def list_for_package(self, package_id: str) -> list[dict]:
        with engine_connect() as connection:
            rows = (
                connection.execute(
                    select(package_settings).where(package_settings.c.package_id == package_id)
                )
                .mappings()
                .all()
            )
        return [dict(row) for row in rows]

    def get(
        self,
        *,
        package_id: str,
        setting_key: str,
        campaign_id: str | None,
        user_id: str | None,
    ) -> dict | None:
        with engine_connect() as connection:
            row = (
                connection.execute(
                    select(package_settings)
                    .where(
                        package_settings.c.package_id == package_id,
                        package_settings.c.campaign_id == _norm(campaign_id),
                        package_settings.c.user_id == _norm(user_id),
                        package_settings.c.setting_key == setting_key,
                    )
                    .limit(1)
                )
                .mappings()
                .first()
            )
        return dict(row) if row is not None else None

    def set(
        self,
        *,
        package_id: str,
        setting_key: str,
        value_json: str,
        campaign_id: str | None,
        user_id: str | None,
    ) -> None:
        now = int(time.time())
        values = {
            "id": uuid.uuid4().hex,
            "package_id": package_id,
            "campaign_id": _norm(campaign_id),
            "user_id": _norm(user_id),
            "setting_key": setting_key,
            "value_json": value_json,
            "created_at": now,
            "updated_at": now,
        }
        with engine_begin() as connection:
            connection.execute(
                upsert_statement(
                    dialect_name=connection.dialect.name,
                    table=package_settings,
                    values=values,
                    index_elements=[
                        package_settings.c.package_id,
                        package_settings.c.campaign_id,
                        package_settings.c.user_id,
                        package_settings.c.setting_key,
                    ],
                    set_={"value_json": value_json, "updated_at": now},
                )
            )

    def delete_for_package(self, *, package_id: str) -> None:
        with engine_begin() as connection:
            connection.execute(
                delete(package_settings).where(package_settings.c.package_id == package_id)
            )
