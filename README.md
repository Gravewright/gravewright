# Gravewright

Gravewright is an open-source virtual tabletop platform for tabletop RPGs.

It is built for self-hosted tables that want server-authoritative gameplay, documented extension APIs, declarative system packages, campaign-scoped modules, and predictable performance under large maps and realtime collaboration.

> [!WARNING]
> **ALPHA — DO NOT RUN LONG CAMPAIGNS.**
>
> Gravewright is in Alpha. Structural changes, especially schema changes, may happen between versions and **there is no guaranteed upgrade path**.
>
> An update can make an existing table unrecoverable.
>
> **Use it for one-shots.** Test it, break it, and report problems and suggestions in [issues](https://github.com/Gravewright/gravewright/issues).
>
> What you lose in a one-shot is one session. In a campaign, it can be months.

## Installation and Demo Video

New to Gravewright? Start here:

[![Gravewright Install Guide](https://img.youtube.com/vi/19F2UvY4j9w/hqdefault.jpg)](https://youtu.be/19F2UvY4j9w)

[Watch the Gravewright install guide and demo](https://youtu.be/19F2UvY4j9w)

The video walks through local installation and shows the current Alpha experience.

## Quick Start

Requirements:

* Python 3.11+
* [`uv`](https://docs.astral.sh/uv/)
* SQLite for local development
* PostgreSQL for production deployments

Run Gravewright locally:

```bash
uv sync
cp .env.example .env
uv run uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

The default local database is:

```text
storage/gravewright.sqlite3
```

Startup creates the runtime schema when needed.

## Current Status

Gravewright is pre-1.0.

Core gameplay, campaigns, realtime transport, maps, actors, items, journals, permissions, systems, modules, and diagnostics are actively evolving.

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
* System API v1 for declarative RPG system packages.
* Module API v1 for campaign-scoped frontend extensions and content packs.
* Owner diagnostics for realtime metrics and scrubbed runtime events.

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
* `docs/modules.md`
* `docs/systems/creating-a-system.md`

Brazilian Portuguese documentation starts at:

* `docs/pt-br/README.md`

## Licensing

* Gravewright core is licensed under Apache-2.0. See `LICENSE`.
* Gravewright public API materials are licensed under MIT. See `LICENSE-API.md`.
* The dual-license boundary is documented in `docs/licensing.md`.

## Development Commands

```bash
uv run pytest tests/unit
python3 -m compileall app tests scripts main.py
docker compose -f tests/docker-compose.perf.yml config
```

The test Docker Compose files live under `tests/`. Use the runner scripts there for performance gates.

## Repository Layout

```text
app/actions/       HTTP, WebSocket, form, redirect, and template handlers
app/business/      product rules for auth, campaigns, users, and permissions
app/engine/        table runtime services for scenes, sheets, chat, modules, systems
app/realtime/      WebSocket transport, command dispatch, event log, presence
app/domain/        enums, value objects, and shared permission definitions
app/persistence/   SQLAlchemy Core tables and repositories
app/contracts/     abstract ports for transport, email, and storage
data/systems/      bundled system packages
data/modules/      bundled module packages
docs/              project documentation
schemas/           public JSON schemas for system API materials
tests/             unit, integration, Docker, and performance tests
```

## Contributing

See `CONTRIBUTING.md`, `SECURITY.md`, and `CODE_OF_CONDUCT.md`.
