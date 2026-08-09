# Campaign export

Campaign export creates a portable `.gwcampaign` ZIP package for a campaign GM.
The GM selects packages, scenes, actors, items, journals, and role-level settings.
The format is explicitly versioned as `gravewright.campaign-export` version 1.

Each package contains exactly:

- `manifest.json`, with format version, selected scopes, row counts, explicit
  exclusions, and the expected SHA-256 and byte size for the payload;
- `campaign.json`, with the allowlisted logical campaign content.

The generated archive is reopened and validated before it is returned. The same
validation contract checks structure, version, size, checksum, and forbidden keys
and is intended to be reused by a future importer before any database write.

## Security boundary

The exporter is allowlist-based. It never reads account, membership, invitation,
join-code, session, password-reset, streamer-link, presence, chat, audit, ownership,
handout, lobby, or per-user permission tables. Physical assets and package settings
are excluded because their files or arbitrary configuration may contain secrets.

Authorship and ownership columns are removed. JSON-valued columns are parsed and
recursively scrubbed of email, password, token, secret, cookie, session, CSRF, code
hash, and user/owner/creator identifiers before being serialized again.

Set `CAMPAIGN_EXPORT_ENABLED=false` and restart for operational rollback. This
hides the UI and makes `POST /campaigns/export` return 404. Successful exports are
recorded as `campaign.exported` in the administrative audit without storing package
contents or filenames.
