"""Typed representation of a Gravewright System Manifest (System API v1).

The manifest *describes* a system; it never executes anything. ``from_dict`` is
deliberately defensive so that a malformed manifest still parses into a stable
shape — :mod:`app.engine.systems.system_manifest_validator` is what reports the
problems with precise, user-facing errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _str(value: object, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list:
    return value if isinstance(value, list) else []


@dataclass(frozen=True)
class TypeDef:
    id: str
    label: str
    schema: str = ""
    sheet: str = ""

    @classmethod
    def from_dict(cls, raw: object) -> TypeDef:
        raw = _dict(raw)
        return cls(
            id=_str(raw.get("id")),
            label=_str(raw.get("label")),
            schema=_str(raw.get("schema")),
            sheet=_str(raw.get("sheet")),
        )


@dataclass(frozen=True)
class ContentPackRef:
    id: str
    type: str
    label: str
    path: str

    @classmethod
    def from_dict(cls, raw: object) -> ContentPackRef:
        raw = _dict(raw)
        return cls(
            id=_str(raw.get("id")),
            type=_str(raw.get("type")),
            label=_str(raw.get("label")),
            path=_str(raw.get("path")),
        )


@dataclass(frozen=True)
class Compatibility:
    minimum: str = ""
    verified: str = ""
    maximum: str = ""

    @classmethod
    def from_dict(cls, raw: object) -> Compatibility:
        raw = _dict(raw)
        return cls(
            minimum=_str(raw.get("minimum")),
            verified=_str(raw.get("verified")),
            maximum=_str(raw.get("maximum")),
        )


@dataclass(frozen=True)
class SystemManifest:
    raw: dict
    manifest_version: int
    type: str
    id: str
    name: str
    version: str
    api_version: str
    description: str
    authors: list[dict]
    license: str
    homepage: str
    compatibility: Compatibility
    capabilities: list[str]
    display: dict
    storage_model: str
    actor_types: list[TypeDef]
    item_types: list[TypeDef]
    content_packs: list[ContentPackRef]
    locales: dict[str, str]
    rules: dict[str, str]
    mappings: dict[str, str]
    area_markers: list[dict] = field(default_factory=list)
    assets: dict = field(default_factory=dict)
    dependencies: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: object) -> SystemManifest:
        raw = _dict(raw)
        system = _dict(raw.get("system"))
        manifest_version = raw.get("manifestVersion")
        return cls(
            raw=raw,
            manifest_version=manifest_version if isinstance(manifest_version, int) else 0,
            type=_str(raw.get("type")),
            id=_str(raw.get("id")),
            name=_str(raw.get("name")),
            version=_str(raw.get("version")),
            api_version=_str(raw.get("apiVersion")),
            description=_str(raw.get("description")),
            authors=[a for a in _list(raw.get("authors")) if isinstance(a, dict)],
            license=_str(raw.get("license")),
            homepage=_str(raw.get("homepage")),
            compatibility=Compatibility.from_dict(raw.get("compatibility")),
            capabilities=[c for c in _list(raw.get("capabilities")) if isinstance(c, str)],
            display=_dict(raw.get("display")),
            storage_model=_str(_dict(system.get("storage")).get("model")),
            actor_types=[TypeDef.from_dict(t) for t in _list(system.get("actorTypes"))],
            item_types=[TypeDef.from_dict(t) for t in _list(system.get("itemTypes"))],
            content_packs=[ContentPackRef.from_dict(p) for p in _list(system.get("contentPacks"))],
            locales={k: _str(v) for k, v in _dict(system.get("locales")).items()},
            rules={k: _str(v) for k, v in _dict(system.get("rules")).items()},
            mappings={k: _str(v) for k, v in _dict(system.get("mappings")).items()},
            area_markers=[m for m in _list(system.get("areaMarkers")) if isinstance(m, dict)],
            assets=_dict(system.get("assets")),
            dependencies=_list(raw.get("dependencies")),
            conflicts=_list(raw.get("conflicts")),
        )

    @property
    def system_id(self) -> str:
        return _str(_dict(self.raw.get("system")).get("id"))

    @property
    def asset_styles(self) -> list[str]:
        """Package-relative CSS files the system contributes to the table UI."""
        return [s for s in _list(self.assets.get("styles")) if isinstance(s, str) and s]

    @property
    def asset_scripts(self) -> list[str]:
        """Package-relative JS files the system contributes to the table UI."""
        return [s for s in _list(self.assets.get("scripts")) if isinstance(s, str) and s]

    def referenced_paths(self) -> list[str]:
        """All relative paths the manifest points at (for safety + existence checks)."""
        paths: list[str] = []
        for value in (self.display.get("icon"), self.display.get("cover")):
            if isinstance(value, str) and value:
                paths.append(value)
        for type_def in (*self.actor_types, *self.item_types):
            if type_def.schema:
                paths.append(type_def.schema)
            if type_def.sheet:
                paths.append(type_def.sheet)
        paths.extend(p for p in self.rules.values() if p)
        paths.extend(p for p in self.mappings.values() if p)
        paths.extend(pack.path for pack in self.content_packs if pack.path)
        paths.extend(p for p in self.locales.values() if p)
        paths.extend(self.asset_styles)
        paths.extend(self.asset_scripts)
                                              
        seen: set[str] = set()
        unique: list[str] = []
        for path in paths:
            if path not in seen:
                seen.add(path)
                unique.append(path)
        return unique

    def summary(self) -> dict:
        """Lightweight dict for list/detail views in the Systems tab."""
        author = self.authors[0].get("name") if self.authors else ""
        return {
            "id": self.id,
            "name": self.name or self.id,
            "version": self.version,
            "api_version": self.api_version,
            "description": self.description,
            "author": author,
            "color": _str(self.display.get("color")),
            "capabilities": list(self.capabilities),
            "actor_types": [{"id": t.id, "label": t.label} for t in self.actor_types],
            "item_types": [{"id": t.id, "label": t.label} for t in self.item_types],
            "area_markers": list(self.area_markers),
            "content_packs": [
                {"id": p.id, "type": p.type, "label": p.label} for p in self.content_packs
            ],
            "compatibility": {
                "minimum": self.compatibility.minimum,
                "verified": self.compatibility.verified,
                "maximum": self.compatibility.maximum,
            },
        }
