# SDK Current State — Phase 0 Baseline

> Snapshot of the Gravewright SDK as it exists at the start of the stability
> sprint. This document is descriptive: it records *what is*, not *what should
> be*. The stability plan (`gravewright_sdk_stability_plan.md`) defines the
> target. Where current behaviour diverges from the target, this document flags
> it as **DRIFT** so later phases have a precise starting point.

Baseline test result: `pytest tests/unit -k sdk` → **103 passed** (793 deselected).

## 1. Package kinds

Defined in `app/engine/sdk/package_manifest.py` (`PackageKind`):

| kind | value |
|---|---|
| Ruleset | `ruleset` |
| Addon | `addon` |
| Library | `library` |
| Content | `content` |
| Theme | `theme` |
| Assets | `assets` |

All six kinds the plan requires already exist.

## 2. Package statuses

Defined in `app/engine/sdk/package_install_service.py`:

`available`, `installed`, `enabled`, `disabled`, `incompatible`, `error`.

Persisted statuses (`_PERSISTED`): `installed`, `enabled`, `disabled`.

Per-campaign activation is tracked separately in `campaign_packages.status`
(`active` / others) and the exclusive ruleset slot (`campaigns.active_system_id`).

## 3. Capabilities (backend vs frontend)

Two independent sources exist today — **there is no canonical file yet** (Phase 2
target: `app/engine/sdk/capabilities.json`).

### Backend — `KNOWN_CAPABILITIES` (`package_manifest_validator.py`)

```
actors.register, items.register, sheets.declarative, sheets.hooks,
sheets.components, rules.declarative, rules.extends, dice.roll, rolls.intent,
combat.config, combat.hooks, tokens.mappings, tokens.extends, scene.tools,
scene.overlays, chat.cards, content.packs, settings, locales,
assets.ui, assets.styles, assets.scripts, assets.pack, assets.images,
assets.audio, assets.maps, assets.icons, hooks.client, commands.register
```

### Backend — `FORBIDDEN_CAPABILITIES`

```
backend.execute, database.raw, filesystem.raw, network.raw, permissions.override
```

Matches the plan's forbidden set exactly.

### Frontend — `CAPABILITIES` (`static/js/sdk/sdk-capabilities.js`)

```
actors.register, items.register, sheets.declarative, sheets.hooks,
sheets.components, rules.declarative, rules.extends, dice.roll, rolls.intent,
combat.config, combat.hooks, tokens.mappings, tokens.extends, scene.tools,
scene.overlays, chat.cards, content.packs, settings, locales,
assets.ui, assets.styles, assets.scripts, hooks.client, commands.register
```

### DRIFT — capability set mismatch

The backend knows 5 capabilities the frontend does not:
`assets.pack`, `assets.images`, `assets.audio`, `assets.maps`, `assets.icons`.

These are *declaration-only* (asset packaging) capabilities with no frontend
method, which is why the JS map omits them — but nothing enforces that the two
lists stay in sync. Phase 2 makes `capabilities.json` canonical and Phase 11
adds a sync test.

### Frontend method → capability map (`CAPABILITY_REQUIREMENTS`)

Gated methods today: `hooks.on/once/emit`, `events.on/once`,
`commands.register`, `chat.send`, `ui.toast/openModal/closeModal`,
`settings.definitions/all/get/set`, `sheets.helpers/register`,
`combat.register/registerPanel/callHook/renderSlot`, `tokens.centerOn`,
`scene.activeCanvas/activeCameraForScene`, `tools.activeTool`,
`content.packs/pack`, `i18n.t`.

Ungated (intentionally public) scoped members: `version`, `package`, `kind`,
`capabilities.*`, `context()`, `game.*`.

## 4. Manifest public fields

Parsed by `PackageManifest.from_dict`:

`schemaVersion` (must be `1`), `sdkVersion` (must be `"1"`), `kind`, `id`,
`name`, `version`, `description`, `authors`, `license`, `homepage`,
`repository`, `compatibility{minimum,verified,maximum}`, `capabilities[]`,
`activation{scope,mode}`, `entrypoints{<name>{styles,scripts}}`,
`provides{storage,actorTypes,itemTypes,rules,mappings,contentPacks,locales,assets,areaMarkers}`,
`settings[]`, `distribution{type,url,sha256}`, `dependencies[]`, `conflicts[]`,
`display{color}`.

No `storage` (managed SQLite) or `interop` blocks exist yet (Phase 7A / Phase 12).

## 5. Error model — `error_key` strings

The SDK validator/loader return **string error keys**, not a structured
`SdkError`. Keys carry the prefix `sdk.validation.*`:

```
not_object, schema_version, sdk_version, kind, id_required, id_invalid,
name_required, version_required, authors_invalid, license_invalid,
compatibility_required, capabilities_required, capability_forbidden,
capability_unknown, activation_required, activation_invalid,
ruleset_activation_mode, ruleset_storage_required, ruleset_actor_types_required,
addon_activation_mode, library_activation_mode, assets_activation_mode,
assets_invalid_assets, assets_image_extension (warn), assets_map_extension (warn),
assets_audio_extension (warn), compatibility_prerelease (warn),
provides_key_unknown (warn), rules_shape_invalid, setting_invalid,
content_pack_invalid, entrypoint_invalid, path_unsafe, dependency_invalid,
conflict_invalid, distribution_invalid, incompatible (warn), manifest_missing,
manifest_unreadable, file_missing
```

### DRIFT — error contract

The plan (Phase 1) requires a structured `SdkError` / `SdkActionResult` /
`DoctorFinding` contract with stable `code` fields under namespaces
`sdk.manifest.*`, `sdk.capabilities.*`, `sdk.storage.*`, etc. Current keys live
under a single `sdk.validation.*` namespace and are bare strings.

### `error_key` usage across the app

`error_key` is widely used in the **action layer** (`app/actions/**`) as the
established UI/route contract — this is the legitimate "edge" use the plan
allows. SDK *services* do not yet emit a structured contract; they return the
`sdk.validation.*` strings above. Phase 1 introduces `SdkError`/`DoctorFinding`
for new/refactored services and keeps `error_key` only as a boundary adapter.

## 6. `manifest_json` as authority

`manifest_json` (the full manifest snapshot) is stored in `installed_packages`
and read back in several places:

```
app/engine/content/content_pack_service.py
app/engine/rules/rules_registry.py
app/engine/sdk/package_asset_service.py
app/engine/sdk/package_install_service.py
app/engine/sdk/package_locale_service.py
app/engine/sheets/schema_service.py
app/engine/sheets/system_layout_service.py
app/persistence/repositories/installed_package_repository.py
app/persistence/tables.py
```

### DRIFT — disk vs DB authority

The plan (Principle 7, Phase 6) requires **disk** to be the manifest authority;
the DB snapshot is for audit/hash only. Several services above read
`manifest_json` from the DB as the working manifest. Phase 6 audits and rewrites
these to load the current validated manifest from disk.

## 7. `installed_packages` schema

Columns (`app/persistence/tables.py`):

`id (pk)`, `kind`, `name`, `version`, `status`, `package_dir`, `manifest_json`,
`compatibility_status`, `validation_errors_json`, `package_sha256 (nullable)`,
`installed_by_user_id`, `installed_at`, `updated_at`, `enabled_at`, `disabled_at`.

### DRIFT — missing integrity fields

`package_sha256` exists. The plan (Phase 6) additionally requires
`manifest_hash`, `last_validated_at`, `last_validation_status`. These are
**absent** and must be added via Alembic migration.

## 8. Migrations infrastructure

Alembic (`migrations/versions/`). Latest revision: `0007_sdk_packages.py`.
`alembic.ini` present. The schema is also expressed in SQLAlchemy
`metadata`/`Table` definitions (`app/persistence/tables.py`). New columns require
both a migration and a `tables.py` update.

## 9. `sdk.hooks` usage

The frontend exposes `sdk.hooks.{on,once,emit}` and `sdk.events.{on,once}`,
all gated by the single `hooks.client` capability, backed by an in-process
listener `Map` in `gravewright-sdk.js`. There is no `sdk.bus.*` yet.

### DRIFT — hooks as interop

The plan marks `hooks.client` as `legacy_experimental` and `sdk.bus.*` as the
formal interop path (Phase 12). Today hooks are the only interop channel and are
documented in `docs/sdk/messaging.md` without a legacy/experimental marker.

## 10. Data layout

`app/engine/sdk/package_registry.py`: `PACKAGES_DIR = data_dir / "packages"`.
Packages are discovered from the configured package directory; this repository
does not ship bundled ruleset or addon packages in `data/packages`.

### DRIFT — universal layout

The plan requires `data/packages/{kind_plural}/{id}/` plus a parallel
`data/storage/packages/{kind_plural}/{id}/` tree. See `docs/sdk/data-layout.md`
for the current vs target layout and the migration path. No managed storage tree
exists yet.

## 11. Frontend runtime lifecycle (as built)

`window.GravewrightSDK` exposes only `version` and `register(definition)`.
`register` enforces: non-empty id, owning package script (nonce-validated or URL
match), id == script owner, active package, no duplicate. `setup` runs once per
package; `ready` runs once after `init` (DOMContentLoaded). A `GravewrightSDKDebug`
introspection object is exposed only when `context.debug === true`. This already
matches much of Phase 11's target; Phase 11 will add tests and capability-map
sync rather than rebuild it.
