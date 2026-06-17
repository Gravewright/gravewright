"""Dependency and conflict resolution between installed SDK packages.

A package may declare ``dependencies`` (other packages it needs) and
``conflicts`` (packages it cannot run alongside). This service checks those
declarations against the installed/enabled set so the UI and CLI can warn before
enabling or activating a package.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engine.sdk.package_compatibility import version_key
from app.engine.sdk.package_install_service import PackageInstallService
from app.persistence.repositories.campaign_package_repository import (
    CampaignPackageRepository,
)
from app.persistence.repositories.campaign_repository import CampaignRepository


@dataclass
class DependencyReport:
    ok: bool = True
    missing: list[dict] = field(default_factory=list)
    disabled: list[dict] = field(default_factory=list)
    inactive: list[dict] = field(default_factory=list)
    outdated: list[dict] = field(default_factory=list)
    too_new: list[dict] = field(default_factory=list)
    wrong_kind: list[dict] = field(default_factory=list)
    conflicts: list[dict] = field(default_factory=list)


class PackageDependencyService:
    def __init__(self) -> None:
        self.install = PackageInstallService()
        self.campaign_packages = CampaignPackageRepository()
        self.campaigns = CampaignRepository()

    def check(self, package_id: str) -> DependencyReport:
        manifest = self.install.get_manifest(package_id)
        report = DependencyReport()
        if manifest is None:
            return report

        installed = {row["id"]: row for row in self.install.installed.list_all()}

        for dependency in manifest.dependencies:
            record = installed.get(dependency.id)
            if record is None:
                report.missing.append({"id": dependency.id, "kind": dependency.kind})
                continue
            if dependency.kind and dependency.kind != record["kind"]:
                report.wrong_kind.append(
                    {"id": dependency.id, "expected": dependency.kind, "actual": record["kind"]}
                )
            if record["status"] != "enabled":
                report.disabled.append({"id": dependency.id, "kind": record["kind"]})
            if dependency.minimum and version_key(record["version"]) < version_key(
                dependency.minimum
            ):
                report.outdated.append(
                    {
                        "id": dependency.id,
                        "installed": record["version"],
                        "minimum": dependency.minimum,
                    }
                )
            if dependency.maximum and version_key(record["version"]) > version_key(
                dependency.maximum
            ):
                report.too_new.append(
                    {
                        "id": dependency.id,
                        "installed": record["version"],
                        "maximum": dependency.maximum,
                    }
                )

        for conflict in manifest.conflicts:
            record = installed.get(conflict.id)
            if record and record["status"] == "enabled":
                report.conflicts.append({"id": conflict.id, "reason": conflict.reason})

        report.ok = not (
            report.missing
            or report.disabled
            or report.outdated
            or report.too_new
            or report.wrong_kind
            or report.conflicts
        )
        return report

    def check_campaign_activation(self, package_id: str, campaign_id: str) -> DependencyReport:
        manifest = self.install.get_manifest(package_id)
        report = DependencyReport()
        if manifest is None:
            return report

        installed = {row["id"]: row for row in self.install.installed.list_all()}
        campaign = self.campaigns.get(campaign_id)
        active_ruleset_id = campaign.get("active_system_id") if campaign else None
        active_package_rows = self.campaign_packages.list_for_campaign(campaign_id)
        active_package_ids = {str(row["package_id"]) for row in active_package_rows}
        enabled_library_ids = {
            row["id"]
            for row in installed.values()
            if row["kind"] == "library" and row["status"] == "enabled"
        }
        loaded_ids = (
            ({active_ruleset_id} if active_ruleset_id else set())
            | active_package_ids
            | enabled_library_ids
        )
        conflict_ids = set(loaded_ids)
        if manifest.kind == "ruleset" and active_ruleset_id != package_id:
            conflict_ids.discard(active_ruleset_id)

        for dependency in manifest.dependencies:
            record = installed.get(dependency.id)
            if record is None:
                report.missing.append({"id": dependency.id, "kind": dependency.kind})
                continue

            dependency_kind = dependency.kind or record["kind"]
            if dependency.kind and dependency.kind != record["kind"]:
                report.wrong_kind.append(
                    {"id": dependency.id, "expected": dependency.kind, "actual": record["kind"]}
                )
            if record["status"] != "enabled":
                report.disabled.append({"id": dependency.id, "kind": record["kind"]})
                continue
            if dependency.minimum and version_key(record["version"]) < version_key(
                dependency.minimum
            ):
                report.outdated.append(
                    {
                        "id": dependency.id,
                        "installed": record["version"],
                        "minimum": dependency.minimum,
                    }
                )
            if dependency.maximum and version_key(record["version"]) > version_key(
                dependency.maximum
            ):
                report.too_new.append(
                    {
                        "id": dependency.id,
                        "installed": record["version"],
                        "maximum": dependency.maximum,
                    }
                )
            if dependency_kind != "library" and dependency.id not in loaded_ids:
                report.inactive.append({"id": dependency.id, "kind": dependency_kind})

        for conflict in manifest.conflicts:
            if conflict.id in conflict_ids:
                report.conflicts.append({"id": conflict.id, "reason": conflict.reason})

        for active_id in conflict_ids:
            if not active_id or active_id == package_id:
                continue
            active_manifest = self.install.get_manifest(str(active_id))
            if active_manifest is None:
                continue
            for conflict in active_manifest.conflicts:
                if conflict.id == package_id:
                    report.conflicts.append(
                        {"id": str(active_id), "reason": conflict.reason, "declared_by": str(active_id)}
                    )

        report.ok = not (
            report.missing
            or report.disabled
            or report.inactive
            or report.outdated
            or report.too_new
            or report.wrong_kind
            or report.conflicts
        )
        return report

    def active_campaign_dependents(self, package_id: str, campaign_id: str) -> list[dict]:
        """Packages active in ``campaign_id`` that depend on ``package_id``.

        Used to block deactivation: deactivating a package other active packages
        in the same campaign depend on would leave them broken.
        """
        active_ids: set[str] = set()
        campaign = self.campaigns.get(campaign_id)
        ruleset_id = campaign.get("active_system_id") if campaign else None
        if ruleset_id:
            active_ids.add(str(ruleset_id))
        for row in self.campaign_packages.list_for_campaign(campaign_id):
            if str(row.get("status")) == "active":
                active_ids.add(str(row["package_id"]))

        out: list[dict] = []
        for active_id in sorted(active_ids):
            if active_id == package_id:
                continue
            manifest = self.install.get_manifest(active_id)
            if manifest is None:
                continue
            if any(dep.id == package_id for dep in manifest.dependencies):
                out.append({"id": active_id})
        return out

    @staticmethod
    def blocking_error_keys(report: DependencyReport) -> list[str]:
        """Every reason a package is blocked, as i18n error keys (for the UI)."""
        keys: list[str] = []
        if report.missing:
            keys.append("sdk.errors.dependency_missing")
        if report.disabled:
            keys.append("sdk.errors.dependency_disabled")
        if report.inactive:
            keys.append("sdk.errors.dependency_inactive")
        if report.outdated:
            keys.append("sdk.errors.dependency_outdated")
        if report.too_new:
            keys.append("sdk.errors.dependency_too_new")
        if report.wrong_kind:
            keys.append("sdk.errors.dependency_wrong_kind")
        if report.conflicts:
            keys.append("sdk.errors.package_conflict_active")
        return keys

    @classmethod
    def first_error_key(cls, report: DependencyReport) -> str | None:
        keys = cls.blocking_error_keys(report)
        return keys[0] if keys else None
