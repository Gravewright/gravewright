"""Package-backed, read-only document libraries with lazy format-2 documents."""
from __future__ import annotations

from collections import OrderedDict
import json
from pathlib import Path
from urllib.parse import quote

from app.engine.sdk import package_registry
from app.engine.sdk.package_paths import safe_join
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_manifest import PackageContentPack, PackageManifest
from app.persistence.repositories.installed_package_repository import InstalledPackageRepository

DEFAULT_INDEX_FIELDS = ("id", "name", "title", "type", "img", "image", "folder", "tags")
MAX_PAGE_SIZE = 200


class ContentPackService:
    def __init__(self) -> None:
        self.installed = InstalledPackageRepository()
        self.install = PackageInstallService()
        self._cache: OrderedDict[str, tuple[int, dict]] = OrderedDict()

    def _record_and_manifest(self, package_id: str) -> tuple[dict, PackageManifest] | None:
        record = self.installed.get(package_id)
        manifest = self.install.get_manifest(package_id) if record else None
        return (record, manifest) if record and manifest else None

    @staticmethod
    def canonical_ref(package_id: str, pack_id: str, entry_id: str) -> str:
        values = (quote(value, safe="-._~") for value in (package_id, pack_id, entry_id))
        return "gwpack://" + "/".join(values)

    @staticmethod
    def _metadata(manifest: PackageManifest, pack: PackageContentPack, locale: dict) -> dict:
        return {"id": pack.id, "type": pack.type,
                "document_type": pack.document_type or pack.type.removesuffix("_pack"),
                "format_version": pack.format_version,
                "index_fields": list(pack.index_fields or DEFAULT_INDEX_FIELDS),
                "label": manifest._resolve_label(pack.label, pack.label_key, locale)}

    def list_packs(self, package_id: str) -> list[dict]:
        pair = self._record_and_manifest(package_id)
        if pair is None:
            return []
        record, manifest = pair
        base = package_registry.PACKAGES_DIR / record["package_dir"]
        locale = manifest.load_locale(base, "en")
        return [self._metadata(manifest, pack, locale) for pack in manifest.content_packs]

    def _read_json(self, base: Path, relative: str) -> dict | None:
        path = safe_join(base, relative)
        if path is None or not path.is_file():
            return None
        try:
            stamp, key = path.stat().st_mtime_ns, str(path)
            cached = self._cache.get(key)
            if cached and cached[0] == stamp:
                self._cache.move_to_end(key)
                return cached[1]
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(parsed, dict):
            return None
        self._cache[key] = (stamp, parsed)
        while len(self._cache) > 32:
            self._cache.popitem(last=False)
        return parsed

    def _source(self, package_id: str, pack_id: str):
        pair = self._record_and_manifest(package_id)
        if pair is None:
            return None
        record, manifest = pair
        ref = next((pack for pack in manifest.content_packs if pack.id == pack_id), None)
        if ref is None:
            return None
        base = package_registry.PACKAGES_DIR / record["package_dir"]
        parsed = self._read_json(base, ref.path)
        return (base, manifest, ref, parsed) if parsed is not None else None

    def get_index(self, package_id: str, pack_id: str, *, query: str = "", offset: int = 0,
                  limit: int = 50) -> dict | None:
        source = self._source(package_id, pack_id)
        if source is None:
            return None
        base, manifest, ref, parsed = source
        raw = parsed.get("index", parsed.get("entries", []))
        fields, needle, indexed = tuple(ref.index_fields or DEFAULT_INDEX_FIELDS), query.casefold().strip(), []
        for entry in raw if isinstance(raw, list) else []:
            if not isinstance(entry, dict) or not str(entry.get("id") or ""):
                continue
            entry_id = str(entry["id"])
            item = {field: entry[field] for field in fields if field in entry}
            item.update({"id": entry_id,
                         "document_type": ref.document_type or ref.type.removesuffix("_pack"),
                         "ref": self.canonical_ref(package_id, pack_id, entry_id)})
            if not needle or needle in " ".join(str(value) for value in item.values()).casefold():
                indexed.append(item)
        offset, limit = max(0, int(offset)), min(MAX_PAGE_SIZE, max(1, int(limit)))
        page = indexed[offset:offset + limit]
        locale = manifest.load_locale(base, "en")
        return {**self._metadata(manifest, ref, locale), "entries": page, "total": len(indexed),
                "offset": offset, "limit": limit, "has_more": offset + len(page) < len(indexed)}

    def get_entry(self, package_id: str, pack_id: str, entry_id: str) -> dict | None:
        source = self._source(package_id, pack_id)
        if source is None:
            return None
        base, _manifest, ref, parsed = source
        raw = parsed.get("index", parsed.get("entries", []))
        entry = next((value for value in raw if isinstance(value, dict)
                      and str(value.get("id") or "") == entry_id), None) if isinstance(raw, list) else None
        if entry is None:
            return None
        document_path = entry.get("document")
        if isinstance(document_path, str) and document_path:
            document = self._read_json(base, document_path)
            if document is None:
                return None
            entry = {**entry, **document, "id": entry_id}
        return {**entry, "document_type": ref.document_type or ref.type.removesuffix("_pack"),
                "ref": self.canonical_ref(package_id, pack_id, entry_id)}

    def get_pack(self, package_id: str, pack_id: str) -> dict | None:
        """Compatibility view; new callers should use get_index/get_entry."""
        result = self.get_index(package_id, pack_id, limit=MAX_PAGE_SIZE)
        source = self._source(package_id, pack_id)
        if result is not None and source and "index" not in source[3]:
            result["entries"] = [entry for item in result["entries"]
                                 if (entry := self.get_entry(package_id, pack_id, item["id"]))]
        return result
