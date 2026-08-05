from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.domain.roles import PlayerRole
from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import campaign_invitations as invitations_table
from app.persistence.tables import campaign_members as members_table
from app.persistence.tables import campaigns as campaigns_table
from app.persistence.tables import users as users_table


@dataclass(frozen=True)
class AcceptInvitationOutcome:
    """Result of accepting an invitation.

    ``membership_created`` is True only when *this* call inserted the membership
    row, so the caller can publish the realtime join event at most once and only
    for a real creation.
    """

    # "accepted" | "not_found" | "not_pending" | "membership_removed"
    status: str
    membership_created: bool = False


class CampaignInvitationRepository:
    def list_pending_for_user(self, user_id: str) -> list[dict]:
        inviter = users_table.alias("inviter")
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(
                        invitations_table.c.id,
                        invitations_table.c.campaign_id,
                        invitations_table.c.role,
                        invitations_table.c.status,
                        invitations_table.c.created_at,
                        campaigns_table.c.title.label("campaign_title"),
                        campaigns_table.c.description.label("campaign_description"),
                        inviter.c.name.label("invited_by_name"),
                    )
                    .select_from(
                        invitations_table
                        .join(campaigns_table, campaigns_table.c.id == invitations_table.c.campaign_id)
                        .join(inviter, inviter.c.id == invitations_table.c.invited_by_user_id)
                    )
                    .where(invitations_table.c.invited_user_id == user_id)
                    .where(invitations_table.c.status == "pending")
                    .order_by(invitations_table.c.created_at.desc())
                )
            )

    def create_pending(
        self,
        *,
        campaign_id: str,
        invited_email: str,
        invited_by_user_id: str,
        role: PlayerRole,
    ) -> str:
        now = int(time.time())
        normalized_email = invited_email.strip().lower()
        with engine_begin() as conn:
            invited_user = one_or_none(
                conn.execute(
                    select(users_table.c.id)
                    .where(func.lower(users_table.c.email) == normalized_email)
                    .limit(1)
                )
            )
            if invited_user is None:
                return "user_not_found"
            invited_user_id = invited_user["id"]
            existing_member = one_or_none(
                conn.execute(
                    select(members_table.c.id)
                    .where(members_table.c.campaign_id == campaign_id)
                    .where(members_table.c.user_id == invited_user_id)
                    .limit(1)
                )
            )
            if existing_member is not None:
                return "already_member"
            existing_pending = one_or_none(
                conn.execute(
                    select(invitations_table.c.id)
                    .where(invitations_table.c.campaign_id == campaign_id)
                    .where(invitations_table.c.invited_user_id == invited_user_id)
                    .where(invitations_table.c.status == "pending")
                    .limit(1)
                )
            )
            if existing_pending is not None:
                return "already_pending"
            conn.execute(
                insert(invitations_table).values(
                    id=uuid.uuid4().hex,
                    campaign_id=campaign_id,
                    invited_user_id=invited_user_id,
                    invited_by_user_id=invited_by_user_id,
                    role=role.value,
                    status="pending",
                    created_at=now,
                    updated_at=now,
                    responded_at=None,
                )
            )
            return "created"

    def accept_for_user(self, *, invitation_id: str, user_id: str) -> AcceptInvitationOutcome:
        """Accept an invitation idempotently and concurrency-safely.

        Each invitation status is handled explicitly:

        - ``pending``: create the membership and flip the invitation to accepted;
        - ``accepted``: idempotent success *only while the membership still
          exists*. Once an administrator removed or banned the member the
          invitation is spent — it reports ``membership_removed`` and touches
          nothing, so an old invite can never undo a removal or a ban;
        - anything else (``declined``, ``revoked``, …): ``not_pending``.

        Read, membership insert, and status update run in one transaction. The
        membership is inserted with ``ON CONFLICT DO NOTHING`` against the
        ``(campaign_id, user_id)`` unique constraint, so N concurrent accepts for
        the same user create exactly one membership and exactly one of them
        reports ``membership_created=True``; the rest are stable idempotent
        successes. On PostgreSQL the invitation row is locked to serialize
        concurrent accepts; on SQLite the process-wide write lock already does.
        """
        now = int(time.time())
        with engine_begin() as conn:
            invitation_query = (
                select(
                    invitations_table.c.id,
                    invitations_table.c.campaign_id,
                    invitations_table.c.invited_user_id,
                    invitations_table.c.role,
                    invitations_table.c.status,
                )
                .where(invitations_table.c.id == invitation_id)
                .where(invitations_table.c.invited_user_id == user_id)
                .limit(1)
            )
            if conn.dialect.name != "sqlite":
                invitation_query = invitation_query.with_for_update()

            invitation = one_or_none(conn.execute(invitation_query))
            if invitation is None:
                return AcceptInvitationOutcome("not_found")

            status = invitation["status"]
            campaign_id = invitation["campaign_id"]

            if status == "accepted":
                # A concurrent accept may have flipped the row moments ago; the
                # membership it created is what makes this call a success.
                if self._membership_exists(conn, campaign_id=campaign_id, user_id=user_id):
                    return AcceptInvitationOutcome("accepted", membership_created=False)
                return AcceptInvitationOutcome("membership_removed")

            if status != "pending":
                return AcceptInvitationOutcome("not_pending")

            created = self._insert_membership_idempotent(
                conn,
                campaign_id=campaign_id,
                user_id=user_id,
                role=invitation["role"],
                now=now,
            )
            conn.execute(
                update(invitations_table)
                .where(invitations_table.c.id == invitation_id)
                .values(status="accepted", updated_at=now, responded_at=now)
            )
            return AcceptInvitationOutcome("accepted", membership_created=created)

    @staticmethod
    def revoke_pending_for_user(conn, *, campaign_id: str, user_id: str) -> int:
        """Revoke this user's still-pending invitations to a campaign.

        Called when a member is removed or banned so a leftover pending invite
        cannot be used to walk straight back in. Already-answered invitations
        (accepted/declined) are left untouched — they are history, and the accept
        path no longer treats an accepted invite as a membership factory.

        Takes the caller's connection so the revocation commits atomically with
        the removal itself. Returns the number of invitations revoked.
        """
        now = int(time.time())
        result = conn.execute(
            update(invitations_table)
            .where(invitations_table.c.campaign_id == campaign_id)
            .where(invitations_table.c.invited_user_id == user_id)
            .where(invitations_table.c.status == "pending")
            .values(status="revoked", updated_at=now, responded_at=now)
        )
        return int(result.rowcount or 0)

    @staticmethod
    def _membership_exists(conn, *, campaign_id: str, user_id: str) -> bool:
        return (
            one_or_none(
                conn.execute(
                    select(members_table.c.id)
                    .where(members_table.c.campaign_id == campaign_id)
                    .where(members_table.c.user_id == user_id)
                    .limit(1)
                )
            )
            is not None
        )

    @staticmethod
    def _insert_membership_idempotent(
        conn, *, campaign_id: str, user_id: str, role: str, now: int
    ) -> bool:
        """Insert the membership if absent; return True only if this call created it.

        Uses ``INSERT ... ON CONFLICT DO NOTHING`` on SQLite/PostgreSQL so a
        losing concurrent insert is a no-op instead of raising an
        ``IntegrityError``. The unique constraint on ``(campaign_id, user_id)``
        remains the last line of defense.

        Whether *this* call won is decided by re-reading the surviving row and
        comparing its id with the one we generated, not by ``rowcount``: driver
        row counts for a skipped upsert are not uniformly reliable across
        backends, and "who created the membership" is what gates the single
        realtime join event.
        """
        member_id = uuid.uuid4().hex
        values = {
            "id": member_id,
            "campaign_id": campaign_id,
            "user_id": user_id,
            "role": role,
            "created_at": now,
            "updated_at": now,
        }
        dialect = conn.dialect.name
        if dialect in ("sqlite", "postgresql"):
            insert_fn = sqlite_insert if dialect == "sqlite" else postgresql_insert
            conn.execute(
                insert_fn(members_table)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["campaign_id", "user_id"])
            )
        else:
            # Fallback for backends without ON CONFLICT support.
            if CampaignInvitationRepository._membership_exists(
                conn, campaign_id=campaign_id, user_id=user_id
            ):
                return False
            conn.execute(insert(members_table).values(**values))

        surviving = one_or_none(
            conn.execute(
                select(members_table.c.id)
                .where(members_table.c.campaign_id == campaign_id)
                .where(members_table.c.user_id == user_id)
                .limit(1)
            )
        )
        return surviving is not None and surviving["id"] == member_id

    def decline_for_user(self, *, invitation_id: str, user_id: str) -> str:
        now = int(time.time())
        with engine_begin() as conn:
            invitation = one_or_none(
                conn.execute(
                    select(invitations_table.c.id, invitations_table.c.status)
                    .where(invitations_table.c.id == invitation_id)
                    .where(invitations_table.c.invited_user_id == user_id)
                    .limit(1)
                )
            )
            if invitation is None:
                return "not_found"
            if invitation["status"] != "pending":
                return "not_pending"
            conn.execute(
                update(invitations_table)
                .where(invitations_table.c.id == invitation_id)
                .values(status="declined", updated_at=now, responded_at=now)
            )
            return "declined"

    def get_campaign_for_user_invitation(self, *, invitation_id: str, user_id: str) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(
                conn.execute(
                    select(
                        campaigns_table.c.id,
                        campaigns_table.c.title,
                        campaigns_table.c.description,
                        campaigns_table.c.active_system_id,
                        members_table.c.role.label("member_role"),
                    )
                    .select_from(
                        invitations_table
                        .join(campaigns_table, campaigns_table.c.id == invitations_table.c.campaign_id)
                        .join(
                            members_table,
                            (members_table.c.campaign_id == campaigns_table.c.id)
                            & (members_table.c.user_id == invitations_table.c.invited_user_id),
                        )
                    )
                    .where(invitations_table.c.id == invitation_id)
                    .where(invitations_table.c.invited_user_id == user_id)
                    .limit(1)
                )
            )
