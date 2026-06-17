"""Validation rules for Gravewright SDK Package Manifests (SDK v1).

The validator never trusts the manifest. It checks the schema/sdk versions, the
``kind``, the ``id`` shape, required metadata, the compatibility window, the
capability allow-list (rejecting forbidden capabilities), activation, the
kind-specific contract, settings, content packs, entrypoints, every referenced
path, and the dependency/conflict format. It returns a structured result with
``errors``, ``warnings``, and a computed ``compatibility_status``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engine.sdk.capability_registry import get_registry
from app.engine.sdk.package_compatibility import (
    COMPAT_INCOMPATIBLE,
    COMPAT_UNVERIFIED,
    compute_compatibility_status,
)
from app.engine.sdk.package_manifest import SDK_VERSION, PackageKind, PackageManifest
from app.engine.sdk.package_interop import validate_interop_manifest
from app.engine.sdk.package_paths import package_id_is_safe, path_is_safe
from app.engine.sdk.package_storage import validate_storage_manifest

# Capabilities are owned by the canonical registry (``capabilities.json``); the
# allow-list and forbidden set are derived from it so there is a single source
# of truth across validator, doctor, frontend and docs.
KNOWN_CAPABILITIES = get_registry().known_names()
FORBIDDEN_CAPABILITIES = get_registry().forbidden_names()

ACTIVATION_MODES = {"exclusive", "multiple", "passive", "none"}
ACTIVATION_SCOPES = {"campaign", "global", "user"}
SETTING_SCOPES = {"global", "campaign", "user"}
SETTING_TYPES = {"boolean", "string", "number", "integer", "enum"}
DISTRIBUTION_TYPES = {"zip", "git", "directory"}

CONTENT_PACK_TYPES = {
    "actor_pack",
    "item_pack",
    "spell_pack",
    "journal_pack",
    "table_pack",
    "condition_pack",
}

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".svg")
MAP_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
AUDIO_EXTENSIONS = (".mp3", ".ogg", ".wav")


@dataclass
class PackageManifestValidation:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    compatibility_status: str = COMPAT_UNVERIFIED

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, error_key: str) -> None:
        if error_key not in self.errors:
            self.errors.append(error_key)

    def warn(self, warning_key: str) -> None:
        if warning_key not in self.warnings:
            self.warnings.append(warning_key)


def validate_manifest(raw: object) -> PackageManifestValidation:
    result = PackageManifestValidation()

    # 1. Reject non-object manifests.
    if not isinstance(raw, dict):
        result.add("sdk.validation.not_object")
        result.compatibility_status = COMPAT_INCOMPATIBLE
        return result

    manifest = PackageManifest.from_dict(raw)

    # 2-3. Schema + SDK versions.
    if manifest.schema_version != 1:
        result.add("sdk.validation.schema_version")
    if manifest.sdk_version != SDK_VERSION:
        result.add("sdk.validation.sdk_version")

    # 4. Kind.
    if manifest.kind not in PackageKind.values():
        result.add("sdk.validation.kind")

    # 5. Id.
    if not manifest.id:
        result.add("sdk.validation.id_required")
    elif not package_id_is_safe(manifest.id):
        result.add("sdk.validation.id_invalid")

    # 6. Required metadata.
    if not manifest.name:
        result.add("sdk.validation.name_required")
    if not manifest.version:
        result.add("sdk.validation.version_required")
    _validate_authors_and_license(raw, result)

    # 7. Compatibility.
    compat = manifest.compatibility
    if not (compat.minimum or compat.maximum or compat.verified):
        result.add("sdk.validation.compatibility_required")

    # 8-9. Capabilities allow-list + forbidden.
    if not isinstance(raw.get("capabilities"), list):
        result.add("sdk.validation.capabilities_required")
    for capability in manifest.capabilities:
        if capability in FORBIDDEN_CAPABILITIES:
            result.add("sdk.validation.capability_forbidden")
        elif capability not in KNOWN_CAPABILITIES:
            result.add("sdk.validation.capability_unknown")

    # 10. Activation.
    if not isinstance(raw.get("activation"), dict):
        result.add("sdk.validation.activation_required")
    else:
        if manifest.activation.mode not in ACTIVATION_MODES:
            result.add("sdk.validation.activation_invalid")
        if manifest.activation.scope and manifest.activation.scope not in ACTIVATION_SCOPES:
            result.add("sdk.validation.activation_invalid")

    # 11. Kind-specific rules.
    _validate_kind_rules(manifest, result)

    # 12. Settings.
    _validate_settings(manifest, result)

    # 13. Content packs.
    for pack in manifest.provides.content_packs:
        if not pack.id or not pack.path or pack.type not in CONTENT_PACK_TYPES:
            result.add("sdk.validation.content_pack_invalid")
            break

    # 13b. HTML sheet manifest contract.
    _validate_html_sheets(manifest, result)

    # 14. Entrypoints.
    if not isinstance(raw.get("entrypoints"), dict):
        result.add("sdk.validation.entrypoint_invalid")

    # 15. Referenced paths.
    for path in manifest.referenced_paths():
        if not path_is_safe(path):
            result.add("sdk.validation.path_unsafe")
            break

    # 16. Dependency / conflict format + distribution.
    _validate_dependencies(manifest, result)
    _validate_distribution(raw, result)

    # 16b. Storage contract (Phase 7A) — manifest-level declaration only.
    for code in validate_storage_manifest(raw):
        result.add(code)

    # 16c. Interop contract (Phase 12) — manifest-level declaration only.
    for code in validate_interop_manifest(raw):
        result.add(code)

    # 17. Compatibility status.
    # A package's compatibility window targets the SDK API line (``SDK_VERSION``,
    # frozen at "1" by Alpha 2.0.0), not the core marketing version — so a core
    # bump (e.g. 1.0.0-rc.1 -> 2.0.0-alpha.0) does not retroactively make SDK 1
    # packages incompatible. ``sdkVersion`` in the manifest names the same line.
    result.compatibility_status = compute_compatibility_status(
        minimum=compat.minimum,
        verified=compat.verified,
        maximum=compat.maximum,
        engine_version=SDK_VERSION,
    )
    if result.compatibility_status == COMPAT_INCOMPATIBLE:
        result.warn("sdk.validation.incompatible")

    return result


def _validate_authors_and_license(raw: dict, result: PackageManifestValidation) -> None:
    authors = raw.get("authors")
    if authors is not None:
        if not isinstance(authors, list) or any(
            not isinstance(a, (str, dict)) for a in authors
        ):
            result.add("sdk.validation.authors_invalid")
    license_value = raw.get("license")
    if license_value is not None and not isinstance(license_value, str):
        result.add("sdk.validation.license_invalid")


def _validate_kind_rules(manifest: PackageManifest, result: PackageManifestValidation) -> None:
    kind = manifest.kind
    mode = manifest.activation.mode

    if kind == PackageKind.RULESET.value:
        if mode != "exclusive":
            result.add("sdk.validation.ruleset_activation_mode")
        if not manifest.provides.storage_model:
            result.add("sdk.validation.ruleset_storage_required")
        if not manifest.provides.actor_types:
            result.add("sdk.validation.ruleset_actor_types_required")
    elif kind == PackageKind.ADDON.value:
        if mode != "multiple":
            result.add("sdk.validation.addon_activation_mode")
    elif kind == PackageKind.LIBRARY.value:
        if mode != "passive":
            result.add("sdk.validation.library_activation_mode")
    elif kind == PackageKind.ASSETS.value:
        if mode != "multiple":
            result.add("sdk.validation.assets_activation_mode")
        _validate_assets(manifest, result)


def _validate_assets(manifest: PackageManifest, result: PackageManifestValidation) -> None:
    provides = manifest.provides
    # Assets packages must not declare game/data models.
    if provides.actor_types or provides.item_types or provides.rules or provides.storage_model:
        result.add("sdk.validation.assets_invalid_assets")
    seen: dict[str, set[str]] = {}
    for category, entry in provides.asset_entries():
        entry_id = entry.get("id")
        path = entry.get("path")
        if not isinstance(entry_id, str) or not entry_id:
            result.add("sdk.validation.assets_invalid_assets")
            continue
        if not isinstance(entry.get("label"), str) or not entry.get("label"):
            result.add("sdk.validation.assets_invalid_assets")
        if not isinstance(path, str) or not path_is_safe(path):
            result.add("sdk.validation.assets_invalid_assets")
            continue
        ids = seen.setdefault(category, set())
        if entry_id in ids:
            result.add("sdk.validation.assets_invalid_assets")
        ids.add(entry_id)
        _warn_asset_extension(category, path, result)


def _warn_asset_extension(category: str, path: str, result: PackageManifestValidation) -> None:
    lowered = path.lower()
    if category in {"images", "portraits", "tokens", "icons"} and not lowered.endswith(
        IMAGE_EXTENSIONS
    ):
        result.warn("sdk.validation.assets_image_extension")
    elif category == "maps" and not lowered.endswith(MAP_EXTENSIONS):
        result.warn("sdk.validation.assets_map_extension")
    elif category == "audio" and not lowered.endswith(AUDIO_EXTENSIONS):
        result.warn("sdk.validation.assets_audio_extension")


def _validate_settings(manifest: PackageManifest, result: PackageManifestValidation) -> None:
    for setting in manifest.settings:
        if not setting.key:
            result.add("sdk.validation.setting_invalid")
        if setting.scope not in SETTING_SCOPES:
            result.add("sdk.validation.setting_invalid")
        if setting.type not in SETTING_TYPES:
            result.add("sdk.validation.setting_invalid")
        if setting.type == "enum" and not setting.options:
            result.add("sdk.validation.setting_invalid")


def _validate_html_sheets(
    manifest: PackageManifest, result: PackageManifestValidation
) -> None:
    for type_def in (*manifest.provides.actor_types, *manifest.provides.item_types):
        sheet = type_def.sheet
        if not isinstance(sheet, dict):
            continue
        mode = sheet.get("mode")
        if mode != "html":
            result.add("sdk.sheets.html.invalid_mode")
            continue
        if "html" in sheet:
            result.add("sdk.sheets.html.inline_html_forbidden")
        if "sheets.html" not in manifest.capabilities:
            result.add("sdk.sheets.html.capability_missing")

        template = sheet.get("template")
        if not isinstance(template, str) or not template:
            result.add("sdk.sheets.html.template_missing")
        elif not path_is_safe(template) or not template.lower().endswith(".html"):
            result.add("sdk.sheets.html.template_unsafe_path")

        controller = sheet.get("controller")
        if controller is not None:
            if not isinstance(controller, str) or not path_is_safe(controller):
                result.add("sdk.sheets.html.controller_unsafe_path")
            if "sheets.controller" not in manifest.capabilities:
                result.add("sdk.sheets.html.controller_missing")

        style = sheet.get("style")
        if style is not None and (not isinstance(style, str) or not path_is_safe(style)):
            result.add("sdk.sheets.html.style_unsafe_path")


def _validate_dependencies(manifest: PackageManifest, result: PackageManifestValidation) -> None:
    for dependency in manifest.dependencies:
        if not dependency.id or not package_id_is_safe(dependency.id):
            result.add("sdk.validation.dependency_invalid")
        if dependency.kind and dependency.kind not in PackageKind.values():
            result.add("sdk.validation.dependency_invalid")
    for conflict in manifest.conflicts:
        if not conflict.id or not package_id_is_safe(conflict.id):
            result.add("sdk.validation.conflict_invalid")


def _validate_distribution(raw: dict, result: PackageManifestValidation) -> None:
    distribution = raw.get("distribution")
    if distribution is None:
        return
    if not isinstance(distribution, dict):
        result.add("sdk.validation.distribution_invalid")
        return
    dist_type = distribution.get("type")
    if dist_type not in DISTRIBUTION_TYPES:
        result.add("sdk.validation.distribution_invalid")
