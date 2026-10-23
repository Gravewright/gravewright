# Windows installation and Gravewright Runner

[Documentation](../README.md) · [Português](../pt-BR/windows-runner.md)

## Install, configure, then run

1. Extract the complete project ZIP into a writable local folder. Use Windows 10 version 1803 or newer, or Windows 11, on x64/AMD64, with `curl.exe`, `tar.exe`, `certutil.exe` and a modern WebGL browser. ARM and 32-bit Windows are not supported by this installer.
2. Double-click **`Install Windows.bat`**. It detects compatible tools, downloads missing tools, installs locked dependencies and builds the frontend when needed. Internet is required for missing downloads.
3. Answer the configuration questions. Enter keeps the displayed value; Ctrl+C cancels without saving the answers. The installer then prepares the database and generates **`Gravewright Runner.bat`** beside itself, plus an optional icon shortcut.
4. Open **`Gravewright Runner.bat`** or its shortcut to start the application. It uses the prepared Python environment and saved settings, without downloading tools, installing dependencies, rebuilding the frontend or asking configuration questions. The default address is **http://127.0.0.1:3000**.
5. Create the first owner account in the browser. Keep the runner console open; press **Ctrl+C** to stop the server. Closing the browser does not stop it.

The installer finishes without starting the server. Run it again whenever you want to change settings, repair missing dependencies or prepare a new project version. It reuses compatible tools and unchanged frontend assets. The runner is generated for this Windows installation; do not distribute it to another computer. After moving or replacing the project, run the installer in the new folder to regenerate the runner and shortcut.

## Tools and preparation

| Tool | Installation-local managed tool |
| --- | --- |
| uv | Verified uv 0.12.13 |
| Python | Managed CPython 3.14, Windows x64, standard GIL build |
| Node.js/npm | Verified Node.js 24.19.0 with npm |

No administrator privileges, permanent PATH changes, Docker or Redis server are required. The installer reuses verified tools in this installation and does not depend on tools in another OS profile. Python dependencies use an isolated environment and `uv sync --locked --no-dev`. Frontend preparation runs `npm ci --include=dev --include=optional` when required, then `npm run build`; input/output hashes allow unchanged assets to be reused. Installation updates generated assets and ignored `node_modules` in the source folder.

## Configuration and personal data

The project `.env` includes every setting and section from `.env.example`. Missing settings are filled automatically, preserving saved values, the private secret and custom options.

The installer asks for table name, language (`en` or `pt-BR`), local port, modules folder, join codes, campaign snapshots, campaign exports and whether to allow tunnels. The tunnel option is a single yes/no choice; no URL is requested. It saves the answers together, preserving the secret and unrelated settings. On subsequent installations the saved answers are the defaults. Relative database, media and modules paths start at the project root.

Selecting `pt-BR` automatically installs and globally activates the official signed [Translator](https://github.com/Gravewright/translator). A missing or unverifiable translation is an installation error; an installed, verified package is reused offline. The official signing keys are added without removing existing trusted keys.

Before preparing the Translator, the installer configures the official Gravewright Marketplace automatically when no catalog is configured, including installations that previously declined it. It verifies the official public keys and saves the catalog settings without an extra question. Existing custom catalogs are preserved; custom key files are kept intact, with any required official keys added to a managed copy. A complete, verified official configuration is reused offline on later installations. Unattended `--check` does not configure the Marketplace.

The database and media use `GRAVEWRIGHT_DATABASE` and `GRAVEWRIGHT_MEDIA_ROOT` from the project `.env`, defaulting to `data/gravewright.sqlite3` and `data/media` in the project. Runner state, collected assets, managed tools and caches also stay **inside the extracted project folder**:

| Path | Purpose |
| --- | --- |
| `data/compendiums/` | Local content |
| `data/staticfiles/` | Collected public assets |
| `data/logs/runner.log` | Startup/runtime diagnostics |
| `data/runner.lock` | Prevents concurrent use of the same data |
| `data/marketplace/<source-location-hash>/trusted-keys.json` | Managed official and retained publisher public keys, when needed |
| `data/runner/` | Downloaded tools, caches and environments per source location |
| `data/runner/prepare.lock` | Prevents simultaneous dependency preparation |
| `data/runner/frontend/<source-location-hash>/state.json` | Frontend preparation state |

The installer creates and reads `.env` in the project root, next to `Install Windows.bat`. If it does not exist, a complete configuration is generated from `.env.example` with a new private secret. Configuration files in user-data directories are never imported. Python environments are managed separately. Defaults come from `.env.example`, then the project `.env`; local network/security bounds are enforced by the runner. The secret is generated automatically. Stop the server before changing settings or backing up the project `.env` and the entire personal `data` directory. Preserve the secret, database and media together. Back up before installing a new version, since migrations can make older source versions incompatible.

## Local execution boundary

The runner serves HTTP only on `127.0.0.1`, with one server process and in-memory Channels. Django debug stays disabled; origin, host, session, CSRF and campaign permissions remain active. Private uploads use guarded application routes. Set `GRAVEWRIGHT_ALLOW_TUNNELS=true` to accept any tunnel hostname through a local agent, with no URL registration or provider restriction. HTTP and HTTPS origins follow each request Host; WebSockets and CSRF still require a matching origin. The server keeps listening on `127.0.0.1:<port>` and trusts scheme headers only from local agents. Changing tunnel URLs requires no configuration change. Set the flag to `false` to restrict access to the local host. The Runner does not install or start tunnel software. For direct LAN or internet hosting, use [deployment](deployment.md).

## Diagnostics and validation

For unattended installation with defaults, without configuration questions or server startup:

```bat
"Install Windows.bat" --check --no-pause --data-dir "data\check"
```

This installs dependencies, prepares assets/database and generates a runner pointing at the selected state directory. It is not read-only. A later normal installation asks the questions. `--data-dir` changes Runner state, logs and collected assets; the database and uploads still follow project `.env`. For isolated checks, use a disposable project copy with separate database/media configuration as well. `--port` overrides only the installation check, not the saved port.

The generated runner accepts `--no-browser`, `--no-pause`, `--data-dir`, `--port` and `--check`. Runner `--check` checks the application/database without tool installation or frontend preparation; it can apply migrations and collect static assets. `--port` applies only to that run. To configure saved values, open the installer.

For download failures, inspect the console and connectivity to GitHub, nodejs.org and package sources. Do not bypass checksum failures. If an older launcher reports `No download found` for `cpython-3.14+gil-windows-x86_64-none`, use the complete updated project. If files or the prepared Python are missing, run the installer again. If the port is occupied, stop the other server or change the saved port. For application failures, inspect `data/logs/runner.log` and redact private information before sharing it.

The installer owns tool/dependency preparation. [create_runner.py](../../scripts/windows/create_runner.py) generates the startup BAT from its [template](../../scripts/windows/runner.bat); [create_shortcut.py](../../scripts/windows/create_shortcut.py) creates the optional icon shortcut. [gravewright_runner.py](../../scripts/gravewright_runner.py) owns personal settings, locking and server lifecycle. See [testing](testing.md): the native Windows harness covers installation, reconfiguration, private Python downloads, offline reuse and the generated runner. Browser validation is separate when `--skip-browser` is used.

## Updates and rollback

The **0.3.2** release uses **`Gravewright-0.3.2-django.zip`** and its matching checksum. It adds database migrations for clocks, clues, campaign preparation and journal history. Follow [upgrading](upgrading.md) before installing it. A manual upgrade requires the complete archive and another run of **`Install Windows.bat`**, preserving `.env`, `data/` and explicit storage overrides. Same-version reissues require manual installation because discovery compares version numbers.

Updates replace the project files in place, including the installer, and regenerate the runner with the new Python environment. In Administration → Updates, **Keep a .old copy for rollback** controls whether the old code and matching data snapshot are retained after success. Temporary recovery remains available during installation. See [deployment](deployment.md) for restoration instructions.

The runner executes an immutable launcher copy under `data/.runner-launchers`, allowing the project BAT to be safely replaced during an update. Preserve that folder together with personal data and backups.
