from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.roles import PlayerRole, SystemRole
from app.engine.modules.module_install_service import STATUS_ENABLED
from app.engine.modules.module_manifest import ModuleManifest
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.installed_module_repository import InstalledModuleRepository
from app.persistence.repositories.module_setting_repository import ModuleSettingRepository

SETTING_SCOPES = {"global", "campaign", "user"}
SETTING_TYPES = {"boolean", "string", "number", "integer", "enum"}


@dataclass(frozen=True)
class ModuleSettingResult:
    success: bool
    module_id: str | None = None
    setting_key: str | None = None
    value: Any = None
    error_key: str | None = None


def setting_key(definition: dict) -> str:
    return str(definition.get("key") or definition.get("id") or "").strip()


def setting_scope(definition: dict) -> str:
    scope = str(definition.get("scope") or "campaign").strip().lower()
    return scope if scope in SETTING_SCOPES else "campaign"


def setting_type(definition: dict) -> str:
    type_name = str(definition.get("type") or "string").strip().lower()
    return type_name if type_name in SETTING_TYPES else "string"


def setting_default(definition: dict) -> object:
    if "default" in definition:
        return definition.get("default")
    type_name = setting_type(definition)
    if type_name == "boolean":
        return False
    if type_name in {"number", "integer"}:
        return 0
    return ""


def enum_values(definition: dict) -> list[str]:
    raw = definition.get("choices", definition.get("options", []))
    if not isinstance(raw, list):
        return []
    values: list[str] = []
    for entry in raw:
        if isinstance(entry, dict):
            value = entry.get("value")
        else:
            value = entry
        if isinstance(value, str) and value:
            values.append(value)
    return values


def coerce_setting_value(definition: dict, raw_value: object) -> object:
    type_name = setting_type(definition)
    if type_name == "boolean":
        if isinstance(raw_value, bool):
            return raw_value
        text = str(raw_value).strip().lower()
        return text in {"1", "true", "yes", "on"}
    if type_name == "integer":
        return int(raw_value)
    if type_name == "number":
        return float(raw_value)
    if type_name == "enum":
        value = str(raw_value)
        allowed = enum_values(definition)
        if value not in allowed:
            raise ValueError("enum value is not allowed")
        return value
    value = "" if raw_value is None else str(raw_value)
    max_length = definition.get("maxLength")
    if isinstance(max_length, int) and max_length > 0:
        value = value[:max_length]
    return value


def _definition_by_key(manifest: ModuleManifest, key: str) -> dict | None:
    for definition in manifest.settings:
        if setting_key(definition) == key:
            return definition
    return None


class ModuleSettingsService:
    def __init__(self) -> None:
        self.installed = InstalledModuleRepository()
        self.values = ModuleSettingRepository()
        self.campaigns = CampaignRepository()

    def _manifest_for_enabled_module(self, module_id: str) -> ModuleManifest | None:
        record = self.installed.get(module_id)
        if record is None or record.get("status") != STATUS_ENABLED:
            return None
        import json

        try:
            return ModuleManifest.from_dict(json.loads(record["manifest_json"]))
        except (TypeError, ValueError):
            return None

    def effective_values(self, *, manifest: ModuleManifest, campaign_id: str | None, user_id: str | None) -> dict[str, object]:
        out: dict[str, object] = {}
        loaded: dict[tuple[str, str], dict[str, object]] = {}

        def values_for(scope: str, subject_id: str) -> dict[str, object]:
            key = (scope, subject_id or "")
            if key not in loaded:
                loaded[key] = self.values.get_values(module_id=manifest.id, scope=scope, subject_id=subject_id)
            return loaded[key]

        for definition in manifest.settings:
            key = setting_key(definition)
            if not key:
                continue
            scope = setting_scope(definition)
            subject_id = ""
            if scope == "campaign":
                subject_id = campaign_id or ""
            elif scope == "user":
                subject_id = user_id or ""
            stored = values_for(scope, subject_id).get(key)
            out[key] = stored if stored is not None else setting_default(definition)
        return out

    def set_value(
        self,
        *,
        module_id: str,
        setting_key_value: str,
        raw_value: object,
        user_id: str,
        user_system_role: str,
        campaign_id: str | None = None,
    ) -> ModuleSettingResult:
        manifest = self._manifest_for_enabled_module(module_id)
        if manifest is None:
            return ModuleSettingResult(success=False, error_key="inside.modules.errors.not_installed")
        if "settings" not in set(manifest.capabilities):
            return ModuleSettingResult(success=False, error_key="inside.modules.settings.errors.capability_required")
        definition = _definition_by_key(manifest, setting_key_value)
        if definition is None:
            return ModuleSettingResult(success=False, error_key="inside.modules.settings.errors.unknown")
        scope = setting_scope(definition)
        subject_id = ""
        if scope == "global":
            if user_system_role != SystemRole.OWNER.value:
                return ModuleSettingResult(success=False, error_key="inside.modules.settings.errors.owner_required")
        elif scope == "campaign":
            if not campaign_id:
                return ModuleSettingResult(success=False, error_key="inside.modules.settings.errors.campaign_required")
            campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
            if campaign is None:
                return ModuleSettingResult(success=False, error_key="inside.campaigns.errors.not_found")
            if campaign.get("member_role") != PlayerRole.GM.value:
                return ModuleSettingResult(success=False, error_key="inside.campaigns.errors.gm_required")
            subject_id = campaign_id
        elif scope == "user":
            subject_id = user_id
        try:
            value = coerce_setting_value(definition, raw_value)
        except (TypeError, ValueError):
            return ModuleSettingResult(success=False, error_key="inside.modules.settings.errors.invalid_value")
        self.values.upsert_value(
            module_id=module_id,
            scope=scope,
            subject_id=subject_id,
            setting_key=setting_key_value,
            value=value,
            updated_by_user_id=user_id,
        )
        return ModuleSettingResult(success=True, module_id=module_id, setting_key=setting_key_value, value=value)
