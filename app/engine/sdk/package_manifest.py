"""Typed representation of a Gravewright SDK Package Manifest (SDK v1).

The manifest *describes* a package; it never executes anything. ``from_dict`` is
deliberately defensive so a malformed manifest still parses into a stable shape
— :mod:`app.engine.sdk.package_manifest_validator` is what reports problems with
precise, user-facing error keys.

Every installable thing in Gravewright is a *package* with a ``kind``:
``ruleset``, ``addon``, ``library``, ``content``, ``theme``, or ``assets``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class PackageKind(str, Enum):
    RULESET = "ruleset"
    ADDON = "addon"
    LIBRARY = "library"
    CONTENT = "content"
    THEME = "theme"
    ASSETS = "assets"

    @classmethod
    def values(cls) -> set[str]:
        return {member.value for member in cls}


# The universal data layout groups packages by kind:
# ``data/packages/{kind_plural}/{id}``. This maps a manifest ``kind`` to its
# directory segment (and back) so discovery, install, asset serving and storage
# all agree on where a package lives.
KIND_TO_DIRECTORY: dict[str, str] = {
    PackageKind.ADDON.value: "addons",
    PackageKind.RULESET.value: "rulesets",
    PackageKind.LIBRARY.value: "libraries",
    PackageKind.THEME.value: "themes",
    PackageKind.CONTENT.value: "content",
    PackageKind.ASSETS.value: "assets",
}
DIRECTORY_TO_KIND: dict[str, str] = {v: k for k, v in KIND_TO_DIRECTORY.items()}

# The SDK API version line. A manifest's ``sdkVersion`` must equal this, and a
# package's compatibility window is evaluated against it — never against the core
# Gravewright release version, so a core release bump never retroactively breaks
# SDK 1 packages. Frozen at ``"1"`` by Alpha 2.0.0 — SDK Freeze.
SDK_VERSION = "1"


def _str(value: object, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list:
    return value if isinstance(value, list) else []


@dataclass(frozen=True)
class PackageCompatibility:
    minimum: str = ""
    verified: str = ""
    maximum: str = ""

    @classmethod
    def from_dict(cls, raw: object) -> PackageCompatibility:
        raw = _dict(raw)
        return cls(
            minimum=_str(raw.get("minimum")),
            verified=_str(raw.get("verified")),
            maximum=_str(raw.get("maximum")),
        )


@dataclass(frozen=True)
class PackageActivation:
    scope: str = "campaign"
    mode: str = "multiple"

    @classmethod
    def from_dict(cls, raw: object) -> PackageActivation:
        raw = _dict(raw)
        return cls(
            scope=_str(raw.get("scope"), "campaign"),
            mode=_str(raw.get("mode"), "multiple"),
        )


@dataclass(frozen=True)
class PackageEntrypoint:
    name: str
    styles: list[str] = field(default_factory=list)
    scripts: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, name: str, raw: object) -> PackageEntrypoint:
        raw = _dict(raw)
        return cls(
            name=name,
            styles=[s for s in _list(raw.get("styles")) if isinstance(s, str) and s],
            scripts=[s for s in _list(raw.get("scripts")) if isinstance(s, str) and s],
        )


@dataclass(frozen=True)
class PackageSetting:
    key: str
    scope: str = "campaign"
    type: str = "string"
    default: object = None
    label: str = ""
    options: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: object) -> PackageSetting:
        raw = _dict(raw)
        return cls(
            key=_str(raw.get("key")),
            scope=_str(raw.get("scope"), "campaign"),
            type=_str(raw.get("type"), "string"),
            default=raw.get("default"),
            label=_str(raw.get("label")),
            options=_list(raw.get("options")),
        )

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "scope": self.scope,
            "type": self.type,
            "default": self.default,
            "label": self.label,
            "options": list(self.options),
        }


@dataclass(frozen=True)
class PackageContentPack:
    id: str
    type: str
    label: str
    path: str
    label_key: str = ""

    @classmethod
    def from_dict(cls, raw: object) -> PackageContentPack:
        raw = _dict(raw)
        return cls(
            id=_str(raw.get("id")),
            type=_str(raw.get("type")),
            label=_str(raw.get("label")),
            label_key=_str(raw.get("labelKey")),
            path=_str(raw.get("path")),
        )


@dataclass(frozen=True)
class TypeDef:
    id: str
    label: str = ""
    label_key: str = ""
    schema: str = ""
    sheet: object = ""

    @classmethod
    def from_dict(cls, raw: object) -> TypeDef:
        raw = _dict(raw)
        return cls(
            id=_str(raw.get("id")),
            label=_str(raw.get("label")),
            label_key=_str(raw.get("labelKey")),
            schema=_str(raw.get("schema")),
            sheet=raw.get("sheet") if isinstance(raw.get("sheet"), (str, dict)) else "",
        )

    @property
    def sheet_path(self) -> str:
        if isinstance(self.sheet, str):
            return self.sheet
        if isinstance(self.sheet, dict):
            if self.sheet.get("mode") == "html":
                return _str(self.sheet.get("template"))
            return _str(self.sheet.get("path"))
        return ""

    @property
    def html_sheet(self) -> dict | None:
        """The HTML-mode sheet descriptor, or ``None`` for a declarative sheet.

        Returns the package-relative ``template``/``controller``/``style`` paths
        the frontend needs to fetch and mount through ``GravewrightHTMLSheets``.
        """
        if isinstance(self.sheet, dict) and self.sheet.get("mode") == "html":
            return {
                "mode": "html",
                "template": _str(self.sheet.get("template")),
                "controller": _str(self.sheet.get("controller")),
                "style": _str(self.sheet.get("style")),
            }
        return None


@dataclass(frozen=True)
class PackageDistribution:
    type: str = ""
    url: str = ""
    sha256: str = ""

    @classmethod
    def from_dict(cls, raw: object) -> PackageDistribution | None:
        if not isinstance(raw, dict):
            return None
        return cls(
            type=_str(raw.get("type")),
            url=_str(raw.get("url")),
            sha256=_str(raw.get("sha256")),
        )


@dataclass(frozen=True)
class PackageRequirement:
    """Shared base for the public dependency/conflict contract.

    A requirement points at another package by ``id``; subclasses add the fields
    that make the public contract explicit.
    """

    id: str
    kind: str = ""


@dataclass(frozen=True)
class PackageDependency(PackageRequirement):
    minimum: str = ""
    verified: str = ""
    maximum: str = ""

    @classmethod
    def from_dict(cls, raw: object) -> PackageDependency:
        raw = _dict(raw)
        return cls(
            id=_str(raw.get("id")),
            kind=_str(raw.get("kind")),
            minimum=_str(raw.get("minimum")),
            verified=_str(raw.get("verified")),
            maximum=_str(raw.get("maximum")),
        )


@dataclass(frozen=True)
class PackageConflict(PackageRequirement):
    reason: str = ""

    @classmethod
    def from_dict(cls, raw: object) -> PackageConflict:
        raw = _dict(raw)
        return cls(
            id=_str(raw.get("id")),
            kind=_str(raw.get("kind")),
            reason=_str(raw.get("reason")),
        )


@dataclass(frozen=True)
class PackageProvides:
    raw: dict = field(default_factory=dict)
    storage_model: str = ""
    actor_types: list[TypeDef] = field(default_factory=list)
    item_types: list[TypeDef] = field(default_factory=list)
    rules: dict[str, str] = field(default_factory=dict)
    mappings: dict[str, str] = field(default_factory=dict)
    content_packs: list[PackageContentPack] = field(default_factory=list)
    locales: dict[str, str] = field(default_factory=dict)
    assets: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: object) -> PackageProvides:
        raw = _dict(raw)
        return cls(
            raw=raw,
            storage_model=_str(_dict(raw.get("storage")).get("model")),
            actor_types=[TypeDef.from_dict(t) for t in _list(raw.get("actorTypes"))],
            item_types=[TypeDef.from_dict(t) for t in _list(raw.get("itemTypes"))],
            rules={k: _str(v) for k, v in _dict(raw.get("rules")).items()},
            mappings={k: _str(v) for k, v in _dict(raw.get("mappings")).items()},
            content_packs=[
                PackageContentPack.from_dict(p) for p in _list(raw.get("contentPacks"))
            ],
            locales={k: _str(v) for k, v in _dict(raw.get("locales")).items()},
            assets=_dict(raw.get("assets")),
        )

    def asset_entries(self) -> list[tuple[str, dict]]:
        """Flatten ``provides.assets`` into ``(category, entry)`` pairs."""
        pairs: list[tuple[str, dict]] = []
        for category, entries in self.assets.items():
            for entry in _list(entries):
                if isinstance(entry, dict):
                    pairs.append((category, entry))
        return pairs


@dataclass(frozen=True)
class PackageManifest:
    raw: dict
    schema_version: int
    sdk_version: str
    kind: str
    id: str
    name: str
    version: str
    description: str
    authors: list
    license: str
    homepage: str
    repository: str
    compatibility: PackageCompatibility
    capabilities: list[str]
    activation: PackageActivation
    entrypoints: dict[str, PackageEntrypoint]
    provides: PackageProvides
    settings: list[PackageSetting] = field(default_factory=list)
    distribution: PackageDistribution | None = None
    dependencies: list[PackageDependency] = field(default_factory=list)
    conflicts: list[PackageConflict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: object) -> PackageManifest:
        raw = _dict(raw)
        schema_version = raw.get("schemaVersion")
        entrypoints = {
            name: PackageEntrypoint.from_dict(name, value)
            for name, value in _dict(raw.get("entrypoints")).items()
        }
        return cls(
            raw=raw,
            schema_version=schema_version if isinstance(schema_version, int) else 0,
            sdk_version=_str(raw.get("sdkVersion")),
            kind=_str(raw.get("kind")),
            id=_str(raw.get("id")),
            name=_str(raw.get("name")),
            version=_str(raw.get("version")),
            description=_str(raw.get("description")),
            authors=_list(raw.get("authors")),
            license=_str(raw.get("license")),
            homepage=_str(raw.get("homepage")),
            repository=_str(raw.get("repository")),
            compatibility=PackageCompatibility.from_dict(raw.get("compatibility")),
            capabilities=[c for c in _list(raw.get("capabilities")) if isinstance(c, str)],
            activation=PackageActivation.from_dict(raw.get("activation")),
            entrypoints=entrypoints,
            provides=PackageProvides.from_dict(raw.get("provides")),
            settings=[PackageSetting.from_dict(s) for s in _list(raw.get("settings"))],
            distribution=PackageDistribution.from_dict(raw.get("distribution")),
            dependencies=[PackageDependency.from_dict(d) for d in _list(raw.get("dependencies"))],
            conflicts=[PackageConflict.from_dict(c) for c in _list(raw.get("conflicts"))],
        )

    # --- domain accessors ------------------------------------------------------
    # Rulesets expose their game model through ``provides``; these read-only
    # properties give the engine a flat view without reaching into ``provides``.

    @property
    def actor_types(self) -> list[TypeDef]:
        return self.provides.actor_types

    @property
    def item_types(self) -> list[TypeDef]:
        return self.provides.item_types

    @property
    def content_packs(self) -> list[PackageContentPack]:
        return self.provides.content_packs

    @property
    def rules(self) -> dict[str, str]:
        return self.provides.rules

    @property
    def mappings(self) -> dict[str, str]:
        return self.provides.mappings

    @property
    def storage_model(self) -> str:
        return self.provides.storage_model

    @property
    def locales(self) -> dict[str, str]:
        return self.provides.locales

    @property
    def display(self) -> dict:
        return _dict(self.raw.get("display"))

    @property
    def area_markers(self) -> list[dict]:
        return [m for m in _list(self.provides.raw.get("areaMarkers")) if isinstance(m, dict)]

    # --- convenience accessors -------------------------------------------------

    def entrypoint_styles(self, entrypoint: str = "game") -> list[str]:
        ep = self.entrypoints.get(entrypoint)
        return list(ep.styles) if ep else []

    def entrypoint_scripts(self, entrypoint: str = "game") -> list[str]:
        ep = self.entrypoints.get(entrypoint)
        return list(ep.scripts) if ep else []

    def has_scripts(self) -> bool:
        return any(ep.scripts for ep in self.entrypoints.values())

    def author_names(self) -> list[str]:
        names: list[str] = []
        for author in self.authors:
            if isinstance(author, str) and author:
                names.append(author)
            elif isinstance(author, dict):
                name = _str(author.get("name"))
                if name:
                    names.append(name)
        return names

    def referenced_paths(self) -> list[str]:
        """All package-relative paths the manifest points at."""
        paths: list[str] = []
        for ep in self.entrypoints.values():
            paths.extend(ep.styles)
            paths.extend(ep.scripts)
        for type_def in (*self.provides.actor_types, *self.provides.item_types):
            if type_def.schema:
                paths.append(type_def.schema)
            if isinstance(type_def.sheet, str) and type_def.sheet:
                paths.append(type_def.sheet)
            elif isinstance(type_def.sheet, dict):
                for key in ("template", "controller", "style", "path"):
                    path = _str(type_def.sheet.get(key))
                    if path:
                        paths.append(path)
        paths.extend(p for p in self.provides.rules.values() if p)
        paths.extend(p for p in self.provides.mappings.values() if p)
        paths.extend(pack.path for pack in self.provides.content_packs if pack.path)
        paths.extend(p for p in self.provides.locales.values() if p)
        for _category, entry in self.provides.asset_entries():
            path = _str(entry.get("path"))
            if path:
                paths.append(path)

        seen: set[str] = set()
        unique: list[str] = []
        for path in paths:
            if path not in seen:
                seen.add(path)
                unique.append(path)
        return unique

    def summary(self, *, package_dir: Path | None = None) -> dict:
        locale_data = self.load_locale(package_dir, "en") if package_dir else {}
        return {
            "id": self.id,
            "name": self.name or self.id,
            "kind": self.kind,
            "version": self.version,
            "description": self.description,
            "authors": self.author_names(),
            "author": self.author_names()[0] if self.author_names() else "",
            "license": self.license,
            "homepage": self.homepage,
            "color": _str(self.display.get("color")),
            "capabilities": list(self.capabilities),
            "activation": {"scope": self.activation.scope, "mode": self.activation.mode},
            "compatibility": {
                "minimum": self.compatibility.minimum,
                "verified": self.compatibility.verified,
                "maximum": self.compatibility.maximum,
            },
            "actor_types": [
                {"id": t.id, "label": self._resolve_label(t.label, t.label_key, locale_data)}
                for t in self.provides.actor_types
            ],
            "item_types": [
                {"id": t.id, "label": self._resolve_label(t.label, t.label_key, locale_data)}
                for t in self.provides.item_types
            ],
            "area_markers": [
                {
                    **m,
                    "label": self._resolve_label(
                        _str(m.get("label")), _str(m.get("labelKey")), locale_data
                    ),
                }
                for m in self.area_markers
            ],
            "content_packs": [
                {"id": p.id, "type": p.type, "label": self._resolve_label(p.label, p.label_key, locale_data)}
                for p in self.provides.content_packs
            ],
            "settings": [s.to_dict() for s in self.settings],
            "dependencies": [{"id": d.id, "kind": d.kind, "minimum": d.minimum} for d in self.dependencies],
            "conflicts": [{"id": c.id, "reason": c.reason} for c in self.conflicts],
        }

    @staticmethod
    def _resolve_label(label: str, label_key: str, locale_data: dict) -> str:
        if label:
            return label
        if label_key and locale_data:
            return locale_data.get(label_key, label_key)
        return label_key

    def load_locale(self, package_dir: Path, locale: str) -> dict:
        path_rel = self.provides.locales.get(locale)
        if not path_rel:
            return {}
        try:
            return json.loads((package_dir / path_rel).read_text(encoding="utf-8"))
        except Exception:
            return {}
