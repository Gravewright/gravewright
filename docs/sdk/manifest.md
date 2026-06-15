# Package Manifest (SDK v1)

Every package ships a `manifest.json` that validates against
`schemas/gravewright-package-v1.schema.json`. The manifest **describes** a
package; it never executes anything.

## Minimal addon

```json
{
  "$schema": "https://raw.githubusercontent.com/Gravewright/gravewright/main/schemas/gravewright-package-v1.schema.json",
  "schemaVersion": 1,
  "sdkVersion": "1",
  "kind": "addon",
  "id": "my-package",
  "name": "My Package",
  "version": "0.1.0",
  "compatibility": { "minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1", "maximum": "1.x" },
  "capabilities": ["assets.scripts"],
  "activation": { "scope": "campaign", "mode": "multiple" },
  "entrypoints": { "game": { "scripts": ["assets/main.js"] } },
  "provides": {}
}
```

## Required top-level fields

`$schema`, `schemaVersion` (must be `1`), `sdkVersion` (must be `"1"`), `kind`,
`id`, `name`, `version`, `compatibility`, `capabilities`, `activation`,
`entrypoints`, `provides`.

## Optional fields

`description`, `authors`, `license`, `homepage`, `repository`, `distribution`,
`dependencies`, `conflicts`, `settings`.

## Field rules

- **`id`** — lowercase kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`). It must equal the
  package directory name.
- **`compatibility`** — at least one of `minimum` / `verified` / `maximum`. The
  engine computes a status (`compatible` / `unverified` / `incompatible`) against
  the running Gravewright version.
- **`activation.mode`** — `exclusive` (ruleset), `multiple` (addon/theme/assets),
  `passive` (library), or `none` (content).
- **`entrypoints.<name>`** — `{ "styles": [...], "scripts": [...] }`; paths are
  package-relative. The table loads the `game` entrypoint.
- **`provides`** — kind-specific data: `storage`, `actorTypes`, `itemTypes`,
  `rules`, `mappings`, `contentPacks`, `locales`, `assets`.

Every referenced path must be package-relative and safe (no `..`, no absolute
paths, no URLs); the loader verifies each path exists.

## Settings

```json
"settings": [
  { "key": "enabled", "scope": "user", "type": "boolean", "default": true, "label": "Enable" }
]
```

`scope` ∈ `global | campaign | user`; `type` ∈ `boolean | string | number | integer | enum`
(an `enum` must declare `options`).

## Distribution / dependencies / conflicts

```json
"distribution": { "type": "zip", "url": "https://example.com/pkg.zip", "sha256": "..." },
"dependencies": [ { "id": "some-library", "kind": "library", "minimum": "0.1.0" } ],
"conflicts": [ { "id": "other-theme", "reason": "Overrides the same UI surfaces." } ]
```

Allowed `distribution.type`: `zip`, `git`, `directory`.
