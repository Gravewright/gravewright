"""Scoped settings for SDK packages.

A package declares settings in its manifest (``settings[]``) with a ``scope``
(``global`` / ``campaign`` / ``user``), ``type``, and ``default``. Values are
persisted per scope in ``package_settings``; ``effective_values`` resolves the
default → campaign → user precedence for a given context.
"""

from __future__ import annotations

import json

from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_manifest import PackageSetting
from app.persistence.repositories.package_setting_repository import (
    PackageSettingRepository,
)


class PackageSettingsService:
    def __init__(self) -> None:
        self.install = PackageInstallService()
        self.repo = PackageSettingRepository()

    def _definitions(self, package_id: str) -> list[PackageSetting]:
        manifest = self.install.get_manifest(package_id)
        return list(manifest.settings) if manifest else []

    def definitions(self, package_id: str) -> list[dict]:
        return [s.to_dict() for s in self._definitions(package_id)]

    def _coerce(self, definition: PackageSetting, value: object) -> object:
        if definition.type == "boolean":
            return bool(value)
        if definition.type == "integer":
            try:
                return int(value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return definition.default
        if definition.type == "number":
            try:
                return float(value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return definition.default
        if definition.type == "enum":
            return value if value in definition.options else definition.default
        return str(value) if value is not None else definition.default

    def effective_values(
        self, package_id: str, campaign_id: str | None, user_id: str | None
    ) -> dict:
        values: dict = {}
        for definition in self._definitions(package_id):
            value = definition.default
            stored = self.repo.get(
                package_id=package_id,
                setting_key=definition.key,
                campaign_id=None,
                user_id=None,
            )
            if stored is not None:
                value = json.loads(stored["value_json"])
            # Campaign scope overrides default; user scope overrides campaign.
            if definition.scope in {"campaign", "user"} and campaign_id:
                stored = self.repo.get(
                    package_id=package_id,
                    setting_key=definition.key,
                    campaign_id=campaign_id,
                    user_id=None,
                )
                if stored is not None:
                    value = json.loads(stored["value_json"])
            if definition.scope == "user" and user_id:
                stored = self.repo.get(
                    package_id=package_id,
                    setting_key=definition.key,
                    campaign_id=None,
                    user_id=user_id,
                )
                if stored is not None:
                    value = json.loads(stored["value_json"])
            values[definition.key] = value
        return values

    def get(
        self,
        package_id: str,
        key: str,
        campaign_id: str | None,
        user_id: str | None,
        default: object = None,
    ) -> object:
        return self.effective_values(package_id, campaign_id, user_id).get(key, default)

    def set(
        self,
        package_id: str,
        key: str,
        value: object,
        campaign_id: str | None,
        user_id: str | None,
    ) -> bool:
        definition = next((d for d in self._definitions(package_id) if d.key == key), None)
        if definition is None:
            return False
        coerced = self._coerce(definition, value)
        scope_campaign = campaign_id if definition.scope == "campaign" else None
        scope_user = user_id if definition.scope == "user" else None
        if definition.scope == "campaign" and not campaign_id:
            return False
        if definition.scope == "user" and not user_id:
            return False
        self.repo.set(
            package_id=package_id,
            setting_key=key,
            value_json=json.dumps(coerced),
            campaign_id=scope_campaign,
            user_id=scope_user,
        )
        return True
