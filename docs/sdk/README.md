# Gravewright SDK

The Gravewright SDK is the **only** supported way to extend Gravewright. Every installable thing — a ruleset, an addon, a shared library, a theme, importable content, or an asset library — is a **Gravewright package** described by a single manifest contract.

There is no separate "System API" or "Module API". Those were removed; do not look for them.

## Concepts

- **Package** — a directory under `data/packages/<package-id>/` with a `manifest.json` and the files it declares.
- **Kind** — what a package is: `ruleset`, `addon`, `library`, `content`, `theme`, or `assets`.
- **Capabilities** — explicit permissions a package declares; the engine and browser SDK gate behavior on them.
- **Activation** — a campaign has exactly one active `ruleset` and any number of active `addon`, `theme`, `assets`, and `content` packages. `library` packages are passive dependencies.
- **Trusted JavaScript** — packages with `assets.scripts` run trusted browser code for table users.

## Guides

- [`manifest.md`](manifest.md) — the package manifest contract (v1).
- [`kinds.md`](kinds.md) — the six package kinds and their rules.
- [`capabilities.md`](capabilities.md) — the capability allow-list and forbidden set.
- [`runtime.md`](runtime.md) — the `window.GravewrightSDK` browser runtime.
- [`messaging.md`](messaging.md) — package-to-package events, payload versioning, and dependency vs optional integration.
- [`cli.md`](cli.md) — the `grave` developer/operator CLI.
- [`creating-packages-with-ai.md`](creating-packages-with-ai.md) — package creation with the CLI + AI loop.
- [`security.md`](security.md) — path safety, upload rules, capability enforcement, and scripted package trust.

## Schema

Every manifest validates against:

```text
schemas/gravewright-package-v1.schema.json
```

## Bundled packages

- `data/packages/dnd5e/` — the D&D 5e ruleset.
- `data/packages/dice-so-nice-lite/` — a dice-animation addon.
