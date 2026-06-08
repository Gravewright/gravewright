# Gravewright Public APIs

This section documents the public integration surfaces for extension authors. API materials are licensed under MIT; core implementation remains Apache-2.0.

> [!WARNING]
> **Alpha API surface.** Gravewright is pre-1.0. Public APIs are documented so system, module, integration, and content-pack authors can experiment, but compatibility guarantees are still being finalized. Breaking API changes should update docs, schemas, and tests in the same change.

## API surfaces

| Document | Audience | Covers |
|---|---|---|
| [`extension-apis.md`](extension-apis.md) | module/system authors | browser globals, scoped module API, sheet hooks, combat hooks |
| [`http.md`](http.md) | integration authors | HTTP route groups and request conventions |
| [`realtime.md`](realtime.md) | realtime clients | `/game/ws`, commands, events, replay behavior |
| [`../modules.md`](../modules.md) | module authors | Module API v1 overview and quick start |
| [`../modules/creating-a-module.md`](../modules/creating-a-module.md) | module authors | complete module authoring guide: manifest, entrypoints, capabilities, hooks, settings, packaging |
| [`../systems/creating-a-system.md`](../systems/creating-a-system.md) | system authors | System API v1 package structure, manifest, schemas, sheets, rules |
| [`../systems/manifest.md`](../systems/manifest.md) | system authors | system manifest reference |

## Choosing the right extension type

| Need | Use |
|---|---|
| define actor/item types | system |
| define sheet schemas and layouts | system |
| define core roll actions and combat configuration | system |
| add optional UI behavior | module |
| add campaign-toggleable automation | module |
| add user/campaign settings | module |
| distribute optional content packs | module or system, depending on ownership |

Rule of thumb: if a campaign cannot function without it, it probably belongs in a system. If a GM should be able to enable/disable it per campaign, it should be a module.

## Stability expectations

During Alpha:

- manifests must declare `apiVersion: "1"`;
- packages should declare `compatibility.minimum`, `compatibility.verified`, and `compatibility.maximum`;
- extension authors should test against the exact Gravewright release they mark as `verified`;
- documented APIs are the only public contract;
- undocumented globals, DOM structure, and implementation details may change without migration support.

## API Material License

API materials are MIT-licensed to allow authors to copy API contracts, schemas, examples, manifest shapes, and starter package structures freely.
