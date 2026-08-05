"""Global install / enable / disable / remove for SDK packages (Inside > Packages).

Disk packages (read-only, discovered by the registry) are merged with the
``installed_packages`` table to produce the state machine:
``available | installed | enabled | disabled | incompatible | error``.

Everything is keyed by **package id** (the on-disk directory name, which equals
the manifest ``id`` for valid packages). Installing or enabling requires the
package to pass validation *and* be compatible.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass

from app.engine.sdk import package_archive_installer, package_registry
from app.engine.sdk.package_compatibility import COMPAT_INCOMPATIBLE
from app.engine.sdk.package_integrity import (
    VALIDATION_VALID,
    compute_manifest_hash,
)
from app.engine.sdk.package_loader import LoadedPackage
from app.engine.sdk.package_manifest import PackageManifest
from app.persistence.repositories.installed_package_repository import (
    InstalledPackageRepository,
)
from app.persistence.repositories.campaign_package_repository import (
    CampaignPackageRepository,
)
from app.persistence.repositories.campaign_repository import CampaignRepository

STATUS_AVAILABLE = "available"
STATUS_INSTALLED = "installed"
STATUS_ENABLED = "enabled"
STATUS_DISABLED = "disabled"
STATUS_INCOMPATIBLE = "incompatible"
STATUS_ERROR = "error"

_PERSISTED = {STATUS_INSTALLED, STATUS_ENABLED, STATUS_DISABLED}


@dataclass(frozen=True)
class PackageActionResult:
    success: bool
    package_id: str | None = None
    error_key: str | None = None
    active_campaign_ids: tuple[str, ...] = ()
    active_dependents: tuple[dict, ...] = ()


def _is_incompatible(loaded: LoadedPackage) -> bool:
    return loaded.validation.compatibility_status == COMPAT_INCOMPATIBLE


def _installable(loaded: LoadedPackage) -> bool:
    return loaded.validation.ok and not _is_incompatible(loaded)


class PackageInstallService:
    def __init__(self) -> None:
        self.installed = InstalledPackageRepository()
        self.campaign_packages = CampaignPackageRepository()
        self.campaigns = CampaignRepository()

    # --- reads -----------------------------------------------------------------

    def list_for_tab(self) -> list[dict]:
        records = {row["id"]: row for row in self.installed.list_all()}
        items: list[dict] = []
        seen: set[str] = set()

        for loaded in package_registry.load_all():
            seen.add(loaded.id)
            items.append(self._tab_item(loaded, records.get(loaded.id)))

        for package_id, record in records.items():
            if package_id not in seen:
                items.append(self._missing_item(package_id, record))

        items.sort(key=lambda i: str(i["name"]).lower())
        return items

    def list_for_kind(self, kind: str) -> list[dict]:
        return [item for item in self.list_for_tab() if item["kind"] == kind]

    def get_details(self, package_id: str) -> dict | None:
        for item in self.list_for_tab():
            if item["id"] == package_id:
                return item
        return None

    def get(self, package_id: str) -> dict | None:
        return self.installed.get(package_id)

    def get_manifest(self, package_id: str) -> PackageManifest | None:
        record = self.installed.get(package_id)
        if record is None:
            return None
        # Disk is the runtime authority: prefer the current validated manifest on
        # disk over the stored snapshot. Fall back to the snapshot only when the
        # package is gone from disk (the doctor flags that drift separately).
        loaded = package_registry.load_by_package_id(package_id)
        if loaded is not None and loaded.raw:
            return loaded.manifest
        try:
            raw = json.loads(record["manifest_json"])
        except (TypeError, ValueError):
            return None
        return PackageManifest.from_dict(raw)

    def get_active_manifest(self, package_id: str) -> PackageManifest | None:
        """Manifest only if the package is installed *and* enabled globally."""
        record = self.installed.get(package_id)
        if record is None or record["status"] != STATUS_ENABLED:
            return None
        return self.get_manifest(package_id)

    # --- writes ----------------------------------------------------------------

    def install(self, *, package_id: str, user_id: str | None) -> PackageActionResult:
        loaded = package_registry.load_by_package_id(package_id)
        if loaded is None:
            return PackageActionResult(success=False, error_key="sdk.errors.not_found")
        if _is_incompatible(loaded):
            return PackageActionResult(success=False, error_key="sdk.errors.incompatible")
        if not loaded.validation.ok:
            return PackageActionResult(success=False, error_key="sdk.errors.invalid_manifest")

        manifest = loaded.manifest
        self.installed.upsert(
            package_id=manifest.id,
            kind=manifest.kind,
            name=manifest.name or manifest.id,
            version=manifest.version,
            status=STATUS_INSTALLED,
            package_dir=loaded.relative_dir,
            manifest_json=json.dumps(loaded.raw),
            compatibility_status=loaded.validation.compatibility_status,
            validation_errors_json="[]",
            installed_by_user_id=user_id,
            manifest_hash=compute_manifest_hash(loaded.raw),
            last_validation_status=VALIDATION_VALID,
        )
        return PackageActionResult(success=True, package_id=manifest.id)

    def install_uploaded_archive(
        self,
        *,
        filename: str,
        data: bytes,
        user_id: str | None,
        replace: bool = False,
        expected_group: str | None = None,
    ) -> PackageActionResult:
        """Install a package from an uploaded ZIP archive (status: installed).

        Extracts and validates the archive in a staging directory, applies the
        conflict policy, promotes it into the canonical packages location, and
        records it. Replacing an existing package is only allowed when it is not
        enabled globally and not active in any campaign.

        ``expected_group`` scopes an upload to its Inside tab: ``"ruleset"`` only
        accepts ``kind == "ruleset"``; ``"addon"`` accepts every non-ruleset kind
        (addon, library, theme, content, assets).
        """
        staged = package_archive_installer.stage_archive(filename=filename, data=data)
        if not staged.success or staged.staging_dir is None:
            return PackageActionResult(success=False, error_key=staged.error_key)

        package_id = staged.package_id or ""
        kind = staged.kind or ""

        if expected_group == "ruleset" and kind != "ruleset":
            package_archive_installer.discard(staged.staging_dir)
            return PackageActionResult(
                success=False, error_key="inside.rulesets.errors.not_a_ruleset_package"
            )
        if expected_group == "addon" and kind == "ruleset":
            package_archive_installer.discard(staged.staging_dir)
            return PackageActionResult(
                success=False, error_key="inside.addons.errors.ruleset_not_allowed"
            )

        target = package_registry.package_dir_for(kind, package_id)
        record = self.installed.get(package_id)
        exists = record is not None or (target is not None and target.exists())

        if exists:
            if not replace:
                package_archive_installer.discard(staged.staging_dir)
                return PackageActionResult(
                    success=False,
                    package_id=package_id,
                    error_key="inside.addons.errors.package_exists",
                )
            if record is not None and record["status"] == STATUS_ENABLED:
                package_archive_installer.discard(staged.staging_dir)
                return PackageActionResult(
                    success=False,
                    package_id=package_id,
                    error_key="inside.addons.errors.disable_before_replace",
                )
            active = self._active_campaign_ids(package_id)
            if active:
                package_archive_installer.discard(staged.staging_dir)
                return PackageActionResult(
                    success=False,
                    package_id=package_id,
                    error_key="inside.addons.errors.disable_campaigns_before_replace",
                    active_campaign_ids=tuple(active),
                )

        try:
            package_archive_installer.promote(
                staging_dir=staged.staging_dir, kind=kind, package_id=package_id
            )
        except Exception:  # noqa: BLE001 - report a clean error, never crash the route
            package_archive_installer.discard(staged.staging_dir)
            return PackageActionResult(
                success=False, package_id=package_id, error_key="inside.addons.errors.package_invalid"
            )

        return self.install(package_id=package_id, user_id=user_id)

    def enable(self, *, package_id: str) -> PackageActionResult:
        record = self.installed.get(package_id)
        if record is None:
            return PackageActionResult(success=False, error_key="sdk.errors.not_installed")
        # Re-read and re-validate the current manifest from disk before enabling.
        loaded = package_registry.load_by_package_id(package_id)
        if loaded is None or not _installable(loaded):
            return PackageActionResult(success=False, error_key="sdk.errors.invalid_manifest")
        self.installed.set_status(package_id=package_id, status=STATUS_ENABLED)
        self.installed.record_validation(
            package_id=package_id,
            manifest_hash=compute_manifest_hash(loaded.raw),
            last_validation_status=VALIDATION_VALID,
        )
        return PackageActionResult(success=True, package_id=package_id)

    def disable(self, *, package_id: str, force: bool = False) -> PackageActionResult:
        record = self.installed.get(package_id)
        if record is None:
            return PackageActionResult(success=False, error_key="sdk.errors.not_installed")
        if not force:
            blocked = self._blocked_by_state(package_id)
            if blocked is not None:
                return blocked
        self.installed.set_status(package_id=package_id, status=STATUS_DISABLED)
        return PackageActionResult(success=True, package_id=package_id)

    def remove(
        self, *, package_id: str, force: bool = False, delete_files: bool = False
    ) -> PackageActionResult:
        record = self.installed.get(package_id)
        if record is None:
            return PackageActionResult(success=False, error_key="sdk.errors.not_installed")
        if not force:
            blocked = self._blocked_by_state(package_id)
            if blocked is not None:
                return blocked
        self.installed.delete(package_id=package_id)
        # ``delete_files`` also deletes the package directory under
        # ``data/packages/{kind}/{id}`` so the package fully disappears (instead
        # of reappearing as "available"). Managed storage
        # (``data/storage/packages/...``) is still preserved.
        if delete_files:
            self._delete_package_files(package_id, kind=str(record["kind"]))
        return PackageActionResult(success=True, package_id=package_id)

    # --- helpers ---------------------------------------------------------------

    @staticmethod
    def _delete_package_files(package_id: str, *, kind: str) -> None:
        package_dir = package_registry.package_dir_for(kind, package_id)
        if package_dir is None:
            return
        try:
            resolved = package_dir.resolve()
            root = package_registry.PACKAGES_DIR.resolve()
        except OSError:
            return
        # Defensive: only ever delete a directory inside the packages root.
        if root not in resolved.parents or not resolved.is_dir():
            return
        shutil.rmtree(resolved, ignore_errors=True)

    def active_dependents(self, package_id: str) -> list[dict]:
        """Enabled packages that declare a dependency on ``package_id``."""
        out: list[dict] = []
        for record in self.installed.list_all():
            if record["status"] != STATUS_ENABLED or record["id"] == package_id:
                continue
            manifest = self.get_manifest(record["id"])
            if manifest is None:
                continue
            if any(dep.id == package_id for dep in manifest.dependencies):
                out.append({"id": record["id"], "kind": record["kind"]})
        return out

    def _blocked_by_state(self, package_id: str) -> PackageActionResult | None:
        """Block a disable/remove that would break active state.

        A package cannot be disabled/removed while it is active in a campaign or
        while another enabled package depends on it (unless ``force``).
        """
        active_campaign_ids = self._active_campaign_ids(package_id)
        if active_campaign_ids:
            return PackageActionResult(
                success=False,
                package_id=package_id,
                error_key="sdk.errors.package_active_in_campaign",
                active_campaign_ids=tuple(active_campaign_ids),
            )
        dependents = self.active_dependents(package_id)
        if dependents:
            return PackageActionResult(
                success=False,
                package_id=package_id,
                error_key="sdk.errors.active_dependents",
                active_dependents=tuple(dependents),
            )
        return None

    def _active_campaign_ids(self, package_id: str) -> list[str]:
        ids = {
            str(row["campaign_id"])
            for row in self.campaign_packages.list_active_for_package(package_id)
        }
        ids.update(str(row["id"]) for row in self.campaigns.list_by_active_system(package_id))
        return sorted(ids)

    def _tab_item(self, loaded: LoadedPackage, record: dict | None) -> dict:
        summary = loaded.manifest.summary(package_dir=loaded.package_dir)
        compat = loaded.validation.compatibility_status
        installable = _installable(loaded)

        if not loaded.validation.ok:
            status = STATUS_ERROR
        elif _is_incompatible(loaded):
            status = STATUS_INCOMPATIBLE
        elif record is not None and record["status"] in _PERSISTED:
            status = record["status"]
        else:
            status = STATUS_AVAILABLE

        return {
            **summary,
            "id": loaded.id,
            "package_id": loaded.id,
            "kind": loaded.manifest.kind,
            "scripted": loaded.manifest.has_scripts(),
            "trusted_code_required": loaded.manifest.has_scripts(),
            "status": status,
            "compatibility_status": compat,
            "validation_errors": list(loaded.validation.errors),
            "validation_warnings": list(loaded.validation.warnings),
            "can_install": installable and record is None,
            "installed": record is not None,
            "enabled": status == STATUS_ENABLED,
        }

    @staticmethod
    def _missing_item(package_id: str, record: dict) -> dict:
        return {
            "id": package_id,
            "package_id": package_id,
            "name": record["name"] or package_id,
            "kind": record["kind"],
            "scripted": False,
            "trusted_code_required": False,
            "version": record["version"],
            "description": "",
            "author": "",
            "color": "",
            "capabilities": [],
            "actor_types": [],
            "item_types": [],
            "area_markers": [],
            "content_packs": [],
            "settings": [],
            "compatibility": {},
            "status": STATUS_ERROR,
            "compatibility_status": COMPAT_INCOMPATIBLE,
            "validation_errors": ["sdk.validation.package_missing"],
            "validation_warnings": [],
            "can_install": False,
            "installed": True,
            "enabled": False,
        }
