from __future__ import annotations

import time
import uuid

from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.engine import Connection

from app.domain.roles import PlayerRole
from app.domain.roles import SystemRole
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import campaign_members as members_table
from app.persistence.tables import streamer_links as links_table
from app.persistence.tables import users as users_table


                                                                           
                                                                
_GUEST_PASSWORD_MARKER = "!streamer-guest-no-login"


class StreamerLinkRepository:
    """Bearer streamer links and the read-only guest principals they mint."""

    def create_active(
        self,
        *,
        campaign_id: str,
        token: str,
        created_by_user_id: str,
        expires_at: int,
    ) -> dict:
        """Revoke any existing active link for the campaign, then mint a new one.

        Only one active link exists per campaign at a time; regenerating revokes
        the previous link (and orphans its guest member, removed on revoke).
        """
        now = int(time.time())
        link_id = uuid.uuid4().hex
        with engine_begin() as conn:
            self._revoke_active(conn, campaign_id=campaign_id, now=now)
            conn.execute(
                insert(links_table).values(
                    id=link_id,
                    campaign_id=campaign_id,
                    token=token,
                    guest_user_id=None,
                    created_by_user_id=created_by_user_id,
                    created_at=now,
                    expires_at=expires_at,
                    revoked_at=None,
                )
            )
            return one_or_none(
                conn.execute(select(links_table).where(links_table.c.id == link_id).limit(1))
            )

    def get_active_for_campaign(self, *, campaign_id: str, now: int | None = None) -> dict | None:
        timestamp = int(time.time()) if now is None else now
        with engine_connect() as conn:
            return one_or_none(
                conn.execute(
                    select(links_table)
                    .where(links_table.c.campaign_id == campaign_id)
                    .where(links_table.c.revoked_at.is_(None))
                    .where(links_table.c.expires_at > timestamp)
                    .order_by(links_table.c.created_at.desc())
                    .limit(1)
                )
            )

    def revoke_active_for_campaign(self, *, campaign_id: str) -> int:
        now = int(time.time())
        with engine_begin() as conn:
            return self._revoke_active(conn, campaign_id=campaign_id, now=now)

    def consume_token(self, *, token: str, now: int | None = None) -> dict | None:
        """Resolve a bearer token to a read-only guest session.

        Returns ``{"campaign_id", "guest_user_id"}`` for a valid (non-revoked,
        non-expired) link, minting the guest ``users`` row and the
        ``streamer`` ``campaign_members`` row on first use. Returns ``None`` for
        an unknown, revoked or expired token.
        """
        timestamp = int(time.time()) if now is None else now
        with engine_begin() as conn:
            link = one_or_none(
                conn.execute(
                    select(links_table)
                    .where(links_table.c.token == token)
                    .where(links_table.c.revoked_at.is_(None))
                    .where(links_table.c.expires_at > timestamp)
                    .limit(1)
                )
            )
            if link is None:
                return None

            campaign_id = link["campaign_id"]
            guest_user_id = link["guest_user_id"]

                                                                                 
                                                      
            if guest_user_id is not None and self._guest_is_valid(
                conn, campaign_id=campaign_id, guest_user_id=guest_user_id
            ):
                return {"campaign_id": campaign_id, "guest_user_id": guest_user_id}

            guest_user_id = self._mint_guest(
                conn, link_id=link["id"], campaign_id=campaign_id, now=timestamp
            )
            return {"campaign_id": campaign_id, "guest_user_id": guest_user_id}

                                                                        
               
                                                                        

    def _revoke_active(self, conn: Connection, *, campaign_id: str, now: int) -> int:
        """Revoke active links and remove their orphaned guest members/users."""
        active = conn.execute(
            select(links_table.c.guest_user_id)
            .where(links_table.c.campaign_id == campaign_id)
            .where(links_table.c.revoked_at.is_(None))
        ).all()
        result = conn.execute(
            update(links_table)
            .where(links_table.c.campaign_id == campaign_id)
            .where(links_table.c.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        for (guest_user_id,) in active:
            if guest_user_id is not None:
                                                                                 
                                                                                 
                conn.execute(users_table.delete().where(users_table.c.id == guest_user_id))
        return int(result.rowcount or 0)

    def _guest_is_valid(self, conn: Connection, *, campaign_id: str, guest_user_id: str) -> bool:
        member = one_or_none(
            conn.execute(
                select(members_table.c.id)
                .where(members_table.c.campaign_id == campaign_id)
                .where(members_table.c.user_id == guest_user_id)
                .where(members_table.c.role == PlayerRole.STREAMER.value)
                .limit(1)
            )
        )
        return member is not None

    def _mint_guest(self, conn: Connection, *, link_id: str, campaign_id: str, now: int) -> str:
        guest_user_id = uuid.uuid4().hex
        conn.execute(
            insert(users_table).values(
                id=guest_user_id,
                name="Streamer",
                email=f"streamer-{guest_user_id}@streamer.guest",
                password_hash=_GUEST_PASSWORD_MARKER,
                system_role=SystemRole.USER.value,
                created_at=now,
                updated_at=now,
            )
        )
        conn.execute(
            insert(members_table).values(
                id=uuid.uuid4().hex,
                campaign_id=campaign_id,
                user_id=guest_user_id,
                role=PlayerRole.STREAMER.value,
                created_at=now,
                updated_at=now,
            )
        )
        conn.execute(
            update(links_table)
            .where(links_table.c.id == link_id)
            .values(guest_user_id=guest_user_id)
        )
        return guest_user_id
