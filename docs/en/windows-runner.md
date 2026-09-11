# Gravewright Runner for Windows

[Documentation](../README.md) · [Português](../pt-BR/windows-runner.md)

**Gravewright Runner** detects installed tools, prepares the application and starts Gravewright on your own Windows computer. It keeps campaigns and settings outside the source folder, so replacing the application files does not remove your personal data.

## Start with two clicks

1. Use **Windows 10 version 1803 or newer, or Windows 11, on x64/AMD64**, with the built-in `curl.exe`, `tar.exe` and `certutil.exe` tools and a modern browser with WebGL. This launcher does not support 32-bit Windows or Windows on ARM.
2. Extract the **complete project ZIP** to a local folder you can write to. Do not run it inside the ZIP or copy only the `.bat` file.
3. Double-click **`Gravewright Runner.bat`**. It checks installed uv, Python and Node.js/npm and shows the selected paths and versions. Internet access is needed to download missing tools or dependencies.
4. Wait for the runner to install dependencies, build the frontend when needed, prepare the database and open the browser. The default address is **http://127.0.0.1:3000**.
5. Create the first owner account on the setup page. On later launches, sign in with the same account. See the [user guide](user-guide.md) for campaigns and the tabletop.

Compatible tools already installed are reused. Only missing or incompatible tools require a separate local installation for your Windows user; the runner does not upgrade or replace your existing tools, require administrator privileges or permanently change your `PATH`. Python application dependencies stay in the runner's isolated environment. Docker and a Redis server are not required.

The `.bat` runs directly in Windows CMD and owns tool detection, downloads, dependency installation, the npm build commands and application startup. It uses the native Windows download/archive/checksum utilities and then invokes the selected Python and Node executables.

Keep the console window open while using Gravewright. **Press Ctrl+C in that window to stop the server.** Closing the browser does not stop it. Wait for the runner to exit before replacing application files or backing up data. If startup fails, the `.bat` keeps its error message visible.

## Tool detection and frontend preparation

| Tool | Compatible existing installation | If none is available |
| --- | --- | --- |
| uv | Version **0.12.0 or newer** available to the launcher | Download the pinned **0.12.13** build and verify its integrity |
| Python | **CPython 3.14**, Windows x64, standard GIL build; discovered through uv, including installed/system and shared managed interpreters | Download a private managed Python 3.14 |
| Node.js and npm | Stable **Node.js 22 or 24 LTS**, x64, with working **npm 10 or newer** | Download the verified **Node.js 24.19.0** Windows package with npm |

The console reports which installation is reused or downloaded. Python is used through an isolated dependency environment, even when its base interpreter comes from an existing installation. Keep reused tools installed while using this runner environment.

The runner checks and synchronizes Python runtime dependencies with `uv sync --locked --no-dev`. For npm, it can reuse an existing dependency installation when required package versions match the lock and a real esbuild check succeeds. Otherwise, or when the recorded dependency inputs change, it runs `npm ci --include=dev --include=optional`, including esbuild. It then executes `npm run build` when preparation is required. This uses the committed npm project under `gravewright/maps/frontend` and rebuilds the generated assets used by the application.

The frontend is built on first preparation and when its inputs change. Subsequent launches check the recorded input and output hashes and skip an unchanged valid build; missing or changed generated outputs trigger another build. The source folder must be writable because preparation updates generated static assets. See [frontend](frontend.md) for the source-to-output mapping. This process does not download newer Gravewright source or run the browser-test suite.

## Project icon and shortcut

The launcher attempts to create **`Gravewright Runner.lnk`** beside the `.bat`, using the Gravewright mark as its icon. Double-click either file to start. The `.bat` itself uses the Windows batch-file icon; the generated shortcut carries the project icon. No shortcut is added to the desktop automatically.

The [icon source note](../../scripts/windows/ICON-NOTICE.md) records its conversion from the existing application styles and the preserved original UI license.

If the source folder does not allow shortcut creation, startup continues and reports the failure. Move the extracted project to a writable folder and launch the `.bat` again to create the shortcut. After moving the project, use the `.bat` in its new location to refresh the shortcut target.

## Where your files are stored

Paste **`%LOCALAPPDATA%\Gravewright`** into File Explorer's address bar. The runner uses these paths for your Windows account:

| Path under that folder | Purpose |
| --- | --- |
| `data\.env` | Persistent secret, port and optional feature configuration |
| `data\gravewright.sqlite3` | Accounts, campaigns and application state |
| `data\media\` | Private uploads and installed modules |
| `data\compendiums\` | Local compendium content |
| `data\staticfiles\` | Generated public application assets; rebuilt by the runner |
| `data\logs\runner.log` | Rotating runtime and startup diagnostics |
| `data\runner.lock` | Lock preventing two runner processes from using the same data |
| `runner\` | Tools downloaded only when needed, package caches and isolated Python environments for each source location |
| `runner\prepare.lock` | Windows file handle lock preventing simultaneous tool/dependency preparation; released automatically when preparation ends |
| `runner\frontend\<source-location-hash>\state.json` | Frontend preparation state used to verify tool versions, inputs and generated outputs |

The source checkout's `.env`, `.venv` and `data/` are separate and remain untouched by this workflow. Frontend preparation updates the project's generated static assets and the ignored npm dependency directory `gravewright/maps/frontend/node_modules`. Existing campaigns created with `main.py` do not appear automatically in the runner's separate database. Use campaign export/import where suitable, or deliberately migrate the complete database and matching media with both servers stopped and backups retained.

All copies of the launcher used by the same Windows account share the default personal data directory. They do not represent independent installations of your campaigns. The runner checks its data lock and the chosen port before database preparation; it does not terminate another program to free the port.

## Settings and backups

Stop the runner before editing **`data\.env`**. To change the default port, edit its `GRAVEWRIGHT_PORT=3000` entry, for example to `GRAVEWRIGHT_PORT=3001`, then launch again. The browser address changes with the port. Keep the generated `DJANGO_SECRET_KEY` private and preserve it across launches and restores.

The runner loads defaults from the supplied `.env.example`, then your personal `.env`. Feature options described in the [configuration guide](configuration.md) can be added there. The local profile enforces its own bind address, storage paths, debug, cookie, host/origin, proxy and Channels settings; changing server deployment variables does not turn the runner into a network server. The source `.env` is not loaded.

For a backup, stop Gravewright and copy the **entire `data` folder** to a safe location. Keep the secret, database and private files together. Before installing a newer project version, retain a backup that matches the previous source version: startup applies database migrations, which can make an older version incompatible with the updated database.

Updates are manual: stop the runner, back up the data, extract the new complete source and run its `.bat`. The new launch checks the available tools, synchronizes dependencies against that version's Python/npm locks, prepares the frontend and applies migrations. It does not download new Gravewright source automatically. Removing the source folder or the disposable `runner` tools folder does not uninstall your campaigns; removing the `data` folder does.

## Local execution boundary

The runner serves **HTTP only on `127.0.0.1`**, with one Daphne process and an in-memory Channels layer. Django debug remains disabled. Browser origin, host, session, CSRF and campaign-permission checks remain active, and private uploads use the application's guarded routes. Only collected public assets are served directly.

This profile is for the computer running the launcher. For other players connecting from another computer, a LAN service, HTTPS or an internet-facing instance, follow [deployment](deployment.md) and configure the standard ASGI application, Redis and storage separately. Do not expose the runner through a tunnel or public reverse proxy.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Missing project files | Extract the complete source ZIP; keep the `.bat`, `scripts`, `config`, application folders and lockfile together |
| Download or dependency installation fails | Read the error in the runner console; confirm access to GitHub releases, nodejs.org and the Python/npm package URLs used by the lockfiles, then launch again |
| A tool integrity check fails | Do not bypass the check; retry from a fresh project copy and inspect the reported download or cached-file problem |
| Frontend preparation fails | Read the npm/build error in the runner console and confirm that the extracted project folder is writable |
| A Windows download/archive/checksum utility is missing | Use a supported Windows installation with `curl.exe`, `tar.exe` and `certutil.exe` available; read the missing-tool name reported by the runner |
| Another instance is running | Use the existing runner window, or stop that instance with Ctrl+C before trying again |
| Port is already in use | Stop your other local server or change `GRAVEWRIGHT_PORT` in the personal `.env` |
| Browser does not open | Open the exact address printed by the runner once it reports readiness |
| Old campaigns are missing | Check whether they were created in the source checkout's database or under another Windows account |
| Application startup fails | Inspect `data\logs\runner.log`; redact secrets, account details and private paths before sharing diagnostics |

## Implementation and validation

[`Gravewright Runner.bat`](../../Gravewright%20Runner.bat) detects compatible installations, downloads missing tools with `curl.exe`, extracts archives with `tar.exe` and verifies checksums with `certutil.exe`. The `uv sync`, `npm ci` and `npm run build` commands are implemented in the batch file. [`scripts/prepare_frontend.py`](../../scripts/prepare_frontend.py) provides `--plan` and `--record` operations for checking dependencies, fingerprints and generated outputs; the batch file supplies the selected tool paths and per-source state directory. The [shortcut helper](../../scripts/windows/create_shortcut.py) uses Python's standard library and Windows COM to create the `.lnk`. See [third-party notices](../../THIRD_PARTY_NOTICES.md) for the licensing scope of reused and downloaded tools.

[`scripts/gravewright_runner.py`](../../scripts/gravewright_runner.py) owns configuration, the data lock, database migrations, static collection, readiness checks, browser launch and the server lifecycle. It supports `--data-dir PATH`, `--port NUMBER`, `--no-browser` and `--check` for controlled developer runs with an already prepared environment. `--port` overrides the current run without editing the stored configuration; `--check` prepares and checks the installation, including migrations and static collection, then exits without serving requests. It is not a read-only check.

The `.bat` supports the same `--data-dir`, `--port`, `--no-browser` and `--check` options when tool detection, dependency installation and frontend preparation are also needed. Double-click it for ordinary startup, or pass arguments in Windows CMD. For example, from the source root, prepare an isolated diagnostic directory without starting the server:

```bat
"Gravewright Runner.bat" --check --data-dir "%TEMP%\Gravewright Runner Check"
```

The example data directory is separate from your normal campaigns and can be removed after the check. `--check` still prepares dependencies and generated frontend assets in addition to the database; it is not a read-only command. Add `--no-pause` for CI or scripted use so failures return an exit code instead of waiting for a key press. Download/install/build diagnostics appear in the console; the batch file does not create a transcript automatically. Application diagnostics are written to `data\logs\runner.log`.

The dedicated settings and ASGI entry points are [`config/runner.py`](../../config/runner.py), [`config/runner_asgi.py`](../../config/runner_asgi.py) and [`config/runner_urls.py`](../../config/runner_urls.py). Standard server entry points keep their Redis requirement with debug disabled. Follow [testing](testing.md) for validation before distributing a Windows release, including a real Windows launch; tests on another operating system do not verify Windows shell, shortcut or console behavior.
