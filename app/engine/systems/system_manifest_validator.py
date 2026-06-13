"""Validation rules for System Manifests (System API v1).

The validator never trusts the manifest: it checks required fields, the ``id``
shape, that every declared path is package-relative and safe, that capabilities
are on the known allow-list (and none are forbidden), and computes a
compatibility status against the running Gravewright version.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config import config
from app.engine.systems.system_manifest import SystemManifest

ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

KNOWN_CAPABILITIES = {
    "actors.register",
    "items.register",
    "sheets.declarative",
    "rules.declarative",
    "content.packs",
    "tokens.mappings",
    "dice.roll",
    "chat.cards",
    "roll.toast",
    "locales",
    "assets.ui",
    "assets.styles",
    "assets.scripts",
    "combat.config",
    "combat.hooks",
    "rolls.intent",
}

FORBIDDEN_CAPABILITIES = {
    "backend.execute",
    "database.raw",
    "filesystem.raw",
    "network.raw",
    "permissions.override",
}

KNOWN_STORAGE_MODELS = {"scoped-json-v1"}

CONTENT_PACK_TYPES = {
    "actor_pack",
    "item_pack",
    "spell_pack",
    "journal_pack",
    "table_pack",
    "condition_pack",
}

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
    """Map a semver-ish string to a comparable tuple.

    ``1.x`` treats the minor/patch as unbounded; a pre-release (``-rc.1``)
    sorts just below the matching release.
    """
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


def compute_compatibility_status(manifest: SystemManifest) -> str:
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
    if "\\" in path or "://" in path:
        return False
    if path.startswith("/") or re.match(r"^[a-zA-Z]:", path):
        return False
    segments = path.split("/")
    return ".." not in segments and "" not in segments[:-1]


def validate_manifest(raw: object) -> ManifestValidation:
    result = ManifestValidation()

    if not isinstance(raw, dict):
        result.add("inside.systems.validation.not_object")
        result.compatibility_status = COMPAT_INCOMPATIBLE
        return result

    manifest = SystemManifest.from_dict(raw)

                                     
    if manifest.manifest_version != 1:
        result.add("inside.systems.validation.manifest_version")
    if manifest.type != "system":
        result.add("inside.systems.validation.type")
    if not manifest.id:
        result.add("inside.systems.validation.id_required")
    elif not ID_PATTERN.match(manifest.id):
        result.add("inside.systems.validation.id_invalid")
    if not manifest.name:
        result.add("inside.systems.validation.name_required")
    if not manifest.version:
        result.add("inside.systems.validation.version_required")
    if not manifest.api_version:
        result.add("inside.systems.validation.api_version_required")

                           
    if not (manifest.compatibility.minimum or manifest.compatibility.maximum):
        result.add("inside.systems.validation.compatibility_required")

                          
    if not manifest.capabilities:
        result.add("inside.systems.validation.capabilities_required")
    for capability in manifest.capabilities:
        if capability in FORBIDDEN_CAPABILITIES:
            result.add("inside.systems.validation.capability_forbidden")
        elif capability not in KNOWN_CAPABILITIES:
            result.add("inside.systems.validation.capability_unknown")

                        
    if not isinstance(raw.get("system"), dict):
        result.add("inside.systems.validation.system_required")
    else:
        if not manifest.system_id:
            result.add("inside.systems.validation.system_id_required")
        elif manifest.id and manifest.system_id != manifest.id:
            result.add("inside.systems.validation.system_id_mismatch")
        if not manifest.storage_model:
            result.add("inside.systems.validation.storage_required")
        elif manifest.storage_model not in KNOWN_STORAGE_MODELS:
            result.add("inside.systems.validation.storage_unknown")
        if not manifest.actor_types:
            result.add("inside.systems.validation.actor_types_required")

                            
    for type_def in (*manifest.actor_types, *manifest.item_types):
        if not type_def.id or not (type_def.label or type_def.label_key):
            result.add("inside.systems.validation.type_fields")

                         
    for pack in manifest.content_packs:
        if pack.type not in CONTENT_PACK_TYPES:
            result.add("inside.systems.validation.content_pack_type")

                                                                   
    for path in manifest.referenced_paths():
        if not _path_is_safe(path):
            result.add("inside.systems.validation.path_unsafe")
            break

    result.compatibility_status = compute_compatibility_status(manifest)
    if result.compatibility_status == COMPAT_INCOMPATIBLE:
        result.add("inside.systems.validation.incompatible")

    return result
