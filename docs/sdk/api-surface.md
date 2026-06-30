# SDK API Surface

> The complete public surface of the Gravewright SDK, split by layer, each entry
> carrying a stability status (see `stability-policy.md`). This is the list the
> plan's Phase 0 requires: "no public API without a status".

Layers: **manifest** (the on-disk package contract), **backend** (Python
services/validation), **frontend** (`window.GravewrightSDK` + the scoped `sdk`),
**persistence** (DB-backed install registry), **storage** (managed SQLite),
**interop** (`sdk.bus.*`), and **HTML sheets**.

## Frontend — global entry point

| API | Status | Notes |
|---|---|---|
| `window.GravewrightSDK.version` | `stable` | Returns `"1"`. |
| `window.GravewrightSDK.register(definition)` | `stable` | `{ id, setup, ready }`; ownership + nonce enforced. Returns `false` on rejection. |
| `window.GravewrightSDKDebug.*` | `internal` | Only present when `context.debug === true`. |

## Frontend — scoped `sdk` (delivered to each package)

| Member | Capability | Status |
|---|---|---|
| `sdk.version` | — (public) | `stable` |
| `sdk.package` | — (public) | `stable` |
| `sdk.kind` | — (public) | `stable` |
| `sdk.capabilities.has/require/list` | — (public) | `stable` |
| `sdk.context()` | — (public) | `stable` |
| `sdk.game.context/campaign/scene/user/ready` | — (public) | `stable` |
| `sdk.settings.definitions/all/get/set` | `settings` | `stable` |
| `sdk.content.packs/pack` | `content.packs` | `stable` |
| `sdk.i18n.t` | `locales` | `stable` |
| `sdk.commands.register` | `commands.register` | `stable` |
| `sdk.chat.send` | `chat.cards` | `stable` |
| `sdk.dice.roll` | `dice.roll` | `stable` |
| `sdk.rolls.intent` | `rolls.intent` | `stable` |
| `sdk.ui.toast/openModal/closeModal` | `assets.ui` | `stable` |
| `sdk.sheets.helpers/register` | `sheets.runtime` | `stable` |
| `sdk.combat.register/registerPanel/dispatch/renderSlot` | `combat.runtime` | `stable` |
| `sdk.tokens.centerOn` | `tokens.extends` | `stable` |
| `sdk.scene.activeCanvas/activeCameraForScene` | `scene.tools` | `stable` |
| `sdk.tools.activeTool` | `scene.tools` | `stable` |
| `sdk.storage.sqlite.query/execute/status` | `storage.sqlite` | `stable` |
| `sdk.bus.publish/subscribe/request/provide` | `bus.*` | `stable` |
| `sdk.sheets.registerController` | `sheets.controller` | `stable` |

Ergonomic shortcuts (`sdk.toast`, `sdk.setting`) delegate
to the namespaces above and inherit their status.

## Manifest — public fields

| Field | Status |
|---|---|
| `schemaVersion` (=1), `sdkVersion` (="1") | `stable` |
| `kind`, `id`, `name`, `version`, `description` | `stable` |
| `authors`, `license`, `homepage`, `repository` | `stable` |
| `compatibility{minimum,verified,maximum}` | `stable` |
| `capabilities[]` | `stable` |
| `activation{scope,mode}` | `stable` |
| `entrypoints{<name>{styles,scripts}}` | `stable` |
| `provides{storage,actorTypes,itemTypes,rules,mappings,contentPacks,locales,assets,areaMarkers}` | `stable` |
| `settings[]` | `stable` |
| `dependencies[]`, `conflicts[]` | `stable` |
| `distribution{type,url,sha256}` | `stable` |
| `display{color}` | `stable` |
| `storage.sqlite{...}` | `stable` |
| `interop{emits,listens,provides,requires}` | `stable` |
| `provides.*.sheet{mode:"html",...}` | `stable` |

## Backend — services / validation

| Symbol | Status | Notes |
|---|---|---|
| `validate_manifest(raw)` → `PackageManifestValidation` | `stable` | Error keys move to `SdkError` codes in Phase 1. |
| `PackageManifest` / `PackageKind` | `stable` | |
| `compute_compatibility_status(...)` | `stable` | SemVer hardening in Phase 3. |
| `package_id_is_safe` / `path_is_safe` / `safe_join` | `stable` | Path-safety single source of truth. |
| `load_package` / `package_registry.*` | `stable` | Kind-root binding added in Phase 5. |
| `PackageInstallService` / `PackageActivationService` | `stable` | |
| `PackageSettingsService` | `stable` | |
| `PackageDependencyService` | `stable` | Reverse-dependency guards in Phase 8. |
| `PackageDoctorService` / `DoctorFinding` | `stable` | Unified finding contract in Phase 1; strict checks in Phase 9. |
| `PackageAssetService` / `PackageContentService` / `PackageLocaleService` | `stable` | |
| `SdkError` / `SdkActionResult` | planned | Phase 1 diagnostics contract. |
| Managed storage service | `stable` | Named query runtime. |
| `sdk.bus` backend/doctor checks | `stable` | Interop declaration checks. |

## Persistence

| Table | Status |
|---|---|
| `installed_packages` | `stable` (integrity fields added in Phase 6) |
| `campaign_packages` | `stable` |
| `package_settings` | `stable` |
| `package_content_imports` | `stable` |

## Closed by the Alpha 2.0.0 SDK Freeze

The gaps tracked during SDK 1 development are now closed and part of the frozen
surface:

- A canonical `capabilities.json` is the single source of truth for backend and
  frontend capability sets (no drift).
- Disk is the runtime authority for manifests; the stored `manifest_json`
  snapshot is only a fallback when a package is gone from disk.
- The universal grouped layout `data/packages/{kind_plural}/{id}` is current, with
  managed package storage under `data/storage/packages/{kind_plural}/{id}`.

Remaining hardening (validation error model, broader schema validation for
`sdk.bus`) is post-freeze work toward LTS 1 and does not change the frozen SDK 1
surface.

See `stability-policy.md` for the level definitions.
