from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.helpers.env import PROJECT_ROOT
from app.persistence.repositories.asset_repository import AssetRepository
from app.persistence.repositories.campaign_repository import CampaignRepository


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
    ) -> None:
        self.assets = assets or AssetRepository()
        self.campaigns = campaigns or CampaignRepository()

    def get_asset(
        self,
        *,
        asset_id: str,
        user_id: str,
        project_root: Path = PROJECT_ROOT,
    ) -> AssetReadResult:
        asset = self.assets.get_by_id(asset_id)
        if asset is None or not asset["storage_path"]:
            return AssetReadResult(success=False, error_key="not_found")

        campaign = self.campaigns.get_for_user(campaign_id=asset["campaign_id"], user_id=user_id)
        if campaign is None:
            return AssetReadResult(success=False, error_key="not_authorized")

        path = project_root / asset["storage_path"]
        if not path.exists():
            return AssetReadResult(success=False, error_key="not_found")

        return AssetReadResult(success=True, path=path, media_type=asset["content_type"] or "image/png")
