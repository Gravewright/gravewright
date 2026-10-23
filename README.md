# Gravewright VTT

[English](README.md) · [Português (Brasil)](README.pt-BR.md)

Gravewright is a self-hosted virtual tabletop for running role-playing games in a browser. This repository contains the Django implementation: server-rendered Jinja2 pages, Datastar interactions, a JavaScript/PixiJS board and Django Channels WebSockets.

The current project version is **0.3.2**, an alpha preview. The source includes campaigns, maps and scenes, independent system sheets and the bundled PDF System, tokens, chat and dice, journals and quests, progress clocks and clues, collaborative mind maps, audio, cards, combat, compendiums and installable browser modules and trusted Django apps. Game rules and document types belong to their system providers. See the [user guide](docs/en/user-guide.md) for the main workflows and current limitations, and [release identifiers](docs/en/development.md#release-identifiers) for package and tag names.

## Campaign preparation and play

| Tool | What you can do |
| --- | --- |
| [Journals and references](docs/en/journals.md) | Organize pages in independent chapters and subchapters, and link sheets, journals, quests and other resources in rich text using each target's permissions |
| [Campaign manager](docs/en/campaign-management.md) | Open **Manage campaign** before entering the table. Use the campaign's native documents, file library, sheets and scene tools, with a personal dashboard, session planner, timeline/calendar, quest columns, connections, player preview and journal history/trash |
| [Progress clocks](docs/en/clocks.md) | Track segmented goals in the table and campaign manager, with campaign/scene scope, audience controls, optional player progress changes and pinned displays |
| [Clues](docs/en/clues.md) | Prepare findings and private GM notes; reveal the finding to players when its discovery progress is complete |
| [Mind maps](docs/en/mindmaps.md) | Organize linked topics in the table and campaign manager, grant selected players editing access and link 37 native resource types using current permissions |
| [PDF System](docs/en/pdf-system.md) | Map text, numeric and checkbox fields onto a non-editable PDF; bind fields to token bars, add saved dice rolls and calculations, and reuse mappings |
| [Map Builder](docs/en/map-builder.md) | Create editable maps, adopt compatible existing scenes, synchronize supported game edits and connect Smart Object mechanisms to native tools, clocks, clues and mind maps |
| [Universal VTT](docs/en/universal-vtt.md) | Import `.uvtt`, `.dd2vtt` and `.df2vtt` maps as native scenes or editable Builder projects, with warnings for approximations and format limits |

The manager and table share campaign records. GM-only preparation, undiscovered
clues and private documents are filtered on the server. A scene or document link
does not grant permission to its target. See the guides for authorization,
concurrent editing and backup behavior.

## Install and run locally

Start with the [Map Builder guide](docs/en/map-builder.md) to create an editable
map project or add interactive elements over a finished map image. The
[Universal VTT guide](docs/en/universal-vtt.md) explains importing `.uvtt`,
`.dd2vtt` and `.df2vtt` files as native scenes, exporting scenes and reviewing
format limitations. The [0.3.2 release notes](docs/releases/0.3.2.md) describe
campaign preparation, clocks and clues, collaborative mind maps, PDF improvements, Pillow 13 and the
required database migrations.

Extract the complete project into a writable folder, run the installer for your operating system, then use its generated Runner. The installer prepares tools, dependencies, the frontend and saved settings; the Runner starts the prepared application.

| Platform | Installer | Generated launcher | Guide |
| --- | --- | --- | --- |
| Windows x64 | `Install Windows.bat` | `Gravewright Runner.bat` | [Windows](docs/en/windows-runner.md) |
| Linux x64 / ARM64 | `bash "./Install Linux.sh"` | `Gravewright Runner.sh` | [Linux](docs/en/linux-runner.md) |
| macOS Intel / Apple Silicon | `Install macOS.command` | `Gravewright Runner.command` | [macOS](docs/en/macos-runner.md) |

The source distribution includes all three platform installers. The release identifiers are **`v0.3.2`** and **`Gravewright-0.3.2-django.zip`**, with a matching SHA-256 file. Managed installations can check the configured repository through **Administration → Updates → Check for updates**. Back up `.env`, configured data and local extensions first. For a manual upgrade, stop the Runner, replace application files while preserving configuration, data and extensions, then rerun the platform installer. See [upgrade and recovery](docs/en/upgrading.md) and the [release instructions](docs/releases/0.3.2.md#download-and-upgrade). This version adds seven migrations for campaign preparation, journal history, PDF mapping templates, clocks, clock descriptions, clues and mind maps relative to 0.3.1; run the normal migration workflow before starting the updated server.

Linux downloads use glibc-based distributions; Alpine/musl needs a compatible Node.js installation already available. The macOS installer targets macOS 13.5 or newer. Installation needs internet for missing tools/packages. Python 3.14, uv and Node.js are prepared privately when compatible tools are unavailable; no permanent PATH changes are made. All launchers use a local profile on `127.0.0.1`, with no Redis service required. See the platform guides for exact requirements and storage paths.

**Mac Intel also needs Apple's Command Line Tools and SDK.** Its first installation compiles the locked cryptography dependency using private Rust/OpenSSL tools, without Homebrew, and can take longer. Missing Apple tools open the system installer in interactive mode; finish it and rerun Gravewright's installer. Unattended `--check` reports the prerequisite instead. See the [macOS guide](docs/en/macos-runner.md) for the source-build support boundary and cache reuse.

### Windows

Extract the complete project and double-click **`Install Windows.bat`**. It installs missing tools, prepares dependencies and the frontend, asks for your settings, and generates **`Gravewright Runner.bat`**. Open the generated runner to start the application without installation or configuration questions. Run the installer again to change settings or prepare an updated project. Keep the runner window open while using Gravewright; press **Ctrl+C** to stop it.

The runner executes directly in **Windows CMD**. Use Windows 10 version 1803 or newer, or Windows 11, on x64; built-in `curl.exe`, `tar.exe` and `certutil.exe` handle downloads, extraction and integrity checks.

The installer saves settings in the project's `.env`. Database and upload paths follow that configuration; their defaults are `data/gravewright.sqlite3` and `data/media` in the project. Runner state, logs and collected assets stay under `data/`; managed tools, environments, caches and temporary files stay under `data/runner/` in this installation. The runner listens on the local computer and does not need a Redis server. A shortcut with the Gravewright icon is created beside the launcher. See the [Windows runner guide](docs/en/windows-runner.md) for requirements, backups and troubleshooting.

Before updating, stop the application and back up the configured database, private media and `.env` together. Managed installations can use Administration → Updates; source installations must install locked dependencies and run migrations. After moving or replacing a Windows project, rerun **`Install Windows.bat`** to prepare it and regenerate its runner. See [deployment and backups](docs/en/deployment.md).

### Linux and macOS

On Linux, open a terminal in the extracted folder and run `bash "./Install Linux.sh"`. On macOS, open **`Install macOS.command`** in Finder, or run `bash "./Install macOS.command"` from that folder. Answer the configuration questions, then start **`Gravewright Runner.sh`** or **`Gravewright Runner.command`**. Keep its terminal open; Ctrl+C stops the application. Run the installer again after moving the project, updating its files or changing saved settings.

Configuration remains in the project's `.env`; the default database and uploads remain `data/gravewright.sqlite3` and `data/media` in that project. Runner state, logs and collected assets stay under `data/`; managed tools, environments, caches and temporary files stay under `data/runner/` in this installation. `--data-dir` relocates Runner state, not the database/media settings in `.env`. The [Linux](docs/en/linux-runner.md) and [macOS](docs/en/macos-runner.md) guides cover unattended checks, offline reuse, permissions, updates and backups.

## Run locally from a terminal

Requirements: **Python 3.14 or newer**, [uv](https://docs.astral.sh/uv/), and a modern browser with WebGL support. Standard server settings require Redis when `DJANGO_DEBUG=false` and whenever multiple ASGI processes need to communicate. The generated Runners use a separate local profile; their installers manage Node.js/npm for frontend preparation. The terminal workflow below serves the committed assets; rebuilding them or running JavaScript tests requires Node.js.

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

Systems using `system.combat`, `content.compendiums` or the module modal API require **VTT 0.2.1 or newer**. These are additive host capabilities; the browser SDK remains **1.0.0**, and an SDK range alone does not establish support in older VTT releases. Systems and their content ship separately from the VTT; the 5e SRD system 0.1.0 is not included in this release.

For a quick check:

```bash
uv run --locked python manage.py check
uv run --locked python manage.py test config gravewright --noinput
node --test tests/modules/*.test.mjs tests/effects/*.test.mjs
```

The Django test runner uses `data/test-gravewright.sqlite3`; `--noinput` permits replacing that test database. Do not run concurrent suites against it. See [testing](docs/en/testing.md) for the full JavaScript suite, controlled environment settings and Playwright scenarios.

## Contribute

Read [CONTRIBUTING.md](CONTRIBUTING.md) and the [development guide](docs/en/development.md). English is the primary documentation language; Portuguese guides are maintained alongside it. Code comments and docstrings use English. The default interface language is English; the official [Translator](https://github.com/Gravewright/translator) supplies installable languages, including Portuguese and Spanish. Modules and systems register private catalogs through the host's translation API. User-authored content retains its original text.

Report ordinary bugs through the repository's issue tracker, including reproduction steps and relevant versions. Follow [SECURITY.md](SECURITY.md) for vulnerability reports.

## License

Gravewright's first-party code and documentation are licensed under **GNU GPL version 3 only (`GPL-3.0-only`)**, with the [independent module permission](LICENSE-EXCEPTION) under section 7. Independently written third-party modules may use **any license, including proprietary licenses**, whether or not they use the provided APIs. Copies and modifications of Gravewright core remain subject to GPL-3.0-only; naming copied core code a module does not change its license.

Read the [licensing policy](LICENSING.md), the unmodified [GPLv3 text](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md). Bundled dependencies, inherited assets and user-provided content retain their own applicable terms.
