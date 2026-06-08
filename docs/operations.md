# Operations

## Backups

Back up both database and file storage.

Database:

- SQLite: back up `storage/gravewright.sqlite3` while the application is stopped or by using SQLite backup tooling.
- PostgreSQL: use `pg_dump` or managed database snapshots.

Files:

```text
storage/scenes/
storage/actor-assets/
storage/journal-assets/
storage/system-data/
data/systems/
data/modules/
```

If `GRAVEWRIGHT_DATA_DIR` points outside the repository, back up that directory too.

## Restore Order

1. Stop the application.
2. Restore the database.
3. Restore `storage/`.
4. Restore `GRAVEWRIGHT_DATA_DIR` or `data/`.
5. Run migrations.
6. Start the application.
7. Open `/inside/diagnostics` as an owner and confirm there are no startup errors.

## Diagnostics

Owner diagnostics are available at:

```text
GET /inside/diagnostics
```

Diagnostics expose in-memory counters, gauges, histograms, and scrubbed recent events for realtime, module lifecycle, content imports, map upload/retile, and blocking calls. They do not include raw cookies, passwords, session identifiers, or payload bodies.

## Logs

Runtime diagnostics emit structured events with stable identifiers such as:

```text
trace_id
command_id
room_id
campaign_id
scene_id
module_id
error_key
```

Use these identifiers to correlate WebSocket, upload, import, and persistence issues without logging private campaign content.

## Campaign Deletion

Deleting a campaign removes campaign-owned database rows through cascades and explicit cleanup. It also deletes uploaded campaign storage for scenes, actor images, journal images, and system-scoped sheet JSON.

## Module Operations

Module package replacement is blocked while the module is globally enabled or enabled in any campaign. Disable the module in every campaign, then globally disable it, then replace or remove it.

## System Operations

Systems are installed and enabled from the Inside Systems panel. A campaign can be assigned an enabled system. System assets are served only from validated package-relative paths.
