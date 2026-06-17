# Gravewright v1.0.0-alpha.1

> [!WARNING]
> **Gravewright v1.0.0-alpha.1 is an Alpha release.**
>
> Back up before updating. Do not run long campaigns yet.
>
> Gravewright is in Alpha. Structural changes, especially database schema, storage layout, SDK/package contracts, realtime events, and public API behavior, may occur between Alpha releases.
>
> **There is no guaranteed upgrade path between Alpha releases.** An update may make an existing table unrecoverable.
>
> **Use it for one-shots, testing, and experimentation.** Test it, break it, and report problems or suggestions in issues.
>
> In a one-shot, you may lose a session. In a long campaign, you may lose months.

## What is this?

This is **Gravewright v1.0.0-alpha.1**, a public Alpha release of Gravewright.

Gravewright is an experimental open source virtual tabletop platform focused on:

- self-hosted table play;
- server-authoritative gameplay;
- scene and map interaction;
- actors, items, journals, chat, combat, permissions, and realtime collaboration;
- large-map handling through tiling and chunk streaming;
- declarative game support through the Gravewright SDK;
- installable SDK packages for rulesets, addons, libraries, themes, content, and assets;
- a local operator CLI for setup, diagnostics, backups, package tooling, and development.

## What changed in v1.0.0-alpha.1

This release consolidates the new SDK/package architecture and local operator tooling.

Highlights:

- Added the unified Gravewright SDK package model.
- Replaced the old System API / Module API split with one package contract.
- Added support for package kinds:
  - `ruleset`
  - `addon`
  - `library`
  - `theme`
  - `content`
  - `assets`
- Added the package manifest schema:
  - `schemas/gravewright-package-v1.schema.json`
- Added package loading from:
  - `data/packages/`
- Added SDK package runtime integration through:
  - `window.GravewrightSDK`
- Added SDK package validation, activation, dependency checks, settings, assets, content imports, and browser runtime registration.
- Added the `grave` operator CLI.
- Added local launchers:
  - `grave`
  - `grave.bat`
- Added CLI commands for:
  - diagnostics;
  - local server startup;
  - backup and restore;
  - lockfile generation;
  - package listing, validation, install, enable, disable, remove, update, and doctor;
  - campaign package activation;
  - package scaffolding with `grave <kind> new`.
- Updated English and Brazilian Portuguese documentation to match the current SDK and CLI architecture.

## Breaking changes

This Alpha may require a clean setup or manual migration from older pre-alpha data.

Breaking changes include:

- The old System API v1 is no longer the public extension model.
- The old Module API v1 is no longer the public extension model.
- Extension authors should use the Gravewright SDK package manifest instead.
- Old `data/systems/` and `data/modules/` layouts should not be treated as current package locations.
- Public package assets now belong under validated package-relative paths.
- Public extension behavior should rely only on documented SDK APIs.
- Undocumented renderer internals, DOM structure, browser globals, fallback labels, and private runtime helpers are not stable extension surfaces.

Before updating an existing Alpha checkout, back it up.

Recommended:

```bash
grave doctor
grave backup -o gravewright-backup.zip --include-assets --verify
```

For local/custom packages, also include package files if supported by your current CLI module:

```bash
grave backup -o gravewright-backup.zip --include-assets --include-packages --verify
```

## How to install locally

```bash
uv sync
cp .env.example .env
chmod +x grave
./grave doctor
./grave run --open
```

Open:

```text
http://127.0.0.1:8000
```

Windows:

```bat
grave.bat doctor
grave.bat run --open
```

Fallback:

```bash
uv run python -m app.cli doctor
uv run python -m app.cli run --open
```

## What to test

Please help by testing:

- fresh installation from the README;
- local setup using `.env.example`;
- `grave doctor`;
- `grave run --open`;
- account creation and login;
- creating and joining campaigns;
- scene upload, maps, grid, fog, tokens, measurements, and realtime sync;
- actors, items, sheets, journals, chat, combat, and permissions;
- SDK package loading from `data/packages/`;
- the bundled `dnd5e` ruleset package;
- the bundled `dice-so-nice-lite` addon package;
- package activation and deactivation per campaign;
- package validation with `grave package validate`;
- package diagnostics with `grave package doctor`;
- package scaffolding with `grave ruleset new`, `grave addon new`, `grave theme new`, `grave content new`, `grave assets new`, and `grave library new`;
- backup and dry-run restore;
- Docker/test setup where applicable;
- browser E2E behavior where Firefox/Selenium are available.

## What not to do yet

Do not trust this release for long-running campaigns.

Known Alpha risks:

- database schema may change without migration support;
- storage layout may change;
- SDK package contracts may change;
- realtime event names and payloads may change;
- existing tables may not survive upgrades;
- package manifests may need updates between Alpha releases;
- documentation may still lag behind implementation in some areas;
- scripted packages run trusted JavaScript in the browser and should only be installed from trusted authors.

## Validation

This release path was locally validated with:

```bash
uv run pytest tests/unit/test_cli_parser_smoke.py -q
uv run pytest tests/unit/test_cli_backup.py tests/unit/test_cli_doctor.py tests/unit/test_sdk_cli.py -q
uv run pytest tests/unit -q
uv run python -m compileall -q app tests scripts main.py
uv run pytest tests/e2e -q
```

Observed local result:

- CLI parser smoke tests passed.
- Focused CLI, backup, doctor, and SDK CLI tests passed.
- Full unit suite passed.
- Compile check passed.
- Browser E2E passed.

## How to help

Open issues for:

- reproducible bugs;
- installation/setup problems;
- confusing documentation;
- missing SDK examples;
- missing package manifest examples;
- SDK package capability feedback;
- package scaffolding feedback;
- performance problems;
- realtime sync problems;
- UI/UX rough edges;
- Alpha upgrade or backup/restore problems.

When reporting a bug, include:

- operating system;
- Python version;
- browser;
- exact command or action;
- expected behavior;
- actual behavior;
- logs with secrets removed;
- screenshots when useful;
- whether the issue happens on a fresh install.

Pull requests are welcome. Please keep PRs focused and read `CONTRIBUTING.md` first.

For security vulnerabilities, do **not** open a public issue. Follow `SECURITY.md`.

## Security note

Gravewright is a multiplayer web application with sessions, user-generated content, uploaded assets, WebSocket commands, and installable packages.

Packages that declare script entrypoints run trusted JavaScript in the browser. Only install scripted packages from authors you trust.

The public SDK does not include dangerous capabilities such as:

- backend execution;
- raw database access;
- raw filesystem access;
- raw network access;
- permission override.

## Licensing

Gravewright uses a mixed permissive licensing model:

- core/runtime code is Apache-2.0;
- public API materials, SDK-facing examples, and integration materials are MIT-licensed where marked.

See:

- `LICENSE`
- `LICENSE-API.md`
- `NOTICE`
- `docs/licensing.md`
