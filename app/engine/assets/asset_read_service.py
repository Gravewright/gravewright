from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.helpers.env import PROJECT_ROOT
from app.domain.roles import has_full_view
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.asset_repository import AssetRepository
from app.persistence.repositories.campaign_repository import CampaignRepository


_MAX_SCAN_DEPTH = 12


@dataclass(frozen=True)
class AssetReadResult:
    success: bool
    path: Path | None = None
    media_type: str | None = None
    error_key: str | None = None


class AssetReadService:
    def __init__(
        self,
        *,
        assets: AssetRepository | None = None,
        campaigns: CampaignRepository | None = None,
        actors: ActorRepository | None = None,
        storage: ScopedJsonStorage | None = None,
    ) -> None:
        self.assets = assets or AssetRepository()
        self.campaigns = campaigns or CampaignRepository()
        self.actors = actors or ActorRepository()
        self.storage = storage or ScopedJsonStorage()

    def get_asset(
        self,
        *,
        asset_id: str,
        user_id: str,
        project_root: Path = PROJECT_ROOT,
        presentation: bool = False,
    ) -> AssetReadResult:
        asset = self.assets.get_by_id(asset_id)
        if asset is None or not asset["storage_path"]:
            return AssetReadResult(success=False, error_key="not_found")

        campaign = self.campaigns.get_for_user(campaign_id=asset["campaign_id"], user_id=user_id)
        if campaign is None:
            return AssetReadResult(success=False, error_key="not_authorized")
        if (
            not presentation
            and not has_full_view(campaign.get("member_role"))
            and asset.get("owner_user_id") != user_id
            and not self._embedded_in_a_sheet_the_user_reads(
                asset_id=asset_id, campaign_id=asset["campaign_id"], user_id=user_id
            )
        ):
            return AssetReadResult(success=False, error_key="not_authorized")

        path = project_root / asset["storage_path"]
        if not path.exists():
            return AssetReadResult(success=False, error_key="not_found")

        return AssetReadResult(
            success=True, path=path, media_type=asset["content_type"] or "image/png"
        )

    def _embedded_in_a_sheet_the_user_reads(
        self, *, asset_id: str, campaign_id: str, user_id: str
    ) -> bool:
        """Whether one of the user's own sheets points at this file.

        A sheet can *be* a library file — the PDF ruleset is the plain case,
        where the character sheet is the uploaded document. Reading the library
        answers to table-wide authority, so without this a player opens their own
        sheet and is denied its contents.

        Only sheets the user already reads are searched, and only for this exact
        id, so nothing else in the library becomes reachable. Which field holds
        the id is the ruleset's business, hence a plain search rather than a
        hard-coded path.
        """
        for actor in self.actors.list_visible_to_user(campaign_id=campaign_id, user_id=user_id):
            envelope = self.storage.read_actor(
                system_id=actor["system_id"],
                campaign_id=campaign_id,
                actor_id=actor["id"],
            )
            if not isinstance(envelope, dict):
                continue
            if _mentions(envelope.get("data"), asset_id, _MAX_SCAN_DEPTH):
                return True
        return False


def _mentions(node: Any, needle: str, depth: int) -> bool:
    if depth <= 0 or not needle:
        return False
    if isinstance(node, str):
        return node == needle
    if isinstance(node, dict):
        return any(_mentions(value, needle, depth - 1) for value in node.values())
    if isinstance(node, list):
        return any(_mentions(value, needle, depth - 1) for value in node)
    return False
