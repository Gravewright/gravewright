# Campaign snapshots

Campaign snapshots are GM-only logical recovery points. Format version 1 stores
a canonical JSON payload and SHA-256 checksum for campaign state, scene state,
fog, board markers, and scene-layer metadata.

Restore is conservative: only campaign state and matching scene/layer IDs are
updated. Scenes created after the snapshot remain untouched. Missing scenes are
reported by preview and are not recreated because doing so without their
physical assets would produce incomplete data.

Before every restore, Gravewright creates an automatic safety snapshot inside
the same database transaction. A checksum or format mismatch aborts the entire
operation. Restore and deletion require explicit text confirmation.

Members, invitations, join codes, chat, presence, actors, items, journals,
tokens, tiles, uploaded assets, and physical files are outside the MVP scope and
are never modified by restore.

`CAMPAIGN_SNAPSHOTS_ENABLED=false` hides the UI and disables all snapshot
routes. `CAMPAIGN_SNAPSHOT_RETENTION` limits retained manual and safety
snapshots per campaign; the oldest records are removed after successful
creation. Disabling the feature does not delete existing snapshots.
