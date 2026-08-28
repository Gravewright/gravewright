# Gravewright Documentation

This directory is the canonical documentation set for Gravewright.

Current release: **Gravewright v1.0.0-beta.4**, certified against **SDK 1 RC 1**. See the
[release notes and complete history](../RELEASE_NOTES.md).

Brazilian Portuguese documentation starts at [pt-br/README.md](pt-br/README.md).
Spanish SDK documentation starts at [es/sdk/README.md](es/sdk/README.md).

## Start Here

- [Getting started](getting-started.md) explains local setup and the first run.
- [Beta status](beta.md) defines compatibility expectations for the current release.
- [Operations](operations.md) covers backup, restore, diagnostics, and runtime storage.
- [Performance](performance.md) defines benchmark methodology and current verified results.
- [Core/SDK coverage audit](maintainers/sdk-coverage.md) records missing gameplay APIs and intentional private boundaries.
- [Benchmark reports](benchmarks/README.md) preserve the realistic-scene and synthetic renderer results.
- [SDK documentation](sdk/README.md) is the entry point for package authors.
- [Porting modules to Gravewright](sdk/porting-modules.md) covers licensing, architecture mapping, SDK gaps, testing, and publication.

## Project Guides

- [Configuration](configuration.md)
- [Architecture](architecture.md)
- [Development](development.md)
- [Testing](testing.md)
- [Deployment](deployment.md)
- [Desktop distribution](distribution/desktop.md)
- [Security](security.md)
- [Licensing](licensing.md)
- [Storage](storage.md)
- [Docker test layout](docker-tests.md)
- [Publication checklist](maintainers/release-checklist.md)
- [Dynamic lighting](features/dynamic-lighting.md)
- [Dice tray](features/dice-tray.md)

## API Guides

- [API overview](api/README.md)
- [HTTP API and authorization](api/http.md)
- [Realtime protocol](api/realtime.md)

## SDK: the only extension model

- [SDK overview](sdk/README.md)
- [SDK 1 manifest](sdk/manifest.md)
- [Declarative packages](sdk/declarative-packages.md)
- [Package kinds](sdk/kinds.md)
- [Capabilities](sdk/capabilities.md)
- [Browser runtime](sdk/runtime.md)
- [Package messaging](sdk/messaging.md)
- [CLI](sdk/cli.md)
- [Creating packages with AI](sdk/creating-packages-with-ai.md)
- [Porting modules](sdk/porting-modules.md)
- [SDK security](sdk/security.md)

## Documentation Rules

- Treat the backend as authoritative for game state.
- Mark public APIs clearly before extension authors rely on them.
- Keep examples minimal and runnable.
- Keep security and licensing boundaries explicit.
- Update docs in the same change that modifies a public route, package manifest schema, SDK contract, CLI command, or deployment requirement.
