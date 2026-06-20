# Gravewright Documentation

This directory is the canonical documentation set for Gravewright.

Brazilian Portuguese documentation is available in `pt-br/README.md`.

## Start Here

- `getting-started.md` explains local setup and first run with the `grave` CLI.
- `alpha.md` explains Alpha risk, backups, and upgrade expectations.
- `operations.md` documents backups, restore, diagnostics, and runtime storage.
- `sdk/README.md` is the entry point for SDK package authors.

## Project Guides

- `configuration.md` documents environment variables and runtime configuration.
- `architecture.md` explains the backend, frontend, persistence, realtime, and SDK package boundaries.
- `development.md` documents the local workflow and contribution expectations.
- `testing.md` documents unit, CLI, E2E, Docker, and performance tests.
- `deployment.md` documents production deployment requirements.
- `desktop-distribution.md` documents building and shipping the unzip-and-run desktop app to end users.
- `security.md` documents the security model and hardening checklist.
- `licensing.md` documents the Apache-2.0 core and MIT API-material split.
- `storage.md` documents uploaded files, package-scoped data, and cleanup behavior.
- `docker-tests.md` documents the test Docker Compose layout.
- `publication-checklist.md` documents the public Alpha publication checklist.

## API Guides

- `api/README.md` is the entry point for public API documentation.
- `api/http.md` lists HTTP route groups and their authorization boundaries.
- `api/realtime.md` documents WebSocket transport, commands, events, and replay behavior.

## SDK: the only extension model

- `sdk/README.md` is the entry point for the Gravewright SDK.
- `sdk/manifest.md` documents the package manifest (v1).
- `sdk/declarative-packages.md` documents declarative schemas, sheets, items, content packs, rules, mappings, locales, and assets.
- `sdk/kinds.md` documents package kinds.
- `sdk/capabilities.md` documents capabilities and enforcement.
- `sdk/runtime.md` documents the `window.GravewrightSDK` browser runtime.
- `sdk/messaging.md` documents package-to-package events.
- `sdk/cli.md` documents the `grave` CLI.
- `sdk/creating-packages-with-ai.md` documents the AI-assisted package creation workflow.
- `sdk/security.md` documents path safety, uploads, and authorization.

## Documentation Rules

- Treat the backend as authoritative for game state.
- Mark public APIs clearly before extension authors rely on them.
- Keep examples minimal and runnable.
- Keep security and licensing boundaries explicit.
- Update docs in the same change that modifies a public route, package manifest schema, SDK contract, CLI command, or deployment requirement.
