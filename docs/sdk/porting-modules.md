# Porting modules to Gravewright

This guide explains how to adapt a module originally built for another virtual
tabletop platform to Gravewright. **Original module** means the project used as a
reference, **source platform** means the environment it was built for, and **port**
means the new Gravewright SDK package.

A port is not a mechanical API rename. Platforms have different data, authority,
permission, lifecycle, and UI models. Preserve useful user-facing behavior while
reimplementing integration through Gravewright's public contracts.

> [!IMPORTANT]
> Use only code and materials you have the right to study, modify, and redistribute.
> This is technical guidance, not legal advice.

## 1. Introduction

Every Gravewright extension is an SDK package. Choose its [`kind`](kinds.md) by
what it does in Gravewright, not by what the source platform called it:

| Result | Likely kind |
|---|---|
| Optional behavior, UI, commands, or automation | `addon` |
| Base game rules | `ruleset` |
| Visual presentation | `theme` |
| Importable content | `content` |
| Reusable media | `assets` |
| Shared passive dependency | `library` |

Read the [declarative model](declarative-model.md), [quick start](quick-start.md),
and [capability power map](power-map.md) first.

## 2. Assess the module before starting

Record the exact repository, version, and commit; code and asset licenses; authors
and required notices; essential and optional features; dependencies; source APIs,
events, data, UI, and permissions; declarative candidates; browser-runtime needs;
private-internal dependencies; and performance, security, and multiplayer risks.

Classify the result as:

- **portable**: rights and public SDK support cover the main behavior;
- **portable with reduced scope**: some features or assets must be replaced or cut;
- **blocked by an SDK GAP**: an essential public operation is missing;
- **not redistributable**: rights do not permit the intended distribution.

Build a minimal public-SDK proof before porting the hardest code.

## 3. Licensing

Publicly visible source is not automatically reusable. Read the complete upstream
license, confirm modification and redistribution rights, identify attribution,
source-offer, notice, and change-marking duties, audit every dependency and asset,
choose a compatible license, and preserve required notices.

### Licenses that commonly allow ports

Gravewright does not enforce a closed license allow-list: manifest `license` accepts
a string. Use a precise [SPDX identifier](https://spdx.org/licenses/). Technical
acceptance does not establish legal compatibility.

| License | Manifest value | Main distribution duty |
|---|---|---|
| MIT | `MIT` | Preserve license text and copyright notices. |
| Apache License 2.0 | `Apache-2.0` | Preserve license/notices, mark changes, and follow its patent terms. |
| BSD 2-Clause | `BSD-2-Clause` | Preserve copyright, conditions, and disclaimer. |
| BSD 3-Clause | `BSD-3-Clause` | Same, plus no endorsement using contributor names. |
| Mozilla Public License 2.0 | `MPL-2.0` | Publish source for modified covered files under MPL. |
| GNU Lesser GPL 2.1 | `LGPL-2.1-only` or `LGPL-2.1-or-later` | Meet LGPL obligations for the covered library and its replacement/modification. |
| GNU Lesser GPL 3.0 | `LGPL-3.0-only` or `LGPL-3.0-or-later` | Meet LGPL obligations for the covered library. |
| GNU GPL 2.0 | `GPL-2.0-only` or `GPL-2.0-or-later` | Distribute covered derivatives compatibly and provide corresponding source. |
| GNU GPL 3.0 | `GPL-3.0-only` or `GPL-3.0-or-later` | Distribute covered derivatives compatibly and provide corresponding source. |
| GNU Affero GPL 3.0 | `AGPL-3.0-only` or `AGPL-3.0-or-later` | Meet GPL duties and offer corresponding source to network users of a modified version. |
| Unlicense | `Unlicense` | Preserve applicable text and verify suitability in your jurisdiction. |

The 3D dice port derives from GNU Affero GPL 3.0 code. Its exact SPDX value must be
`AGPL-3.0-only` or `AGPL-3.0-or-later`, according to the upstream grant. “GNU” alone
is not a license: GPL, LGPL, AGPL, `only`, and `or-later` have different effects.

Common non-code licenses include `CC0-1.0`, `CC-BY-4.0`, `CC-BY-SA-4.0`, and
`OFL-1.1`. Use Creative Commons licenses for content/assets rather than software
code. `CC-BY-NC-*` restricts commercial use. `CC-BY-ND-*` does not allow distribution
of adaptations and therefore cannot cover a modified asset.

Do not redistribute material with no license, `All Rights Reserved`, personal-use
only terms, a ban on derivatives, purchase-only access without redistribution
permission, or terms incompatible with the release. Source access is not permission.

### Declaring the license

Use exact SPDX identifiers or expressions:

```json
{ "license": "MIT" }
```

```json
{ "license": "AGPL-3.0-only" }
```

Use `OR` only for a genuine alternative licensing choice:

```json
{ "license": "MIT OR Apache-2.0" }
```

Use `AND` only when the same work is genuinely subject to every named license at the
same time. Do not use it to summarize independent files under different licenses.
Declare the main code license in the manifest and map third-party code, fonts, and
assets individually in `THIRD_PARTY_NOTICES.md`, without implying relicensing. Put
the main license text in `LICENSE`; retain required file headers; record project,
version, commit, and upstream license in `UPSTREAM.md`; and explain coverage in
`README.md`. Provide corresponding source whenever copyleft terms require it.

Recommended provenance layout:

```text
my-port/
├── LICENSE
├── README.md
├── THIRD_PARTY_NOTICES.md
└── UPSTREAM.md
```

## 4. Intellectual property and assets

A code license does not automatically cover trademarks, names, artwork, 3D models,
maps, text, game publications, audio, or fonts. Inventory each item with its source,
author, license/permission, modifications, and destination. Avoid implying upstream
affiliation; replace ambiguous assets; keep attribution with the package; and never
include campaign data, credentials, databases, or personal files.

## 5. Define the port scope

Break the module into observable features rather than files. Mark each feature as
**port**, **reimplement**, **replace**, or **exclude**, with a reason and Gravewright
implementation. Explicitly document what version one does not support. A smaller,
honest, tested port is better than an incomplete copy.

## 6. Map the architecture

| Required concept | Gravewright contract |
|---|---|
| Lifecycle | `window.GravewrightSDK.register` |
| Metadata and compatibility | `manifest.json` |
| API permission | `capabilities` |
| Current table data | `sdk.context()` and `sdk.game.*` |
| Package events | `sdk.bus.*` |
| Chat and rolls | `sdk.chat.*` and public DTOs |
| Configuration | declared settings and `sdk.settings.*` |
| Sheets/combat | `sdk.sheets.*` / `sdk.combat.*` |
| Scenes/tokens | `sdk.scene.*`, `sdk.tokens.*`, `sdk.tools.*` |
| UI and localization | documented `sdk.ui.*` slots and `sdk.i18n.*` |
| Content/media | declared packs and package-relative paths |

Verify every mapping in the [SDK reference](reference.md). Anything without a
documented method, event, DTO, capability, or slot is private.

For every multiplayer action, define initiator, validating/persisting authority,
audience, local/shared/durable state, and reconnect/concurrency behavior. Never use
private DOM, HTTP, raw WebSocket, database, filesystem, or renderer internals to
bypass authority. See [authority](authority-model.md) and [security](security.md).

## 7. Package structure

Create the appropriate scaffold:

```bash
grave addon new my-port --name "My Port" --js --settings
```

A typical package contains `manifest.json`, `README.md`, license/provenance files,
and only the required `src/`, `scripts/`, `styles/`, `assets/`, and `locales/` files.
Declare only used capabilities and entrypoints; prefer declarative SDK features.

```js
window.GravewrightSDK.register({
  id: "my-port",
  setup(sdk) {
    // Register listeners, commands, and integrations.
  },
  ready(sdk) {
    // Mount behavior that requires a ready game or DOM.
  },
});
```

Keep initialization idempotent and teardown complete. Pin incorporated libraries,
retain their notices, remove source-platform adapters, document reproducible builds,
and never ship `node_modules`, caches, secrets, or unnecessary development files.

## 8. Implement through the SDK

Build vertical slices: registration; public input/event; conversion to the port's
internal model; minimal visible effect; permissions/multiplayer; settings; a11y and
errors; teardown. Keep an explicit boundary:

```text
public event/DTO → port adapter → independent engine → package UI/effect
```

Pass only required public fields to reused code and handle optional fields, missing
features, and versions safely.

## 9. Use AI to automate the port

AI can inventory dependencies, produce adapters, convert formats, generate tests,
and explain diagnostics. It cannot grant rights or justify bypassing the SDK.

Give it the approved scope, licensed inputs, relevant public SDK docs, architecture
map, validation commands, and a package-only editing boundary. Require it not to
invent capabilities/events/DTOs/slots, access private internals, or include unlicensed
assets. Ask for small patches with APIs, provenance, behavior changes, tests, and
remaining risks.

```text
Edit only data/packages/addons/my-port.
Use only documented Gravewright SDK 1 APIs.
Do not invent capabilities or access private DOM, database, filesystem, network,
WebSocket, stores, or browser globals.
Preserve provenance and licenses. Add GM/player tests.
After each patch run:
grave package validate data/packages/addons/my-port
grave package doctor my-port
```

Never upload `.env`, databases, saves, private campaigns, credentials, or commercial
packages to an external AI service. See [Creating packages with AI](creating-packages-with-ai.md).

## 10. Validate, test, and debug

```bash
grave package validate data/packages/addons/my-port
grave package doctor my-port
```

Test install/activation/deactivation, reload, simultaneous GM and players,
visibility/permissions, resource lifecycle, sync/reconnect/duplicate events,
concurrency, old and new campaigns, setting persistence, dependency states, teardown,
realistic performance, accessibility, and safe failures. Unit-test deterministic
adapters and use real-browser E2E tests for lifecycle, UI, authority, and multiplayer.
Install and test the final artifact in a clean environment.

## 11. Report an SDK GAP

An SDK GAP exists when a legitimate, general behavior cannot be composed from public
APIs—not merely because the source API looked different. Search the power map,
reference, and DTOs; try public composition; reduce the blocker to a minimal package;
check authority/privacy; and describe the need without prescribing copied internals.

Include: goal-oriented title, use case, expected behavior and audience, evaluated
public APIs and why they fail, minimal reproduction, exact restriction, smallest
general capability proposed, authority/security analysis, and alternatives. Do not
ship against internals while waiting; reduce scope or keep the feature experimental.

## 12. Document authorship and changes

The port README must explain behavior, reused/reimplemented/excluded parts,
non-affiliation where relevant, installation, capabilities and reasons, SDK
compatibility, reproducible build, limitations, license, and links to `UPSTREAM.md`
and `THIRD_PARTY_NOTICES.md`. Keep a changelog that distinguishes port fixes,
upstream syncs, and SDK-required changes.

## 13. Publish

Validate and test everything; install the clean artifact; verify manifest, versions,
dependencies, rights, and asset inventory; publish its SHA-256 and release notes;
choose `dev`, `testing`, or `stable`; and submit the channel manifest according to
the [Marketplace guide](marketplace.md).

Exclude secrets, databases, campaign content, development dependencies, caches,
unlicensed material, unnecessary source-project copies, and unused source-platform
files.

## 14. Maintain the port

Pin the upstream version for every release. For updates, compare against the recorded
commit, classify only in-scope changes, update the independent engine without
overwriting the Gravewright adapter, refresh notices/inventory, rerun multiplayer and
clean-artifact tests, and document permanent divergence. Contract-test the adapter.

## 15. Final checklist

- [ ] Every included code/asset license permits modification and redistribution.
- [ ] `LICENSE`, `UPSTREAM.md`, and `THIRD_PARTY_NOTICES.md` are complete.
- [ ] Ported, replaced, and excluded scope is documented.
- [ ] Every integration is public SDK and every capability is justified.
- [ ] Authority, visibility, durability, reconnect, and concurrency are defined.
- [ ] `grave package validate` and `grave package doctor` pass.
- [ ] Adapters have unit tests and applicable GM/player flows have E2E tests.
- [ ] Teardown, missing dependencies, accessibility, and performance were tested.
- [ ] The final artifact installs cleanly and contains only required files.
- [ ] Manifest, compatibility, channel, hash, README, and release notes are correct.
- [ ] Upstream updates have a documented, non-destructive maintenance process.
