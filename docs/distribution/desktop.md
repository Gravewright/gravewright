# Optional Windows UI distribution

Gravewright Core and Gravewright Windows UI are separate products. The standard
Core installation provides the server, web application, and `grave` operator CLI.
It has no PySide6 or Qt dependency and does not load a native desktop interface.

The optional Windows UI is maintained and built from the separate
`gravewright-windows-ui` project. It discovers a separately installed Core and
uses only the public `grave` CLI plus local HTTP readiness. It never imports Core
modules, reads the database, or writes the Core data directory directly.

## Official Windows Core ZIP

The recommended Core release is source-based and has the minimal console
`Gravewright.exe` at the ZIP root. Build it with:

```powershell
uv run python scripts/build_windows_release.py
```

The launcher definition is `packaging/windows-launcher.spec`. It freezes only
standard-library bootstrap/orchestration code and contains no Core, web, database,
Qt, or PySide6 modules. The ZIP contains `Gravewright.exe`, `pyproject.toml`,
`uv.lock`, and the Core source/assets required by `uv sync --frozen`.

On first run it finds or installs verified `uv 0.9.11`, prepares the locked
environment, delegates configuration and Doctor to the existing Core commands,
then runs `grave run --open`. `grave.spec` remains an alternative maintainer build
for a fully frozen CLI bundle; it is not the one-click source ZIP launcher.

## Optional UI

Build and release the Windows UI independently from its own repository. It may be
placed beside a `Gravewright Core` directory, located through `PATH` or
`GRAVEWRIGHT_COMMAND`, or selected by the user. Its release lifecycle and future
updater are independent from Core updates.

The UI currently preserves server start/stop, readiness, browser opening, logs,
Doctor, Backup, Restore, and package commands. Shutdown begins with a graceful
console signal and uses forced termination only as a timeout fallback.
