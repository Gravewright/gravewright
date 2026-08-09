from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.business.permissions import PermissionService
from app.domain.permissions.permissions import TablePermission
from app.engine.actors.actor_permissions import can_view_actor
from app.engine.content.content_pack_service import ContentPackService
from app.engine.items.item_permissions import can_view_item
from app.engine.journals.journal_service import JournalService
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.global_search_repository import GlobalSearchRepository


SEARCH_LIMIT_MAX = 20
SEARCH_QUERY_MIN = 2
SEARCH_QUERY_MAX = 100


@dataclass(frozen=True)
class GlobalSearchResult:
    success: bool
    results: list[dict[str, Any]] = field(default_factory=list)
    error_key: str | None = None


class GlobalSearchService:
    def __init__(self) -> None:
        self.repository = GlobalSearchRepository()
        self.campaigns = CampaignRepository()
        self.permissions = PermissionService()
        self.journals = JournalService()
        self.content_packs = ContentPackService()

    def search(
        self, *, campaign_id: str, user_id: str, query: str, limit: int = SEARCH_LIMIT_MAX
    ) -> GlobalSearchResult:
        normalized = " ".join(query.strip().split())[:SEARCH_QUERY_MAX]
        if len(normalized) < SEARCH_QUERY_MIN:
            return GlobalSearchResult(success=True)
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return GlobalSearchResult(success=False, error_key="search.errors.denied")
        limit = max(1, min(int(limit), SEARCH_LIMIT_MAX))
        candidate_limit = limit * 2
        results: list[dict[str, Any]] = []

        for actor in self.repository.search_actors(
            campaign_id=campaign_id, query=normalized, limit=candidate_limit
        ):
            if can_view_actor(actor=actor, campaign=campaign, user_id=user_id):
                results.append(self._resource(actor, "actor", "ph-user", actor["name"]))

        for item in self.repository.search_items(
            campaign_id=campaign_id, query=normalized, limit=candidate_limit
        ):
            if can_view_item(item=item, campaign=campaign, user_id=user_id):
                results.append(self._resource(item, "item", "ph-sword", item["name"]))

        for journal in self.repository.search_journals(
            campaign_id=campaign_id, query=normalized, limit=candidate_limit
        ):
            if self.journals.can_view_journal(journal=journal, campaign=campaign, user_id=user_id):
                results.append(
                    self._resource(
                        journal,
                        "journal",
                        "ph-book-open-text",
                        journal["title"],
                        snippet=self._snippet(journal.get("content_markdown"), normalized),
                    )
                )

        can_view_scenes = self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.SCENE_VIEW,
        )
        can_manage_scenes = self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.SCENE_MANAGE,
        )
        if can_view_scenes:
            for scene in self.repository.search_scenes(
                campaign_id=campaign_id, query=normalized, limit=candidate_limit
            ):
                if not can_manage_scenes and not bool(scene.get("active")):
                    continue
                entry = self._resource(scene, "scene", "ph-map", scene["name"])
                entry["target"]["action"] = (
                    "focus_scene" if scene.get("active") else "open_scene_manager"
                )
                results.append(entry)

        if campaign.get("member_role") == "gm":
            results.extend(self._search_compendiums(campaign=campaign, query=normalized))
        results.sort(key=lambda row: (row["title"].casefold(), row["type"], row["id"]))
        return GlobalSearchResult(success=True, results=results[:limit])

    @staticmethod
    def _resource(
        row: dict, resource_type: str, icon: str, title: str, *, snippet: str = ""
    ) -> dict[str, Any]:
        labels = {
            "actor": "open_actor",
            "item": "open_item",
            "journal": "open_journal",
            "scene": "open_scene",
        }
        folder = str(row.get("folder_name") or "")
        subtype = str(row.get("type") or "")
        return {
            "id": str(row["id"]),
            "type": resource_type,
            "title": str(title),
            "subtitle": folder or subtype,
            "icon": icon,
            "snippet": snippet,
            "target": {"action": labels[resource_type], "id": str(row["id"])},
        }

    def _search_compendiums(self, *, campaign: dict, query: str) -> list[dict[str, Any]]:
        system_id = str(campaign.get("active_system_id") or "")
        if not system_id:
            return []
        try:
            packs = self.content_packs.list_packs(system_id)
        except (OSError, ValueError):
            return []
        needle = query.casefold()
        return [
            {
                "id": str(pack.get("id", "")),
                "type": "compendium",
                "title": str(pack.get("label") or pack.get("name") or pack.get("id") or ""),
                "subtitle": str(pack.get("type") or system_id),
                "icon": "ph-books",
                "snippet": "",
                "target": {
                    "action": "open_compendium",
                    "system_id": system_id,
                    "id": str(pack.get("id", "")),
                },
            }
            for pack in packs
            if needle
            in str(pack.get("label") or pack.get("name") or pack.get("id") or "").casefold()
        ]

    @staticmethod
    def _snippet(content: Any, query: str) -> str:
        text = re.sub(r"\s+", " ", str(content or "")).strip()
        if not text:
            return ""
        index = text.casefold().find(query.casefold())
        start = max(0, index - 35) if index >= 0 else 0
        excerpt = text[start : start + 110]
        return ("…" if start else "") + excerpt + ("…" if start + 110 < len(text) else "")
