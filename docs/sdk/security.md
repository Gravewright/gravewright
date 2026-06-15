# Security

Packages are untrusted content. The SDK enforces several boundaries.

## Path safety

Every manifest-declared path and every archive entry must stay inside the
package directory. The loader/validator reject:

```
empty paths            absolute paths         URLs
backslashes            Windows drive prefixes ..  traversal
single-dot segments    double slashes         trailing slash on files
colons in segments     Windows device names   segments ending in space/dot
paths that resolve outside the package dir
```

See `app/engine/sdk/package_paths.py` (`package_id_is_safe`, `path_is_safe`,
`safe_join`).

## Capabilities

Capabilities are an allow-list; unknown capabilities are rejected and the
forbidden set (`backend.execute`, `database.raw`, `filesystem.raw`,
`network.raw`, `permissions.override`) is always rejected. There is no
server-side code execution in SDK v1.

Browser capability gates are a package-author contract and a defense-in-depth
check, not a JavaScript sandbox. A package that declares `assets.scripts` runs
trusted JavaScript in the same page as the table and can access browser globals
such as `window`, `document`, and `fetch`. Installing a scripted package means
trusting its author. Declarative packages without JavaScript remain the safe
package path.

Server routes still enforce package state, user role, and relevant capabilities
for mutable operations; client-side gates are never the only authorization
boundary. Concretely, every mutable package-scoped flow re-checks the capability
on the server, independent of the client SDK:

- `POST /sdk/packages/settings` requires the package to be enabled and to declare
  `settings` (`sdk.errors.capability_required`).
- `POST /sdk/packages/content/import` requires the package to be enabled and to
  declare `content.packs` (`sdk.errors.capability_required`).

Activation, install/enable/disable/remove are operator/GM actions gated by role
(see Authorization) rather than by package capability.

## Script ownership (per-package nonce)

Package scripts register with the runtime via `GravewrightSDK.register({ id })`.
To bind a `<script>` to the package it claims, the server tags each package
script with `data-gw-package` and a fresh per-render `data-gw-nonce`, and ships
the matching `{ id: nonce }` map in the game context (`packageNonces`). The SDK
honors a `register` call only when the registering script's declared id and nonce
match the server-issued pair; otherwise the registration is refused.

This makes the script→package binding explicit and testable instead of inferred
from `document.currentScript.src` alone, and prevents one package's code from
registering on behalf of another (or DOM-injected scripts from registering at
all). Nonces are per render, so they cannot be reused across page loads.

## Asset serving

The asset route only serves files the manifest **declares**, and only for an
enabled package, with a content-type whitelist. Anything else is a 404.

In v1 this is a **public, static** model: `GET /sdk/packages/<id>/asset/<path>`
serves any declared file of any *globally enabled* package to anyone, with no
campaign or membership check. This is correct for the current bundled packages,
whose assets (scripts, styles, sprites) are not secret — they ship with the open
package and are meant to load on every table that activates the package.

### Future: private / paid assets

If a package ever ships **private or paid** asset content, the public model is no
longer adequate and must change to **campaign-scoped asset serving**:

- authorize each asset request against the requesting user's membership of a
  specific campaign (and that the package is *active* in that campaign), not just
  "globally enabled";
- scope the asset URL to a campaign (e.g. `/sdk/campaigns/<campaign-id>/packages/<id>/asset/<path>`)
  so the server can enforce per-campaign access;
- treat the asset bytes as a protected resource (no public CDN caching, signed or
  expiring URLs as needed).

Until that requirement exists, keep assets public/declared/enabled — do not put
anything secret behind the current asset route.

## Upload (untrusted ZIP)

Package uploads remain untrusted. Reject non-zip files, too many entries,
oversized packages, absolute paths, `..` traversal, Windows drive prefixes,
backslashes, symlinks, `.env`, `storage/`, SQLite files, `__pycache__/`, `.pyc`,
logs, and `node_modules/`. The archive must contain `manifest.json` at the root
or `<package-id>/manifest.json`. Validate the manifest and every declared path
before promoting to `data/packages/<package-id>/`.

## Authorization

- Owner-only: install / enable / disable / remove / upload a package globally.
- GM-only (per campaign): set ruleset, activate/deactivate packages, change
  campaign-scoped settings, import package content.
- User scope: change user-scoped package settings.
