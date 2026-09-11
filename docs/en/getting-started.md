# Getting started

[Documentation](../README.md) · [Português](../pt-BR/getting-started.md)

On Windows, the [Gravewright Runner](windows-runner.md) detects and reuses installed tools, installs missing prerequisites, prepares Python/npm dependencies and the frontend build, then starts the local application with two clicks. The terminal workflow below is for a source checkout with manually managed configuration.

## Prerequisites

Use Python 3.14 or newer as required by [pyproject.toml](../../pyproject.toml). The project uses Python 3.14 syntax; selecting an older interpreter is not supported. Install uv using its [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/). Run the following commands from the directory containing `manage.py`.

```bash
uv sync --locked
cp -n .env.example .env
uv run --locked python manage.py migrate
uv run --locked python main.py
```

`uv sync` includes the development dependency group. The lock file supplies the reproducible package versions. This terminal workflow serves the existing JavaScript and CSS assets. To rebuild them, use the npm project under `gravewright/maps/frontend` as described in [frontend](frontend.md); the Windows runner performs that preparation automatically. In Windows CMD, replace the copy command with `if not exist .env copy .env.example .env`.

## First access

Open `http://127.0.0.1:3000`. Before an owner exists, `/setup` creates the VTT owner and signs in. Choose a name, email and a password of at least 12 characters. `/register` creates participant accounts after setup; `/login` signs in existing users.

The owner can create campaigns through `/inside`, invite players and enter the table. Campaign membership determines GM/player permissions. See the [user guide](user-guide.md).

If you need Django's separate `/admin/` interface:

```bash
uv run --locked python manage.py createsuperuser
```

This creates an administrative account, not a VTT owner. Do not use it as a replacement for `/setup`.

## Files and settings

`.env` is optional and loads automatically. Exported process variables take precedence; `${NAME}` in `.env` remains literal. Restart the server after changing settings. See the complete [configuration reference](configuration.md).

| Path | Purpose |
| --- | --- |
| `.env` | Local configuration and private secrets |
| `data/gravewright.sqlite3` | Default application database |
| `data/media/` | Default private uploads and installed module packages |
| `data/vtt/compendiums/` | Optional native content collections read from disk |
| `staticfiles/` | Output of `collectstatic`; regenerated for deployment |
| `data/test-gravewright.sqlite3` | Django test database |
| `test-results/` | Browser test logs, reports and screenshots |

If you override database/media paths, create their parent directories and ensure the service account can write to them. Normal local development uses a single ASGI process and an in-memory Channels layer. Public hosting and multiple workers require additional setup; see [deployment](deployment.md).

## Common problems

| Symptom | Check |
| --- | --- |
| Missing table / `no such table` | Run migrations against the intended `GRAVEWRIGHT_DATABASE` |
| Existing campaigns appear missing | Confirm the database path; root `db.sqlite3` is not the configured default |
| Startup rejects a setting | Read the named variable; booleans and limits are validated |
| Startup requests a secret or Redis | Standard server settings with `DJANGO_DEBUG=false` require a persistent secret and Redis URL; the Windows runner has a separate local profile |
| Login works but cookies disappear on local HTTP | Clear `GRAVEWRIGHT_PUBLIC_ORIGIN` and disable `DJANGO_SECURE_COOKIES` for local HTTP; start a fresh browser session |
| Invalid host or WebSocket rejection | Match the browser URL to `GRAVEWRIGHT_PUBLIC_ORIGIN`, including its port; check allowed hosts and trusted proxy headers in [deployment](deployment.md) |
| Port 3000 is occupied | Set `GRAVEWRIGHT_PORT` or run `manage.py runserver 127.0.0.1:3001` |
| Changes are not visible across processes | Configure all processes with the same Redis channel layer |
| Blank board or render failures | Check browser console, WebGL availability and asset/network errors |

For contributor checks and browser setup, continue to [testing](testing.md).
