"""Typed representation of a Gravewright Module Manifest (Module API v1).

Modules are optional extensions. Like systems, manifests are declarative: the
backend validates and serves declared package files, but never executes module
code server-side.
"""

from __future__ import annotations

from dataclasses import dataclass, field


SUPPORTED_SCHEMA_VERSION = 1
ENTRYPOINT_CONTEXTS = {"game", "inside"}
ENTRYPOINT_KINDS = {"styles", "scripts"}


def _str(value: object, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _int(value: object, default: int = 0) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def _list(value: object) -> list:
    return value if isinstance(value, list) else []


def _string_list(value: object) -> list[str]:
    return [item for item in _list(value) if isinstance(item, str) and item]


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
class ModuleManifest:
    raw: dict
    schema_version: int
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
    entrypoints: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    settings: list[dict] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    locales: dict[str, str] = field(default_factory=dict)
    content_packs: list[dict] = field(default_factory=list)
    system_compatibility: dict = field(default_factory=dict)
    dependencies: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)
    load_order: int = 0

    @classmethod
    def from_dict(cls, raw: object) -> ModuleManifest:
        raw = _dict(raw)
        module = _dict(raw.get("module"))
        schema_version = raw.get("schemaVersion")
        return cls(
            raw=raw,
            schema_version=schema_version if isinstance(schema_version, int) else 0,
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
            entrypoints=_parse_entrypoints(module.get("entrypoints")),
            settings=[s for s in _list(module.get("settings")) if isinstance(s, dict)],
            hooks=[h for h in _list(module.get("hooks")) if isinstance(h, str)],
            locales={k: _str(v) for k, v in _dict(module.get("locales")).items()},
            content_packs=[p for p in _list(module.get("contentPacks")) if isinstance(p, dict)],
            system_compatibility=_dict(module.get("systems")),
            dependencies=_list(raw.get("dependencies", module.get("dependencies"))),
            conflicts=_list(raw.get("conflicts", module.get("conflicts"))),
            load_order=_int(raw.get("loadOrder", raw.get("priority", module.get("loadOrder", module.get("priority", 0))))),
        )

    @property
    def module_id(self) -> str:
        return _str(_dict(self.raw.get("module")).get("id"))

    def dependency_ids(self) -> list[str]:
        return _relationship_ids(self.dependencies)

    def conflict_ids(self) -> list[str]:
        return _relationship_ids(self.conflicts)

    def entrypoint_styles(self, context: str = "game") -> list[str]:
        return list(self.entrypoints.get(context, {}).get("styles", []))

    def entrypoint_scripts(self, context: str = "game") -> list[str]:
        return list(self.entrypoints.get(context, {}).get("scripts", []))

    @property
    def asset_styles(self) -> list[str]:
        """Game-page styles kept for callers that predate named entrypoints."""
        return self.entrypoint_styles("game")

    @property
    def asset_scripts(self) -> list[str]:
        """Game-page scripts kept for callers that predate named entrypoints."""
        return self.entrypoint_scripts("game")

    def entrypoint_paths(self) -> list[str]:
        paths: list[str] = []
        for context in sorted(self.entrypoints):
            entrypoint = self.entrypoints[context]
            paths.extend(entrypoint.get("styles", []))
            paths.extend(entrypoint.get("scripts", []))
        return _unique(paths)

    def referenced_paths(self) -> list[str]:
        paths: list[str] = []
        for value in (self.display.get("icon"), self.display.get("cover")):
            if isinstance(value, str) and value:
                paths.append(value)
        paths.extend(p for p in self.locales.values() if p)
        paths.extend(self.entrypoint_paths())
        for pack in self.content_packs:
            path = pack.get("path")
            if isinstance(path, str) and path:
                paths.append(path)
        return _unique(paths)

    def summary(self) -> dict:
        author = self.authors[0].get("name") if self.authors else ""
        return {
            "id": self.id,
            "name": self.name or self.id,
            "version": self.version,
            "schema_version": self.schema_version,
            "api_version": self.api_version,
            "description": self.description,
            "author": author,
            "color": _str(self.display.get("color")),
            "capabilities": list(self.capabilities),
            "entrypoints": self.entrypoints,
            "settings": list(self.settings),
            "hooks": list(self.hooks),
            "dependencies": self.dependency_ids(),
            "conflicts": self.conflict_ids(),
            "load_order": self.load_order,
            "content_packs": [
                {"id": _str(p.get("id")), "type": _str(p.get("type")), "label": _str(p.get("label"))}
                for p in self.content_packs
            ],
            "compatibility": {
                "minimum": self.compatibility.minimum,
                "verified": self.compatibility.verified,
                "maximum": self.compatibility.maximum,
            },
        }


def _parse_entrypoints(raw: object) -> dict[str, dict[str, list[str]]]:
    raw = _dict(raw)
    entrypoints: dict[str, dict[str, list[str]]] = {}
    for context, value in raw.items():
        if not isinstance(context, str) or not isinstance(value, dict):
            continue
        entrypoints[context] = {
            "styles": _string_list(value.get("styles")),
            "scripts": _string_list(value.get("scripts")),
        }
    return entrypoints


def _unique(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def _relationship_ids(value: list) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for item in value:
        module_id = ""
        if isinstance(item, str):
            module_id = item
        elif isinstance(item, dict):
            raw_id = item.get("id") or item.get("module") or item.get("module_id")
            module_id = raw_id if isinstance(raw_id, str) else ""
        if module_id and module_id not in seen:
            seen.add(module_id)
            ids.append(module_id)
    return ids
