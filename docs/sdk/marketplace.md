# Marketplace v1 curated registry

The Marketplace is a curated discovery and installation index. Its canonical
source is [`marketplace.toml`](../../marketplace.toml). An entry approves one
stable package identity for catalog display; it does not activate the package,
grant capabilities, or describe its runtime implementation.

## Registry format

```toml
version = 1

[[packages]]
id = "example-addon"
name = "Example Addon"
kind = "addon"
manifest = "https://packages.example/example-addon/manifest.json"
enabled = true
channel = "stable"
category = "gm-tools"
tags = ["tools"]
featured = false
reviewed_at = "2026-08-16"
update_policy = "publisher"
```

`id`, `name`, `kind`, `manifest`, `enabled`, `channel`, and `update_policy` are the registry
fields. `category`, `tags`, `featured`, and `reviewed_at` are optional editorial
fields. IDs must be unique. Kinds are exactly `ruleset`, `addon`, `library`,
`content`, `theme`, and `assets`. Channels are `stable`, `beta`, or
`experimental`. Manifest and artifact URLs must be HTTP(S) URLs without embedded
credentials.

The package manifest remains authoritative for technical identity, version,
SDK compatibility, dependencies, entrypoints, capabilities, license, and
`distribution`. Marketplace refresh rejects an entry when manifest `id` or
`kind` differs from the approved entry. Marketplace v1 requires a ZIP
distribution with its SHA-256 digest.

`update_policy = "publisher"` follows the version published by a trusted
publisher's stable root manifest. Community entries use a manifest pinned to
the approved release together with `update_policy = "curated"` and
`approved_version`. They may also specify `approved_sha256` when review must
bind the exact bytes as well as the version. Marketplace v1 intentionally does
not implement manifest history; pinning the community manifest URL keeps fresh
installs reproducible.

```toml
[[packages]]
id = "community-addon"
kind = "addon"
manifest = "https://raw.githubusercontent.com/example/addon/v1.4.2/manifest.json"
enabled = true
channel = "stable"
update_policy = "curated"
approved_version = "1.4.2"
```

The manifest's `$schema` only identifies the JSON Schema used for validation.
It is never used for discovery or download. The preferred v1 fields are
top-level `download` and `sha256`; the existing `distribution.url` and
`distribution.sha256` representation remains compatible. Release artifacts
should use immutable, versioned URLs.

`enabled = false` (or removing the entry) removes the package from discovery.
It never uninstalls, disables, or deletes an already-installed package.

## Refresh and cache

Refresh fetches manifests only, validates each independently, and writes an
atomic cache under the configured Gravewright data directory. Opening the UI
reads this cache and does not contact every publisher. A bad package becomes
Unavailable without hiding valid siblings. A registry error or total network
failure retains the last valid cache and reports Refresh failed.

## Installation and updates

Install and Update use the same pipeline:

1. Resolve the approved cached entry.
2. Download the bounded artifact.
3. compare its SHA-256 digest;
4. validate ZIP members, sizes, paths and symlinks;
5. extract into staging;
6. bind staged manifest ID, kind, version, and SDK version to the fetched manifest;
7. run Package Doctor against staging;
8. swap the package tree and persist installed state;
9. restore the previous tree if the final swap or persistence fails.

An install leaves the package installed but does not enable it globally or
activate it in campaigns. Updating preserves its existing lifecycle status.
The existing manual file install remains available for advanced use and does
not require Marketplace membership.

Marketplace approval means curated for discovery and installation. Package
browser JavaScript remains trusted package code; approval is not a sandbox or a
complete security audit.

## Maintainer approval workflow

1. Review the package source, manifest, license, publisher and distribution.
2. Run Package Doctor against the packaged ZIP.
3. Confirm SDK 1 compatibility and declared capabilities.
4. Reproduce the artifact SHA-256.
5. Add the minimal curated entry to `marketplace.toml`.
6. Merge the reviewed change; users expose it on their next Refresh.

The versioned registry and stable package ID allow later signed indexes,
publisher submissions, screenshots and multiple registries without changing
installed package identity.
