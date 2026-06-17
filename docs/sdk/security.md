# SDK security model

The SDK is designed around declarative package manifests, explicit capabilities, safe file references, scoped browser runtimes, and server-authoritative game state.

## Security goals

- Make extension intent visible before install/activation.
- Keep package capabilities explicit and reviewable.
- Prevent package path traversal.
- Avoid backend plugin execution in SDK v1.
- Avoid raw database, filesystem, network, and permission override access.
- Keep browser package APIs scoped to the owning package.
- Treat the server as authoritative for persistence, permissions, and game state.

## Capabilities are explicit

Every package declares requested capabilities in `manifest.json`.

```json
"capabilities": ["assets.scripts", "settings"]
```

The engine rejects unknown and forbidden capabilities. The browser runtime gates SDK methods according to declared capabilities.

## Forbidden capabilities

The following are always rejected:

```text
backend.execute
database.raw
filesystem.raw
network.raw
permissions.override
```

SDK v1 does not support backend-executed package code.

## Trusted browser JavaScript

Packages that declare `assets.scripts` run trusted browser code for table users.

Review packages with `assets.scripts` carefully:

- confirm the package source;
- review requested capabilities;
- inspect package scripts;
- prefer declarative manifests when possible;
- install only packages appropriate for the table.

The CLI warns when installing packages that run trusted JavaScript.

## Script ownership

The runtime verifies that a package script can register only its own manifest id. Registration is refused when:

- the script is not associated with a package;
- the claimed id differs from the script package id;
- the package is inactive;
- the package already registered.

This prevents one package script from registering as another active package.

## Path safety

Manifest-referenced paths must be package-relative and safe.

Invalid:

```text
../secret.txt
/etc/passwd
https://example.com/script.js
C:\Users\file.txt
```

Valid:

```text
assets/main.js
assets/theme.css
schemas/character.schema.json
content/items.gwpack.json
locales/en.json
```

The loader verifies referenced paths and rejects unsafe paths.

## Public vs private browser surfaces

Public:

- `window.GravewrightSDK.register(...)`
- scoped `sdk.*` object passed to package lifecycle functions
- documented package events
- documented sheet/combat runtime plugins through `sdk.sheets` and `sdk.combat`

Private unless explicitly documented:

- renderer globals;
- private stores;
- DOM structure;
- internal WebSocket event ordering;
- internal CSS class names;
- fallback labels;
- full sheet renderer replacement;
- full combat renderer replacement;
- `window.GravewrightSDKDebug` in production.

## Server authority

Browser packages can improve UI, submit intentions, and react to state. They must not treat browser-local state as authoritative.

Package authors should assume:

- permissions are enforced server-side;
- game state changes must go through documented routes/commands/intents;
- local UI state can be stale;
- WebSocket messages can be delayed, replayed, or rejected;
- other packages may be absent or inactive.

## Operator checklist

Before installing a package:

- Run `grave package validate <package>`.
- Review `capabilities`.
- Check whether `assets.scripts` is present.
- Check `dependencies` and `conflicts`.
- Review package source and license.
- Back up important campaigns.

Before updating packages:

```bash
grave backup -o gravewright-backup.zip --include-assets --include-packages --verify
grave lock -o grave.lock.json
```

## Package author checklist

- Use the smallest capability set.
- Keep files inside the package directory.
- Avoid private globals and DOM internals.
- Namespace events by package id.
- Version cross-package event payloads.
- Treat missing optional peer packages as normal.
- Do not store secrets in package settings.
- Document every capability request.
