"""Intent → capabilities/manifest/files derivation for ``grave <kind> new``.

Package authors should answer *what they want to build*:

- "does it have characters?"
- "does it have monsters?"
- "does it have a sheet?"
- "does it need JavaScript?"
- "does it ship content?"
- "does it provide assets?"

They should not need to pick raw capabilities by hand.

This module is the pure, I/O-free core that turns an :class:`Intent` into:

- a valid SDK package manifest;
- starter files referenced by that manifest;
- a README with next steps.

The CLI ``new`` command can be flag-driven or interactive and should remain a
thin shell around these functions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.config import config

SCHEMA_URL = (
    "https://raw.githubusercontent.com/Gravewright/gravewright/main/"
    "schemas/gravewright-package-v1.schema.json"
)

KINDS = {"ruleset", "addon", "library", "theme", "assets", "content"}

# activation.mode required per kind by the manifest validator/runtime.
_KIND_MODE = {
    "ruleset": "exclusive",
    "addon": "multiple",
    "library": "passive",
    "theme": "multiple",
    "assets": "multiple",
    "content": "multiple",
}

MAIN_SCRIPT = "assets/main.js"
MAIN_STYLE = "assets/main.css"
SAMPLE_ASSET = "assets/sample.svg"

DEFAULT_VERSION = "0.1.0"


@dataclass(frozen=True)
class Intent:
    """What the author wants to build, in plain terms.

    Defaults intentionally favor a useful first ruleset while remaining harmless
    for other package kinds.
    """

    # Game model.
    has_characters: bool = True
    has_monsters: bool = False
    has_items: bool = False
    has_sheets: bool = False
    has_rolls: bool = False
    has_combat: bool = False

    # Package provides.
    wants_content: bool = False
    wants_settings: bool = False
    wants_locales: bool = False

    # Runtime/client behavior.
    uses_js: bool = False
    uses_hooks: bool = False
    uses_sheet_hooks: bool = False
    uses_combat_hooks: bool = False
    uses_scene_tools: bool = False
    uses_scene_overlays: bool = False
    uses_token_extensions: bool = False

    # Asset package categories.
    has_images: bool = False
    has_maps: bool = False
    has_audio: bool = False
    has_icons: bool = False


@dataclass(frozen=True)
class PackageScaffold:
    """Pure scaffold result.

    ``files`` maps package-relative paths to UTF-8 text content. The writer layer
    decides whether to overwrite, prompt, or dry-run.
    """

    manifest: dict
    files: dict[str, str]


# --- helpers ----------------------------------------------------------------


def _json(data: object) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "my-package"


def suggest_package_id(name: str) -> str:
    """Return a safe kebab-case package id suggestion."""
    return _slugify(name)


def _title(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").title()


def _add(caps: list[str], cap: str) -> None:
    if cap not in caps:
        caps.append(cap)


def _asset_categories(intent: Intent) -> list[str]:
    categories: list[str] = []
    if intent.has_images:
        categories.append("images")
    if intent.has_maps:
        categories.append("maps")
    if intent.has_audio:
        categories.append("audio")
    if intent.has_icons:
        categories.append("icons")
    if not categories:
        categories.append("images")
    return categories


def _activation(kind: str) -> dict:
    mode = _KIND_MODE.get(kind, "multiple")
    activation: dict = {"mode": mode}
    if mode != "passive":
        activation["scope"] = "campaign"
    return activation


# --- capability derivation --------------------------------------------------


def derive_capabilities(kind: str, intent: Intent) -> list[str]:
    """Capabilities implied by the intent, in stable order.

    No forbidden capabilities are ever generated here.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown package kind: {kind}")

    caps: list[str] = []

    if kind == "ruleset":
        _add(caps, "actors.register")
        if intent.has_items:
            _add(caps, "items.register")
        if intent.has_sheets:
            _add(caps, "sheets.declarative")
        if intent.has_rolls:
            _add(caps, "dice.roll")
            _add(caps, "rolls.intent")
        if intent.has_combat:
            _add(caps, "combat.config")
        if intent.wants_content:
            _add(caps, "content.packs")
        if intent.wants_locales:
            _add(caps, "locales")
        if intent.wants_settings:
            _add(caps, "settings")
        if intent.uses_js:
            _add(caps, "assets.ui")
            _add(caps, "assets.styles")
            _add(caps, "assets.scripts")

    elif kind == "addon":
        if intent.uses_js:
            _add(caps, "assets.ui")
            _add(caps, "assets.styles")
            _add(caps, "assets.scripts")
        if intent.uses_hooks:
            _add(caps, "hooks.client")
        if intent.uses_sheet_hooks:
            _add(caps, "sheets.hooks")
        if intent.uses_combat_hooks:
            _add(caps, "combat.hooks")
        if intent.uses_scene_tools:
            _add(caps, "scene.tools")
        if intent.uses_scene_overlays:
            _add(caps, "scene.overlays")
        if intent.uses_token_extensions:
            _add(caps, "tokens.extends")
        if intent.wants_content:
            _add(caps, "content.packs")
        if intent.wants_locales:
            _add(caps, "locales")
        if intent.wants_settings or not caps:
            # Bare addons should still be configurable rather than gaining
            # broader runtime powers.
            _add(caps, "settings")

    elif kind == "library":
        if intent.uses_js:
            _add(caps, "assets.scripts")
            _add(caps, "assets.styles")
        if intent.uses_hooks:
            _add(caps, "hooks.client")
        if intent.wants_locales:
            _add(caps, "locales")
        if intent.wants_settings:
            _add(caps, "settings")
        # A passive library may intentionally have no capabilities. The manifest
        # still contains an empty capabilities list.

    elif kind == "theme":
        _add(caps, "assets.styles")
        _add(caps, "assets.ui")
        if intent.uses_js:
            _add(caps, "assets.scripts")
        if intent.wants_settings:
            _add(caps, "settings")
        if intent.wants_locales:
            _add(caps, "locales")

    elif kind == "assets":
        _add(caps, "assets.pack")
        for category in _asset_categories(intent):
            if category == "images":
                _add(caps, "assets.images")
            elif category == "maps":
                _add(caps, "assets.maps")
            elif category == "audio":
                _add(caps, "assets.audio")
            elif category == "icons":
                _add(caps, "assets.icons")
        if intent.wants_locales:
            _add(caps, "locales")

    elif kind == "content":
        _add(caps, "content.packs")
        if intent.wants_locales:
            _add(caps, "locales")

    return caps


# --- manifest derivation ----------------------------------------------------


def _actor_type(type_id: str, label: str, *, with_sheet: bool) -> dict:
    raw = {
        "id": type_id,
        "label": label,
        "schema": f"schemas/actors/{type_id}.schema.json",
    }
    if with_sheet:
        raw["sheet"] = f"layouts/actors/{type_id}.sheet.json"
    return raw


def _item_type(type_id: str, label: str, *, with_sheet: bool) -> dict:
    raw = {
        "id": type_id,
        "label": label,
        "schema": f"schemas/items/{type_id}.schema.json",
    }
    if with_sheet:
        raw["sheet"] = f"layouts/items/{type_id}.sheet.json"
    return raw


def _derive_ruleset_provides(intent: Intent) -> dict:
    actor_types = []

    if intent.has_characters or not intent.has_monsters:
        actor_types.append(_actor_type("character", "Character", with_sheet=intent.has_sheets))

    if intent.has_monsters:
        actor_types.append(_actor_type("monster", "Monster", with_sheet=intent.has_sheets))

    provides: dict = {
        "storage": {"model": "scoped-json-v1"},
        "actorTypes": actor_types,
    }

    if intent.has_items:
        provides["itemTypes"] = [
            _item_type("item", "Item", with_sheet=intent.has_sheets),
        ]

    if intent.has_rolls:
        provides["rules"] = {"derived": "rules/derived.gw.json"}

    if intent.has_combat:
        provides["mappings"] = {"tokens": "mappings/tokens.gw.json"}

    if intent.wants_content:
        provides["contentPacks"] = [
            {
                "id": "sample-actors",
                "type": "actor_pack",
                "label": "Sample Actors",
                "path": "content/sample-actors.gw.json",
            }
        ]

    if intent.wants_locales:
        provides["locales"] = {"en": "locales/en.json"}

    return provides


def _derive_assets_provides(intent: Intent) -> dict:
    assets: dict[str, list[dict]] = {}

    for category in _asset_categories(intent):
        if category == "audio":
            path = "assets/sample.ogg"
        elif category == "maps":
            path = "assets/sample-map.svg"
        elif category == "icons":
            path = "assets/sample-icon.svg"
        else:
            path = SAMPLE_ASSET

        assets.setdefault(category, []).append(
            {
                "id": "sample",
                "label": "Sample",
                "path": path,
            }
        )

    provides: dict = {"assets": assets}
    if intent.wants_locales:
        provides["locales"] = {"en": "locales/en.json"}
    return provides


def _derive_content_provides(intent: Intent) -> dict:
    provides: dict = {
        "contentPacks": [
            {
                "id": "sample-journals",
                "type": "journal_pack",
                "label": "Sample Journals",
                "path": "content/sample-journals.gw.json",
            }
        ]
    }
    if intent.wants_locales:
        provides["locales"] = {"en": "locales/en.json"}
    return provides


def _derive_provides(kind: str, intent: Intent) -> dict:
    if kind == "ruleset":
        return _derive_ruleset_provides(intent)
    if kind == "assets":
        return _derive_assets_provides(intent)
    if kind == "content":
        return _derive_content_provides(intent)
    if kind in {"addon", "theme", "library"} and intent.wants_locales:
        return {"locales": {"en": "locales/en.json"}}
    return {}


def _derive_entrypoints(kind: str, intent: Intent) -> dict:
    styles: list[str] = []
    scripts: list[str] = []

    if kind == "theme":
        styles.append(MAIN_STYLE)

    if intent.uses_js:
        # Scripted packages get a starter script and style. The package manager
        # will warn that scripted packages are trusted JavaScript.
        if MAIN_STYLE not in styles:
            styles.append(MAIN_STYLE)
        scripts.append(MAIN_SCRIPT)

    if not styles and not scripts:
        return {}

    entrypoint: dict[str, list[str]] = {}
    if styles:
        entrypoint["styles"] = styles
    if scripts:
        entrypoint["scripts"] = scripts
    return {"game": entrypoint}


def _derive_settings(intent: Intent, capabilities: list[str]) -> list[dict]:
    if "settings" not in capabilities:
        return []
    return [
        {
            "key": "enabled",
            "scope": "campaign",
            "type": "boolean",
            "default": True,
            "label": "Enabled",
        }
    ]


def build_manifest(
    *,
    package_id: str,
    name: str,
    version: str,
    kind: str,
    intent: Intent,
) -> dict:
    """A complete manifest derived from the intent.

    Referenced starter files are created by :func:`build_files`.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown package kind: {kind}")

    capabilities = derive_capabilities(kind, intent)
    compat = config.gravewright_version

    return {
        "$schema": SCHEMA_URL,
        "schemaVersion": 1,
        "sdkVersion": "1",
        "kind": kind,
        "id": package_id,
        "name": name,
        "version": version,
        "description": "",
        "authors": ["You"],
        "license": "MIT",
        "compatibility": {
            "minimum": compat,
            "verified": compat,
        },
        "capabilities": capabilities,
        "activation": _activation(kind),
        "entrypoints": _derive_entrypoints(kind, intent),
        "provides": _derive_provides(kind, intent),
        "settings": _derive_settings(intent, capabilities),
        "dependencies": [],
        "conflicts": [],
    }


# --- starter file generation ------------------------------------------------


def _readme(package_id: str, kind: str, name: str) -> str:
    return f"""# {name}

Gravewright SDK package.

- Package id: `{package_id}`
- Kind: `{kind}`

## Next steps

Validate the package:

```bash
grave package validate data/packages/{package_id}
```

Install and enable it:

```bash
grave package install {package_id} --yes --enable
```

If this package is campaign-activated, activate it in a campaign:

```bash
grave campaign package activate <campaign_id> {package_id}
```

## AI workflow

After editing, run:

```bash
grave package doctor {package_id}
```

Paste the output into your AI assistant and ask it to fix only this package.
Do not edit Gravewright core.
"""


def _main_js(package_id: str, intent: Intent) -> str:
    lines = [
        "(() => {",
        f'  const PACKAGE_ID = "{package_id}";',
        "",
        "  window.GravewrightSDK.register({",
        "    id: PACKAGE_ID,",
        "    setup(sdk) {",
        '      console.log(`[${PACKAGE_ID}] setup`, sdk.package);',
    ]

    if intent.wants_settings:
        lines.extend(
            [
                '      const enabled = sdk.settings.get("enabled", true);',
                "      if (!enabled) return;",
            ]
        )

    if intent.uses_hooks:
        lines.extend(
            [
                '      sdk.on("game:ready", () => {',
                '        console.log(`[${PACKAGE_ID}] game ready`);',
                "      });",
            ]
        )

    lines.extend(
        [
            "    },",
            "    ready(sdk) {",
            '      console.log(`[${PACKAGE_ID}] ready`, sdk.game.context());',
            "    },",
            "  });",
            "})();",
            "",
        ]
    )

    return "\n".join(lines)


def _main_css(package_id: str) -> str:
    class_name = package_id.replace("-", "_")
    return f""":root {{
  /* {package_id} theme/package variables */
}}

.gw-package-{class_name} {{
  /* Add package-specific styles here. */
}}
"""


def _sample_svg(label: str = "Sample") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <rect width="256" height="256" rx="32" fill="#24283b"/>
  <circle cx="128" cy="112" r="56" fill="#7c5cff"/>
  <text x="128" y="196" text-anchor="middle" font-family="sans-serif" font-size="24" fill="#ffffff">{label}</text>
</svg>
"""


def _sample_audio_placeholder() -> str:
    # Text placeholder keeps the scaffold pure-text. Users should replace it with
    # a real .ogg file; doctor/package validation will surface wrong content
    # later if stricter binary/audio validation is added.
    return "Replace this placeholder with a real .ogg audio file.\n"


def _actor_schema(type_id: str) -> dict:
    return {
        "type": "object",
        "title": _title(type_id),
        "properties": {
            "attributes": {
                "type": "object",
                "properties": {
                    "hp": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "integer", "default": 10},
                            "max": {"type": "integer", "default": 10},
                        },
                    }
                },
            }
        },
    }


def _item_schema(type_id: str) -> dict:
    return {
        "type": "object",
        "title": _title(type_id),
        "properties": {
            "description": {"type": "string", "default": ""},
        },
    }


def _actor_sheet(type_id: str) -> dict:
    return {
        "title": _title(type_id),
        "sections": [
            {
                "id": "main",
                "label": "Main",
                "fields": [
                    {"path": "attributes.hp.value", "label": "HP"},
                    {"path": "attributes.hp.max", "label": "Max HP"},
                ],
            }
        ],
    }


def _item_sheet(type_id: str) -> dict:
    return {
        "title": _title(type_id),
        "sections": [
            {
                "id": "main",
                "label": "Main",
                "fields": [
                    {"path": "description", "label": "Description"},
                ],
            }
        ],
    }


def _derived_rules() -> dict:
    return {
        "derived": [],
        "notes": "Add declarative derived fields here.",
    }


def _token_mappings() -> dict:
    return {
        "hp": {
            "value": "attributes.hp.value",
            "max": "attributes.hp.max",
        }
    }


def _sample_actor_pack() -> dict:
    return {
        "id": "sample-actors",
        "type": "actor_pack",
        "entries": [
            {
                "id": "sample-character",
                "type": "character",
                "name": "Sample Character",
                "data": {
                    "attributes": {
                        "hp": {
                            "value": 10,
                            "max": 10,
                        }
                    }
                },
            }
        ],
    }


def _sample_journal_pack() -> dict:
    return {
        "id": "sample-journals",
        "type": "journal_pack",
        "entries": [
            {
                "id": "welcome",
                "type": "handout",
                "title": "Welcome",
                "visibility": "private",
                "content_markdown": "Replace this with your package content.",
                "data": {},
            }
        ],
    }


def _locale_catalog(name: str) -> dict:
    return {
        "package.name": name,
        "package.description": "",
        "settings.enabled": "Enabled",
    }


def build_files(*, manifest: dict, intent: Intent) -> dict[str, str]:
    """Return starter files for a generated package.

    ``manifest.json`` is included so the writer can create the full package tree
    from a single mapping.
    """
    package_id = str(manifest["id"])
    kind = str(manifest["kind"])
    name = str(manifest["name"])

    files: dict[str, str] = {
        "manifest.json": _json(manifest),
        "README.md": _readme(package_id, kind, name),
    }

    entrypoint = manifest.get("entrypoints", {}).get("game", {})
    for style in entrypoint.get("styles", []) or []:
        files[style] = _main_css(package_id)
    for script in entrypoint.get("scripts", []) or []:
        files[script] = _main_js(package_id, intent)

    provides = manifest.get("provides", {})

    for actor in provides.get("actorTypes", []) or []:
        actor_id = actor["id"]
        if actor.get("schema"):
            files[actor["schema"]] = _json(_actor_schema(actor_id))
        if actor.get("sheet"):
            files[actor["sheet"]] = _json(_actor_sheet(actor_id))

    for item in provides.get("itemTypes", []) or []:
        item_id = item["id"]
        if item.get("schema"):
            files[item["schema"]] = _json(_item_schema(item_id))
        if item.get("sheet"):
            files[item["sheet"]] = _json(_item_sheet(item_id))

    for path in (provides.get("rules", {}) or {}).values():
        files[path] = _json(_derived_rules())

    for path in (provides.get("mappings", {}) or {}).values():
        files[path] = _json(_token_mappings())

    for pack in provides.get("contentPacks", []) or []:
        pack_type = pack.get("type")
        path = pack.get("path")
        if not path:
            continue
        if pack_type == "journal_pack":
            files[path] = _json(_sample_journal_pack())
        else:
            files[path] = _json(_sample_actor_pack())

    for _locale, path in (provides.get("locales", {}) or {}).items():
        files[path] = _json(_locale_catalog(name))

    assets = provides.get("assets", {}) or {}
    for category, entries in assets.items():
        for entry in entries or []:
            path = entry.get("path")
            if not path:
                continue
            if category == "audio":
                files[path] = _sample_audio_placeholder()
            else:
                files[path] = _sample_svg(entry.get("label") or "Sample")

    return files


def build_package(
    *,
    package_id: str,
    name: str,
    version: str = DEFAULT_VERSION,
    kind: str,
    intent: Intent,
) -> PackageScaffold:
    """Build a complete pure scaffold: manifest + starter files."""
    manifest = build_manifest(
        package_id=package_id,
        name=name,
        version=version,
        kind=kind,
        intent=intent,
    )
    return PackageScaffold(
        manifest=manifest,
        files=build_files(manifest=manifest, intent=intent),
    )
