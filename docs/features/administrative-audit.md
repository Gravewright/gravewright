# Administrative audit history

Administrative history is an append-only, campaign-scoped record of critical
GM operations. Catalog version 1 covers join-code lifecycle, membership created
through codes, role-permission changes, package/ruleset activation, and campaign
snapshot lifecycle.

Each event stores internal actor and subject IDs, action, result, timestamp, and
metadata accepted by an event-specific allowlist. Arbitrary payloads are not
accepted. Passwords, tokens, cookies, sessions, e-mail addresses, IP addresses,
codes, and hashes are never part of the persistent metadata contract.

Only a campaign GM may list, filter, paginate, or export its history. JSON
exports contain at most 10,000 matching events and use `Cache-Control: no-store`.
The UI renders event values as text, never as server-provided HTML.

`ADMINISTRATIVE_AUDIT_ENABLED=false` disables recording and hides the routes/UI
without deleting existing events. `ADMINISTRATIVE_AUDIT_RETENTION_DAYS`
controls pruning; the default is 180 days.
