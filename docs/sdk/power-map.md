# SDK power map

This page maps author goals to the package manifest, capabilities, runtime SDK methods, and detailed docs.

Use it when you know what you want to build but do not yet know which SDK surface to use.

## Core map

| Author goal | Manifest surface | Capability | Runtime SDK | Detailed docs |
|---|---|---|---|---|
| Create a game ruleset | `kind: "ruleset"`, `activation.mode: "exclusive"`, `provides` | varies | optional | [`declarative-model.md`](declarative-model.md), [`kinds.md`](kinds.md) |
| Create an addon | `kind: "addon"`, `activation.mode: "multiple"` | varies | optional | [`kinds.md`](kinds.md), [`author-complete-checklist.md`](author-complete-checklist.md) |
| Create a library dependency | `kind: "library"`, `activation.mode: "passive"` | varies | usually none | [`kinds.md`](kinds.md) |
| Create a theme | `kind: "theme"`, styles entrypoint | `assets.styles`, maybe `assets.ui`, `settings` | optional | [`content-and-assets.md`](content-and-assets.md), [`settings.md`](settings.md) |
| Create importable content | `kind: "content"`, `provides.contentPacks` | `content.packs` | `sdk.content.*` optional | [`content-and-assets.md`](content-and-assets.md) |
| Create media/asset library | `kind: "assets"`, `provides.assets` | `assets.pack`, media-specific `assets.*` | usually none | [`content-and-assets.md`](content-and-assets.md) |

## Manifest/data power map

| Feature | Declare here | Typical files | Capability |
|---|---|---|---|
| Actor types | `provides.actorTypes` | `schemas/*.schema.json`, `sheets/*.sheet.json` | `actors.register` |
| Item types | `provides.itemTypes` | `schemas/*.schema.json`, `sheets/*.sheet.json` | `items.register` |
| Declarative sheets | `provides.actorTypes[].sheet`, `provides.itemTypes[].sheet` | `sheets/*.json` | `sheets.declarative` |
| Sheet components | declarative layouts using `sheets/components/` | `sheets/components/*.json` | `sheets.components` |
| Rules documents | `provides.rules` | `rules/*.json` | `rules.declarative` |
| Rule extensions | `provides.rules`, runtime behavior | `rules/*.json`, `assets/*.js` | `rules.extends`, `assets.scripts` |
| Dice/roll metadata | actions/formulas in `provides.rules`, `provides.mappings` | `rules/*.json`, `mappings/*.json` | `dice.roll`, `rolls.intent` |
| Combat defaults | documents in `provides.rules` | `rules/combat.json` | `combat.config` |
| Token mappings | `provides.mappings` | `mappings/token-*.json` | `tokens.mappings` |
| Scene overlays | runtime and declared entrypoints | `assets/*.js`, `assets/*.css` | `scene.overlays`, `assets.scripts` |
| Content packs | `provides.contentPacks` | `content/*.json` | `content.packs` |
| Locales | `provides.locales` | `locales/en.json`, `locales/pt-BR.json` | `locales` |
| Settings | `settings` | manifest only | `settings` |
| Styles | `entrypoints.game.styles` | `assets/*.css` | `assets.styles` |
| Scripts | `entrypoints.game.scripts` | `assets/*.js` | `assets.scripts` |
| UI assets | `provides.assets` or package paths | `assets/icons`, `assets/images` | `assets.ui`, media-specific capabilities |
| Dependencies | `dependencies` | manifest only | none |
| Conflicts | `conflicts` | manifest only | none |
| Distribution | `distribution` | manifest only | none |

## Runtime SDK power map

| Runtime goal | SDK method(s) | Required capability | Notes |
|---|---|---|---|
| Check package identity | `sdk.package`, `sdk.kind`, `sdk.version` | none | Always available in scoped SDK. |
| Check capabilities | `sdk.capabilities.has`, `sdk.capabilities.require`, `sdk.capabilities.list` | none | Use for optional behavior. |
| Read context | `sdk.context()`, `sdk.game.context()` | none | Returns frozen snapshots. |
| Read campaign | `sdk.game.campaign()` | none | Snapshot, not a raw mutable model. |
| Read scene | `sdk.game.scene()` | none | Snapshot of active scene context. |
| Read user | `sdk.game.user()` | none | Snapshot of active user context. |
| Check readiness | `sdk.game.ready()` | none | True after game runtime is ready. |
| Subscribe to events | `sdk.bus.subscribe` | `bus.subscribe` | Declare in `interop.listens`; names should be package-scoped. |
| Publish event | `sdk.bus.publish` | `bus.publish` | Declare in `interop.emits`; payloads should include `version`. |
| Register command | `sdk.commands.register` | `commands.register` | Command names should be package-scoped. |
| Show toast | `sdk.ui.toast`, `sdk.toast` | `assets.ui` | UI helper. |
| Open/close modal | `sdk.ui.openModal`, `sdk.ui.closeModal` | `assets.ui` | Only documented/core modal ids. |
| Send chat card/intent | `sdk.chat.send` | `chat.cards` | Treat as an intent; core remains authoritative. |
| Roll a formula | `sdk.dice.roll` | `dice.roll` | Server-authoritative formula roll and chat card. |
| Execute roll/action intent | `sdk.rolls.intent` | `rolls.intent` | Server-authoritative Sheet IR action, targets, damage, and initiative. |
| List settings | `sdk.settings.definitions`, `sdk.settings.all` | `settings` | Values visible to current package. |
| Read setting | `sdk.settings.get`, `sdk.setting(key)` | `settings` | Use fallback values. |
| Write setting | `sdk.settings.set`, `sdk.setting(key, value)` | `settings` | Persists through SDK settings endpoint. |
| Use sheet helpers | `sdk.sheets.helpers` | `sheets.runtime` | Runtime helper access. |
| Register sheet behavior | `sdk.sheets.register` | `sheets.runtime` | Use after declaring sheet capability. |
| Register combat behavior | `sdk.combat.register` | `combat.runtime` | Runtime combat integration. |
| Register combat panel | `sdk.combat.registerPanel` | `combat.runtime` | Panel object should be stable and documented by package. |
| Dispatch combat event | `sdk.combat.dispatch` | `combat.runtime` | Package-owned combat runtime bridge. |
| Render combat slot | `sdk.combat.renderSlot` | `combat.runtime` | Returns rendered slot results or empty array. |
| Center on token | `sdk.tokens.centerOn` | `tokens.extends` | Client helper only. |
| Read active canvas | `sdk.scene.activeCanvas` | `scene.tools` | Client helper only. |
| Read camera for scene | `sdk.scene.activeCameraForScene` | `scene.tools` | Client helper only. |
| Read active tool | `sdk.tools.activeTool` | `scene.tools` | Client helper only. |
| List content packs | `sdk.content.packs` | `content.packs` | Async. |
| Read a content pack | `sdk.content.pack` | `content.packs` | Async. |
| Translate text | `sdk.i18n.t` | `locales` | Falls back when missing. |

## Build recipes

### I want to build a full ruleset

Use:

- `kind: "ruleset"`
- `activation.mode: "exclusive"`
- `provides.actorTypes`
- `provides.itemTypes`
- `provides.actorTypes[].sheet` / `provides.itemTypes[].sheet`
- `provides.rules`
- `provides.mappings`
- `provides.contentPacks`
- `provides.locales`
- `settings`
- optional `entrypoints.game.styles`
- optional `entrypoints.game.scripts`

Capabilities usually include:

```json
[
  "actors.register",
  "items.register",
  "sheets.declarative",
  "rules.declarative",
  "combat.config",
  "tokens.mappings",
  "content.packs",
  "settings",
  "locales",
  "assets.styles"
]
```

Add runtime capabilities only if using runtime methods:

```json
[
  "assets.scripts",
  "sheets.runtime",
  "combat.runtime",
  "dice.roll",
  "rolls.intent",
  "chat.cards",
  "assets.ui"
]
```

### I want to build a scripted addon

Use:

- `kind: "addon"`
- `activation.mode: "multiple"`
- `entrypoints.game.scripts`
- `assets.scripts`
- exact method capabilities from [`capabilities.md`](capabilities.md)

Example capability set:

```json
[
  "assets.scripts",
  "assets.ui",
  "settings",
  "chat.cards",
  "commands.register"
]
```

### I want to build a pure CSS theme

Use:

- `kind: "theme"`
- `entrypoints.game.styles`
- `assets.styles`
- optional `settings`

Do not use `assets.scripts` unless the theme has browser behavior.

### I want to build importable content

Use:

- `kind: "content"`
- `provides.contentPacks`
- `content.packs`
- optional dependency on the ruleset expected by the pack

Do not use runtime JavaScript for importable content unless the content package also adds UI behavior.

### I want to build a media library

Use:

- `kind: "assets"`
- `provides.assets`
- `assets.pack`
- media-specific capabilities such as `assets.images`, `assets.audio`, `assets.maps`, `assets.icons`

## What to read next

1. [`declarative-model.md`](declarative-model.md) — understand the package model.
2. [`author-complete-checklist.md`](author-complete-checklist.md) — make sure authors can use the full SDK.
3. [`manifest.md`](manifest.md) — write the contract.
4. [`capabilities.md`](capabilities.md) — request the right permissions.
5. [`runtime.md`](runtime.md) and [`reference.md`](reference.md) — add browser behavior.
6. [`validation.md`](validation.md) — validate and debug.
