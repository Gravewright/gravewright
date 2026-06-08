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
- Persistent `GRAVEWRIGHT_DATA_DIR` if systems and modules are installed outside the repository.

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

`storage/` contains local SQLite when used, uploaded scene assets, actor assets, journal assets, chunk files, and system-scoped sheet JSON. `data/` contains installable systems and modules when `GRAVEWRIGHT_DATA_DIR` is not set elsewhere.

## Migrations

Run Alembic migrations as part of deployment:

```bash
alembic upgrade head
```

Startup can create missing runtime schema objects, but schema evolution should go through migrations.

## Health Check

The Docker test compose files use:

```bash
python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"
```

Production deployments may use `/` or `/login` through the reverse proxy, plus direct internal checks for the application port.
