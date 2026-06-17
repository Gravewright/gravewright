# SDK troubleshooting

Use this guide when a package does not validate, install, activate, or run correctly.

## Start with validation

```bash
grave package validate data/packages/my-package
grave package validate data/packages/my-package --json
grave package doctor my-package
grave doctor --packages-dir data/packages
```

Fix validation errors before debugging browser runtime behavior.

## Package does not appear

Check:

- package directory is under `data/packages/{kind_plural}/{id}/`;
- `manifest.json` exists;
- manifest `id` matches the directory name;
- `kind` is valid;
- package validates;
- package is installed/enabled when required;
- package compatibility is not incompatible.

Useful commands:

```bash
grave package list
grave package doctor my-package
grave doctor --json
```

## Manifest validation fails

Common causes:

- missing `schemaVersion: 1`;
- missing `sdkVersion: "1"`;
- invalid package `kind`;
- unsafe id or path;
- missing compatibility declaration;
- unknown or forbidden capability;
- wrong activation mode for kind;
- ruleset missing storage model or actor types;
- assets package declaring game model fields;
- missing content pack path;
- invalid setting enum without `options`.

See [`validation.md`](validation.md).

## Entrypoint script does not run

Check:

- package declares `assets.scripts` capability;
- script path is listed under `entrypoints.game.scripts`;
- script path exists and is package-relative;
- package is active in the current campaign;
- browser console has no script load errors;
- `window.GravewrightSDK.register({ id })` uses the exact manifest id.

## `GravewrightSDK.register` returns false

Likely causes:

- missing `id`;
- id does not match the manifest id;
- script is not loaded as a package-owned script;
- package is inactive;
- duplicate registration;
- package script ownership/nonce check failed.

Inspect the browser console for a `GravewrightSDK.register refused ...` message.

## Capability error at runtime

Example:

```text
Package "my-package" attempted to use sdk.chat.send but does not declare capability "chat.cards".
```

Fix one of these:

- add the required capability to `manifest.json`;
- stop calling that SDK method;
- replace the runtime behavior with declarative package data.

See [`capabilities.md`](capabilities.md).

## Settings do not persist

Check:

- package declares `settings` capability;
- setting is declared in `manifest.json`;
- setting `key` matches exactly;
- setting `type` and `scope` are valid;
- enum settings declare `options`;
- the active campaign id is available or explicitly passed to `sdk.settings.set`.

Example:

```js
await sdk.settings.set("enabled", true, { campaignId: sdk.game.campaign()?.id });
```

## Content pack cannot be loaded

Check:

- package declares `content.packs` capability;
- content pack is listed under `provides.contentPacks`;
- content pack `id` is correct;
- content pack `type` is one of the allowed values;
- content pack `path` exists and is safe;
- runtime uses the current package's `sdk.content.pack(packId)`.

## Events are not received

Check:

- both packages declare the matching `bus.*` capabilities and `interop` entries;
- listener is registered before the event fires or the event is emitted after registration;
- event name matches exactly;
- event name is package-namespaced;
- payload `version` is supported;
- optional peer package is installed and active when expected.

For optional integrations, absence of events is normal when the peer package is inactive.

## Sheet runtime plugins do not run

Check:

- package declares `sheets.runtime`;
- ruleset/addon script registers through `sdk.sheets.register(...)`;
- plugin methods use supported names;
- the plugin returns the expected type;
- package is active in the campaign;
- browser console has no setup errors.

## Combat runtime plugins do not run

Check:

- package declares `combat.runtime`;
- package registers with `sdk.combat.register(...)` or `sdk.combat.registerPanel(...)`;
- plugin handlers/slots use supported names;
- return values match documented expectations;
- package is active.

## Package works in debug but not production

Check for accidental use of:

- `window.GravewrightSDKDebug`;
- private renderer globals;
- DOM structure not documented as public;
- test-only data;
- `APP_DEBUG=true` behavior.

`window.GravewrightSDKDebug` is absent in production.

## Old extension docs still appear

Remove stale files and links. The supported extension surface is the SDK package model under `docs/sdk/`:

```bash
rm -f docs/api/extension-apis.md

```

Do not preserve old extension API pages in the public docs. Replace them with SDK package-model pages.
