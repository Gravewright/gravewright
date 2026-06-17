"""Scoped settings for SDK packages.

A package declares settings in its manifest (``settings[]``) with a ``scope``
(``global`` / ``campaign`` / ``user``), ``type``, and ``default``. Values are
persisted per scope in ``package_settings``; ``effective_values`` resolves the
default → campaign → user precedence for a given context.

Coercion is **explicit and strict** (Phase 4): a value that cannot be coerced to
the declared type is rejected with the stable code ``sdk.settings.invalid_value``
rather than silently falling back to a default or a truthy ``bool("false")``.

Scope semantics:

* ``global``  — one value per package (owner-managed).
* ``campaign`` — one value per package per campaign (GM-managed).
* ``user``    — one value per package per user, **global to that user** (not
  per-campaign): user-scoped rows are keyed by ``user_id`` with an empty
  ``campaign_id``.
"""

from __future__ import annotations

import json

from app.engine.sdk.diagnostics import SdkActionResult, SdkError
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_manifest import PackageSetting
from app.persistence.repositories.package_setting_repository import (
    PackageSettingRepository,
)

SETTING_INVALID_VALUE = "sdk.settings.invalid_value"

# Explicit boolean vocabulary. Anything outside these sets is invalid — we never
# coerce an unrecognised value (the classic ``bool("false") is True`` bug).
_BOOLEAN_TRUE = frozenset({"true", "1", "yes", "on"})
_BOOLEAN_FALSE = frozenset({"false", "0", "no", "off", ""})


class SettingValueError(ValueError):
    """Raised when a value cannot be coerced to a setting's declared type."""

    def __init__(self, setting_key: str, setting_type: str, value: object) -> None:
        super().__init__(f"invalid value for {setting_key!r} ({setting_type})")
        self.error = SdkError(
            code=SETTING_INVALID_VALUE,
            message=f"invalid value for setting {setting_key!r}",
            details={"setting_key": setting_key, "type": setting_type},
        )


def _coerce_boolean(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):  # 0/1 (bool already handled above)
        if value in (0, 1):
            return bool(value)
        raise ValueError(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in _BOOLEAN_TRUE:
            return True
        if token in _BOOLEAN_FALSE:
            return False
    raise ValueError(value)


def _coerce_integer(value: object) -> int:
    if isinstance(value, bool):  # bool is an int subclass; reject it explicitly
        raise ValueError(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ValueError(value)
    if isinstance(value, str):
        return int(value.strip())  # raises ValueError on non-integer text
    raise ValueError(value)


def _coerce_number(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value.strip())
    raise ValueError(value)


def coerce_setting_value(definition: PackageSetting, value: object) -> object:
    """Coerce ``value`` to ``definition.type`` or raise :class:`SettingValueError`."""
    try:
        if definition.type == "boolean":
            return _coerce_boolean(value)
        if definition.type == "integer":
            return _coerce_integer(value)
        if definition.type == "number":
            return _coerce_number(value)
        if definition.type == "enum":
            if value in definition.options:
                return value
            raise ValueError(value)
        # string
        if value is None:
            raise ValueError(value)
        return str(value)
    except (TypeError, ValueError) as exc:
        raise SettingValueError(definition.key, definition.type, value) from exc


def _parse_stored(value_json: str, default: object) -> object:
    """Parse a stored value, falling back to ``default`` on corruption."""
    try:
        return json.loads(value_json)
    except (TypeError, ValueError):
        return default


class PackageSettingsService:
    def __init__(self) -> None:
        self.install = PackageInstallService()
        self.repo = PackageSettingRepository()

    def _definitions(self, package_id: str) -> list[PackageSetting]:
        manifest = self.install.get_manifest(package_id)
        return list(manifest.settings) if manifest else []

    def definitions(self, package_id: str) -> list[dict]:
        return [s.to_dict() for s in self._definitions(package_id)]

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
                value = _parse_stored(stored["value_json"], definition.default)
            # Campaign scope overrides default; user scope overrides campaign.
            if definition.scope in {"campaign", "user"} and campaign_id:
                stored = self.repo.get(
                    package_id=package_id,
                    setting_key=definition.key,
                    campaign_id=campaign_id,
                    user_id=None,
                )
                if stored is not None:
                    value = _parse_stored(stored["value_json"], definition.default)
            if definition.scope == "user" and user_id:
                stored = self.repo.get(
                    package_id=package_id,
                    setting_key=definition.key,
                    campaign_id=None,
                    user_id=user_id,
                )
                if stored is not None:
                    value = _parse_stored(stored["value_json"], definition.default)
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
    ) -> SdkActionResult:
        definition = next((d for d in self._definitions(package_id) if d.key == key), None)
        if definition is None:
            return SdkActionResult.fail(
                SdkError(
                    code="sdk.settings.invalid_value",
                    message=f"unknown setting {key!r}",
                    details={"setting_key": key, "reason": "unknown"},
                    package_id=package_id,
                )
            )
        if definition.scope == "campaign" and not campaign_id:
            return SdkActionResult.fail(
                SdkError(
                    code="sdk.settings.invalid_value",
                    message="campaign-scoped setting requires a campaign",
                    details={"setting_key": key, "reason": "missing_campaign"},
                    package_id=package_id,
                )
            )
        if definition.scope == "user" and not user_id:
            return SdkActionResult.fail(
                SdkError(
                    code="sdk.settings.invalid_value",
                    message="user-scoped setting requires a user",
                    details={"setting_key": key, "reason": "missing_user"},
                    package_id=package_id,
                )
            )
        try:
            coerced = coerce_setting_value(definition, value)
        except SettingValueError as exc:
            error = SdkError(
                code=exc.error.code,
                message=exc.error.message,
                details=exc.error.details,
                package_id=package_id,
                campaign_id=campaign_id,
            )
            return SdkActionResult.fail(error)

        scope_campaign = campaign_id if definition.scope == "campaign" else None
        scope_user = user_id if definition.scope == "user" else None
        self.repo.set(
            package_id=package_id,
            setting_key=key,
            value_json=json.dumps(coerced),
            campaign_id=scope_campaign,
            user_id=scope_user,
        )
        return SdkActionResult.ok(package_id=package_id, campaign_id=campaign_id)
