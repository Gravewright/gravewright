# SDK Diagnostics Contract

> The common, machine-readable format every SDK service speaks for errors,
> findings, and action results. Defined in `app/engine/sdk/diagnostics.py`
> (Phase 1 of the stability plan).

## Why

Bare `error_key` strings are fine at the *edges* (routes, templates, CLI) but a
weak internal contract: they mix namespaces, are easy to typo, and tempt tests
to assert on human text. The diagnostics contract is the **internal** format.

> SDK services return `SdkError` / `SdkActionResult` / `DoctorFinding`. At the
> HTTP boundary the structured `code` is also surfaced as `error_key`.

## Types

### `SdkError`

```python
SdkError(
    code: str,                       # stable, machine-readable
    message: str = "",               # human-readable; never asserted on
    details: dict[str, Any] = {},
    package_id: str | None = None,
    campaign_id: str | None = None,
)
```

### `SdkActionResult`

```python
SdkActionResult(
    success: bool,
    package_id: str | None = None,
    campaign_id: str | None = None,
    error: SdkError | None = None,
    warnings: tuple[SdkError, ...] = (),
)
```

Construct with `SdkActionResult.ok(...)` / `SdkActionResult.fail(error)`.

### `DoctorFinding`

```python
DoctorFinding(
    code: str,
    severity: Literal["error", "warning", "info"],
    message: str = "",
    details: dict[str, Any] = {},
    package_id: str | None = None,
    campaign_id: str | None = None,
)
```

All three expose `to_dict()` for the UI/CLI; optional fields are *omitted* (not
null) when absent.

## Code convention

A code is a lowercase, dot-separated identifier whose first segment is `sdk`,
matching `^sdk(\.[a-z0-9]+(_[a-z0-9]+)*)+$`. Public namespaces:

```text
sdk.manifest.*        sdk.compatibility.*   sdk.capabilities.*
sdk.paths.*           sdk.dependencies.*    sdk.conflicts.*
sdk.settings.*        sdk.assets.*          sdk.content.*
sdk.locale.*          sdk.frontend.*        sdk.interop.*
sdk.persistence.*     sdk.storage.*
```

Initial catalogue (see `SDK_ERROR_CODES`), e.g.:

```text
sdk.manifest.id_mismatch
sdk.manifest.kind_root_mismatch
sdk.capabilities.unknown
sdk.capabilities.forbidden
sdk.paths.unsafe
sdk.dependencies.active_dependents
sdk.settings.invalid_value
sdk.persistence.manifest_hash_mismatch
sdk.storage.sqlite.query_missing
```

Tests assert on `code` and `details`, **never** on `message`.

## HTTP boundary

SDK endpoints return the structured `code`. At the HTTP boundary the same value
is mirrored into the `error_key` field so the route/template/CLI layer has a
single stable error string; there is no separate error vocabulary or mapping.

## Adoption status

Phase 1 establishes the contract, the catalogue, the adapter, and these tests.
Later phases emit these codes as they touch each service: compatibility
(Phase 3), manifest identity (Phase 5), persistence integrity (Phase 6), storage
(Phase 7), reverse dependencies (Phase 8). The strict doctor (Phase 9) migrates
`PackageDoctorService` onto the canonical `DoctorFinding`; until then it keeps
its existing finding dicts.

## Doctor finding codes

`grave doctor` emits package findings whose `code` field is **frozen and
Alpha-stable** as of Alpha 2.0.0 — tooling and tests may match on them. The
current set mixes two naming styles for historical reasons:

Namespaced (`sdk.<area>.<detail>`):

```text
sdk.manifest.snapshot_stale
sdk.persistence.manifest_hash_mismatch
sdk.storage.orphaned_storage
sdk.storage.sqlite.database_unreadable
sdk.storage.sqlite.migration_dirty
sdk.storage.sqlite.migration_hash_mismatch
sdk.doctor.audit_error
```

Un-namespaced (retained as-is for compatibility):

```text
active_but_disabled          active_but_not_installed
capability_unknown           capability_forbidden
enabled_but_incompatible     enabled_but_invalid
package_missing_on_disk      orphan_content_import
orphan_setting_undeclared    orphan_setting_uninstalled
setting_value_corrupted      bus.provider_conflict
bus.provider_not_found
```

Full normalization onto the `sdk.<area>.<detail>` convention (e.g.
`sdk.dependency.missing`, `sdk.capability.unknown`,
`sdk.bus.provider_conflict`) is **post-freeze** work toward LTS 1. When it lands,
the un-namespaced codes will be kept as documented aliases so existing tooling
does not break; the freeze does not rename them.
