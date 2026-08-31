# Manifest

`manifest.json` is the static security and composition boundary. The kernel reads and validates it before importing module code.

The machine-readable tooling schema is available at
[`docs/schema/manifest-v1.json`](../../schema/manifest-v1.json). Runtime
validation remains authoritative for semantic checks such as SemVer ranges.

```json
{
  "name": "dice-roller",
  "kind": "addon",
  "provider": "community",
  "version": "1.0.0",
  "entry": "./index.ts",
  "types": "./types.ts",
  "dependencies": {},
  "exports": { "get": ["read", "write", "stat", "roll"] }
}
```

It may also declare `routes`, `middleware`, `slots`, concrete `dependencies`,
capability `requires`/`provides`, and release download fields. A room additionally
declares `room_protocol: "gravewright.room/v1"` and canonical `exposes.slots`.
Entry and types paths must stay inside the module directory.

Do not hand-maintain generated fields. Use:

```bash
grave module build modules/dice-roller
grave module build modules/dice-roller --check
```

The manifest is not a sandbox: installed module code still executes with the host process permissions.

## Manifest with composition and release metadata

```json
{
  "name": "character-sheet",
  "kind": "system",
  "provider": "community",
  "version": "2.1.0",
  "entry": "./index.js",
  "types": "./types.d.ts",
  "dependencies": { "campaign-api": "^1.0.0" },
  "routes": { "/characters": "characters" },
  "middleware": { "/characters": ["authenticate"] },
  "slots": { "room.sidebar": ["sidebarPanel"] },
  "exports": { "get": ["read", "write", "stat", "characters", "authenticate", "sidebarPanel"] },
  "download_url": "https://example.org/releases/character-sheet-2.1.0.zip",
  "download_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
}
```

A release manifest is rejected if its ZIP hash differs, its archived name/version differs, or its entry escapes the package.
