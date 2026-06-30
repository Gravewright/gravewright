# Capabilities

A package declares the capabilities it needs in `manifest.json`. Gravewright validates declared capabilities against an allow-list and rejects forbidden capabilities. The browser SDK gates methods at runtime.

If a package calls a gated SDK method without declaring the required capability, the method throws an actionable error:

```text
Package "x" attempted to use sdk.chat.send but does not declare capability "chat.cards".
```

## Allowed capabilities

<!-- BEGIN GENERATED: allowed-capabilities -->
| Capability | Purpose |
|---|---|
| `actors.register` | Register actor type behavior/data through package metadata. |
| `assets.audio` | Provide audio assets. |
| `assets.icons` | Provide icon assets. |
| `assets.images` | Provide image assets. |
| `assets.maps` | Provide map assets. |
| `assets.pack` | Provide asset packs. |
| `assets.scripts` | Load trusted package JavaScript. |
| `assets.styles` | Load package CSS. |
| `assets.ui` | Use UI methods such as toasts and modals. |
| `assets.video` | Provide video assets. |
| `bus.provide` | Provide an SDK interop bus method other packages can request. |
| `bus.publish` | Publish SDK interop bus events. |
| `bus.request` | Request a value from an SDK interop bus provider. |
| `bus.subscribe` | Subscribe to SDK interop bus events. |
| `chat.cards` | Send chat cards/messages through `sdk.chat`. |
| `combat.config` | Provide combat configuration. |
| `combat.runtime` | Use `sdk.combat.*` runtime methods and panel registration. |
| `commands.register` | Register client commands. |
| `content.packs` | Provide and read content packs. |
| `dice.roll` | Request server-authoritative dice rolls through `sdk.dice`. |
| `items.register` | Register item type behavior/data through package metadata. |
| `locales` | Provide locales and use `sdk.i18n.t`. |
| `rolls.intent` | Request server-authoritative declarative roll/action intents. |
| `rules.declarative` | Provide declarative rules documents. |
| `rules.extends` | Extend rule behavior. |
| `scene.overlays` | Provide scene overlays. |
| `scene.tools` | Use scene/tool methods such as `sdk.scene.*` and `sdk.tools.*`. |
| `settings` | Define and use package settings. |
| `sheets.components` | Provide sheet components. |
| `sheets.controller` | Attach a controller script to an HTML sheet. |
| `sheets.declarative` | Provide declarative sheet layouts. |
| `sheets.html` | Provide HTML-mode actor/item sheets. |
| `sheets.richText` | Render sanitized rich text in an HTML sheet. |
| `sheets.runtime` | Use `sdk.sheets.*` runtime methods. |
| `storage.sqlite` | Use Gravewright-managed SQLite storage scoped to a package. |
| `tokens.extends` | Use token extension methods such as `sdk.tokens.centerOn`. |
| `tokens.mappings` | Provide token mappings. |
<!-- END GENERATED -->

> Generated from `KNOWN_CAPABILITIES` in `app/engine/sdk/package_manifest_validator.py` and `docs/sdk/_data/capability-descriptions.json`. Do not edit by hand — run `uv run python scripts/generate_sdk_reference.py`.

## Forbidden capabilities

These are always rejected:

<!-- BEGIN GENERATED: forbidden-capabilities -->
```text
backend.execute
database.raw
filesystem.raw
network.raw
permissions.override
```
<!-- END GENERATED -->

There is no backend plugin execution in SDK v1. Packages are declarative plus browser-runtime code. The server remains authoritative for game state, permissions, persistence, and validation.

## Runtime method gates

<!-- BEGIN GENERATED: method-gates -->
| SDK method | Required capability |
|---|---|
| `sdk.bus.provide` | `bus.provide` |
| `sdk.bus.publish` | `bus.publish` |
| `sdk.bus.request` | `bus.request` |
| `sdk.bus.subscribe` | `bus.subscribe` |
| `sdk.chat.send` | `chat.cards` |
| `sdk.combat.dispatch` | `combat.runtime` |
| `sdk.combat.register` | `combat.runtime` |
| `sdk.combat.registerPanel` | `combat.runtime` |
| `sdk.combat.renderSlot` | `combat.runtime` |
| `sdk.commands.register` | `commands.register` |
| `sdk.content.pack` | `content.packs` |
| `sdk.content.packs` | `content.packs` |
| `sdk.dice.roll` | `dice.roll` |
| `sdk.i18n.t` | `locales` |
| `sdk.rolls.intent` | `rolls.intent` |
| `sdk.scene.activeCameraForScene` | `scene.tools` |
| `sdk.scene.activeCanvas` | `scene.tools` |
| `sdk.settings.all` | `settings` |
| `sdk.settings.definitions` | `settings` |
| `sdk.settings.get` | `settings` |
| `sdk.settings.set` | `settings` |
| `sdk.sheets.helpers` | `sheets.runtime` |
| `sdk.sheets.register` | `sheets.runtime` |
| `sdk.sheets.registerController` | `sheets.controller` |
| `sdk.storage.sqlite.execute` | `storage.sqlite` |
| `sdk.storage.sqlite.query` | `storage.sqlite` |
| `sdk.storage.sqlite.status` | `storage.sqlite` |
| `sdk.tokens.centerOn` | `tokens.extends` |
| `sdk.tools.activeTool` | `scene.tools` |
| `sdk.ui.closeModal` | `assets.ui` |
| `sdk.ui.openModal` | `assets.ui` |
| `sdk.ui.toast` | `assets.ui` |
<!-- END GENERATED -->

> Generated from `CAPABILITY_REQUIREMENTS` in `static/js/sdk/sdk-capabilities.js`. Do not edit by hand — run `uv run python scripts/generate_sdk_reference.py`.

## Review guidance

Request the smallest capability set possible.

- Do not declare `assets.scripts` unless the package truly needs trusted browser code.
- Do not declare `assets.ui` for CSS-only themes.
- Do not declare `settings` unless the package defines or reads settings.
- Prefer declarative package data over runtime scripting when possible.
