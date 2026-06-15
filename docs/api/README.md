# Gravewright Public APIs

This section documents the public integration surfaces for SDK package authors.

API materials are licensed under MIT. The core implementation remains Apache-2.0.

> [!WARNING]
> **Alpha API surface.**
>
> Gravewright is pre-1.0. Public APIs are documented so package authors can
> experiment, but compatibility guarantees are still being finalized.
>
> Breaking API changes should update docs, schemas, and tests in the same change.

## API Surfaces

| Document | Audience | Covers |
|---|---|---|
| [`http.md`](http.md) | Integration authors | HTTP route groups and request conventions |
| [`realtime.md`](realtime.md) | Realtime clients | `/game/ws`, commands, events, and replay behavior |
| [`../sdk/README.md`](../sdk/README.md) | Package authors | The Gravewright SDK — the only extension model |
| [`../sdk/manifest.md`](../sdk/manifest.md) | Package authors | Package manifest (v1) reference |
| [`../sdk/runtime.md`](../sdk/runtime.md) | Package authors | `window.GravewrightSDK` browser runtime |

## Choosing the Right Package Kind

| Need | Kind |
|---|---|
| Define actor/item types, sheets, rules, combat | `ruleset` |
| Provide ruleset vocabulary, labels, locale files | `ruleset` |
| Add optional UI behavior / automation per campaign | `addon` |
| Add a visual theme | `theme` |
| Provide reusable media (tokens, maps, audio) | `assets` |
| Distribute importable content packs | `content` |
| Share passive code/styles between packages | `library` |

Rule of thumb: if a campaign cannot function without it, it belongs in a
`ruleset`. If a GM should enable/disable it per campaign, it is an `addon`,
`theme`, `assets`, or `content` package. See [`../sdk/kinds.md`](../sdk/kinds.md).

## Stability Expectations

During Alpha:

- manifests must declare `schemaVersion: 1` and `sdkVersion: "1"`;
- packages should declare `compatibility.minimum`, `compatibility.verified`, and `compatibility.maximum`;
- package authors should test against the exact Gravewright release they mark as `verified`;
- documented APIs are the only public contract;
- undocumented globals, DOM structure, renderer internals, fallback behavior, private stores, and implementation details may change without migration support.

## Public vs Private API

Public APIs are documented in this directory and the SDK guides. The following
are not public contracts unless explicitly documented: internal JavaScript
globals, renderer-local state, private stores, DOM structure, undocumented CSS
class names, fallback labels, and internal WebSocket event shapes not documented
under `api/realtime.md`.

Packages should use the documented SDK: declarative manifests, schemas, rules,
hooks, slots, labels, locales, assets, and `window.GravewrightSDK`.

## API Material License

API materials are MIT-licensed to allow authors to copy API contracts, schemas,
examples, manifest shapes, and starter package structures freely.
