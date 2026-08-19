from __future__ import annotations

from dataclasses import dataclass

from app.domain.roles import PlayerRole
from app.engine.sdk.package_install_service import PackageInstallService
from app.persistence.repositories.campaign_repository import CampaignRepository


CORE_AREA_MARKER_PRESETS = (
    {"id": "core.line", "shape": "line", "labelKey": "game.tool_dock.shape.line", "style": {"stroke": "#c69c59", "fill": "transparent", "strokeWidth": 2}},
    {"id": "core.circle", "shape": "circle", "labelKey": "game.tool_dock.shape.circle", "style": {"stroke": "#c69c59", "fill": "rgba(198,156,89,0.14)", "strokeWidth": 2}},
    {"id": "core.square", "shape": "square", "labelKey": "game.tool_dock.shape.square", "style": {"stroke": "#c69c59", "fill": "rgba(198,156,89,0.14)", "strokeWidth": 2}},
    {"id": "core.cone", "shape": "cone", "labelKey": "game.tool_dock.shape.cone", "style": {"stroke": "#c69c59", "fill": "rgba(198,156,89,0.14)", "strokeWidth": 2}},
)


def resolved_area_marker_presets(presets: list[dict] | None) -> list[dict]:
    source = presets if presets else CORE_AREA_MARKER_PRESETS
    return [
        {**preset, **({"style": dict(preset["style"])} if isinstance(preset.get("style"), dict) else {})}
        for preset in source
    ]


@dataclass(frozen=True)
class CampaignSystemResult:
    success: bool
    error_key: str | None = None


class CampaignSystemService:
    def __init__(self) -> None:
        self.campaigns = CampaignRepository()
        self.system_install = PackageInstallService()

    def _is_assignable(self, system_id: str) -> bool:
        record = self.system_install.installed.get(system_id)
        return record is not None and record["status"] == "enabled" and record["kind"] == "ruleset"

    def area_marker_presets(self, system_id: str | None) -> list[dict]:
        """Resolved area-marker presets for an enabled system (empty if none/detached).

        Mirrors what ``GamePageService`` injects into the page on load so a live
        ``campaign.system.changed`` broadcast can refresh the tool palette in place.
        """
        if not system_id:
            return resolved_area_marker_presets([])
        for item in self.system_install.list_for_tab():
            if item["id"] == system_id and item["status"] == "enabled":
                return resolved_area_marker_presets(item.get("area_markers", []))
        return resolved_area_marker_presets([])

    def assign_to_campaign(
        self,
        *,
        campaign_id: str,
        user_id: str,
        system_id: str | None,
    ) -> CampaignSystemResult:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return CampaignSystemResult(
                success=False, error_key="inside.campaigns.errors.not_found"
            )
        if campaign["member_role"] != PlayerRole.GM.value:
            return CampaignSystemResult(
                success=False, error_key="inside.campaigns.errors.gm_required"
            )
        if system_id is not None and not self._is_assignable(system_id):
            return CampaignSystemResult(success=False, error_key="inside.rulesets.errors.not_found")

        self.campaigns.update_system(
            campaign_id=campaign_id,
            changed_by_user_id=user_id,
            next_system_id=system_id,
        )
        return CampaignSystemResult(success=True)
