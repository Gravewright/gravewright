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
| `actors.items.read` | Discover ruleset-declared actor-local item-copy slots and snapshots. |
| `actors.items.write` | Insert and remove validated actor-local item snapshots through declared slots. |
| `actors.read` | Read visible actor snapshots. |
| `actors.register` | Register actor type behavior/data through package metadata. |
| `actors.write` | Create, update, and delete actors through semantic commands. |
| `assets.audio` | Provide audio assets. |
| `assets.icons` | Provide icon assets. |
| `assets.images` | Provide image assets. |
| `assets.import` | Ingest a user-selected file into a validated, campaign-owned asset without filesystem access. |
| `assets.library` | Read the campaign asset library: list uploaded files (images and PDFs) the member is allowed to see. |
| `assets.maps` | Provide map assets. |
| `assets.pack` | Provide asset packs. |
| `assets.scripts` | Load trusted package JavaScript. |
| `assets.styles` | Load package CSS. |
| `assets.ui` | Use UI methods such as toasts and modals. |
| `assets.video` | Provide video assets. |
| `audio.playback` | Control first-class core-owned semantic audio playbacks. |
| `automation.schedule` | Schedule exact durable-safe registered actions under execution-time authority. |
| `bus.provide` | Provide an SDK interop bus method other packages can request. |
| `bus.publish` | Publish SDK interop bus events. |
| `bus.request` | Request a value from an SDK interop bus provider. |
| `bus.subscribe` | Subscribe to SDK interop bus events. |
| `campaign.members.read` | Read the campaign member roster (user id, role, display name) for orchestration and participant selection. |
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
| `gameplay.flows.manage` | Register, start, and advance bounded gameplay flows. |
| `gameplay.flows.participate` | Submit typed choices as an authorized flow participant. |
| `gameplay.flows.read` | Read audience-filtered authoritative gameplay flow state. |
| `handouts.present` | Present authorized content without granting persistent access. |
| `input.commands` | Register semantic commands and gestures with conflict-safe user bindings. |
| `interactions.request` | Request and cancel bounded server-owned decisions from explicit campaign recipients. |
| `interactions.respond` | Discover and answer directed interactions as the authenticated recipient. |
| `items.data.write` | Patch validated item-sheet data editable by the current user. |
| `items.read` | Read visible item snapshots. |
| `items.register` | Register item type behavior/data through package metadata. |
| `items.write` | Create, update, and delete items through semantic commands. |
| `journals.read` | Read journals and handouts visible to the current user. |
| `journals.write` | Create, update, and delete validated journals. |
| `locales` | Provide locales and use `sdk.i18n.t`. |
| `navigation.scene` | Change authorized users' persisted viewed-scene context without moving tokens. |
| `packages.inspect` | Discover public metadata and interop declarations for packages active in the current campaign. |
| `pdf.annotations.read` | Read annotations for visible PDF documents. |
| `pdf.annotations.write` | Create, update, and delete validated annotations for visible PDF documents. |
| `pdf.presentation` | Coordinate versioned PDF presentation without granting document access. |
| `pdf.read` | Read PDF documents and metadata visible to the current user. |
| `pdf.viewer` | Open and navigate PDF documents in the host viewer. |
| `permissions.inspect` | Inspect the current user's effective permission decisions. |
| `rolls.intent` | Request server-authoritative declarative roll/action intents. |
| `rules.actions` | Discover and execute versioned package-declared semantic actions authoritatively. |
| `rules.declarative` | Provide declarative rules documents. |
| `rules.extends` | Extend rule behavior. |
| `scene.effects.read` | Read semantic scene effects. |
| `scene.effects.write` | Manage semantic scene effects. |
| `scene.fog.read` | Read logical fog state without renderer internals. |
| `scene.fog.write` | Manage fog through bounded authoritative operations. |
| `scene.geometry.read` | Read audience-filtered walls, doors, semantic channels, and lights without renderer internals. |
| `scene.geometry.write` | Manage logical walls, doors, closed semantic channels, discovery presentation, and lights. |
| `scene.images.read` | Read permission-filtered scene-image placements. |
| `scene.images.write` | Place, update, and remove authorized scene images. |
| `scene.measurements.shared` | Share bounded expiring measurements with an explicit audience. |
| `scene.objectTypes.register` | Register bounded declarative world-object types for the active package. |
| `scene.objects.interact` | Submit authorized semantic interaction intents for visible world objects. |
| `scene.objects.read` | Read and hit-test audience-filtered scene world objects. |
| `scene.objects.write` | Create, update, move, and delete authoritative scene world objects. |
| `scene.overlays` | Provide scene overlays. |
| `scene.read` | Read visible scene snapshots. |
| `scene.shaders.customLibrary` | Integrate a package-owned custom shader library with the trusted core editor and placement flow. |
| `scene.shaders.read` | Discover semantic shader presets and read applied instances without renderer internals. |
| `scene.shaders.write` | Apply and manage validated semantic shader presets without raw GLSL authority. |
| `scene.spatialSounds.read` | Read authorized persistent native Spatial Sound configuration for a Scene. |
| `scene.spatialSounds.write` | Create, update and delete persistent native Spatial Sounds with Scene authority and CAS. |
| `scene.templates.read` | Read permission-filtered persistent gameplay templates in world space. |
| `scene.templates.write` | Create, update, and delete bounded persistent gameplay templates. |
| `scene.tools` | Use scene/tool methods such as `sdk.scene.*` and `sdk.tools.*`. |
| `scene.zones.read` | Read visible semantic scene zones and observable token membership. |
| `scene.zones.write` | Create, update, and delete versioned campaign-owned semantic scene zones. |
| `settings` | Define and use package settings. |
| `sheets.components` | Provide sheet components. |
| `sheets.controller` | Attach a controller script to an HTML sheet. |
| `sheets.declarative` | Provide declarative sheet layouts. |
| `sheets.html` | Provide HTML-mode actor/item sheets. |
| `sheets.richText` | Render sanitized rich text in an HTML sheet. |
| `sheets.runtime` | Use `sdk.sheets.*` runtime methods. |
| `sounds.read` | Read reusable native Sound resources in the active campaign. |
| `sounds.write` | Create, update and safely delete reusable native Sound resources from authorized audio Assets. |
| `storage.sqlite` | Use Gravewright-managed SQLite storage scoped to a package. |
| `timelines.control` | Cancel future cues of an authorized semantic timeline. |
| `timelines.read` | Read authorized core-timed semantic timelines. |
| `timelines.start` | Register and start bounded semantic timelines. |
| `tokens.extends` | Use token extension methods such as `sdk.tokens.centerOn`. |
| `tokens.manage` | Create, update, and delete tokens authoritatively. |
| `tokens.mappings` | Provide token mappings. |
| `tokens.move` | Move controlled tokens authoritatively. |
| `tokens.read` | Read visible token snapshots. |
| `tokens.targets` | Manage the current user's private, scene-scoped target set. |
| `tokens.transfer` | Atomically transfer stable token identities between authorized scenes. |
| `ui.applications` | Render package applications incrementally through named UI parts. |
| `ui.dragDrop` | Register typed semantic drag sources and concrete authority-revalidated destinations. |
| `ui.presentations` | Show bounded core-rendered ephemeral presentations to authorized audiences. |
| `ui.slots` | Mount package-owned UI in documented host slots. |
| `users.presentation.read` | Read the bounded public presentation color of participants visible in the active campaign. |
| `workflows.control` | Cancel authorized workflows without implicit rollback. |
| `workflows.read` | Read authorized durable workflow instances. |
| `workflows.start` | Register bounded definitions and start core-owned durable workflows. |
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
| `sdk.actors.data` | `actors.read` |
| `sdk.actors.delete` | `actors.write` |
| `sdk.actors.get` | `actors.read` |
| `sdk.actors.items.insertCopy` | `actors.items.write` |
| `sdk.actors.items.listCopies` | `actors.items.read` |
| `sdk.actors.items.removeCopy` | `actors.items.write` |
| `sdk.actors.items.slots` | `actors.items.read` |
| `sdk.actors.list` | `actors.read` |
| `sdk.actors.patchData` | `actors.data.write` |
| `sdk.actors.update` | `actors.write` |
| `sdk.assets.cancelImport` | `assets.import` |
| `sdk.assets.ingest` | `assets.import` |
| `sdk.assets.list` | `assets.library` |
| `sdk.audio.get` | `audio.playback` |
| `sdk.audio.list` | `audio.playback` |
| `sdk.audio.play` | `audio.playback` |
| `sdk.audio.stop` | `audio.playback` |
| `sdk.audio.update` | `audio.playback` |
| `sdk.automation.audit` | `automation.schedule` |
| `sdk.automation.cancel` | `automation.schedule` |
| `sdk.automation.get` | `automation.schedule` |
| `sdk.automation.list` | `automation.schedule` |
| `sdk.automation.schedule` | `automation.schedule` |
| `sdk.bus.provide` | `bus.provide` |
| `sdk.bus.publish` | `bus.publish` |
| `sdk.bus.request` | `bus.request` |
| `sdk.bus.subscribe` | `bus.subscribe` |
| `sdk.campaign.members` | `campaign.members.read` |
| `sdk.cards.definitions.get` | `cards.read` |
| `sdk.cards.definitions.instantiate` | `cards.manage` |
| `sdk.cards.definitions.list` | `cards.read` |
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
| `sdk.gameplay.flows.advance` | `gameplay.flows.manage` |
| `sdk.gameplay.flows.get` | `gameplay.flows.read` |
| `sdk.gameplay.flows.list` | `gameplay.flows.read` |
| `sdk.gameplay.flows.register` | `gameplay.flows.manage` |
| `sdk.gameplay.flows.start` | `gameplay.flows.manage` |
| `sdk.gameplay.flows.submit` | `gameplay.flows.participate` |
| `sdk.handouts.present` | `handouts.present` |
| `sdk.i18n.t` | `locales` |
| `sdk.input.bindings.get` | `input.commands` |
| `sdk.input.bindings.set` | `input.commands` |
| `sdk.input.commands.execute` | `input.commands` |
| `sdk.input.commands.list` | `input.commands` |
| `sdk.input.commands.register` | `input.commands` |
| `sdk.input.gestures.register` | `input.commands` |
| `sdk.interactions.cancel` | `interactions.request` |
| `sdk.interactions.get` | `interactions.respond` |
| `sdk.interactions.list` | `interactions.respond` |
| `sdk.interactions.request` | `interactions.request` |
| `sdk.interactions.respond` | `interactions.respond` |
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
| `sdk.navigation.scene.getState` | `navigation.scene` |
| `sdk.navigation.scene.go` | `navigation.scene` |
| `sdk.packages.get` | `packages.inspect` |
| `sdk.packages.has` | `packages.inspect` |
| `sdk.pdf.annotations.create` | `pdf.annotations.write` |
| `sdk.pdf.annotations.delete` | `pdf.annotations.write` |
| `sdk.pdf.annotations.list` | `pdf.annotations.read` |
| `sdk.pdf.annotations.update` | `pdf.annotations.write` |
| `sdk.pdf.get` | `pdf.read` |
| `sdk.pdf.metadata` | `pdf.read` |
| `sdk.pdf.presentation.current` | `pdf.presentation` |
| `sdk.pdf.presentation.end` | `pdf.presentation` |
| `sdk.pdf.presentation.start` | `pdf.presentation` |
| `sdk.pdf.presentation.update` | `pdf.presentation` |
| `sdk.pdf.viewer.currentPage` | `pdf.viewer` |
| `sdk.pdf.viewer.goToPage` | `pdf.viewer` |
| `sdk.pdf.viewer.open` | `pdf.viewer` |
| `sdk.pdf.viewer.search` | `pdf.viewer` |
| `sdk.permissions.can` | `permissions.inspect` |
| `sdk.permissions.check` | `permissions.inspect` |
| `sdk.rolls.intent` | `rolls.intent` |
| `sdk.rules.actions.execute` | `rules.actions` |
| `sdk.rules.actions.executeReference` | `rules.actions` |
| `sdk.rules.actions.get` | `rules.actions` |
| `sdk.rules.actions.list` | `rules.actions` |
| `sdk.rules.actions.resolve` | `rules.actions` |
| `sdk.scene.active` | `scene.read` |
| `sdk.scene.activeCameraForScene` | `scene.tools` |
| `sdk.scene.activeCanvas` | `scene.tools` |
| `sdk.scene.effects.create` | `scene.effects.write` |
| `sdk.scene.effects.delete` | `scene.effects.write` |
| `sdk.scene.effects.list` | `scene.effects.read` |
| `sdk.scene.effects.presets` | `scene.effects.read` |
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
| `sdk.scene.measurements.cancel` | `scene.measurements.shared` |
| `sdk.scene.measurements.listShared` | `scene.measurements.shared` |
| `sdk.scene.measurements.measure` | `scene.tools` |
| `sdk.scene.measurements.share` | `scene.measurements.shared` |
| `sdk.scene.objectTypes.register` | `scene.objectTypes.register` |
| `sdk.scene.objects.create` | `scene.objects.write` |
| `sdk.scene.objects.delete` | `scene.objects.write` |
| `sdk.scene.objects.get` | `scene.objects.read` |
| `sdk.scene.objects.hitTest` | `scene.objects.read` |
| `sdk.scene.objects.interact` | `scene.objects.interact` |
| `sdk.scene.objects.list` | `scene.objects.read` |
| `sdk.scene.objects.update` | `scene.objects.write` |
| `sdk.scene.shaders.apply` | `scene.shaders.write` |
| `sdk.scene.shaders.customLibrary.clearPreview` | `scene.shaders.customLibrary` |
| `sdk.scene.shaders.customLibrary.openEditor` | `scene.shaders.customLibrary` |
| `sdk.scene.shaders.customLibrary.preview` | `scene.shaders.customLibrary` |
| `sdk.scene.shaders.customLibrary.registerProvider` | `scene.shaders.customLibrary` |
| `sdk.scene.shaders.customLibrary.use` | `scene.shaders.customLibrary` |
| `sdk.scene.shaders.enable` | `scene.shaders.write` |
| `sdk.scene.shaders.getPreset` | `scene.shaders.read` |
| `sdk.scene.shaders.list` | `scene.shaders.read` |
| `sdk.scene.shaders.presets` | `scene.shaders.read` |
| `sdk.scene.shaders.remove` | `scene.shaders.write` |
| `sdk.scene.shaders.update` | `scene.shaders.write` |
| `sdk.scene.spatialSounds.create` | `scene.spatialSounds.write` |
| `sdk.scene.spatialSounds.delete` | `scene.spatialSounds.write` |
| `sdk.scene.spatialSounds.get` | `scene.spatialSounds.read` |
| `sdk.scene.spatialSounds.list` | `scene.spatialSounds.read` |
| `sdk.scene.spatialSounds.update` | `scene.spatialSounds.write` |
| `sdk.scene.templates.create` | `scene.templates.write` |
| `sdk.scene.templates.delete` | `scene.templates.write` |
| `sdk.scene.templates.get` | `scene.templates.read` |
| `sdk.scene.templates.list` | `scene.templates.read` |
| `sdk.scene.templates.update` | `scene.templates.write` |
| `sdk.scene.zones.create` | `scene.zones.write` |
| `sdk.scene.zones.delete` | `scene.zones.write` |
| `sdk.scene.zones.get` | `scene.zones.read` |
| `sdk.scene.zones.list` | `scene.zones.read` |
| `sdk.scene.zones.members` | `scene.zones.read` |
| `sdk.scene.zones.update` | `scene.zones.write` |
| `sdk.settings.all` | `settings` |
| `sdk.settings.definitions` | `settings` |
| `sdk.settings.get` | `settings` |
| `sdk.settings.onChange` | `settings` |
| `sdk.settings.scope` | `settings` |
| `sdk.settings.set` | `settings` |
| `sdk.sheets.helpers` | `sheets.runtime` |
| `sdk.sheets.register` | `sheets.runtime` |
| `sdk.sheets.registerController` | `sheets.controller` |
| `sdk.sounds.create` | `sounds.write` |
| `sdk.sounds.delete` | `sounds.write` |
| `sdk.sounds.get` | `sounds.read` |
| `sdk.sounds.list` | `sounds.read` |
| `sdk.sounds.update` | `sounds.write` |
| `sdk.storage.sqlite.execute` | `storage.sqlite` |
| `sdk.storage.sqlite.query` | `storage.sqlite` |
| `sdk.storage.sqlite.status` | `storage.sqlite` |
| `sdk.timelines.cancel` | `timelines.control` |
| `sdk.timelines.get` | `timelines.read` |
| `sdk.timelines.list` | `timelines.read` |
| `sdk.timelines.register` | `timelines.start` |
| `sdk.timelines.start` | `timelines.start` |
| `sdk.tokens.centerOn` | `tokens.extends` |
| `sdk.tokens.create` | `tokens.manage` |
| `sdk.tokens.delete` | `tokens.manage` |
| `sdk.tokens.get` | `tokens.read` |
| `sdk.tokens.list` | `tokens.read` |
| `sdk.tokens.move` | `tokens.move` |
| `sdk.tokens.targets.clear` | `tokens.targets` |
| `sdk.tokens.targets.list` | `tokens.targets` |
| `sdk.tokens.targets.set` | `tokens.targets` |
| `sdk.tokens.transfer` | `tokens.transfer` |
| `sdk.tokens.transferMany` | `tokens.transfer` |
| `sdk.tokens.update` | `tokens.manage` |
| `sdk.tools.activeTool` | `scene.tools` |
| `sdk.tools.register` | `scene.tools` |
| `sdk.ui.applications.close` | `ui.applications` |
| `sdk.ui.applications.register` | `ui.applications` |
| `sdk.ui.applications.render` | `ui.applications` |
| `sdk.ui.closeModal` | `assets.ui` |
| `sdk.ui.dragDrop.drop` | `ui.dragDrop` |
| `sdk.ui.dragDrop.registerSource` | `ui.dragDrop` |
| `sdk.ui.dragDrop.registerTarget` | `ui.dragDrop` |
| `sdk.ui.dragDrop.sources` | `ui.dragDrop` |
| `sdk.ui.dragDrop.targets` | `ui.dragDrop` |
| `sdk.ui.openModal` | `assets.ui` |
| `sdk.ui.presentations.close` | `ui.presentations` |
| `sdk.ui.presentations.get` | `ui.presentations` |
| `sdk.ui.presentations.list` | `ui.presentations` |
| `sdk.ui.presentations.show` | `ui.presentations` |
| `sdk.ui.presentations.update` | `ui.presentations` |
| `sdk.ui.presentations.wait` | `ui.presentations` |
| `sdk.ui.slots.available` | `ui.slots` |
| `sdk.ui.slots.register` | `ui.slots` |
| `sdk.ui.toast` | `assets.ui` |
| `sdk.users.presentation.get` | `users.presentation.read` |
| `sdk.users.presentation.list` | `users.presentation.read` |
| `sdk.workflows.cancel` | `workflows.control` |
| `sdk.workflows.get` | `workflows.read` |
| `sdk.workflows.list` | `workflows.read` |
| `sdk.workflows.register` | `workflows.start` |
| `sdk.workflows.start` | `workflows.start` |
<!-- END GENERATED -->

> Generated from `CAPABILITY_REQUIREMENTS` in `static/js/sdk/sdk-capabilities.js`. Do not edit by hand: run `uv run python scripts/generate_sdk_reference.py`.

## Review guidance

Request the smallest capability set possible.

- Do not declare `assets.scripts` unless the package truly needs trusted browser code.
- Do not declare `assets.ui` for CSS-only themes.
- Do not declare `settings` unless the package defines or reads settings.
- Prefer declarative package data over runtime scripting when possible.
