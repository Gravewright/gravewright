"""Loads a package's ``locales/{id}.json`` catalog.

A package ships flat ``key -> string`` catalogs so its declarative sheet/rules IR
can reference ``labelKey``/``titleKey`` instead of hard-coding one language.
Resolution mirrors the app i18n fallback (exact locale -> short locale -> ``en``).
"""

from __future__ import annotations

import json

from app.engine.sdk import package_registry
from app.engine.sdk.package_manifest import PackageManifest
from app.engine.sdk.package_paths import safe_join
from app.persistence.repositories.installed_package_repository import (
    InstalledPackageRepository,
)

DEFAULT_LOCALE = "en"


class PackageLocaleService:
    def __init__(self) -> None:
        self.installed = InstalledPackageRepository()

    def get_locale(self, package_id: str, locale: str) -> dict[str, str]:
        record = self.installed.get(package_id)
        if record is None:
            return {}
        try:
            manifest = PackageManifest.from_dict(json.loads(record["manifest_json"]))
        except (TypeError, ValueError):
            return {}

        path = self._pick_locale_path(manifest.locales, locale)
        if not path:
            return {}

        base = package_registry.PACKAGES_DIR / record["package_dir"]
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
