# Configuration

Gravewright reads environment variables through `app/config.py`. Environment files are loaded according to `APP_ENV`, and local `.env` values can override shared defaults.

## Environment Modes

```text
development
staging
production
test
```

Production mode performs strict startup validation and fails fast on unsafe settings.

## Core Settings

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | Runtime environment. |
| `APP_DEBUG` | Enables debug behavior. Must be false in production. |
| `WEB_WORKERS` | Uvicorn worker count. Must be 1 in production for V1 realtime correctness. |
| `PUBLIC_BASE_URL` | Canonical external URL. Must be HTTPS in production. |
| `ALLOWED_HOSTS` | Comma-separated accepted hosts. Required in production. |
| `TRUSTED_PROXIES` | Comma-separated proxy IPs or CIDRs. |
| `WS_ALLOWED_ORIGINS` | Explicit WebSocket origins. Derived from `ALLOWED_HOSTS` when empty. |
| `GRAVEWRIGHT_DATA_DIR` | System and module package root. Defaults to `data/`. |
| `DATABASE_URL` | SQLAlchemy database URL. |

## Database Settings

Local default:

```env
DATABASE_URL=sqlite:///storage/gravewright.sqlite3
```

Production should use PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/gravewright
```

SQLite production use is refused unless `ALLOW_SQLITE_IN_PRODUCTION=true` is set. MySQL/MariaDB is not a supported production backend in V1.

## Session Settings

| Variable | Purpose |
| --- | --- |
| `SESSION_SECRET` | Signing secret. Use at least 32 random characters in production. |
| `SESSION_MAX_AGE` | Session lifetime in seconds. |
| `SESSION_COOKIE_NAME` | Browser cookie name. |
| `SESSION_COOKIE_SECURE` | Must be true in production. |
| `SESSION_COOKIE_HTTPONLY` | Must be true in production. |
| `SESSION_COOKIE_SAMESITE` | `lax`, `strict`, or `none`. |
| `SESSION_COOKIE_DOMAIN` | Optional cookie domain. |

## Rate and Size Limits

Configuration includes positive integer limits for:

- auth attempts and password reset windows;
- WebSocket message size and command buckets;
- viewport chunk width, height, area, known chunks, and layer count;
- fog operation and coordinate limits;
- token batch creation;
- board markers and measurements;
- map upload bytes, image dimensions, tile size, and tile count.

All numeric limits must be greater than zero.

## Privacy Settings

`PRIVACY_ENABLED` controls whether the privacy panel and related settings are visible for the instance.
