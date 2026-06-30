# Exemplos da SDK

Cada exemplo desta página é um pacote real em [`examples/packages/`](../../../examples/packages). O CI valida todos eles com `grave package validate`, então os trechos abaixo permanecem em sincronia com pacotes que de fato passam na validação.

```bash
grave package validate examples/packages
```

## Addon mínimo com um toast

Pacote: [`examples/packages/hello-toast`](../../../examples/packages/hello-toast)

```text
examples/packages/hello-toast/
  manifest.json
  assets/
    hello-toast.js
```

`manifest.json`:

```json
{
  "$schema": "https://raw.githubusercontent.com/Gravewright/gravewright/main/schemas/gravewright-package-v1.schema.json",
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "addon",
  "id": "hello-toast",
  "name": "Hello Toast",
  "version": "0.1.0",
  "description": "Minimal addon that shows a toast when the game is ready.",
  "authors": ["Example Author"],
  "license": "MIT",
  "compatibility": {
    "minimum": "1",
    "verified": "1"
  },
  "capabilities": ["assets.scripts", "assets.ui"],
  "activation": {
    "scope": "campaign",
    "mode": "multiple"
  },
  "entrypoints": {
    "game": {
      "scripts": ["assets/hello-toast.js"]
    }
  },
  "provides": {}
}
```

`assets/hello-toast.js`:

```js
window.GravewrightSDK.register({
  id: "hello-toast",
  ready(sdk) {
    sdk.toast("Hello from the Gravewright SDK");
  },
});
```

Valide:

```bash
grave package validate examples/packages/hello-toast
```

## Addon com settings

Pacote: [`examples/packages/toggle-example`](../../../examples/packages/toggle-example)

Trecho do `manifest.json`:

```json
{
  "kind": "addon",
  "id": "toggle-example",
  "capabilities": ["assets.scripts", "assets.ui", "settings"],
  "settings": [
    {
      "key": "enabled",
      "scope": "user",
      "type": "boolean",
      "default": true,
      "label": "Enable addon"
    }
  ],
  "entrypoints": {
    "game": {
      "scripts": ["assets/toggle-example.js"]
    }
  }
}
```

`assets/toggle-example.js`:

```js
window.GravewrightSDK.register({
  id: "toggle-example",
  ready(sdk) {
    if (sdk.setting("enabled") !== false) {
      sdk.toast("Toggle Example enabled");
    }
  },
});
```

## Addon que escuta eventos de pacote

Trecho do `manifest.json`:

```json
"capabilities": ["assets.scripts", "bus.subscribe"],
"interop": { "listens": { "dice-roller.settled": {} } }
```

Runtime:

```js
window.GravewrightSDK.register({
  id: "event-listener",
  setup(sdk) {
    sdk.bus.subscribe("dice-roller.settled", (payload) => {
      if (!payload || payload.version !== 1) return;
      console.log("Dice settled", payload);
    });
  },
});
```

## Pacote que emite eventos versionados

```js
window.GravewrightSDK.register({
  id: "roller-addon",
  setup(sdk) {
    function announceRoll(rollId, total) {
      sdk.bus.publish("roller-addon.roll-finished", {
        version: 1,
        rollId,
        total,
      });
    }
  },
});
```

Requer:

```json
"capabilities": ["assets.scripts", "bus.publish"],
"interop": { "emits": { "roller-addon.roll-finished": {} } }
```

## Esqueleto mínimo de ruleset

Pacote: [`examples/packages/my-rpg`](../../../examples/packages/my-rpg)

```text
examples/packages/my-rpg/
  manifest.json
  schemas/
    character.schema.json
    item.schema.json
  layouts/
    character.sheet.gw.json
    item.sheet.gw.json
  rules/
    formulas.gw.json
  locales/
    en.json
```

`manifest.json`:

```json
{
  "$schema": "https://raw.githubusercontent.com/Gravewright/gravewright/main/schemas/gravewright-package-v1.schema.json",
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "ruleset",
  "id": "my-rpg",
  "name": "My RPG",
  "version": "0.1.0",
  "description": "Minimal ruleset example with one actor type, one item type, a rule, and locales.",
  "authors": ["Example Author"],
  "license": "MIT",
  "compatibility": {
    "minimum": "1",
    "verified": "1"
  },
  "capabilities": [
    "actors.register",
    "items.register",
    "sheets.declarative",
    "rules.declarative",
    "locales"
  ],
  "activation": {
    "scope": "campaign",
    "mode": "exclusive"
  },
  "entrypoints": {},
  "provides": {
    "storage": {
      "model": "scoped-json-v1"
    },
    "actorTypes": [
      {
        "id": "character",
        "labelKey": "my-rpg.actor.character",
        "schema": "schemas/character.schema.json",
        "sheet": "layouts/character.sheet.gw.json"
      }
    ],
    "itemTypes": [
      {
        "id": "item",
        "labelKey": "my-rpg.item.item",
        "schema": "schemas/item.schema.json",
        "sheet": "layouts/item.sheet.gw.json"
      }
    ],
    "rules": {
      "formulas": "rules/formulas.gw.json"
    },
    "locales": {
      "en": "locales/en.json"
    }
  }
}
```

Valide:

```bash
grave package validate examples/packages/my-rpg
```

## Asset pack

Pacote: [`examples/packages/dark-fantasy-assets`](../../../examples/packages/dark-fantasy-assets)

```json
{
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "assets",
  "id": "dark-fantasy-assets",
  "name": "Dark Fantasy Assets",
  "version": "0.1.0",
  "compatibility": { "minimum": "1", "verified": "1" },
  "capabilities": ["assets.pack", "assets.images", "assets.maps", "assets.icons"],
  "activation": { "scope": "campaign", "mode": "multiple" },
  "entrypoints": {},
  "provides": {
    "assets": {
      "images": [
        { "id": "banner", "label": "Banner", "path": "images/banner.webp" }
      ],
      "maps": [
        { "id": "crypt", "label": "Crypt", "path": "maps/crypt.webp" }
      ],
      "icons": [
        { "id": "skull", "label": "Skull", "path": "icons/skull.svg" }
      ]
    }
  }
}
```
