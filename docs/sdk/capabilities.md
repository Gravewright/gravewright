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
| `actors.data.write` | Patch validated actor sheet data the current user may edit. |
| `actors.read` | Read visible actor snapshots. |
| `actors.register` | Register actor type behavior/data through package metadata. |
| `actors.write` | Create, update, and delete actors through semantic commands. |
| `assets.audio` | Provide audio assets. |
| `assets.icons` | Provide icon assets. |
| `assets.images` | Provide image assets. |
| `assets.library` | Read the campaign asset library: list uploaded files (images and PDFs) the member is allowed to see. |
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
| `cards.manage` | Shuffle, reset, draw, reveal, discard, and play cards through authoritative services. |
| `cards.read` | Read permission-filtered decks, piles, cards, and placements. |
| `chat.cards` | Send chat cards/messages through `sdk.chat`. |
| `chat.read` | Read chat messages visible to the current user. |
| `combat.config` | Declare how initiative is rolled and which resources combat reads. |
| `combat.manage` | Manage authoritative combat state. |
| `combat.read` | Read the authoritative combat snapshot. |
| `combat.runtime` | Use `sdk.combat.*` runtime methods and panel registration. |
| `commands.register` | Register client commands. |
| `content.index` | Search a permission-filtered index of campaign content. |
| `content.packs` | Provide and read content packs. |
| `content.references` | Resolve and open permission-filtered universal content references. |
| `dice.roll` | Request server-authoritative dice rolls through `sdk.dice`. |
| `events.subscribe` | Subscribe to permission-filtered semantic game events. |
| `handouts.present` | Present authorized content without granting persistent access. |
| `items.data.write` | Patch validated item-sheet data editable by the current user. |
| `items.read` | Read visible item snapshots. |
| `items.register` | Register item type behavior/data through package metadata. |
| `items.write` | Create, update, and delete items through semantic commands. |
| `journals.read` | Read journals and handouts visible to the current user. |
| `journals.write` | Create, update, and delete validated journals. |
| `locales` | Provide locales and use `sdk.i18n.t`. |
| `pdf.annotations.read` | Read annotations for visible PDF documents. |
| `pdf.annotations.write` | Create, update, and delete validated annotations for visible PDF documents. |
| `pdf.read` | Read PDF documents and metadata visible to the current user. |
| `pdf.viewer` | Open and navigate PDF documents in the host viewer. |
| `permissions.inspect` | Inspect the current user's effective permission decisions. |
| `rolls.intent` | Request server-authoritative declarative roll/action intents. |
| `rules.actions` | Execute bounded declarative action graphs authoritatively. |
| `rules.declarative` | Provide declarative rules documents. |
| `rules.extends` | Extend rule behavior. |
| `scene.effects.read` | Read semantic scene effects. |
| `scene.effects.write` | Manage semantic scene effects. |
| `scene.fog.read` | Read logical fog state without renderer internals. |
| `scene.fog.write` | Manage fog through bounded authoritative operations. |
| `scene.geometry.read` | Read logical walls, doors, and lights. |
| `scene.geometry.write` | Manage logical walls, doors, and lights. |
| `scene.images.read` | Read permission-filtered scene-image placements. |
| `scene.images.write` | Place, update, and remove authorized scene images. |
| `scene.overlays` | Provide scene overlays. |
| `scene.read` | Read visible scene snapshots. |
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
| `tokens.manage` | Create, update, and delete tokens authoritatively. |
| `tokens.mappings` | Provide token mappings. |
| `tokens.move` | Move controlled tokens authoritatively. |
| `tokens.read` | Read visible token snapshots. |
| `ui.applications` | Render package applications incrementally through named UI parts. |
| `ui.slots` | Mount package-owned UI in documented host slots. |
<!-- END GENERATED -->

> Generated from `KNOWN_CAPABILITIES` in `app/engine/sdk/package_manifest_validator.py` and `docs/sdk/_data/capability-descriptions.json`. Do not edit by hand: run `uv run python scripts/generate_sdk_reference.py`.

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
| `sdk.actors.create` | `actors.write` |
| `sdk.actors.delete` | `actors.write` |
| `sdk.actors.get` | `actors.read` |
| `sdk.actors.list` | `actors.read` |
| `sdk.actors.patchData` | `actors.data.write` |
| `sdk.actors.update` | `actors.write` |
| `sdk.assets.list` | `assets.library` |
| `sdk.bus.provide` | `bus.provide` |
| `sdk.bus.publish` | `bus.publish` |
| `sdk.bus.request` | `bus.request` |
| `sdk.bus.subscribe` | `bus.subscribe` |
| `sdk.cards.discard` | `cards.manage` |
| `sdk.cards.discardPlacement` | `cards.manage` |
| `sdk.cards.draw` | `cards.manage` |
| `sdk.cards.play` | `cards.manage` |
| `sdk.cards.reset` | `cards.manage` |
| `sdk.cards.reveal` | `cards.manage` |
| `sdk.cards.shuffle` | `cards.manage` |
| `sdk.cards.state` | `cards.read` |
| `sdk.cards.updatePlacement` | `cards.manage` |
| `sdk.chat.get` | `chat.read` |
| `sdk.chat.list` | `chat.read` |
| `sdk.chat.send` | `chat.cards` |
| `sdk.combat.add` | `combat.manage` |
| `sdk.combat.advance` | `combat.manage` |
| `sdk.combat.advanceRound` | `combat.manage` |
| `sdk.combat.combatants` | `combat.read` |
| `sdk.combat.current` | `combat.read` |
| `sdk.combat.dispatch` | `combat.runtime` |
| `sdk.combat.end` | `combat.manage` |
| `sdk.combat.moveCombatant` | `combat.manage` |
| `sdk.combat.register` | `combat.runtime` |
| `sdk.combat.registerPanel` | `combat.runtime` |
| `sdk.combat.remove` | `combat.manage` |
| `sdk.combat.renderSlot` | `combat.runtime` |
| `sdk.combat.rollInitiative` | `combat.manage` |
| `sdk.combat.setFlags` | `combat.manage` |
| `sdk.combat.setInitiative` | `combat.manage` |
| `sdk.combat.setInitiativeOrder` | `combat.manage` |
| `sdk.combat.setTurn` | `combat.manage` |
| `sdk.combat.start` | `combat.manage` |
| `sdk.commands.register` | `commands.register` |
| `sdk.content.can` | `content.references` |
| `sdk.content.get` | `content.references` |
| `sdk.content.link` | `content.references` |
| `sdk.content.open` | `content.references` |
| `sdk.content.pack` | `content.packs` |
| `sdk.content.packs` | `content.packs` |
| `sdk.content.ref` | `content.references` |
| `sdk.content.resolve` | `content.references` |
| `sdk.content.search` | `content.index` |
| `sdk.dice.roll` | `dice.roll` |
| `sdk.events.available` | `events.subscribe` |
| `sdk.events.on` | `events.subscribe` |
| `sdk.events.once` | `events.subscribe` |
| `sdk.handouts.present` | `handouts.present` |
| `sdk.i18n.t` | `locales` |
| `sdk.items.create` | `items.write` |
| `sdk.items.delete` | `items.write` |
| `sdk.items.get` | `items.read` |
| `sdk.items.list` | `items.read` |
| `sdk.items.patchData` | `items.data.write` |
| `sdk.items.update` | `items.write` |
| `sdk.journals.create` | `journals.write` |
| `sdk.journals.delete` | `journals.write` |
| `sdk.journals.get` | `journals.read` |
| `sdk.journals.list` | `journals.read` |
| `sdk.journals.update` | `journals.write` |
| `sdk.pdf.annotations.create` | `pdf.annotations.write` |
| `sdk.pdf.annotations.delete` | `pdf.annotations.write` |
| `sdk.pdf.annotations.list` | `pdf.annotations.read` |
| `sdk.pdf.annotations.update` | `pdf.annotations.write` |
| `sdk.pdf.get` | `pdf.read` |
| `sdk.pdf.metadata` | `pdf.read` |
| `sdk.pdf.viewer.currentPage` | `pdf.viewer` |
| `sdk.pdf.viewer.goToPage` | `pdf.viewer` |
| `sdk.pdf.viewer.open` | `pdf.viewer` |
| `sdk.pdf.viewer.search` | `pdf.viewer` |
| `sdk.permissions.can` | `permissions.inspect` |
| `sdk.rolls.intent` | `rolls.intent` |
| `sdk.rules.actions.execute` | `rules.actions` |
| `sdk.rules.actions.validate` | `rules.actions` |
| `sdk.scene.active` | `scene.read` |
| `sdk.scene.activeCameraForScene` | `scene.tools` |
| `sdk.scene.activeCanvas` | `scene.tools` |
| `sdk.scene.effects.create` | `scene.effects.write` |
| `sdk.scene.effects.delete` | `scene.effects.write` |
| `sdk.scene.effects.list` | `scene.effects.read` |
| `sdk.scene.effects.update` | `scene.effects.write` |
| `sdk.scene.fog.disable` | `scene.fog.write` |
| `sdk.scene.fog.enable` | `scene.fog.write` |
| `sdk.scene.fog.paint` | `scene.fog.write` |
| `sdk.scene.fog.reset` | `scene.fog.write` |
| `sdk.scene.fog.state` | `scene.fog.read` |
| `sdk.scene.geometry.createLight` | `scene.geometry.write` |
| `sdk.scene.geometry.createWall` | `scene.geometry.write` |
| `sdk.scene.geometry.deleteLight` | `scene.geometry.write` |
| `sdk.scene.geometry.deleteWall` | `scene.geometry.write` |
| `sdk.scene.geometry.deleteWalls` | `scene.geometry.write` |
| `sdk.scene.geometry.lights` | `scene.geometry.read` |
| `sdk.scene.geometry.moveWallNode` | `scene.geometry.write` |
| `sdk.scene.geometry.moveWalls` | `scene.geometry.write` |
| `sdk.scene.geometry.setDoorState` | `scene.geometry.write` |
| `sdk.scene.geometry.splitWall` | `scene.geometry.write` |
| `sdk.scene.geometry.updateLight` | `scene.geometry.write` |
| `sdk.scene.geometry.updateWall` | `scene.geometry.write` |
| `sdk.scene.geometry.walls` | `scene.geometry.read` |
| `sdk.scene.get` | `scene.read` |
| `sdk.scene.images.delete` | `scene.images.write` |
| `sdk.scene.images.list` | `scene.images.read` |
| `sdk.scene.images.place` | `scene.images.write` |
| `sdk.scene.images.update` | `scene.images.write` |
| `sdk.scene.list` | `scene.read` |
| `sdk.settings.all` | `settings` |
| `sdk.settings.definitions` | `settings` |
| `sdk.settings.get` | `settings` |
| `sdk.settings.onChange` | `settings` |
| `sdk.settings.scope` | `settings` |
| `sdk.settings.set` | `settings` |
| `sdk.sheets.helpers` | `sheets.runtime` |
| `sdk.sheets.register` | `sheets.runtime` |
| `sdk.sheets.registerController` | `sheets.controller` |
| `sdk.storage.sqlite.execute` | `storage.sqlite` |
| `sdk.storage.sqlite.query` | `storage.sqlite` |
| `sdk.storage.sqlite.status` | `storage.sqlite` |
| `sdk.tokens.centerOn` | `tokens.extends` |
| `sdk.tokens.create` | `tokens.manage` |
| `sdk.tokens.delete` | `tokens.manage` |
| `sdk.tokens.get` | `tokens.read` |
| `sdk.tokens.list` | `tokens.read` |
| `sdk.tokens.move` | `tokens.move` |
| `sdk.tokens.update` | `tokens.manage` |
| `sdk.tools.activeTool` | `scene.tools` |
| `sdk.ui.applications.close` | `ui.applications` |
| `sdk.ui.applications.register` | `ui.applications` |
| `sdk.ui.applications.render` | `ui.applications` |
| `sdk.ui.closeModal` | `assets.ui` |
| `sdk.ui.openModal` | `assets.ui` |
| `sdk.ui.slots.available` | `ui.slots` |
| `sdk.ui.slots.register` | `ui.slots` |
| `sdk.ui.toast` | `assets.ui` |
<!-- END GENERATED -->

> Generated from `CAPABILITY_REQUIREMENTS` in `static/js/sdk/sdk-capabilities.js`. Do not edit by hand: run `uv run python scripts/generate_sdk_reference.py`.

## Review guidance

Request the smallest capability set possible.

- Do not declare `assets.scripts` unless the package truly needs trusted browser code.
- Do not declare `assets.ui` for CSS-only themes.
- Do not declare `settings` unless the package defines or reads settings.
- Prefer declarative package data over runtime scripting when possible.
