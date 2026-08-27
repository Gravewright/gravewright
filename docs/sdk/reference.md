# Browser SDK reference

This page documents the scoped `sdk` object passed to package runtimes by `window.GravewrightSDK.register(...)`.

```js
window.GravewrightSDK.register({
  id: "my-package",
  setup(sdk, payload) {},
  ready(sdk, payload) {},
});
```

## `sdk.version`

```js
sdk.version // "1"
```

The SDK runtime version string.

## `sdk.package`

```js
sdk.package.id
sdk.package.kind
sdk.package.version
```

Frozen package identity for the current scoped runtime.

## `sdk.kind`

```js
sdk.kind // "ruleset", "addon", "library", "theme", "content", or "assets"
```

Shortcut for the package kind.

## `sdk.capabilities`

### `sdk.capabilities.has(capability)`

Returns `true` when the current package declared `capability`.

```js
if (sdk.capabilities.has("settings")) {
  const enabled = sdk.settings.get("enabled", true);
}
```

### `sdk.capabilities.require(capability, apiName = "sdk")`

Throws if the package did not declare `capability`.

```js
sdk.capabilities.require("storage.sqlite", "my-feature");
```

### `sdk.capabilities.list()`

Returns the package's declared capability list.

```js
console.log(sdk.capabilities.list());
```

## `sdk.context()`

Returns a frozen snapshot of the current game context.

```js
const context = sdk.context();
```

Prefer namespace-specific helpers under `sdk.game` when possible.

## `sdk.game`

### `sdk.game.context()`

Returns a frozen snapshot of the game context.

### `sdk.game.campaign()`

Returns the current campaign snapshot or `null`.

### `sdk.game.scene()`

Returns the current scene snapshot or `null`.

### `sdk.game.user()`

Returns the current user snapshot or `null`.

### `sdk.game.ready()`

Returns `true` after the game runtime is ready.

## `sdk.commands`

Requires `commands.register`.

### `sdk.commands.register(name, handler)`

Registers a browser command by dispatching a `vtt:command-register` event.

```js
sdk.commands.register("my-package.open-panel", async () => {
  sdk.ui.openModal("my-panel");
});
```

Command names should be package-namespaced.

## `sdk.assets`

Requires `assets.library`.

### `sdk.assets.list(options)`

Lists the campaign's asset library. The server filters by member role, so a package
never sees more than the current user is allowed to.

Each entry carries `kind`: `"image"` or `"pdf"`: so packages do not have to
reinterpret `content_type`. Filter with `options.kind`; `options.campaignId`
defaults to the active campaign.

```js
const sheets = await sdk.assets.list({ kind: "pdf" });
// [{ id, filename, src, kind: "pdf", byte_size, ... }]
```

`src` is the URL to fetch the bytes. Images are served inline; everything else is
served as an attachment, so render a PDF through a canvas renderer rather than
embedding the URL directly.

### `sdk.assets.ingest(file)` / `sdk.assets.cancelImport(assetId)`

Requires `assets.import`. `ingest` accepts an actual user-selected browser
`File`; the core validates and creates a campaign-owned asset. It accepts no
server path and returns no storage path or digest. The bounded synchronous SDK 1
pipeline returns `ready`; cancelling a completed import is non-destructive.

## `sdk.ui`

Requires `assets.ui`.

### `sdk.ui.toast(message, options)`

Shows a UI toast through the core toast surface.

```js
sdk.ui.toast("Saved", { duration: 3000 });
```

### `sdk.ui.openModal(modalId)`

Opens a core modal by id.

### `sdk.ui.closeModal(modalOrId)`

Closes a core modal by id or modal reference.

## `sdk.chat`

Requires `chat.cards`.

### `sdk.chat.send(message)`

Submits a package-owned chat message/card request through the browser event bridge.

```js
sdk.chat.send({
  type: "package-card",
  title: "Roll Result",
  total: 17,
});
```

The server and core runtime remain authoritative. Treat this as an intent, not a direct persistence write.

## `sdk.dice`

Requires `dice.roll`.

### `sdk.dice.roll({ formula, label = "", actorId = "" })`

Requests a server-authoritative actor roll through `POST /game/actor/roll`.
The response includes total, dice groups, rendered chat metadata, and any
presentation fields returned by the engine.

```js
await sdk.dice.roll({
  actorId: ctx.actor.id,
  label: "Attack",
  formula: "2d20kh1 + @sheet.attackBonus",
});
```

## `sdk.rolls`

Requires `rolls.intent`.

### `sdk.rolls.intent({ actorId, actionId, inputs = {}, rollOptions = {}, target = {} })`

Requests a server-authoritative declarative action through
`POST /game/actor/action`. Use this for Sheet IR actions, targets, damage
application, initiative, and other effects declared in `rules/actions.gw.json`.

```js
await sdk.rolls.intent({
  actorId: ctx.actor.id,
  actionId: "attack.primary",
  inputs: {},
  rollOptions: { visibility: "public" },
  target: { actorId: targetActorId, tokenId: targetTokenId },
});
```

See [`rolls.md`](rolls.md) for formula syntax and system patterns.

## `sdk.settings`

Requires `settings`.

### `sdk.settings.definitions()`

Returns declared setting definitions from the client manifest.

### `sdk.settings.all()`

Returns current setting values visible to the package.

### `sdk.settings.get(key, fallback = undefined)`

Reads a setting value.

```js
const enabled = sdk.settings.get("enabled", true);
```

### `sdk.settings.set(key, value, options = {})`

Persists a setting value through the SDK settings endpoint.

```js
await sdk.settings.set("enabled", false);
await sdk.settings.set("enabled", true, { campaignId: "campaign-id" });
```

When `options.campaignId` is omitted, the active campaign id is used when available.

## `sdk.sheets`

Requires `sheets.runtime`.

### `sdk.sheets.helpers()`

Returns public sheet helper functions exposed by the core sheet runtime.

### `sdk.sheets.register(plugin)`

Registers sheet behavior for the package.

```js
sdk.sheets.register({
  labels: {
    actorName: "Name",
    roll: "Roll",
  },
  renderSection(node, variant, renderContext, helpers) {
    if (variant !== "special") return null;
    const section = helpers.el("section", "my-special-section");
    section.appendChild(helpers.el("h3", null, node.label || "Special"));
    return section;
  },
  renderHeaderIdentity(main, bundle, helpers) {
    main.appendChild(helpers.el("div", "my-subtitle", bundle.actor?.type || ""));
  },
  autoFitWidth(actorType) {
    return actorType === "character" ? 820 : null;
  },
});
```

### `sdk.sheets.registerController(sheetType, controller)`

Registers an HTML sheet controller for a declared `sheet.mode = "html"` sheet.

```js
sdk.sheets.registerController("character", {
  setup(ctx) {},
  mount(ctx) {},
  update(ctx) {},
  unmount(ctx) {},
  async onAction(action, ctx) {},
});
```

Controllers handle `data-action` events and should clean up external listeners
from `unmount`.

## `sdk.combat`

Requires `combat.runtime`.

### `sdk.combat.register(plugin)`

Registers lightweight combat runtime handlers and slots.

Handlers are called during a render: `beforeRender`, `afterRender` and
`combatantMeta` (whose return value is appended to the combatant's meta line).
The `combatantActions` slot returns nodes placed next to a combatant's menu.

```js
sdk.combat.register({
  handlers: {
    combatantMeta({ combatant }) {
      return combatant.defeated ? "down" : "";
    },
  },
  slots: {
    combatantActions({ combatant, isGm }) {
      if (!isGm) return [];
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Concentration";
      button.dataset.combatantId = combatant.id;
      return button;
    },
  },
});
```

Each payload carries the combatant as the panel sees it: `id`, `actor_id`,
`token_id`, `name`, `initiative` (`null` until rolled), `hidden`, `defeated`,
`position`, `is_current`, `is_next`, `has_acted`, `can_move_up`, `can_move_down`
and `bar` (the combatant's primary token bar, or `null`). `initiative` is text,
not a number: read `state.config.input` to know
what shape the active system puts in it.

### `sdk.combat.registerPanel(panel)`

Replaces the default combat panel. The object must expose `renderPanel(panel,
state)`, which owns everything inside the panel body.

```js
sdk.combat.registerPanel({
  renderPanel(panel, state) {
    const target = panel.querySelector("[data-combat-state]");
    target.textContent = `Round ${state.round}: ${state.current_name}`;
  },
});
```

Replacing the panel means reimplementing initiative editing and the turn
controls, so prefer handlers and slots when they are enough.

### `sdk.combat.dispatch(name, payload)`

Dispatches a combat runtime event to the current package's registered handler.

### `sdk.combat.renderSlot(name, payload)`

Renders a combat slot and returns an array of rendered nodes or values.

## `sdk.tokens`

Requires `tokens.extends`.

### `sdk.tokens.centerOn(tokenId)`

Centers the active map on a token.

```js
sdk.tokens.centerOn(tokenId);
```

## `sdk.scene`

Requires `scene.tools`.

### `sdk.scene.activeCanvas()`

Returns the active canvas object when available, otherwise `null`.

### `sdk.scene.activeCameraForScene(sceneId)`

Returns camera data for a scene when available, otherwise `null`.

## `sdk.tools`

Requires `scene.tools`.

### `sdk.tools.activeTool()`

Returns the active map/tool id, defaulting to `"select"` when unavailable.

## `sdk.content`

Requires `content.packs`.

### `sdk.content.packs()`

Loads content pack summaries for the current package.

```js
const packs = await sdk.content.packs();
```

### `sdk.content.pack(packId)`

Loads a specific content pack.

```js
const spells = await sdk.content.pack("my-rpg-spells");
```

## `sdk.storage.sqlite`

Requires `storage.sqlite`.

### `sdk.storage.sqlite.query(scope, name, params = {})`

Runs a declared read query through the managed storage endpoint.

```js
const rows = await sdk.storage.sqlite.query("campaign", "getState", {
  key: "panel-state",
});
```

### `sdk.storage.sqlite.execute(scope, name, params = {})`

Runs a declared write query through the managed storage endpoint.

```js
await sdk.storage.sqlite.execute("campaign", "saveState", {
  key: "panel-state",
  value_json: JSON.stringify(state),
});
```

### `sdk.storage.sqlite.status(scope)`

Returns managed storage status for the package and scope.

```js
const status = await sdk.storage.sqlite.status("campaign");
```

The package never receives a path or submits SQL; the backend resolves package,
campaign, capability, scope, query name, and declared parameters.

## `sdk.bus`

Requires the matching `bus.*` capability per method.

### `sdk.bus.publish(eventName, payload)`

Publishes a package-owned event. Event names must be in the package namespace.

```js
await sdk.bus.publish("my-package.panel.opened", { panelId: "main" });
```

### `sdk.bus.subscribe(eventName, handler)`

Subscribes to bus events and returns an unsubscribe function.

```js
const off = sdk.bus.subscribe("other-ruleset.actor.rested", (payload) => {
  console.log(payload);
});
```

### `sdk.bus.provide(methodName, handler)`

Registers one package-owned RPC provider for `methodName`.

```js
const off = sdk.bus.provide("my-package.state.get", async (payload) => {
  return { key: payload.key, value: "open" };
});
```

### `sdk.bus.request(methodName, payload, options)`

Calls a bus provider and resolves to `{ ok: true, value }` or
`{ ok: false, error }`.

```js
const result = await sdk.bus.request("my-package.state.get", {
  key: "panel-state",
});
```

## `sdk.i18n`

Requires `locales`.

### `sdk.i18n.t(key, fallback)`

Looks up a locale key from the package locale catalog. Returns `fallback` when provided, otherwise returns `key`.

```js
const label = sdk.i18n.t("my-rpg.action.attack", "Attack");
```

## SDK 1 semantic runtime

These SDK 1 methods apply package-capability and current-user permission gates and return frozen public snapshots. Reads are bounded to 100 entries; writes remain server-authoritative.

- `sdk.events.on`, `sdk.events.once`, `sdk.events.available`; `sdk.permissions.can`.
  PDF annotation mutations emit the visibility-filtered aggregate event
  `pdf.annotations.changed` for authorized re-read.
- `sdk.actors.get`, `sdk.actors.list`, `sdk.actors.data`, `sdk.actors.create`, `sdk.actors.update`, `sdk.actors.delete`.
- `sdk.items.get`, `sdk.items.list`, `sdk.items.create`, `sdk.items.update`, `sdk.items.delete`.
- `sdk.tokens.get`, `sdk.tokens.list`, `sdk.tokens.move`, `sdk.tokens.create`, `sdk.tokens.update`, `sdk.tokens.delete`; private targeting uses `sdk.tokens.targets.list`, `sdk.tokens.targets.set`, and `sdk.tokens.targets.clear`.
- `sdk.scene.get`, `sdk.scene.list`, `sdk.scene.active`.
- `sdk.scene.geometry.walls`, `sdk.scene.geometry.lights`, `sdk.scene.geometry.createWall`, `sdk.scene.geometry.updateWall`, `sdk.scene.geometry.deleteWall`, `sdk.scene.geometry.createLight`, `sdk.scene.geometry.updateLight`, `sdk.scene.geometry.deleteLight`, `sdk.scene.geometry.setDoorState`.
- `sdk.scene.effects.list`, `sdk.scene.effects.create`, `sdk.scene.effects.update`, `sdk.scene.effects.delete`.
- `sdk.ui.slots.available`, `sdk.ui.slots.register`; `sdk.chat.list`, `sdk.chat.get`.
- `sdk.combat.current`, `sdk.combat.combatants`, `sdk.combat.start`, `sdk.combat.end`, `sdk.combat.advance`, `sdk.combat.setTurn`, `sdk.combat.add`, `sdk.combat.remove`.
- `sdk.rules.actions.list`, `sdk.rules.actions.get`, `sdk.rules.actions.resolve`, `sdk.rules.actions.execute`, `sdk.rules.actions.executeReference`.
- `sdk.automation.schedule`, `sdk.automation.get`, `sdk.automation.list`, `sdk.automation.cancel` accept only durable-safe registered actions; `sdk.automation.audit` returns bounded, package-owned, payload-free transition records.
- `sdk.pdf.get`, `sdk.pdf.metadata`; `sdk.pdf.viewer.open`, `sdk.pdf.viewer.goToPage`, `sdk.pdf.viewer.search`, `sdk.pdf.viewer.currentPage`.
- `sdk.pdf.annotations.list`, `sdk.pdf.annotations.create`; presentation uses `sdk.pdf.presentation.start`, `sdk.pdf.presentation.current`, `sdk.pdf.presentation.update`, and `sdk.pdf.presentation.end`. See [PDF API](pdf.md).
- `sdk.cards.state`, `sdk.cards.definitions.list`, `sdk.cards.definitions.get`,
  `sdk.cards.definitions.instantiate`, `sdk.cards.shuffle`, `sdk.cards.reset`, `sdk.cards.draw`,
  `sdk.cards.reveal`, `sdk.cards.discard`, `sdk.cards.play`,
  `sdk.cards.updatePlacement`, `sdk.cards.discardPlacement`.

Runtime journals use `sdk.journals.get`, `sdk.journals.list`,
`sdk.journals.create`, `sdk.journals.update`, and `sdk.journals.delete`.
Authorized transient presentation uses `sdk.handouts.present`.

Scene tooling includes `sdk.scene.fog.state`, `sdk.scene.fog.enable`,
`sdk.scene.fog.disable`, `sdk.scene.fog.reset`, `sdk.scene.fog.paint`,
`sdk.scene.images.list`, `sdk.scene.images.place`, `sdk.scene.images.update`,
`sdk.scene.images.delete`, `sdk.scene.geometry.splitWall`,
`sdk.scene.geometry.moveWallNode`, `sdk.scene.geometry.moveWalls`, and
`sdk.scene.geometry.deleteWalls`.

Spatial extension tooling uses `sdk.tools.register` for a package-scoped tool
with automatic disposal and stable world-pointer DTOs. Pure distance queries use
`sdk.scene.measurements.measure`. Expiring shared measurements use `sdk.scene.measurements.share`, `sdk.scene.measurements.listShared`, and `sdk.scene.measurements.cancel`. Persistent shared templates use
`sdk.scene.templates.list`, `sdk.scene.templates.get`,
`sdk.scene.templates.create`, `sdk.scene.templates.update`, and
`sdk.scene.templates.delete`. Particle controls can discover their public
parameter schemas with `sdk.scene.effects.presets`.

Semantic shaders use `sdk.scene.shaders.presets`,
`sdk.scene.shaders.getPreset`, `sdk.scene.shaders.list`,
`sdk.scene.shaders.apply`, `sdk.scene.shaders.update`,
`sdk.scene.shaders.enable`, and `sdk.scene.shaders.remove`. These methods expose
only stable preset metadata, typed parameters and versioned instances; bundled
GLSL and renderer lifecycle remain private.

Trusted custom libraries use `sdk.scene.shaders.customLibrary.registerProvider`,
`sdk.scene.shaders.customLibrary.openEditor`, and
`sdk.scene.shaders.customLibrary.preview`, `sdk.scene.shaders.customLibrary.clearPreview`, and
`sdk.scene.shaders.customLibrary.use`. They connect package-owned storage and UI
to the core-owned editor and placement flow without exposing compilation,
renderer access, or automatic raw application.

Permission-aware UI can distinguish denial from an unsupported action with
`sdk.permissions.check`; `sdk.permissions.can` remains the boolean shortcut.
Optional integrations discover only active public package metadata with
`sdk.packages.get` and `sdk.packages.has`.

Scene image placements expose a monotonic `version`. Pass
`{ expectedVersion: placement.version }` as the third argument to
`sdk.scene.images.update`; a stale writer receives `STALE_VERSION` and its
entire patch is rejected before `scene.images.changed` is emitted.

Annotations support `sdk.pdf.annotations.update` and
`sdk.pdf.annotations.delete` in addition to list/create.
- `sdk.actors.patchData`; `sdk.actors.items.slots`, `sdk.actors.items.listCopies`, `sdk.actors.items.insertCopy`, `sdk.actors.items.removeCopy`; `sdk.combat.setInitiative`, `sdk.combat.moveCombatant`, `sdk.combat.setInitiativeOrder`.

Updates accept `expectedVersion` where documented; a mismatch returns `STALE_VERSION`. Registered actions contain at most 16 allow-listed semantic operations; callers cannot submit graphs. No raw database, transport, renderer, filesystem, or core-DOM access is exposed.

Item sheet data is updated with `sdk.items.patchData`. Combat management also
provides `sdk.combat.advanceRound`, `sdk.combat.setFlags`, and
`sdk.combat.rollInitiative`.

## Universal content references

Packages declaring `content.references` can create a canonical URI with
`sdk.content.ref`, resolve it with `sdk.content.resolve`, obtain its authorized
public value with `sdk.content.get`, and probe access with `sdk.content.can`.
Use `sdk.content.open` to ask the host to open the target and `sdk.content.link`
to build a portable rich-link payload. Resolution is server-side and cannot
cross the active campaign.
`sdk.content.search` queries the authorized campaign content index by text and kind.
It returns `{ entries, nextCursor }`; pass `nextCursor` back as `options.cursor`
to continue. Cursors are opaque, results remain permission-filtered, and each
page is bounded to 100 entries.

`sdk.actors.data(actorId)` returns `{ actor_id, version, data }` after the same
visibility checks as the actor sheet. Hidden and missing actors are both
reported as `NOT_FOUND`. Sheet mutations emit `actor.data.updated`.

Public resource events include `journal.created`, `journal.updated`,
`journal.deleted`, `cards.state.changed`, `scene.fog.changed`, and
`scene.images.changed`. Journal event audiences are filtered using journal
visibility before delivery, including deletion.

## Partial applications and scoped settings

Packages declaring `ui.applications` use `sdk.ui.applications.register`,
`sdk.ui.applications.render`, and `sdk.ui.applications.close`. A render may name
only changed parts, preserving unrelated DOM, focus, and scroll state.

Settings expose `sdk.settings.scope` and `sdk.settings.onChange`. Supported
scopes are `client`, `user`, `campaign`, and `package`; legacy `global` is an
alias for `package`.

## Scene zones and directed interactions

Semantic regions use `sdk.scene.zones.list`, `sdk.scene.zones.get`, `sdk.scene.zones.members`, `sdk.scene.zones.create`, `sdk.scene.zones.update`, and `sdk.scene.zones.delete`. Directed decisions use `sdk.interactions.request`, `sdk.interactions.get`, `sdk.interactions.list`, `sdk.interactions.respond`, and `sdk.interactions.cancel`.

## Scene world objects and semantic presentations

Packages register bounded types with `sdk.scene.objectTypes.register`. Authoritative instances use `sdk.scene.objects.list`, `sdk.scene.objects.get`, `sdk.scene.objects.hitTest`, `sdk.scene.objects.create`, `sdk.scene.objects.update`, `sdk.scene.objects.delete`, and `sdk.scene.objects.interact`. Temporary core-owned projections use `sdk.ui.presentations.show`, `sdk.ui.presentations.get`, `sdk.ui.presentations.list`, `sdk.ui.presentations.wait`, `sdk.ui.presentations.update`, and `sdk.ui.presentations.close`.

## Pointer, audio, navigation and input

Typed drag/drop uses `sdk.ui.dragDrop.registerSource`, `sdk.ui.dragDrop.registerTarget`, `sdk.ui.dragDrop.sources`, `sdk.ui.dragDrop.targets`, and `sdk.ui.dragDrop.drop`. Core audio uses `sdk.audio.play`, `sdk.audio.get`, `sdk.audio.list`, `sdk.audio.update`, and `sdk.audio.stop`. Persisted view navigation uses `sdk.navigation.scene.go` and `sdk.navigation.scene.getState`. Declarative input uses `sdk.input.commands.register`, `sdk.input.commands.list`, `sdk.input.commands.execute`, `sdk.input.bindings.get`, `sdk.input.bindings.set`, and `sdk.input.gestures.register`.

## Durable composition

Multi-step authoritative processes use `sdk.workflows.register`, `sdk.workflows.start`,
`sdk.workflows.get`, `sdk.workflows.list`, and `sdk.workflows.cancel`. Ruleset-independent turn and phase state uses `sdk.gameplay.flows.register`,
`sdk.gameplay.flows.start`, `sdk.gameplay.flows.get`,
`sdk.gameplay.flows.list`, `sdk.gameplay.flows.advance`, and
`sdk.gameplay.flows.submit`. Stable token identities move between Scenes with
`sdk.tokens.transfer` or the atomic party operation `sdk.tokens.transferMany`;
view navigation remains separate. Scheduled semantic sequencing uses
`sdk.timelines.register`, `sdk.timelines.start`, `sdk.timelines.get`,
`sdk.timelines.list`, and `sdk.timelines.cancel`. All four domains remain
server-authoritative and reject executable callbacks, raw renderer operations,
and package-owned timing authority.

An `INTERACTION` step may declare an optional `resultKey`. When the interaction
completes, core writes the single recipient's resolved response *value* — never the
interaction object — into `context[resultKey]`, which the existing `BRANCH` step
consumes unchanged. The key must be a workflow-local identifier and may not claim the
runtime slots `input`, `lastResult`, or `interaction`. Because a scalar branch cannot
represent disagreement, a `resultKey` is only valid on a request with exactly one
recipient. Cancellation, expiry, and provider failure leave the key unset rather than
inventing an answer, so a definition that must handle refusal branches on an absent
key. The value is always derived from server-owned interaction state; a package
cannot supply or override it.

## Campaign roster and token control

`sdk.campaign.members()` returns the campaign roster as `{ userId, role, name }`,
the same membership the native table already shows the caller. It carries no account
metadata, is scoped to the active campaign, and answers only for a caller who is
themselves a member. It is a roster, not a presence feed: membership is not online
status.

The bounded visual projection is separate: `sdk.users.presentation.get(userId)`
and `sdk.users.presentation.list()` return only `{ userId, color }` for members
visible in the active campaign. See [User presentation](user-presentation.md).

`TokenDTO.controllers` reports the users who may control that token, derived from the
same authority that decides whether a move is allowed, so a token with several owners
lists all of them rather than collapsing to one. The projection is filtered: a caller
sees controllers only for tokens they could control themselves, which keeps a shared
board from becoming a roster side-channel. Knowing a controller id grants nothing —
every operation still derives its principal from the authenticated session.

Together these let a module react to `zone.entered`: read the token, take the
authorized controllers, and address a Directed Interaction at a real participant.

## Native Sounds and Spatial Sounds

Reusable semantic audio content is a first-class campaign resource, distinct
from runtime playback. The Sound library uses `sdk.sounds.list`,
`sdk.sounds.get`, `sdk.sounds.create`, `sdk.sounds.update`, and
`sdk.sounds.delete`; creation references an authorized canonical `audio` Asset
(`{ kind: "library-asset", id }`) or a package-shipped audio resource
(`{ kind: "package-asset", id }`), which the server canonicalizes through the
same safe ingestion pipeline before the Sound exists. Deleting a Sound that a
Playlist, Soundscape, or Spatial Sound still references fails with the native
dependency policy instead of leaving a broken reference.

Persistent Scene emitters use `sdk.scene.spatialSounds.list`,
`sdk.scene.spatialSounds.get`, `sdk.scene.spatialSounds.create`,
`sdk.scene.spatialSounds.update`, and `sdk.scene.spatialSounds.delete`. An
emitter references a Sound by `soundId`; raw Asset URLs and filesystem paths are
never accepted as emitter identity. With `constrainedByWalls`, Wall and Door
geometry attenuates the emitter as a projection, so opening or closing a Door
changes what listeners hear without restarting the stream.

The boundary is deliberate: `sdk.sounds.*` owns reusable persistent content,
`sdk.audio.*` owns runtime playback and control, and `sdk.scene.spatialSounds.*`
owns persistent spatial Scene emitters.

## Shortcuts

| Shortcut | Equivalent |
|---|---|
| `sdk.toast(message, options)` | `sdk.ui.toast(message, options)` |
| `sdk.setting(key)` | `sdk.settings.get(key)` |
| `sdk.setting(key, value)` | `sdk.settings.set(key, value)` |
