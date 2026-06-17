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

```js
sdk.combat.register({
  handlers: {
    participantMeta({ participant }) {
      return participant?.actor_type || "";
    },
  },
  slots: {
    participantActions({ participant }) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = participant?.actor_type || "Action";
      return button;
    },
  },
});
```

### `sdk.combat.registerPanel(panel)`

Registers a combat panel replacement/extension object.

```js
sdk.combat.registerPanel({
  renderHud(context) {},
  renderPanel(context) {},
});
```

Panel replacement is powerful; prefer lightweight handlers and slots when possible.

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

## Shortcuts

| Shortcut | Equivalent |
|---|---|
| `sdk.toast(message, options)` | `sdk.ui.toast(message, options)` |
| `sdk.setting(key)` | `sdk.settings.get(key)` |
| `sdk.setting(key, value)` | `sdk.settings.set(key, value)` |
