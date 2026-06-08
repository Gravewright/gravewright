# Module API v1

Modules are optional Gravewright extensions. They can add UI assets, client-side hooks, settings, content packs, and lightweight integrations without changing the core application and without replacing the active game system.

> [!WARNING]
> **Alpha API.** Module API v1 is available for public experimentation, but breaking changes may still happen between Alpha releases.

## Start here

- [Creating a Module](modules/creating-a-module.md) — complete guide for manifest structure, entrypoints, capabilities, hooks, settings, packaging, and validation.
- [Extension APIs](api/extension-apis.md) — browser-facing APIs exposed to modules and system UI extensions.
- [System API v1](systems/creating-a-system.md) — use this when you need to define actor types, item types, sheets, schemas, and rules.

## System or module?

| Use case | Create |
|---|---|
| Define actor types, item types, schemas, sheets, roll actions, combat rules | System |
| Add optional UI, toasts, themes, hooks, settings, or content packs | Module |
| Extend a specific system without replacing it | Module |
| Create a new ruleset or game implementation | System |

## Quick start

A module is installed under:

```text
<GRAVEWRIGHT_DATA_DIR>/modules/<module-id>/manifest.json
```

It has two activation levels:

1. **Global install/enablement**: an owner makes the package available.
2. **Campaign enablement**: a GM chooses which globally-enabled modules load for a campaign.

This prevents a globally installed module from affecting every table automatically.

## Minimal package

```text
data/modules/my-module/
  manifest.json
  assets/my-module.js
```

Minimal manifest:

```json
{
  "schemaVersion": 1,
  "type": "module",
  "id": "my-module",
  "name": "My Module",
  "version": "0.1.0",
  "apiVersion": "1",
  "description": "Example Gravewright module.",
  "authors": [{ "name": "Your Name" }],
  "license": "MIT",
  "compatibility": {
    "minimum": "1.0.0-rc.1",
    "verified": "1.0.0-rc.1",
    "maximum": "1.x"
  },
  "capabilities": ["assets.scripts", "hooks.client", "assets.ui"],
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

Runtime registration:

```js
(function () {
  window.Gravewright.modules.register({
    id: "my-module",

    init(api) {
      api.hooks.on("game:ready", ({ context }) => {
        api.ui.toast(`My Module loaded in ${context.campaign?.name || "campaign"}`);
      });
    }
  });
})();
```

For the full guide, continue with [Creating a Module](modules/creating-a-module.md).
