# Package manifest reference — SDK v1

Every Gravewright SDK package has a `manifest.json`. The manifest describes the package; it never executes code.

The manifest is the center of the declarative package model. Before filling out individual fields, read [`declarative-model.md`](declarative-model.md) to understand how package data, capabilities, entrypoints, and optional runtime code fit together.

Manifests validate against:

```text
schemas/gravewright-package-v1.schema.json
```

## Minimal addon

```json
{
  "$schema": "https://raw.githubusercontent.com/Gravewright/gravewright/main/schemas/gravewright-package-v1.schema.json",
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "addon",
  "id": "my-package",
  "name": "My Package",
  "version": "0.1.0",
  "description": "Optional campaign extension.",
  "authors": ["Example Author"],
  "license": "MIT",
  "compatibility": {
    "minimum": "1.0.0-rc.1",
    "verified": "1.0.0-rc.1",
    "maximum": "1.x"
  },
  "capabilities": ["assets.scripts"],
  "activation": {
    "scope": "campaign",
    "mode": "multiple"
  },
  "entrypoints": {
    "game": {
      "scripts": ["assets/main.js"]
    }
  },
  "provides": {}
}
```

## Required top-level fields

| Field | Type | Required value / rule |
|---|---:|---|
| `$schema` | string | Recommended. Should point to the SDK v1 schema. |
| `schemaVersion` | integer | Must be `1`. |
| `sdkVersion` | string | Must be `"1"`. |
| `kind` | string | One of `ruleset`, `addon`, `library`, `content`, `theme`, `assets`. |
| `id` | string | Lowercase kebab-case: `^[a-z0-9]+(-[a-z0-9]+)*$`. Must match the package directory name. |
| `name` | string | Human-readable package name. |
| `version` | string | Package version. Semver-style values are recommended. |
| `compatibility` | object | At least one of `minimum`, `verified`, or `maximum`. |
| `capabilities` | string array | Requested SDK capabilities. Must use the allow-list. |
| `activation` | object | Activation scope and mode. `mode` is required. |
| `entrypoints` | object | Named style/script entrypoints. The table loads `game`. |
| `provides` | object | Kind-specific declarative data. Use `{}` if the package provides no data. |

## Optional top-level fields

| Field | Type | Purpose |
|---|---:|---|
| `description` | string | Package summary shown to users/operators. |
| `authors` | array | Strings or objects. Used for package summaries. |
| `license` | string | Package license or content rights note. |
| `homepage` | string | Package homepage. |
| `repository` | string | Source repository. |
| `distribution` | object | Distribution metadata for zip/git/directory packages. |
| `dependencies` | array | Required package relationships. |
| `conflicts` | array | Packages that cannot coexist with this package. |
| `settings` | array | Declared package settings. |
| `display` | object | Optional UI metadata such as `color`. |

## Compatibility

```json
"compatibility": {
  "minimum": "1.0.0-rc.1",
  "verified": "1.0.0-rc.1",
  "maximum": "1.x"
}
```

The engine computes a compatibility status against the running **SDK API version
line** (the same line named by `sdkVersion`, frozen at `1` by Alpha 2.0.0), not
the core Gravewright marketing version — so a core release bump does not
retroactively make SDK 1 packages incompatible:

- `compatible` — the package is within the declared compatibility window.
- `unverified` — the package did not declare enough information to prove compatibility.
- `incompatible` — the package is outside the declared compatibility window.

## Activation

```json
"activation": {
  "scope": "campaign",
  "mode": "multiple"
}
```

Allowed `scope` values:

- `campaign`
- `global`
- `user`

Allowed `mode` values:

- `exclusive` — exactly one active package in this slot. Required for `ruleset`.
- `multiple` — many packages can be active. Required for `addon`, `theme`, `content`, and `assets`.
- `passive` — not activated directly; loaded as a dependency. Required for `library`.
- `none` — reserved for non-activated metadata/content use.

## Entrypoints

```json
"entrypoints": {
  "game": {
    "styles": ["assets/package.css"],
    "scripts": ["assets/package.js"]
  }
}
```

Entrypoints are named groups of browser assets. The current table runtime loads `game`.

Path rules:

- paths are package-relative;
- paths must not contain `..`;
- paths must not be absolute;
- paths must not be URLs;
- every referenced path must exist.

## `provides`

`provides` contains declarative package data. Its shape is kind-specific.

### `provides.storage`

Rulesets must declare a storage model.

```json
"provides": {
  "storage": {
    "model": "scoped-json-v1"
  }
}
```

### `provides.actorTypes`

Rulesets must declare at least one actor type.

```json
"actorTypes": [
  {
    "id": "character",
    "label": "Character",
    "labelKey": "my-rpg.actor.character",
    "schema": "schemas/character.schema.json",
    "sheet": "layouts/character.sheet.gw.json"
  }
]
```

| Field | Purpose |
|---|---|
| `id` | Stable type id. |
| `label` | Inline display label. |
| `labelKey` | Locale key. Preferred for translated packages. |
| `schema` | Package-relative JSON schema path. |
| `sheet` | Package-relative declarative sheet layout path. |

### `provides.itemTypes`

```json
"itemTypes": [
  {
    "id": "weapon",
    "labelKey": "my-rpg.item.weapon",
    "schema": "schemas/item.schema.json",
    "sheet": "layouts/items/weapon.sheet.gw.json"
  }
]
```

### `provides.rules`

Rulesets can provide rules documents by named purpose.

```json
"rules": {
  "formulas": "rules/formulas.gw.json",
  "derived": "rules/derived.gw.json",
  "actions": "rules/actions.gw.json",
  "validation": "rules/validation.gw.json",
  "conditions": "rules/conditions.gw.json",
  "combat": "rules/combat.gw.json"
}
```

### `provides.mappings`

Mappings connect declarative ruleset data to Gravewright runtime surfaces.

```json
"mappings": {
  "tokens": "mappings/token.gw.json",
  "chatCards": "mappings/chat-cards.gw.json",
  "rollToast": "mappings/roll-toast.gw.json"
}
```

### `provides.contentPacks`

```json
"contentPacks": [
  {
    "id": "my-rpg-weapons",
    "type": "item_pack",
    "label": "Weapons",
    "labelKey": "my-rpg.content.weapons",
    "path": "content/items.weapons.gwpack.json"
  }
]
```

Allowed content pack types:

- `actor_pack`
- `item_pack`
- `spell_pack`
- `journal_pack`
- `table_pack`
- `condition_pack`

### `provides.locales`

```json
"locales": {
  "en": "locales/en.json",
  "pt-BR": "locales/pt-BR.json"
}
```

Locale files are JSON dictionaries. Runtime translation is available through `sdk.i18n.t(key, fallback)` when the package declares `locales` capability.

### `provides.assets`

```json
"assets": {
  "images": [
    { "id": "logo", "label": "Logo", "path": "assets/logo.webp" }
  ],
  "maps": [
    { "id": "dungeon-map", "label": "Dungeon Map", "path": "maps/dungeon.webp" }
  ],
  "audio": [
    { "id": "theme", "label": "Theme", "path": "audio/theme.ogg" }
  ],
  "icons": [
    { "id": "sword", "label": "Sword", "path": "icons/sword.svg" }
  ]
}
```

Asset entries require:

- `id`
- `label`
- safe package-relative `path`

The validator warns when common asset categories use unexpected extensions.

## Settings

```json
"settings": [
  {
    "key": "enabled",
    "scope": "user",
    "type": "boolean",
    "default": true,
    "label": "Enable"
  },
  {
    "key": "theme",
    "scope": "campaign",
    "type": "enum",
    "default": "dark",
    "label": "Theme",
    "options": ["dark", "light"]
  }
]
```

Allowed setting scopes:

- `global`
- `campaign`
- `user`

Allowed setting types:

- `boolean`
- `string`
- `number`
- `integer`
- `enum`

`enum` settings must declare `options`.

## Distribution

```json
"distribution": {
  "type": "zip",
  "url": "https://example.com/my-package.zip",
  "sha256": "..."
}
```

Allowed `distribution.type` values:

- `zip`
- `git`
- `directory`

## Dependencies

```json
"dependencies": [
  {
    "id": "shared-library",
    "kind": "library",
    "minimum": "0.1.0",
    "verified": "0.1.0",
    "maximum": "0.x"
  }
]
```

Use dependencies only when absence is an error. If a package merely enhances behavior when another package is present, prefer optional event listening through `sdk.bus.subscribe(...)` and degrade gracefully.

## Conflicts

```json
"conflicts": [
  {
    "id": "other-theme",
    "reason": "Overrides the same UI surfaces."
  }
]
```

Conflicts communicate packages that should not be installed or activated together.

## Complete ruleset skeleton

```json
{
  "$schema": "https://raw.githubusercontent.com/Gravewright/gravewright/main/schemas/gravewright-package-v1.schema.json",
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "ruleset",
  "id": "my-rpg",
  "name": "My RPG",
  "version": "0.1.0",
  "authors": ["Example Author"],
  "license": "MIT",
  "compatibility": {
    "minimum": "1.0.0-rc.1",
    "verified": "1.0.0-rc.1",
    "maximum": "1.x"
  },
  "capabilities": [
    "actors.register",
    "items.register",
    "sheets.declarative",
    "sheets.runtime",
    "rules.declarative",
    "combat.config",
    "combat.runtime",
    "tokens.mappings",
    "content.packs",
    "locales",
    "assets.styles",
    "assets.scripts"
  ],
  "activation": {
    "scope": "campaign",
    "mode": "exclusive"
  },
  "entrypoints": {
    "game": {
      "styles": ["assets/my-rpg.css"],
      "scripts": ["assets/my-rpg.js"]
    }
  },
  "provides": {
    "storage": {
      "model": "scoped-json-v1"
    },
    "actorTypes": [
      {
        "id": "character",
        "labelKey": "my-rpg.actor.character",
        "schema": "schemas/character.schema.json",
        "sheet": "layouts/character.sheet.gw.json"
      }
    ],
    "itemTypes": [
      {
        "id": "item",
        "labelKey": "my-rpg.item.item",
        "schema": "schemas/item.schema.json",
        "sheet": "layouts/item.sheet.gw.json"
      }
    ],
    "rules": {
      "formulas": "rules/formulas.gw.json"
    },
    "contentPacks": [],
    "locales": {
      "en": "locales/en.json"
    }
  }
}
```
