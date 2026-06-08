# Creating a Module

> [!WARNING]
> **Module API v1 is Alpha.**
> Modules run JavaScript in the table browser context and can affect a campaign's user experience. Do not use experimental modules in long campaigns before testing them in one-shots.

A **module** is an optional Gravewright extension. It can add CSS, client-side JavaScript, hooks, settings, optional content, and lightweight integrations without changing the core application and without defining a complete game system.

Modules are installed globally, but enabled per campaign. Installing a module does not automatically affect every table: the GM chooses which modules load for each campaign.

## When to create a module

Create a module when you want to:

- add optional behavior to a table;
- add a visual overlay, theme, button, toast, or panel;
- listen to hooks such as `game:ready` or `scene:loaded`;
- add settings per user, campaign, or installation;
- distribute optional content packs;
- improve the experience of an existing system without replacing it;
- experiment with a feature before proposing it for core.

Do not create a module to define actor types, fundamental schemas, base character sheets, or structural game rules. Use a **system** for that.

## Mental model

A module has three main parts:

1. **Manifest**: declares identity, assets, capabilities, settings, dependencies, conflicts, and compatibility.
2. **Assets**: CSS and JavaScript loaded in entrypoints such as `game` and `inside`.
3. **Client-side runtime**: code that registers the module with `window.Gravewright.modules.register(...)` and uses the scoped public API.

The backend validates and serves declared files. It does not execute module code on the server.

## Recommended package layout

```text
data/modules/my-module/
  manifest.json
  README.md

  assets/
    my-module.css
    my-module.js

  locales/
    en.json
    pt-BR.json

  content/
    items.extra.gwpack.json
```

Minimal layout:

```text
data/modules/my-module/
  manifest.json
  assets/my-module.js
```

## Minimal manifest

```json
{
  "schemaVersion": 1,
  "type": "module",
  "id": "my-module",
  "name": "My Module",
  "version": "0.1.0",
  "apiVersion": "1",
  "description": "Example Gravewright module.",
  "authors": [
    { "name": "Your Name" }
  ],
  "license": "MIT",
  "compatibility": {
    "minimum": "1.0.0-rc.1",
    "verified": "1.0.0-rc.1",
    "maximum": "1.x"
  },
  "capabilities": [
    "assets.scripts",
    "hooks.client",
    "assets.ui"
  ],
  "display": {
    "color": "#7c5cff"
  },
  "module": {
    "id": "my-module",
    "entrypoints": {
      "game": {
        "scripts": ["assets/my-module.js"]
      }
    }
  }
}
```

### Important rules

- Use `schemaVersion`, not `manifestVersion`.
- `type` must be `"module"`.
- `apiVersion` must be `"1"`.
- Top-level `id` and `module.id` must match.
- IDs use lowercase kebab-case: `my-module`.
- Assets must be declared under `module.entrypoints`.
- The backend only serves declared and validated files.
- Absolute paths, URLs, `..`, double slashes, and files outside the package are rejected.

## Entrypoints

Entrypoints tell Gravewright where module assets should load.

```json
{
  "module": {
    "entrypoints": {
      "game": {
        "styles": ["assets/game.css"],
        "scripts": ["assets/game.js"]
      },
      "inside": {
        "styles": ["assets/inside.css"],
        "scripts": ["assets/inside.js"]
      }
    }
  }
}
```

Currently accepted entrypoints:

| Entrypoint | Use |
|---|---|
| `game` | active table/campaign page |
| `inside` | internal management screens, when supported |

Current limits:

| Limit | Value |
|---|---:|
| CSS files per entrypoint | 16 |
| JS files per entrypoint | 16 |
| declared asset paths | 64 |
| maximum served asset size | 2 MB |
| maximum path length | 240 characters |
| CSS extensions | `.css` |
| JS extensions | `.js`, `.mjs` |

## Capabilities

Capabilities declare what the module intends to use. Privileged APIs require matching capabilities.

| Capability | Allows |
|---|---|
| `assets.ui` | UI interactions, scene/canvas helpers, and lightweight visual helpers |
| `assets.styles` | CSS loading |
| `assets.scripts` | JavaScript loading |
| `chat.cards` | sending chat messages/cards through the public API |
| `content.packs` | distributing content packs |
| `hooks.client` | registering client-side hooks |
| `locales` | providing translation files |
| `settings` | declaring and changing module settings |
| `sheets.extends` | sheet extension, reserved/experimental |
| `rules.extends` | rules extension, reserved/experimental |
| `tokens.extends` | interacting with tokens through the public API |

Forbidden capabilities are rejected:

```text
backend.execute
database.raw
filesystem.raw
network.raw
permissions.override
```

Declare only what you use. This makes auditing easier and reduces the risk surface.

## Basic runtime

Create `assets/my-module.js`:

```js
(function () {
  window.Gravewright.modules.register({
    id: "my-module",

    init(api, payload) {
      // Called during module runtime initialization.
      // Use this to register hooks and prepare local state.
      api.hooks.on("game:ready", ({ context }) => {
        api.ui.toast(`My Module loaded in ${context.campaign?.name || "campaign"}`);
      });
    },

    ready(api, payload) {
      // Called after game:ready for this module.
      const user = api.game.user();
      console.debug("My Module ready", { user });
    }
  });
})();
```

The runtime `id` must match the manifest `id`. If it does not match, the runtime cannot associate the loaded code with the validated manifest.

## Public module API

The runtime receives an `api` object scoped to the module:

```js
init(api, payload) {}
ready(api, payload) {}
```

Available namespaces:

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

Use the scoped `api` passed to your module. Do not call privileged root globals directly.

### `api.capabilities`

```js
api.capabilities.has("settings");
api.capabilities.require("settings", "my-feature");
api.capabilities.requirement("settings.get");
api.capabilities.list();
```

Use capabilities checks to fail early when a required capability was not declared in the manifest.

### `api.game`

```js
const context = api.game.context();
const campaign = api.game.campaign();
const scene = api.game.scene();
const user = api.game.user();
```

These methods return frozen copies of context data. Do not mutate the returned objects. The backend remains authoritative for game state.

### `api.hooks`

Requires `hooks.client`.

```js
const off = api.hooks.on("scene:loaded", ({ scene }) => {
  console.log("Scene loaded", scene);
});

api.hooks.once("game:ready", ({ context }) => {
  console.log("Ready", context);
});

off();
```

Current official hooks:

```text
module:init
module:ready
module:failed
game:ready
campaign:loaded
scene:loaded
```

You can inspect the official hook list:

```js
api.hooks.official();
```

### `api.ui`

Requires `assets.ui`.

```js
api.ui.toast("Hello from an extension", { duration: 4000 });
api.ui.openModal("my-modal-id");
api.ui.closeModal("my-modal-id");
```

Use UI APIs for lightweight interaction. Do not manipulate internal core DOM unless the documentation explicitly allows it.

### `api.tools`

Requires `assets.ui`.

```js
const activeTool = api.tools.activeTool();
```

### `api.scene`

Requires `assets.ui`.

```js
const canvas = api.scene.activeCanvas();
const camera = api.scene.activeCameraForScene(sceneId);
```

Use these carefully: canvas and camera APIs are UI helpers, not authoritative state sources.

### `api.tokens`

Requires `tokens.extends`.

```js
api.tokens.centerOn(tokenId);
```

### `api.chat`

Requires `chat.cards`.

```js
api.chat.send({
  type: "module-message",
  text: "Message sent by the module"
});
```

The API dispatches a client-side `vtt:chat-send` event. Core decides how that becomes a real message.

### `api.settings`

Requires `settings`.

```js
const definitions = api.settings.definitions();
const all = api.settings.all();
const color = api.settings.get("dice.color", "#7c5cff");
await api.settings.set("dice.color", "#ff006e");
```

`settings.set` sends to:

```text
POST /modules/settings
```

The payload includes `module_id`, `key`, `value`, and `campaign_id`.

## Declaring settings

In the manifest:

```json
{
  "capabilities": ["settings"],
  "module": {
    "id": "my-module",
    "settings": [
      {
        "key": "ui.enabled",
        "scope": "campaign",
        "type": "boolean",
        "default": true,
        "label": "Enable extra UI"
      },
      {
        "key": "dice.color",
        "scope": "user",
        "type": "string",
        "default": "#7c5cff",
        "label": "Dice color",
        "maxLength": 32
      },
      {
        "key": "automation.mode",
        "scope": "campaign",
        "type": "enum",
        "default": "assistive",
        "label": "Automation mode",
        "choices": [
          { "value": "off", "label": "Off" },
          { "value": "assistive", "label": "Assistive" },
          { "value": "strict", "label": "Strict" }
        ]
      }
    ]
  }
}
```

Accepted scopes:

| Scope | Meaning |
|---|---|
| `global` | installation-wide value |
| `campaign` | campaign-specific value |
| `user` | user-specific value |

Accepted types:

| Type | Expected value |
|---|---|
| `boolean` | `true`/`false` |
| `string` | text |
| `number` | number |
| `integer` | integer |
| `enum` | one of the declared choices |

Setting key rules:

- starts with a lowercase letter;
- uses lowercase letters, numbers, and `_`;
- may use dots for namespaces: `dice.color`, `ui.enabled`;
- maximum length: 96 characters.

## Dependencies, conflicts, and load order

```json
{
  "dependencies": ["base-rules"],
  "conflicts": [
    { "id": "alternate-rules" }
  ],
  "loadOrder": 10
}
```

Rules:

- dependencies must be installed, globally enabled, and campaign-enabled;
- a module cannot be enabled if it conflicts with an already-enabled module;
- conflicts are checked both ways;
- a module cannot be disabled while another enabled module depends on it;
- `loadOrder` must be between `-10000` and `10000`;
- dependencies load before dependents;
- after dependency ordering, modules load by `loadOrder`, name, and id.

Use dependencies for real contracts, not cosmetic ordering. For simple before/after behavior, prefer `loadOrder`.

## Content packs in modules

Modules can distribute optional content:

```json
{
  "capabilities": ["content.packs"],
  "module": {
    "contentPacks": [
      {
        "id": "extra-weapons",
        "type": "item_pack",
        "label": "Extra Weapons",
        "path": "content/items.extra-weapons.gwpack.json"
      }
    ]
  }
}
```

Accepted module pack types:

- `actor_pack`;
- `item_pack`;
- `spell_pack`;
- `journal_pack`.

The content must make sense for the active campaign system.

## System compatibility

Use `module.systems` when the module only works with specific systems:

```json
{
  "module": {
    "systems": {
      "dnd5e": {
        "minimum": "0.3.0",
        "verified": "0.3.0"
      }
    }
  }
}
```

During Alpha, treat system compatibility as operational documentation: clearly state which systems you tested with.

## Locales

```json
{
  "capabilities": ["locales"],
  "module": {
    "locales": {
      "en": "locales/en.json",
      "pt-BR": "locales/pt-BR.json"
    }
  }
}
```

## Full example: scene welcome toast

`manifest.json`:

```json
{
  "schemaVersion": 1,
  "type": "module",
  "id": "scene-welcome",
  "name": "Scene Welcome",
  "version": "0.1.0",
  "apiVersion": "1",
  "description": "Shows a toast when a scene is loaded.",
  "authors": [{ "name": "Your Name" }],
  "license": "MIT",
  "compatibility": {
    "minimum": "1.0.0-rc.1",
    "verified": "1.0.0-rc.1",
    "maximum": "1.x"
  },
  "capabilities": [
    "assets.scripts",
    "assets.ui",
    "hooks.client",
    "settings"
  ],
  "display": {
    "color": "#22c55e"
  },
  "module": {
    "id": "scene-welcome",
    "entrypoints": {
      "game": {
        "scripts": ["assets/scene-welcome.js"]
      }
    },
    "settings": [
      {
        "key": "toast.enabled",
        "scope": "user",
        "type": "boolean",
        "default": true,
        "label": "Show toast when a scene loads"
      }
    ]
  }
}
```

`assets/scene-welcome.js`:

```js
(function () {
  window.Gravewright.modules.register({
    id: "scene-welcome",

    init(api) {
      api.hooks.on("scene:loaded", ({ scene }) => {
        if (!api.settings.get("toast.enabled", true)) return;
        api.ui.toast(`Scene loaded: ${scene?.name || "unnamed"}`);
      });
    }
  });
})();
```

## ZIP packaging

Accepted layouts:

```text
scene-welcome.zip
  manifest.json
  assets/scene-welcome.js
```

or:

```text
scene-welcome.zip
  scene-welcome/
    manifest.json
    assets/scene-welcome.js
```

The upload process installs into staging before moving the package to `data/modules/<module-id>/`. The zip is treated as untrusted input.

Do not include:

- `.env`;
- SQLite databases;
- `storage/`;
- `node_modules/`;
- `__pycache__/`;
- `.pyc`;
- logs;
- real campaign data;
- unlicensed assets.

## Installing and enabling

Operational flow:

1. Install the module through the Inside Modules screen or upload endpoint.
2. Enable it globally.
3. Open the campaign.
4. Enable the module for that campaign.
5. Reload the table.

Management routes:

```text
POST /modules/upload
POST /modules/install
POST /modules/enable
POST /modules/disable
POST /modules/remove
POST /campaigns/modules/enable
POST /campaigns/modules/disable
POST /modules/settings
```

Campaign module management requires GM access.

## Validation checklist

Before distributing:

```bash
python3 -m json.tool data/modules/my-module/manifest.json > /dev/null
uv run pytest tests/unit/test_module_manifest.py tests/unit/test_module_install_service.py tests/unit/test_module_client_api.py
```

Verify also:

- `id` and `module.id` match;
- every declared path exists;
- every used privileged API has a matching capability;
- setting keys, scopes, types, defaults, and enum choices are valid;
- the module installs from zip;
- the module enables globally;
- the module enables for a campaign;
- the module appears in `window.Gravewright.modules.list()`;
- `init` and `ready` run without browser console errors;
- disabling the module does not break the campaign;
- the package contains no secrets, local databases, caches, logs, or real campaign data.

## Common errors

| Error | Likely cause | Fix |
|---|---|---|
| Manifest invalid | wrong `schemaVersion`, `type`, `apiVersion`, or compatibility fields | compare with the minimal manifest |
| Runtime does not register | JS `id` does not match manifest `id` | use the same id in both places |
| Asset does not load | path not declared, file missing, or capability missing | declare the asset and capability |
| Capability error | API used without matching capability | add the capability or remove the API usage |
| Setting does not save | missing `settings` capability or invalid key/type | declare `settings` and validate the setting definition |
| Hook never fires | wrong hook name or module failed during `init` | check official hook names and browser console |
| Module affects the wrong campaign | global enablement confused with campaign enablement | enable only in the target campaign |
| Upload rejected | zip contains unsafe paths or unsupported layout | use one of the accepted zip layouts |

## Distribution notes

For Alpha distribution, include a README in the module package with:

- supported Gravewright version;
- supported systems, if any;
- required capabilities;
- settings reference;
- install and enable instructions;
- known limitations;
- license and third-party asset attribution.
