# Deployment

Gravewright is designed for self-hosted deployment. Production should use PostgreSQL and a single application worker in V1.

## Production Requirements

- HTTPS termination.
- `APP_ENV=production`.
- `APP_DEBUG=false`.
- `WEB_WORKERS=1`.
- Strong `SESSION_SECRET`.
- Explicit `PUBLIC_BASE_URL`.
- Explicit `ALLOWED_HOSTS`.
- `SESSION_COOKIE_SECURE=true`.
- `SESSION_COOKIE_HTTPONLY=true`.
- PostgreSQL `DATABASE_URL`.
- Persistent `storage/` volume.
- Persistent `GRAVEWRIGHT_DATA_DIR` if SDK packages are installed outside the repository.

## Why One Worker

V1 realtime fan-out, diagnostics, metrics, and in-process connection tracking do not cross process boundaries. Production startup refuses `WEB_WORKERS>1` to avoid silent multiplayer breakage. Scale vertically until a multi-process transport is implemented.

## Minimal Environment

```env
APP_ENV=production
APP_DEBUG=false
WEB_WORKERS=1
PUBLIC_BASE_URL=https://gravewright.example
ALLOWED_HOSTS=gravewright.example
WS_ALLOWED_ORIGINS=https://gravewright.example
SESSION_SECRET=<random 32+ character secret>
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=lax
DATABASE_URL=postgresql+psycopg://gravewright:<password>@db:5432/gravewright
DATABASE_ECHO=false
GRAVEWRIGHT_DATA_DIR=/var/lib/gravewright/data
```

## Reverse Proxy

Forward:

- `Host`
- `X-Forwarded-For`
- `X-Forwarded-Proto`
- WebSocket upgrade headers for `/game/ws`

Configure `TRUSTED_PROXIES` for your proxy addresses.

## Storage Volumes

Persist:

```text
storage/
data/ or GRAVEWRIGHT_DATA_DIR
```

`storage/` contains local SQLite when used, uploaded scene assets, actor assets, journal assets, chunk files, and package-scoped sheet JSON. `data/` contains installable SDK packages when `GRAVEWRIGHT_DATA_DIR` is not set elsewhere.

## Docker Compose

The repository ships a root `docker-compose.yml` for a quick single-host run:

```bash
docker compose up -d --build   # open http://localhost:8000
docker compose logs -f
docker compose down            # stop; data is kept in named volumes
```

It builds the image from `Dockerfile`, runs one worker, uses SQLite, and
persists data in the named volumes `gravewright-storage` (`/app/storage`) and
`gravewright-data` (`/app/data`). The default settings serve over plain HTTP for
local/self-hosted use.

Before exposing it to the internet, override the environment in
`docker-compose.yml` (or via the shell/`.env`) for production:

- set a strong `SESSION_SECRET` (`python -c "import secrets; print(secrets.token_urlsafe(48))"`);
- set `SESSION_COOKIE_SECURE=true` and terminate HTTPS at a reverse proxy;
- set `ALLOWED_HOSTS`, `PUBLIC_BASE_URL`, and `WS_ALLOWED_ORIGINS` to your domain.

PostgreSQL is recommended for public installs; it requires building the image
with the `postgres` extra (`psycopg`), which the default image does not include.

## Migrations

Alembic is the authority for schema creation and evolution. In production the
application **refuses to start against a database that is behind head** (it
reports the current and expected revisions) unless `AUTO_MIGRATE=true` is set —
it will not silently `create_all`. Back up first, then upgrade as part of
deployment:

```bash
grave backup -o pre-upgrade.zip --include-packages --verify   # then test a restore
grave db status                                               # current vs expected head
grave db upgrade                                              # alembic upgrade head
```

`grave run` performs `grave db upgrade` automatically before serving. Set
`AUTO_MIGRATE=true` if you want a directly-launched production server to migrate
on startup instead of failing fast. Local development bootstraps the schema from
metadata for convenience, but that is **not** the supported upgrade path. See
[`adr/ADR-migration-baseline.md`](adr/ADR-migration-baseline.md).

### Recovery

If an upgrade goes wrong:

1. Stop the application.
2. Restore the pre-upgrade backup into a throwaway data dir and verify it starts:
   `grave restore pre-upgrade.zip --dry-run`, then restore for real.
3. Re-run `grave db status` to confirm the restored revision, and only retry the
   upgrade once the cause is understood.

## Health Check

The Docker test compose files use:

```bash
python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"
```

Production deployments may use `/` or `/login` through the reverse proxy, plus direct internal checks for the application port.
