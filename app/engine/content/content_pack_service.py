"""Read-only Content Pack access (System API v0, §10).

Content packs are declared in the manifest (``contentPacks``) and live as JSON
files in the package. They are read-only catalogues — when the GM uses an entry
the core copies it into the campaign (via ``sheet.drop`` / ``content.entry.import``).
"""

from __future__ import annotations

import json

from app.engine.systems import system_loader
from app.engine.systems.system_loader import safe_join
from app.engine.systems.system_manifest import SystemManifest
from app.persistence.repositories.installed_system_repository import InstalledSystemRepository


class ContentPackService:
    def __init__(self) -> None:
        self.installed = InstalledSystemRepository()

    def _record_and_manifest(self, system_id: str) -> tuple[dict, SystemManifest] | None:
        record = self.installed.get(system_id)
        if record is None:
            return None
        try:
            manifest = SystemManifest.from_dict(json.loads(record["manifest_json"]))
        except (TypeError, ValueError):
            return None
        return record, manifest

    def list_packs(self, system_id: str) -> list[dict]:
        pair = self._record_and_manifest(system_id)
        if pair is None:
            return []
        record, manifest = pair
        package_dir = system_loader.SYSTEMS_DIR / record["package_dir"]
        locale_data = manifest._load_locale(package_dir, "en")
        return [
            {
                "id": pack.id,
                "type": pack.type,
                "label": manifest._resolve_label(pack.label, pack.label_key, locale_data),
            }
            for pack in manifest.content_packs
        ]

    def _read_pack_file(self, package_dir: str, relative: str) -> dict | None:
        base = system_loader.SYSTEMS_DIR / package_dir
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
        package_dir = system_loader.SYSTEMS_DIR / record["package_dir"]
        locale_data = manifest._load_locale(package_dir, "en")
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
