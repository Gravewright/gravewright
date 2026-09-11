# Gravewright VTT

[English](README.md) · [Português (Brasil)](README.pt-BR.md)

Gravewright is a self-hosted virtual tabletop for running role-playing games in a browser. This repository contains the Django implementation: server-rendered Jinja2 pages, Datastar interactions, a JavaScript/PixiJS board and Django Channels WebSockets.

The current project version is **Alpha 0.1.0**, an alpha preview. The source includes campaigns, maps and scenes, actors with PDF character sheets, tokens, chat and dice, journals and quests, audio, cards, combat, compendiums and installable frontend modules. See the [user guide](docs/en/user-guide.md) for the main workflows and current limitations, and [release identifiers](docs/en/development.md#release-identifiers) for package and tag names.

## Run on Windows

Extract the complete project and double-click **`Gravewright Runner.bat`**. It detects compatible **uv, Python and Node.js/npm** already installed, installs missing tools when needed, prepares the locked Python and npm dependencies, builds the frontend and opens the application in your browser. Later launches reuse the tools and unchanged frontend build. Keep the runner window open while using Gravewright; press **Ctrl+C** to stop it.

The runner executes directly in **Windows CMD**. Use Windows 10 version 1803 or newer, or Windows 11, on x64; built-in `curl.exe`, `tar.exe` and `certutil.exe` handle downloads, extraction and integrity checks.

The runner stores your settings, campaigns and uploads under `%LOCALAPPDATA%\Gravewright`, separately from the source folder. It runs on this computer only and does not need a Redis server. A shortcut with the Gravewright icon is created beside the launcher. See the [Windows runner guide](docs/en/windows-runner.md) for requirements, backups and troubleshooting.

## Run locally from a terminal

Requirements: **Python 3.14 or newer**, [uv](https://docs.astral.sh/uv/), and a modern browser with WebGL support. Standard server settings require Redis when `DJANGO_DEBUG=false` and whenever multiple ASGI processes need to communicate. The Windows runner uses a separate local profile and manages Node.js/npm for frontend preparation. The terminal workflow below serves the committed assets; rebuilding them or running JavaScript tests requires Node.js.

From a source checkout:

```bash
uv sync --locked
cp -n .env.example .env
uv run --locked python manage.py migrate
uv run --locked python main.py
```

The copy command preserves an existing `.env`. Open **http://127.0.0.1:3000** and use `/setup` to create the first VTT owner. Later accounts register as participants. `createsuperuser` grants Django administration privileges; it does not create the VTT owner.

The default database is `data/gravewright.sqlite3`; private uploads and installed modules live under `data/media/`. The root-level `db.sqlite3` is not the configured default. Keep `.env` and runtime data out of source control.

See [getting started](docs/en/getting-started.md) for prerequisites, first login and troubleshooting. For public HTTPS and secure WebSockets, follow [deployment and backups](docs/en/deployment.md), including the Nginx proxy example and public-origin settings.

## For developers

Start with the [documentation index](docs/README.md), [architecture](docs/en/architecture.md) and [code map](docs/en/code-map.md).

| Area | Where to start |
| --- | --- |
| Startup, settings and routing | `main.py`, `manage.py`, `config/` |
| Public Python facade | `api/` |
| Business rules and persistence | `gravewright/<domain>/services.py`, `models.py` |
| WebSocket authentication and command dispatch | `gravewright/realtime/` |
| Table composition and browser code | `gravewright/table/`, `gravewright/maps/frontend/` |
| Modules, contracts and SDK | `gravewright/modules/` |
| Browser regression scenarios | `tests/e2e/` |

The [API guide](docs/en/api.md) distinguishes Python calls, HTTP routes and WebSocket/browser contracts. The [module guide](docs/en/modules.md) explains manifests, package verification, lifecycle and examples. The [frontend guide](docs/en/frontend.md) describes assets, rendering and generated contracts.

For a quick check:

```bash
uv run --locked python manage.py check
uv run --locked python manage.py test config gravewright --noinput
node --test tests/modules/*.test.mjs tests/effects/*.test.mjs
```

The Django test runner uses `data/test-gravewright.sqlite3`; `--noinput` permits replacing that test database. Do not run concurrent suites against it. See [testing](docs/en/testing.md) for the full JavaScript suite, controlled environment settings and Playwright scenarios.

## Contribute

Read [CONTRIBUTING.md](CONTRIBUTING.md) and the [development guide](docs/en/development.md). English is the primary documentation language; Portuguese guides are maintained alongside it. Code comments and docstrings use English. The current application locale setting supports English; the Portuguese documentation does not imply a translated application UI.

Report ordinary bugs through the repository's issue tracker, including reproduction steps and relevant versions. Follow [SECURITY.md](SECURITY.md) for vulnerability reports.

## License

Gravewright's first-party code and documentation are licensed under **GNU GPL version 3 only (`GPL-3.0-only`)**, with the [independent module permission](LICENSE-EXCEPTION) under section 7. Independently written third-party modules may use **any license, including proprietary licenses**, whether or not they use the provided APIs. Copies and modifications of Gravewright core remain subject to GPL-3.0-only; naming copied core code a module does not change its license.

Read the [licensing policy](LICENSING.md), the unmodified [GPLv3 text](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md). Bundled dependencies, inherited assets and user-provided content retain their own applicable terms.
