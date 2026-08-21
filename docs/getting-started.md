# Getting Started

## Requirements

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- A browser with modern JavaScript support

SQLite is used by default for local development.

## Easy Install (Installers)

For non-technical users, one-click installers set everything up: including the
correct Python version (via `uv`), and then launch Gravewright in your browser.
No administrator rights are required.

- **Windows:** extract the official ZIP and double-click `Gravewright.exe`.
  The executable includes its own minimal Python runtime and does not require
  Python or administrator access. `install-windows.bat` is a debug fallback.
- **macOS / Linux:** run `bash install-macos-linux.sh` in this folder.

The Windows launcher installs a checksum-verified, pinned official `uv` binary
when needed. Each installer installs the pinned dependencies with
`uv sync --frozen`, creates `.env` with a unique `SESSION_SECRET`, runs
diagnostics, and starts the server at `http://127.0.0.1:8000`. Run the same file
again any time to play later. The steps below are the manual path.

## Run with Docker

With [Docker](https://docs.docker.com/get-docker/) installed:

```bash
docker compose up -d --build
```

Open `http://localhost:8000`. Your data persists in named Docker volumes. Stop
with `docker compose down`. See `docker-compose.yml` and the deployment guide
for hardening notes before exposing it publicly.

## Install Dependencies

```bash
uv sync
```

## Configure Local Environment

```bash
cp .env.example .env
```

The default `.env.example` is suitable for local development. Change `SESSION_SECRET` before using any shared or public instance.

## Run Diagnostics

```bash
chmod +x grave
./grave doctor
```

Fallback:

```bash
uv run python -m app.cli doctor
```

## Start the App

```bash
./grave run --open
```

Fallback:

```bash
uv run python -m app.cli run --open
```

Open:

```text
http://127.0.0.1:8000
```

Windows:

```bat
grave.bat doctor
grave.bat run --open
```

## Database Schema

`grave run` creates and upgrades the database through the official Alembic path
(`alembic upgrade head`) before starting the server, so you normally don't touch
migrations directly. To inspect or drive it yourself:

```bash
grave db status    # current revision, expected head, up-to-date?
grave db upgrade   # alembic upgrade head (back up first)
```

Local development bootstraps the schema from metadata for convenience, but that
is not the supported upgrade mechanism: always evolve real data with
`grave db upgrade` / `alembic upgrade head`. See
[`database.md`](database.md) and [`adr/ADR-migration-baseline.md`](adr/ADR-migration-baseline.md).

## First Local Flow

1. Register a local user.
2. Open `/inside`.
3. Create a campaign.
4. Open the campaign and use **Entry code** in Settings to generate a code for
   players. Share either the code or `/join/<code>`; players can enter it from
   Inside without sharing an email address. The full code is shown only once.
   Email invitations remain visible as a legacy compatibility flow during the
   transition release.
5. Check package availability:

   ```bash
   ./grave package list
   ```

6. Install and enable a ruleset package if needed:

   ```bash
   ./grave package install <ruleset-id> --yes --enable
   ```

   You can also install a ruleset or add-on without the CLI: as the owner, open
   **Inside > Add-ons** and upload its `.zip` package. Tick "Replace existing" to
   overwrite a package with the same id. Uploaded packages are installed; enable
   them from the same screen.

7. Assign the ruleset to the campaign from the UI or package activation flow.
8. Open the campaign table.
9. Upload a map from the Scenes panel.
10. Create actors, items, journals, and tokens.

## Back Up Before Updating

Before updating Gravewright or changing packages on a table you care about:

```bash
./grave doctor
./grave backup -o gravewright-backup.zip --include-assets --verify
```

Test restore on a copy before updating real data.

## Local Data

Default runtime files live under:

```text
storage/
```

Default package data lives under:

```text
data/packages/
```

Set `GRAVEWRIGHT_DATA_DIR` if installable SDK packages should live outside the repository.
