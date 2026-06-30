# SDK Stability Policy

> Defines what "stable" means for the Gravewright SDK and how each public API is
> classified. This is the contract authors can rely on. Derived from
> `gravewright_sdk_stability_plan.md`.

## Guiding rule

> **Do not stabilize accidental behaviour. Stabilize only intentional contract.**

The SDK is considered stable when a package valid for `sdkVersion: "1"` keeps
installing, enabling, and running across `1.x` releases — unless it uses
capabilities marked `forbidden`.

Package authors should target the final SDK line with `compatibility.minimum`
and `compatibility.verified` set to `"1"`; pre-release values such as
`1.0.0-rc.1` are historical and validate as unverified against SDK 1 final.

## Stability levels

| Status | Meaning |
|---|---|
| `stable` | Public API. Must not break within `sdkVersion: "1"`. |
| `forbidden` | Capability the SDK refuses (unsafe surface). |

## Classification of current/planned surfaces

| Surface | Status | Notes |
|---|---|---|
| `manifest` v1 fields (kind, id, name, version, compatibility, capabilities, activation, entrypoints, provides, settings, dependencies, conflicts) | `stable` (frozen at beta) | The public package contract. |
| `settings.*` | `stable` | Coercion rules tightened in Phase 4. |
| `content.*` | `stable` | |
| `i18n.*` | `stable` | |
| Frontend lifecycle (`GravewrightSDK.register`, `setup`, `ready`) | `stable` | Hardened/tested in Phase 11. |
| `storage.sqlite` (`sdk.storage.sqlite.*`) | `stable` | Managed package SQLite storage with named queries and Gravewright-owned paths. |
| `sdk.bus.*` (`bus.publish/subscribe/request/provide`) | `stable` | The package-to-package communication contract. |
| `sheets.html` / `sheets.controller` / `sheets.richText` | `stable` | HTML template/controller sheet contract. |

## Policy requirements

1. Every public API has a status (`stable` or `forbidden`). No public API may be
   statusless.
2. The doctor errors on unknown or forbidden capabilities.
3. Breaking changes to the manifest contract require a new `sdkVersion` or a
   formal migration.
4. Capabilities are declared in the canonical `capabilities.json`; every public,
   gated method maps to a capability there.

## Release gates (summary)

> Historical: these were the internal stability-sprint gates. Their contents
> shipped together as **Gravewright Alpha 2.0.0 — SDK Freeze** (`v2.0.0-alpha.0`),
> which froze the SDK 1 surface. The version names below are the sprint plan's,
> not the released tag.

| Release | Theme |
|---|---|
| `v1.0.0-alpha.2` | Foundations: diagnostics contract, capability registry, semver, settings, manifest identity, integrity migration, documented universal layout. |
| `v1.0.0-alpha.3` | Storage contract (Phase 7A), reverse dependencies, strict doctor, v1 fixtures. |
| `v1.0.0-alpha.4` | Storage runtime (Phase 7B), frontend lifecycle + capability sync. |
| `v1.0.0-alpha.5` | `sdk.bus.*` interop hardening. |
| `v1.0.0-beta.1` | Freeze: manifest v1 frozen, compatibility policy published. |
| `v1.0.0-rc.1` | Bugfixes/docs/tests only. |

See the plan's "Fase 14 — Release gates" for the full per-gate contents.
