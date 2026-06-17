from __future__ import annotations

import time
import uuid

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select

from app.domain.permissions.permissions import PermissionEffect
from app.domain.permissions.permissions import PermissionSubjectType
from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.tables import campaign_permission_overrides as overrides_table


class CampaignPermissionRepository:
    def list_subject_effects(
        self,
        *,
        campaign_id: str,
        subject_type: PermissionSubjectType,
        subject_id: str,
    ) -> dict[str, PermissionEffect]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(overrides_table.c.permission_key, overrides_table.c.effect)
                    .where(overrides_table.c.campaign_id == campaign_id)
                    .where(overrides_table.c.subject_type == subject_type.value)
                    .where(overrides_table.c.subject_id == subject_id)
                )
            )
        return {row["permission_key"]: PermissionEffect(row["effect"]) for row in rows}

    def list_all_role_effects_for_campaign(self, *, campaign_id: str) -> dict[str, dict[str, PermissionEffect]]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(overrides_table.c.subject_id, overrides_table.c.permission_key, overrides_table.c.effect)
                    .where(overrides_table.c.campaign_id == campaign_id)
                    .where(overrides_table.c.subject_type == PermissionSubjectType.ROLE.value)
                )
            )
        result: dict[str, dict[str, PermissionEffect]] = {}
        for row in rows:
            result.setdefault(row["subject_id"], {})[row["permission_key"]] = PermissionEffect(row["effect"])
        return result

    def list_campaign_overrides(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(overrides_table)
                    .where(overrides_table.c.campaign_id == campaign_id)
                    .order_by(
                        overrides_table.c.subject_type.asc(),
                        overrides_table.c.subject_id.asc(),
                        overrides_table.c.permission_key.asc(),
                    )
                )
            )

    def replace_subject_effects(
        self,
        *,
        campaign_id: str,
        subject_type: PermissionSubjectType,
        subject_id: str,
        effects: dict[str, PermissionEffect],
    ) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                delete(overrides_table)
                .where(overrides_table.c.campaign_id == campaign_id)
                .where(overrides_table.c.subject_type == subject_type.value)
                .where(overrides_table.c.subject_id == subject_id)
            )
            rows = [
                {
                    "id": uuid.uuid4().hex,
                    "campaign_id": campaign_id,
                    "subject_type": subject_type.value,
                    "subject_id": subject_id,
                    "permission_key": permission_key,
                    "effect": effect.value,
                    "created_at": now,
                    "updated_at": now,
                }
                for permission_key, effect in sorted(effects.items())
            ]
            if rows:
                conn.execute(insert(overrides_table), rows)
