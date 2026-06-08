# Browser Extension APIs

Gravewright exposes public browser APIs for systems and modules. API materials are MIT-licensed. The implementation remains Apache-2.0.

> [!WARNING]
> **Alpha.** Use only documented APIs. Internal globals, private stores, and core DOM structure may change between Alpha releases.

## Main surfaces

| Surface | Used by | Purpose |
|---|---|---|
| `window.Gravewright.modules` | modules | register runtimes, inspect modules, get scoped APIs |
| scoped `api.*` | modules | hooks, UI, settings, chat, scene, token, and context APIs |
| `window.GravewrightSheets` | systems | small sheet behavior extensions |
| `window.GravewrightCombat` | systems | lightweight combat tracker hooks and slots |

The backend is authoritative for game state. Browser APIs can improve UI, react to events, and submit intentions; they should not treat local state as final truth.

## Module runtime API

```js
(function () {
  window.Gravewright.modules.register({
    id: "my-module",
    init(api, payload) {},
    ready(api, payload) {}
  });
})();
```

The runtime id must match the manifest id.

`payload` contains:

```js
{
  module,   // normalized module manifest
  api,      // scoped module API
  context   // current game context
}
```

## Scoped module API

Namespaces:

```text
api.version
api.capabilities
api.hooks
api.game
api.chat
api.scene
api.settings
api.tokens
api.tools
api.ui
```

### `api.capabilities`

```js
api.capabilities.has("settings");
api.capabilities.require("assets.ui", "my-feature");
api.capabilities.requirement("settings.get");
api.capabilities.list();
```

### `api.game`

```js
const context = api.game.context();
const campaign = api.game.campaign();
const scene = api.game.scene();
const user = api.game.user();
```

Returned values are cloned/frozen snapshots.

### `api.hooks`

Requires `hooks.client`.

```js
const off = api.hooks.on("game:ready", ({ context }) => {});
api.hooks.once("scene:loaded", ({ scene }) => {});
off();
```

Official hooks: `module:init`, `module:ready`, `module:failed`, `game:ready`, `campaign:loaded`, `scene:loaded`.

### `api.ui`

Requires `assets.ui`.

```js
api.ui.toast("Hello from a module", { duration: 4000 });
api.ui.openModal("modal-id");
api.ui.closeModal("modal-id");
```

### `api.settings`

Requires `settings`.

```js
const value = api.settings.get("ui.enabled", true);
await api.settings.set("ui.enabled", false);
```

### `api.chat`

Requires `chat.cards`.

```js
api.chat.send({ type: "module-message", text: "Hello" });
```

### `api.scene`, `api.tokens`, `api.tools`

```js
const canvas = api.scene.activeCanvas();       // assets.ui
const camera = api.scene.activeCameraForScene(sceneId); // assets.ui
api.tokens.centerOn(tokenId);                  // tokens.extends
const tool = api.tools.activeTool();            // assets.ui
```

## System Sheet API

```js
(function () {
  const Sheets = window.GravewrightSheets;
  if (!Sheets || typeof Sheets.registerSystem !== "function") return;

  Sheets.registerSystem("my-system", {
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
    }
  });
})();
```

Known hooks:

| Hook | Return | Purpose |
|---|---|---|
| `renderSection(node, variant, renderContext, helpers)` | `Node` or `null` | render a custom sheet section |
| `renderHeaderIdentity(main, bundle, helpers)` | `void` | extend the sheet header |
| `autoFitWidth(actorType)` | number or `null` | suggest modal width |

## System Combat API

```js
(function () {
  const Combat = window.GravewrightCombat;
  if (!Combat || typeof Combat.registerSystem !== "function") return;

  Combat.registerSystem("my-system", {
    hooks: {
      participantMeta(payload) {
        return payload.participant?.actor_type || "";
      }
    },
    slots: {
      participantBadge(payload) {
        const badge = document.createElement("span");
        badge.className = "my-combat-badge";
        badge.textContent = payload.participant?.actor_type || "";
        return badge;
      }
    }
  });
})();
```

The combat API is intentionally small. Systems should not replace the entire core combat tracker renderer.
