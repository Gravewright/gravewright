# Gravewright Public APIs

This section documents the public integration surfaces for extension authors.

API materials are licensed under MIT. The core implementation remains Apache-2.0.

> [!WARNING]
> **Alpha API surface.**
>
> Gravewright is pre-1.0. Public APIs are documented so system, module, integration, and content-pack authors can experiment, but compatibility guarantees are still being finalized.
>
> Breaking API changes should update docs, schemas, and tests in the same change.

## API Surfaces

| Document | Audience | Covers |
|---|---|---|
| [`extension-apis.md`](extension-apis.md) | Module and system authors | Browser globals, scoped module APIs, sheet hooks, sheet labels, combat hooks, and combat slots |
| [`http.md`](http.md) | Integration authors | HTTP route groups and request conventions |
| [`realtime.md`](realtime.md) | Realtime clients | `/game/ws`, commands, events, and replay behavior |
| [`../modules.md`](../modules.md) | Module authors | Module API v1 overview and quick start |
| [`../modules/creating-a-module.md`](../modules/creating-a-module.md) | Module authors | Manifest structure, entrypoints, capabilities, hooks, settings, packaging, and validation |
| [`../systems/creating-a-system.md`](../systems/creating-a-system.md) | System authors | System API v1 package structure, manifest, schemas, sheets, rules, labels, assets, and combat configuration |
| [`../systems/manifest.md`](../systems/manifest.md) | System authors | System manifest reference |

## Choosing the Right Extension Type

| Need | Use |
|---|---|
| Define actor types | System |
| Define item types | System |
| Define sheet schemas and layouts | System |
| Define core roll actions and combat configuration | System |
| Provide ruleset vocabulary, labels, and locale files | System |
| Add optional UI behavior | Module |
| Add campaign-toggleable automation | Module |
| Add user or campaign settings | Module |
| Distribute optional content packs | Module or system, depending on ownership |

Rule of thumb: if a campaign cannot function without it, it probably belongs in a system.

If a GM should be able to enable or disable it per campaign, it should be a module.

## Stability Expectations

During Alpha:

- manifests must declare `apiVersion: "1"`;
- packages should declare `compatibility.minimum`, `compatibility.verified`, and `compatibility.maximum`;
- extension authors should test against the exact Gravewright release they mark as `verified`;
- documented APIs are the only public contract;
- undocumented globals, DOM structure, renderer internals, fallback behavior, private stores, and implementation details may change without migration support;
- public API changes should be reflected in docs and tests in the same change.

## Public vs Private API

Public APIs are documented in this directory and related system/module guides.

The following are not public contracts unless explicitly documented:

- internal JavaScript globals;
- renderer-local state;
- private stores;
- DOM structure;
- CSS class names not documented as extension hooks;
- fallback labels;
- full sheet renderer replacement;
- full combat renderer replacement;
- internal WebSocket event shapes not documented under `api/realtime.md`.

Systems and modules should use documented APIs, declarative manifests, schemas, rules, hooks, slots, labels, locales, and assets instead of relying on implementation details.

## API Material License

API materials are MIT-licensed to allow authors to copy API contracts, schemas, examples, manifest shapes, and starter package structures freely.