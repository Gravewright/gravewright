# Tutorial: from zero to a working addon

This walkthrough builds a real, installable addon from scratch: a package that shows a
toast when the game is ready. The finished package is shipped as
[`examples/packages/hello-toast`](../../examples/packages/hello-toast) and is validated
in CI, so every step here is known to work.

An `addon` is an optional, campaign-activated package. It can add UI, plugins, settings,
chat cards, scene tools, and runtime behavior, and several addons can be active in the
same campaign at once.

## Prerequisites

- A working Gravewright checkout where the `grave` CLI runs (see [`getting-started.md`](../getting-started.md)).
- A campaign you can activate packages in (note its campaign id).

## 1. Scaffold the package

Generate an addon that includes trusted JavaScript:

```bash
grave addon new hello-toast --name "Hello Toast" --js
```

This creates the package under `data/packages/hello-toast/`:

```text
data/packages/hello-toast/
  manifest.json
  README.md
  assets/
    hello-toast.js
```

The generated `manifest.json` already declares `kind: "addon"`, `activation.mode: "multiple"`,
the `assets.scripts` capability, and the `entrypoints.game.scripts` entry that loads your
script. Because the addon shows a toast, add the `assets.ui` capability:

```json
{
  "kind": "addon",
  "id": "hello-toast",
  "capabilities": ["assets.scripts", "assets.ui"],
  "activation": { "scope": "campaign", "mode": "multiple" },
  "entrypoints": {
    "game": {
      "scripts": ["assets/hello-toast.js"]
    }
  },
  "provides": {}
}
```

> `sdk.toast(...)` is gated by `assets.ui`. Calling it without declaring the capability
> throws an actionable error. See [`capabilities.md`](capabilities.md).

## 2. Write the runtime

Replace `assets/hello-toast.js` with:

```js
window.GravewrightSDK.register({
  id: "hello-toast",
  ready(sdk) {
    sdk.toast("Hello from the Gravewright SDK");
  },
});
```

The `id` must match the manifest id and must be called from the package's own declared
script. `ready` runs after the game runtime is ready. See [`runtime.md`](runtime.md).

## 3. Validate

```bash
grave package validate data/packages/hello-toast
```

Expected output:

```text
hello-toast: ok
```

If you see `error: ...`, the message names the manifest field or missing file to fix.
The full error key list is in [`validation.md`](validation.md).

## 4. Install and enable

```bash
grave package install hello-toast --yes --enable
```

Install prints the package's requested capabilities before committing (it warns when a
package runs trusted JavaScript). `--enable` makes it available to campaigns.

## 5. Activate in a campaign

```bash
grave campaign package activate <campaign_id> hello-toast
```

Use the campaign's **id**, not its title. List active packages to confirm:

```bash
grave campaign package list <campaign_id>
```

## 6. See it work

Open the campaign's table in Gravewright. When the game runtime is ready, the toast
**"Hello from the Gravewright SDK"** appears.

## 7. Debug when something is off

```bash
grave package doctor hello-toast
```

Doctor reports manifest validity, install/enable status, and dependency problems with an
actionable fix for each. See [`troubleshooting.md`](troubleshooting.md).

## Next steps

- Add a user setting (see [`examples/packages/toggle-example`](../../examples/packages/toggle-example) and [`settings.md`](settings.md)).
- Build a ruleset: [`tutorial-ruleset.md`](tutorial-ruleset.md).
- Map goals to capabilities and APIs: [`power-map.md`](power-map.md).
