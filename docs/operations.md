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

### Request correlation

Every HTTP request is assigned a `request_id` (`RequestIdMiddleware`): an inbound
`X-Request-ID` is honored (sanitized) or one is generated, and it is echoed on
the response `X-Request-ID` header. The id is stored in a context variable and
attached automatically to every `emit_diagnostic`/audit event for that request —
including work offloaded via `run_blocking`. Correlate a user-reported failure to
server logs by its `X-Request-ID` without touching any payload.

### Redaction

`emit_diagnostic` redacts sensitive field values (`token`, `password`, `cookie`,
`csrf`, `authorization`, `api_key`, `session*`, `email`, …) to `[redacted]`
before anything reaches the ring buffer or the logs, so a careless caller cannot
leak secrets or PII. Raw redemption codes, tokens, cookies and `SESSION_SECRET`
must never be passed to diagnostics; they are hashed at rest regardless.

### Audit events

Security-relevant operations emit `audit.<action>` events via `emit_audit` with
`actor_id`, `result`, a `request_id`, internal ids and a timestamp — never a
secret. Current actions include `schema.mismatch`, `membership.created`,
`membership.removed` (extended incrementally to `login.blocked`,
`permission.changed`, `package.activated`).

### Log levels and retention

- Levels: `error` for blocked/failed security events (e.g. `schema.mismatch`),
  `warn` for degraded conditions (slow blocking calls, rate limiting), `info`
  for normal audit/diagnostic events.
- The in-process ring buffer keeps the most recent ~500 events for
  `/inside/diagnostics`; it is not durable. For retention, ship the structured
  JSON log lines to your log stack (recommend 30–90 days for audit events).
- Metrics available in-process (`realtime_metrics`): HTTP/DB/blocking-call
  latency, realtime queue depth, error and 429 rates, and migration failures.

## Campaign Deletion

Deleting a campaign removes campaign-owned database rows through cascades and explicit cleanup. It also deletes uploaded campaign storage for scenes, actor images, journal images, and package-scoped sheet JSON.

## Campaign-entry transition and rollback

Join codes are the primary campaign-entry flow. During the compatibility
release, `CAMPAIGN_EMAIL_INVITATION_CREATION_ENABLED=true` keeps the legacy
email CTA available and marked as legacy. Existing pending invitations may be
accepted or declined until their normal expiry; disabling new creation does not
cancel or delete them.

For rapid rollback, set `CAMPAIGN_JOIN_CODE_ENABLED=false` and restart the app.
This hides both join-code interfaces and returns 404 from join-code routes. It
does not delete codes, redemptions, memberships, email invitations, or schema.
Optionally revoke active codes before rollback. Do not drop
`campaign_invitations` in this release. A later release may disable legacy
creation by default, wait through the invitation expiry window, and only then
remove its UI/actions/schema in a dedicated migration after backup verification.

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
