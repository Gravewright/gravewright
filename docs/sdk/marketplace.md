# Marketplace v2 and distribution channels

The canonical package catalog is the `marketplace.toml` published by
`Gravewright/gravewright-marketplace`. Gravewright downloads it over HTTPS,
validates the complete document, and atomically retains the last known-good
copy. The repository copy is publication input only and may be removed from the
Core repository.

The owner selects `stable`, `testing`, or `dev`. Core and Packages are linked by
default but can be selected independently. Resolution never leaks upward:

- `stable` resolves only `stable`;
- `testing` resolves `testing`, then falls back to `stable`;
- `dev` resolves `dev`, then `testing`, then `stable`.

Changing to a less adventurous channel never downgrades installed code. A
newer installed package is shown as `ahead-of-channel` until the selected
channel catches up or the owner performs an explicit, separately protected
downgrade.

The same document declares which Core channels are currently published. Core
authority is fixed to the official Gravewright repository and GitHub Releases
feed; alternate hosts are rejected.

```toml
[core]
id = "gravewright"
name = "Gravewright"
enabled = true
repository = "https://github.com/Gravewright/gravewright"
releases = "https://api.github.com/repos/Gravewright/gravewright/releases?per_page=30"

[core.channels.dev]
enabled = true
```

Presence publishes a channel; absence makes it unavailable. During development,
Core and packages may expose only `dev`, so stable/testing users never receive
those builds.

## Registry format

```toml
version = 2

[[packages]]
id = "example-addon"
name = "Example Addon"
kind = "addon"
enabled = true
source = "community"
update_policy = "publisher"

[packages.channels.stable]
manifest = "https://packages.example/stable/manifest.json"

[packages.channels.testing]
manifest = "https://packages.example/testing/manifest.json"

[packages.channels.dev]
manifest = "https://packages.example/dev/manifest.json"
```

IDs remain unique. Each entry may expose any subset of the three channels.
Marketplace v1 is accepted as migration input and its legacy `beta` and
`experimental` values map to `testing` and `dev`.

For `update_policy = "curated"`, every declared channel carries its own
`approved_version` and optional `approved_sha256`. `publisher` follows the
version at the channel-specific manifest.

## Provenance and commercial access

`source` is `core`, `community`, or `partner`; the UI presents `partner` as a
verified Publisher. Channel, provenance, editorial policy, and download rights
are independent. Optional listing metadata supports protected IP:

```toml
source = "partner"
access = "entitled"
publisher = "Example Publisher"
license_model = "commercial"
auth_provider = "example-publisher"
```

The public catalog never contains credentials, license keys, permanent secret
URLs, or buyer data. Until an entitlement provider is connected, entitled
packages are visible as `license-required` and installation fails closed.
Selecting `dev` does not grant access to a publisher's private dev channel.

## Integrity and installation

The manifest remains authoritative for SDK compatibility, capabilities,
dependencies, conflicts, and ZIP distribution. Every installation validates
HTTPS policy, SHA-256, archive limits and paths, staged identity, Package Doctor,
and dependency state before atomic promotion. Failures preserve the previous
tree. A bad remote registry or total network failure preserves the last valid
catalog.

The catalog controls package manifests and which Core channels are published.
Core binaries still come exclusively from the official Gravewright GitHub
Releases feed and use the same channel vocabulary.
The running web process never overwrites itself; the verified launcher handles
product replacement and recovery.
