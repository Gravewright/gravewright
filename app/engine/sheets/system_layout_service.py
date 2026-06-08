"""Loads an actor type's declarative Sheet IR from its system package (§8.1)."""

from __future__ import annotations

import json

from app.config import config
from app.engine.sheets.sheet_localizer import localize_layout
from app.engine.systems import system_loader
from app.engine.systems.system_loader import safe_join
from app.engine.systems.system_manifest import SystemManifest
from app.engine.systems.system_locale_service import SystemLocaleService
from app.persistence.repositories.installed_system_repository import InstalledSystemRepository


class SystemLayoutService:
    def __init__(self) -> None:
        self.installed = InstalledSystemRepository()
        self.locales = SystemLocaleService()

    def get_actor_sheet(self, *, system_id: str, actor_type: str, locale: str | None = None) -> dict | None:
        return self._get_sheet(system_id=system_id, type_id=actor_type, kind="actor", locale=locale)

    def get_item_sheet(self, *, system_id: str, item_type: str, locale: str | None = None) -> dict | None:
        return self._get_sheet(system_id=system_id, type_id=item_type, kind="item", locale=locale)

    def _get_sheet(self, *, system_id: str, type_id: str, kind: str, locale: str | None) -> dict | None:
        record = self.installed.get(system_id)
        if record is None:
            return None
        try:
            manifest = SystemManifest.from_dict(json.loads(record["manifest_json"]))
        except (TypeError, ValueError):
            return None

        type_defs = manifest.item_types if kind == "item" else manifest.actor_types
        sheet_path = ""
        for type_def in type_defs:
            if type_def.id == type_id:
                sheet_path = type_def.sheet
                break
        if not sheet_path:
            return None

        base = system_loader.SYSTEMS_DIR / record["package_dir"]
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
