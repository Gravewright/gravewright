from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.engine.journals.journal_service import JournalService
from app.helpers.env import PROJECT_ROOT
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.journal_asset_repository import JournalAssetRepository
from app.persistence.repositories.journal_repository import JournalRepository


@dataclass(frozen=True)
class JournalAssetReadResult:
    success: bool
    path: Path | None = None
    media_type: str | None = None
    error_key: str | None = None


class JournalAssetReadService:
    def __init__(
        self,
        *,
        assets: JournalAssetRepository | None = None,
        campaigns: CampaignRepository | None = None,
        journals: JournalRepository | None = None,
        journal_service: JournalService | None = None,
    ) -> None:
        self.assets = assets or JournalAssetRepository()
        self.campaigns = campaigns or CampaignRepository()
        self.journals = journals or JournalRepository()
        self.journal_service = journal_service or JournalService()

    def get_asset(
        self,
        *,
        asset_id: str,
        user_id: str,
        project_root: Path = PROJECT_ROOT,
    ) -> JournalAssetReadResult:
        asset = self.assets.get_by_id(asset_id)
        if asset is None or not asset["storage_path"]:
            return JournalAssetReadResult(success=False, error_key="not_found")

        campaign = self.campaigns.get_for_user(
            campaign_id=asset["campaign_id"],
            user_id=user_id,
        )
        if campaign is None:
            return JournalAssetReadResult(success=False, error_key="not_authorized")

        journal_id = asset["journal_id"] if "journal_id" in asset.keys() else None
        if journal_id:
            journal = self.journals.get_by_id(journal_id)
            if journal is None or not self.journal_service.can_view_journal(
                journal=dict(journal),
                campaign=dict(campaign),
                user_id=user_id,
            ):
                return JournalAssetReadResult(success=False, error_key="not_authorized")

        path = project_root / asset["storage_path"]
        if not path.exists():
            return JournalAssetReadResult(success=False, error_key="not_found")

        return JournalAssetReadResult(
            success=True,
            path=path,
            media_type=asset["content_type"] or "image/png",
        )
