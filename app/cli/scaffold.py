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

from app.engine.sdk.package_manifest import SDK_VERSION

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
    # Explicit actor/item sheet type ids (e.g. ("character", "npc")). When set,
    # these drive generation and supersede the legacy has_characters/has_monsters
    # /has_items booleans. Ids are normalized to lowercase kebab-case.
    actor_types: tuple[str, ...] | None = None
    item_types: tuple[str, ...] | None = None
    # The system's core dice mechanic; seeds the character schema and sheet with
    # one minimal example. See MECHANICS for the supported ids.
    mechanic: str = "none"
    # Optional text-only sheet sections added to every actor sheet.
    wants_biography: bool = False
    wants_notes: bool = False
    wants_effects: bool = False
    # Which declared types get a sheet. ``None`` means "all declared types";
    # a tuple restricts generation to the named types (the rest stay sheet-less).
    sheet_types: tuple[str, ...] | None = None
    # False selects declarative Sheet IR (the simpler mode); True selects HTML
    # templates and the HTML sheet runtime (full-control mode).
    html_sheets: bool = False
    has_rolls: bool = False
    has_combat: bool = False

    # Package provides.
    wants_content: bool = False
    wants_settings: bool = False
    wants_locales: bool = False

    # Runtime/client behavior.
    uses_js: bool = False
    uses_sheet_runtime: bool = False
    uses_combat_runtime: bool = False
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
        if _ruleset_item_type_ids(intent):
            _add(caps, "items.register")
        if _ruleset_has_any_sheet(intent):
            if intent.html_sheets:
                _add(caps, "sheets.html")
                _add(caps, "assets.styles")
                if _ruleset_uses_rich_text(intent):
                    _add(caps, "sheets.richText")
            else:
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
        if intent.uses_sheet_runtime:
            _add(caps, "sheets.runtime")
        if intent.uses_combat_runtime:
            _add(caps, "combat.runtime")
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


SHARED_SHEET_STYLE = "styles/sheet.css"


def _normalize_ids(values) -> list[str]:
    """Lowercase-kebab-case and de-duplicate type ids, preserving order."""
    out: list[str] = []
    for value in values or []:
        slug = _slugify(str(value))
        if slug and slug not in out:
            out.append(slug)
    return out


def _ruleset_actor_type_ids(intent: Intent) -> list[str]:
    """The actor type ids a ruleset scaffold declares, in stable order."""
    if intent.actor_types is not None:
        return _normalize_ids(intent.actor_types)
    ids: list[str] = []
    if intent.has_characters or not intent.has_monsters:
        ids.append("character")
    if intent.has_monsters:
        ids.append("monster")
    return ids


def _ruleset_item_type_ids(intent: Intent) -> list[str]:
    """The item type ids a ruleset scaffold declares, in stable order."""
    ids = _normalize_ids(intent.item_types) if intent.item_types is not None else (
        ["item"] if intent.has_items else []
    )
    if intent.wants_effects and "effect" not in ids:
        ids.append("effect")
    return ids


def _ruleset_inventory_type_ids(intent: Intent) -> list[str]:
    return [type_id for type_id in _ruleset_item_type_ids(intent) if type_id != "effect"]


def declared_sheet_type_ids(intent: Intent) -> list[str]:
    """Every actor/item type id a ruleset scaffold declares."""
    return _ruleset_actor_type_ids(intent) + _ruleset_item_type_ids(intent)


def _mechanic_actor_id(intent: Intent) -> str | None:
    """The actor type that carries the core-mechanic example (character first)."""
    actor_ids = _ruleset_actor_type_ids(intent)
    if not actor_ids:
        return None
    return "character" if "character" in actor_ids else actor_ids[0]


def _type_wants_sheet(type_id: str, intent: Intent) -> bool:
    """Whether ``type_id`` should get a sheet given the ``--sheets`` selection."""
    if not intent.has_sheets:
        return False
    return intent.sheet_types is None or type_id in intent.sheet_types


def _sheet_descriptor(type_id: str, intent: Intent) -> str | dict:
    """Return the manifest sheet value for the selected authoring mode."""
    if not intent.html_sheets:
        return f"layouts/{type_id}.sheet.gw.json"
    return {
        "mode": "html",
        "template": f"sheets/{type_id}.html",
        "style": SHARED_SHEET_STYLE,
    }


def _sheet_type_kinds(intent: Intent) -> list[tuple[str, str]]:
    """``(kind_dir, type_id)`` for every type that gets a sheet."""
    out: list[tuple[str, str]] = []
    for tid in _ruleset_actor_type_ids(intent):
        if _type_wants_sheet(tid, intent):
            out.append(("actors", tid))
    for tid in _ruleset_item_type_ids(intent):
        if _type_wants_sheet(tid, intent):
            out.append(("items", tid))
    return out


def _ruleset_has_any_sheet(intent: Intent) -> bool:
    return bool(_sheet_type_kinds(intent))


def _actor_type(type_id: str, intent: Intent) -> dict:
    raw = {
        "id": type_id,
        "label": _title(type_id),
        "schema": f"schemas/actors/{type_id}.schema.json",
    }
    if _type_wants_sheet(type_id, intent):
        raw["sheet"] = _sheet_descriptor(type_id, intent)
    return raw


def _item_type(type_id: str, intent: Intent) -> dict:
    raw = {
        "id": type_id,
        "label": _title(type_id),
        "schema": f"schemas/items/{type_id}.schema.json",
    }
    if _type_wants_sheet(type_id, intent):
        raw["sheet"] = _sheet_descriptor(type_id, intent)
    return raw


def _derive_ruleset_provides(intent: Intent) -> dict:
    provides: dict = {
        "storage": {"model": "scoped-json-v1"},
        "actorTypes": [_actor_type(t, intent) for t in _ruleset_actor_type_ids(intent)],
    }

    item_ids = _ruleset_item_type_ids(intent)
    if item_ids:
        provides["itemTypes"] = [_item_type(t, intent) for t in item_ids]

    rules: dict[str, str] = {}
    if intent.has_rolls:
        rules["derived"] = "rules/derived.gw.json"
    if (
        _ruleset_roll_action(intent) is not None
        or _ruleset_inventory_type_ids(intent)
        or intent.wants_effects
    ):
        # The mechanic's roll preset is a real, server-executed system action.
        rules["actions"] = "rules/actions.gw.json"
    if rules:
        provides["rules"] = rules

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


def _ruleset_uses_rich_text(intent: Intent) -> bool:
    """Whether any generated template mounts a block (rich-text) editor.

    Item sheets always edit a rich description; actor sheets do when the
    biography or notes tab is enabled. ``sheets.richText`` gates the editor.
    """
    kinds = _sheet_type_kinds(intent)
    if any(kind_dir == "items" for kind_dir, _ in kinds):
        return True
    if (intent.wants_biography or intent.wants_notes) and any(
        kind_dir == "actors" for kind_dir, _ in kinds
    ):
        return True
    return False


def _html_sheet_style_paths(kind: str, intent: Intent) -> list[str]:
    """The shared sheet stylesheet, which must load via the game entrypoint.

    A ``sheet.style`` declaration alone does not inject CSS into the page; the
    file must also be listed in ``entrypoints.game.styles``.
    """
    if kind == "ruleset" and intent.html_sheets and _ruleset_has_any_sheet(intent):
        return [SHARED_SHEET_STYLE]
    return []


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

    for style in _html_sheet_style_paths(kind, intent):
        if style not in styles:
            styles.append(style)

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
    # The compatibility window targets the SDK API line (SDK_VERSION), which is
    # what the manifest validator compares against — not the core marketing
    # version. Using config.gravewright_version here (e.g. "2.0.0-alpha.0") made
    # every freshly scaffolded package validate as `sdk.validation.incompatible`.
    compat = SDK_VERSION

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


# --- core mechanics ---------------------------------------------------------
#
# A field spec is ``{path, label, type, default[, options]}`` where ``type`` is
# ``number``, ``text`` or ``select``. ``path`` is relative to ``system`` and may
# be dotted (e.g. ``attributes.strength``). Each mechanic seeds one minimal
# example — fields plus a single sample roll button (``data-action`` placeholder
# wired to no controller) — into the character (or first) actor sheet.

_DND_ABILITIES = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)


def _ability_fields(names, *, default: int = 10) -> list[dict]:
    return [
        {"path": f"attributes.{name}", "label": _title(name), "type": "number", "default": default}
        for name in names
    ]


MECHANICS: dict[str, dict] = {
    "d20-attribute-modifier-skill": {
        "label": "d20 + attribute modifier + skill",
        "fields": _ability_fields(_DND_ABILITIES)
        + [{"path": "skills.athletics", "label": "Athletics", "type": "number", "default": 0}],
        "roll": {
            "label": "Strength + Athletics check",
            "action": "strength-check",
            "formula": "1d20 + floor((@sheet.attributes.strength - 10) / 2) + @sheet.skills.athletics",
        },
    },
    "d20-attribute-modifier": {
        "label": "d20 + attribute modifier",
        "fields": _ability_fields(_DND_ABILITIES),
        "roll": {
            "label": "Strength check",
            "action": "ability-check",
            "formula": "1d20 + floor((@sheet.attributes.strength - 10) / 2)",
        },
    },
    "d20-roll-under": {
        "label": "d20 roll-under attribute",
        "fields": _ability_fields(_DND_ABILITIES, default=12),
        "roll": {
            "label": "Strength roll-under",
            "action": "roll-under-check",
            "formula": "under(1, 20, clamp(@sheet.attributes.strength, 1, 20))",
        },
    },
    "d100-percentile": {
        "label": "d100 percentile skills",
        "fields": [
            {"path": "skills.perception", "label": "Perception %", "type": "number", "default": 50}
        ],
        "roll": {
            "label": "Perception percentile check",
            "action": "percentile-check",
            "formula": "under(1, 100, clamp(@sheet.skills.perception, 1, 100))",
        },
    },
    "dice-pool-successes": {
        "label": "Dice pool — count successes",
        "fields": [
            {"path": "pool.size", "label": "Pool size", "type": "number", "default": 3},
            {"path": "pool.target", "label": "Target number", "type": "number", "default": 6},
        ],
        "roll": {
            "label": "Roll success pool",
            "action": "pool-roll",
            "formula": "successes(clamp(@sheet.pool.size, 1, 100), 6, clamp(@sheet.pool.target, 1, 6))",
        },
    },
    "dice-pool-count-hits": {
        "label": "Dice pool — count hits",
        "fields": [
            {"path": "pool.size", "label": "Pool size", "type": "number", "default": 6},
            {"path": "pool.hit", "label": "Hit on", "type": "number", "default": 5},
        ],
        "roll": {
            "label": "Roll hit pool",
            "action": "pool-roll",
            "formula": "successes(clamp(@sheet.pool.size, 1, 100), 6, clamp(@sheet.pool.hit, 1, 6))",
        },
    },
    "exploding-dice": {
        "label": "Exploding dice",
        "fields": [
            {"path": "die.size", "label": "Die size", "type": "number", "default": 6},
            {"path": "die.explode", "label": "Explode threshold", "type": "number", "default": 6},
        ],
        "roll": {
            "label": "Exploding roll",
            "action": "exploding-roll",
            "formula": "explode(@sheet.die.size, @sheet.die.explode)",
        },
    },
    "step-dice": {
        "label": "Step dice (d4–d12)",
        "fields": [
            {
                "path": f"attributes.{name}",
                "label": _title(name),
                "type": "select",
                "options": [
                    {"value": sides, "label": f"d{sides}"}
                    for sides in (4, 6, 8, 10, 12)
                ],
                "default": 6,
            }
            for name in ("strength", "agility", "mind", "spirit")
        ],
        "roll": {
            "label": "Strength step die",
            "action": "step-roll",
            "formula": "die(@sheet.attributes.strength)",
        },
    },
    "fudge-fate": {
        "label": "Fudge / Fate (4dF)",
        "fields": [
            {"path": "aspects", "label": "Aspects", "type": "text", "default": ""},
            {"path": "approaches.careful", "label": "Careful", "type": "number", "default": 0},
        ],
        "roll": {
            "label": "Careful approach",
            "action": "fate-roll",
            "formula": "fate() + @sheet.approaches.careful",
        },
    },
    "2d6-pbta": {
        "label": "2d6 Powered by the Apocalypse",
        "fields": [
            {"path": f"stats.{stat}", "label": _title(stat), "type": "number", "default": 0}
            for stat in ("cool", "hard", "hot", "sharp", "weird")
        ],
        "roll": {"label": "Roll move", "action": "move-roll", "formula": "2d6 + @sheet.stats.cool"},
    },
    "2d20": {
        "label": "2d20 system",
        "fields": _ability_fields(
            ("agility", "brawn", "coordination", "insight"), default=8
        )
        + [{"path": "skills.athletics", "label": "Athletics", "type": "number", "default": 1}],
        "roll": {
            "label": "Agility + Athletics test",
            "action": "d20-test",
            "formula": "under(2, 20, clamp(@sheet.attributes.agility + @sheet.skills.athletics, 1, 20))",
        },
    },
    "year-zero-d6-pool": {
        "label": "Year Zero d6 pool",
        "fields": [
            {"path": f"attributes.{name}", "label": _title(name), "type": "number", "default": 3}
            for name in ("strength", "agility", "wits", "empathy")
        ],
        "roll": {
            "label": "Strength dice pool",
            "action": "year-zero-roll",
            "formula": "successes(clamp(@sheet.attributes.strength, 1, 100), 6, 6)",
        },
    },
    "cards": {
        "label": "Card draw resolution",
        "fields": [{"path": "hand", "label": "Hand", "type": "text", "default": ""}],
        "roll": {"label": "Draw card", "action": "draw-card", "formula": "draw(52)"},
    },
    "custom": {
        "label": "Custom mechanic",
        "fields": [{"path": "resource", "label": "Resource", "type": "number", "default": 0}],
        "roll": {
            "label": "Custom resource roll",
            "action": "custom-roll",
            "formula": "1d20 + @sheet.resource",
        },
    },
    "none": {
        "label": "No dice mechanic",
        "fields": [],
        "roll": None,
    },
}


def mechanic_ids() -> list[str]:
    """Supported core-mechanic ids, in presentation order."""
    return list(MECHANICS.keys())


def _mechanic(mechanic_id: str) -> dict:
    return MECHANICS.get(mechanic_id, MECHANICS["none"])


def _ruleset_roll_action(intent: Intent) -> dict | None:
    """Return the generated action for the selected mechanic, when it rolls."""
    roll = _mechanic(intent.mechanic).get("roll")
    if not isinstance(roll, dict):
        return None
    return {
        "id": roll["action"],
        "type": "roll",
        "label": roll["label"],
        "formula": roll["formula"],
    }


def _actions_rules(intent: Intent) -> dict:
    actions: dict[str, dict] = {}
    action = _ruleset_roll_action(intent)
    if action is not None:
        action_id = action.pop("id")
        actions[action_id] = action
    if _ruleset_inventory_type_ids(intent):
        actions["add-item"] = {
            "type": "append",
            "target": "items",
            "value": "@drop.entry",
        }
    if intent.wants_effects:
        actions["add-effect"] = {
            "type": "append",
            "target": "effects",
            "value": "@drop.entry",
        }
    return {"actions": actions}


# --- schema / template generation -------------------------------------------


# Text-only sections (no numbers, no rich text) for the optional tabs.
def _field_schema(field: dict) -> dict:
    kind = field["type"]
    if kind == "number":
        default = field.get("default", 0)
        return {"type": "integer" if isinstance(default, int) else "number", "default": default}
    if kind == "bool":
        return {"type": "boolean", "default": bool(field.get("default", False))}
    if kind == "select":
        options = [
            option.get("value") if isinstance(option, dict) else option
            for option in field["options"]
        ]
        value_type = "integer" if all(isinstance(option, int) for option in options) else "string"
        return {"type": value_type, "enum": options, "default": field.get("default", options[0])}
    return {"type": "string", "default": field.get("default", "")}


def _schema_from_fields(fields: list[dict]) -> dict:
    """Build nested JSON-schema properties from dotted field paths."""
    props: dict = {}
    for field in fields:
        parts = field["path"].split(".")
        cursor = props
        for part in parts[:-1]:
            node = cursor.setdefault(part, {"type": "object", "properties": {}})
            cursor = node["properties"]
        cursor[parts[-1]] = _field_schema(field)
    return props


def _actor_schema(type_id: str, intent: Intent, *, is_mechanic: bool) -> dict:
    properties: dict = {}
    if is_mechanic:
        properties.update(_schema_from_fields(_mechanic(intent.mechanic)["fields"]))
    # Biography/Notes are stored as rich-text documents (the block-editor shape).
    if intent.wants_biography:
        properties["biography"] = _rich_doc_schema()
    if intent.wants_notes:
        properties["notes"] = _rich_doc_schema()
    # Items dropped onto the sheet collect here (see the Items tab).
    if _ruleset_inventory_type_ids(intent):
        properties["items"] = {"type": "array", "default": []}
    if intent.wants_effects:
        properties["effects"] = {"type": "array", "default": []}
    return {"type": "object", "title": _title(type_id), "properties": properties}


_WEAPON_TYPES = {"weapon", "ammunition", "wand", "rod", "staff", "grenade", "explosive", "maneuver", "technique"}
_ARMOR_TYPES = {"armor", "shield", "clothing"}
_POWER_TYPES = {"spell", "power", "ability", "feat", "talent", "trait", "ritual", "cantrip", "prayer", "blessing", "curse", "invocation"}
_CONSUMABLE_TYPES = {"consumable", "potion", "scroll", "poison", "drug", "food"}


def _item_fields(type_id: str) -> list[dict]:
    fields: list[dict] = [
        {"path": "category", "label": "Category", "type": "text", "default": type_id}
    ]
    if type_id in _WEAPON_TYPES:
        fields += [
            {"path": "damage", "label": "Damage", "type": "text", "default": "1d6"},
            {"path": "attackBonus", "label": "Attack bonus", "type": "number", "default": 0},
            {"path": "damageType", "label": "Damage type", "type": "text", "default": "physical"},
            {"path": "equipped", "label": "Equipped", "type": "bool", "default": False},
        ]
    elif type_id in _ARMOR_TYPES:
        fields += [
            {"path": "armor", "label": "Armor", "type": "number", "default": 1},
            {"path": "equipped", "label": "Equipped", "type": "bool", "default": False},
        ]
    elif type_id in _POWER_TYPES:
        fields += [
            {"path": "level", "label": "Level", "type": "number", "default": 0},
            {"path": "cost", "label": "Cost", "type": "number", "default": 0},
            {"path": "damage", "label": "Effect / damage", "type": "text", "default": ""},
        ]
    elif type_id in _CONSUMABLE_TYPES:
        fields += [
            {"path": "quantity", "label": "Quantity", "type": "number", "default": 1},
            {"path": "effect", "label": "Effect", "type": "text", "default": ""},
        ]
    else:
        fields.append({"path": "quantity", "label": "Quantity", "type": "number", "default": 1})
    return fields


def _item_schema(type_id: str) -> dict:
    if type_id == "effect":
        return {
            "type": "object",
            "title": "Effect",
            "properties": {
                "category": {"type": "string", "default": "condition"},
                "condition": {"type": "string", "default": ""},
                "enabled": {"type": "boolean", "default": True},
                "modifiers": {
                    "type": "array",
                    "default": [{"target": "roll.any", "operation": "add", "value": 0, "label": "Effect modifier"}],
                },
                "description": _rich_doc_schema(),
            },
        }
    properties = _schema_from_fields(_item_fields(type_id))
    properties["description"] = _rich_doc_schema()
    return {"type": "object", "title": _title(type_id), "properties": properties}


def _rich_doc_schema() -> dict:
    """A block-editor document field (``gw-journal-doc-v1`` shape) — free-form object."""
    return {"type": "object", "default": {}}


def _sheet_class(package_id: str) -> str:
    """The shared package-scoped root class used by every sheet template/CSS."""
    return f"gw-{package_id}-sheet"


def _field_html(field: dict) -> str:
    bind = f"system.{field['path']}"
    if field["type"] == "number":
        control = '<input type="number" data-bind="{}">'.format(bind)
    elif field["type"] == "bool":
        control = '<input type="checkbox" data-bind="{}">'.format(bind)
    elif field["type"] == "select":
        options = "".join(
            f'<option value="{o.get("value")}">{o.get("label", o.get("value"))}</option>'
            if isinstance(o, dict)
            else f'<option value="{o}">{o}</option>'
            for o in field["options"]
        )
        control = f'<select data-bind="{bind}">{options}</select>'
    elif field["type"] == "textarea":
        control = f'<textarea data-bind="{bind}"></textarea>'
    else:
        control = f'<input data-bind="{bind}">'
    return f"      {field['label']}\n      {control}"


def _rich_editor_html(root: str, path: str) -> list[str]:
    """A block (Notion-style) editor host bound to a sheet data path."""
    return [f'    <div class="{root}__editor" data-rich-editor="system.{path}"></div>']


def _actor_html(package_id: str, type_id: str, intent: Intent, *, is_mechanic: bool) -> str:
    root = _sheet_class(package_id)
    title = _title(type_id)
    header = [
        f'<form class="{root}" data-sheet-type="{type_id}">',
        f'  <header class="{root}__header">',
        f'    <label>\n      Name\n      <input data-bind="actor.name" aria-label="{title} name">\n    </label>',
        f'    <span class="{root}__type" data-text="actor.type"></span>',
        "  </header>",
    ]

    # Each panel is (label, [content lines]); two or more panels render as tabs.
    panels: list[tuple[str, list[str]]] = []
    if is_mechanic:
        mechanic = _mechanic(intent.mechanic)
        content: list[str] = []
        if mechanic["fields"]:
            content.append(f'    <div class="{root}__fields">')
            for field in mechanic["fields"]:
                content.append("      <label>")
                content.append(_field_html(field))
                content.append("      </label>")
            content.append("    </div>")
        if mechanic["roll"]:
            roll = mechanic["roll"]
            content.append(
                f'    <button type="button" data-action="{roll["action"]}">{roll["label"]}</button>'
            )
        if content:
            panels.append(("Main", content))
    if intent.wants_biography:
        panels.append(("Biography", _rich_editor_html(root, "biography")))
    if intent.wants_notes:
        panels.append(("Notes", _rich_editor_html(root, "notes")))
    if _ruleset_inventory_type_ids(intent):
        # Items are dropped onto the sheet (core drop flow) and listed here.
        panels.append(
            (
                "Items",
                [
                    f'    <div class="{root}__items" data-item-list="system.items"'
                    ' data-drop-zone="items" data-accepts="item"'
                    ' data-empty-text="Drag items here to add them."></div>'
                ],
            )
        )
    if intent.wants_effects:
        panels.append(
            (
                "Effects",
                [
                    f'    <div class="{root}__items" data-item-list="system.effects"'
                    ' data-drop-zone="effects" data-accepts="effect"'
                    ' data-empty-text="Drag effects here to apply them."></div>'
                ],
            )
        )

    return "\n".join(header + _render_panels(root, panels) + ["</form>"]) + "\n"


def _render_panels(root: str, panels: list[tuple[str, list[str]]]) -> list[str]:
    if not panels:
        return []
    if len(panels) == 1:
        _label, content = panels[0]
        return [f'  <section class="{root}__panel">', *content, "  </section>"]
    body = [f'  <nav class="{root}__tabs" role="tablist" aria-label="Sheet sections">']
    for index, (label, _) in enumerate(panels):
        tab_id = label.lower()
        body.append(
            f'    <button type="button" class="{root}__tab" data-tab="{tab_id}"'
            f' role="tab" aria-selected="{"true" if index == 0 else "false"}"'
            f' aria-controls="panel-{tab_id}">{label}</button>'
        )
    body.append("  </nav>")
    for index, (label, content) in enumerate(panels):
        tab_id = label.lower()
        body.append(
            f'  <section id="panel-{tab_id}" class="{root}__panel"'
            f' data-tab-panel="{tab_id}" role="tabpanel" aria-label="{label}"'
            f'{" hidden" if index else ""}>'
        )
        body.extend(content)
        body.append("  </section>")
    return body


def _item_html(package_id: str, type_id: str) -> str:
    root = _sheet_class(package_id)
    title = _title(type_id)
    fields = (
        [
            {"path": "category", "label": "Category", "type": "text"},
            {"path": "condition", "label": "Condition", "type": "text"},
            {"path": "enabled", "label": "Enabled", "type": "bool"},
            {"path": "modifiers.0.target", "label": "Modifier target", "type": "text"},
            {
                "path": "modifiers.0.operation",
                "label": "Operation",
                "type": "select",
                "options": ["add", "subtract", "add_dice", "advantage", "disadvantage", "resistance", "vulnerability", "immunity", "reduce", "damage_over_time", "heal_over_time"],
            },
            {"path": "modifiers.0.value", "label": "Value / dice", "type": "text"},
        ]
        if type_id == "effect"
        else _item_fields(type_id)
    )
    field_lines = [f'  <div class="{root}__fields">']
    for field in fields:
        field_lines.extend(["    <label>", _field_html(field), "    </label>"])
    field_lines.append("  </div>")
    fields_html = "\n".join(field_lines)
    editor = "\n".join(_rich_editor_html(root, "description"))
    return f"""<form class="{root}" data-sheet-type="{type_id}">
  <header class="{root}__header">
    <label>
      Name
      <input data-bind="item.name" aria-label="{title} name">
    </label>
    <span class="{root}__type" data-text="item.type"></span>
  </header>

{fields_html}
{editor}
</form>
"""


def _declarative_field(field: dict) -> dict:
    node_type = {
        "number": "numberField",
        "select": "selectField",
        "textarea": "textArea",
        "bool": "checkboxField",
    }.get(field["type"], "textField")
    node = {
        "type": node_type,
        "label": field["label"],
        "path": f"sheet.{field['path']}",
    }
    if field["type"] == "select":
        node["options"] = field["options"]
    return node


def _declarative_actor_sheet(type_id: str, intent: Intent, *, is_mechanic: bool) -> dict:
    children: list[dict] = []
    if is_mechanic:
        children.extend(_declarative_field(field) for field in _mechanic(intent.mechanic)["fields"])
        action = _ruleset_roll_action(intent)
        if action:
            children.append({
                "type": "rollButton",
                "label": action["label"],
                "action": action["id"],
            })
    if intent.wants_biography:
        children.append({"type": "textArea", "label": "Biography", "path": "sheet.biography"})
    if intent.wants_notes:
        children.append({"type": "textArea", "label": "Notes", "path": "sheet.notes"})
    if _ruleset_inventory_type_ids(intent):
        children.append(
            {
                "type": "itemList",
                "label": "Items",
                "path": "sheet.items",
                "dropZone": {
                    "type": "dropZone",
                    "id": "items",
                    "accepts": ["item"],
                    "onDrop": "add-item",
                },
            }
        )
    if intent.wants_effects:
        children.append(
            {
                "type": "itemList",
                "label": "Effects",
                "path": "sheet.effects",
                "row": {"type": "effectRow"},
                "dropZone": {
                    "type": "dropZone",
                    "id": "effects",
                    "accepts": ["effect"],
                    "onDrop": "add-effect",
                },
            }
        )
    return {
        "kind": "actorSheet",
        "actorType": type_id,
        "title": {"bind": "core.name"},
        "body": {"type": "section", "variant": "main", "children": children},
    }


def _declarative_item_sheet(type_id: str) -> dict:
    fields = (
        [
            {"path": "category", "label": "Category", "type": "text"},
            {"path": "condition", "label": "Condition", "type": "text"},
            {"path": "enabled", "label": "Enabled", "type": "bool"},
            {"path": "modifiers.0.target", "label": "Modifier target", "type": "text"},
            {"path": "modifiers.0.operation", "label": "Operation", "type": "text"},
            {"path": "modifiers.0.value", "label": "Value / dice", "type": "text"},
        ]
        if type_id == "effect"
        else _item_fields(type_id)
    )
    return {
        "kind": "itemSheet",
        "itemType": type_id,
        "title": {"bind": "core.name"},
        "body": {
            "type": "section",
            "variant": "main",
            "children": [
                *[_declarative_field(field) for field in fields],
                {"type": "textArea", "label": "Description", "path": "sheet.description"},
            ],
        },
    }


def _shared_sheet_css(package_id: str) -> str:
    root = _sheet_class(package_id)
    return f""".{root} {{
  display: grid;
  gap: 1rem;
  padding: 1rem;
}}

.{root}__header {{
  display: flex;
  align-items: center;
  gap: 0.75rem;
}}

.{root} input,
.{root} select,
.{root} textarea {{
  width: 100%;
}}

.{root}__fields {{
  display: grid;
  gap: 0.5rem;
}}

.{root}__rolls {{
  display: flex;
  gap: 0.5rem;
}}

.{root}__tabs {{
  display: flex;
  gap: 0.25rem;
  border-bottom: 1px solid currentColor;
}}

.{root}__tab {{
  border: 0;
  background: transparent;
  padding: 0.4rem 0.75rem;
  cursor: pointer;
  opacity: 0.6;
  color: inherit;
  font: inherit;
}}

.{root}__tab.is-active {{
  opacity: 1;
  border-bottom: 2px solid currentColor;
}}

.{root}__panel[hidden] {{
  display: none;
}}

.{root}__editor {{
  min-height: 8rem;
  border: 1px solid currentColor;
  border-radius: 0.25rem;
  padding: 0.5rem;
}}

.{root}__items {{
  display: grid;
  gap: 0.25rem;
  min-height: 5rem;
  padding: 0.75rem;
  border: 1px dashed color-mix(in srgb, currentColor 45%, transparent);
  border-radius: 0.35rem;
}}

.{root}__items.is-drop-active {{
  border-color: currentColor;
  background: color-mix(in srgb, currentColor 8%, transparent);
}}

.gw-item-list__row {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}}

.gw-item-list__open {{
  flex: 1;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}}

.gw-item-list__editor {{
  margin-bottom: 0.75rem;
  padding: 0.75rem;
  border: 1px solid color-mix(in srgb, currentColor 30%, transparent);
  border-radius: 0.35rem;
}}

.gw-item-list__editor[hidden] {{
  display: none;
}}

[data-actor-sheet-root].is-drop-active {{
  outline: 2px dashed currentColor;
  outline-offset: -4px;
}}
"""


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

    provides = manifest.get("provides", {})

    entrypoint = manifest.get("entrypoints", {}).get("game", {})
    # The shared sheet stylesheet appears in the game entrypoint but gets its own
    # content below, so skip the generic placeholder for it.
    sheet_styles = set(_html_sheet_style_paths(kind, intent))
    for style in entrypoint.get("styles", []) or []:
        if style not in sheet_styles:
            files[style] = _main_css(package_id)
    for script in entrypoint.get("scripts", []) or []:
        files[script] = _main_js(package_id, intent)

    mechanic_actor = _mechanic_actor_id(intent)
    for actor in provides.get("actorTypes", []) or []:
        actor_id = actor["id"]
        sheet = actor.get("sheet")
        has_html_sheet = isinstance(sheet, dict) and sheet.get("mode") == "html"
        if actor.get("schema"):
            files[actor["schema"]] = _json(
                _actor_schema(actor_id, intent, is_mechanic=actor_id == mechanic_actor)
            )
        if has_html_sheet:
            files[sheet["template"]] = _actor_html(
                package_id, actor_id, intent, is_mechanic=actor_id == mechanic_actor
            )
        elif isinstance(sheet, str):
            files[sheet] = _json(
                _declarative_actor_sheet(
                    actor_id, intent, is_mechanic=actor_id == mechanic_actor
                )
            )

    for item in provides.get("itemTypes", []) or []:
        item_id = item["id"]
        sheet = item.get("sheet")
        has_html_sheet = isinstance(sheet, dict) and sheet.get("mode") == "html"
        if item.get("schema"):
            files[item["schema"]] = _json(_item_schema(item_id))
        if has_html_sheet:
            files[sheet["template"]] = _item_html(package_id, item_id)
        elif isinstance(sheet, str):
            files[sheet] = _json(_declarative_item_sheet(item_id))

    if intent.html_sheets and _ruleset_has_any_sheet(intent):
        files[SHARED_SHEET_STYLE] = _shared_sheet_css(package_id)

    rules = provides.get("rules", {}) or {}
    if rules.get("derived"):
        files[rules["derived"]] = _json(_derived_rules())
    if rules.get("actions"):
        files[rules["actions"]] = _json(_actions_rules(intent))

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
