from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from sqlalchemy import insert, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.domain.roles import PlayerRole
from app.persistence.database import engine_begin, engine_connect, one_or_none
from app.persistence.tables import (
    campaign_join_code_redemptions,
    campaign_join_codes,
    campaign_members,
    campaigns,
)


@dataclass(frozen=True)
class RedeemJoinCodeOutcome:
    status: str
    campaign_id: str | None = None
    join_code_id: str | None = None
    membership_created: bool = False

    @property
    def success(self) -> bool:
        return self.status in {"redeemed", "already_member"}


class CampaignJoinCodeRepository:
    """Atomic persistence operations for reusable campaign join codes."""

    def rotate_active_code(
        self,
        *,
        campaign_id: str,
        created_by_user_id: str,
        code_hash: str,
        expires_at: int,
        max_uses: int | None,
        now: int | None = None,
    ) -> dict:
        timestamp = int(time.time()) if now is None else now
        code_id = uuid.uuid4().hex
        with engine_begin() as connection:


            campaign_query = select(campaigns.c.id).where(campaigns.c.id == campaign_id)
            if connection.dialect.name != "sqlite":
                campaign_query = campaign_query.with_for_update()
            if one_or_none(connection.execute(campaign_query)) is None:
                raise ValueError("campaign not found")

            connection.execute(
                update(campaign_join_codes)
                .where(campaign_join_codes.c.campaign_id == campaign_id)
                .where(campaign_join_codes.c.revoked_at.is_(None))
                .values(revoked_at=timestamp, updated_at=timestamp)
            )
            connection.execute(
                insert(campaign_join_codes).values(
                    id=code_id,
                    campaign_id=campaign_id,
                    code_hash=code_hash,
                    created_by_user_id=created_by_user_id,
                    role=PlayerRole.PLAYER.value,
                    max_uses=max_uses,
                    use_count=0,
                    expires_at=expires_at,
                    revoked_at=None,
                    last_used_at=None,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )
            row = self._status_row(connection, code_id=code_id)
        if row is None:
            raise RuntimeError("rotated join code could not be read back")
        return row

    def revoke_active_code(self, *, campaign_id: str, now: int | None = None) -> dict | None:
        timestamp = int(time.time()) if now is None else now
        with engine_begin() as connection:
            query = (
                select(campaign_join_codes.c.id)
                .where(campaign_join_codes.c.campaign_id == campaign_id)
                .where(campaign_join_codes.c.revoked_at.is_(None))
                .limit(1)
            )
            if connection.dialect.name != "sqlite":
                query = query.with_for_update()
            active = one_or_none(connection.execute(query))
            if active is None:
                return None
            connection.execute(
                update(campaign_join_codes)
                .where(campaign_join_codes.c.id == active["id"])
                .values(revoked_at=timestamp, updated_at=timestamp)
            )
            return self._status_row(connection, code_id=active["id"])

    def get_status_for_campaign(self, *, campaign_id: str) -> dict | None:
        with engine_connect() as connection:
            active = one_or_none(
                connection.execute(
                    self._status_query()
                    .where(campaign_join_codes.c.campaign_id == campaign_id)
                    .where(campaign_join_codes.c.revoked_at.is_(None))
                    .order_by(campaign_join_codes.c.created_at.desc())
                    .limit(1)
                )
            )
            if active is not None:
                return active
            return one_or_none(
                connection.execute(
                    self._status_query()
                    .where(campaign_join_codes.c.campaign_id == campaign_id)
                    .order_by(
                        campaign_join_codes.c.updated_at.desc(),
                        campaign_join_codes.c.id.desc(),
                    )
                    .limit(1)
                )
            )

    def redeem_for_user(
        self,
        *,
        code_hash: str,
        user_id: str,
        now: int | None = None,
    ) -> RedeemJoinCodeOutcome:
        timestamp = int(time.time()) if now is None else now
        with engine_begin() as connection:
            code_query = (
                select(
                    campaign_join_codes.c.id,
                    campaign_join_codes.c.campaign_id,
                    campaign_join_codes.c.max_uses,
                    campaign_join_codes.c.use_count,
                    campaign_join_codes.c.expires_at,
                    campaign_join_codes.c.revoked_at,
                )
                .where(campaign_join_codes.c.code_hash == code_hash)
                .limit(1)
            )
            if connection.dialect.name != "sqlite":
                code_query = code_query.with_for_update()
            code = one_or_none(connection.execute(code_query))
            if code is None:
                return RedeemJoinCodeOutcome("not_found")

            code_id = code["id"]
            campaign_id = code["campaign_id"]
            base = {"campaign_id": campaign_id, "join_code_id": code_id}
            if code["revoked_at"] is not None:
                return RedeemJoinCodeOutcome("revoked", **base)
            if timestamp >= code["expires_at"]:
                return RedeemJoinCodeOutcome("expired", **base)

            if self._membership_exists(connection, campaign_id=campaign_id, user_id=user_id):
                return RedeemJoinCodeOutcome("already_member", **base)

            max_uses = code["max_uses"]
            if max_uses is not None and code["use_count"] >= max_uses:
                return RedeemJoinCodeOutcome("exhausted", **base)

            membership_created = self._insert_membership(
                connection,
                campaign_id=campaign_id,
                user_id=user_id,
                now=timestamp,
            )
            if not membership_created:
                return RedeemJoinCodeOutcome("already_member", **base)

            self._insert_redemption(
                connection,
                join_code_id=code_id,
                campaign_id=campaign_id,
                user_id=user_id,
                now=timestamp,
            )
            connection.execute(
                update(campaign_join_codes)
                .where(campaign_join_codes.c.id == code_id)
                .values(
                    use_count=campaign_join_codes.c.use_count + 1,
                    last_used_at=timestamp,
                    updated_at=timestamp,
                )
            )
            return RedeemJoinCodeOutcome("redeemed", membership_created=True, **base)

    @staticmethod
    def _membership_exists(connection, *, campaign_id: str, user_id: str) -> bool:
        return (
            one_or_none(
                connection.execute(
                    select(campaign_members.c.id)
                    .where(campaign_members.c.campaign_id == campaign_id)
                    .where(campaign_members.c.user_id == user_id)
                    .limit(1)
                )
            )
            is not None
        )

    @staticmethod
    def _insert_membership(connection, *, campaign_id: str, user_id: str, now: int) -> bool:
        member_id = uuid.uuid4().hex
        values = {
            "id": member_id,
            "campaign_id": campaign_id,
            "user_id": user_id,
            "role": PlayerRole.PLAYER.value,
            "created_at": now,
            "updated_at": now,
        }
        dialect = connection.dialect.name
        if dialect in {"sqlite", "postgresql"}:
            insert_fn = sqlite_insert if dialect == "sqlite" else postgresql_insert
            connection.execute(
                insert_fn(campaign_members)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["campaign_id", "user_id"])
            )
        else:
            if CampaignJoinCodeRepository._membership_exists(
                connection, campaign_id=campaign_id, user_id=user_id
            ):
                return False
            connection.execute(insert(campaign_members).values(**values))
        surviving = one_or_none(
            connection.execute(
                select(campaign_members.c.id)
                .where(campaign_members.c.campaign_id == campaign_id)
                .where(campaign_members.c.user_id == user_id)
                .limit(1)
            )
        )
        return surviving is not None and surviving["id"] == member_id

    @staticmethod
    def _insert_redemption(
        connection, *, join_code_id: str, campaign_id: str, user_id: str, now: int
    ) -> None:
        connection.execute(
            insert(campaign_join_code_redemptions).values(
                id=uuid.uuid4().hex,
                join_code_id=join_code_id,
                campaign_id=campaign_id,
                user_id=user_id,
                redeemed_at=now,
            )
        )

    @staticmethod
    def _status_query():

        return select(
            campaign_join_codes.c.id,
            campaign_join_codes.c.campaign_id,
            campaign_join_codes.c.created_by_user_id,
            campaign_join_codes.c.role,
            campaign_join_codes.c.max_uses,
            campaign_join_codes.c.use_count,
            campaign_join_codes.c.expires_at,
            campaign_join_codes.c.revoked_at,
            campaign_join_codes.c.last_used_at,
            campaign_join_codes.c.created_at,
            campaign_join_codes.c.updated_at,
        )

    @classmethod
    def _status_row(cls, connection, *, code_id: str) -> dict | None:
        return one_or_none(
            connection.execute(cls._status_query().where(campaign_join_codes.c.id == code_id))
        )
