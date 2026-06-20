# Desktop Distribution

How to ship the Gravewright desktop app to end users. The desktop build is a
self-contained PyInstaller one-dir bundle: it wraps Python, every dependency, and
the project itself, runs the server in-process, and shows it in a native window
via WebView2. Users **unzip and run** — no Python, no `uv`, no terminal.

The Portuguese version of this page is `pt-br/distribuicao-desktop.md`.

## 1. Build the bundle

The build is defined by `Gravewright.spec` at the repo root. From a checkout with
dev dependencies installed (`uv sync`):

```bash
uv run pyinstaller --noconfirm Gravewright.spec
```

Output: `dist/Gravewright/`, containing:

- `Gravewright.exe` — the launcher (double-click target, no console).
- `Gravewright-debug.exe` — identical app, but opens a console showing uvicorn
  logs and Python tracebacks. For diagnosing a broken launch; end users run the
  normal exe.
- `_internal/` — Python runtime, libraries, templates, static assets, schemas
  (shared by both exes).

`GravewrightData/` is **not** part of the build. It is created next to the exe on
first run and holds the SQLite database, installed packages, and uploads. Do not
ship it; do not commit it.

## 2. Package the ZIP

Ship the **entire `Gravewright` folder**. The exe does not run on its own — it
needs `_internal/` beside it. Keep that folder as the ZIP root so users extract a
single self-contained directory:

```powershell
Compress-Archive -Path dist/Gravewright -DestinationPath Gravewright-2.0.0-alpha.0-win64.zip
```

Name the file with the version and architecture, e.g.
`Gravewright-2.0.0-alpha.0-win64.zip`.

## 3. Publish

GitHub Releases is the recommended channel: free, versioned, direct download
links, and the release body holds the install instructions. Upload the ZIP as a
release asset and paste the instructions from the next section into the notes.

## 4. Ready-to-paste release notes

```markdown
## Install (Windows)

1. Download `Gravewright-<version>-win64.zip`.
2. Right-click the ZIP → **Extract All**.
3. Open the extracted `Gravewright` folder and run **Gravewright.exe**.
4. If Windows shows "Windows protected your PC": click **More info** →
   **Run anyway**. (The app is not code-signed yet, so this warning is expected.)

Your data (campaigns, uploads, installed packages) lives in the `GravewrightData`
folder created next to the app. Back it up to keep your games; delete it to start
fresh.

### Requirement: Microsoft WebView2 Runtime
The app uses Microsoft WebView2 to draw its window. It ships with up-to-date
Windows 10/11, so most users need nothing. If the window does not open, the app
will point you to the free download:
https://developer.microsoft.com/microsoft-edge/webview2/
```

## Configuration (`.env`)

The frozen app reads an optional `.env` placed **next to `Gravewright.exe`** (the
folder users extract). Values there take precedence over the built-in defaults, so
it is the supported way to configure an installed copy. Do not edit anything inside
`_internal/` — that folder is overwritten on every update.

```dotenv
# dist/Gravewright/.env  (optional)
APP_NAME=My Table
SESSION_SECRET=replace-with-a-long-random-string
```

Notes:
- A few values are fixed by the launcher and cannot be overridden via `.env`
  unless the launcher does not already set them: it pins `ALLOWED_HOSTS=*`
  (loopback-only window) and, when you do not set them yourself, `DATABASE_URL`
  and `GRAVEWRIGHT_DATA_DIR` (pointing at `GravewrightData/` next to the exe).
- If you override `GRAVEWRIGHT_DATA_DIR` or `DATABASE_URL`, use **absolute
  paths** — relative paths resolve against an internal folder, not the exe.
- Leaving `.env` absent is fine; the app runs with sensible local defaults.

## Notes and caveats

- **WebView2 Runtime** — bundled with current Windows 10/11. The launcher
  (`desktop.py`) detects when it is missing, shows a native dialog, and opens the
  Microsoft download page, so users are never left with a window that silently
  fails to appear.
- **SmartScreen** — unsigned executables trigger "Windows protected your PC".
  Users dismiss it with **More info → Run anyway**. To remove the warning,
  sign the exe with an Authenticode certificate (an EV certificate clears it
  immediately; a standard certificate builds reputation over time).
- **Antivirus false positives** — PyInstaller executables are occasionally
  flagged by heuristics. Code signing reduces this; report false positives to the
  vendor if they occur.
- **Per-platform builds** — a build produced on Windows runs on Windows only.
  Build on macOS/Linux for those platforms.

## Troubleshooting a broken launch

Run **`Gravewright-debug.exe`** — it opens a console with the live server logs and
any Python traceback, which is the fastest way to see why the normal exe failed.

Build-time gotcha: if a rebuild fails with `PermissionError [WinError 32] ... is
being used by another process` on `dist/Gravewright`, leftover `msedgewebview2.exe`
(WebView2) child processes from a previous run are holding the folder. Close the
app fully (or `taskkill /IM msedgewebview2.exe /F`) and rebuild.
