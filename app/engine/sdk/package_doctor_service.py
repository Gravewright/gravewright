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

import json
import hashlib
import sqlite3

from app.engine.sdk import package_registry
from app.engine.sdk.capability_registry import get_registry
from app.engine.sdk.diagnostics import DoctorFinding
from app.engine.sdk.package_compatibility import COMPAT_INCOMPATIBLE
from app.engine.sdk.package_integrity import compute_manifest_hash
from app.engine.sdk.package_paths import safe_join
from app.engine.sdk.package_storage import storage_block
from app.engine.sdk.package_storage_runtime import (
    MIGRATIONS_TABLE,
    MIGRATION_STATE_TABLE,
    DB_FILENAME,
)
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
                    details=dict(entry),
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

        # Each sub-audit is isolated: a broken package or corrupt row must never
        # crash the whole audit — it is reported as an internal error finding.
        for name, audit in (
            ("installed", self._audit_installed),
            ("campaign_activations", self._audit_campaign_activations),
            ("orphan_settings", self._audit_orphan_settings),
            ("orphan_content", self._audit_orphan_content),
            ("orphan_storage", self._audit_orphan_storage),
        ):
            try:
                findings.extend(audit(installed))
            except Exception as exc:  # defensive: the doctor must not crash
                findings.append(
                    DoctorFinding(
                        code="sdk.doctor.audit_error",
                        severity=SEVERITY_ERROR,
                        message=f"audit '{name}' failed: {exc}",
                        details={"audit": name},
                    )
                )
        return findings

    def report(self) -> dict:
        findings = self.audit()
        errors = sum(1 for f in findings if f.severity == SEVERITY_ERROR)
        return {
            "ok": errors == 0,
            "error_count": errors,
            "warning_count": len(findings) - errors,
            "findings": [f.to_dict() for f in findings],
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
                        details={"status": record["status"], "version": record["version"]},
                    )
                )
                continue

            findings.extend(self._audit_capabilities(package_id, loaded))

            # Manifest identity binding (Phase 5): a directory/manifest mismatch
            # is a structural error regardless of enabled state.
            for code in ("sdk.manifest.id_mismatch", "sdk.manifest.kind_root_mismatch"):
                if code in loaded.validation.errors:
                    findings.append(
                        DoctorFinding(
                            code=code,
                            severity=SEVERITY_ERROR,
                            package_id=package_id,
                        )
                    )
            findings.extend(self._audit_manifest_integrity(package_id, record, loaded))

            # Storage (Phase 7A) and interop (Phase 12): surface invalid contracts.
            for code in loaded.validation.errors:
                if code.startswith("sdk.storage.") or code.startswith("sdk.interop."):
                    findings.append(
                        DoctorFinding(
                            code=code,
                            severity=SEVERITY_ERROR,
                            package_id=package_id,
                        )
                    )
            findings.extend(self._audit_storage_runtime_state(package_id, loaded))

            if record["status"] == STATUS_ENABLED:
                if not loaded.validation.ok:
                    findings.append(
                        DoctorFinding(
                            code="enabled_but_invalid",
                            severity=SEVERITY_ERROR,
                            package_id=package_id,
                            details={"errors": list(loaded.validation.errors)},
                        )
                    )
                elif loaded.validation.compatibility_status == COMPAT_INCOMPATIBLE:
                    findings.append(
                        DoctorFinding(
                            code="enabled_but_incompatible",
                            severity=SEVERITY_ERROR,
                            package_id=package_id,
                            details={"compatibility": loaded.validation.compatibility_status},
                        )
                    )
                # Global dependency / conflict drift for enabled packages.
                findings.extend(
                    _dependency_findings(
                        package_id, self.dependencies.check(package_id), campaign_id=None
                    )
                )
        return findings

    def _audit_capabilities(self, package_id: str, loaded) -> list[DoctorFinding]:
        """Flag declared capabilities against the canonical registry.

        Unknown and forbidden capabilities are always errors.
        """
        registry = get_registry()
        findings: list[DoctorFinding] = []
        for capability in loaded.manifest.capabilities:
            if capability in registry.forbidden_names():
                findings.append(
                    DoctorFinding(
                        code="capability_forbidden",
                        severity=SEVERITY_ERROR,
                        package_id=package_id,
                        details={"capability": capability},
                    )
                )
                continue
            status = registry.status_of(capability)
            if status is None:
                findings.append(
                    DoctorFinding(
                        code="capability_unknown",
                        severity=SEVERITY_ERROR,
                        package_id=package_id,
                        details={"capability": capability},
                    )
                )
        return findings

    def _audit_manifest_integrity(
        self, package_id: str, record: dict, loaded
    ) -> list[DoctorFinding]:
        """Compare the stored manifest hash against the snapshot and disk.

        * stored hash != snapshot hash → the DB snapshot/hash pair is internally
          inconsistent (``sdk.persistence.manifest_hash_mismatch``).
        * stored hash != disk hash → the on-disk manifest changed since install
          (``sdk.manifest.snapshot_stale``).
        """
        stored_hash = record.get("manifest_hash")
        if not stored_hash:
            return []
        disk_hash = compute_manifest_hash(loaded.raw)
        try:
            snapshot_hash = compute_manifest_hash(json.loads(record["manifest_json"]))
        except (TypeError, ValueError):
            snapshot_hash = None
        if snapshot_hash is not None and stored_hash != snapshot_hash:
            return [
                DoctorFinding(
                    code="sdk.persistence.manifest_hash_mismatch",
                    severity=SEVERITY_ERROR,
                    package_id=package_id,
                    details={"stored": stored_hash, "snapshot": snapshot_hash},
                )
            ]
        if stored_hash != disk_hash:
            return [
                DoctorFinding(
                    code="sdk.manifest.snapshot_stale",
                    severity=SEVERITY_WARNING,
                    package_id=package_id,
                    details={"stored": stored_hash, "disk": disk_hash},
                )
            ]
        return []

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
                            details={"status": record["status"]},
                        )
                    )
                findings.extend(
                    _dependency_findings(
                        package_id,
                        self.dependencies.check_campaign_activation(package_id, campaign_id),
                        campaign_id=campaign_id,
                    )
                )
            findings.extend(self._audit_campaign_interop(campaign_id, package_ids))
        return findings

    def _audit_campaign_interop(
        self, campaign_id: str, package_ids: set[str]
    ) -> list[DoctorFinding]:
        providers: dict[str, list[str]] = {}
        required: list[tuple[str, str]] = []
        for package_id in package_ids:
            manifest = self.install.get_manifest(package_id)
            if manifest is None:
                continue
            interop = manifest.raw.get("interop") if isinstance(manifest.raw, dict) else None
            if not isinstance(interop, dict):
                continue
            provides = interop.get("provides")
            if isinstance(provides, dict):
                for method in provides:
                    providers.setdefault(str(method), []).append(package_id)
            requires = interop.get("requires")
            if isinstance(requires, dict):
                for method, declaration in requires.items():
                    optional = isinstance(declaration, dict) and declaration.get("optional") is True
                    if not optional:
                        required.append((package_id, str(method)))

        findings: list[DoctorFinding] = []
        for method, package_list in sorted(providers.items()):
            if len(package_list) > 1:
                for package_id in package_list:
                    findings.append(
                        DoctorFinding(
                            code="bus.provider_conflict",
                            severity=SEVERITY_ERROR,
                            package_id=package_id,
                            campaign_id=campaign_id,
                            details={"method": method, "providers": list(package_list)},
                        )
                    )
        for package_id, method in required:
            if method not in providers:
                findings.append(
                    DoctorFinding(
                        code="bus.provider_not_found",
                        severity=SEVERITY_ERROR,
                        package_id=package_id,
                        campaign_id=campaign_id,
                        details={"method": method},
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
                        details={"setting_key": key},
                    )
                )
            elif key not in declared.get(package_id, set()):
                findings.append(
                    DoctorFinding(
                        code="orphan_setting_undeclared",
                        severity=SEVERITY_WARNING,
                        package_id=package_id,
                        details={"setting_key": key},
                    )
                )
            else:
                # Declared setting: flag a stored value that is not valid JSON so
                # a corrupted row is diagnosed rather than crashing at read time.
                try:
                    json.loads(row["value_json"])
                except (TypeError, ValueError):
                    findings.append(
                        DoctorFinding(
                            code="setting_value_corrupted",
                            severity=SEVERITY_WARNING,
                            package_id=package_id,
                            details={"setting_key": key},
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
                        details={"content_pack_id": row.get("content_pack_id")},
                    )
                )
        return findings

    def _audit_orphan_storage(self, installed: dict[str, dict]) -> list[DoctorFinding]:
        """Managed storage directories whose package is no longer installed."""
        findings: list[DoctorFinding] = []
        root = package_registry.STORAGE_PACKAGES_DIR
        if not root.is_dir():
            return findings
        for kind_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            for package_dir in sorted(p for p in kind_dir.iterdir() if p.is_dir()):
                if package_dir.name not in installed:
                    findings.append(
                        DoctorFinding(
                            code="sdk.storage.orphaned_storage",
                            severity=SEVERITY_WARNING,
                            package_id=package_dir.name,
                            details={"storage_dir": str(package_dir)},
                        )
                    )
        return findings

    def _audit_storage_runtime_state(self, package_id: str, loaded) -> list[DoctorFinding]:
        """Inspect managed SQLite DBs for migration dirty/hash drift."""
        block = storage_block(loaded.raw) or {}
        migrations_rel = block.get("migrations")
        if not migrations_rel:
            return []
        migrations_dir = safe_join(loaded.package_dir, migrations_rel)
        storage_root = package_registry.storage_dir_for(loaded.manifest.kind, package_id)
        if migrations_dir is None or storage_root is None or not storage_root.is_dir():
            return []

        current_hashes: dict[str, str] = {}
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            text = sql_file.read_text(encoding="utf-8")
            current_hashes[sql_file.stem] = hashlib.sha256(text.encode("utf-8")).hexdigest()

        findings: list[DoctorFinding] = []
        for db_path in sorted(storage_root.rglob(DB_FILENAME)):
            try:
                conn = sqlite3.connect(db_path)
                try:
                    dirty = self._storage_state_value(conn)
                    if dirty and dirty != "clean":
                        findings.append(
                            DoctorFinding(
                                code="sdk.storage.sqlite.migration_dirty",
                                severity=SEVERITY_ERROR,
                                package_id=package_id,
                                details={"state": dirty, "database": str(db_path)},
                            )
                        )
                    if self._table_exists(conn, MIGRATIONS_TABLE):
                        rows = conn.execute(
                            f"SELECT version, sha256 FROM {MIGRATIONS_TABLE}"
                        ).fetchall()
                        for version, stored_hash in rows:
                            current_hash = current_hashes.get(str(version))
                            if current_hash is not None and current_hash != stored_hash:
                                findings.append(
                                    DoctorFinding(
                                        code="sdk.storage.sqlite.migration_hash_mismatch",
                                        severity=SEVERITY_ERROR,
                                        package_id=package_id,
                                        details={
                                            "version": version,
                                            "database": str(db_path),
                                        },
                                    )
                                )
                finally:
                    conn.close()
            except sqlite3.Error as exc:
                findings.append(
                    DoctorFinding(
                        code="sdk.storage.sqlite.database_unreadable",
                        severity=SEVERITY_ERROR,
                        package_id=package_id,
                        details={"database": str(db_path), "error": str(exc)},
                    )
                )
        return findings

    @staticmethod
    def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        return row is not None

    def _storage_state_value(self, conn: sqlite3.Connection) -> str | None:
        if not self._table_exists(conn, MIGRATION_STATE_TABLE):
            return None
        row = conn.execute(
            f"SELECT value FROM {MIGRATION_STATE_TABLE} WHERE key = 'status'"
        ).fetchone()
        return None if row is None else str(row[0])
