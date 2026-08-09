from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select

from app.persistence.database import engine_connect
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.handout_grant_repository import HandoutGrantRepository
from app.persistence.tables import campaign_members, items_core, journals, library_assets

RESOURCE_TABLES = {"journal": journals, "item": items_core, "asset": library_assets}
SUBJECT_TYPES = {"everyone", "user", "role"}
TARGET_ROLES = {"assistant_gm", "player", "streamer"}


@dataclass(frozen=True)
class HandoutResult:
    success: bool
    grant: dict | None = None
    grants: list[dict] = field(default_factory=list)
    error_key: str | None = None


class HandoutService:
    def __init__(self) -> None:
        self.campaigns = CampaignRepository()
        self.grants = HandoutGrantRepository()

    def grant(self, *, campaign_id: str, user_id: str, resource_type: str,
              resource_id: str, subject_type: str, subject_id: str = "") -> HandoutResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return HandoutResult(False, error_key="handout.errors.denied")
        if not self._resource_exists(campaign_id, resource_type, resource_id):
            return HandoutResult(False, error_key="handout.errors.not_found")
        normalized_subject = subject_id.strip()
        if subject_type not in SUBJECT_TYPES:
            return HandoutResult(False, error_key="handout.errors.invalid_subject")
        if subject_type == "everyone":
            normalized_subject = ""
        elif subject_type == "role":
            if normalized_subject not in TARGET_ROLES:
                return HandoutResult(False, error_key="handout.errors.invalid_subject")
        elif not self._is_member(campaign_id, normalized_subject):
            return HandoutResult(False, error_key="handout.errors.invalid_subject")
        row = self.grants.grant(
            campaign_id=campaign_id, resource_type=resource_type, resource_id=resource_id,
            subject_type=subject_type, subject_id=normalized_subject,
            created_by_user_id=user_id,
        )
        return HandoutResult(True, grant=row)

    def prepare_presentation(self, *, campaign_id: str, user_id: str, resource_type: str,
                             resource_id: str, subject_type: str,
                             subject_id: str = "") -> HandoutResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return HandoutResult(False, error_key="handout.errors.denied")
        if not self._resource_exists(campaign_id, resource_type, resource_id):
            return HandoutResult(False, error_key="handout.errors.not_found")
        normalized_subject = subject_id.strip()
        if subject_type == "everyone":
            normalized_subject = ""
        elif subject_type == "role" and normalized_subject not in TARGET_ROLES:
            return HandoutResult(False, error_key="handout.errors.invalid_subject")
        elif subject_type == "user" and not self._is_member(campaign_id, normalized_subject):
            return HandoutResult(False, error_key="handout.errors.invalid_subject")
        elif subject_type not in SUBJECT_TYPES:
            return HandoutResult(False, error_key="handout.errors.invalid_subject")
        return HandoutResult(True, grant={
            "campaign_id": campaign_id, "resource_type": resource_type,
            "resource_id": resource_id, "subject_type": subject_type,
            "subject_id": normalized_subject, "created_by_user_id": user_id,
        })

    def revoke(self, *, campaign_id: str, user_id: str, grant_id: str) -> HandoutResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return HandoutResult(False, error_key="handout.errors.denied")
        row = self.grants.revoke(grant_id=grant_id, campaign_id=campaign_id)
        return HandoutResult(row is not None, grant=row, error_key=None if row else "handout.errors.not_found")

    def list(self, *, campaign_id: str, user_id: str, resource_type: str, resource_id: str) -> HandoutResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return HandoutResult(False, error_key="handout.errors.denied")
        return HandoutResult(True, grants=self.grants.list_active(
            campaign_id=campaign_id, resource_type=resource_type, resource_id=resource_id
        ))

    def can_view(self, *, campaign_id: str, user_id: str, resource_type: str, resource_id: str) -> bool:
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if role is None:
            return False
        if role == "gm":
            return True
        return self.grants.can_view(
            campaign_id=campaign_id, resource_type=resource_type, resource_id=resource_id,
            user_id=user_id, role=role,
        )

    def list_received(self, *, campaign_id: str, user_id: str) -> HandoutResult:
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if role is None:
            return HandoutResult(False, error_key="handout.errors.denied")
        rows = self.grants.list_accessible(campaign_id=campaign_id, user_id=user_id, role=role)
        resources = []
        seen = set()
        with engine_connect() as connection:
            for grant in rows:
                key = (grant["resource_type"], grant["resource_id"])
                if key in seen:
                    continue
                table = RESOURCE_TABLES.get(grant["resource_type"])
                if table is None:
                    continue
                title_column = table.c.filename if grant["resource_type"] == "asset" else (
                    table.c.title if grant["resource_type"] == "journal" else table.c.name
                )
                found = connection.execute(select(title_column).where(
                    table.c.id == grant["resource_id"], table.c.campaign_id == campaign_id
                )).first()
                if found is None:
                    continue
                seen.add(key)
                resources.append({
                    "resource_type": grant["resource_type"],
                    "resource_id": grant["resource_id"],
                    "title": found[0],
                })
        return HandoutResult(True, grants=resources)

    @staticmethod
    def _resource_exists(campaign_id: str, resource_type: str, resource_id: str) -> bool:
        table = RESOURCE_TABLES.get(resource_type)
        if table is None:
            return False
        with engine_connect() as connection:
            return connection.execute(select(table.c.id).where(
                table.c.id == resource_id, table.c.campaign_id == campaign_id
            )).first() is not None

    @staticmethod
    def _is_member(campaign_id: str, user_id: str) -> bool:
        if not user_id:
            return False
        with engine_connect() as connection:
            return connection.execute(select(campaign_members.c.user_id).where(
                campaign_members.c.campaign_id == campaign_id,
                campaign_members.c.user_id == user_id,
            )).first() is not None
