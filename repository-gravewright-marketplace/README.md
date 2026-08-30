# gravewright-marketplace

Official package catalog for [Gravewright](https://github.com/Gravewright/gravewright).

This repository hosts the marketplace index consumed by Gravewright to discover available rulesets, addons, content packs, themes, libraries, and other supported packages.

## Catalog

The marketplace is defined in:

```text
marketplace.toml
```

Each entry describes a package available for discovery or installation through Gravewright.

Catalog metadata may include:

* package identifier and kind;
* current version;
* compatibility information;
* distribution source;
* download artifact;
* SHA-256 digest;
* project and author information.

The authoritative package format and validation rules are defined by the Gravewright SDK.

## Package distribution

Packages listed in the marketplace may be classified by distribution source:

* **Core** — maintained or distributed as part of the official Gravewright ecosystem.
* **Community** — maintained by community authors and independent developers.
* **Partner** — distributed by recognized publishers or project partners.

Distribution classification is metadata only. It does not grant additional SDK capabilities, permissions, or runtime privileges.

## Adding or updating a package

Changes to the marketplace are made by editing `marketplace.toml`.

When publishing a new package version, ensure that its catalog entry references the correct release artifact and SHA-256 digest.

Package artifacts must remain valid according to the Gravewright SDK contract and compatibility requirements.

## Security

Marketplace packages are validated by Gravewright before installation.

Remote artifacts are subject to integrity, compatibility, manifest, dependency, and package validation checks. A marketplace listing does not bypass the normal Gravewright package security model.

## Related project

* [Gravewright](https://github.com/Gravewright/gravewright) — open-source virtual tabletop and extensible RPG platform.

## License

Marketplace metadata is maintained by the Gravewright project. Individual packages retain their own licenses and ownership terms.
