# Browser Extension APIs

Gravewright exposes public browser APIs for systems and modules.

API materials are MIT-licensed. The implementation remains Apache-2.0.

> [!WARNING]
> **Alpha.**
>
> Use only documented APIs. Internal globals, private stores, renderer internals, fallback behavior, and core DOM structure may change between Alpha releases.

## Main Surfaces

| Surface | Used by | Purpose |
|---|---|---|
| `window.Gravewright.modules` | Modules | Register module runtimes, inspect modules, and get scoped APIs |
| scoped `api.*` | Modules | Hooks, UI, settings, chat, scene, token, and context APIs |
| `window.GravewrightSheets` | Systems | Sheet labels, small sheet behavior extensions, and sheet header/section hooks |
| `window.GravewrightCombat` | Systems | Lightweight combat tracker hooks and slots |

The backend is authoritative for game state.

Browser APIs can improve UI, react to events, and submit intentions. They should not treat local state as final truth.

## Module Runtime API

```js
(function () {
  window.Gravewright.modules.register({
    id: "my-module",

    init(api, payload) {
      // Called when the module runtime is initialized.
    },

    ready(api, payload) {
      // Called when the module runtime is ready.
    }
  });
})();
```

The runtime id must match the manifest id.

`payload` contains:

```js
{
  module,  // normalized module manifest
  api,     // scoped module API
  context  // current game context
}
```

## Scoped Module API

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

Returned values are cloned or frozen snapshots.

### `api.hooks`

Requires `hooks.client`.

```js
const off = api.hooks.on("game:ready", ({ context }) => {
  // React to the game becoming ready.
});

api.hooks.once("scene:loaded", ({ scene }) => {
  // React once.
});

off();
```

Official hooks:

- `module:init`
- `module:ready`
- `module:failed`
- `game:ready`
- `campaign:loaded`
- `scene:loaded`

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
api.chat.send({
  type: "module-message",
  text: "Hello"
});
```

### `api.scene`, `api.tokens`, and `api.tools`

```js
const canvas = api.scene.activeCanvas(); // assets.ui
const camera = api.scene.activeCameraForScene(sceneId); // assets.ui

api.tokens.centerOn(tokenId); // tokens.extends

const tool = api.tools.activeTool(); // assets.ui
```

## System Sheet API

Systems may register small browser-side sheet behavior through `window.GravewrightSheets`.

```js
(function () {
  const Sheets = window.GravewrightSheets;
  if (!Sheets || typeof Sheets.registerSystem !== "function") return;

  Sheets.registerSystem("my-system", {
    labels: {
      actorName: "Name",
      roll: "Roll",
      equipped: "Equipped",
      prepared: "Prepared"
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
    }
  });
})();
```

### Sheet labels

Systems may provide sheet labels through `labels`.

The engine provides English fallback labels. System labels are merged with the fallback labels. Missing keys fall back to English.

Known sheet label keys:

| Key | Purpose |
|---|---|
| `actorName` | Actor name placeholder |
| `levelPrefix` | Prefix used before a level value |
| `equipped` | Equipped item badge |
| `spellCirclePrefix` | Prefix used before a spell circle/level |
| `prepared` | Prepared spell badge |
| `active` | Active effect/status label |
| `inactive` | Inactive effect/status label |
| `qtyPrefix` | Quantity prefix |
| `portrait` | Portrait placeholder |
| `token` | Token placeholder |
| `uploadPortrait` | Portrait upload title |
| `uploadToken` | Token upload title |
| `cancel` | Cancel button label |
| `roll` | Generic roll label |
| `rollDialogTitle` | Roll dialog title |
| `healed` | Healing toast text |
| `tookDamage` | Damage toast text |
| `reducedFrom` | Damage reduction toast text |

Example:

```js
(function () {
  const Sheets = window.GravewrightSheets;
  if (!Sheets || typeof Sheets.registerSystem !== "function") return;

  Sheets.registerSystem("my-system", {
    labels: {
      actorName: "Name",
      levelPrefix: "Level",
      equipped: "Equipped",
      spellCirclePrefix: "Circle",
      prepared: "Prepared",
      active: "Active",
      inactive: "Inactive",
      qtyPrefix: "Qty",
      portrait: "Portrait",
      token: "Token",
      uploadPortrait: "Upload portrait",
      uploadToken: "Upload token",
      cancel: "Cancel",
      roll: "Roll",
      rollDialogTitle: "Roll",
      healed: "healed",
      tookDamage: "took",
      reducedFrom: "reduced from"
    }
  });
})();
```

### Sheet hooks

Known sheet hooks:

| Hook | Return | Purpose |
|---|---|---|
| `renderSection(node, variant, renderContext, helpers)` | `Node` or `null` | Render a custom sheet section |
| `renderHeaderIdentity(main, bundle, helpers)` | `void` | Extend the sheet header identity area |
| `autoFitWidth(actorType)` | `number` or `null` | Suggest modal width for an actor type |

### Sheet helper boundary

The `helpers` object passed to sheet hooks is the supported helper surface.

Systems should not rely on undocumented renderer variables, private stores, DOM structure, or internal CSS classes unless they are explicitly documented as public extension points.

## System Combat API

Systems may register lightweight combat hooks and slots through `window.GravewrightCombat`.

```js
(function () {
  const Combat = window.GravewrightCombat;
  if (!Combat || typeof Combat.registerSystem !== "function") return;

  Combat.registerSystem("my-system", {
    hooks: {
      participantMeta({ participant }) {
        return participant?.actor_type || "";
      }
    },

    slots: {
      participantActions({ participant }) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "my-combat-action";
        button.textContent = participant?.actor_type || "Action";
        return button;
      }
    }
  });
})();
```

Known combat hooks:

| Hook | Return | Purpose |
|---|---|---|
| `beforeRender` | `void` | Called before the combat tracker renders |
| `afterRender` | `void` | Called after the combat tracker renders |
| `participantMeta` | `string`, `string[]`, or falsy | Adds system-specific participant metadata |

Known combat slots:

| Slot | Return | Purpose |
|---|---|---|
| `participantActions` | `Node`, `Node[]`, or falsy | Adds system-specific controls to a participant action area |

The combat API is intentionally small.

Systems should prefer combat configuration, labels, hooks, slots, and CSS over replacing the entire core combat tracker renderer.

Replacing `window.GravewrightCombatPanel` is not part of the stable public API during Alpha.

## Private Implementation Details

The following are private unless documented elsewhere:

- renderer globals;
- DOM structure;
- private stores;
- internal event ordering;
- CSS class names not documented as extension hooks;
- fallback labels;
- full sheet renderer replacement;
- full combat renderer replacement.

Use documented APIs, declarative configuration, labels, locales, hooks, slots, and assets instead.