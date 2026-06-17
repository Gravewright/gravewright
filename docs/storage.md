# Storage

Gravewright uses database rows for metadata and local file storage for uploaded or package data.

## Runtime Storage Root

Default:

```text
storage/
```

For SQLite, package-scoped sheet data is colocated with the active database path. For external databases, storage remains under the configured local storage root.

## Scene Storage

Uploaded maps create scene asset files and chunk files under:

```text
storage/scenes/<scene_id>/
```

Typical subdirectories:

```text
assets/original/
assets/tiles/<layer_id>/
chunks/<layer_id>/
```

Scene metadata is stored in database tables such as `scenes`, `scene_layers`, `scene_assets`, `scene_tiles`, and `scene_chunks`.

## Actor Asset Storage

Actor portrait and token images are stored under:

```text
storage/actor-assets/<campaign_id>/<actor_id>/
```

The actor row stores the current asset path.

## Journal Asset Storage

Journal images are stored under:

```text
storage/journal-assets/<campaign_id>/
```

The `journal_assets` table stores asset metadata and storage paths.

## Package Sheet Data

Ruleset-scoped actor and item sheet JSON is currently stored under:

```text
storage/system-data/<system_id>/campaigns/<campaign_id>/actors/<actor_id>.json
storage/system-data/<system_id>/campaigns/<campaign_id>/items/<item_id>.json
```

`system_id` is the current internal storage column/name for the active ruleset package id. Paths are derived from validated IDs and confined to the storage root.

## Package Data

Default:

```text
data/packages/
```

Override with:

```env
GRAVEWRIGHT_DATA_DIR=/var/lib/gravewright/data
```

## Cleanup

Campaign deletion deletes campaign database rows and campaign-owned storage. Scene deletion removes scene rows and scene storage. Package removal removes database installation state but does not automatically delete package directories from disk.
