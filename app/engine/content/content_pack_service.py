"""Read-only Content Pack access (Gravewright SDK, §10).

Content packs are declared in the manifest (``contentPacks``) and live as JSON
files in the package. They are read-only catalogues — when the GM uses an entry
the core copies it into the campaign (via ``sheet.drop`` / ``content.entry.import``).
"""

from __future__ import annotations

import json

from app.engine.sdk import package_registry
from app.engine.sdk.package_paths import safe_join
from app.engine.sdk.package_manifest import PackageManifest
from app.persistence.repositories.installed_package_repository import InstalledPackageRepository


class ContentPackService:
    def __init__(self) -> None:
        self.installed = InstalledPackageRepository()

    def _record_and_manifest(self, system_id: str) -> tuple[dict, SystemManifest] | None:
        record = self.installed.get(system_id)
        if record is None:
            return None
        try:
            manifest = PackageManifest.from_dict(json.loads(record["manifest_json"]))
        except (TypeError, ValueError):
            return None
        return record, manifest

    def list_packs(self, system_id: str) -> list[dict]:
        pair = self._record_and_manifest(system_id)
        if pair is None:
            return []
        record, manifest = pair
        package_dir = package_registry.PACKAGES_DIR / record["package_dir"]
        locale_data = manifest.load_locale(package_dir, "en")
        return [
            {
                "id": pack.id,
                "type": pack.type,
                "label": manifest._resolve_label(pack.label, pack.label_key, locale_data),
            }
            for pack in manifest.content_packs
        ]

    def _read_pack_file(self, package_dir: str, relative: str) -> dict | None:
        base = package_registry.PACKAGES_DIR / package_dir
        path = safe_join(base, relative)
        if path is None or not path.is_file():
            return None
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return parsed if isinstance(parsed, dict) else None

    def get_pack(self, system_id: str, pack_id: str) -> dict | None:
        pair = self._record_and_manifest(system_id)
        if pair is None:
            return None
        record, manifest = pair
        ref = next((p for p in manifest.content_packs if p.id == pack_id), None)
        if ref is None:
            return None
        parsed = self._read_pack_file(record["package_dir"], ref.path)
        if parsed is None:
            return None
        entries = parsed.get("entries")
        package_dir = package_registry.PACKAGES_DIR / record["package_dir"]
        locale_data = manifest.load_locale(package_dir, "en")
        return {
            "id": pack_id,
            "type": ref.type,
            "label": manifest._resolve_label(ref.label, ref.label_key, locale_data),
            "entries": [e for e in entries if isinstance(e, dict)] if isinstance(entries, list) else [],
        }

    def get_entry(self, system_id: str, pack_id: str, entry_id: str) -> dict | None:
        pack = self.get_pack(system_id, pack_id)
        if pack is None:
            return None
        return next((e for e in pack["entries"] if e.get("id") == entry_id), None)
