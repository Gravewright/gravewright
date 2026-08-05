"""Loads an actor type's declarative Sheet IR from its system package (§8.1)."""

from __future__ import annotations

import json

from app.config import config
from app.engine.sheets.sheet_localizer import localize_layout
from app.engine.sdk import package_registry
from app.engine.sdk.package_paths import safe_join
from app.engine.sdk.package_manifest import PackageManifest
from app.engine.sdk.package_locale_service import PackageLocaleService
from app.persistence.repositories.installed_package_repository import InstalledPackageRepository


class SystemLayoutService:
    def __init__(self) -> None:
        self.installed = InstalledPackageRepository()
        self.locales = PackageLocaleService()

    def get_actor_sheet(self, *, system_id: str, actor_type: str, locale: str | None = None) -> dict | None:
        return self._get_sheet(system_id=system_id, type_id=actor_type, kind="actor", locale=locale)

    def get_item_sheet(self, *, system_id: str, item_type: str, locale: str | None = None) -> dict | None:
        return self._get_sheet(system_id=system_id, type_id=item_type, kind="item", locale=locale)

    def get_actor_html_sheet(self, *, system_id: str, actor_type: str) -> dict | None:
        return self._get_html_sheet(system_id=system_id, type_id=actor_type, kind="actor")

    def get_item_html_sheet(self, *, system_id: str, item_type: str) -> dict | None:
        return self._get_html_sheet(system_id=system_id, type_id=item_type, kind="item")

    def _manifest_for(self, system_id: str) -> PackageManifest | None:
        record = self.installed.get(system_id)
        if record is None:
            return None
        try:
            return PackageManifest.from_dict(json.loads(record["manifest_json"]))
        except (TypeError, ValueError):
            return None

    def _type_def(self, *, system_id: str, type_id: str, kind: str):
        manifest = self._manifest_for(system_id)
        if manifest is None:
            return None
        type_defs = manifest.item_types if kind == "item" else manifest.actor_types
        for type_def in type_defs:
            if type_def.id == type_id:
                return type_def
        return None

    def _get_html_sheet(self, *, system_id: str, type_id: str, kind: str) -> dict | None:
        type_def = self._type_def(system_id=system_id, type_id=type_id, kind=kind)
        return type_def.html_sheet if type_def is not None else None

    def _get_sheet(self, *, system_id: str, type_id: str, kind: str, locale: str | None) -> dict | None:
        type_def = self._type_def(system_id=system_id, type_id=type_id, kind=kind)
        if type_def is None:
            return None
        # HTML-mode sheets are not declarative Sheet IR; they are served as
        # templates and mounted client-side (see ``get_*_html_sheet``).
        if type_def.html_sheet is not None:
            return None
        sheet_path = type_def.sheet_path
        if not sheet_path:
            return None
        record = self.installed.get(system_id)
        if record is None:
            return None

        base = package_registry.PACKAGES_DIR / record["package_dir"]
        path = safe_join(base, sheet_path)
        if path is None or not path.is_file():
            return None
        try:
            layout = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(layout, dict):
            return None
        catalog = self.locales.get_locale(system_id, locale or config.default_locale)
        return localize_layout(layout, catalog)
