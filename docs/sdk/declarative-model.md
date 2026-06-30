# Declarative package model

Gravewright packages are **declarative first**.

That means the package manifest and the files it points to are the primary API surface. Runtime JavaScript is optional and should be added only when the package needs behavior that cannot be represented as package data.

The authoring rule is:

```text
Declare everything the engine can load, validate, index, activate, localize, and secure.
Script only the behavior that genuinely needs client-side runtime code.
```

This page is the starting point for package authors. It explains the model before the individual manifest fields and SDK methods.

## Mental model

A package is not a loose plugin. It is a contract:

```text
data/packages/{kind_plural}/{id}/
├─ manifest.json          # package contract
├─ assets/                # scripts, styles, images, audio, maps, icons
├─ schemas/               # actor/item schemas or other package schemas
├─ sheets/                # declarative sheet layouts/templates
├─ rules/                 # declarative rules documents
├─ mappings/              # token, sheet, roll, or content mappings
├─ content/               # importable packs
├─ locales/               # translation files
└─ README.md              # package author/user notes
```

The engine reads `manifest.json`, validates it, resolves dependencies and conflicts, checks capabilities, loads declared assets, indexes declared content, exposes declared settings, and then gives any package script a scoped browser SDK.

```text
manifest.json
  -> validates against SDK v1 schema
  -> declares package kind and activation mode
  -> declares capabilities
  -> declares provided game data
  -> declares entrypoint scripts/styles
  -> declares settings, dependencies, conflicts, distribution
  -> loads into the server-side package registry
  -> exposes a package-scoped client manifest
  -> optional browser runtime receives a gated sdk object
```

## What "declarative" means

Declarative package data is data the engine can understand without executing package code.

Use declarative data for:

| Author need | Prefer declaring in | Typical capability |
|---|---|---|
| Package identity and compatibility | top-level manifest fields | none |
| Package kind and activation behavior | `kind`, `activation` | none |
| Package permissions | `capabilities` | capability-specific |
| CSS and JS files | `entrypoints.game.styles`, `entrypoints.game.scripts` | `assets.styles`, `assets.scripts` |
| User/campaign settings | `settings` | `settings` |
| Actor types | `provides.actorTypes` or package-specific type definitions | `actors.register` |
| Item types | `provides.itemTypes` or package-specific type definitions | `items.register` |
| Sheet layouts | `provides.actorTypes[].sheet`, `provides.itemTypes[].sheet`, `sheets/` | `sheets.declarative` |
| Sheet components | `sheets/components/` used by declarative layouts | `sheets.components` |
| Rules documents | `provides.rules`, `rules/` | `rules.declarative` |
| Combat configuration | documents in `provides.rules` | `combat.config` |
| Token mappings | `provides.mappings`, `mappings/` | `tokens.mappings` |
| Roll mappings/intents | actions/formulas in `provides.rules`, mappings when needed | `rolls.intent`, `dice.roll` |
| Importable content packs | `provides.contentPacks`, `content/` | `content.packs` |
| Locales | `provides.locales`, `locales/` | `locales` |
| Asset libraries | `provides.assets`, `assets/` | `assets.pack`, `assets.images`, `assets.audio`, `assets.maps`, `assets.icons` |
| Package-to-package requirements | `dependencies`, `conflicts` | none |
| Distribution metadata | `distribution` | none |

The exact shape of each object is documented in [`manifest.md`](manifest.md), [`content-and-assets.md`](content-and-assets.md), and the SDK v1 JSON Schema.

## Runtime JavaScript is an extension layer, not the foundation

A scripted package can declare a browser script:

```json
{
  "capabilities": ["assets.scripts", "assets.ui"],
  "entrypoints": {
    "game": {
      "scripts": ["assets/main.js"]
    }
  }
}
```

Then register a runtime:

```js
window.GravewrightSDK.register({
  id: "my-package",
  setup(sdk) {
    // Wire up state before the game runtime is ready.
  },
  ready(sdk) {
    // DOM and game runtime are ready here.
    sdk.ui.toast("My package is ready");
  }
});
```

Use runtime JavaScript for:

- responding to client-side events;
- registering commands;
- sending chat cards or chat intents;
- adding UI behavior through documented SDK methods;
- reading/writing package settings;
- registering sheet/combat runtime plugins when declarative data is not enough;
- centering on tokens or reading current scene/tool state;
- composing package-to-package integrations through versioned events.

Do not use runtime JavaScript for:

- backend execution;
- raw database writes;
- raw filesystem access;
- raw network calls;
- permission override;
- depending on private globals or undocumented DOM structure;
- replacing declarative data that the engine already supports.

## Declarative vs runtime decision table

| Question | Use declarative data | Use runtime SDK |
|---|---:|---:|
| Can the engine load and validate it before the table opens? | yes | no |
| Does it define durable package content? | yes | no |
| Does it need a capability but no client interaction? | yes | no |
| Does it need browser events, UI, or commands? | no | yes |
| Does it depend on current scene/user/table state? | maybe | yes |
| Does it need to persist user/campaign preferences? | declare setting | call `sdk.settings.*` |
| Does it need to send a chat intent/card from a click handler? | declare capability | call `sdk.chat.send` |
| Does it need a custom sheet layout? | declare sheet | only add script for dynamic behavior |
| Does it need combat configuration? | declare config | add script for runtime/panel behavior |
| Does it need reusable art/maps/icons/audio? | declare asset pack | no, unless UI behavior is needed |

## Minimal declarative addon

This addon contributes CSS and settings. It does not run JavaScript.

```json
{
  "$schema": "https://raw.githubusercontent.com/Gravewright/gravewright/main/schemas/gravewright-package-v1.schema.json",
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "addon",
  "id": "clean-ui",
  "name": "Clean UI",
  "version": "0.1.0",
  "description": "Small visual improvements for the table UI.",
  "authors": ["Example Author"],
  "license": "MIT",
  "compatibility": {
    "minimum": "1",
    "verified": "1",
    "maximum": "1.x"
  },
  "capabilities": ["assets.styles", "settings"],
  "activation": {
    "scope": "campaign",
    "mode": "multiple"
  },
  "entrypoints": {
    "game": {
      "styles": ["assets/clean-ui.css"]
    }
  },
  "settings": [
    {
      "key": "compactMode",
      "type": "boolean",
      "scope": "campaign",
      "default": true,
      "label": "Compact mode"
    }
  ],
  "provides": {}
}
```

## Minimal declarative content package

A content package should be importable without script execution.

```json
{
  "$schema": "https://raw.githubusercontent.com/Gravewright/gravewright/main/schemas/gravewright-package-v1.schema.json",
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "content",
  "id": "starter-encounters",
  "name": "Starter Encounters",
  "version": "0.1.0",
  "compatibility": { "minimum": "1", "verified": "1" },
  "capabilities": ["content.packs"],
  "activation": { "scope": "campaign", "mode": "multiple" },
  "entrypoints": { "game": {} },
  "provides": {
    "contentPacks": [
      {
        "id": "encounters",
        "label": "Starter Encounters",
        "path": "content/encounters.json",
        "type": "encounter"
      }
    ]
  }
}
```

## Minimal declarative asset package

An asset package contributes media for other packages or campaigns.

```json
{
  "$schema": "https://raw.githubusercontent.com/Gravewright/gravewright/main/schemas/gravewright-package-v1.schema.json",
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "assets",
  "id": "dark-forest-assets",
  "name": "Dark Forest Assets",
  "version": "0.1.0",
  "compatibility": { "minimum": "1", "verified": "1" },
  "capabilities": ["assets.pack", "assets.images", "assets.maps", "assets.icons"],
  "activation": { "scope": "campaign", "mode": "multiple" },
  "entrypoints": { "game": {} },
  "provides": {
    "assets": [
      { "id": "forest-map", "type": "map", "path": "assets/maps/forest.webp", "label": "Dark Forest Map" },
      { "id": "wolf-icon", "type": "icon", "path": "assets/icons/wolf.svg", "label": "Wolf Icon" }
    ]
  }
}
```

## Minimal declarative ruleset

A ruleset is the campaign's base game system. It should declare the game structure first, then add runtime plugins only when necessary.

```json
{
  "$schema": "https://raw.githubusercontent.com/Gravewright/gravewright/main/schemas/gravewright-package-v1.schema.json",
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "ruleset",
  "id": "my-rpg",
  "name": "My RPG",
  "version": "0.1.0",
  "compatibility": { "minimum": "1", "verified": "1", "maximum": "1.x" },
  "capabilities": [
    "actors.register",
    "items.register",
    "sheets.declarative",
    "rules.declarative",
    "tokens.mappings",
    "content.packs",
    "settings",
    "locales"
  ],
  "activation": { "scope": "campaign", "mode": "exclusive" },
  "entrypoints": {
    "game": {
      "styles": ["assets/my-rpg.css"]
    }
  },
  "settings": [
    {
      "key": "useOptionalFatigue",
      "type": "boolean",
      "scope": "campaign",
      "default": false,
      "label": "Use optional fatigue rules"
    }
  ],
  "provides": {
    "actorTypes": [
      {
        "id": "character",
        "label": "Character",
        "schema": "schemas/character.schema.json",
        "sheet": "sheets/character.sheet.json"
      }
    ],
    "itemTypes": [
      {
        "id": "weapon",
        "label": "Weapon",
        "schema": "schemas/weapon.schema.json",
        "sheet": "sheets/weapon.sheet.json"
      }
    ],
    "rules": [
      { "id": "core", "path": "rules/core.json", "label": "Core Rules" }
    ],
    "mappings": [
      { "id": "default-token", "path": "mappings/token-defaults.json", "type": "token" }
    ],
    "contentPacks": [
      { "id": "starter", "label": "Starter Content", "path": "content/starter.json", "type": "mixed" }
    ],
    "locales": [
      { "locale": "en", "path": "locales/en.json" },
      { "locale": "pt-BR", "path": "locales/pt-BR.json" }
    ]
  }
}
```

## Full ruleset authoring flow

```text
1. Choose `kind: "ruleset"` and `activation.mode: "exclusive"`.
2. Define actor and item types.
3. Create JSON schemas for each durable data shape.
4. Create declarative sheet layouts for actors/items.
5. Declare rules documents and mappings.
6. Add starter content packs.
7. Add locales for every user-facing label.
8. Add settings for optional rules.
9. Request only the capabilities required by the manifest and runtime.
10. Validate with `grave package validate`.
11. Install and activate with `grave package install --enable`.
12. Inspect with `grave package doctor`.
13. Add runtime JavaScript only for behavior not representable declaratively.
14. Re-validate after every manifest, path, or capability change.
```

## Full addon authoring flow

```text
1. Choose `kind: "addon"` and `activation.mode: "multiple"`.
2. Decide whether the addon is content-only, style-only, settings-only, scripted, or mixed.
3. Declare assets, styles, settings, content packs, locales, dependencies, and conflicts.
4. Add `assets.scripts` only if the addon has browser behavior.
5. Add the exact runtime capability for each SDK method used.
6. Use package-namespaced events and commands.
7. Keep all emitted payloads versioned.
8. Validate, install, activate, test, and run doctor.
```

## Package directory conventions

These conventions make packages easier to inspect and safer to validate:

```text
data/packages/<id>/
├─ manifest.json
├─ README.md
├─ CHANGELOG.md
├─ LICENSE
├─ assets/
│  ├─ main.js
│  ├─ styles.css
│  ├─ icons/
│  ├─ images/
│  ├─ maps/
│  └─ audio/
├─ content/
├─ locales/
├─ mappings/
├─ rules/
├─ schemas/
└─ sheets/
```

Rules:

- Keep package ids lowercase kebab-case.
- Keep manifest paths relative to the package root.
- Do not use `..`, absolute paths, or paths outside the package.
- Prefer JSON for durable package data.
- Keep runtime scripts in `assets/` and declare them explicitly.
- Keep styles in `assets/` and declare them explicitly.
- Keep package README examples aligned with the manifest.

## Author checklist

A package is not author-complete until all of these are true:

- The package has a valid `manifest.json`.
- The package kind matches the intended activation mode.
- All provided files are declared and exist.
- Every declared capability is used by manifest data, runtime code, or both.
- No undeclared capability is needed by runtime code.
- No forbidden capability is requested.
- All public labels are localized or intentionally fixed.
- Settings have defaults, scopes, labels, and descriptions where useful.
- Dependencies and conflicts are explicit.
- Scripted packages register exactly once with the same id as the manifest.
- Runtime code uses only the scoped `sdk`, not private globals.
- Events and commands are package-namespaced.
- Cross-package payloads include a `version` field.
- The package passes validation and doctor checks.
- The package works after reinstalling from a clean copy.

## Design principle

Declarative first is what lets Gravewright make packages installable, inspectable, secure, dependency-aware, and portable. Runtime code should enhance the package, not hide its contract.
