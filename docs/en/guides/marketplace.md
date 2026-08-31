# Marketplace publishing and installation

The marketplace is a `system` module, not a special kernel subsystem. The
included implementation serves `/marketplace` through the active server and
reads the official catalog from the Gravewright marketplace repository.

## Discovery model

A catalog contains metadata and stable `manifest_url` values. Gravewright does
not depend on a Git hosting brand: GitHub, GitLab, GitBucket, a CDN, or a plain
HTTPS server work when they expose the same documents.

```text
catalog ──► stable manifest URL ──► immutable release ZIP
                                      └── SHA-256 in manifest
```

The stable manifest can be updated to point at the newest release. Installation
uses the version and ZIP referenced by that manifest; it never clones or installs
the repository's `main` branch.

## Publish a module

1. Build a release ZIP with `manifest.json` at its root or inside one top-level directory.
2. Publish the ZIP as an immutable release asset.
3. Compute its SHA-256 digest.
4. Publish a stable HTTPS JSON manifest containing `download_url` and `download_sha256`.
5. Open an issue in the marketplace repository requesting catalog inclusion.

When publishing a new version, upload a new immutable ZIP and then update the
stable manifest and catalog metadata. Never replace bytes behind an existing
version and hash.

## What installation verifies

The included installer accepts public HTTPS URLs on port 443 without embedded
credentials. It rejects private and reserved network addresses, checks each
redirect again, pins each connection to the address that passed validation,
limits response time and size, and limits archive file count and expanded size.
It rejects path traversal, links, and special files before extraction begins.

Before commit it verifies the archive SHA-256, the archived module name and
version, and that the entry exists inside the package. Production npm
dependencies require a published `package-lock.json` and are installed inside
the module with `npm ci --omit=dev --ignore-scripts`. Packages without a lockfile
are rejected so installation cannot resolve a different tree on each machine.

Node dependencies are registry-only. Package and lockfile validation rejects
filesystem, workspace, URL, Git, shorthand repository and arbitrary tarball
specifiers. Every external lock entry must resolve from the approved npm
registry and carry integrity metadata. Installation uses a temporary npm config
and cache; host tokens, user configuration and module `.npmrc` files are not
inherited. TLS verification remains enabled. `--ignore-scripts` is a risk
reduction measure, not a sandbox.

These controls reduce transport, SSRF, and archive risks. They do not audit the
module's JavaScript or isolate it from the host process.

## Dependencies and activation

The UI first requests a dry-run plan. When dependencies are missing, it shows
their names, versions, and installation order before asking for confirmation.
The installer resolves the complete graph and commits dependencies before the
requested module. A failure rolls back prepared installs.

Installed modules remain disabled until the project explicitly changes their
state. Recipes may include desired states and capability-provider choices as one
reviewable composition plan.

## Additional catalogs

Add local catalog configuration in `gravewright.marketplace.local.json` or set
comma-separated URLs in `GRAVEWRIGHT_CATALOGS`. The official catalog remains
enabled. Remote failures fall back to the last valid local cache and surface a
warning instead of silently pretending the catalog is current.
