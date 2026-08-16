# SDK 1 quick start

Create an addon with this layout:

```text
my-addon/
├── manifest.json
└── main.js
```

`manifest.json`:

```json
{"schemaVersion":1,"sdkVersion":"1","kind":"addon","id":"my-addon","name":"My Addon","version":"1.0.0","compatibility":{"minimum":"1","verified":"1"},"capabilities":["assets.scripts","events.subscribe","assets.ui"],"activation":{"scope":"campaign","mode":"multiple"},"entrypoints":{"game":{"scripts":["main.js"]}},"provides":{}}
```

`main.js`:

```js
(() => {
  let dispose = () => {};
  window.GravewrightSDK.register({
    id: "my-addon",
    setup(sdk) {
      dispose = sdk.events.on("scene.updated", () => {
        sdk.ui.toast("The scene changed.");
      });
    },
    unload() { dispose(); },
  });
})();
```

Validate it with `grave package validate path/to/my-addon`, install it, activate
it for a campaign, and run `grave doctor`. Packages receive only the methods
allowed by their declared capabilities and the current user's authority.

See [manifest](manifest.md), [methods](method-reference.md),
[DTOs](dto-reference.md), and the [machine-readable contract](_data/gravewright-sdk-1.json).
