# Browser Runtime — `window.GravewrightSDK`

The single browser entry point for packages. Loaded by the table from
`static/js/sdk/`. The active packages' client manifests are injected as JSON in
the page and consumed by the runtime before package scripts register.

## Registering a package

```js
window.GravewrightSDK.register({
  id: "my-package",
  setup(sdk, payload) {
    // Register hooks, sheets, combat, local state.
  },
  ready(sdk, payload) {
    // Called after the game runtime is ready.
  },
});
```

`setup` runs once the package's client manifest is known; `ready` runs after the
game runtime is ready. A package must register from its own declared script URL;
the runtime refuses duplicate registrations and attempts to register as another
active package.

## The scoped `sdk`

Each package receives a scoped `sdk` with these namespaces:

```
sdk.version      sdk.package      sdk.kind        sdk.capabilities
sdk.context      sdk.game         sdk.hooks       sdk.events
sdk.commands     sdk.ui           sdk.chat        sdk.settings
sdk.sheets       sdk.combat       sdk.tokens      sdk.scene
sdk.tools        sdk.content      sdk.i18n
```

### Shortcuts

```js
sdk.on("game:ready", cb);
sdk.once("scene:loaded", cb);
sdk.toast("Hello");
sdk.setting("enabled");          // get
sdk.setting("enabled", true);    // set
```

## Capability enforcement

Namespace methods are gated by capabilities. Calling a method without the
declared capability throws:

```
Package "x" attempted to use sdk.chat.send but does not declare capability "chat.cards".
```

The global object exposes only the public runtime entry point. Internal
manifest-loading helpers and the package event bus are not public globals;
packages should use the scoped `sdk` passed to `register`.

## Debug introspection (`window.GravewrightSDKDebug`)

When the server runs with `APP_DEBUG=true` it sets `context.debug`, and the
runtime exposes a read-only `window.GravewrightSDKDebug` for development and
tests. It is **absent in production** (`APP_DEBUG` must be `false` there):

```js
GravewrightSDKDebug.packages()  // active package client manifests
GravewrightSDKDebug.runtimes()  // ids of packages that registered a runtime
GravewrightSDKDebug.listeners() // registered package event names
GravewrightSDKDebug.context()   // the frozen game context
```

The browser end-to-end test (`tests/e2e/test_sdk_packages_e2e.py`) drives a real
Firefox through install → enable → activate → table and reads this object to
confirm that bundled packages actually register through the SDK.

## Notes for ruleset integration

Rulesets register sheet and combat behavior through `sdk.sheets.register(...)`
and `sdk.combat.register(...)`. Rulesets that replace the combat panel use
`sdk.combat.registerPanel({ renderHud, renderPanel })`.
`window.GravewrightSDK` is the only public package API; pre-SDK browser globals
are not part of the contract.
