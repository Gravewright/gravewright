# Architecture

Gravewright is a server-authoritative VTT. The browser renders the table and sends user intent; the backend validates permissions, mutates state, persists data, and broadcasts events.

## Layers

```text
app/actions/       Litestar route handlers, forms, redirects, templates, WebSocket entrypoints
app/business/      product rules for auth, campaigns, invitations, users, and permissions
app/engine/        table runtime services for maps, sheets, actors, items, journals, and SDK packages
app/realtime/      WebSocket transport, command dispatch, event log, scene stream, presence
app/domain/        shared enums, permissions, value objects, and domain constraints
app/persistence/   SQLAlchemy Core tables and repositories
app/contracts/     abstract ports for transport, email, and storage
app/infrastructure concrete storage, email, image, and integration implementations
```

## Dependency Direction

```text
actions -> business/engine -> persistence
actions -> contracts
engine -> domain
business -> domain
persistence -> tables/database only
```

Rules:

- `actions` do not import repositories directly.
- `engine` does not depend on Litestar request, response, or template objects.
- `persistence` does not import services.
- `domain` does not import infrastructure.
- contracts define ports; implementations live in runtime packages.

## Request Flow

1. A Litestar handler in `app/actions` receives a request.
2. Authentication and CSRF guards run for protected routes.
3. The handler calls a service from Litestar dependency injection.
4. The service validates permissions and product rules.
5. Repositories execute SQLAlchemy Core statements.
6. The handler returns a redirect, JSON response, file response, template, or WebSocket event.

## Realtime Flow

1. Browser connects to `/game/ws`.
2. The server authenticates the session and room membership.
3. Commands enter `CommandDispatcher`.
4. Domain command handlers validate permissions and payloads.
5. State mutations are persisted.
6. Events are appended to the room event log and broadcast to subscribed users.
7. Clients reconcile state from events, manifests, or viewport chunks.

## Persistence

The schema source is `app/persistence/tables.py`. Repositories use SQLAlchemy Core and plain row dictionaries. SQLite is the default local backend. PostgreSQL is the supported production backend.

## Frontend

The frontend uses Jinja templates, static JavaScript modules, PixiJS for board rendering, and the public `window.GravewrightSDK` browser runtime for packages. Core UI code lives under `static/js`. CSS lives under `static/css`.

## SDK Package Boundaries

SDK packages are the only extension model. Rulesets define RPG rules, sheets, mappings, assets, and content packs. Addons, themes, content packages, asset libraries, and passive libraries extend a campaign through declared capabilities. Every package is validated from `schemas/gravewright-package-v1.schema.json` and loaded through explicit public APIs documented under `docs/sdk/`.
