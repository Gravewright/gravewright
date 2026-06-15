"""Database-aware health audit for installed SDK packages.

The filesystem checks (`grave doctor` / package validation) only see the package
directories on disk. This service cross-references the **database** state —
``installed_packages``, per-campaign activations, stored settings and recorded
content imports — against what is actually installable on disk, surfacing drift
an operator would otherwise only discover at runtime:

* a package marked ``enabled`` whose manifest no longer validates;
* a package active in a campaign while globally ``disabled`` / not installed;
* a package row whose package directory is gone from disk;
* unmet dependencies / active conflicts, globally and per campaign;
* orphan setting values and content imports for packages that are gone;
* declared content/locale/asset files missing on disk (via the loader).

Each finding is a plain dict so the CLI can render text or JSON without coupling
to this module.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.engine.sdk import package_registry
from app.engine.sdk.package_compatibility import COMPAT_INCOMPATIBLE
from app.engine.sdk.package_dependency_service import DependencyReport, PackageDependencyService
from app.engine.sdk.package_install_service import (
    STATUS_ENABLED,
    PackageInstallService,
)
from app.persistence.repositories.campaign_package_repository import CampaignPackageRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.installed_package_repository import InstalledPackageRepository
from app.persistence.repositories.package_content_import_repository import (
    PackageContentImportRepository,
)
from app.persistence.repositories.package_setting_repository import PackageSettingRepository

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"


@dataclass
class DoctorFinding:
    code: str
    severity: str
    package_id: str
    detail: dict = field(default_factory=dict)
    campaign_id: str | None = None


def _dependency_findings(
    package_id: str, report: DependencyReport, *, campaign_id: str | None
) -> list[DoctorFinding]:
    """Translate a :class:`DependencyReport` into doctor findings."""
    out: list[DoctorFinding] = []
    buckets = (
        ("dependency_missing", SEVERITY_ERROR, report.missing),
        ("dependency_disabled", SEVERITY_ERROR, report.disabled),
        ("dependency_inactive", SEVERITY_ERROR, report.inactive),
        ("dependency_outdated", SEVERITY_ERROR, report.outdated),
        ("dependency_too_new", SEVERITY_ERROR, report.too_new),
        ("dependency_wrong_kind", SEVERITY_ERROR, report.wrong_kind),
        ("conflict_active", SEVERITY_ERROR, report.conflicts),
    )
    for code, severity, entries in buckets:
        for entry in entries:
            out.append(
                DoctorFinding(
                    code=code,
                    severity=severity,
                    package_id=package_id,
                    campaign_id=campaign_id,
                    detail=dict(entry),
                )
            )
    return out


class PackageDoctorService:
    def __init__(self) -> None:
        self.install = PackageInstallService()
        self.installed = InstalledPackageRepository()
        self.dependencies = PackageDependencyService()
        self.campaigns = CampaignRepository()
        self.campaign_packages = CampaignPackageRepository()
        self.settings = PackageSettingRepository()
        self.content_imports = PackageContentImportRepository()

    def audit(self) -> list[DoctorFinding]:
        findings: list[DoctorFinding] = []
        installed = {row["id"]: row for row in self.installed.list_all()}

        findings.extend(self._audit_installed(installed))
        findings.extend(self._audit_campaign_activations(installed))
        findings.extend(self._audit_orphan_settings(installed))
        findings.extend(self._audit_orphan_content(installed))
        return findings

    def report(self) -> dict:
        findings = self.audit()
        errors = sum(1 for f in findings if f.severity == SEVERITY_ERROR)
        return {
            "ok": errors == 0,
            "error_count": errors,
            "warning_count": len(findings) - errors,
            "findings": [self._serialize(f) for f in findings],
        }

    # --- audits ----------------------------------------------------------------

    def _audit_installed(self, installed: dict[str, dict]) -> list[DoctorFinding]:
        findings: list[DoctorFinding] = []
        for package_id, record in installed.items():
            loaded = package_registry.load_by_package_id(package_id)
            if loaded is None:
                findings.append(
                    DoctorFinding(
                        code="package_missing_on_disk",
                        severity=SEVERITY_ERROR,
                        package_id=package_id,
                        detail={"status": record["status"], "version": record["version"]},
                    )
                )
                continue

            if record["status"] == STATUS_ENABLED:
                if not loaded.validation.ok:
                    findings.append(
                        DoctorFinding(
                            code="enabled_but_invalid",
                            severity=SEVERITY_ERROR,
                            package_id=package_id,
                            detail={"errors": list(loaded.validation.errors)},
                        )
                    )
                elif loaded.validation.compatibility_status == COMPAT_INCOMPATIBLE:
                    findings.append(
                        DoctorFinding(
                            code="enabled_but_incompatible",
                            severity=SEVERITY_ERROR,
                            package_id=package_id,
                            detail={"compatibility": loaded.validation.compatibility_status},
                        )
                    )
                # Global dependency / conflict drift for enabled packages.
                findings.extend(
                    _dependency_findings(
                        package_id, self.dependencies.check(package_id), campaign_id=None
                    )
                )
        return findings

    def _audit_campaign_activations(self, installed: dict[str, dict]) -> list[DoctorFinding]:
        findings: list[DoctorFinding] = []
        # Build the set of (campaign_id, package_id) activations from both the
        # exclusive ruleset slot and the multi-activation table.
        activations: dict[str, set[str]] = {}
        for campaign in self.campaigns.list_with_active_system():
            ruleset_id = campaign.get("active_system_id")
            if ruleset_id:
                activations.setdefault(campaign["id"], set()).add(str(ruleset_id))
        for row in self.campaign_packages.list_all():
            if str(row.get("status")) == "active":
                activations.setdefault(str(row["campaign_id"]), set()).add(str(row["package_id"]))

        for campaign_id, package_ids in activations.items():
            for package_id in sorted(package_ids):
                record = installed.get(package_id)
                if record is None:
                    findings.append(
                        DoctorFinding(
                            code="active_but_not_installed",
                            severity=SEVERITY_ERROR,
                            package_id=package_id,
                            campaign_id=campaign_id,
                        )
                    )
                    continue
                if record["status"] != STATUS_ENABLED:
                    findings.append(
                        DoctorFinding(
                            code="active_but_disabled",
                            severity=SEVERITY_ERROR,
                            package_id=package_id,
                            campaign_id=campaign_id,
                            detail={"status": record["status"]},
                        )
                    )
                findings.extend(
                    _dependency_findings(
                        package_id,
                        self.dependencies.check_campaign_activation(package_id, campaign_id),
                        campaign_id=campaign_id,
                    )
                )
        return findings

    def _audit_orphan_settings(self, installed: dict[str, dict]) -> list[DoctorFinding]:
        findings: list[DoctorFinding] = []
        declared: dict[str, set[str]] = {}
        for package_id, _record in installed.items():
            manifest = self.install.get_manifest(package_id)
            declared[package_id] = (
                {s.key for s in manifest.settings if s.key} if manifest else set()
            )
        for row in self.settings.list_all():
            package_id = str(row["package_id"])
            key = str(row["setting_key"])
            if package_id not in installed:
                findings.append(
                    DoctorFinding(
                        code="orphan_setting_uninstalled",
                        severity=SEVERITY_WARNING,
                        package_id=package_id,
                        detail={"setting_key": key},
                    )
                )
            elif key not in declared.get(package_id, set()):
                findings.append(
                    DoctorFinding(
                        code="orphan_setting_undeclared",
                        severity=SEVERITY_WARNING,
                        package_id=package_id,
                        detail={"setting_key": key},
                    )
                )
        return findings

    def _audit_orphan_content(self, installed: dict[str, dict]) -> list[DoctorFinding]:
        findings: list[DoctorFinding] = []
        for row in self.content_imports.list_all():
            package_id = str(row["package_id"])
            if package_id not in installed:
                findings.append(
                    DoctorFinding(
                        code="orphan_content_import",
                        severity=SEVERITY_WARNING,
                        package_id=package_id,
                        campaign_id=str(row.get("campaign_id")) or None,
                        detail={"content_pack_id": row.get("content_pack_id")},
                    )
                )
        return findings

    @staticmethod
    def _serialize(finding: DoctorFinding) -> dict:
        data = asdict(finding)
        if data.get("campaign_id") is None:
            data.pop("campaign_id")
        if not data.get("detail"):
            data.pop("detail", None)
        return data
