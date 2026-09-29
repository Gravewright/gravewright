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

| Tool | Compatible existing installation | Private fallback |
| --- | --- | --- |
| uv | Version 0.12.0 or newer | Verified uv 0.12.13 |
| Python | CPython 3.14, Windows x64, standard GIL build | Managed `cpython-3.14-windows-x86_64-none`, validated after discovery |
| Node.js/npm | Stable Node.js 22 or 24 LTS x64, npm 10 or newer | Verified Node.js 24.19.0 with npm |

No administrator privileges, permanent PATH changes, Docker or Redis server are required. Reused tools must remain installed. Python dependencies use an isolated environment and `uv sync --locked --no-dev`. Frontend preparation runs `npm ci --include=dev --include=optional` when required, then `npm run build`; input/output hashes allow unchanged assets to be reused. Installation updates generated assets and ignored `node_modules` in the source folder.

## Configuration and personal data

The installer asks for table name, language (`en` or `pt-BR`), local port, modules folder, join codes, campaign snapshots and campaign exports. It saves the answers together, preserving the secret and unrelated settings. On subsequent installations the saved answers are the defaults. Relative modules paths start at the personal data directory.

It also offers the default Gravewright Marketplace once. Accepting downloads the official public keys, verifies their SHA-256 and saves the catalog settings. Declining records the choice; the owner can still install it under Settings → Marketplace. Deleting `data/.default-marketplace-choice` allows the installer to offer it again.

Personal files default to **`%LOCALAPPDATA%\Gravewright`**:

| Path | Purpose |
| --- | --- |
| `data/.env` | Private secret and saved configuration |
| `data/gravewright.sqlite3` | Accounts and campaigns |
| `data/media/`, `data/compendiums/` | Private files and local content |
| `data/staticfiles/` | Collected public assets |
| `data/logs/runner.log` | Startup/runtime diagnostics |
| `data/runner.lock` | Prevents concurrent use of the same data |
| `runner/` | Downloaded tools, caches and environments per source location |
| `runner/prepare.lock` | Prevents simultaneous dependency preparation |
| `runner/frontend/<source-location-hash>/state.json` | Frontend preparation state |

The source checkout's `.env`, `.venv` and development database are separate. Defaults come from `.env.example`, then the personal `.env`; local network/security/storage bounds are enforced by the runner. The secret is generated automatically. Stop the server before changing settings or backing up the entire personal `data` directory. Preserve the secret, database and media together. Back up before installing a new version, since migrations can make older source versions incompatible.

## Local execution boundary

The runner serves HTTP only on `127.0.0.1`, with one server process and in-memory Channels. Django debug stays disabled; origin, host, session, CSRF and campaign permissions remain active. Private uploads use guarded application routes. For LAN or internet access, follow [deployment](deployment.md) with the standard ASGI profile. Do not expose the local runner through a tunnel or public reverse proxy.

## Diagnostics and validation

For unattended installation with defaults, without configuration questions or server startup:

```bat
"Install Windows.bat" --check --no-pause --data-dir "%TEMP%\Gravewright Install Check"
```

This installs dependencies, prepares assets/database and generates a runner pointing at the selected data directory. It is not read-only. A later normal installation asks the questions. `--data-dir` chooses the stored data directory; `--port` overrides only the installation check, not the saved port.

The generated runner accepts `--no-browser`, `--no-pause`, `--data-dir`, `--port` and `--check`. Runner `--check` checks the application/database without tool installation or frontend preparation; it can apply migrations and collect static assets. `--port` applies only to that run. To configure saved values, open the installer.

For download failures, inspect the console and connectivity to GitHub, nodejs.org and package sources. Do not bypass checksum failures. If an older launcher reports `No download found` for `cpython-3.14+gil-windows-x86_64-none`, use the complete updated project. If files or the prepared Python are missing, run the installer again. If the port is occupied, stop the other server or change the saved port. For application failures, inspect `data/logs/runner.log` and redact private information before sharing it.

The installer owns tool/dependency preparation. [create_runner.py](../../scripts/windows/create_runner.py) generates the startup BAT from its [template](../../scripts/windows/runner.bat); [create_shortcut.py](../../scripts/windows/create_shortcut.py) creates the optional icon shortcut. [gravewright_runner.py](../../scripts/gravewright_runner.py) owns personal settings, locking and server lifecycle. See [testing](testing.md): the native Windows harness covers installation, reconfiguration, private Python downloads, offline reuse and the generated runner. Browser validation is separate when `--skip-browser` is used.

## Updates and rollback

Updates replace the project files in place, including the installer, and regenerate the runner with the new Python environment. In Administration → Updates, **Keep a .old copy for rollback** controls whether the old code and matching data snapshot are retained after success. Temporary recovery remains available during installation. See [deployment](deployment.md) for restoration instructions.

The runner executes an immutable launcher copy under `data/.runner-launchers`, allowing the project BAT to be safely replaced during an update. Preserve that folder together with personal data and backups.
