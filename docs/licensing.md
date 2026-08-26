# Licensing

Gravewright uses a dual-license model.

## Core License

The Gravewright core is licensed under Apache-2.0. The core includes the server implementation, frontend implementation, persistence layer, realtime runtime, templates, tests, Docker configuration, bundled infrastructure code, and general project documentation unless another license is explicitly stated.

The Apache-2.0 license text is in `LICENSE`.

## API Materials License

Gravewright public API materials are licensed under MIT. The MIT license text is in `LICENSE-API.md`.

API materials include:

- the public JSON schema in `schemas/gravewright-package-v1.schema.json`;
- Gravewright SDK specifications and examples in `docs/sdk/`;
- the documented public browser API `window.GravewrightSDK`;
- manifest formats, content-pack formats, declarative layout formats, roll/action format examples, and compatibility examples intended for external package authors.

## Boundary

The MIT license covers the API contract and examples so system, module, integration, and content-pack authors can copy the contract shape freely. It does not relicense the Gravewright core implementation that serves, validates, renders, stores, or executes those contracts.

If a file mixes API specification text with core implementation text, the implementation remains Apache-2.0 and the documented API material remains MIT.

## Third-Party Packages

Runtime dependencies, browser libraries, bundled systems, bundled modules, generated assets, and content packs may have their own licenses. Keep their license and notice files with the package.

The canonical project-wide attribution list is `THIRD_PARTY_NOTICES.md`.
License notices stored beside an asset must also remain beside that asset when
it is copied or redistributed. In particular, the bundled door icons are works
by Delapouite from Game-icons.net under CC BY 3.0; their per-file attribution is
stored in `static/icons/LICENSE-GAME-ICONS.md`.

## Package licenses

SDK packages do not have to use the core license. Authors must choose a license
compatible with all reused code and material and declare a precise SPDX identifier
in manifest `license`, such as `MIT`, `Apache-2.0`, `MPL-2.0`, `GPL-3.0-only`, or
`AGPL-3.0-only`.

The schema accepts a string; this is not automatic legal approval. Include the main
text in `LICENSE` and map differently licensed materials in
`THIRD_PARTY_NOTICES.md`. See [Porting modules](sdk/porting-modules.md#3-licensing)
for the explained list of permissive, GNU copyleft, and asset licenses.

## Contributions

Unless explicitly stated otherwise:

- contributions to core files are submitted under Apache-2.0;
- contributions to public API materials are submitted under MIT;
- contributions that modify both are submitted under the applicable license for each part.
