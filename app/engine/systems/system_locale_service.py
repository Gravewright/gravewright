"""Loads a system package's ``locales/{id}.json`` catalog (System API v0).

A system ships flat ``key -> string`` catalogs so its Sheet IR can reference
``labelKey``/``titleKey`` instead of hard-coding a single language. Resolution
mirrors the app i18n fallback (exact locale → short locale → ``en``). Read on
demand; files are small.
"""

from __future__ import annotations

import json

from app.engine.systems import system_loader
from app.engine.systems.system_loader import safe_join
from app.engine.systems.system_manifest import SystemManifest
from app.persistence.repositories.installed_system_repository import InstalledSystemRepository

DEFAULT_LOCALE = "en"


class SystemLocaleService:
    def __init__(self) -> None:
        self.installed = InstalledSystemRepository()

    def get_locale(self, system_id: str, locale: str) -> dict[str, str]:
        record = self.installed.get(system_id)
        if record is None:
            return {}
        try:
            manifest = SystemManifest.from_dict(json.loads(record["manifest_json"]))
        except (TypeError, ValueError):
            return {}

        path = self._pick_locale_path(manifest.locales, locale)
        if not path:
            return {}

        base = system_loader.SYSTEMS_DIR / record["package_dir"]
        resolved = safe_join(base, path)
        if resolved is None or not resolved.is_file():
            return {}
        try:
            catalog = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(catalog, dict):
            return {}
        return {str(k): str(v) for k, v in catalog.items() if isinstance(v, str)}

    @staticmethod
    def _pick_locale_path(locales: dict[str, str], locale: str) -> str:
        if not isinstance(locales, dict):
            return ""
        if locale in locales:
            return locales[locale]
        short = locale.split("-", 1)[0] if locale else ""
        if short and short in locales:
            return locales[short]
        return locales.get(DEFAULT_LOCALE, "")
