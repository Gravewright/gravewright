"""Validation rules for Module Manifests (Module API v1)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config import config
from app.engine.modules.module_manifest import ENTRYPOINT_CONTEXTS, ENTRYPOINT_KINDS, SUPPORTED_SCHEMA_VERSION
from app.engine.modules.module_manifest import ModuleManifest

ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

KNOWN_CAPABILITIES = {
    "assets.ui",
    "assets.styles",
    "assets.scripts",
    "chat.cards",
    "content.packs",
    "hooks.client",
    "locales",
    "settings",
    "sheets.extends",
    "rules.extends",
    "tokens.extends",
}

FORBIDDEN_CAPABILITIES = {
    "backend.execute",
    "database.raw",
    "filesystem.raw",
    "network.raw",
    "permissions.override",
}

CONTENT_PACK_TYPES = {
    "actor_pack",
    "item_pack",
    "spell_pack",
    "journal_pack",
}

MAX_ENTRYPOINT_STYLES = 16
MAX_ENTRYPOINT_SCRIPTS = 16
MAX_MODULE_SETTINGS = 64
MAX_MODULE_CONTENT_PACKS = 32
MAX_MODULE_RELATIONSHIPS = 32
MIN_MODULE_LOAD_ORDER = -10000
MAX_MODULE_LOAD_ORDER = 10000
MAX_CONTENT_PACK_LABEL_LENGTH = 120
MAX_SETTING_KEY_LENGTH = 96
MAX_DECLARED_ASSET_PATHS = 64
MAX_ASSET_PATH_LENGTH = 240
MAX_ASSET_BYTES = 2_000_000
STYLE_EXTENSIONS = {".css"}
SCRIPT_EXTENSIONS = {".js", ".mjs"}
SETTING_SCOPES = {"global", "campaign", "user"}
SETTING_TYPES = {"boolean", "string", "number", "integer", "enum"}
SETTING_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")

COMPAT_COMPATIBLE = "compatible"
COMPAT_UNVERIFIED = "unverified"
COMPAT_INCOMPATIBLE = "incompatible"

_BIG = 1_000_000


@dataclass
class ManifestValidation:
    errors: list[str] = field(default_factory=list)
    compatibility_status: str = COMPAT_UNVERIFIED

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, error_key: str) -> None:
        if error_key not in self.errors:
            self.errors.append(error_key)


def _version_key(version: str) -> tuple[int, int, int, int]:
    version = (version or "").strip()
    is_release = "-" not in version
    core = version.split("-", 1)[0]
    parts = core.split(".")

    def part(index: int) -> int:
        if index >= len(parts):
            return 0
        token = parts[index]
        if token in {"x", "*"}:
            return _BIG
        try:
            return int(token)
        except ValueError:
            return 0

    return (part(0), part(1), part(2), 1 if is_release else 0)


def compute_compatibility_status(manifest: ModuleManifest) -> str:
    current = _version_key(config.gravewright_version)
    minimum = manifest.compatibility.minimum
    maximum = manifest.compatibility.maximum
    verified = manifest.compatibility.verified

    if minimum and current < _version_key(minimum):
        return COMPAT_INCOMPATIBLE
    if maximum and current > _version_key(maximum):
        return COMPAT_INCOMPATIBLE
    if verified and _version_key(verified) == current:
        return COMPAT_COMPATIBLE
    return COMPAT_UNVERIFIED


def _path_is_safe(path: str) -> bool:
    if not path or not isinstance(path, str):
        return False
    if len(path) > MAX_ASSET_PATH_LENGTH:
        return False
    if "\\" in path or "://" in path:
        return False
    if path.startswith("/") or re.match(r"^[a-zA-Z]:", path):
        return False
    segments = path.split("/")
    return ".." not in segments and "" not in segments[:-1]


def _suffix(path: str) -> str:
    slash = path.rsplit("/", 1)[-1]
    if "." not in slash:
        return ""
    return "." + slash.rsplit(".", 1)[-1].lower()


def _validate_entrypoints(raw_module: object, manifest: ModuleManifest, result: ManifestValidation) -> None:
    module = raw_module if isinstance(raw_module, dict) else {}
    entrypoints_raw = module.get("entrypoints")
    if "assets" in module:
        result.add("inside.modules.validation.assets_legacy")
    if entrypoints_raw is None:
        if {"assets.ui", "assets.styles", "assets.scripts", "hooks.client"} & set(manifest.capabilities):
            result.add("inside.modules.validation.entrypoints_required")
        return
    if not isinstance(entrypoints_raw, dict):
        result.add("inside.modules.validation.entrypoints_invalid")
        return

    declared: list[str] = []
    for context, entrypoint in entrypoints_raw.items():
        if context not in ENTRYPOINT_CONTEXTS:
            result.add("inside.modules.validation.entrypoint_unknown")
            continue
        if not isinstance(entrypoint, dict):
            result.add("inside.modules.validation.entrypoint_invalid")
            continue
        for key in entrypoint:
            if key not in ENTRYPOINT_KINDS:
                result.add("inside.modules.validation.entrypoint_unknown")
        styles = entrypoint.get("styles", [])
        scripts = entrypoint.get("scripts", [])
        if styles is not None and not isinstance(styles, list):
            result.add("inside.modules.validation.entrypoint_invalid")
            styles = []
        if scripts is not None and not isinstance(scripts, list):
            result.add("inside.modules.validation.entrypoint_invalid")
            scripts = []
        if len(styles) > MAX_ENTRYPOINT_STYLES or len(scripts) > MAX_ENTRYPOINT_SCRIPTS:
            result.add("inside.modules.validation.asset_limit")
        for path in styles:
            if not isinstance(path, str):
                result.add("inside.modules.validation.entrypoint_invalid")
                continue
            declared.append(path)
            if _suffix(path) not in STYLE_EXTENSIONS:
                result.add("inside.modules.validation.asset_type")
        for path in scripts:
            if not isinstance(path, str):
                result.add("inside.modules.validation.entrypoint_invalid")
                continue
            declared.append(path)
            if _suffix(path) not in SCRIPT_EXTENSIONS:
                result.add("inside.modules.validation.asset_type")

    if len(declared) > MAX_DECLARED_ASSET_PATHS:
        result.add("inside.modules.validation.asset_limit")
    if len(set(declared)) != len(declared):
        result.add("inside.modules.validation.asset_duplicate")
    for path in declared:
        if len(path) > MAX_ASSET_PATH_LENGTH:
            result.add("inside.modules.validation.asset_path_too_long")


def _validate_settings(manifest: ModuleManifest, result: ManifestValidation) -> None:
    if len(manifest.settings) > MAX_MODULE_SETTINGS:
        result.add("inside.modules.validation.settings_limit")
        return
    seen: set[str] = set()
    for setting in manifest.settings:
        key = setting.get("key") or setting.get("id")
        key_valid = isinstance(key, str) and bool(key) and len(key) <= MAX_SETTING_KEY_LENGTH and bool(SETTING_KEY_PATTERN.match(key))
        if not key_valid:
            result.add("inside.modules.validation.setting_key")
        elif key in seen:
            result.add("inside.modules.validation.setting_duplicate")
        elif isinstance(key, str):
            seen.add(key)
        scope = str(setting.get("scope") or "campaign").lower()
        if scope not in SETTING_SCOPES:
            result.add("inside.modules.validation.setting_scope")
        type_name = str(setting.get("type") or "string").lower()
        if type_name not in SETTING_TYPES:
            result.add("inside.modules.validation.setting_type")
            continue
        if type_name == "enum":
            raw_options = setting.get("choices", setting.get("options"))
            values: list[str] = []
            options_valid = True
            if not isinstance(raw_options, list) or not raw_options:
                result.add("inside.modules.validation.setting_options")
                options_valid = False
            else:
                for option in raw_options:
                    value = option.get("value") if isinstance(option, dict) else option
                    if not isinstance(value, str) or not value:
                        result.add("inside.modules.validation.setting_options")
                        options_valid = False
                    else:
                        values.append(value)
                if len(values) != len(set(values)):
                    result.add("inside.modules.validation.setting_options")
                    options_valid = False
            if "default" in setting:
                default = setting.get("default")
                if not isinstance(default, str) or not options_valid or default not in values:
                    result.add("inside.modules.validation.setting_default")
        elif "default" in setting:
            default = setting.get("default")
            if type_name == "boolean" and not isinstance(default, bool):
                result.add("inside.modules.validation.setting_default")
            elif type_name == "integer" and not isinstance(default, int):
                result.add("inside.modules.validation.setting_default")
            elif type_name == "number" and not isinstance(default, (int, float)):
                result.add("inside.modules.validation.setting_default")
            elif type_name == "string" and not isinstance(default, str):
                result.add("inside.modules.validation.setting_default")
        max_length = setting.get("maxLength")
        if max_length is not None and (not isinstance(max_length, int) or max_length < 1 or max_length > 4096):
            result.add("inside.modules.validation.setting_max_length")



def _validate_content_packs(manifest: ModuleManifest, result: ManifestValidation) -> None:
    if len(manifest.content_packs) > MAX_MODULE_CONTENT_PACKS:
        result.add("inside.modules.validation.content_pack_limit")
        return
    seen: set[str] = set()
    for pack in manifest.content_packs:
        pack_id = pack.get("id")
        if not isinstance(pack_id, str) or not pack_id or not ID_PATTERN.match(pack_id):
            result.add("inside.modules.validation.content_pack_id")
        elif pack_id in seen:
            result.add("inside.modules.validation.content_pack_duplicate")
        else:
            seen.add(pack_id)

        pack_type = pack.get("type")
        if not isinstance(pack_type, str) or pack_type not in CONTENT_PACK_TYPES:
            result.add("inside.modules.validation.content_pack_type")

        label = pack.get("label")
        if label is not None and (not isinstance(label, str) or len(label) > MAX_CONTENT_PACK_LABEL_LENGTH):
            result.add("inside.modules.validation.content_pack_label")

        path = pack.get("path")
        if not isinstance(path, str) or not path or _suffix(path) != ".json":
            result.add("inside.modules.validation.content_pack_path")
        elif not _path_is_safe(path):
            result.add("inside.modules.validation.path_unsafe")


def _relationship_id(item: object) -> str | None:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        value = item.get("id") or item.get("module") or item.get("module_id")
        return value if isinstance(value, str) else None
    return None


def _validate_relationship_list(
    *,
    manifest: ModuleManifest,
    values: list,
    error_key: str,
    duplicate_key: str,
    self_key: str,
    result: ManifestValidation,
) -> None:
    if len(values) > MAX_MODULE_RELATIONSHIPS:
        result.add("inside.modules.validation.relationship_limit")
        return
    seen: set[str] = set()
    for item in values:
        module_id = _relationship_id(item)
        if not module_id or not ID_PATTERN.match(module_id):
            result.add(error_key)
            continue
        if module_id == manifest.id:
            result.add(self_key)
        if module_id in seen:
            result.add(duplicate_key)
        seen.add(module_id)


def _validate_relationships(manifest: ModuleManifest, result: ManifestValidation) -> None:
    _validate_relationship_list(
        manifest=manifest,
        values=manifest.dependencies,
        error_key="inside.modules.validation.dependency_id",
        duplicate_key="inside.modules.validation.dependency_duplicate",
        self_key="inside.modules.validation.dependency_self",
        result=result,
    )
    _validate_relationship_list(
        manifest=manifest,
        values=manifest.conflicts,
        error_key="inside.modules.validation.conflict_id",
        duplicate_key="inside.modules.validation.conflict_duplicate",
        self_key="inside.modules.validation.conflict_self",
        result=result,
    )
    if manifest.load_order < MIN_MODULE_LOAD_ORDER or manifest.load_order > MAX_MODULE_LOAD_ORDER:
        result.add("inside.modules.validation.load_order")


def _validate_capability_contract(manifest: ModuleManifest, result: ManifestValidation) -> None:
    capabilities = set(manifest.capabilities)
    styles = manifest.entrypoint_paths() and any(manifest.entrypoint_styles(ctx) for ctx in ENTRYPOINT_CONTEXTS)
    scripts = manifest.entrypoint_paths() and any(manifest.entrypoint_scripts(ctx) for ctx in ENTRYPOINT_CONTEXTS)
    if styles and not ({"assets.ui", "assets.styles"} & capabilities):
        result.add("inside.modules.validation.capability_missing")
    if scripts and "assets.scripts" not in capabilities:
        result.add("inside.modules.validation.capability_missing")
    if manifest.hooks and "hooks.client" not in capabilities:
        result.add("inside.modules.validation.capability_missing")
    if manifest.settings and "settings" not in capabilities:
        result.add("inside.modules.validation.capability_missing")
    if manifest.locales and "locales" not in capabilities:
        result.add("inside.modules.validation.capability_missing")
    if manifest.content_packs and "content.packs" not in capabilities:
        result.add("inside.modules.validation.capability_missing")


def validate_manifest(raw: object) -> ManifestValidation:
    result = ManifestValidation()

    if not isinstance(raw, dict):
        result.add("inside.modules.validation.not_object")
        result.compatibility_status = COMPAT_INCOMPATIBLE
        return result

    manifest = ModuleManifest.from_dict(raw)

    if manifest.schema_version != SUPPORTED_SCHEMA_VERSION:
        result.add("inside.modules.validation.schema_version")
    if raw.get("manifestVersion") is not None:
        result.add("inside.modules.validation.manifest_version_legacy")
    if manifest.type != "module":
        result.add("inside.modules.validation.type")
    if not manifest.id:
        result.add("inside.modules.validation.id_required")
    elif not ID_PATTERN.match(manifest.id):
        result.add("inside.modules.validation.id_invalid")
    if not manifest.name:
        result.add("inside.modules.validation.name_required")
    if not manifest.version:
        result.add("inside.modules.validation.version_required")
    if not manifest.api_version:
        result.add("inside.modules.validation.api_version_required")

    if not (manifest.compatibility.minimum or manifest.compatibility.maximum):
        result.add("inside.modules.validation.compatibility_required")

    if not manifest.capabilities:
        result.add("inside.modules.validation.capabilities_required")
    for capability in manifest.capabilities:
        if capability in FORBIDDEN_CAPABILITIES:
            result.add("inside.modules.validation.capability_forbidden")
        elif capability not in KNOWN_CAPABILITIES:
            result.add("inside.modules.validation.capability_unknown")

    module_raw = raw.get("module")
    if not isinstance(module_raw, dict):
        result.add("inside.modules.validation.module_required")
    else:
        if not manifest.module_id:
            result.add("inside.modules.validation.module_id_required")
        elif manifest.id and manifest.module_id != manifest.id:
            result.add("inside.modules.validation.module_id_mismatch")
        _validate_entrypoints(module_raw, manifest, result)

    _validate_content_packs(manifest, result)

    _validate_settings(manifest, result)
    _validate_relationships(manifest, result)
    _validate_capability_contract(manifest, result)

    for path in manifest.referenced_paths():
        if not _path_is_safe(path):
            result.add("inside.modules.validation.path_unsafe")
            break

    result.compatibility_status = compute_compatibility_status(manifest)
    if result.compatibility_status == COMPAT_INCOMPATIBLE:
        result.add("inside.modules.validation.incompatible")

    return result
