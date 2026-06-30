# Browser runtime — `window.GravewrightSDK`

`window.GravewrightSDK` is the single public browser entry point for package scripts.

The table page loads active package client manifests, loads declared package assets, and then the browser runtime gives each registered package a scoped `sdk` object. The scoped `sdk` exposes only documented namespaces and enforces the package's declared capabilities.

## Registering a package

```js
window.GravewrightSDK.register({
  id: "my-package",
  setup(sdk, payload) {
    // Called once the package manifest is known.
  },
  ready(sdk, payload) {
    // Called after the game runtime is ready.
  },
});
```

`register` returns `true` when registration is accepted and `false` when rejected.

Registration is rejected when:

- `id` is missing;
- the script is not running as a package-owned script;
- the script's package id does not match the claimed id;
- the package is not active in the current campaign;
- the package already registered a runtime.

## Script ownership

Package scripts are associated with their manifest id. The runtime verifies the current script before accepting `register(...)`:

- package scripts can claim only their own package id;
- package scripts cannot impersonate another package;
- duplicate registrations are refused;
- inactive package registrations are refused.

Server-provided script metadata can include `data-gw-package` and `data-gw-nonce`. When present, the nonce must match the package nonce in the game context.

## Lifecycle

### `setup(sdk, payload)`

Called once after the package runtime and active client manifest are both known.

Use `setup` to:

- register runtime plugins;
- register commands;
- register sheet behavior;
- register combat behavior;
- initialize browser-local state;
- subscribe to package events.

Do not assume the full game UI is ready unless `sdk.game.ready()` returns `true`.

### `ready(sdk, payload)`

Called once after the game runtime is ready.

Use `ready` to:

- read the active context;
- initialize UI that requires the table runtime;
- react to loaded scene/campaign state;
- emit package-ready events.

### Ready lifecycle

A package's `ready(sdk, payload)` runs once after the table runtime is
initialized:

```js
window.GravewrightSDK.register({
  id: "my-package",
  ready(sdk, { context }) {
    // Table runtime is ready.
  },
});
```

## Payload shape

Both `setup` and `ready` receive:

```js
{
  package: /* active client manifest for this package */,
  context: /* game context snapshot */
}
```

Treat payload data as read-only. Use documented SDK methods to read or request mutations.

## Scoped SDK namespaces

```text
sdk.version
sdk.package
sdk.kind
sdk.capabilities
sdk.context
sdk.game
sdk.bus
sdk.commands
sdk.ui
sdk.chat
sdk.dice
sdk.rolls
sdk.settings
sdk.sheets
sdk.combat
sdk.tokens
sdk.scene
sdk.tools
sdk.content
sdk.i18n
```

See [`reference.md`](reference.md) for complete method details.

## Shortcuts

```js
sdk.toast("Hello");                   // alias for sdk.ui.toast
sdk.setting("enabled");               // get a setting
sdk.setting("enabled", true);         // set a setting
```

Shortcuts enforce the same capabilities as the underlying namespace methods.

## Dev-only debug object

When the server runs with `APP_DEBUG=true`, the runtime exposes a read-only debug object:

```js
GravewrightSDKDebug.packages();   // active package client manifests
GravewrightSDKDebug.runtimes();   // package ids that registered a runtime
GravewrightSDKDebug.listeners();  // registered event names
GravewrightSDKDebug.context();    // frozen game context
```

`window.GravewrightSDKDebug` is absent in production. Do not rely on it in package code.

## Error behavior

Package lifecycle errors are caught and logged so one package cannot crash the entire runtime.

Capability violations throw clear errors from the calling SDK method. Package authors should fix the manifest or stop calling the method.

## Public boundary

Public:

- `window.GravewrightSDK.version`
- `window.GravewrightSDK.register(...)`
- the scoped `sdk` object passed to registered packages

Not public:

- internal manifest loading helpers;
- internal package event bus implementation;
- private renderer globals;
- DOM structure;
- `window.GravewrightSDKDebug` in production;
