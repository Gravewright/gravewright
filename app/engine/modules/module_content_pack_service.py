"""Read-only access to content packs declared by installed modules."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.engine.modules import module_loader
from app.engine.modules.module_manifest import ModuleManifest
from app.engine.systems.system_loader import safe_join
from app.persistence.repositories.campaign_module_repository import CampaignModuleRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.installed_module_repository import InstalledModuleRepository

_STATUS_ENABLED = "enabled"
_IMPORTABLE_PACK_TYPES = {"actor_pack", "item_pack", "spell_pack", "journal_pack"}
_MAX_PACK_BYTES = 2_000_000
_MAX_PACK_ENTRIES = 1_000


@dataclass(frozen=True)
class ModulePackRef:
    id: str
    type: str
    label: str
    path: str


def _str(value: object) -> str:
    return value if isinstance(value, str) else ""


def _pack_ref(raw: object) -> ModulePackRef | None:
    if not isinstance(raw, dict):
        return None
    pack_id = _str(raw.get("id"))
    pack_type = _str(raw.get("type"))
    label = _str(raw.get("label")) or pack_id
    path = _str(raw.get("path"))
    if not (pack_id and pack_type and path):
        return None
    return ModulePackRef(id=pack_id, type=pack_type, label=label, path=path)


class ModuleContentPackService:
    def __init__(self) -> None:
        self.installed = InstalledModuleRepository()
        self.campaign_modules = CampaignModuleRepository()
        self.campaigns = CampaignRepository()

    def _record_and_manifest(self, *, campaign_id: str, module_id: str, user_id: str | None = None) -> tuple[dict, ModuleManifest] | None:
        if user_id is None or self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id) is None:
            return None
        record = self.installed.get(module_id)
        if record is None or record.get("status") != _STATUS_ENABLED:
            return None
        if not self.campaign_modules.is_enabled(campaign_id=campaign_id, module_id=module_id):
            return None
        try:
            manifest = ModuleManifest.from_dict(json.loads(record["manifest_json"]))
        except (TypeError, ValueError):
            return None
        if "content.packs" not in set(manifest.capabilities):
            return None
        return record, manifest

    def list_packs(self, *, campaign_id: str, module_id: str, user_id: str | None = None) -> list[dict]:
        pair = self._record_and_manifest(campaign_id=campaign_id, module_id=module_id, user_id=user_id)
        if pair is None:
            return []
        _, manifest = pair
        out: list[dict] = []
        for raw in manifest.content_packs:
            ref = _pack_ref(raw)
            if ref is None or ref.type not in _IMPORTABLE_PACK_TYPES:
                continue
            out.append({"id": ref.id, "type": ref.type, "label": ref.label, "module_id": manifest.id})
        return out

    def _read_pack_file(self, *, package_dir: str, relative: str) -> dict | None:
        base = module_loader.MODULES_DIR / package_dir
        path = safe_join(base, relative)
        if path is None or not path.is_file():
            return None
        try:
            if path.stat().st_size > _MAX_PACK_BYTES:
                return None
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return parsed if isinstance(parsed, dict) else None

    def get_pack(self, *, campaign_id: str, module_id: str, pack_id: str, user_id: str | None = None) -> dict | None:
        pair = self._record_and_manifest(campaign_id=campaign_id, module_id=module_id, user_id=user_id)
        if pair is None:
            return None
        record, manifest = pair
        ref = next((candidate for candidate in (_pack_ref(p) for p in manifest.content_packs) if candidate and candidate.id == pack_id), None)
        if ref is None or ref.type not in _IMPORTABLE_PACK_TYPES:
            return None
        parsed = self._read_pack_file(package_dir=record["package_dir"], relative=ref.path)
        if parsed is None:
            return None
        entries = parsed.get("entries")
        if not isinstance(entries, list):
            entries = []
        clean_entries = [entry for entry in entries if isinstance(entry, dict)][: _MAX_PACK_ENTRIES]
        return {
            "id": ref.id,
            "type": ref.type,
            "label": ref.label,
            "module_id": manifest.id,
            "entries": clean_entries,
        }

    def get_entry(self, *, campaign_id: str, module_id: str, pack_id: str, entry_id: str, user_id: str | None = None) -> dict | None:
        pack = self.get_pack(campaign_id=campaign_id, module_id=module_id, pack_id=pack_id, user_id=user_id)
        if pack is None:
            return None
        return next((entry for entry in pack["entries"] if entry.get("id") == entry_id), None)
