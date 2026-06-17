# Content and assets

SDK packages can provide importable content and reusable media through manifest `provides` fields.

## Content packs

Content packs are declared under `provides.contentPacks`.

```json
"provides": {
  "contentPacks": [
    {
      "id": "my-rpg-weapons",
      "type": "item_pack",
      "label": "Weapons",
      "labelKey": "my-rpg.content.weapons",
      "path": "content/items.weapons.gwpack.json"
    }
  ]
}
```

Allowed content pack types:

- `actor_pack`
- `item_pack`
- `spell_pack`
- `journal_pack`
- `table_pack`
- `condition_pack`

Each content pack needs:

- stable `id`;
- valid `type`;
- `label` or `labelKey` for display;
- safe package-relative `path`.

## Reading content packs at runtime

Declare the `content.packs` capability:

```json
"capabilities": ["content.packs"]
```

Read pack summaries:

```js
const packs = await sdk.content.packs();
```

Read a specific pack:

```js
const pack = await sdk.content.pack("my-rpg-weapons");
```

## Assets packages

Asset packages use `kind: "assets"` and provide media under `provides.assets`.

```json
{
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "assets",
  "id": "my-assets",
  "name": "My Assets",
  "version": "0.1.0",
  "compatibility": {
    "verified": "1.0.0-rc.1"
  },
  "capabilities": ["assets.pack", "assets.images", "assets.maps", "assets.icons"],
  "activation": {
    "scope": "campaign",
    "mode": "multiple"
  },
  "entrypoints": {},
  "provides": {
    "assets": {
      "images": [
        { "id": "logo", "label": "Logo", "path": "images/logo.webp" }
      ],
      "maps": [
        { "id": "dungeon", "label": "Dungeon", "path": "maps/dungeon.webp" }
      ],
      "icons": [
        { "id": "sword", "label": "Sword", "path": "icons/sword.svg" }
      ]
    }
  }
}
```

## Asset entry fields

| Field | Required | Description |
|---|---:|---|
| `id` | Yes | Stable asset id unique inside the category. |
| `label` | Yes | Human-readable label. |
| `path` | Yes | Safe package-relative path. |

## Path safety

All manifest-referenced paths must be safe:

- no `..` path traversal;
- no absolute paths;
- no URLs;
- package-relative only;
- path must exist inside the package directory.

Unsafe paths are rejected with `sdk.validation.path_unsafe` or an asset-specific validation error.

## Extension warnings

The validator warns when common asset categories use unexpected extensions.

Expected image extensions:

```text
.png .jpg .jpeg .webp .svg
```

Expected map extensions:

```text
.png .jpg .jpeg .webp
```

Expected audio extensions:

```text
.mp3 .ogg .wav
```

## Assets package restrictions

An `assets` package must not declare game/data model fields such as:

- `provides.storage`
- `provides.actorTypes`
- `provides.itemTypes`
- `provides.rules`

Use `ruleset` for game models and `content` for importable content.
