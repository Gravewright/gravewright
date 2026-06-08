from __future__ import annotations

import json
import time
import uuid

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update

from app.domain.roles import PlayerRole
from app.engine.state.state_manager import create_state_pair
from app.helpers.codes import hash_removal_code
from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import campaign_delete_codes
from app.persistence.tables import campaign_members
from app.persistence.tables import campaign_system_history
from app.persistence.tables import campaigns as campaigns_table
from app.persistence.tables import module_settings
from app.persistence.tables import users


class CampaignRepository:
    """Campaign persistence implemented with SQLAlchemy Core."""

    def list_for_user(self, user_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(campaigns_table, campaign_members.c.role.label("member_role"))
                    .select_from(
                        campaigns_table.join(
                            campaign_members,
                            campaign_members.c.campaign_id == campaigns_table.c.id,
                        )
                    )
                    .where(campaign_members.c.user_id == user_id)
                    .order_by(campaigns_table.c.updated_at.desc())
                )
            )

    def list_members_for_user_campaigns(self, user_id: str) -> list[dict]:
        user_campaigns = select(campaign_members.c.campaign_id).where(
            campaign_members.c.user_id == user_id
        )
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(
                        campaign_members.c.campaign_id,
                        campaign_members.c.role,
                        users.c.id.label("user_id"),
                        users.c.name,
                        users.c.email,
                    )
                    .select_from(campaign_members.join(users, users.c.id == campaign_members.c.user_id))
                    .where(campaign_members.c.campaign_id.in_(user_campaigns))
                    .order_by(users.c.name.asc())
                )
            )

    def list_members(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(
                        campaign_members.c.user_id,
                        campaign_members.c.role,
                        users.c.name,
                    )
                    .select_from(campaign_members.join(users, users.c.id == campaign_members.c.user_id))
                    .where(campaign_members.c.campaign_id == campaign_id)
                    .order_by(users.c.name.asc())
                )
            )

    def list_member_user_ids(self, *, campaign_id: str) -> list[str]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(campaign_members.c.user_id)
                    .where(campaign_members.c.campaign_id == campaign_id)
                    .order_by(campaign_members.c.created_at.asc())
                )
            )
        return [row["user_id"] for row in rows]

    def get_member(
        self,
        *,
        campaign_id: str,
        user_id: str,
    ) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(
                conn.execute(
                    select(
                        campaign_members.c.campaign_id,
                        campaign_members.c.user_id,
                        campaign_members.c.role,
                        users.c.name,
                        users.c.email,
                    )
                    .select_from(campaign_members.join(users, users.c.id == campaign_members.c.user_id))
                    .where(campaign_members.c.campaign_id == campaign_id)
                    .where(campaign_members.c.user_id == user_id)
                    .limit(1)
                )
            )

    def get_for_user(
        self,
        *,
        campaign_id: str,
        user_id: str,
    ) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(
                conn.execute(
                    select(campaigns_table, campaign_members.c.role.label("member_role"))
                    .select_from(
                        campaigns_table.join(
                            campaign_members,
                            campaign_members.c.campaign_id == campaigns_table.c.id,
                        )
                    )
                    .where(campaigns_table.c.id == campaign_id)
                    .where(campaign_members.c.user_id == user_id)
                    .limit(1)
                )
            )

    def get_member_role(
        self,
        *,
        campaign_id: str,
        user_id: str,
    ) -> str | None:
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(campaign_members.c.role)
                    .where(campaign_members.c.campaign_id == campaign_id)
                    .where(campaign_members.c.user_id == user_id)
                    .limit(1)
                )
            )
        return None if row is None else str(row["role"])

    def update_measure_flash_seconds(self, *, campaign_id: str, seconds: int) -> bool:
        now = int(time.time())
        normalized_seconds = max(1, min(60, int(seconds)))

        with engine_begin() as conn:
            row = one_or_none(
                conn.execute(
                    select(campaigns_table.c.persistent_state_json)
                    .where(campaigns_table.c.id == campaign_id)
                    .limit(1)
                )
            )
            if row is None:
                return False

            try:
                state = json.loads(row["persistent_state_json"] or "{}")
            except Exception:
                state = {}
            if not isinstance(state, dict):
                state = {}
            table_settings = state.get("table_settings")
            if not isinstance(table_settings, dict):
                table_settings = {}
            table_settings["measure_flash_seconds"] = normalized_seconds
            state["table_settings"] = table_settings

            conn.execute(
                update(campaigns_table)
                .where(campaigns_table.c.id == campaign_id)
                .values(
                    persistent_state_json=json.dumps(state, separators=(",", ":")),
                    state_version=campaigns_table.c.state_version + 1,
                    updated_at=now,
                )
            )
            return True

    def create(
        self,
        *,
        owner_user_id: str,
        title: str,
        description: str,
    ) -> dict:
        now = int(time.time())
        campaign_id = uuid.uuid4().hex
        member_id = uuid.uuid4().hex

        initial_state = {
            "entity": "campaign",
            "title": title,
            "description": description,
            "active_system_id": None,
            "created_by_user_id": owner_user_id,
            "state_reason": "created",
        }

        initial_state_json, persistent_state_json = create_state_pair(initial_state)

        with engine_begin() as conn:
            conn.execute(
                insert(campaigns_table).values(
                    id=campaign_id,
                    owner_user_id=owner_user_id,
                    title=title,
                    description=description,
                    active_system_id=None,
                    initial_state_json=initial_state_json,
                    persistent_state_json=persistent_state_json,
                    state_version=1,
                    created_at=now,
                    updated_at=now,
                )
            )
            conn.execute(
                insert(campaign_members).values(
                    id=member_id,
                    campaign_id=campaign_id,
                    user_id=owner_user_id,
                    role=PlayerRole.GM.value,
                    created_at=now,
                    updated_at=now,
                )
            )
            row = self._get_for_user(conn, campaign_id=campaign_id, user_id=owner_user_id)

        if row is None:
            raise RuntimeError("Created campaign could not be read back.")
        return row

    def update_details(
        self,
        *,
        campaign_id: str,
        title: str,
        description: str,
    ) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(campaigns_table)
                .where(campaigns_table.c.id == campaign_id)
                .values(
                    title=title,
                    description=description,
                    state_version=campaigns_table.c.state_version + 1,
                    updated_at=now,
                )
            )

    def create_delete_code(
        self,
        *,
        campaign_id: str,
        requested_by_user_id: str,
        code: str,
        ttl_seconds: int,
    ) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(campaign_delete_codes)
                .where(campaign_delete_codes.c.campaign_id == campaign_id)
                .where(campaign_delete_codes.c.requested_by_user_id == requested_by_user_id)
                .where(campaign_delete_codes.c.used_at.is_(None))
                .values(used_at=now)
            )
            conn.execute(
                insert(campaign_delete_codes).values(
                    id=uuid.uuid4().hex,
                    campaign_id=campaign_id,
                    requested_by_user_id=requested_by_user_id,
                    code_hash=hash_removal_code(code),
                    created_at=now,
                    expires_at=now + ttl_seconds,
                    used_at=None,
                )
            )

    def has_valid_delete_code(
        self,
        *,
        campaign_id: str,
        requested_by_user_id: str,
        code: str,
    ) -> bool:
        now = int(time.time())
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(campaign_delete_codes.c.id)
                    .where(campaign_delete_codes.c.campaign_id == campaign_id)
                    .where(campaign_delete_codes.c.requested_by_user_id == requested_by_user_id)
                    .where(campaign_delete_codes.c.code_hash == hash_removal_code(code))
                    .where(campaign_delete_codes.c.used_at.is_(None))
                    .where(campaign_delete_codes.c.expires_at > now)
                    .limit(1)
                )
            )
        return row is not None

    def delete(
        self,
        *,
        campaign_id: str,
    ) -> None:
        with engine_begin() as conn:
            conn.execute(
                delete(module_settings)
                .where(module_settings.c.scope == "campaign")
                .where(module_settings.c.subject_id == campaign_id)
            )
            conn.execute(delete(campaigns_table).where(campaigns_table.c.id == campaign_id))

    def remove_member(
        self,
        *,
        campaign_id: str,
        user_id: str,
    ) -> None:
        with engine_begin() as conn:
            conn.execute(
                delete(campaign_members)
                .where(campaign_members.c.campaign_id == campaign_id)
                .where(campaign_members.c.user_id == user_id)
            )

    def update_system(
        self,
        *,
        campaign_id: str,
        changed_by_user_id: str,
        next_system_id: str | None,
    ) -> dict:
        now = int(time.time())
        history_id = uuid.uuid4().hex

        with engine_begin() as conn:
            campaign = one_or_none(
                conn.execute(select(campaigns_table).where(campaigns_table.c.id == campaign_id).limit(1))
            )
            if campaign is None:
                raise ValueError("Campaign not found.")

            previous_system_id = campaign["active_system_id"]
            conn.execute(
                update(campaigns_table)
                .where(campaigns_table.c.id == campaign_id)
                .values(
                    active_system_id=next_system_id,
                    state_version=campaigns_table.c.state_version + 1,
                    updated_at=now,
                )
            )
            conn.execute(
                insert(campaign_system_history).values(
                    id=history_id,
                    campaign_id=campaign_id,
                    previous_system_id=previous_system_id,
                    next_system_id=next_system_id,
                    changed_by_user_id=changed_by_user_id,
                    created_at=now,
                )
            )
            row = one_or_none(
                conn.execute(select(campaigns_table).where(campaigns_table.c.id == campaign_id).limit(1))
            )

        if row is None:
            raise RuntimeError("Updated campaign could not be read back.")
        return row

    @staticmethod
    def _get_for_user(conn, *, campaign_id: str, user_id: str) -> dict | None:                
        return one_or_none(
            conn.execute(
                select(campaigns_table, campaign_members.c.role.label("member_role"))
                .select_from(
                    campaigns_table.join(
                        campaign_members,
                        campaign_members.c.campaign_id == campaigns_table.c.id,
                    )
                )
                .where(campaigns_table.c.id == campaign_id)
                .where(campaign_members.c.user_id == user_id)
                .limit(1)
            )
        )
