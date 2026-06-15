# Operations

## Operator CLI

Use the `grave` CLI for local operation:

```bash
grave doctor
grave run --open
grave backup -o gravewright-backup.zip --include-assets --verify
grave restore gravewright-backup.zip --dry-run
grave package list
grave lock -o grave.lock.json
```

Fallback:

```bash
uv run python -m app.cli doctor
```

## Backups

Before updating Gravewright or changing packages, create a backup.

SQLite/local:

```bash
grave backup -o gravewright-backup.zip --include-assets --verify
```

For local/custom packages, create a self-contained backup when supported:

```bash
grave backup -o gravewright-backup.zip --include-assets --include-packages --verify
```

PostgreSQL production deployments should use `pg_dump` or managed database snapshots in addition to file storage backups.

Back up:

- database;
- `storage/`;
- `GRAVEWRIGHT_DATA_DIR` or `data/packages/`;
- deployment `.env` or secret manager values;
- local/custom packages that cannot be re-downloaded.

## Restore

Test first:

```bash
grave restore gravewright-backup.zip --dry-run
```

Restore requires confirmation:

```bash
grave restore gravewright-backup.zip --yes
```

Recommended order:

1. Stop the application.
2. Restore the database.
3. Restore `storage/`.
4. Restore `GRAVEWRIGHT_DATA_DIR` or `data/packages/`.
5. Run `grave doctor`.
6. Start the application.
7. Open `/inside/diagnostics` as an owner and confirm there are no startup errors.

## Diagnostics

CLI diagnostics:

```bash
grave doctor
grave doctor --json
grave doctor --ai
```

Owner diagnostics are available at:

```text
GET /inside/diagnostics
```

Diagnostics expose in-memory counters, gauges, histograms, and scrubbed recent events for realtime, SDK package lifecycle, content imports, map upload/retile, and blocking calls. They do not include raw cookies, passwords, session identifiers, or payload bodies.

## Logs

Runtime diagnostics emit structured events with stable identifiers such as:

```text
trace_id
command_id
room_id
campaign_id
scene_id
package_id
error_key
```

Use these identifiers to correlate WebSocket, upload, import, package, and persistence issues without logging private campaign content.

## Campaign Deletion

Deleting a campaign removes campaign-owned database rows through cascades and explicit cleanup. It also deletes uploaded campaign storage for scenes, actor images, journal images, and package-scoped sheet JSON.

## Package Operations

Package replacement is blocked while the package is globally enabled or active in any campaign. Deactivate the package in every campaign, globally disable it, then replace or remove it.

Useful commands:

```bash
grave package list
grave package doctor <package_id>
grave package disable <package_id>
grave package remove <package_id>
grave campaign package list <campaign_id>
grave campaign package deactivate <campaign_id> <package_id>
```

## Ruleset Operations

Rulesets are SDK packages with `kind: "ruleset"`. A campaign can have one active ruleset. Package assets are served only from validated package-relative paths declared by the manifest.
