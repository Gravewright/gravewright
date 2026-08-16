# Início rápido da SDK 1

Crie um addon com esta estrutura:

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

Valide com `grave package validate caminho/do/my-addon`, instale, ative na
campanha e execute `grave doctor`. O package recebe somente métodos permitidos
pelas capabilities declaradas e pela autoridade do usuário atual.

Consulte [manifest](manifest.md), [métodos](method-reference.md),
[DTOs](dto-reference.md) e o
[contrato legível por máquina](../../sdk/_data/gravewright-sdk-1.json).
