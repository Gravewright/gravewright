"""Server-side authority gate for public SDK runtime calls.

Browser capability checks are developer feedback only. Every SDK 1 request is
revalidated here against membership, package activation, SDK version, and the
installed manifest's declared capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.sdk.package_asset_service import PackageAssetService
from app.engine.sdk.package_install_service import PackageInstallService
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.realtime.metrics import realtime_metrics


@dataclass(frozen=True)
class RuntimeAuthorityResult:
    allowed: bool
    error_key: str | None = None


class SdkRuntimeAuthority:
    def __init__(self) -> None:
        self.campaigns = CampaignRepository()
        self.assets = PackageAssetService()
        self.install = PackageInstallService()

    def authorize(
        self, *, campaign_id: str, user_id: str, package_id: str, capability: str
    ) -> RuntimeAuthorityResult:
        realtime_metrics.increment("sdk_calls_by_package")
        realtime_metrics.increment(f"sdk.calls.{package_id[:80] or 'unknown'}")
        if self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id) is None:
            realtime_metrics.increment("sdk_permission_denied")
            return RuntimeAuthorityResult(False, "sdk.runtime.campaign_denied")
        if package_id not in self.assets.active_package_ids(campaign_id):
            realtime_metrics.increment("sdk_denied_capability")
            return RuntimeAuthorityResult(False, "sdk.runtime.package_inactive")
        manifest = self.install.get_active_manifest(package_id)
        if manifest is None:
            realtime_metrics.increment("sdk_denied_capability")
            return RuntimeAuthorityResult(False, "sdk.runtime.package_disabled")
        if capability not in manifest.capabilities:
            realtime_metrics.increment("sdk_denied_capability")
            return RuntimeAuthorityResult(False, "sdk.runtime.capability_required")
        return RuntimeAuthorityResult(True)
