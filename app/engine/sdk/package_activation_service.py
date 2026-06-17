"""Per-campaign activation of installed SDK packages.

A campaign has exactly one active *ruleset* (stored on the campaign as its
``active_system_id`` — the ruleset package id) and any number of active
``addon`` / ``theme`` / ``assets`` / ``content`` packages, recorded in
``campaign_packages`` keyed by their activation role (the package ``kind``).
``library`` packages are passive and cannot be activated directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.sdk.package_dependency_service import PackageDependencyService
from app.engine.sdk.package_install_service import PackageInstallService
from app.persistence.repositories.campaign_package_repository import (
    CampaignPackageRepository,
)
from app.persistence.repositories.campaign_repository import CampaignRepository

ROLE_RULESET = "ruleset"
_ACTIVATABLE_KINDS = {"addon", "theme", "assets", "content"}


@dataclass(frozen=True)
class ActivationResult:
    success: bool
    error_key: str | None = None
    active_dependents: tuple[dict, ...] = ()


class PackageActivationService:
    def __init__(self) -> None:
        self.install = PackageInstallService()
        self.dependencies = PackageDependencyService()
        self.campaign_packages = CampaignPackageRepository()
        self.campaigns = CampaignRepository()

    def _enabled(self, package_id: str) -> dict | None:
        record = self.install.get(package_id)
        if record is None or record["status"] != "enabled":
            return None
        return record

    def set_campaign_ruleset(
        self, campaign_id: str, package_id: str | None, user_id: str
    ) -> ActivationResult:
        if package_id is not None:
            record = self._enabled(package_id)
            if record is None:
                return ActivationResult(success=False, error_key="sdk.errors.not_found")
            if record["kind"] != ROLE_RULESET:
                return ActivationResult(success=False, error_key="sdk.errors.not_a_ruleset")
            dependency_report = self.dependencies.check_campaign_activation(
                package_id, campaign_id
            )
            if not dependency_report.ok:
                return ActivationResult(
                    success=False,
                    error_key=self.dependencies.first_error_key(dependency_report),
                )
        # The ruleset is exclusive: it is the campaign's authoritative active id.
        self.campaigns.update_system(
            campaign_id=campaign_id,
            changed_by_user_id=user_id,
            next_system_id=package_id,
        )
        self.campaign_packages.deactivate_role(
            campaign_id=campaign_id, activation_role=ROLE_RULESET
        )
        if package_id is not None:
            self.campaign_packages.activate(
                campaign_id=campaign_id,
                package_id=package_id,
                activation_role=ROLE_RULESET,
                enabled_by_user_id=user_id,
            )
        return ActivationResult(success=True)

    def activate_package(
        self, campaign_id: str, package_id: str, user_id: str
    ) -> ActivationResult:
        record = self._enabled(package_id)
        if record is None:
            return ActivationResult(success=False, error_key="sdk.errors.not_found")
        if record["kind"] not in _ACTIVATABLE_KINDS:
            return ActivationResult(success=False, error_key="sdk.errors.not_activatable")
        dependency_report = self.dependencies.check_campaign_activation(package_id, campaign_id)
        if not dependency_report.ok:
            return ActivationResult(
                success=False,
                error_key=self.dependencies.first_error_key(dependency_report),
            )
        existing = self.campaign_packages.list_for_campaign(campaign_id)
        load_order = len(existing)
        self.campaign_packages.activate(
            campaign_id=campaign_id,
            package_id=package_id,
            activation_role=record["kind"],
            enabled_by_user_id=user_id,
            load_order=load_order,
        )
        return ActivationResult(success=True)

    def deactivate_package(
        self, campaign_id: str, package_id: str, user_id: str, force: bool = False
    ) -> ActivationResult:
        if not force:
            dependents = self.dependencies.active_campaign_dependents(package_id, campaign_id)
            if dependents:
                return ActivationResult(
                    success=False,
                    error_key="sdk.errors.active_dependents",
                    active_dependents=tuple(dependents),
                )
        self.campaign_packages.deactivate(campaign_id=campaign_id, package_id=package_id)
        return ActivationResult(success=True)

    def list_campaign_packages(self, campaign_id: str) -> list[dict]:
        out: list[dict] = []
        for row in self.campaign_packages.list_for_campaign(campaign_id):
            record = self.install.get(row["package_id"])
            out.append(
                {
                    "package_id": row["package_id"],
                    "activation_role": row["activation_role"],
                    "status": row["status"],
                    "load_order": row["load_order"],
                    "name": record["name"] if record else row["package_id"],
                    "kind": record["kind"] if record else row["activation_role"],
                    "version": record["version"] if record else "",
                }
            )
        return out

    def get_active_ruleset(self, campaign_id: str) -> dict | None:
        campaign = self.campaigns.get(campaign_id)
        ruleset_id = campaign.get("active_system_id") if campaign else None
        if not ruleset_id:
            return None
        return self.install.get(ruleset_id)
