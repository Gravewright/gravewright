# Gravewright Documentation

This directory is the canonical documentation set for Gravewright.

Brazilian Portuguese documentation is available in `pt-br/README.md`.

## Project Guides

- `getting-started.md` explains local setup and the first run.
- `configuration.md` documents environment variables and runtime configuration.
- `architecture.md` explains the backend, frontend, persistence, realtime, and extension boundaries.
- `development.md` documents the local workflow and contribution expectations.
- `testing.md` documents unit, integration, Docker, and performance tests.
- `deployment.md` documents production deployment requirements.
- `operations.md` documents backups, migrations, diagnostics, and runtime storage.
- `security.md` documents the security model and hardening checklist.
- `licensing.md` documents the Apache-2.0 core and MIT API-material split.
- `storage.md` documents uploaded files, system data, and cleanup behavior.
- `docker-tests.md` documents the test Docker Compose layout.

## API Guides

- `api/README.md` is the entry point for public API documentation.
- `api/http.md` lists HTTP route groups and their authorization boundaries.
- `api/realtime.md` documents WebSocket transport, commands, events, and replay behavior.
- `api/extension-apis.md` documents public browser APIs exposed to systems and modules.
- `modules.md` documents Module API v1.
- `systems/README.md` is the entry point for System API documentation.
- `systems/creating-a-system.md` documents System API v1 package creation.
- `systems/manifest.md` documents system manifests.
- `systems/sheets.md` documents declarative sheets.
- `systems/rolls.md` documents rolls.
- `systems/combat.md` documents combat.
- `systems/content-packs.md` documents system content packs.

## Documentation Rules

- Treat the backend as authoritative for game state.
- Mark public APIs clearly before extension authors rely on them.
- Keep examples minimal and runnable.
- Keep security and licensing boundaries explicit.
- Update docs in the same change that modifies a public route, manifest schema, module API, system API, or deployment requirement.
