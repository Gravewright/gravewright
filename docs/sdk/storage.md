# Managed Storage (`storage.sqlite`)

<<<<<<< HEAD
> **Status: stable in SDK 1.** A package declares the storage it needs;
> Gravewright owns the path, lifecycle, permissions, migrations, limits, and
> backup.
=======
> **Status: experimental.** Phase 7A defines and validates the storage
> *contract*; the runtime (query execution, endpoints, migrations) lands in
> Phase 7B. A package declares the storage it needs; Gravewright owns the path,
> lifecycle, permissions, and backup.
>>>>>>> origin/main

## Declaring storage

A package declares the `storage.sqlite` capability and a `storage.sqlite` block:

```json
{
  "capabilities": ["storage.sqlite"],
  "storage": {
    "sqlite": {
<<<<<<< HEAD
=======
      "status": "experimental",
>>>>>>> origin/main
      "location": "gravewright-managed",
      "scopes": ["campaign", "global"],
      "migrations": "storage/sqlite/migrations",
      "queries": "storage/sqlite/queries.json",
      "maxSizeMB": 50,
      "backup": true
    }
  }
}
```

- The capability and the block are mutually required (`sdk.storage.capability_missing`
  / `sdk.storage.declaration_invalid`).
- `scopes` must be a subset of `campaign`, `global`.
- `migrations` and `queries` must be safe, package-relative paths and exist on
  disk.

## Managed paths

Gravewright resolves storage paths from the validated `(kind, id, scope)` — a
package never receives an absolute path:

| Scope | Path |
|---|---|
| `global` | `data/storage/packages/{kind_plural}/{id}/global/data.sqlite3` |
| `campaign` | `data/storage/packages/{kind_plural}/{id}/campaigns/{campaign_id}/data.sqlite3` |

## Named queries

SQL lives in `queries.json` inside the package and is loaded **only** from the
validated package on disk. SQL or query definitions supplied by a client are
never accepted.

```json
{
  "queries": {
    "getState": {
      "type": "read",
      "params": { "key": "string" },
      "sql": "SELECT value_json FROM addon_state WHERE key = :key LIMIT 1"
    },
    "saveState": {
      "type": "write",
      "params": { "key": "string", "value_json": "json-string", "updated_at": "integer" },
      "sql": "INSERT INTO addon_state (key, value_json, updated_at) VALUES (:key, :value_json, :updated_at)"
    }
  }
}
```

Rules:

- Each query declares a `type` (`read` or `write`), a `params` whitelist, and a
  single `sql` statement.
- Parameter types: `string`, `integer`, `number`, `boolean`, `json`,
  `json-string`, `uuid`, `id`.
- A `read` statement must start with `SELECT`/`WITH`; a `write` with
  `INSERT`/`UPDATE`/`DELETE`.
- Multiple statements and `ATTACH`/`PRAGMA`/`VACUUM` are rejected
  (`sdk.storage.sqlite.query_sql_disallowed`).
<<<<<<< HEAD
- At runtime parameters are whitelisted per query: missing, extra, or
  wrong-typed parameters are rejected.

## Runtime

The managed storage runtime is available and capability-gated:
=======
- At runtime (Phase 7B) parameters are whitelisted per query: missing, extra, or
  wrong-typed parameters are rejected.

## What Phase 7A does not do

No endpoints, no query execution, no database files are created. The contract is
validated by the manifest validator (declaration) and the package loader
(migrations directory + `queries.json` on disk), and surfaced by the doctor.

## Runtime (Phase 7B)

The managed storage runtime is now available (experimental, capability-gated):
>>>>>>> origin/main

```ts
await sdk.storage.sqlite.execute("campaign", "saveState", {
  key: "panel-state",
  value_json: JSON.stringify(state),
});
const rows = await sdk.storage.sqlite.query("campaign", "getState", { key: "panel-state" });
const info = await sdk.storage.sqlite.status("campaign");
```

The backend (`POST /sdk/packages/{id}/storage/sqlite/{query|execute|status}`) is
the authority: it resolves the enabled package, checks the `storage.sqlite`
capability, validates the scope and the caller's permission, opens the managed
SQLite database, applies any pending migrations
(`gravewright_package_migrations`), loads the named query from disk, checks the
query type matches the operation, whitelists the parameters, and executes with
bound parameters. There is no `sdk.storage.sqlite.raw` and no path is ever
exposed.

<<<<<<< HEAD
Runtime limits:

- default max DB size: 50 MB, configurable via `maxSizeMB` (a positive number up
  to 1024; the manifest validator rejects invalid or out-of-range values with
  `sdk.storage.max_size_invalid` / `sdk.storage.max_size_too_large`);
- query timeout: 3000 ms;
- max rows returned: 1000;
- max result payload: 1 MB;
- SQLite busy timeout: 1000 ms.

=======
>>>>>>> origin/main
Backup/export: a package backup includes both `data/packages/{kind_plural}/{id}`
and `data/storage/packages/{kind_plural}/{id}`; an export/publish includes only
the package directory. The doctor reports storage directories whose package is
no longer installed (`sdk.storage.orphaned_storage`).
