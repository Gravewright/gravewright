# Gravewright Public APIs

This section documents public integration surfaces for Gravewright.

The supported extension surface is the Gravewright SDK package model. Rulesets, addons, libraries, themes, content packs, and asset packs are all SDK packages described by `manifest.json` and validated against SDK v1.

> [!WARNING]
> Gravewright is Alpha software. Public APIs are documented so package authors can experiment, but compatibility guarantees are still being finalized. Breaking public API changes must update docs, schemas, and tests in the same change.

## API surfaces

| Document | Audience | Covers |
|---|---|---|
| [`../sdk/README.md`](../sdk/README.md) | Package authors | SDK overview and package author entry point |
| [`../sdk/manifest.md`](../sdk/manifest.md) | Package authors and tooling authors | Manifest contract, required fields, optional fields, and `provides` structure |
| [`../sdk/runtime.md`](../sdk/runtime.md) | Browser package authors | `window.GravewrightSDK`, lifecycle, scoped `sdk`, plugins, UI, chat, settings, sheets, combat, scene, tokens, content, and i18n |
| [`../sdk/reference.md`](../sdk/reference.md) | Runtime package authors | Complete browser SDK namespace and method reference |
| [`../sdk/capabilities.md`](../sdk/capabilities.md) | Package authors and reviewers | Capability allow-list, forbidden capabilities, and method gates |
| [`../sdk/security.md`](../sdk/security.md) | Package authors and operators | Path safety, trusted JavaScript, capability enforcement, and private API boundaries |
| [`http.md`](http.md) | Integration authors | HTTP route groups and request conventions |
| [`realtime.md`](realtime.md) | Realtime clients | `/game/ws`, commands, events, and replay behavior |

## Choosing the right package kind

| Need | Use |
|---|---|
| Define the campaign's base rules, actor types, item types, sheets, rules, mappings, and combat behavior | `ruleset` |
| Add optional campaign behavior, UI, plugins, settings, scene tools, chat cards, or runtime behavior | `addon` |
| Share passive code, metadata, styles, locales, or reusable building blocks between other packages | `library` |
| Ship visual styles and UI assets | `theme` |
| Ship importable content without runtime behavior | `content` |
| Ship reusable media such as images, maps, icons, audio, and portraits | `assets` |

A campaign has exactly one active `ruleset`. A campaign can activate multiple `addon`, `theme`, `content`, and `assets` packages. `library` packages are passive dependencies.

## Public vs private API

The public browser entry point for packages is `window.GravewrightSDK.register(...)`. The package receives a scoped `sdk` object. Internal globals, private stores, renderer state, unlisted DOM structure, undocumented CSS class names, and backend internals are not public contracts.

Package code must prefer:

- declarative manifests;
- declared capabilities;
- `sdk.*` namespaces;
- documented sheet and combat runtime plugin registration;
- content packs, asset packs, settings, locales, and events.

Package code must not rely on:

- scoped `api.*` from the removed module model;
- undocumented renderer globals;
- direct database access;
- backend execution;
- raw filesystem or network access;
- permission overrides.

## Stability expectations

During Alpha:

- manifests must declare `schemaVersion: 1` and `sdkVersion: "1"`;
- packages should declare `compatibility.minimum`, `compatibility.verified`, and `compatibility.maximum`;
- package authors should test against the exact Gravewright release they mark as `verified`;
- documented APIs are the only public contract;
- breaking API changes should update docs, schemas, example packages, and tests in the same change.

## API material license

API materials are MIT-licensed to allow authors to copy API contracts, manifest shapes, schemas, examples, and starter package structures. The Gravewright core implementation remains Apache-2.0.
