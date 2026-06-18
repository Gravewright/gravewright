# SDK Data Layout — Universal Packages + Managed Storage

> Defines where packages and their persistent storage live on disk. The
> universal grouped layout `data/packages/{kind_plural}/{id}` is the only
> supported layout, frozen by Alpha 2.0.0 — SDK Freeze.

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

## Current layout (universal grouped)

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

## Backup / export UX

- **Full instance backup**: copy `data/` (includes packages and storage).
- **Package backup (with data)**: `data/packages/{kind_plural}/{id}/` +
  `data/storage/packages/{kind_plural}/{id}/`.
- **Package export/publish (no data)**: `data/packages/{kind_plural}/{id}/` only;
  storage is excluded by default.

CLI surface for this is defined in Phase 7B (`grave package backup|export`).

## Implementation status

Discovery reads only `data/packages/{kind_plural}/{id}`; directories outside a
kind root are not discovered. Kind-root binding is enforced: a package whose
`manifest.kind` disagrees with its `kind_plural` root fails with
`sdk.manifest.kind_root_mismatch`, and a `manifest.id` that differs from the
directory name fails with `sdk.manifest.id_mismatch`.
