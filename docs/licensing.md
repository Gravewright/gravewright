# Licensing

Gravewright uses a dual-license model.

## Core License

The Gravewright core is licensed under Apache-2.0. The core includes the server implementation, frontend implementation, persistence layer, realtime runtime, templates, tests, Docker configuration, bundled infrastructure code, and general project documentation unless another license is explicitly stated.

The Apache-2.0 license text is in `LICENSE`.

## API Materials License

Gravewright public API materials are licensed under MIT. The MIT license text is in `LICENSE-API.md`.

API materials include:

- public JSON schemas in `schemas/`;
- System API v1 specifications and examples in `docs/systems/`;
- Module API v1 specifications and examples in `docs/modules.md`;
- documented public browser APIs such as `window.Gravewright`, `window.GravewrightSheets`, and `window.GravewrightCombat`;
- manifest formats, content-pack formats, declarative layout formats, roll/action format examples, and compatibility examples intended for external system or module authors.

## Boundary

The MIT license covers the API contract and examples so system, module, integration, and content-pack authors can copy the contract shape freely. It does not relicense the Gravewright core implementation that serves, validates, renders, stores, or executes those contracts.

If a file mixes API specification text with core implementation text, the implementation remains Apache-2.0 and the documented API material remains MIT.

## Third-Party Packages

Runtime dependencies, browser libraries, bundled systems, bundled modules, generated assets, and content packs may have their own licenses. Keep their license and notice files with the package.

## Contributions

Unless explicitly stated otherwise:

- contributions to core files are submitted under Apache-2.0;
- contributions to public API materials are submitted under MIT;
- contributions that modify both are submitted under the applicable license for each part.
