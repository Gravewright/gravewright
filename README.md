# Gravewright

Gravewright is an open-source virtual tabletop platform for tabletop RPGs.

It is built for self-hosted tables that want server-authoritative gameplay, a documented SDK with declarative ruleset/addon/library/theme/content/asset packages, a first-class operator CLI, and predictable performance under large maps and realtime collaboration.

Current release: **Gravewright 1.0.0 Beta 4**, certified against **SDK 1 RC 1**.
See [RELEASE_NOTES.md](RELEASE_NOTES.md) for the complete release history.

[Website](https://gravewright.com/) ·
[Beta 4 release](https://github.com/Gravewright/gravewright/releases/tag/v1.0.0-beta.4) ·
[Download for Windows](https://github.com/Gravewright/gravewright/releases/download/v1.0.0-beta.4/Gravewright-Windows-x64.zip) ·
[Documentation](https://gravewright.com/wiki/) ·
[Issues](https://github.com/Gravewright/gravewright/issues)

> [!WARNING]
> Gravewright is beta software. Keep verified backups of campaign data before
> upgrades. Scripted SDK packages execute trusted JavaScript in the browser;
> install them only from authors you trust.

## Installation and Demo Video

New to Gravewright? Start here:

[![Gravewright Install Guide](https://img.youtube.com/vi/19F2UvY4j9w/hqdefault.jpg)](https://youtu.be/19F2UvY4j9w)

[Watch the Gravewright install guide and demo](https://youtu.be/19F2UvY4j9w)

The video walks through local installation and shows the application experience.

## Easy Install (recommended for most people)

No terminal knowledge required. The installer sets up everything for you -
including the correct Python version, and then opens Gravewright in your
browser. No administrator rights are needed.

1. Download or clone Gravewright to a folder on your computer.
2. Run the installer for your system:
   * **Windows:** download and extract the
     [official Windows ZIP](https://github.com/Gravewright/gravewright/releases/download/v1.0.0-beta.4/Gravewright-Windows-x64.zip),
     then double-click **`Gravewright.exe`**.
     `install-windows.bat` remains only as a transitional/debug fallback. If SmartScreen
     shows a warning, choose *More info → Run anyway*.
   * **macOS / Linux:** open a terminal in the folder and run:

     ```bash
     bash install-macos-linux.sh
     ```

3. Wait for setup to finish (the first run can take a few minutes). Your browser
   opens automatically at `http://127.0.0.1:8000`.

To play again later, just run the same installer again: it skips setup and
starts right away. Keep the window open while you play; close it or press
`Ctrl+C` to stop.

## Run with Docker

If you already have [Docker](https://docs.docker.com/get-docker/) installed, you
can run everything with one command: no Python or `uv` needed:

```bash
docker compose up -d --build
```

Then open `http://localhost:8000`. Useful commands:

```bash
docker compose logs -f      # watch the logs
docker compose down         # stop (your data is kept)
docker compose up -d --build  # update after pulling changes
```

Your database, uploads, and installed packages are stored in named Docker
volumes, so they survive restarts and rebuilds. This default setup uses SQLite
and serves over plain HTTP for local/self-hosted use; before exposing it
publicly, put an HTTPS reverse proxy in front, set your domain in
`ALLOWED_HOSTS`, and provide a strong `SESSION_SECRET` (see `docker-compose.yml`).

The steps below are the manual path for developers and advanced users.

## Requirements

* Python 3.11+
* [`uv`](https://docs.astral.sh/uv/)
* SQLite for local development
* PostgreSQL for production deployments

## Quick Start

```bash
uv sync
cp .env.development.example .env
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
grave run --diagnostics
grave backup -o backup.zip --include-assets --verify
grave restore backup.zip --dry-run
grave package list
grave package validate data/packages/rulesets/my-rpg
grave package install my-rpg --yes --enable
grave campaign package activate <campaign_id> my-addon
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
grave addon new my-addon --name "My Addon" --js --settings
grave lock -o grave.lock.json
```

## Backups

Before updating Gravewright or changing packages, create a backup:

```bash
grave backup -o gravewright-backup.zip --include-assets --verify
```

For a self-contained backup that also includes installed packages and their managed storage (recommended before an upgrade), add `--include-packages`:

```bash
grave backup -o gravewright-backup.zip --include-assets --include-packages --verify
```

Test a restore without changing data, on a copy, before relying on it for an upgrade:

```bash
grave restore gravewright-backup.zip --dry-run
```

Restore requires explicit confirmation:

```bash
grave restore gravewright-backup.zip --yes
```

Restore is destructive. Gravewright keeps a `*.pre-restore` safety copy of the previous SQLite database before overwriting it.

## Current Status

Gravewright is currently **v1.0.0-beta.4: Beta 4**.

SDK 1 RC 1 is the frozen public compatibility candidate. Packages still declare
`"sdkVersion": "1"`; RC status is release metadata, not a second manifest version.
Breaking changes require explicit contract review and, when incompatible, a future SDK line.

Core gameplay, campaigns, realtime transport, maps, actors, items, journals, permissions, SDK packages, package tooling, diagnostics, Marketplace channels, and browser SDK runtime are included in the Beta 4 line.

## What Gravewright Includes

* Account auth with server-side sessions and CSRF protection.
* Campaign creation, editing, membership, invitations, removal, and delete confirmation.
* Cascading campaign deletion for database rows and uploaded campaign storage.
* Realtime table state through `/game/ws`.
* Scene upload, tiling, chunk streaming, fog, tokens, measurements, pings, and board markers.
* Dynamic lighting with walls, doors, token vision, cinematic rendering, scene shaders, compositing modes, opacity, and a localized library of 50 shader presets.
* Configurable particle effects with multiple emitter shapes, motion styles, appearance controls, and live scene updates.
* Actors, items, sheets, folders, ownership, and per-resource permissions.
* Journals, quests, quest boards, image assets, and editor blocks.
* Chat, dice rolls, roll presentation, and combat turn order.
* Streamer links for read-only campaign viewing.
* Campaign join codes, ready checks, cloning, snapshots, administrative audit history, and global search.
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
| `addon` | Optional campaign extension. Can add UI, plugins, settings, content, scene tools, or runtime behavior. |
| `library` | Passive dependency shared by other packages. |
| `theme` | Visual/UI package, mostly CSS and UI assets. |
| `content` | Importable content-only package. |
| `assets` | Reusable media package for images, maps, icons, audio, and similar assets. |

Unsafe capabilities such as backend execution, direct unmanaged database access, raw filesystem access, raw network access, and permission override are not part of the public SDK. Packages that need SQL use the managed, scoped `storage.sqlite` capability.

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
grave package validate data/packages/rulesets/my-rpg
grave package doctor my-rpg
```

## Documentation

Start with:

- [Documentation index](docs/README.md)
- [Getting started](docs/getting-started.md)
- [Configuration](docs/configuration.md)
- [Architecture](docs/architecture.md)
- [Operations](docs/operations.md)
- [Performance and benchmarks](docs/performance.md)
- [Testing](docs/testing.md)
- [Deployment](docs/deployment.md)
- [Security](docs/security.md)
- [API](docs/api/README.md)
- [SDK](docs/sdk/README.md)
- [SDK governance policy](GRAVEWRIGHT_SDK_GOVERNANCE_POLICY.md)

Additional languages and the module-porting guide:

- [Documentação em português brasileiro](docs/pt-br/README.md)
- [Portando módulos para o Gravewright](docs/pt-br/sdk/porting-modules.md)
- [Porting modules to Gravewright (English)](docs/sdk/porting-modules.md)
- [Portar módulos a Gravewright (Español)](docs/es/sdk/portar-modulos.md)

## Licensing

* Gravewright core is licensed under Apache-2.0. See `LICENSE`.
* Gravewright public API materials are licensed under MIT. See `LICENSE-API.md`.
* The dual-license boundary is documented in `docs/licensing.md`.
* Bundled third-party materials and their attributions are listed in
  `THIRD_PARTY_NOTICES.md`.

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
Gravewright.exe          Official minimal Windows bootstrapper (release ZIP)
install-windows.bat      Transitional/debug Windows fallback
install-macos-linux.sh   One-click setup + launch for macOS/Linux
docker-compose.yml       One-command Docker run (SQLite, persistent volumes)
Dockerfile               Container image build
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

Contributions are welcome.

If you would like to help improve Gravewright:

- Start with a [`good first issue`](https://github.com/Gravewright/gravewright/labels/good%20first%20issue) if you are new to the project.
- Check [`help wanted`](https://github.com/Gravewright/gravewright/labels/help%20wanted) for areas where contributions are especially welcome.
- Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request.
- Use [Discussions](https://github.com/Gravewright/gravewright/discussions) for questions, ideas, and proposals that are not yet ready to become issues.

Please follow the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

Security vulnerabilities should **not** be reported through public issues or discussions. See [`SECURITY.md`](SECURITY.md) for private reporting instructions.
