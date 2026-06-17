# SDK Data Layout — Universal Packages + Managed Storage

<<<<<<< HEAD
> Defines where packages and their persistent storage live on disk. The
> universal grouped layout `data/packages/{kind_plural}/{id}` is the only
> supported layout, frozen by Alpha 2.0.0 — SDK Freeze.
=======
> Defines where packages and their persistent storage live on disk. Records the
> **current** flat layout, the **target** universal layout from the stability
> plan, and the migration path between them.
>>>>>>> origin/main

## Architectural rule

> Everything is a package. A package lives in
> `data/packages/{kind_plural}/{id}`. Its storage lives in
> `data/storage/packages/{kind_plural}/{id}`.

`kind_plural` mapping:

| `manifest.kind` | `kind_plural` |
|---|---|
| `addon` | `addons` |
| `ruleset` | `rulesets` |
| `library` | `libraries` |
| `theme` | `themes` |
| `content` | `content` |
| `assets` | `assets` |

> Note: `content` and `assets` are already plural-as-written; their directory
> equals the kind.

<<<<<<< HEAD
## Current layout (universal grouped)
=======
## Current layout (Phase 0)

Defined by `app/engine/sdk/package_registry.py`
(`PACKAGES_DIR = data_dir / "packages"`). Packages are **flat**, keyed only by
id; there is no kind grouping and no managed storage tree.

```text
data/
  packages/
    dnd5e/                # ruleset, flat
      manifest.json
    dice-so-nice-lite/    # addon, flat
      manifest.json
  inside/                 # unrelated existing data
```

## Target layout
>>>>>>> origin/main

```text
data/
  packages/
    addons/{id}/
    rulesets/{id}/
    libraries/{id}/
    themes/{id}/
    content/{id}/
    assets/{id}/

  storage/
    packages/
      addons/{id}/
        global/data.sqlite3
        campaigns/{campaign_id}/data.sqlite3
      rulesets/{id}/
        ...
      (libraries|themes|content|assets)/{id}/

  .gravewright/
    instance.json
    schema-version
    locks/

  backups/
```

### Path mapping

| `manifest.kind` | Package directory | Storage directory |
|---|---|---|
| `addon` | `data/packages/addons/{id}` | `data/storage/packages/addons/{id}` |
| `ruleset` | `data/packages/rulesets/{id}` | `data/storage/packages/rulesets/{id}` |
| `library` | `data/packages/libraries/{id}` | `data/storage/packages/libraries/{id}` |
| `theme` | `data/packages/themes/{id}` | `data/storage/packages/themes/{id}` |
| `content` | `data/packages/content/{id}` | `data/storage/packages/content/{id}` |
| `assets` | `data/packages/assets/{id}` | `data/storage/packages/assets/{id}` |

### Storage scopes (Phase 7A/7B)

| Scope | Path |
|---|---|
| `global` | `data/storage/packages/{kind_plural}/{id}/global/data.sqlite3` |
| `campaign` | `data/storage/packages/{kind_plural}/{id}/campaigns/{campaign_id}/data.sqlite3` |

<<<<<<< HEAD
=======
## Migration path (current → target)

The flat→grouped move is a real migration handled in Phase 5
(manifest identity + kind-root binding). The plan, since the project is in
Alpha, prefers failing early over preserving an accidental layout:

1. **Resolve kind → directory** centrally (a single helper consumed by registry,
   loader, asset service, install service, storage service).
2. **Move on-disk packages** from `data/packages/{id}` to
   `data/packages/{kind_plural}/{id}` based on the validated `manifest.kind`.
   For the two existing packages: `dnd5e` (ruleset) →
   `data/packages/rulesets/dnd5e`; `dice-so-nice-lite` (addon) →
   `data/packages/addons/dice-so-nice-lite`.
3. **Update `installed_packages.package_dir`** to the new path (covered by the
   integrity work in Phase 6).
4. **Enforce kind-root binding**: a package under `addons/` whose manifest says
   `kind: "ruleset"` fails with `sdk.manifest.kind_root_mismatch`; a manifest
   `id` that differs from the directory name fails with
   `sdk.manifest.id_mismatch`.

Until Phase 5 lands, discovery continues to read the flat layout. This document
is the contract the migration implements against.

>>>>>>> origin/main
## Backup / export UX

- **Full instance backup**: copy `data/` (includes packages and storage).
- **Package backup (with data)**: `data/packages/{kind_plural}/{id}/` +
  `data/storage/packages/{kind_plural}/{id}/`.
- **Package export/publish (no data)**: `data/packages/{kind_plural}/{id}/` only;
  storage is excluded by default.

CLI surface for this is defined in Phase 7B (`grave package backup|export`).

<<<<<<< HEAD
## Implementation status

Discovery reads only `data/packages/{kind_plural}/{id}`; directories outside a
kind root are not discovered. Kind-root binding is enforced: a package whose
=======
## Implementation status (Phase 5)

The grouped layout is **live**: discovery reads
`data/packages/{kind_plural}/{id}` and the bundled packages have moved
(`rulesets/dnd5e`, `addons/dice-so-nice-lite`). The legacy flat
`data/packages/{id}` layout is still discovered as a **fallback** so existing
installs keep working; the doctor reports flat packages (`package_flat_layout`)
so they can be migrated. Kind-root binding is enforced: a package whose
>>>>>>> origin/main
`manifest.kind` disagrees with its `kind_plural` root fails with
`sdk.manifest.kind_root_mismatch`, and a `manifest.id` that differs from the
directory name fails with `sdk.manifest.id_mismatch`.
