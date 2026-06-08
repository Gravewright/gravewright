from __future__ import annotations

from dataclasses import dataclass

from app.persistence.repositories.actor_permission_repository import ActorPermissionRepository
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.item_permission_repository import ItemPermissionRepository
from app.persistence.repositories.item_repository import ItemRepository
from app.persistence.repositories.journal_permission_repository import JournalPermissionRepository
from app.persistence.repositories.journal_repository import JournalRepository


@dataclass(frozen=True)
class ResourcePermissionPage:
    resource: dict
    campaign: dict
    title: str
    rows: list[dict]


def _access_from_owner_permission(*, is_owner: bool, permission: dict | None) -> str:
    if is_owner:
        return "owner"
    if permission and permission["can_view"]:
        return "read"
    return "none"


class ResourcePermissionPageService:
    def __init__(
        self,
        *,
        actors: ActorRepository | None = None,
        actor_permissions: ActorPermissionRepository | None = None,
        campaigns: CampaignRepository | None = None,
        items: ItemRepository | None = None,
        item_permissions: ItemPermissionRepository | None = None,
        journals: JournalRepository | None = None,
        journal_permissions: JournalPermissionRepository | None = None,
    ) -> None:
        self.actors = actors or ActorRepository()
        self.actor_permissions = actor_permissions or ActorPermissionRepository()
        self.campaigns = campaigns or CampaignRepository()
        self.items = items or ItemRepository()
        self.item_permissions = item_permissions or ItemPermissionRepository()
        self.journals = journals or JournalRepository()
        self.journal_permissions = journal_permissions or JournalPermissionRepository()

    def build_page(
        self,
        *,
        resource_type: str,
        resource_id: str,
        user_id: str,
    ) -> ResourcePermissionPage | None:
        resource, campaign = self.load_resource(
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
        )
        if resource is None or campaign is None or campaign.get("member_role") != "gm":
            return None

        members = [
            dict(member)
            for member in self.campaigns.list_members(campaign_id=resource["campaign_id"])
            if member["role"] != "gm"
        ]
        owners, permissions = self._owners_and_permissions(
            resource_type=resource_type,
            resource_id=resource_id,
        )

        return ResourcePermissionPage(
            resource=resource,
            campaign=campaign,
            title=resource["title"] if resource_type == "journal" else resource["name"],
            rows=[
                {
                    "user_id": member["user_id"],
                    "name": member["name"],
                    "access": _access_from_owner_permission(
                        is_owner=member["user_id"] in owners,
                        permission=permissions.get(member["user_id"]),
                    ),
                }
                for member in members
            ],
        )

    def list_non_gm_members(self, *, campaign_id: str) -> list[dict]:
        return [
            dict(member)
            for member in self.campaigns.list_members(campaign_id=campaign_id)
            if member["role"] != "gm"
        ]

    def load_resource(
        self,
        *,
        resource_type: str,
        resource_id: str,
        user_id: str,
    ) -> tuple[dict | None, dict | None]:
        if resource_type == "journal":
            journal = self.journals.get_by_id(resource_id)
            if journal is None or journal["status"] != "active":
                return None, None
            campaign = self.campaigns.get_for_user(
                campaign_id=journal["campaign_id"],
                user_id=user_id,
            )
            return dict(journal), dict(campaign) if campaign is not None else None

        if resource_type == "actor":
            actor = self.actors.get(resource_id)
            if actor is None or actor["status"] != "active":
                return None, None
            campaign = self.campaigns.get_for_user(
                campaign_id=actor["campaign_id"],
                user_id=user_id,
            )
            return dict(actor), dict(campaign) if campaign is not None else None

        if resource_type == "item":
            item = self.items.get(resource_id)
            if item is None or item["status"] != "active":
                return None, None
            campaign = self.campaigns.get_for_user(
                campaign_id=item["campaign_id"],
                user_id=user_id,
            )
            return dict(item), dict(campaign) if campaign is not None else None

        return None, None

    def _owners_and_permissions(
        self,
        *,
        resource_type: str,
        resource_id: str,
    ) -> tuple[set[str], dict]:
        if resource_type == "actor":
            return (
                {o["id"] for o in self.actors.list_owners_for_actor(actor_id=resource_id)},
                self.actor_permissions.list_for_actor(actor_id=resource_id),
            )
        if resource_type == "item":
            return (
                {o["id"] for o in self.items.list_owners_for_item(item_id=resource_id)},
                self.item_permissions.list_for_item(item_id=resource_id),
            )
        return (
            {o["id"] for o in self.journals.list_owners_for_journal(journal_id=resource_id)},
            self.journal_permissions.list_for_journal(journal_id=resource_id),
        )
