# Gravewright

Gravewright is an open-source virtual tabletop platform for tabletop RPGs.

It is built for self-hosted tables that want server-authoritative gameplay, a documented SDK with declarative ruleset/addon/library/theme/content/asset packages, a first-class operator CLI, and predictable performance under large maps and realtime collaboration.

> [!WARNING]
> **ALPHA — BACK UP BEFORE UPDATING. DO NOT RUN LONG CAMPAIGNS YET.**
>
> Gravewright is in Alpha. Structural changes, especially schema, SDK, storage, package lifecycle, and migration changes, may happen between versions and **there is no guaranteed upgrade path**.
>
> An update can make an existing table unrecoverable.
>
> Use it for one-shots, test tables, and short Alpha arcs only. Before updating, create a backup and keep the version you played on.
>
> **Recommended Alpha use:** one-shots and short campaigns of a few sessions.
>
> **Not recommended yet:** long-running campaigns, public production hosting, or irreplaceable campaign data.
>
> Test it, break it, and report problems and suggestions in [issues](https://github.com/Gravewright/gravewright/issues).

## Installation and Demo Video

New to Gravewright? Start here:

[![Gravewright Install Guide](https://img.youtube.com/vi/19F2UvY4j9w/hqdefault.jpg)](https://youtu.be/19F2UvY4j9w)

[Watch the Gravewright install guide and demo](https://youtu.be/19F2UvY4j9w)

The video walks through local installation and shows the current Alpha experience.

## Requirements

* Python 3.11+
* [`uv`](https://docs.astral.sh/uv/)
* SQLite for local development
* PostgreSQL for production deployments

## Quick Start

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

Fallback that does not require the `grave` console script to be installed:

```bash
uv run python -m app.cli doctor
uv run python -m app.cli run --open
```

The default local database is:

```text
storage/gravewright.sqlite3
```

Startup creates the runtime schema when needed.

## Grave CLI

The `grave` CLI is the local operator and SDK tooling interface.

Common commands:

```bash
grave doctor
grave doctor --json
grave run --open
grave backup -o backup.zip --include-assets --verify
grave restore backup.zip --dry-run
grave package list
grave package validate data/packages/dnd5e
grave package install dnd5e --yes --enable
grave campaign package activate <campaign_id> dice-so-nice-lite
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
grave addon new my-addon --name "My Addon" --js --settings
grave lock -o grave.lock.json
```

## Backups

Before updating Gravewright or changing packages, create a backup:

```bash
grave backup -o gravewright-backup.zip --include-assets --verify
```

For local/custom packages, create a self-contained backup when supported by your current CLI module:

```bash
grave backup -o gravewright-backup.zip --include-assets --include-packages --verify
```

Test a restore without changing data:

```bash
grave restore gravewright-backup.zip --dry-run
```

Restore requires explicit confirmation:

```bash
grave restore gravewright-backup.zip --yes
```

Restore is destructive. Gravewright keeps a `*.pre-restore` safety copy of the previous SQLite database before overwriting it.

## Current Status

Gravewright is pre-1.0 Alpha.

Core gameplay, campaigns, realtime transport, maps, actors, items, journals, permissions, SDK packages, package tooling, diagnostics, and browser SDK runtime are actively evolving.

APIs documented under `docs/` are intended to become stable public contracts, but breaking changes may still happen before a 1.0 release.

## What Gravewright Includes

* Account auth with server-side sessions and CSRF protection.
* Campaign creation, editing, membership, invitations, removal, and delete confirmation.
* Cascading campaign deletion for database rows and uploaded campaign storage.
* Realtime table state through `/game/ws`.
* Scene upload, tiling, chunk streaming, fog, tokens, measurements, pings, and board markers.
* Actors, items, sheets, folders, ownership, and per-resource permissions.
* Journals, quests, quest boards, image assets, and editor blocks.
* Chat, dice rolls, roll presentation, and combat turn order.
* Streamer links for read-only campaign viewing.
* Gravewright SDK packages for rulesets, addons, libraries, themes, content, and assets.
* SDK package manifest validation, loading, dependency checks, activation, settings, assets, content imports, browser runtime integration, and CLI scaffolding.
* Local operator CLI with `doctor`, `run`, `backup`, `restore`, package management, lockfile generation, and package scaffolding.
* Owner diagnostics for realtime metrics and scrubbed runtime events.

## Gravewright SDK

Gravewright packages are declarative SDK packages.

Supported package kinds:

| Kind | Purpose |
|---|---|
| `ruleset` | Campaign base game system. Defines actor/item types, sheets, rules, combat, mappings, and content. |
| `addon` | Optional campaign extension. Can add UI, hooks, settings, content, scene tools, or runtime behavior. |
| `library` | Passive dependency shared by other packages. |
| `theme` | Visual/UI package, mostly CSS and UI assets. |
| `content` | Importable content-only package. |
| `assets` | Reusable media package for images, maps, icons, audio, and similar assets. |

Unsafe capabilities such as backend execution, raw database access, raw filesystem access, raw network access, and permission override are not part of the public SDK.

## Creating Packages

Use the CLI to scaffold a package:

```bash
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
grave addon new my-addon --name "My Addon" --js --settings
grave theme new my-theme --name "My Theme"
grave content new my-content --name "My Content"
```

Then validate it:

```bash
grave package validate data/packages/my-rpg
grave package doctor my-rpg
```

## Documentation

Start with:

* `docs/README.md`
* `docs/getting-started.md`
* `docs/configuration.md`
* `docs/architecture.md`
* `docs/development.md`
* `docs/testing.md`
* `docs/deployment.md`
* `docs/operations.md`
* `docs/security.md`
* `docs/licensing.md`
* `docs/api/README.md`
* `docs/sdk/README.md`
* `docs/sdk/cli.md`

Brazilian Portuguese documentation starts at:

* `docs/pt-br/README.md`

## Licensing

* Gravewright core is licensed under Apache-2.0. See `LICENSE`.
* Gravewright public API materials are licensed under MIT. See `LICENSE-API.md`.
* The dual-license boundary is documented in `docs/licensing.md`.

## Development Commands

```bash
grave doctor
grave run --open
uv run pytest tests/unit
uv run pytest tests/e2e -q
python3 -m compileall app tests scripts main.py
docker compose -f tests/docker-compose.perf.yml config
```

## Repository Layout

```text
grave             Linux/macOS local CLI launcher
grave.bat         Windows local CLI launcher
app/cli/          Gravewright operator CLI and SDK package tooling
app/actions/      HTTP, WebSocket, form, redirect, and template handlers
app/business/     product rules for auth, campaigns, users, and permissions
app/engine/       table runtime services for scenes, sheets, chat, and the SDK
app/engine/sdk/   Gravewright SDK: package manifest, validator, loader, services
app/realtime/     WebSocket transport, command dispatch, event log, presence
app/domain/       enums, value objects, and shared permission definitions
app/persistence/  SQLAlchemy Core tables and repositories
app/contracts/    abstract ports for transport, email, and storage
data/packages/    bundled SDK packages (rulesets, addons, ...)
docs/             project documentation
schemas/          public JSON schema for the package manifest
tests/            unit, integration, Docker, and performance tests
```

## Contributing

See `CONTRIBUTING.md`, `SECURITY.md`, and `CODE_OF_CONDUCT.md`.
