# Inicio rápido de SDK 1

Cree un addon con esta estructura:

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

Valide con `grave package validate ruta/del/my-addon`, instálelo, actívelo en la
campaña y ejecute `grave doctor`. El package recibe únicamente los métodos
permitidos por las capabilities declaradas y por la autoridad del usuario actual.

Consulte [manifest](../../sdk/manifest.md), [métodos](method-reference.md),
[DTOs](dto-reference.md) y el
[contrato legible por máquina](../../sdk/_data/gravewright-sdk-1.json).
