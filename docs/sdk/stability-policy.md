# SDK Stability Policy

> Defines what "stable" means for the Gravewright SDK and how each public API is
> classified. This is the contract authors can rely on. Derived from
> `gravewright_sdk_stability_plan.md`.

## Guiding rule

> **Do not stabilize accidental behaviour. Stabilize only intentional contract.**

SDK 1 is currently at RC 1. The certified candidate requires a package valid for
`sdkVersion: "1"` to keep installing, enabling, and running across compatible
product releases unless it uses capabilities marked `forbidden`.

Package authors target the SDK identifier with `compatibility.minimum` and
`compatibility.verified` set to `"1"`. Product or RC labels such as
`1.0.0-beta.4` and `1.0.0-rc.1` do not belong in these SDK compatibility fields.

## Stability levels

| Status | Meaning |
|---|---|
| `stable` | Public API included in the frozen RC 1 candidate. It must not break within `sdkVersion: "1"`. |
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

## RC 1 enforcement

The semantic fingerprint is
`docs/sdk/_data/gravewright-sdk-1.rc1-snapshot.json`. CI regenerates the public
contract and rejects breaking drift. See
[`rc1-compatibility-policy.md`](rc1-compatibility-policy.md) and
[`rc1-certification.md`](rc1-certification.md); historical development gates
belong in release history, not in the current authoring contract.
