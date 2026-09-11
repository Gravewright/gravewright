# Code map

[Documentation](../README.md) · [Português](../pt-BR/code-map.md) · [Architecture](architecture.md)

Use this map to find the owner of a behavior before editing it. Most Django apps
follow `models.py` for persistence, `services.py` for domain rules, `views.py` and
`urls.py` for HTTP, and `tests/` or `tests.py` for behavior checks. Migrations describe
schema history; they are not the place to document or change current service logic.

## Start here

| Location | What it does |
| --- | --- |
| [`manage.py`](../../manage.py) | Django management entry point. |
| [`main.py`](../../main.py) | Starts the ASGI development server using the configured host and port. |
| [`scripts/gravewright_runner.py`](../../scripts/gravewright_runner.py) | Prepares the personal configuration/database/assets and runs the local Daphne server for Gravewright Runner. |
| [`Gravewright Runner.bat`](../../Gravewright%20Runner.bat) | Windows CMD launcher: detects/reuses uv, Python and Node/npm, installs missing tools, runs locked dependency/build commands and starts the application. |
| [`scripts/prepare_frontend.py`](../../scripts/prepare_frontend.py) | Plans frontend preparation from dependency/source/output fingerprints and records verified build outputs for the batch launcher. |
| [`scripts/windows/create_shortcut.py`](../../scripts/windows/create_shortcut.py) | Creates the Windows icon shortcut through standard-library ctypes and Windows COM. |
| [`config/runner.py`](../../config/runner.py), [`config/runner_asgi.py`](../../config/runner_asgi.py), [`config/runner_urls.py`](../../config/runner_urls.py) | Dedicated local execution profile, collected static assets and runner routes; see the [Windows guide](windows-runner.md). |
| [`pyproject.toml`](../../pyproject.toml), [`uv.lock`](../../uv.lock) | Python requirements and locked dependency resolution. |
| [`config/environment.py`](../../config/environment.py) | Environment loading and parsing of booleans, paths and the public origin. |
| [`config/engine.py`](../../config/engine.py) | Feature flags and validated engine limits. |
| [`config/settings.py`](../../config/settings.py) | Installed apps, SQLite, sessions, templates, media and Channels configuration. |
| [`config/asgi.py`](../../config/asgi.py), [`config/wsgi.py`](../../config/wsgi.py) | Server entry points; ASGI includes the tabletop WebSocket transport. |
| [`config/proxy.py`](../../config/proxy.py) | Restores HTTP/WebSocket schemes from one valid forwarded-proto header sent by a trusted socket peer. |
| [`config/urls.py`](../../config/urls.py) | Aggregates app HTTP routes. |
| [`config/jinja2.py`](../../config/jinja2.py) | Template environment shared by the Jinja2 interface. |
| [`api/`](../../api) | Supported Python extension imports, reexporting authorized domain entry points. |
| [`scripts/generate_frontend_api.py`](../../scripts/generate_frontend_api.py) | Regenerates the browser method registry from its transport contract. |

## Application domains

Paths below are relative to `gravewright/`.

| App | Main models | Read first | Related implementation |
| --- | --- | --- | --- |
| [`accounts/`](../../gravewright/accounts) | `User`, `AuthAttempt`, `UserPreference` | `services.py`, `models.py` | `forms.py` validates account input; `managers.py` normalizes identities; `client_ip.py` resolves trusted proxies; `middleware.py` bounds auth bodies and sets response security policy. |
| [`campaigns/`](../../gravewright/campaigns) | `Campaign`, `Membership`, `AccessCode`, `JoinAttempt`, `Onboarding`, `StreamerLink` | `services.py`, `streamer.py` | `onboarding.py` prepares first-use guidance; `catalog.py` describes the native ruleset; views handle invitations, membership and covers. |
| [`web/`](../../gravewright/web) | None | `inside.py`, `responses.py` | Composes account/campaign/settings pages; `iconography.py` supplies template icons; `jinja2/` and `static/` contain shared UI. |
| [`table/`](../../gravewright/table) | `LobbyState` | `domain.py`, `views.py`, `services.py` | `media.py` uploads/serves audio and cards; `events.py` declares trusted change signals; `dock.json` and message JSON configure the table interface. |
| [`actors/`](../../gravewright/actors) | `Actor`, `Folder`, `Asset` | `services.py` | Views implement sheet reads and authenticated PDF/image uploads and delivery. |
| [`pdf_system/`](../../gravewright/pdf_system) | None | `schema.py` | Native PDF sheet defaults and validation; browser sheet behavior lives in `static/`. |
| [`tokens/`](../../gravewright/tokens) | `Token` | `services.py` | Actor linkage, snapshots, movement, vision and filtered drag previews; `views.py` exposes state. |
| [`maps/`](../../gravewright/maps) | `Scene`, `Tile`, `Broadcast`, `SceneState`, `SceneObject`, `Folder`, `Receipt`, `MapAsset`, `AssetFolder` | `services.py`, `objects.py`, `views.py` | `assets.py` handles the asset library; `extra_objects.py`, `markers.py`, `zones.py` validate specialized layers; render scheduling/prefetch helpers prioritize tiles. |
| [`journals/`](../../gravewright/journals) | `Journal`, `Folder`, `Access`, `Asset`, `Receipt`, `BoardEntry` | `services.py`, `data.py`, `types.py` | `documents.py` validates structured text and secret blocks; `presentations.py` manages handout tickets; views protect uploads and downloads. |
| [`chat/`](../../gravewright/chat) | `Message`, `Recipient`, `SendWindow`, `CardAttachment` | `services.py`, `context.py` | `card_attachments.py` captures immutable card faces; templates render stored chat/roll data. |
| [`dice/`](../../gravewright/dice) | `Submission` | `services.py`, `engine.py` | `grammar/parser.py`, `compiler.py`, `runtime.py` own native notation and evaluation; grammar documentation and deterministic fixture tests live beside them. |
| [`items/`](../../gravewright/items) | `Item`, `Folder` | `services.py` | Permission-filtered item documents; `types()` currently returns no native types. |
| [`combat/`](../../gravewright/combat) | `Encounter` | `services.py`, `effects.py` | `active_effects.py` provides effect helpers; `formula_engine.py` is a separate declarative formula interpreter. |
| [`cards/`](../../gravewright/cards) | `Deck`, `Card`, `CardAsset`, `DeckDefinition` | `services.py` | Controls deck lifecycle, draws, ownership and visibility; card file routes live in `table/media.py`. |
| [`audio/`](../../gravewright/audio) | `Track`, `Playlist`, `Playback` | `services.py`, `transport.py` | `metadata.py` inspects audio; `soundtrack.py` schedules music; `geometry.py` calculates attenuation through walls. |
| [`compendiums/`](../../gravewright/compendiums) | `Pack`, `Entry`, `EntryAsset`, `ContentAccess` | `services.py`, `catalog.py` | `graph.py` selects portable dependencies; `assets.py` copies/restores linked files; `signals.py` cleans owned files. |
| [`realtime/`](../../gravewright/realtime) | `PresenceConnection` | `consumers.py`, `services.py`, `dispatch.py` | `routing.py`, `security.py`, `scene_stream.py`, `gm_guided_prefetch.py` own sockets, origin checks and viewport scheduling. |
| [`administration/`](../../gravewright/administration) | `HostSettings`, `Snapshot`, `AuditEvent` | `views.py`, `archives.py`, `preferences.py` | `updates.py` discovers source releases; `release_metadata.py` validates/fetches release metadata. |
| [`modules/`](../../gravewright/modules) | Package/catalog state | `packages.py`, `operations.py`, `contracts/` | Extension installation, marketplace and transport contracts; inspect this app when changing package capabilities or generated API declarations. |

## Following a feature through the code

### A character sheet save

1. Browser/API submits `actors.command` with action `sheet.save`.
2. `realtime/consumers.py` or `api.actors.command` reaches
   `actors/services.py:command`.
3. The command locks the campaign, reloads membership and checks its receipt.
4. `save_sheet()` resolves actor versus token snapshot, checks revisions and calls
   `pdf_system/schema.py:normalize`.
5. The service saves data/revisions and calls `realtime/dispatch.py:changed`.
6. Committed actor/token/layer invalidations cause each subscribed socket to read
   its own authorized state.

### A map viewport update

1. The socket receives `scene.viewport`.
2. `scene_stream.py:resolve` checks scene access, LOD, coordinates, generation and
   configured viewport bounds.
3. `SceneStreamMixin` feeds `maps/render_scheduler.py` and, when appropriate,
   exchanges GM samples through Channels.
4. The consumer emits tile-ready/prefetch hints. The browser downloads raster bytes
   from the authenticated tile route in `maps/views.py`.

### A new chat roll

1. `realtime/consumers.py:roll` validates the payload and asks `dice/services.py`
   for a durable claim.
2. `dice/engine.py:evaluate` parses, compiles and executes the expression outside the
   database executor. A replay skips evaluation.
3. `dice/services.py:complete` rechecks membership/session and commits the message.
4. `realtime/dispatch.py:message` publishes committed data; each receiver checks
   current authorization, scene and audience before delivery.

### A reusable content import

1. `compendiums/services.py` checks pack visibility, command permission and system.
2. Bundled entries pass through `administration/archives.py:import_campaign`.
3. The importer validates the manifest and allowlisted graph, rewrites resource/file
   references and merges into the destination campaign.
4. `table/domain.py` records the command result and schedules dependent state
   refreshes after commit.

## Where a contributor should make a change

| Change | Likely owner | Review alongside it |
| --- | --- | --- |
| Campaign or resource permission | Owning service, often `journals.services.member` or `maps.services.scene` | HTTP file views, socket delivery projections, streamer checks and retries. |
| New resource command | Owning `services.py` and command transport contract | Validation, request identity, revisions, dispatch, Python API and browser wrapper generation. |
| New database field/model | Owning `models.py` and a new migration | Projections, defaults, import/export graph and test fixtures. |
| New scene object | `maps/objects.py` or a specialized helper | Recipient filtering, version checks, token/vision/audio interactions and renderer support. |
| Dice notation | `dice/grammar/` | Compiler bounds, runtime facts, stored result compatibility and deterministic fixtures. |
| New upload format | Owning upload view and format inspector | File ownership, authenticated download, cleanup on failure and archive extension allowlist. |
| Shared table UI | `table/jinja2/`, `table/static/`, `table/dock.json` | Browser state/API contract and corresponding server capabilities. |
| Host setting | `config/engine.py` or `administration/preferences.py` | Environment validation, UI exposure, docs and feature-gated behavior. |
| Extension/package behavior | `modules/` and `api/` | Installed manifest contracts, supported imports, license notice and transport generation. |

## Reading and documentation conventions

Code docstrings use English, matching the primary documentation. They explain the
boundary or invariant rather than repeat assignments. Public entry-point docstrings
are available through Python's `help()`; domain rules and cross-file interactions
are explained in [Architecture](architecture.md).

Names such as `who` usually mean a freshly resolved `Membership`; `campaign`/`user`
parameters in public services may be IDs, while internal helpers accept model
instances. Read the signature and caller before passing a value. Similarly,
`table.domain.module()` selects one of five built-in resource services; it is not
the installer for third-party packages under `gravewright/modules/`.

Keep English and Portuguese guides in sync when changing behavior. Preserve
upstream license/comments in vendored assets and avoid editing generated frontend
wrappers directly. See [Development](development.md) and [Testing](testing.md) for
the contributor workflow.
